import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from specmd.codex import handle_hook, observed_changes, run_hook


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "specmd.toml").write_text("schema = 1\n")

    def payload(self, event="Stop", **extra):
        return {"cwd": str(self.root), "hook_event_name": event, "stop_hook_active": False, **extra}

    def result(self, status):
        return {"protocol_version": 1, "status": status, "may_complete": False,
                "manifest": {"documents": []}, "findings": [{"kind": "test", "message": "Pendência do fixture."}]}

    def test_waiting_returns_control_and_never_marks_done_on_repeated_calls(self):
        for active in (False, True):
            response = handle_hook(self.payload(stop_hook_active=active), lambda _: self.result("waiting_human_review"))
            self.assertFalse(response["continue"])
            self.assertNotIn("decision", response)
            state = json.loads((self.root / ".specmd/local/status.json").read_text())
            self.assertFalse(state["may_complete"])
            self.assertEqual(state["status"], "waiting_human_review")

    def test_repairable_block_has_one_retry_then_returns_control(self):
        inspect = lambda _: self.result("blocked")
        first = handle_hook(self.payload(), inspect)
        self.assertEqual(first["decision"], "block")
        self.assertTrue(first["reason"])
        second = handle_hook(self.payload(stop_hook_active=True), inspect)
        self.assertFalse(second["continue"])
        self.assertIn("evitar um ciclo", second["stopReason"])
        self.assertFalse(json.loads((self.root / ".specmd/local/status.json").read_text())["may_complete"])

    def test_unconfigured_project_is_noop(self):
        (self.root / "specmd.toml").unlink()
        self.assertEqual(handle_hook(self.payload()), {})
        self.assertFalse((self.root / ".specmd").exists())

    def test_config_removal_after_activation_remains_pending(self):
        handle_hook(self.payload(), lambda _: self.result("waiting_human_review"))
        (self.root / "specmd.toml").unlink()
        reply = handle_hook(self.payload(), lambda _: {"status": "inactive", "may_complete": None})
        self.assertEqual(reply["decision"], "block")
        self.assertIn("removida", reply["reason"])

    def test_session_start_and_post_tool_use_have_protocol_specific_context(self):
        for event in ("SessionStart", "PostToolUse"):
            reply = handle_hook(self.payload(event), lambda _: self.result("waiting_human_review"))
            self.assertEqual(reply["hookSpecificOutput"]["hookEventName"], event)
            self.assertIn("may_complete=false", reply["hookSpecificOutput"]["additionalContext"])

    def test_invalid_payload_emits_control_json_instead_of_unreliable_error_exit(self):
        with patch("sys.stdin", io.StringIO('{"hook_event_name":"Stop"}')), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_hook(), 0)
        reply = json.loads(output.getvalue())
        self.assertFalse(reply["continue"])
        self.assertIn("erro de verificação", reply["stopReason"])

    def test_core_exception_does_not_silently_allow_completion(self):
        with patch("specmd.codex.handle_hook", side_effect=RuntimeError("fixture failure")), patch("sys.stdin", io.StringIO("{}")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run_hook(), 0)
        reply = json.loads(output.getvalue())
        self.assertFalse(reply["continue"])
        self.assertIn("fixture failure", reply["stopReason"])

    def test_symlinked_state_is_rejected_without_writing_outside(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.root / ".specmd").symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "link simbólico"):
            handle_hook(self.payload(), lambda _: self.result("waiting_human_review"))
        self.assertFalse((elsewhere / "local").exists())

    def test_observed_changes_include_rename_as_remove_and_add(self):
        before = {"documents": [{"path": "old.md", "sha256": "a"}, {"path": "changed.md", "sha256": "b"}]}
        after = {"documents": [{"path": "new.md", "sha256": "a"}, {"path": "changed.md", "sha256": "c"}]}
        self.assertEqual(observed_changes(before, after), [{"kind": "added", "path": "new.md"}, {"kind": "modified", "path": "changed.md"}, {"kind": "removed", "path": "old.md"}])


if __name__ == "__main__":
    unittest.main()
