"""Legacy adoption starts from the existing documentation (SMD-REQ-030)."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from specmd import hooks, workflow
from specmd.cli import main
from specmd.demo import create_demo

REPOSITORY = Path(__file__).resolve().parents[1]
COVERED = "## LEG-REQ-002 — Covered\n\n```gherkin\nFeature: B\n  Scenario: Covered\n    Given a step\n```\n"
DISCOUNT = """
## CART-REQ-003 — Discount

```gherkin
Feature: Discount

  Scenario: Discount above 1000 cents
    Given an empty cart
    When I add items of 600 and 500 cents
    Then the total should be 990 cents
```
"""


class AdoptionListTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-adopt-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for path, content in {
            "README.md": "# Project\n",
            "docs/setup.md": "# Setup\n",
            "docs/team.md": "# Team notes\n",
            "docs/refunds.md": "# Refunds\n\nPayments can be refunded within 7 days.\n",
            "docs/billing.md": "## LEG-REQ-001 — No scenario\n\nText.\n\n" + COVERED,
            "docs/ready.md": "## LEG-REQ-003 — Ready\n\n```gherkin\nFeature: C\n  Scenario: Ready\n    Given a step\n```\n",
            ".specmdignore": "docs/team.md\n",
        }.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def adopt(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["adopt", "--root", str(self.root)])
        return code, json.loads(output.getvalue())

    def test_lists_every_document_without_scenarios_in_path_order(self):  # SMD-SCN-130
        code, result = self.adopt()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "adoption")
        self.assertEqual([item["path"] for item in result["pending"]],
                         ["docs/billing.md", "docs/refunds.md", "docs/setup.md"])
        self.assertEqual(result["pending"][0]["requirements_without_scenarios"], ["LEG-REQ-001"])
        self.assertEqual((result["documents"], result["documented"]), (4, 2))

    def test_documents_the_developer_ignores_leave_the_list(self):  # SMD-SCN-131
        (self.root / ".specmdignore").write_text("docs/team.md\ndocs/setup.md\n", encoding="utf-8")
        self.assertNotIn("docs/setup.md", [item["path"] for item in self.adopt()[1]["pending"]])

    def test_the_command_guides_one_document_at_a_time(self):  # SMD-SCN-132
        text = (REPOSITORY / "commands/adopt.md").read_text(encoding="utf-8")
        for expected in ("specmd_cli.py\" adopt", "Handle one document at a time", "continue only after their confirmation",
                         "Write exactly the ones they name into `.specmdignore`", "Do not fix it on your own",
                         "Tagging scenarios `@wip` is the developer's decision"):
            self.assertIn(expected, text)


class ModuleCoreTests(unittest.TestCase):
    def test_new_functions_do_not_change_the_module_level_but_constants_do(self):
        from specmd.diagnosis import _module_core

        base = _module_core(b"LIMIT = 10\n\ndef allowed(days):\n    return days <= LIMIT\n")
        with_function = _module_core(b"LIMIT = 10\n\ndef allowed(days):\n    return days <= LIMIT\n\n"
                                     b"def other():\n    return 1\n")
        with_constant = _module_core(b"LIMIT = 7\n\ndef allowed(days):\n    return days <= LIMIT\n")
        self.assertEqual(base, with_function)
        self.assertNotEqual(base, with_constant)


class DivergenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-divergence-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        self.commit()
        environment = patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)

    def commit(self):
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t"]
        if not (self.root / ".git").exists():
            subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "base"], check=True)

    def hook(self, event):
        return hooks.handle_hook({"hook_event_name": event})

    def test_new_scenario_contradicting_existing_code_suggests_asking_the_dev(self):  # SMD-SCN-133
        self.assertTrue(workflow.run_project(self.root)["run"]["passed"])
        with (self.root / "docs/cart.md").open("a", encoding="utf-8") as stream:
            stream.write(DISCOUNT)
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        (self.root / "app.py").write_text((self.root / "app.py").read_text() + "\n# reviewed\n")
        reason = self.hook("Stop")["reason"]
        self.assertIn('1 scenario never passed ("Discount above 1000 cents")', reason)
        self.assertIn("this is a divergence between documentation and code: ask the developer which one holds "
                      "before changing either", reason)

    def test_regression_in_a_scenario_that_passed_has_no_divergence_hint(self):
        self.assertTrue(workflow.run_project(self.root)["run"]["passed"])
        app = self.root / "app.py"
        app.write_text(app.read_text().replace("sum(self.prices)", "sum(self.prices) + 1"))
        run = workflow.run_project(self.root)["run"]
        self.assertEqual(run["divergent"], [])
        self.assertNotIn("divergence", hooks._format_failures(run))

    @unittest.skipUnless(sys.version_info >= (3, 12), "per-scenario coverage requires Python 3.12+")
    def test_existing_scenario_broken_by_the_agent_is_not_divergence(self):  # SMD-SCN-138
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        app = self.root / "app.py"
        app.write_text(app.read_text().replace("return sum(self.prices)",
                                               "return sum(self.prices) + (1 if self.prices else 0)"))
        reason = self.hook("Stop")["reason"]
        self.assertNotIn("divergence", reason)
        self.assertIn('1 scenario that already existed broke with the code change ("Add two items"). '
                      "If the developer confirmed the new rule, update the scenario; otherwise, fix the code.", reason)
        self.assertNotIn("confirm with the developer before changing it", reason)

    @unittest.skipUnless(sys.version_info >= (3, 12), "per-scenario coverage requires Python 3.12+")
    def test_legacy_scenario_whose_code_the_agent_did_not_touch_is_divergence(self):  # SMD-SCN-133
        app = self.root / "app.py"
        app.write_text(app.read_text().replace("return sum(self.prices)", "return sum(self.prices) * 2"))
        self.commit()  # Legacy code that already disagrees with the documentation.
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        app.write_text(app.read_text() + "\n\ndef new_function():\n    return 1\n")
        reason = self.hook("Stop")["reason"]
        self.assertIn('1 scenario never passed ("Add two items")', reason)
        self.assertNotIn("broke with the code change", reason)


if __name__ == "__main__":
    unittest.main()
