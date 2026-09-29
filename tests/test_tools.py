"""Exercise the actual CLI against disposable packages and destinations."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
MAIN_NAME = "i2e-fable-opus"
LEAD = "i2e-fable-lead"
IMPLEMENTER = "i2e-opus-implementer"


class PackageToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "package"
        self.dest = self.base / "claude"
        self.skill = self.dest / "skills" / MAIN_NAME
        self.agents = self.dest / "agents" / MAIN_NAME
        shutil.copytree(SCRIPTS, self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.main = self.repo / "skills" / MAIN_NAME
        self.write(self.main / "SKILL.md", """---
name: i2e-fable-opus
description: Coordinate issue implementation with explicit model roles.
---
# Workflow

Follow the [role instructions](references/roles.md) and [task form](templates/task.md).
""")
        self.write_agent(LEAD, "claude-fable-5-1")
        self.write_agent(IMPLEMENTER, "claude-opus-5-5")
        self.write(self.main / "references" / "roles.md", "# Roles\n\nCoordinate work using the approved role contract.\n")
        self.write(self.main / "templates" / "task.md", "# Task\n\nRecord the concrete goal and acceptance evidence.\n")
        self.environment = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.base / "default-claude"))
        self.environment.pop("PYTHONDONTWRITEBYTECODE", None)

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_agent(self, name: str, model: str, effort: str = "max") -> None:
        self.write(self.main / "agents" / f"{name}.md", f"""---
name: {name}
description: Perform one role in the issue workflow.
model: {model}
effort: {effort}
---
Follow the delegated contract.
""")

    def cli(self, script: str, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([sys.executable, str(self.repo / "scripts" / script), *args],
                                cwd=self.base, env=self.environment, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        return self.cli("install.py", "--dest", str(self.dest), *args, success=success)

    @staticmethod
    def snapshot(root: Path) -> dict[str, tuple[bytes | None, int, int]]:
        """Capture bytes and mtimes, including directories, to detect writes."""
        return {str(path.relative_to(root)): (path.read_bytes() if path.is_file() else None,
                                             path.stat().st_mtime_ns, path.stat().st_mode)
                for path in root.rglob("*")}

    def test_valid_package_and_cwd_independent_install(self) -> None:
        self.cli("validate.py")
        self.install()
        self.assertEqual((self.skill / "SKILL.md").read_bytes(),
                         (self.main / "SKILL.md").read_bytes())
        for name in (LEAD, IMPLEMENTER):
            self.assertEqual((self.agents / f"{name}.md").read_bytes(),
                             (self.main / "agents" / f"{name}.md").read_bytes())
        self.assertEqual(sorted(path.name for path in self.dest.iterdir()), ["agents", "skills"])
        self.assertEqual([path.name for path in (self.dest / "skills").iterdir()], [MAIN_NAME])
        self.assertEqual([path.name for path in (self.dest / "agents").iterdir()], [MAIN_NAME])

    def test_default_destination_respects_claude_config_dir(self) -> None:
        self.cli("install.py")
        default = self.base / "default-claude"
        self.assertTrue((default / "skills" / MAIN_NAME / "SKILL.md").is_file())
        self.assertTrue((default / "agents" / MAIN_NAME / f"{LEAD}.md").is_file())
        self.assertFalse(self.dest.exists())

    def test_identical_install_is_noop(self) -> None:
        self.install()
        before = self.snapshot(self.base)
        result = self.install()
        self.assertIn("unchanged:", result.stdout)
        self.assertEqual(before, self.snapshot(self.base))

    def test_conflict_does_not_overwrite_or_install_agents(self) -> None:
        self.write(self.skill / "private.txt", "Preserve this installed skill.\n")
        before = self.snapshot(self.base)
        result = self.install(success=False)
        self.assertIn("--update", result.stderr)
        self.assertEqual(before, self.snapshot(self.base))

    def test_update_backs_up_exact_trees_and_preserves_unrelated_entries(self) -> None:
        self.install()
        self.write(self.skill / "private.txt", "Original local customization.\n")
        self.write(self.agents / "extra.md", "Original agent customization.\n")
        unrelated_skill = self.dest / "skills" / "unrelated" / "SKILL.md"
        unrelated_agent = self.dest / "agents" / "unrelated.md"
        self.write(unrelated_skill, "Unrelated skill.\n")
        self.write(unrelated_agent, "Unrelated agent.\n")
        previous_skill = self.snapshot(self.skill)
        previous_agents = self.snapshot(self.agents)
        previous_unrelated = (self.snapshot(unrelated_skill.parent), unrelated_agent.read_bytes())
        result = self.install("--update")
        backup_root = self.dest / f".{MAIN_NAME}-backups"
        backups = list(backup_root.iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(previous_skill, self.snapshot(backups[0] / "skills" / MAIN_NAME))
        self.assertEqual(previous_agents, self.snapshot(backups[0] / "agents" / MAIN_NAME))
        self.assertEqual(previous_unrelated,
                         (self.snapshot(unrelated_skill.parent), unrelated_agent.read_bytes()))
        self.assertIn(str(backups[0] / "skills" / MAIN_NAME), result.stdout)
        self.assertFalse((self.skill / "private.txt").exists())
        self.assertFalse((self.agents / "extra.md").exists())
        self.install("--check")

    def test_failed_second_replacement_restores_both_previous_bundles(self) -> None:
        self.install()
        self.write(self.skill / "private.txt", "Original skill.\n")
        self.write(self.agents / "private.txt", "Original agents.\n")
        before_skill = self.snapshot(self.skill)
        before_agents = self.snapshot(self.agents)
        # Simulate a filesystem failure after the first replacement succeeded.
        runner = f"""
