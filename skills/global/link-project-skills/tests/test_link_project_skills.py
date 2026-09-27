"""Behavioural tests for link-project-skills.

The linker touches real directories, so these tests care most about what it
refuses to do: never delete a real directory, never write inside a legacy
whole-directory junction, never silently change what a link points at without
saying so.

Symlink creation can be unavailable (Windows without Developer Mode, some
sandboxes); those tests skip rather than fail, and the mapping tests — which need
no filesystem links — always run.

Every run passes an explicit --config inside a temporary directory, so the
developer's own agent-config.json and local checkouts never influence a result.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
LINKER_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(LINKER_DIR))

import link_project_skills as lps  # noqa: E402
import skill_links  # noqa: E402


def _symlinks_available() -> bool:
    """Probe whether this environment can create directory links at all."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target").mkdir()
            lps.create_link(root / "link", root / "target")
            return True
    except (OSError, NotImplementedError):
        return False


SYMLINKS_OK = _symlinks_available()
requires_links = unittest.skipUnless(SYMLINKS_OK, "this environment cannot create directory links")


class LinkerCase(unittest.TestCase):
    """Base class providing a throwaway project directory."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.project = self.root / "study-project"
        self.project.mkdir()
        self.config = self.root / "agent-config.json"
        self.addCleanup(self._tmp.cleanup)

    def run_linker(self, *argv: str) -> tuple[list[lps.Action], int]:
        """Invoke the linker with the project and an isolated config pre-filled."""
        args = lps.build_parser().parse_args(
            ["--project", str(self.project), "--config", str(self.config), *argv]
        )
        return lps.run(args)

    def make_external(self, name: str, folder: str | None = None) -> Path:
        """Create an independent skill checkout with SKILL.md at its root."""
        checkout = self.root / "checkouts" / (folder or f"{name}-skill")
        checkout.mkdir(parents=True)
        (checkout / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: test skill\n---\n", encoding="utf-8"
        )
        return checkout

    def register(self, name: str, path: Path) -> None:
        """Write an agent-config.json registering one external skill."""
        config = {"skills": {"external": {name: {"path": str(path)}}}}
        self.config.write_text(json.dumps(config), encoding="utf-8")

    def outcomes(self, actions: list[lps.Action]) -> dict[str, str]:
        """Map each link path's basename+parent to its outcome."""
        return {
            f"{Path(a.link).parent.parent.name}/{Path(a.link).name}": a.outcome for a in actions
        }


class TestRepositoryResolution(unittest.TestCase):
    """The linker must find its own repository without a hardcoded path."""

    def test_repo_root_is_this_checkout(self) -> None:
        self.assertEqual(lps.resolve_repo(), REPO_ROOT)

    def test_repo_marker_exists(self) -> None:
        self.assertTrue((lps.REPO_ROOT / lps.REPO_MARKER).is_file())

    def test_no_absolute_path_is_hardcoded(self) -> None:
        for script in sorted(LINKER_DIR.glob("*.py")):
            source = script.read_text(encoding="utf-8")
            for fragment in ("C:\\Users", "D:\\coding", "D:/coding", "/home/user/", "/Users/"):
                with self.subTest(script=script.name, fragment=fragment):
                    self.assertNotIn(fragment, source)


