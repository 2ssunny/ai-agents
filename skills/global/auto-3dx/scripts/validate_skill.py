"""Validates the auto-3dx skill against its document contract and the installed SDK.

Two checks run:

1. Document contract (standard library only): the frontmatter holds only `name`
   and `description`, the name matches the folder, every linked `references/`
   file exists, SKILL.md stays short, and no machine-specific user path is
   committed.
2. API check (needs `auto_3dx` importable): every ```python block in SKILL.md and
   references/examples.md is parsed, and each attribute or call on an object whose
   type can be inferred is checked against the installed package -- the member
   exists, the arguments bind to its signature, package-root imports come from
   `auto_3dx.__all__`, and no retired name is used. Without `auto_3dx` the check is
   reported as SKIPPED, which is not a pass.

Run it in the environment where auto-3dx is installed:

    python skills/global/auto-3dx/scripts/validate_skill.py
"""

import ast
import collections.abc
import dataclasses
import importlib
import inspect
import re
import sys
import types
import typing
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
CODE_FILES = ("SKILL.md", "references/examples.md")
ALLOWED_FRONTMATTER_KEYS = {"name", "description"}
MAX_SKILL_LINES = 200
USER_PATH_PATTERNS = (r"[A-Za-z]:\\Users\\", r"/home/[a-z]+/", r"/Users/[a-z]+/")

#: Retired or deprecated upstream names that examples must not teach.
RETIRED_NAMES = {
    "snapshot_edges": "use part.topology.edges()",
    "snapshot_faces": "use part.topology.faces()",
    "editor_com_object": "use com_object",
    "raw": "the only escape hatch is com_object",
}

CODE_BLOCK = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
SEQUENCE_ORIGINS = (
    list,
    tuple,
    collections.abc.Iterator,
    collections.abc.Iterable,
    collections.abc.Sequence,
    collections.abc.Generator,
)
MISSING = object()

# Inferred types are small tuples:
#   ("inst", cls)  an instance of an auto_3dx class
#   ("cls", cls)   the class object itself
#   ("mod", mod)   an auto_3dx module
#   ("seq", item)  a list, tuple or iterator whose items have type `item`
#   ("method", cls, name, static_member, owner_kind)
Inferred = tuple | None


def read_text(path: Path) -> str:
    """Reads a file as UTF-8 with normalised newlines."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def check_document() -> list[str]:
    """Checks the SKILL.md contract shared by every skill in this repository.

    Returns:
        One message per failure; empty when the contract holds.
    """
    failures: list[str] = []
    skill_text = read_text(SKILL_DIR / "SKILL.md")
    match = FRONTMATTER.match(skill_text)
    if match is None:
        return ["SKILL.md must open with a --- frontmatter block."]
    keys = re.findall(r"^([A-Za-z_][\w-]*):", match.group(1), re.MULTILINE)
    extra = set(keys) - ALLOWED_FRONTMATTER_KEYS
    if extra:
        failures.append(f"Frontmatter has platform-specific keys: {sorted(extra)}.")
    name = re.search(r"^name:\s*(\S+)\s*$", match.group(1), re.MULTILINE)
    if name is None or name.group(1) != SKILL_DIR.name:
        failures.append(f"Frontmatter name must be {SKILL_DIR.name!r}.")
    if not re.search(r"^description:\s*\S", match.group(1), re.MULTILINE):
        failures.append("Frontmatter description must not be empty.")
    lines = len(skill_text.splitlines())
    if lines > MAX_SKILL_LINES:
        failures.append(f"SKILL.md is {lines} lines; move detail into references/.")
    for link in sorted(set(re.findall(r"\]\((references/[\w./-]+)\)", skill_text))):
        if not (SKILL_DIR / link).is_file():
            failures.append(f"SKILL.md links {link}, which does not exist.")
    for path in sorted(SKILL_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".yaml", ".py"}:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = read_text(path)
        for pattern in USER_PATH_PATTERNS:
            if re.search(pattern, text):
                failures.append(f"{path.relative_to(SKILL_DIR)} contains a user path.")
    return failures


def resolve_hint(hint: Any) -> Inferred:
    """Turns a type hint into an inferred type, or None when it is not useful."""
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        options = [arg for arg in typing.get_args(hint) if arg is not type(None)]
        return resolve_hint(options[0]) if len(options) == 1 else None
    if origin in SEQUENCE_ORIGINS:
        args = [arg for arg in typing.get_args(hint) if arg is not Ellipsis]
        return ("seq", resolve_hint(args[0]) if args else None)
    if inspect.isclass(hint) and hint.__module__.startswith("auto_3dx"):
        return ("inst", hint)
    return None


def return_type(function: Any) -> Inferred:
    """Reads a function's return annotation as an inferred type."""
    try:
        hints = typing.get_type_hints(inspect.unwrap(function))
    except Exception:  # noqa: BLE001 -- unresolvable forward references are not errors
        return None
    return resolve_hint(hints.get("return"))


