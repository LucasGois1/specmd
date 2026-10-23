"""No LLM: exercise a simulated agent and fixture browser through public APIs."""
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from specmd.demo import create_demo
from specmd.review_server import build_server
from specmd.workflow import get_review, check_project, run_project, audit_project
from specmd.codex import handle_hook


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="specmd-experience-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "cart"
        self.demo = create_demo(self.root)
        self.authority = Path(self.demo["authority"])
        self.trust = Path(self.demo["trust_store"])

    def hook(self, event="Stop", active=False):
        with patch.dict(os.environ, {"SPECMD_TRUST_STORE": str(self.trust)}):
            return handle_hook({"hook_event_name": event, "cwd": str(self.root), "stop_hook_active": active})

    @contextmanager
    def browser(self):
        server = build_server(self.root, self.authority, self.trust)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def decision(self, server, decision="accept", identifier=None):
        identifier = identifier or get_review(self.root, self.trust)["id"]
        body = json.dumps({"proposal_id": identifier, "reviewer": "synthetic-browser-fixture",
                           "read_confirmed": True, "decision": decision})
        client = http.client.HTTPConnection(*server.server_address[:2], timeout=5)
        self.addCleanup(client.close)
        client.request("POST", "/api/accept", body=body, headers={
            "Content-Type": "application/json", "Origin": server.base_url,
            "X-SpecMD-Review-Token": server.review_token})
        response = client.getresponse()
        return response.status, json.loads(response.read())

    def test_complete_local_experience_with_real_tests_and_mocked_agent(self):
        start = self.hook("SessionStart")
        self.assertIn("waiting_human_review", start["hookSpecificOutput"]["additionalContext"])
        self.assertFalse(self.hook()["continue"])
        source_tool = {"hook_event_name": "PreToolUse", "cwd": str(self.root),
                       "tool_name": "Write", "tool_input": {"file_path": str(self.root / "app.py")}}
        document_tool = {**source_tool, "tool_input": {"file_path": str(self.root / "docs/cart.md")}}
        with patch.dict(os.environ, {"SPECMD_TRUST_STORE": str(self.trust)}):
            self.assertEqual(handle_hook(source_tool)["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertEqual(handle_hook(document_tool), {})
        with self.browser() as server:
            client = http.client.HTTPConnection(*server.server_address[:2], timeout=5)
            client.request("GET", "/")
            response = client.getresponse()
            page = response.read().decode()
            client.close()
            self.assertEqual(response.status, 200)
            self.assertIn("Somar itens", page)
            self.assertIn(".specmd/traceability.json", page)
            # This request is a test fixture, not a claim that a human read it.
            self.assertEqual(self.decision(server)[0], 200)
            self.assertEqual(check_project(self.root, self.trust)["status"], "awaiting_evidence")
            with patch.dict(os.environ, {"SPECMD_TRUST_STORE": str(self.trust)}):
                self.assertEqual(handle_hook(source_tool), {})
            self.assertEqual(self.hook()["decision"], "block")
            completed = run_project(self.root, self.trust)
            self.assertEqual(completed["status"], "demo_passed", completed)
            self.assertEqual(completed["test_mode"], "real")
            self.assertEqual(self.hook(), {})
            # Source-only modification invalidates evidence without new approval.
            app = self.root / "app.py"
            app.write_text(app.read_text().replace("sum(self.prices)", "sum(self.prices) + 1"))
            self.assertEqual(check_project(self.root, self.trust)["status"], "awaiting_evidence")
            self.assertFalse(run_project(self.root, self.trust)["may_complete"])
            app.write_text(app.read_text().replace("sum(self.prices) + 1", "sum(self.prices)"))
            self.assertTrue(run_project(self.root, self.trust)["may_complete"])
            # Narrative change requires a new browser decision, no automatic fix.
            contract = self.root / "docs/cart.md"
            old_id = get_review(self.root, self.trust)["id"]
            contract.write_text(contract.read_text() + "\nNão há taxa adicional.\n")
            self.assertEqual(check_project(self.root, self.trust)["status"], "waiting_human_review")
            self.assertEqual(self.decision(server, identifier=old_id)[0], 409)
            self.assertEqual(self.decision(server)[0], 200)
            self.assertTrue(run_project(self.root, self.trust)["may_complete"])
            self.assertEqual(self.decision(server, decision="reject")[0], 200)
            self.assertFalse(check_project(self.root, self.trust)["may_complete"])
        audit = audit_project(self.root, self.trust)
        self.assertEqual(len(audit["decisions"]), 3)
        self.assertFalse(list(self.root.rglob("*.feature")))
        self.assertFalse(list(self.root.rglob("*.key")))

    def test_cli_subprocess_and_hook_bootstrap_use_the_same_state(self):
        command = [sys.executable, "-m", "specmd", "check", "--root", str(self.root), "--trust", str(self.trust)]
        pending = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(pending.returncode, 1)
        self.assertEqual(json.loads(pending.stdout)["status"], "waiting_human_review")
        with self.browser() as server:
            self.assertEqual(self.decision(server)[0], 200)
        executed = subprocess.run([sys.executable, "-m", "specmd", "run", "--root", str(self.root),
                                   "--trust", str(self.trust)], capture_output=True, text=True, timeout=10)
        self.assertEqual(executed.returncode, 0, executed.stdout)
        repository = Path(__file__).resolve().parents[1]
        env = {**os.environ, "SPECMD_TRUST_STORE": str(self.trust)}
        stopped = subprocess.run([sys.executable, str(repository / "scripts" / "specmd_hook.py")],
                                 input=json.dumps({"hook_event_name": "Stop", "cwd": str(self.root), "stop_hook_active": False}),
                                 text=True, capture_output=True, env=env, timeout=10)
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertEqual(json.loads(stopped.stdout), {})
        denied = subprocess.run(command + ["--require-real"], capture_output=True, text=True, timeout=10)
        self.assertEqual(denied.returncode, 1)
        self.assertFalse(json.loads(denied.stdout)["may_complete"])

    def test_fresh_protected_execution_path_with_fixture_provisioning(self):
        # Simulates an operator provisioning protected trust, not real isolation.
        with self.browser() as server:
            self.assertEqual(self.decision(server)[0], 200)
        trust = json.loads(self.trust.read_text())
        trust["mode"] = "protected"
        self.trust.write_text(json.dumps(trust))
        result = run_project(self.root, self.trust, require_real=True)
        self.assertEqual(result["status"], "passed", result)
        self.assertTrue(result["may_complete"])
        self.assertEqual(result["test_mode"], "real")
        # A stored unsigned report cannot grant a protected pass on its own.
        self.assertEqual(check_project(self.root, self.trust)["status"], "demo_passed")


if __name__ == "__main__":
    unittest.main()