class TestTargetMapping(LinkerCase):
    """Both agent directories must map to the same canonical source."""

    def test_both_agent_directories_are_populated(self) -> None:
        actions, _ = self.run_linker("--skill", "exam-prep", "--dry-run")
        links = {Path(action.link) for action in actions}
        self.assertIn(self.project / ".agents" / "skills" / "exam-prep", links)
        self.assertIn(self.project / ".claude" / "skills" / "exam-prep", links)

    def test_both_links_share_one_canonical_target(self) -> None:
        actions, _ = self.run_linker("--skill", "exam-prep", "--dry-run")
        targets = {action.target for action in actions}
        self.assertEqual(len(targets), 1, f"content would be duplicated: {targets}")
        self.assertEqual(
            Path(targets.pop()), REPO_ROOT / "skills" / "global" / "exam-prep"
        )

    def test_agents_selection_narrows_the_targets(self) -> None:
        claude_only, _ = self.run_linker("--skill", "exam-prep", "--agents", "claude", "--dry-run")
        codex_only, _ = self.run_linker("--skill", "exam-prep", "--agents", "codex", "--dry-run")
        self.assertEqual(len(claude_only), 1)
        self.assertEqual(len(codex_only), 1)
        self.assertIn(".claude", claude_only[0].link)
        self.assertIn(".agents", codex_only[0].link)

    def test_unknown_skill_is_rejected_before_anything_is_touched(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            self.run_linker("--skill", "no-such-skill")
        self.assertEqual(caught.exception.code, lps.EXIT_UNRESOLVED)
        self.assertFalse((self.project / ".claude").exists())

    def test_linking_nothing_is_a_usage_error(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            self.run_linker()
        self.assertEqual(caught.exception.code, skill_links.EXIT_USAGE)


class TestExternalSkills(LinkerCase):
    """A registered external checkout is linked in place, never copied."""

    def test_external_skill_resolves_to_its_checkout(self) -> None:
        checkout = self.make_external("cad-tool")
        self.register("cad-tool", checkout)
        actions, code = self.run_linker("--skill", "cad-tool", "--dry-run")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertEqual({Path(a.target) for a in actions}, {checkout})

    def test_link_is_named_after_the_skill_not_the_checkout_folder(self) -> None:
        checkout = self.make_external("cad-tool", folder="some-other-folder-name")
        self.register("cad-tool", checkout)
        actions, _ = self.run_linker("--skill", "cad-tool", "--dry-run")
        self.assertEqual({Path(a.link).name for a in actions}, {"cad-tool"})

    def test_internal_and_external_skills_link_together(self) -> None:
        self.register("cad-tool", self.make_external("cad-tool"))
        actions, code = self.run_linker("--skill", "exam-prep", "--skill", "cad-tool", "--dry-run")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertEqual(len(actions), 4)
        internal = REPO_ROOT / "skills" / "global" / "exam-prep"
        self.assertIn(internal, {Path(a.target) for a in actions})

    def test_missing_checkout_is_an_unresolved_skill(self) -> None:
        self.register("cad-tool", self.root / "never-cloned")
        with self.assertRaises(SystemExit) as caught:
            self.run_linker("--skill", "cad-tool")
        self.assertEqual(caught.exception.code, lps.EXIT_UNRESOLVED)
        self.assertFalse((self.project / ".claude").exists())

    def test_checkout_declaring_another_name_is_unresolved(self) -> None:
        self.register("cad-tool", self.make_external("something-else"))
        with self.assertRaises(SystemExit) as caught:
            self.run_linker("--skill", "cad-tool")
        self.assertEqual(caught.exception.code, lps.EXIT_UNRESOLVED)

    def test_malformed_configuration_stops_before_anything_is_touched(self) -> None:
        self.config.write_text("{not json", encoding="utf-8")
        with self.assertRaises(SystemExit) as caught:
            self.run_linker("--skill", "exam-prep")
        self.assertEqual(caught.exception.code, skill_links.EXIT_CONFIG)
        self.assertFalse((self.project / ".claude").exists())

    def test_unregistered_name_is_unresolved(self) -> None:
        self.register("cad-tool", self.make_external("cad-tool"))
        with self.assertRaises(SystemExit) as caught:
            self.run_linker("--skill", "no-such-skill")
        self.assertEqual(caught.exception.code, lps.EXIT_UNRESOLVED)


class TestDryRun(LinkerCase):
    """--dry-run must not touch the filesystem."""

    def test_dry_run_creates_nothing(self) -> None:
        self.run_linker("--skill", "exam-prep", "--dry-run", "--gitignore")
        self.assertFalse((self.project / ".claude").exists())
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".gitignore").exists())

    def test_dry_run_reports_intended_actions(self) -> None:
        actions, code = self.run_linker("--skill", "exam-prep", "--dry-run")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertTrue(all(action.outcome == "would-link" for action in actions))


