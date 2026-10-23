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

from specmd import hooks
from specmd import state as hook_state
from specmd.demo import create_demo

REPOSITORY = Path(__file__).resolve().parents[1]
GAP_DOC = """---
specmd:
  schema: 1
  id: SMD-DEMO-DOC-002
  kind: behavioral
---

# Cupons

## SMD-DEMO-REQ-003 — Cupom de desconto

Um cupom DEZ aplica 10% de desconto.
"""
SCENARIO = """
```gherkin
# language: pt
Funcionalidade: Cupom

  @SMD-DEMO-REQ-003 @SMD-DEMO-SCN-003
  Cenário: Cupom DEZ
    Dado um carrinho vazio
    Quando eu adicionar itens de 500 e 500 centavos
    Então o total deve ser 1000 centavos
```
"""


class HookLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-hooks-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        environment = patch.dict(os.environ, {}, clear=False)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def hook(self, event, **extra):
        return hooks.handle_hook({"hook_event_name": event, "cwd": str(self.root), **extra})

    def edit_app(self, old, new):
        app = self.root / "app.py"
        app.write_text(app.read_text().replace(old, new))

    def test_project_without_configuration_is_ignored(self):
        (self.root / "specmd.toml").unlink()
        for event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"):
            self.assertEqual(self.hook(event, tool_name="Edit"), {})

    def test_read_only_tools_return_without_touching_the_project(self):
        with patch.object(hooks, "find_root", side_effect=AssertionError("disk access")):
            self.assertEqual(hooks.handle_hook({"hook_event_name": "PostToolUse", "tool_name": "Read"}), {})

    def test_session_start_summarizes_documentation_and_conventions(self):
        reply = self.hook("SessionStart")
        context = reply["hookSpecificOutput"]["additionalContext"]
        self.assertIn("1 (2 cenários)", context)
        self.assertIn("mostre-os ao dev e peça confirmação", context)
        state = hook_state.load(self.root)
        self.assertIn("code_fp_baseline", state)
        self.assertIn("docs/cart.md", state["spec_at_prompt"])

    def test_documentation_gap_is_reported_after_the_edit_and_once_at_stop(self):
        self.hook("SessionStart")
        (self.root / "docs/cupons.md").write_text(GAP_DOC)
        context = self.hook("PostToolUse", tool_name="Write")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("docs/cupons.md", context)
        self.assertIn("não possui cenário", context)
        self.assertIn("pergunte ao dev", context)
        self.assertEqual(self.hook("PostToolUse", tool_name="Edit"), {})
        first = self.hook("Stop", stop_hook_active=False)
        self.assertEqual(first["decision"], "block")
        self.assertIn("SMD-DEMO-REQ-003", first["reason"])
        second = self.hook("Stop", stop_hook_active=True)
        self.assertNotIn("decision", second)
        self.assertNotIn("continue", second)

    def test_new_scenarios_wait_for_the_developer_before_execution(self):
        self.hook("SessionStart")
        (self.root / "docs/cupons.md").write_text(GAP_DOC + SCENARIO)
        context = self.hook("PostToolUse", tool_name="Write")["hookSpecificOutput"]["additionalContext"]
        self.assertIn("peça confirmação antes de implementar", context)
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        reply = self.hook("Stop")
        self.assertIn("aguardando sua confirmação", reply["systemMessage"])
        self.assertNotIn("last_run", hook_state.load(self.root))
        self.assertEqual(self.hook("UserPromptSubmit"), {})
        reply = self.hook("Stop")
        self.assertIn("3 cenários passando", reply["systemMessage"])

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
        self.assertIn("2 de 2 cenários", first["reason"])
        self.assertIn("Total observado 501; esperado 500", first["reason"])
        repeated = self.hook("Stop", stop_hook_active=True)
        self.assertIn("ainda não passam", repeated["systemMessage"])
        self.edit_app("return sum(self.prices) + 1", "return sum(self.prices)")
        fixed = self.hook("Stop", stop_hook_active=True)
        self.assertIn("2 cenários passando", fixed["systemMessage"])
        self.assertEqual(self.hook("Stop"), {})

    def test_undefined_steps_come_back_with_a_snippet(self):
        self.hook("SessionStart")
        (self.root / "docs/cupons.md").write_text(GAP_DOC + SCENARIO.replace(
            "    Então", '    E eu aplicar o cupom "DEZ"\n    Então'))
        self.hook("UserPromptSubmit")
        self.edit_app("return sum(self.prices)", "return sum(self.prices) + 0")
        reply = self.hook("Stop")
        self.assertEqual(reply["decision"], "block")
        self.assertIn("Passo sem implementação", reply["reason"])
        self.assertIn("def step_impl(context)", reply["reason"])

    def test_block_cap_lets_the_agent_stop(self):
        for index in range(hooks.MAX_BLOCKS):
            self.assertEqual(hooks._block_once(self.root, f"sig-{index}", "motivo", "resumo")["decision"], "block")
        self.assertEqual(hooks._block_once(self.root, "sig-new", "motivo", "resumo"), {"systemMessage": "resumo"})
        self.hook("UserPromptSubmit")
        self.assertEqual(hooks._block_once(self.root, "sig-new", "motivo", "resumo")["decision"], "block")

    def test_project_root_from_claude_project_dir(self):
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.root)
        self.assertEqual(hooks.find_root({"cwd": "/"}), self.root)

    def test_internal_errors_never_stop_the_session(self):
        for event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"):
            with self.subTest(event=event), patch.object(hooks, "handle_hook", side_effect=RuntimeError("falha")), \
                    patch("sys.stdin", io.StringIO(json.dumps({"hook_event_name": event}))), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(hooks.run_hook(), 0)
            reply = json.loads(output.getvalue())
            self.assertNotIn("continue", reply)
            self.assertNotIn("decision", reply)
            if event in {"SessionStart", "Stop"}:
                self.assertIn("falha", reply["systemMessage"])
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
        declarations = [path.relative_to(REPOSITORY).as_posix() for path in REPOSITORY.glob("**/hooks.json")
                        if not {".git", ".venv", "dist", "research"} & set(path.relative_to(REPOSITORY).parts)]
        self.assertEqual(declarations, ["hooks/hooks.json"])


if __name__ == "__main__":
    unittest.main()
