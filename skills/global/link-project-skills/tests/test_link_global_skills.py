"""Behavioural tests for link_global_skills.py and the shared skill resolution.

Everything runs against a throwaway ai-agents repository, a throwaway home
directory and a throwaway agent-config.json, so neither the developer's real
home, their configuration, nor this checkout's skills influence a result.

Tests that need filesystem links skip where links cannot be created.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import link_global_skills as lgs  # noqa: E402
import skill_links as sl  # noqa: E402

INTERNAL = ("alpha", "beta")


def _links_available() -> bool:
    """Probe whether this environment can create directory links at all."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target").mkdir()
            sl.create_link(root / "link", root / "target")
            return True
    except (OSError, NotImplementedError):
        return False


requires_links = unittest.skipUnless(_links_available(), "cannot create directory links here")


def write_skill(directory: Path, name: str) -> Path:
    """Create a skill directory whose SKILL.md declares `name`."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test skill {name}\n---\n\n# {name}\n", encoding="utf-8"
    )
    return directory


class GlobalCase(unittest.TestCase):
    """Base class: a fake repository, home directory and configuration."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.repo = self.root / "ai-agents"
        (self.repo / "global-instructions").mkdir(parents=True)
        (self.repo / "global-instructions" / "global_rule.md").write_text("rules", encoding="utf-8")
        self.global_dir = self.repo / "skills" / "global"
        for name in INTERNAL:
            write_skill(self.global_dir / name, name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.root / "agent-config.json"

    def run_linker(self, *argv: str) -> tuple[list[sl.Action], int]:
        """Invoke the global linker against the fake home and configuration."""
        args = lgs.build_parser().parse_args(
            ["--home", str(self.home), "--config", str(self.config), *argv]
        )
        return lgs.run(args, repo=self.repo)

    def make_external(self, name: str, folder: str = "") -> Path:
        """Create an independent skill checkout with SKILL.md at its root."""
        return write_skill(self.root / "checkouts" / (folder or f"{name}-skill"), name)

    def write_config(self, external: dict[str, object]) -> None:
        """Write an agent-config.json with the given external-skill section."""
        self.config.write_text(json.dumps({"skills": {"external": external}}), encoding="utf-8")

    def by_link(self, actions: list[sl.Action]) -> dict[str, sl.Action]:
        """Index actions by '<agent dir>/<name>' relative to the home directory."""
        indexed = {}
        for action in actions:
            path = Path(action.link)
            if self.home in path.parents:
                indexed[path.relative_to(self.home).as_posix()] = action
        return indexed

    def make_legacy(self, directory: str) -> Path:
        """Create the legacy layout: a whole-directory link to skills/global."""
        root = self.home / directory
        root.parent.mkdir(parents=True, exist_ok=True)
        sl.create_link(root, self.global_dir)
        return root


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


class TestConfiguration(GlobalCase):
    """agent-config.json is optional, strict when present, and never guessed at."""

    def test_missing_file_means_no_external_skills(self) -> None:
        self.assertEqual(sl.load_external_skills(self.config), {})

    def test_missing_skills_section_means_no_external_skills(self) -> None:
        self.config.write_text(json.dumps({"commit": {"author": "x"}}), encoding="utf-8")
        self.assertEqual(sl.load_external_skills(self.config), {})

    def test_comment_keys_are_ignored(self) -> None:
        checkout = self.make_external("cad-tool")
        self.config.write_text(
            json.dumps(
                {
                    "skills": {
                        "_readme": ["comment"],
                        "external": {"_example": "ignored", "cad-tool": {"path": str(checkout)}},
                    }
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(sl.load_external_skills(self.config), {"cad-tool": checkout})

    def test_malformed_configurations_are_rejected(self) -> None:
        cases = {
            "invalid json": "{",
            "top level list": json.dumps([]),
            "skills not object": json.dumps({"skills": []}),
            "unknown skills key": json.dumps({"skills": {"externals": {}}}),
            "external not object": json.dumps({"skills": {"external": []}}),
            "entry is a string": json.dumps({"skills": {"external": {"a": "/x"}}}),
            "path missing": json.dumps({"skills": {"external": {"a": {}}}}),
            "path empty": json.dumps({"skills": {"external": {"a": {"path": " "}}}}),
            "path not string": json.dumps({"skills": {"external": {"a": {"path": 3}}}}),
            "relative path": json.dumps({"skills": {"external": {"a": {"path": "rel/dir"}}}}),
            "unknown entry key": json.dumps(
                {"skills": {"external": {"a": {"path": str(self.root), "branch": "main"}}}}
            ),
            "name with separator": json.dumps(
                {"skills": {"external": {"../escape": {"path": str(self.root)}}}}
            ),
            "upper-case name": json.dumps(
                {"skills": {"external": {"Cad": {"path": str(self.root)}}}}
            ),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.config.write_text(text, encoding="utf-8")
                with self.assertRaises(sl.ConfigError):
                    sl.load_external_skills(self.config)

    def test_malformed_configuration_exits_before_touching_anything(self) -> None:
        self.config.write_text("{", encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.run_linker()
        self.assertEqual(caught.exception.code, sl.EXIT_CONFIG)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_home_relative_path_is_expanded(self) -> None:
        checkout = write_skill(self.home / "src" / "cad-tool-skill", "cad-tool")
        self.write_config({"cad-tool": {"path": "~/src/cad-tool-skill"}})
        with mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)}):
            loaded = sl.load_external_skills(self.config)
        self.assertTrue(sl.same_path(loaded["cad-tool"], checkout))

    @unittest.skipUnless(os.name == "nt", "Windows path forms")
    def test_windows_path_forms_are_equivalent(self) -> None:
        checkout = self.make_external("cad-tool")
        forms = {
            "backslashes": str(checkout),
            "forward slashes": checkout.as_posix(),
            "trailing separator": str(checkout) + "\\",
            "other case": str(checkout).upper(),
        }
        for label, value in forms.items():
            with self.subTest(label):
                self.write_config({"cad-tool": {"path": value}})
                loaded = sl.load_external_skills(self.config)["cad-tool"]
                self.assertTrue(sl.same_path(loaded, checkout))
                self.assertIsNone(sl.check_external("cad-tool", loaded))

    @unittest.skipUnless(os.name == "nt", "drive-relative paths exist only on Windows")
    def test_windows_drive_relative_path_is_rejected(self) -> None:
        self.write_config({"cad-tool": {"path": "D:checkouts\\cad-tool"}})
        with self.assertRaises(sl.ConfigError):
            sl.load_external_skills(self.config)

    @unittest.skipIf(os.name == "nt", "POSIX path forms")
    def test_posix_absolute_path_is_accepted_and_windows_form_is_not(self) -> None:
        checkout = self.make_external("cad-tool")
        self.write_config({"cad-tool": {"path": str(checkout)}})
        self.assertEqual(sl.load_external_skills(self.config), {"cad-tool": checkout})
        self.write_config({"cad-tool": {"path": "D:/checkouts/cad-tool"}})
        with self.assertRaises(sl.ConfigError):
            sl.load_external_skills(self.config)


class TestResolution(GlobalCase):
    """Internal and external skills resolve into one catalog."""

    def test_internal_skills_come_from_skills_global(self) -> None:
        catalog = sl.build_catalog(self.repo, self.config)
        self.assertEqual(sorted(catalog.skills), list(INTERNAL))
        self.assertEqual({s.kind for s in catalog.skills.values()}, {sl.KIND_INTERNAL})

    def test_a_link_inside_skills_global_is_not_an_internal_skill(self) -> None:
        if not _links_available():
            self.skipTest("cannot create directory links here")
        sl.create_link(self.global_dir / "vendored", self.make_external("vendored"))
        self.assertNotIn("vendored", sl.build_catalog(self.repo, self.config).skills)

    def test_external_skill_is_resolved_to_its_checkout(self) -> None:
        checkout = self.make_external("cad-tool", folder="cad-tool-repository")
        self.write_config({"cad-tool": {"path": str(checkout)}})
        skill = sl.build_catalog(self.repo, self.config).skills["cad-tool"]
        self.assertEqual((skill.source, skill.kind), (checkout, sl.KIND_EXTERNAL))

    def test_skill_md_with_byte_order_mark_is_read(self) -> None:
        checkout = self.root / "bom-skill"
        checkout.mkdir()
        (checkout / "SKILL.md").write_text("---\nname: bom\n---\n", encoding="utf-8-sig")
        self.assertEqual(sl.read_skill_name(checkout), "bom")

    def test_unusable_external_checkouts_are_reported(self) -> None:
        not_a_skill = self.root / "empty-checkout"
        not_a_skill.mkdir()
        a_file = self.root / "file.txt"
        a_file.write_text("x", encoding="utf-8")
        cases = {
            "missing": (self.root / "never-cloned", "not found"),
            "no SKILL.md": (not_a_skill, "no SKILL.md"),
            "a file": (a_file, "not a directory"),
            "wrong name": (self.make_external("other"), "declares name"),
        }
        for label, (path, fragment) in cases.items():
            with self.subTest(label):
                self.write_config({"cad-tool": {"path": str(path)}})
                catalog = sl.build_catalog(self.repo, self.config)
                self.assertNotIn("cad-tool", catalog.skills)
                self.assertIn(fragment, catalog.unavailable["cad-tool"][1])

    def test_external_registration_shadows_an_internal_copy_with_a_note(self) -> None:
        checkout = self.make_external("alpha")
        self.write_config({"alpha": {"path": str(checkout)}})
        catalog = sl.build_catalog(self.repo, self.config)
        self.assertEqual(catalog.skills["alpha"].source, checkout)
        self.assertTrue(any("shadows the internal copy" in note for note in catalog.notes))

    def test_broken_external_registration_does_not_fall_back_to_the_internal_copy(self) -> None:
        self.write_config({"alpha": {"path": str(self.root / "never-cloned")}})
        catalog = sl.build_catalog(self.repo, self.config)
        self.assertNotIn("alpha", catalog.skills)
        self.assertIn("alpha", catalog.unavailable)


# --------------------------------------------------------------------------
# Global skill directories
# --------------------------------------------------------------------------


class TestDryRun(GlobalCase):
    """--dry-run must not touch the home directory."""

    def test_dry_run_on_a_fresh_home_creates_nothing(self) -> None:
        self.write_config({"cad-tool": {"path": str(self.make_external("cad-tool"))}})
        actions, code = self.run_linker("--dry-run", "--antigravity")
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(list(self.home.iterdir()), [])
        links = self.by_link(actions)
        for directory in (".claude/skills", ".agents/skills"):
            for name in (*INTERNAL, "cad-tool"):
                self.assertEqual(links[f"{directory}/{name}"].outcome, "would-link")

    @requires_links
    def test_dry_run_migration_changes_nothing(self) -> None:
        root = self.make_legacy(".claude/skills")
        actions, code = self.run_linker("--migrate", "--dry-run", "--agents", "claude")
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(actions[0].outcome, "would-replace")
        self.assertTrue(sl.is_link(root))
        self.assertEqual({a.outcome for a in actions[1:]}, {"would-link"})


@requires_links
class TestPerSkillLinks(GlobalCase):
    """Every skill gets its own link in both agent directories."""

    def test_internal_and_external_skills_are_linked(self) -> None:
        checkout = self.make_external("cad-tool", folder="cad-tool-repository")
        self.write_config({"cad-tool": {"path": str(checkout)}})
        actions, code = self.run_linker()
        self.assertEqual(code, sl.EXIT_OK, actions)
        for directory in (".claude/skills", ".agents/skills"):
            root = self.home / directory
            self.assertFalse(sl.is_link(root))
            for name in INTERNAL:
                self.assertTrue(sl.same_path(sl.link_target(root / name), self.global_dir / name))
            self.assertTrue(sl.same_path(sl.link_target(root / "cad-tool"), checkout))
            self.assertTrue((root / "cad-tool" / "SKILL.md").is_file())

    def test_second_run_skips_everything(self) -> None:
        self.write_config({"cad-tool": {"path": str(self.make_external("cad-tool"))}})
        self.run_linker()
        actions, code = self.run_linker()
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual({a.outcome for a in actions}, {"skipped"}, actions)

    def test_a_stale_link_is_repointed(self) -> None:
        old = write_skill(self.root / "old-copy", "cad-tool")
        root = self.home / ".agents" / "skills"
        sl.create_link(root / "cad-tool", old)
        checkout = self.make_external("cad-tool")
        self.write_config({"cad-tool": {"path": str(checkout)}})
        actions, code = self.run_linker("--agents", "codex")
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(self.by_link(actions)[".agents/skills/cad-tool"].outcome, "replaced")
        self.assertTrue(sl.same_path(sl.link_target(root / "cad-tool"), checkout))
        self.assertTrue((old / "SKILL.md").is_file(), "the old target must survive")

    def test_a_broken_link_is_repointed(self) -> None:
        gone = self.root / "gone"
        gone.mkdir()
        link = self.home / ".claude" / "skills" / "alpha"
        sl.create_link(link, gone)
        gone.rmdir()
        actions, code = self.run_linker("--agents", "claude")
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(self.by_link(actions)[".claude/skills/alpha"].outcome, "replaced")
        self.assertTrue((link / "SKILL.md").is_file())

    def test_a_real_directory_is_rejected_and_kept(self) -> None:
        mine = write_skill(self.home / ".claude" / "skills" / "alpha", "alpha")
        (mine / "notes.md").write_text("mine", encoding="utf-8")
        actions, code = self.run_linker("--agents", "claude")
        self.assertEqual(code, sl.EXIT_REJECTED)
        self.assertEqual(self.by_link(actions)[".claude/skills/alpha"].outcome, "rejected")
        self.assertEqual((mine / "notes.md").read_text(encoding="utf-8"), "mine")
        # The rest is still linked.
        self.assertEqual(self.by_link(actions)[".claude/skills/beta"].outcome, "linked")

    def test_unmanaged_entries_are_left_alone(self) -> None:
        own = write_skill(self.home / ".claude" / "skills" / "my-own-skill", "my-own-skill")
        self.run_linker("--agents", "claude")
        self.assertTrue((own / "SKILL.md").is_file())
        self.assertFalse(sl.is_link(own))

    def test_missing_external_checkout_is_rejected_but_others_are_linked(self) -> None:
        self.write_config({"cad-tool": {"path": str(self.root / "never-cloned")}})
        actions, code = self.run_linker("--agents", "codex")
        self.assertEqual(code, sl.EXIT_REJECTED)
        links = self.by_link(actions)
        self.assertEqual(links[".agents/skills/cad-tool"].outcome, "rejected")
        self.assertEqual(links[".agents/skills/alpha"].outcome, "linked")
        self.assertFalse((self.home / ".agents" / "skills" / "cad-tool").exists())

    def test_a_file_where_the_directory_belongs_is_rejected(self) -> None:
        (self.home / ".agents").mkdir()
        (self.home / ".agents" / "skills").write_text("oops", encoding="utf-8")
        actions, code = self.run_linker("--agents", "codex")
        self.assertEqual(code, sl.EXIT_REJECTED)
        self.assertEqual(len(actions), 1)
        self.assertTrue((self.home / ".agents" / "skills").is_file())


@requires_links
class TestLegacyMigration(GlobalCase):
    """The whole-directory link to skills/global is converted only on request."""

    def test_legacy_layout_is_rejected_without_migrate(self) -> None:
        root = self.make_legacy(".claude/skills")
        actions, code = self.run_linker("--agents", "claude")
        self.assertEqual(code, sl.EXIT_REJECTED)
        self.assertEqual(len(actions), 1)
        self.assertIn("--migrate", actions[0].detail)
        self.assertTrue(sl.is_link(root))
        self.assertEqual(sorted(p.name for p in self.global_dir.iterdir()), list(INTERNAL))

    def test_migrate_converts_to_per_skill_links_without_touching_the_skills(self) -> None:
        checkout = self.make_external("cad-tool")
        self.write_config({"cad-tool": {"path": str(checkout)}})
        for directory in (".claude/skills", ".agents/skills"):
            self.make_legacy(directory)

        actions, code = self.run_linker("--migrate")
        self.assertEqual(code, sl.EXIT_OK, actions)
        for directory in (".claude/skills", ".agents/skills"):
            root = self.home / directory
            self.assertEqual(self.by_link(actions)[directory].outcome, "replaced")
            self.assertFalse(sl.is_link(root))
            self.assertEqual(sorted(p.name for p in root.iterdir()), [*INTERNAL, "cad-tool"])
        # Internal skills are intact and nothing was written into the repository.
        self.assertEqual(sorted(p.name for p in self.global_dir.iterdir()), list(INTERNAL))
        for name in INTERNAL:
            self.assertTrue((self.global_dir / name / "SKILL.md").is_file())

    def test_migrate_is_idempotent(self) -> None:
        self.make_legacy(".agents/skills")
        self.run_linker("--migrate", "--agents", "codex")
        actions, code = self.run_linker("--migrate", "--agents", "codex")
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual({a.outcome for a in actions}, {"skipped"})

    def test_a_link_to_somewhere_else_is_never_migrated(self) -> None:
        elsewhere = self.root / "dotfiles-skills"
        elsewhere.mkdir()
        root = self.home / ".claude" / "skills"
        root.parent.mkdir(parents=True)
        sl.create_link(root, elsewhere)
        actions, code = self.run_linker("--migrate", "--agents", "claude")
        self.assertEqual(code, sl.EXIT_REJECTED)
        self.assertTrue(sl.is_link(root))
        self.assertEqual(list(elsewhere.iterdir()), [])


# --------------------------------------------------------------------------
# Antigravity
# --------------------------------------------------------------------------


class TestAntigravity(GlobalCase):
    """skills.json entries are added, never rewritten or removed."""

    def setUp(self) -> None:
        super().setUp()
        self.registry = self.home / ".gemini" / "config" / "skills.json"
        self.checkout = self.make_external("cad-tool", folder="cad-tool-repository")
        self.write_config({"cad-tool": {"path": str(self.checkout)}})

    def entries(self) -> list[dict[str, object]]:
        """Read the registry's entries."""
        return json.loads(self.registry.read_text(encoding="utf-8"))["entries"]

    def run_antigravity(self, *argv: str) -> tuple[list[sl.Action], int]:
        """Run only the Antigravity registration (no link directories)."""
        args = lgs.build_parser().parse_args(
            ["--home", str(self.home), "--config", str(self.config), "--antigravity", *argv]
        )
        catalog = sl.build_catalog(self.repo, self.config)
        actions = lgs.register_antigravity(self.home, catalog, self.repo, args.dry_run)
        return actions, sl.exit_code(actions)

    def test_skipped_when_antigravity_is_not_set_up(self) -> None:
        actions, code = self.run_antigravity()
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(actions[0].outcome, "skipped")
        self.assertFalse((self.home / ".gemini").exists())

    def test_registry_is_created_with_internal_and_external_entries(self) -> None:
        (self.home / ".gemini").mkdir()
        actions, code = self.run_antigravity()
        self.assertEqual(code, sl.EXIT_OK)
        self.assertEqual(
            self.entries(),
            [
                {"path": self.global_dir.as_posix()},
                {
                    "path": self.checkout.parent.as_posix(),
                    "include_only": ["cad-tool-repository"],
                },
            ],
        )

    def test_existing_entries_and_keys_are_preserved_and_not_duplicated(self) -> None:
        self.registry.parent.mkdir(parents=True)
        own = {"path": "~/personal-skills", "exclude": ["old-.*"]}
        self.registry.write_text(
            json.dumps({"inherits": [{"path": "x.json"}], "entries": [own]}), encoding="utf-8"
        )
        self.run_antigravity()
        first = self.registry.read_text(encoding="utf-8")
        data = json.loads(first)
        self.assertEqual(data["inherits"], [{"path": "x.json"}])
        self.assertEqual(data["entries"][0], own)
        self.assertEqual(len(data["entries"]), 3)

        actions, _ = self.run_antigravity()
        self.assertEqual({a.outcome for a in actions}, {"skipped"})
        self.assertEqual(self.registry.read_text(encoding="utf-8"), first)

    def test_equivalent_existing_path_counts_as_registered(self) -> None:
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text(
            json.dumps({"entries": [{"path": str(self.global_dir) + os.sep}]}), encoding="utf-8"
        )
        actions, _ = self.run_antigravity()
        self.assertEqual([a.outcome for a in actions], ["skipped", "linked"])

    def test_malformed_registry_is_rejected_and_untouched(self) -> None:
        self.registry.parent.mkdir(parents=True)
        self.registry.write_text("{broken", encoding="utf-8")
        actions, code = self.run_antigravity()
        self.assertEqual(code, sl.EXIT_REJECTED)
        self.assertEqual(self.registry.read_text(encoding="utf-8"), "{broken")

    def test_dry_run_leaves_the_registry_alone(self) -> None:
        (self.home / ".gemini").mkdir()
        actions, _ = self.run_antigravity("--dry-run")
        self.assertEqual({a.outcome for a in actions}, {"would-link"})
        self.assertFalse(self.registry.exists())


# --------------------------------------------------------------------------
# Path normalisation
# --------------------------------------------------------------------------


class TestPathNormalisation(unittest.TestCase):
    """Paths read back from links must compare equal to the paths configured."""

    @unittest.skipUnless(os.name == "nt", "Windows extended-length prefixes")
    def test_extended_length_prefix_is_stripped(self) -> None:
        self.assertEqual(sl.normalize_path("\\\\?\\D:\\x\\y"), Path("D:\\x\\y"))
        self.assertEqual(sl.normalize_path("\\\\?\\UNC\\server\\share"), Path("\\\\server\\share"))

    @unittest.skipUnless(os.name == "nt", "Windows extended-length prefixes")
    def test_prefixed_and_plain_paths_are_the_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp).resolve()
            self.assertTrue(sl.same_path("\\\\?\\" + str(plain), plain))

    @unittest.skipIf(os.name == "nt", "POSIX paths are left as they are")
    def test_posix_paths_are_unchanged(self) -> None:
        self.assertEqual(sl.normalize_path("/srv/skills"), Path("/srv/skills"))

    def test_none_is_never_the_same_path(self) -> None:
        self.assertFalse(sl.same_path(None, Path.cwd()))

    @requires_links
    def test_link_target_of_a_fresh_link_equals_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            link = Path(tmp) / "link"
            sl.create_link(link, target)
            self.assertTrue(sl.same_path(sl.link_target(link), target))


if __name__ == "__main__":
    unittest.main()