@requires_links
class TestIdempotency(LinkerCase):
    """Re-running must be safe and must say so."""

    def test_first_run_links_and_second_run_skips(self) -> None:
        first, code = self.run_linker("--skill", "exam-prep")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertTrue(all(action.outcome == "linked" for action in first), msg=first)

        second, code = self.run_linker("--skill", "exam-prep")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertTrue(all(action.outcome == "skipped" for action in second), msg=second)

    def test_external_link_is_created_then_skipped(self) -> None:
        self.register("cad-tool", self.make_external("cad-tool"))
        first, _ = self.run_linker("--skill", "cad-tool")
        self.assertTrue(all(a.outcome == "linked" for a in first), msg=first)
        second, code = self.run_linker("--skill", "cad-tool")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertTrue(all(a.outcome == "skipped" for a in second), msg=second)
        for directory in (".agents/skills", ".claude/skills"):
            self.assertTrue((self.project / directory / "cad-tool" / "SKILL.md").is_file())

    def test_a_broken_link_is_repointed(self) -> None:
        gone = self.root / "deleted-location"
        gone.mkdir()
        link = self.project / ".agents" / "skills" / "exam-prep"
        lps.create_link(link, gone)
        gone.rmdir()
        self.assertFalse(link.exists())

        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "codex")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertEqual(actions[0].outcome, "replaced")
        self.assertIn("broken", actions[0].detail)
        self.assertTrue((link / "SKILL.md").is_file())

    def test_links_resolve_to_the_canonical_skill(self) -> None:
        self.run_linker("--skill", "exam-prep")
        for directory in (".agents/skills", ".claude/skills"):
            with self.subTest(directory=directory):
                link = self.project / directory / "exam-prep"
                self.assertTrue(lps.is_link(link))
                self.assertTrue((link / "SKILL.md").is_file())

    def test_a_stale_link_is_repointed_and_reported_as_replaced(self) -> None:
        elsewhere = self.root / "old-location"
        elsewhere.mkdir()
        link = self.project / ".claude" / "skills" / "exam-prep"
        link.parent.mkdir(parents=True)
        lps.create_link(link, elsewhere)

        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "claude")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertEqual(actions[0].outcome, "replaced")
        self.assertTrue((link / "SKILL.md").is_file())

    def test_gitignore_is_updated_once(self) -> None:
        self.run_linker("--skill", "exam-prep", "--gitignore")
        first = (self.project / ".gitignore").read_text(encoding="utf-8")
        self.run_linker("--skill", "exam-prep", "--gitignore")
        self.assertEqual((self.project / ".gitignore").read_text(encoding="utf-8"), first)
        self.assertIn(".claude/skills", first)
        self.assertIn(".agents/skills", first)


@requires_links
class TestNonDestructive(LinkerCase):
    """Real content must never be removed."""

    def test_a_real_directory_is_rejected_not_deleted(self) -> None:
        existing = self.project / ".claude" / "skills" / "exam-prep"
        existing.mkdir(parents=True)
        (existing / "my-notes.md").write_text("local work", encoding="utf-8")

        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "claude")
        self.assertEqual(code, lps.EXIT_REJECTED)
        self.assertEqual(actions[0].outcome, "rejected")
        self.assertEqual((existing / "my-notes.md").read_text(encoding="utf-8"), "local work")

    def test_a_real_directory_blocks_an_external_skill_too(self) -> None:
        self.register("cad-tool", self.make_external("cad-tool"))
        existing = self.project / ".agents" / "skills" / "cad-tool"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("vendored copy", encoding="utf-8")

        actions, code = self.run_linker("--skill", "cad-tool", "--agents", "codex")
        self.assertEqual(code, lps.EXIT_REJECTED)
        self.assertEqual(actions[0].outcome, "rejected")
        self.assertEqual((existing / "SKILL.md").read_text(encoding="utf-8"), "vendored copy")

    def test_a_real_file_in_the_way_is_rejected(self) -> None:
        target = self.project / ".agents" / "skills" / "exam-prep"
        target.parent.mkdir(parents=True)
        target.write_text("not a directory", encoding="utf-8")

        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "codex")
        self.assertEqual(code, lps.EXIT_REJECTED)
        self.assertTrue(target.is_file())

    def test_removing_a_link_leaves_its_target_intact(self) -> None:
        target = self.root / "canonical"
        target.mkdir()
        (target / "keep.md").write_text("important", encoding="utf-8")
        link = self.root / "pointer"
        lps.create_link(link, target)

        lps.remove_link(link)

        self.assertFalse(link.exists())
        self.assertTrue((target / "keep.md").is_file())


