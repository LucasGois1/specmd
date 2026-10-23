"""Local-demo integration tests. Synthetic test decisions are not human consent."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from specmd.cli import main
from specmd.config import load_config
from specmd.demo import create_demo
from specmd.workflow import accept_review, check_project, prepare_review, run_project


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="specmd-demo-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "cart"

    def test_creation_keeps_authority_external_and_never_approves_or_executes(self):
        result = create_demo(self.root)
        self.assertEqual(result["status"], "demo_created")
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["assurance"], "local_demo")
        trust = Path(result["trust_store"])
        self.assertFalse(trust.is_relative_to(self.root))
        self.assertTrue(trust.is_file())
        self.assertFalse(any(self.root.rglob("*.key")))
        self.assertFalse((self.root / ".specmd/approvals").exists())
        self.assertFalse((self.root / ".specmd/local/evidence.json").exists())
        self.assertEqual(load_config(self.root)["schema"], 2)
        status = check_project(self.root, trust)
        self.assertEqual(status["status"], "waiting_human_review", status)
        self.assertFalse(status["may_complete"])

    def test_synthetic_acceptance_fixture_runs_real_behave_but_only_demo_assurance(self):
        setup = create_demo(self.root)
        trust = Path(setup["trust_store"])
        blocked = run_project(self.root, trust)
        self.assertEqual(blocked["status"], "waiting_human_review")
        self.assertFalse((self.root / ".specmd/local/evidence.json").exists())
        proposal = prepare_review(self.root, trust)
        # Explicit automation fixture: this records no real person's approval.
        accepted = accept_review(self.root, proposal["id"], Path(setup["authority"]),
                                 "automated synthetic fixture")
        self.assertEqual(accepted["status"], "accepted")
        result = run_project(self.root, trust)
        self.assertEqual(result["status"], "demo_passed", result)
        self.assertEqual(result["test_mode"], "real")
        self.assertEqual(result["assurance"], "local_demo")
        self.assertTrue(result["may_complete"])
        observed = result["evidence"]["execution"]["scenarios"]
        self.assertEqual({item["id"] for item in observed}, {"SMD-DEMO-SCN-001", "SMD-DEMO-SCN-002"})
        self.assertTrue(all(item["status"] == "passed" for item in observed))
        self.assertFalse(list(self.root.rglob("*.feature")))
        protected = run_project(self.root, trust, require_real=True)
        self.assertFalse(protected["may_complete"])
        self.assertEqual(protected["status"], "blocked")

    def test_refuses_existing_project_without_overwriting_any_file(self):
        self.root.mkdir()
        sentinel = self.root / "app.py"
        sentinel.write_text("existing project")
        with self.assertRaisesRegex(ValueError, "sobrescrito"):
            create_demo(self.root)
        self.assertEqual(sentinel.read_text(), "existing project")
        self.assertFalse(self.base.joinpath("cart-authority").exists())

    def test_refuses_authority_inside_project_before_creating_any_files(self):
        with self.assertRaisesRegex(ValueError, "fora do projeto"):
            create_demo(self.root, self.root / "authority")
        self.assertFalse(self.root.exists())

    def test_refuses_overwriting_existing_authority(self):
        authority = self.base / "authority"
        authority.mkdir()
        sentinel = authority / "private.key"
        sentinel.write_text("not a real key")
        with self.assertRaisesRegex(ValueError, "chaves existentes"):
            create_demo(self.root, authority)
        self.assertEqual(sentinel.read_text(), "not a real key")
        self.assertFalse(self.root.exists())


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="specmd-cli-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def invoke(self, arguments):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            exit_code = main(arguments)
        return exit_code, json.loads(output.getvalue())

    def test_init_defaults_to_schema_two_and_keeps_legacy_explicit(self):
        code, result = self.invoke(["init", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(result["schema"], 2)
        config = load_config(self.root)
        self.assertEqual(config["project_id"], self.root.name)
        self.assertEqual(config["traceability"]["policy"], "strict")
        legacy = self.root / "legacy"
        legacy.mkdir()
        code, result = self.invoke(["init", "--root", str(legacy), "--legacy"])
        self.assertEqual(code, 0)
        self.assertEqual(load_config(legacy), {"schema": 1})

    def test_check_never_returns_zero_for_pending_error_or_inactive(self):
        for status, expected in (("waiting_human_review", 1), ("awaiting_evidence", 1), ("blocked", 1), ("error", 2), ("inactive", 2)):
            with self.subTest(status=status), patch("specmd.workflow.check_project", return_value={"status": status, "may_complete": False, "findings": []}):
                code, result = self.invoke(["check", "--root", str(self.root)])
                self.assertEqual(code, expected)
                self.assertEqual(result["status"], status)

    def test_verify_always_requires_fresh_real_verification(self):
        with patch("specmd.workflow.run_project", return_value={"status": "blocked", "may_complete": False, "findings": []}) as run:
            code, _ = self.invoke(["verify", "--root", str(self.root)])
        self.assertEqual(code, 1)
        run.assert_called_once_with(self.root, None, require_real=True)

    def test_review_prepare_uses_external_trust_environment(self):
        external = self.root.parent / "fixture-trust.json"
        with patch.dict("os.environ", {"SPECMD_TRUST_STORE": str(external)}), patch("specmd.workflow.prepare_review", return_value={"id": "fixture"}) as prepare:
            code, result = self.invoke(["review", "--root", str(self.root), "--prepare"])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "review_prepared")
        prepare.assert_called_once_with(self.root, trust_path=external)

    def test_audit_is_read_only_and_routes_to_workflow(self):
        with patch("specmd.workflow.audit_project", return_value={"status": "audit", "may_complete": False}) as audit:
            code, result = self.invoke(["audit", "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "audit")
        audit.assert_called_once_with(self.root, None)


if __name__ == "__main__":
    unittest.main()
