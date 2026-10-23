import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from specmd import state as hook_state
from specmd import workflow
from specmd.demo import create_demo


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-workflow-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "project"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def touch(self, relative, content="x\n"):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def test_fingerprint_changes_with_code_but_not_markdown_or_local_state(self):
        before = workflow.fingerprint_code(self.root)
        self.touch("docs/notes.md", "# Notas\n")
        self.touch(".specmd/local/state.json", "{}")
        self.touch(".claude/settings.local.json", "{}")
        self.assertEqual(workflow.fingerprint_code(self.root), before)
        self.touch("app.py", (self.root / "app.py").read_text() + "\n# mudança\n")
        self.assertNotEqual(workflow.fingerprint_code(self.root), before)

    def test_fingerprint_respects_gitignore(self):
        before = workflow.fingerprint_code(self.root)
        self.touch("build-output/artifact.bin")
        self.touch(".gitignore", (self.root / ".gitignore").read_text() + "build-output/\n")
        changed = workflow.fingerprint_code(self.root)
        self.assertNotEqual(changed, before)  # .gitignore itself is code-side
        self.touch("build-output/artifact.bin", "outro\n")
        self.assertEqual(workflow.fingerprint_code(self.root), changed)

    def test_fingerprint_without_git_walks_pruned_tree(self):
        (self.root / ".git").rename(self.root / ".git-off")
        before = workflow.fingerprint_code(self.root)
        self.touch("node_modules/lib.js")
        self.assertEqual(workflow.fingerprint_code(self.root), before)
        self.touch("src/lib.py")
        self.assertNotEqual(workflow.fingerprint_code(self.root), before)

    def test_run_records_state_and_check_reuses_it_until_code_changes(self):
        self.assertEqual(workflow.check_project(self.root)["status"], "ready")
        result = workflow.run_project(self.root)
        self.assertEqual(result["status"], "passing", result)
        self.assertEqual(result["run"]["expected"], 2)
        self.assertEqual(workflow.check_project(self.root)["status"], "passing")
        self.touch("app.py", (self.root / "app.py").read_text().replace("sum(self.prices)", "sum(self.prices) + 1"))
        checked = workflow.check_project(self.root)
        self.assertEqual(checked["status"], "ready")
        self.assertFalse(checked["run"]["current"])
        failing = workflow.run_project(self.root)
        self.assertEqual(failing["status"], "failing")
        self.assertEqual(len(failing["run"]["failures"]), 2)

    def test_artifacts_written_by_tests_do_not_make_the_run_stale(self):
        steps = self.root / "tests/steps/cart_steps.py"
        steps.write_text(steps.read_text() + "\nfrom pathlib import Path\nPath('artifact.log').write_text('x')\n")
        self.assertEqual(workflow.run_project(self.root)["status"], "passing")
        self.assertEqual(workflow.check_project(self.root)["status"], "passing")

    def test_documentation_gaps_skip_execution(self):
        self.touch("docs/new.md", "# Sem classificação\n")
        result = workflow.run_project(self.root)
        self.assertEqual(result["status"], "needs_scenarios")
        self.assertNotIn("last_run", hook_state.load(self.root))

    def test_state_is_atomic_and_lock_times_out(self):
        hook_state.update(self.root, lambda state: state.__setitem__("value", 1))
        self.assertEqual(json.loads((self.root / ".specmd/local/state.json").read_text())["value"], 1)
        with hook_state.locked(self.root):
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                with hook_state.locked(self.root, timeout=0.2):
                    pass
            self.assertLess(time.monotonic() - start, 2)

    def test_corrupt_state_is_ignored(self):
        self.touch(".specmd/local/state.json", "{not json")
        self.assertEqual(hook_state.load(self.root), {})
        self.assertEqual(workflow.check_project(self.root)["status"], "ready")

    def test_symlinked_local_state_is_refused(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (self.root / ".specmd").mkdir(exist_ok=True)
        os.symlink(outside, self.root / ".specmd/local")
        with self.assertRaises(ValueError):
            hook_state.save(self.root, {"x": 1})
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
