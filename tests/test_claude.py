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

from specmd.claude import handle_hook, run_hook


class ClaudeHookTests(unittest.TestCase):
    """Protocol and bootstrap tests; no native Claude Code dispatcher is used."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "specmd.toml").write_text("schema = 1\n")

    def payload(self, event="Stop", **extra):
        return {"cwd": str(self.root), "hook_event_name": event, "stop_hook_active": False, **extra}

    def result(self, status, complete=False, demo=False):
        return {"status": status, "may_complete": complete, "manifest": {"documents": []},
                "verification_mode": "demo" if demo else "real", "assurance": "local_demo" if demo else "protected",
                "findings": [] if complete else [{"kind": "fixture", "message": "Pendência do fixture."}]}

    def test_waiting_human_yields_control_without_false_completion(self):
        for active in (False, True):
            reply = handle_hook(self.payload(stop_hook_active=active), lambda _: self.result("waiting_human_review"))
            self.assertFalse(reply["continue"])
            self.assertNotIn("decision", reply)
            state = json.loads((self.root / ".specmd/local/status.json").read_text())
            self.assertFalse(state["may_complete"])

    def test_repairable_block_requests_one_retry_without_looping(self):
        inspect = lambda _: self.result("blocked")
        self.assertEqual(handle_hook(self.payload(), inspect)["decision"], "block")
        reply = handle_hook(self.payload(stop_hook_active=True), inspect)
        self.assertFalse(reply["continue"])
        self.assertNotIn("decision", reply)

    def test_real_and_explicit_demo_success_allow_normal_stop(self):
        for status, demo in (("passed", False), ("demo_passed", True)):
            self.assertEqual(handle_hook(self.payload(), lambda _: self.result(status, True, demo)), {})

    def test_context_events_keep_their_native_names_and_demo_label(self):
        for event in ("SessionStart", "PostToolUse"):
            reply = handle_hook(self.payload(event), lambda _: self.result("demo_passed", True, True))
            self.assertEqual(reply["hookSpecificOutput"]["hookEventName"], event)
            self.assertIn("SIMULADA", reply["hookSpecificOutput"]["additionalContext"])

    def test_false_success_with_a_finding_is_rejected(self):
        result = self.result("passed", True)
        result["findings"] = [{"kind": "missing", "message": "Teste faltante."}]
        with self.assertRaises(ValueError):
            handle_hook(self.payload(), lambda _: result)

    def test_malformed_input_emits_valid_stop_control_not_unreliable_exit(self):
        with patch("sys.stdin", io.StringIO("{")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_hook(), 0)
        reply = json.loads(output.getvalue())
        self.assertFalse(reply["continue"])
        self.assertIn("erro de verificação", reply["stopReason"])

    def test_declared_shell_command_bootstraps_without_editable_install(self):
        # Native host dispatch is not claimed: run the declared POSIX command as
        # a subprocess in a project which has not opted into SpecMD.
        (self.root / "specmd.toml").unlink()
        repository = Path(__file__).resolve().parents[1]
        declaration = json.loads((repository / "integrations/claude/hooks.json").read_text())
        self.assertEqual(set(declaration["hooks"]), {"SessionStart", "PreToolUse", "PostToolUse", "Stop"})
        command = declaration["hooks"]["Stop"][0]["hooks"][0]["command"]
        environment = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(repository), "SPECMD_PYTHON": sys.executable}
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(["sh", "-c", command], cwd=self.root, env=environment,
                                input=json.dumps(self.payload()), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()
