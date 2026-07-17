# Code Style & Formatting

## Python
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes.
- **Type Hints**: Mandatory on all function signatures. `def foo(x: int) -> str:`
- **Docstrings**: Google style. Required for all public functions/classes.
- **Imports**: stdlib → third-party → local. Separated by blank lines.
- **Magic Numbers**: No bare numeric literals. Define as named constants.
- **Max Line Length**: 100 characters.

## JavaScript / TypeScript
- **Naming**: `camelCase` for variables/functions, `PascalCase` for components/classes.
- **TypeScript**: Prefer `interface` over `type` for object shapes.
- **Async**: Use `async/await`. Avoid raw `.then()` chains.
- **Components**: One component per file. File name matches component name.
- **Package manager**: npm only (no pnpm, no yarn).

## General
- **No dead code**: Remove unused imports, commented-out blocks before committing.
- **No magic strings**: Use enums or constants for repeated string literals.
- **Comments**: Explain *why*, not *what*. Code should be self-documenting.