class ApiChecker:
    """Walks example code and checks it against the installed auto_3dx package."""

    def __init__(self, root_exports: set[str], label: str) -> None:
        self.root_exports = root_exports
        self.label = label
        self.env: dict[str, Inferred] = {}
        self.errors: list[str] = []
        self.checked = 0

    def fail(self, node: ast.AST, message: str) -> None:
        self.errors.append(f"{self.label}:{getattr(node, 'lineno', '?')}: {message}")

    # Statements ------------------------------------------------------------------

    def block(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.statement(statement)

    def statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.ImportFrom):
            self.import_from(node)
        elif isinstance(node, ast.Import):
            self.import_modules(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = self.expr(node.value)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                self.bind_target(target, value)
        elif isinstance(node, ast.With):
            for item in node.items:
                context = self.expr(item.context_expr)
                if item.optional_vars is not None:
                    self.bind_target(item.optional_vars, self.entered(context))
            self.block(node.body)
        elif isinstance(node, ast.For):
            iterable = self.expr(node.iter)
            item = iterable[1] if iterable and iterable[0] == "seq" else None
            self.bind_target(node.target, item)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, ast.Try):
            self.block(node.body)
            for handler in node.handlers:
                self.expr(handler.type)
                if handler.name:
                    self.env[handler.name] = None
                self.block(handler.body)
            self.block(node.orelse)
            self.block(node.finalbody)
        elif isinstance(node, (ast.If, ast.While)):
            self.expr(node.test)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.block(node.body)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self.expr(child)

    def bind_target(self, target: ast.expr, value: Inferred) -> None:
        if isinstance(target, ast.Name):
            self.env[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            item = value[1] if value and value[0] == "seq" else None
            for element in target.elts:
                self.bind_target(element, item)
            return
        self.expr(target)

    def entered(self, context: Inferred) -> Inferred:
        """Returns the type a `with` statement binds for a context expression."""
        if context and context[0] == "seq":
            return context[1]
        if context and context[0] == "inst":
            enter = inspect.getattr_static(context[1], "__enter__", None)
            return return_type(enter) if inspect.isfunction(enter) else None
        return None

    def import_from(self, node: ast.ImportFrom) -> None:
        module_name = node.module or ""
        if not module_name.startswith("auto_3dx"):
            return
        try:
            module = importlib.import_module(module_name)
        except ImportError as error:
            self.fail(node, f"cannot import {module_name}: {error}")
            return
        for alias in node.names:
            if module_name == "auto_3dx" and alias.name not in self.root_exports:
                self.fail(node, f"{alias.name} is not a package-root export; import it from its own package")
            value = getattr(module, alias.name, MISSING)
            if value is MISSING:
                self.fail(node, f"{module_name} has no name {alias.name!r}")
                continue
            self.checked += 1
            self.env[alias.asname or alias.name] = self.wrap(value)

    def import_modules(self, node: ast.Import) -> None:
        for alias in node.names:
            if not alias.name.startswith("auto_3dx"):
                continue
            try:
                module = importlib.import_module(alias.name)
            except ImportError as error:
                self.fail(node, f"cannot import {alias.name}: {error}")
                continue
            if alias.asname:
                self.env[alias.asname] = ("mod", module)
            else:
                self.env[alias.name.split(".")[0]] = ("mod", importlib.import_module("auto_3dx"))

    @staticmethod
    def wrap(value: Any) -> Inferred:
        if inspect.isclass(value):
            return ("cls", value)
        if inspect.ismodule(value):
            return ("mod", value)
        return None

    # Expressions -----------------------------------------------------------------

    def expr(self, node: ast.AST | None) -> Inferred:
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return self.env.get(node.id)
        if isinstance(node, ast.Attribute):
            return self.attribute(node)
        if isinstance(node, ast.Call):
            return self.call(node)
        if isinstance(node, ast.Subscript):
            self.expr(node.slice)
            base = self.expr(node.value)
            if base and base[0] == "seq":
                return base[1]
            if base and base[0] == "inst":
                getitem = inspect.getattr_static(base[1], "__getitem__", None)
                return return_type(getitem) if inspect.isfunction(getitem) else None
            return None
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return self.comprehension(node)
        for child in ast.iter_child_nodes(node):
            self.expr(child)
        return None

    def comprehension(self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp) -> Inferred:
        """Checks a comprehension with its loop variables typed, without leaking them."""
        saved = dict(self.env)
        for generator in node.generators:
            iterable = self.expr(generator.iter)
            self.bind_target(generator.target, iterable[1] if iterable and iterable[0] == "seq" else None)
            for condition in generator.ifs:
                self.expr(condition)
        if isinstance(node, ast.DictComp):
            self.expr(node.key)
            self.expr(node.value)
        else:
            self.expr(node.elt)
        self.env = saved
        return None

    def attribute(self, node: ast.Attribute) -> Inferred:
        if node.attr in RETIRED_NAMES:
            self.fail(node, f"{node.attr!r} is retired: {RETIRED_NAMES[node.attr]}")
        owner = self.expr(node.value)
        if not owner or owner[0] not in {"inst", "cls", "mod"}:
            return None
        if owner[0] == "mod":
            value = getattr(owner[1], node.attr, MISSING)
            if value is MISSING:
                self.fail(node, f"{owner[1].__name__} has no name {node.attr!r}")
                return None
            self.checked += 1
            return self.wrap(value)
        cls = owner[1]
        # Dataclass fields first: a field with a default is also a class attribute
        # holding that default, which would hide the field's annotated type.
        if dataclasses.is_dataclass(cls) and node.attr in {f.name for f in dataclasses.fields(cls)}:
            self.checked += 1
            try:
                return resolve_hint(typing.get_type_hints(cls).get(node.attr))
            except Exception:  # noqa: BLE001
                return None
        static = inspect.getattr_static(cls, node.attr, MISSING)
        if static is MISSING:
            self.fail(node, f"{cls.__name__} has no member {node.attr!r}")
            return None
        self.checked += 1
        if isinstance(static, property):
            return return_type(static.fget)
        if inspect.isfunction(static) or isinstance(static, (classmethod, staticmethod)):
            return ("method", cls, node.attr, static, owner[0])
        return None

    def call(self, node: ast.Call) -> Inferred:
        for argument in node.args:
            self.expr(argument.value if isinstance(argument, ast.Starred) else argument)
        for keyword in node.keywords:
            self.expr(keyword.value)
        target = self.expr(node.func)
        if not target:
            return None
        if target[0] == "cls":
            return ("inst", target[1])
        if target[0] != "method":
            return None
        _, cls, name, static, owner_kind = target
        function = static.__func__ if isinstance(static, (classmethod, staticmethod)) else static
        self.bind_arguments(node, cls, name, static, function, owner_kind)
        return return_type(function)

    def bind_arguments(
        self, node: ast.Call, cls: type, name: str, static: Any, function: Any, owner_kind: str
    ) -> None:
        if any(isinstance(arg, ast.Starred) for arg in node.args):
            return
        if any(keyword.arg is None for keyword in node.keywords):
            return
        needs_first = isinstance(static, classmethod) or (
            inspect.isfunction(static) and owner_kind == "inst"
        )
        try:
            signature = inspect.signature(function)
        except (TypeError, ValueError):
            return
        positional = [None] * (len(node.args) + (1 if needs_first else 0))
        keywords = {keyword.arg: None for keyword in node.keywords}
        try:
            signature.bind(*positional, **keywords)
        except TypeError as error:
            self.fail(node, f"{cls.__name__}.{name}{signature} rejects this call: {error}")


def check_code(source: str, label: str, root_exports: set[str]) -> tuple[list[str], int]:
    """Checks every python block in one Markdown document.

    Blocks are checked in order and share names, as a reader would run them.

    Returns:
        The failure messages and how many names were checked.
    """
    checker = ApiChecker(root_exports, label)
    for match in CODE_BLOCK.finditer(source):
        first_line = source.count("\n", 0, match.start(1))
        try:
            tree = ast.parse(match.group(1))
        except SyntaxError as error:
            checker.errors.append(f"{label}:{first_line + (error.lineno or 0)}: syntax error: {error.msg}")
            continue
        ast.increment_lineno(tree, first_line)
        checker.block(tree.body)
    return checker.errors, checker.checked


def check_api() -> tuple[str, list[str], int]:
    """Runs the API check, or reports it as skipped when auto_3dx is unavailable."""
    try:
        auto_3dx = importlib.import_module("auto_3dx")
    except ImportError:
        return "SKIPPED", ["auto_3dx is not importable in this environment."], 0
    failures: list[str] = []
    checked = 0
    for relative in CODE_FILES:
        errors, count = check_code(read_text(SKILL_DIR / relative), relative, set(auto_3dx.__all__))
        failures.extend(errors)
        checked += count
    if checked == 0:
        failures.append("No auto_3dx names were checked; the examples could not be analysed.")
    status = "FAIL" if failures else "PASS"
    return status, failures, checked


def main() -> int:
    document_failures = check_document()
    print(f"document contract: {'FAIL' if document_failures else 'PASS'}")
    for failure in document_failures:
        print(f"  - {failure}")

    status, api_messages, checked = check_api()
    detail = f" ({checked} names checked)" if status != "SKIPPED" else ""
    print(f"api check: {status}{detail}")
    for message in api_messages:
        print(f"  - {message}")

    return 1 if document_failures or status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
