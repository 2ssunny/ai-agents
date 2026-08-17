"""Behavioural tests for link-project-skills.

The linker touches real directories, so these tests care most about what it
refuses to do: never delete a real directory, never write inside a legacy
whole-directory junction, never silently change what a link points at without
saying so.

Symlink creation can be unavailable (Windows without Developer Mode, some
sandboxes); those tests skip rather than fail, and the mapping tests — which need
no filesystem links — always run.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_DIR.parents[2]
LINKER_DIR = REPO_ROOT / "skills" / "global" / "link-project-skills" / "scripts"
sys.path.insert(0, str(LINKER_DIR))

import link_project_skills as lps  # noqa: E402


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
        self.addCleanup(self._tmp.cleanup)

    def run_linker(self, *argv: str) -> tuple[list[lps.Action], int]:
        """Invoke the linker with the project pre-filled."""
        args = lps.build_parser().parse_args(["--project", str(self.project), *argv])
        return lps.run(args)

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
        source = (LINKER_DIR / "link_project_skills.py").read_text(encoding="utf-8")
        for fragment in ("C:\\Users", "/home/user/", "/Users/"):
            with self.subTest(fragment=fragment):
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
        self.assertEqual(caught.exception.code, 2)


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
