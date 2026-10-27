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

from specmd import hooks, messages
from specmd import state as hook_state
from specmd.demo import create_demo
from specmd.runner import default_runners

REPOSITORY = Path(__file__).resolve().parents[1]
GAP_DOC = """---
specmd:
  schema: 1
  id: SMD-DEMO-DOC-002
  kind: behavioral
---

# Coupons

## SMD-DEMO-REQ-003 — Discount coupon

A TEN coupon applies a 10% discount.
"""
SCENARIO = """
```gherkin
Feature: Coupon

  @SMD-DEMO-REQ-003 @SMD-DEMO-SCN-003
  Scenario: TEN coupon
    Given an empty cart
    When I add items of 500 and 500 cents
    Then the total should be 1000 cents
```
"""


class HookLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-hooks-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        environment = patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)

    def hook(self, event, **extra):
        return hooks.handle_hook({"hook_event_name": event, "cwd": str(self.root), **extra})

    def edit_app(self, old, new):
        app = self.root / "app.py"
        app.write_text(app.read_text().replace(old, new))

    def test_project_without_configuration_is_ignored(self):
        (self.root / "specmd.toml").unlink()
        for event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"):
            self.assertEqual(self.hook(event, tool_name="Edit"), {})

    def test_hook_log_records_each_reply_when_asked(self):
        log = self.root.parent / "hooks.jsonl"
        payload = json.dumps({"hook_event_name": "SessionStart"})
        with patch.dict(os.environ, {"SPECMD_HOOK_LOG": str(log)}), patch("sys.stdin", io.StringIO(payload)), \
                contextlib.redirect_stdout(io.StringIO()):
            hooks.run_hook()
        entry = json.loads(log.read_text().splitlines()[0])
        self.assertEqual(entry["event"], "SessionStart")
        self.assertIn("SpecMD is active", entry["reply"]["hookSpecificOutput"]["additionalContext"])

    def test_codex_project_config_activates_without_specmd_toml(self):  # SMD-SCN-140
        (self.root / "specmd.toml").unlink()
        self.assertEqual(self.hook("SessionStart"), {})
        (self.root / ".codex").mkdir()
        (self.root / ".codex/config.toml").write_text('[plugins."specmd@specmd"]\nenabled = true\n')
        self.assertIn("SpecMD is active", self.hook("SessionStart")["hookSpecificOutput"]["additionalContext"])
        (self.root / ".codex/config.toml").write_text('[plugins."specmd@specmd"]\nenabled = false\n')
        self.assertEqual(self.hook("SessionStart"), {})

    def test_messages_follow_the_project_language(self):
        self.addCleanup(messages.use, "en")
        config = self.root / "specmd.toml"
        config.write_text('language = "pt"\n' + config.read_text())
        context = self.hook("SessionStart")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("SpecMD ativo neste repositório.", context)
        self.assertIn("mostre-os ao dev e peça confirmação", context)
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 1")
        self.assertIn("2 de 2 cenários da documentação não passaram.", self.hook("Stop")["reason"])

    def test_read_only_tools_return_without_touching_the_project(self):
        with patch.object(hooks, "find_root", side_effect=AssertionError("disk access")):
            self.assertEqual(hooks.handle_hook({"hook_event_name": "PostToolUse", "tool_name": "Read"}), {})

    def test_edits_outside_the_documentation_skip_the_analysis(self):
        def post(tool, path):
            return hooks.handle_hook({"hook_event_name": "PostToolUse", "tool_name": tool,
                                      "tool_input": {"file_path": path}})

        with patch.object(hooks, "find_root", side_effect=AssertionError("disk access")):
            self.assertEqual(post("Edit", str(self.root / "app.py")), {})
            self.assertEqual(post("Write", "tests/steps/cart_steps.py"), {})
        for tool, path in (("Write", "docs/new.MD"), ("Edit", ".specmdignore"), ("Edit", "specmd.toml"),
                           ("Bash", "app.py"), ("Edit", None)):
            with self.subTest(tool=tool, path=path), \
                    patch.object(hooks, "find_root", return_value=None) as find_root:
                post(tool, path)
                find_root.assert_called_once()

    def test_session_start_summarizes_documentation_and_conventions(self):
        reply = self.hook("SessionStart")
        context = reply["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1 (2 scenarios)", context)
        self.assertIn("show them to the developer and ask for confirmation", context)
        self.assertIn("tagging @wip is the developer's decision", context)
        self.assertIn("If existing code contradicts the documentation, do not fix either one on your own", context)
        self.assertIn("scripts/specmd_cli.py", context)
        self.assertIn(f"run --root {self.root}", context)
        state = hook_state.load(self.root)
        self.assertIn("code_baseline", state)
        self.assertIn("docs/cart.md", state["spec_at_prompt"])

    def test_documentation_gap_is_reported_after_the_edit_and_once_at_stop(self):
        self.hook("SessionStart")
        (self.root / "docs/coupons.md").write_text(GAP_DOC)
        context = self.hook("PostToolUse", tool_name="Write")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("docs/coupons.md", context)
        self.assertIn("Document without Gherkin scenarios", context)
        self.assertIn("ask the developer", context)
        self.assertEqual(self.hook("PostToolUse", tool_name="Edit"), {})
        first = self.hook("Stop", stop_hook_active=False)
        self.assertEqual(first["decision"], "block")
        self.assertIn("SMD-DEMO-REQ-003", first["reason"])
        second = self.hook("Stop", stop_hook_active=True)
        self.assertNotIn("decision", second)
        self.assertNotIn("continue", second)

    def test_documentation_only_changes_wait_for_the_developer(self):
        self.hook("SessionStart")
        (self.root / "docs/coupons.md").write_text(GAP_DOC + SCENARIO)
        context = self.hook("PostToolUse", tool_name="Write")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ask for confirmation before implementing", context)
        reply = self.hook("Stop")
        self.assertIn("awaiting your confirmation", reply["systemMessage"])
        self.assertNotIn("last_run", hook_state.load(self.root))

    def test_code_change_verifies_even_scenarios_written_in_the_same_turn(self):
        # The agent proposed the scenarios in chat, the developer confirmed, and
        # the agent wrote them and the code in the following turn.
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        (self.root / "docs/coupons.md").write_text(GAP_DOC + SCENARIO)
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        reply = self.hook("Stop")
        self.assertIn("3 scenarios passing", reply["systemMessage"])
        self.assertIn("changed after the developer's last message", reply["systemMessage"])
        self.assertTrue(hook_state.load(self.root)["last_run"]["passed"])
        self.hook("UserPromptSubmit")
        self.assertEqual(self.hook("Stop"), {})

    def test_failing_scenario_written_with_the_code_is_fed_back_with_a_reminder(self):
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        (self.root / "docs/coupons.md").write_text(GAP_DOC + SCENARIO.replace("1000 cents\n```", "900 cents\n```"))
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        reply = self.hook("Stop")
        self.assertEqual(reply["decision"], "block")
        self.assertIn("Observed total 1000; expected 900", reply["reason"])
        self.assertIn("if they have not confirmed them yet", reply["reason"])

    def test_no_code_change_in_the_session_demands_no_execution(self):
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        self.assertEqual(self.hook("Stop"), {})
        self.assertNotIn("last_run", hook_state.load(self.root))

    def test_code_change_runs_scenarios_and_feeds_back_failures_until_green(self):
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 1")
        first = self.hook("Stop")
        self.assertEqual(first["decision"], "block")
        self.assertIn("2 of 2 documented scenarios", first["reason"])
        self.assertIn("Observed total 501; expected 500", first["reason"])
        repeated = self.hook("Stop", stop_hook_active=True)
        self.assertIn("still failing", repeated["systemMessage"])
        self.edit_app("return sum(self.prices) + 1", "return sum(self.prices)")
        fixed = self.hook("Stop", stop_hook_active=True)
        self.assertIn("2 scenarios passing", fixed["systemMessage"])
        self.assertEqual(self.hook("Stop"), {})

    def test_committing_after_a_green_run_does_not_run_again(self):
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        self.assertIn("2 scenarios passing", self.hook("Stop")["systemMessage"])
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "x"], check=True)
        with patch("specmd.workflow.run_project", side_effect=AssertionError("ran again")):
            self.assertEqual(self.hook("Stop"), {})

    @unittest.skipUnless(sys.version_info >= (3, 12), "per-scenario coverage requires Python 3.12+")
    def test_later_changes_run_only_the_affected_scenarios_and_say_so(self):
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        self.edit_app("self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertIn("2 scenarios passing", self.hook("Stop")["systemMessage"])
        self.edit_app("price_cents + 0", "price_cents + 1")
        failing = self.hook("Stop")
        self.assertEqual(failing["decision"], "block")
        self.assertIn("1 of 1 scenario affected by the change failed; 1 scenario does not run the changed code.",
                      failing["reason"])
        self.edit_app("price_cents + 1", "price_cents")
        fixed = self.hook("Stop", stop_hook_active=True)
        self.assertIn("1 scenario affected by the change, passing; 1 scenario does not run the changed code.",
                      fixed["systemMessage"])

    def test_undefined_steps_come_back_with_a_snippet(self):
        self.hook("SessionStart")
        (self.root / "docs/coupons.md").write_text(GAP_DOC + SCENARIO.replace(
            "    Then", '    And I apply the coupon "TEN"\n    Then'))
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        reply = self.hook("Stop")
        self.assertEqual(reply["decision"], "block")
        self.assertIn("Step without implementation", reply["reason"])
        self.assertIn("def step_impl(context)", reply["reason"])

    def test_steps_directory_is_found_without_runner_configuration(self):
        (self.root / "specmd.toml").write_text("")
        self.assertEqual(default_runners(self.root), [{"id": "python", "language": "python", "steps": "tests/steps"}])
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        self.assertIn("2 scenarios passing", self.hook("Stop")["systemMessage"])

    def test_block_cap_lets_the_agent_stop(self):
        for index in range(hooks.MAX_BLOCKS):
            self.assertEqual(hooks._block_once(self.root, f"sig-{index}", "reason", "summary")["decision"], "block")
        self.assertEqual(hooks._block_once(self.root, "sig-new", "reason", "summary"), {"systemMessage": "summary"})
        self.hook("UserPromptSubmit")
        self.assertEqual(hooks._block_once(self.root, "sig-new", "reason", "summary")["decision"], "block")

    def test_project_root_from_environment_not_payload(self):
        self.assertEqual(hooks.find_root(), self.root)
        os.environ.pop("CLAUDE_PROJECT_DIR")
        previous = os.getcwd()
        os.chdir(self.root / "docs")
        self.addCleanup(os.chdir, previous)
        self.assertEqual(hooks.find_root(), self.root)
        neutral = tempfile.TemporaryDirectory()
        self.addCleanup(neutral.cleanup)
        os.chdir(neutral.name)
        self.assertEqual(hooks.handle_hook({"hook_event_name": "SessionStart", "cwd": str(self.root)}), {})

    def test_project_scope_installation_activates_without_configuration(self):
        (self.root / "specmd.toml").unlink()
        self.assertIsNone(hooks.find_root())
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text(json.dumps({"enabledPlugins": {"specmd@specmd": True}}))
        self.assertEqual(hooks.find_root(), self.root)
        self.assertIn("SpecMD is active", self.hook("SessionStart")["hookSpecificOutput"]["additionalContext"])
        (self.root / ".claude/settings.local.json").write_text(json.dumps({"enabledPlugins": {"specmd@specmd": False}}))
        self.assertIsNone(hooks.find_root())
        (self.root / ".claude/settings.local.json").write_text(json.dumps({"enabledPlugins": {"other@team": True}}))
        self.assertEqual(hooks.find_root(), self.root)

    def test_internal_errors_never_stop_the_session(self):
        for event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"):
            with self.subTest(event=event), patch.object(hooks, "handle_hook", side_effect=RuntimeError("boom")), \
                    patch("sys.stdin", io.StringIO(json.dumps({"hook_event_name": event}))), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(hooks.run_hook(), 0)
            reply = json.loads(output.getvalue())
            self.assertNotIn("continue", reply)
            self.assertNotIn("decision", reply)
            if event in {"SessionStart", "Stop"}:
                self.assertIn("boom", reply["systemMessage"])
        with patch("sys.stdin", io.StringIO("{")), contextlib.redirect_stdout(io.StringIO()) as output:
            hooks.run_hook()
        self.assertEqual(json.loads(output.getvalue()), {})


class HookPackagingTests(unittest.TestCase):
    def test_declaration_has_the_lifecycle_events_and_no_pretool_gate(self):
        declaration = json.loads((REPOSITORY / "hooks/hooks.json").read_text())
        self.assertEqual(set(declaration["hooks"]), {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"})
        self.assertGreaterEqual(declaration["hooks"]["Stop"][0]["hooks"][0]["timeout"], 120)

    def test_declared_shell_command_bootstraps_in_either_host_environment(self):
        # Codex injects PLUGIN_ROOT; Claude Code injects only CLAUDE_PLUGIN_ROOT.
        declaration = json.loads((REPOSITORY / "hooks/hooks.json").read_text())
        command = declaration["hooks"]["Stop"][0]["hooks"][0]["command"]
        with tempfile.TemporaryDirectory() as directory:
            for variable in ("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT"):
                with self.subTest(variable=variable):
                    environment = {key: value for key, value in os.environ.items()
                                   if key not in {"PYTHONPATH", "PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT", "CLAUDE_PROJECT_DIR"}}
                    environment.update({variable: str(REPOSITORY), "SPECMD_PYTHON": sys.executable})
                    payload = json.dumps({"hook_event_name": "Stop", "cwd": directory, "stop_hook_active": False})
                    result = subprocess.run(["sh", "-c", command], cwd=directory, env=environment,
                                            input=payload, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout), {})

    def test_plugin_root_has_a_single_hook_declaration(self):
        # Claude Code loads hooks/hooks.json from the plugin root besides any
        # manifest path; a second declaration made every hook run twice.
        claude = json.loads((REPOSITORY / ".claude-plugin/plugin.json").read_text())
        codex = json.loads((REPOSITORY / ".codex-plugin/plugin.json").read_text())
        self.assertNotIn("hooks", claude)
        self.assertEqual(codex["hooks"], "./hooks/hooks.json")
        # codex-plugin/ is the generated bundle: a copy of this same file, never loaded from here.
        declarations = [path.relative_to(REPOSITORY).as_posix() for path in REPOSITORY.glob("**/hooks.json")
                        if not {".git", ".venv", "dist", "research", "codex-plugin"} & set(path.relative_to(REPOSITORY).parts)]
        self.assertEqual(declarations, ["hooks/hooks.json"])
        self.assertEqual((REPOSITORY / "codex-plugin/hooks/hooks.json").read_bytes(),
                         (REPOSITORY / "hooks/hooks.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