import runpy
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, {str(self.repo / 'scripts')!r})
original_rename = Path.rename
def fail_agents(source, target):
    if source.parent.name.startswith('.i2e-install-') and source.name == 'agents':
        raise OSError('Simulated second replacement failure')
    return original_rename(source, target)
with patch.object(Path, 'rename', fail_agents):
    runpy.run_path({str(self.repo / 'scripts' / 'install.py')!r}, run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-c", runner, "--dest", str(self.dest), "--update"],
                                cwd=self.base, env=self.environment, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Simulated second replacement failure", result.stderr)
        self.assertEqual(before_skill, self.snapshot(self.skill))
        self.assertEqual(before_agents, self.snapshot(self.agents))
        self.assertEqual([path.name for path in (self.dest / "skills").iterdir()], [MAIN_NAME])
        self.assertEqual([path.name for path in (self.dest / "agents").iterdir()], [MAIN_NAME])

    def test_dry_run_never_creates_destination(self) -> None:
        before = self.snapshot(self.base)
        result = self.install("--dry-run")
        self.assertIn("Would install:", result.stdout)
        self.assertEqual(before, self.snapshot(self.base))

    def test_update_dry_run_never_creates_backups_or_changes_target(self) -> None:
        self.write(self.skill / "local.txt", "Keep me.\n")
        before = self.snapshot(self.base)
        result = self.install("--update", "--dry-run")
        self.assertIn("Would update:", result.stdout)
        self.assertIn("Would preserve exact previous tree", result.stdout)
        self.assertEqual(before, self.snapshot(self.base))

    def test_check_missing_is_read_only(self) -> None:
        before = self.snapshot(self.base)
        result = self.install("--check", success=False)
        self.assertIn("MISSING:", result.stdout)
        self.assertEqual(before, self.snapshot(self.base))

    def test_check_identical_and_different_are_read_only(self) -> None:
        self.install()
        before = self.snapshot(self.base)
        self.install("--check")
        self.assertEqual(before, self.snapshot(self.base))
        self.write(self.agents / f"{LEAD}.md", "Local change.\n")
        before = self.snapshot(self.base)
        result = self.install("--check", success=False)
        self.assertIn(f"OK: {self.skill}", result.stdout)
        self.assertIn(f"DIFFERS: {self.agents}", result.stdout)
        self.assertEqual(before, self.snapshot(self.base))

    def test_symlink_source_entry_is_rejected(self) -> None:
        external = self.base / "external.txt"
        self.write(external, "External content.\n")
        (self.main / "references" / "external.md").symlink_to(external)
        self.install(success=False)
        self.assertFalse(self.dest.exists())

    def test_symlink_source_directory_is_rejected(self) -> None:
        original = self.repo / "original-main"
        self.main.rename(original)
        self.main.symlink_to(original, target_is_directory=True)
        self.install(success=False)
        self.assertFalse(self.dest.exists())

    def test_symlink_target_and_nested_entry_are_rejected(self) -> None:
        outside = self.base / "outside"
        self.write(outside / "keep.txt", "Original.\n")
        self.skill.parent.mkdir(parents=True)
        self.skill.symlink_to(outside, target_is_directory=True)
        self.install("--update", success=False)
        self.assertEqual((outside / "keep.txt").read_text(), "Original.\n")
        self.skill.unlink()
        self.skill.mkdir()
        (self.skill / "linked.txt").symlink_to(outside / "keep.txt")
        self.install("--update", success=False)
        self.assertTrue((self.skill / "linked.txt").is_symlink())

    def test_symlink_skill_and_agent_directories_are_rejected(self) -> None:
        for kind in ("skills", "agents"):
            with self.subTest(kind=kind):
                outside = self.base / f"outside-{kind}"
                outside.mkdir()
                self.dest.mkdir(exist_ok=True)
                (self.dest / kind).symlink_to(outside, target_is_directory=True)
                self.install(success=False)
                self.assertEqual(list(outside.iterdir()), [])
                self.assertEqual([path.name for path in self.dest.iterdir()], [kind])
                (self.dest / kind).unlink()

    def test_invalid_source_does_not_touch_existing_install(self) -> None:
        self.install()
        (self.main / "agents" / f"{IMPLEMENTER}.md").unlink()
        before = self.snapshot(self.base)
        self.install("--update", success=False)
        self.assertEqual(before, self.snapshot(self.base))

    def test_missing_source_directory_is_rejected(self) -> None:
        self.main.rename(self.repo / "hidden-main")
        self.install(success=False)
        self.assertFalse(self.dest.exists())

    def test_agent_definitions_must_pin_model_and_max_effort(self) -> None:
        for model, effort in (("fable", "max"), ("claude-fable-5-1", "high"), ("inherit", "max")):
            with self.subTest(model=model, effort=effort):
                self.write_agent(LEAD, model, effort)
                result = self.cli("validate.py", success=False)
                self.assertIn(f"Subagent {LEAD} must pin", result.stderr)
        self.write_agent(LEAD, "claude-fable-5-1")
        self.cli("validate.py")
        self.write_agent(IMPLEMENTER, "claude-fable-5-1")
        self.cli("validate.py", success=False)

    def test_main_links_cannot_escape_bundle(self) -> None:
        self.write(self.repo / "README.md", "Outside bundle.\n")
        self.write(self.main / "references" / "roles.md", "[Outside](../../../README.md)\n")
        result = self.cli("validate.py", success=False)
        self.assertIn("escapes the bundle", result.stderr)

    def test_broken_relative_link_is_rejected(self) -> None:
        self.write(self.main / "references" / "roles.md", "[Missing](missing.md)\n")
        self.cli("validate.py", success=False)

    def test_absolute_and_file_links_are_rejected(self) -> None:
        for target in (str(self.main / "SKILL.md"), (self.main / "SKILL.md").as_uri()):
            with self.subTest(target=target):
                self.write(self.main / "references" / "roles.md", f"[Machine path]({target})\n")
                self.cli("validate.py", success=False)

    def test_reference_style_links_and_encoded_paths_are_checked(self) -> None:
        self.write(self.main / "references" / "extra notes.md", "Useful notes.\n")
        self.write(self.main / "references" / "roles.md", "[Notes][notes]\n\n[notes]: extra%20notes.md\n")
        self.cli("validate.py")
        self.write(self.main / "references" / "roles.md", "[Bad][bad]\n\n[bad]: %2e%2e/%2e%2e/elsewhere.md\n")
        self.cli("validate.py", success=False)

    def test_frontmatter_and_matching_names_are_required(self) -> None:
        self.write(self.main / "agents" / f"{LEAD}.md", "Follow the delegated contract.\n")
        self.cli("validate.py", success=False)
        self.write(self.main / "agents" / f"{LEAD}.md", "---\nname: i2e-other\ndescription: Lead.\n"
                   "model: claude-fable-5-1\neffort: max\n---\nFollow the delegated contract.\n")
        self.cli("validate.py", success=False)
        self.write_agent(LEAD, "claude-fable-5-1")
        self.write(self.main / "SKILL.md", "# No frontmatter\n")
        self.cli("validate.py", success=False)

    def test_block_strings_are_supported(self) -> None:
        self.write(self.main / "agents" / f"{LEAD}.md", """---
name: 'i2e-fable-lead'
description: >-
  Decide and review
  issue implementation.
model: "claude-fable-5-1"
effort: max
---
Follow the delegated contract.
""")
        self.cli("validate.py")

    def test_scaffolds_are_rejected(self) -> None:
        self.write(self.main / "references" / "roles.md", "TODO: fill this in.\n")
        self.cli("validate.py", success=False)

    def test_source_cannot_be_installation_target(self) -> None:
        before = self.snapshot(self.base)
        self.cli("install.py", "--dest", str(self.repo), "--update", success=False)
        self.assertEqual(before, self.snapshot(self.base))

    def test_checkout_and_ancestor_cannot_be_installation_targets(self) -> None:
        for nested_checkout in (False, True):
            with self.subTest(nested_checkout=nested_checkout):
                destination = self.base / ("ancestor-case" if nested_checkout else "checkout-case")
                target = destination / "skills" / MAIN_NAME
                checkout = target / "checkout" if nested_checkout else target
                shutil.copytree(self.repo, checkout)
                self.write(checkout / ".git" / "HEAD", "ref: refs/heads/main\n")
                self.write(destination / "skills" / "sibling-data" / "keep.txt", "Preserve sibling data.\n")
                if nested_checkout:
                    self.write(target / "other-project" / "keep.txt", "Preserve adjacent project.\n")
                before = self.snapshot(self.base)
                result = subprocess.run(
                    [sys.executable, str(checkout / "scripts" / "install.py"),
                     "--dest", str(destination), "--update"],
                    cwd=self.base, env=self.environment, text=True, capture_output=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("overlaps package source", result.stderr)
                self.assertEqual(before, self.snapshot(self.base))
                self.assertTrue((checkout / "scripts" / "install.py").is_file())
                self.assertTrue((checkout / "skills" / MAIN_NAME / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