@requires_links
class TestLegacyLayout(LinkerCase):
    """The old whole-directory junction must be detected, not written into."""

    def make_legacy(self) -> Path:
        """Create the legacy layout: .claude/skills is itself a link."""
        central = self.root / "central-project-skills"
        central.mkdir()
        legacy = self.project / ".claude" / "skills"
        legacy.parent.mkdir(parents=True)
        lps.create_link(legacy, central)
        return central

    def test_legacy_layout_is_rejected_without_migrate(self) -> None:
        central = self.make_legacy()
        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "claude")
        self.assertEqual(code, lps.EXIT_REJECTED)
        self.assertEqual(actions[0].outcome, "rejected")
        self.assertIn("--migrate", actions[0].detail)
        # Nothing was written into the central repository through the junction.
        self.assertEqual(list(central.iterdir()), [])

    def test_codex_directory_is_still_wired_despite_the_legacy_claude_layout(self) -> None:
        self.make_legacy()
        actions, _ = self.run_linker("--skill", "exam-prep")
        codex = [a for a in actions if ".agents" in a.link]
        self.assertEqual(len(codex), 1)
        self.assertEqual(codex[0].outcome, "linked")

    def test_migrate_converts_to_a_real_directory_without_losing_content(self) -> None:
        central = self.make_legacy()
        (central / "pipeline").mkdir()
        (central / "pipeline" / "SKILL.md").write_text(
            "---\nname: pipeline\n---\n", encoding="utf-8"
        )

        actions, code = self.run_linker("--skill", "exam-prep", "--agents", "claude", "--migrate")
        self.assertEqual(code, lps.EXIT_OK)
        self.assertEqual(actions[0].outcome, "replaced")

        legacy = self.project / ".claude" / "skills"
        self.assertFalse(lps.is_link(legacy))
        self.assertTrue(legacy.is_dir())
        self.assertTrue((legacy / "exam-prep" / "SKILL.md").is_file())
        # The central content the junction pointed at is untouched.
        self.assertTrue((central / "pipeline" / "SKILL.md").is_file())

    def test_migrate_dry_run_changes_nothing(self) -> None:
        self.make_legacy()
        actions, _ = self.run_linker(
            "--skill", "exam-prep", "--agents", "claude", "--migrate", "--dry-run"
        )
        self.assertEqual(actions[0].outcome, "would-replace")
        self.assertTrue(lps.is_link(self.project / ".claude" / "skills"))


class TestLinkDetection(LinkerCase):
    """is_link must not confuse a real directory with a link."""

    def test_real_directory_is_not_a_link(self) -> None:
        directory = self.project / "plain"
        directory.mkdir()
        self.assertFalse(lps.is_link(directory))

    def test_missing_path_is_not_a_link(self) -> None:
        self.assertFalse(lps.is_link(self.project / "absent"))

    @requires_links
    def test_created_link_is_detected(self) -> None:
        target = self.root / "t"
        target.mkdir()
        link = self.root / "l"
        lps.create_link(link, target)
        self.assertTrue(lps.is_link(link))


if __name__ == "__main__":
    unittest.main()
