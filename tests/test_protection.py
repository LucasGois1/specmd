"""Confirmed scenarios are protected and ignored documents that gain rules are reported."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from specmd import hooks
from specmd.demo import create_demo

SECOND_REQUIREMENT = """## CART-REQ-002 — Empty cart

A cart without items must have a total of zero cents.

```gherkin
# language: en
Feature: Empty cart

  Scenario: Check an empty cart
    Given an empty cart
    When I check the cart total
    Then the total should be 0 cents
```
"""


class HookCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-protection-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        environment = patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")

    def hook(self, event, **extra):
        return hooks.handle_hook({"hook_event_name": event, **extra})

    def edit(self, path, old, new):
        target = self.root / path
        text = target.read_text()
        self.assertIn(old, text)
        target.write_text(text.replace(old, new))

    def after_edit(self, path):
        reply = self.hook("PostToolUse", tool_name="Edit", tool_input={"file_path": str(self.root / path)})
        return reply.get("hookSpecificOutput", {}).get("additionalContext", "")


class ProtectedScenarioTests(HookCase):
    def test_changed_expectation_reaches_the_agent_and_the_developer(self):  # SMD-SCN-123
        self.edit("docs/cart.md", "Then the total should be 500 cents", "Then the total should be 510 cents")
        line = 'docs/cart.md:14 "Add two items" — Then the total should be 500 cents → Then the total should be 510 cents'
        self.assertIn(line, self.after_edit("docs/cart.md"))
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 5)")
        reply = self.hook("Stop")
        self.assertNotIn("decision", reply)
        self.assertIn("scenarios changed in this response", reply["systemMessage"])
        self.assertIn(line, reply["systemMessage"])
        self.assertIn("2 scenarios passing", reply["systemMessage"])

    def test_only_the_changed_steps_are_shown(self):
        self.edit("docs/cart.md", "items of 200 and 300 cents\n    Then the total should be 500",
                  "items of 200 and 310 cents\n    Then the total should be 510")
        context = self.after_edit("docs/cart.md")
        self.assertIn('"Add two items" — Then the total should be 500 cents → Then the total should be 510 cents; '
                      "When I add items of 200 and 300 cents → When I add items of 200 and 310 cents",
                      context)
        self.assertNotIn("Given an empty cart", context)

    def test_removed_scenario_wip_tag_and_removed_requirement(self):  # SMD-SCN-124
        self.edit("docs/cart.md", SECOND_REQUIREMENT, "")
        self.edit("docs/cart.md", "  Scenario: Add two items", "  @wip\n  Scenario: Add two items")
        context = self.after_edit("docs/cart.md")
        self.assertIn('"Check an empty cart" — removed or renamed', context)
        self.assertIn('"Add two items" — tagged @wip', context)
        self.assertIn("requirement CART-REQ-002 (docs/cart.md:20) — removed", context)
        self.assertIn("restore the scenarios", context)
        message = self.hook("Stop")["systemMessage"]
        for text in ("removed or renamed", "tagged @wip", "requirement CART-REQ-002"):
            self.assertIn(text, message)

    def test_expectation_adjusted_to_failing_code_comes_back_once(self):  # SMD-SCN-125
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 5)")
        self.assertEqual(self.hook("Stop")["decision"], "block")  # 510 instead of 500
        self.edit("docs/cart.md", "Then the total should be 500 cents", "Then the total should be 510 cents")
        reply = self.hook("Stop", stop_hook_active=True)
        self.assertEqual(reply["decision"], "block")
        self.assertIn("the expected value of scenarios that were failing changed together with the code", reply["reason"])
        self.assertIn("Then the total should be 500 cents → Then the total should be 510 cents", reply["reason"])
        self.assertIn("Observed total 510; expected 500)", reply["reason"])
        self.assertIn("restore the scenario", reply["reason"])
        allowed = self.hook("Stop", stop_hook_active=True)
        self.assertNotIn("decision", allowed)
        self.assertIn("scenarios changed in this response", allowed["systemMessage"])

    def test_change_to_a_passing_scenario_is_only_reported(self):  # SMD-SCN-126
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertIn("2 scenarios passing", self.hook("Stop")["systemMessage"])
        self.hook("UserPromptSubmit")
        self.edit("docs/cart.md", "Then the total should be 500 cents", "Then the total should be 510 cents")
        self.edit("app.py", "price_cents + 0", "price_cents + 5")
        reply = self.hook("Stop")
        self.assertNotIn("decision", reply)
        self.assertIn("500 cents → Then the total should be 510 cents", reply["systemMessage"])

    def test_ignoring_a_document_reports_its_scenarios_and_rules(self):
        (self.root / ".specmdignore").write_text("docs/cart.md\n")
        context = self.after_edit(".specmdignore")
        self.assertIn('"Add two items" — removed or renamed', context)
        self.assertIn("requirement CART-REQ-001 (docs/cart.md:6) — removed", context)
        self.assertIn("docs/cart.md is in .specmdignore, but now declares CART-REQ-001, CART-REQ-002, "
                      "a Gherkin block", context)

    def test_new_developer_message_resets_the_baseline(self):
        self.edit("docs/cart.md", "Then the total should be 500 cents", "Then the total should be 510 cents")
        self.hook("UserPromptSubmit")
        self.assertNotIn("scenarios from the developer's last message", self.after_edit("docs/cart.md"))


class IgnoredDocumentTests(HookCase):
    def test_requirement_written_in_an_ignored_document_is_reported(self):  # SMD-SCN-127
        (self.root / ".specmdignore").write_text("docs/setup.md\n")
        (self.root / "docs/setup.md").write_text("# Setup\n\nInstall the dependencies.\n")
        self.after_edit("docs/setup.md")
        self.edit("docs/setup.md", "Install", "## PAY-REQ-009 — Retries\n\nInstall")
        context = self.after_edit("docs/setup.md")
        self.assertIn("docs/setup.md is in .specmdignore, but now declares PAY-REQ-009", context)
        self.assertIn("Move the rule to a behavior document or take the file out of .specmdignore "
                      "(or use !docs/setup.md). When in doubt, ask the developer.", context)
        self.edit("docs/setup.md", "Install", "```gherkin\nFeature: X\n```\n\nInstall")
        self.assertIn("now declares a Gherkin block", self.after_edit("docs/setup.md"))

    def test_existing_example_in_an_ignored_readme_is_not_reported(self):  # SMD-SCN-128
        (self.root / "README.md").write_text("# Demo\n\n```gherkin\nFeature: Example\n```\n")
        self.hook("SessionStart")
        self.edit("README.md", "# Demo", "# Cart demo")
        self.assertEqual(self.after_edit("README.md"), "")
        self.edit("README.md", "# Cart demo", "# Cart demo\n\n## Feature: Another")
        self.assertIn("README.md is ignored by default by SpecMD, but now declares Gherkin headings (MDG)",
                      self.after_edit("README.md"))

    def test_the_warning_does_not_block_the_end_of_the_turn(self):  # SMD-SCN-129
        (self.root / ".specmdignore").write_text("docs/setup.md\n")
        (self.root / "docs/setup.md").write_text("# Setup\n")
        self.after_edit("docs/setup.md")
        (self.root / "docs/setup.md").write_text("# Setup\n\n## PAY-REQ-009 — Retries\n")
        self.assertIn("PAY-REQ-009", self.after_edit("docs/setup.md"))
        self.assertNotIn("decision", self.hook("Stop"))


if __name__ == "__main__":
    unittest.main()
