"""Lifecycle tests use a fixture decision, never claim an actual human read it."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from specmd import workflow


CONTRACT = '''---
specmd:
  schema: 1
  id: SMD-TEST-DOC-001
  kind: behavioral
---
# Teste
## SMD-TEST-REQ-001 — Somar valores
O resultado deve ser a soma dos valores, sem taxa adicional.
```gherkin
# language: pt
@SMD-TEST-REQ-001
Funcionalidade: Soma
  @SMD-TEST-SCN-001
  Cenário: Somar
    Dado os valores 2 e 3
    Quando somados
    Então o resultado é 5
```
'''


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        from specmd.authority import initialize_authority
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        (self.root / "specmd.toml").write_text('schema = 2\nproject_id = "test"\n[[runners]]\nid="python"\nlanguage="python"\n')
        (self.root / "contract.md").write_text(CONTRACT)
        (self.root / "app.py").write_text("def add(a, b):\n    return a + b\n")
        (self.root / ".specmd").mkdir()
        (self.root / ".specmd/traceability.json").write_text(json.dumps({"schema": 1, "files": {
            "app.py": {"requirements": ["SMD-TEST-REQ-001"], "scenarios": ["SMD-TEST-SCN-001"]}}}))
        self.authority = self.base / "authority"
        initialize_authority(self.authority, "test", str(self.root))
        self.trust = self.authority / "trust.json"

    def approve(self):
        proposal = workflow.prepare_review(self.root)
        workflow.accept_review(self.root, proposal["id"], self.authority, "fixture-reviewer")
        return proposal

    def execution(self, passed=True, mode="real"):
        return {"schema": 1, "mode": mode, "passed": passed, "runners": [], "findings": [],
                "scenarios": [{"id": "SMD-TEST-SCN-001", "status": "passed" if passed else "failed", "steps_executed": 3}]}

    def run_fixture(self, passed=True):
        with patch("specmd.runner.execute_project", return_value=self.execution(passed)):
            return workflow.run_project(self.root, self.trust)

    def test_cannot_complete_without_review_then_evidence(self):
        self.assertEqual(workflow.check_project(self.root, self.trust)["status"], "waiting_human_review")
        self.approve()
        self.assertEqual(workflow.check_project(self.root, self.trust)["status"], "awaiting_evidence")
        result = self.run_fixture()
        self.assertEqual(result["status"], "demo_passed")
        self.assertTrue(result["may_complete"])
        self.assertEqual(result["assurance"], "local_demo")

    def test_changed_prose_or_scenario_invalidates_approval(self):
        self.approve()
        self.assertTrue(self.run_fixture()["may_complete"])
        (self.root / "contract.md").write_text(CONTRACT.replace("sem taxa adicional", "com taxa adicional"))
        result = workflow.check_project(self.root, self.trust)
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["status"], "waiting_human_review")

    def test_code_change_preserves_approval_and_invalidates_evidence(self):
        self.approve()
        self.run_fixture()
        (self.root / "app.py").write_text("def add(a,b):\n    return a + b + 1\n")
        result = workflow.check_project(self.root, self.trust)
        self.assertEqual(result["status"], "awaiting_evidence")
        self.assertEqual(result["findings"][0]["kind"], "evidence_stale")
        self.assertFalse(self.run_fixture(False)["may_complete"])

    def test_stale_review_cannot_be_accepted(self):
        proposal = workflow.prepare_review(self.root)
        (self.root / "contract.md").write_text(CONTRACT + "\nOutra regra proposta.\n")
        with self.assertRaisesRegex(ValueError, "mudou"):
            workflow.accept_review(self.root, proposal["id"], self.authority, "fixture")

    def test_review_shows_previous_accepted_narrative(self):
        self.approve()
        (self.root / "contract.md").write_text(CONTRACT + "\nNovo texto.\n")
        review = workflow.prepare_review(self.root, self.trust)
        self.assertEqual(review["documents"][0]["previous_text"], CONTRACT)
        self.assertIn("Novo texto", review["documents"][0]["text"])

    def test_new_unclassified_markdown_blocks(self):
        self.approve()
        (self.root / "untracked.md").write_text("# Regra desconhecida\n")
        result = workflow.check_project(self.root, self.trust)
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["status"], "blocked")

    def test_reference_exemption_is_also_version_bound(self):
        (self.root / "editor.md").write_text('---\nspecmd:\n  schema: 1\n  id: SMD-TEST-DOC-002\n  kind: reference\n  exemption_reason: Guia de editor sem regra de produto\n---\n# Editor\n')
        self.approve()
        self.run_fixture()
        with (self.root / "editor.md").open("a") as stream:
            stream.write("\nTexto novo.\n")
        self.assertEqual(workflow.check_project(self.root, self.trust)["status"], "waiting_human_review")

    def test_unknown_behavior_source_or_test_blocks(self):
        self.approve()
        (self.root / "invented_test.py").write_text("assert 1 == 1\n")
        result = workflow.check_project(self.root, self.trust)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any(f["kind"] == "behavior_origin_missing" for f in result["findings"]))

    def test_traceability_edit_requires_review_even_if_docs_unchanged(self):
        self.approve()
        path = self.root / ".specmd/traceability.json"
        value = json.loads(path.read_text())
        value["files"]["app.py"]["note"] = "outra justificativa"
        path.write_text(json.dumps(value))
        self.assertEqual(workflow.check_project(self.root, self.trust)["status"], "waiting_human_review")

    def test_copied_public_trust_inside_repository_is_rejected(self):
        inside = self.root / ".specmd/trust.json"
        inside.write_bytes(self.trust.read_bytes())
        result = workflow.check_project(self.root, inside)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["may_complete"])

    def test_missing_trust_remains_pending(self):
        with patch.dict("os.environ", {}, clear=True):
            result = workflow.check_project(self.root)
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["status"], "waiting_human_review")

    def test_changed_files_during_run_discard_evidence(self):
        self.approve()
        def changing(*args):
            (self.root / "app.py").write_text("# changed while testing\n")
            return self.execution()
        with patch("specmd.runner.execute_project", side_effect=changing):
            result = workflow.run_project(self.root, self.trust)
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["findings"][0]["kind"], "changed_during_execution")
        self.assertFalse((self.root / ".specmd/local/evidence.json").exists())

    def test_partial_or_zero_scenario_success_cannot_pass(self):
        self.approve()
        report = self.execution()
        report["scenarios"] = []
        with patch("specmd.runner.execute_project", return_value=report):
            result = workflow.run_project(self.root, self.trust)
        self.assertFalse(result["may_complete"])

    def test_local_mode_never_satisfies_protected_gate(self):
        self.approve()
        with patch("specmd.runner.execute_project", return_value=self.execution()):
            result = workflow.run_project(self.root, self.trust, require_real=True)
        self.assertFalse(result["may_complete"])
        self.assertEqual(result["findings"][0]["kind"], "protected_execution_required")

    def test_rejection_invalidates_old_acceptance(self):
        proposal = self.approve()
        self.run_fixture()
        workflow.accept_review(self.root, proposal["id"], self.authority, "fixture", decision="reject")
        result = workflow.check_project(self.root, self.trust)
        self.assertFalse(result["may_complete"])

    def test_mutated_evidence_digest_is_detected(self):
        self.approve()
        self.run_fixture()
        path = self.root / ".specmd/local/evidence.json"
        value = json.loads(path.read_text())
        value["code_sha256"] = "forged"
        path.write_text(json.dumps(value))
        self.assertFalse(workflow.check_project(self.root, self.trust)["may_complete"])

    def test_tampered_local_diff_cache_cannot_forge_previous_text(self):
        self.approve()
        path = self.root / ".specmd/local/last-accepted-review.json"
        path.write_text('{"documents":[{"path":"contract.md","text":"forged"}]}')
        current = workflow.prepare_review(self.root, self.trust)
        self.assertEqual(current["documents"][0]["previous_text"], CONTRACT)

    def test_duplicate_traceability_keys_are_rejected(self):
        (self.root / ".specmd/traceability.json").write_text('{"schema":1,"files":{},"files":{}}')
        result = workflow.check_project(self.root, self.trust)
        self.assertEqual(result["status"], "error")
        self.assertFalse(result["may_complete"])

    def test_expired_evidence_is_not_a_success(self):
        self.approve()
        self.run_fixture()
        path = self.root / ".specmd/local/evidence.json"
        value = json.loads(path.read_text())
        value["created_at"] = "2000-01-01T00:00:00+00:00"
        value["sha256"] = workflow.digest({k: v for k, v in value.items() if k != "sha256"})
        path.write_text(json.dumps(value))
        result = workflow.check_project(self.root, self.trust)
        self.assertEqual(result["findings"][0]["kind"], "evidence_expired")
        self.assertFalse(result["may_complete"])

    def test_empty_fresh_evidence_cannot_promote_an_old_report(self):
        self.approve()
        self.run_fixture()
        trust = json.loads(self.trust.read_text())
        trust["mode"] = "protected"
        self.trust.write_text(json.dumps(trust))
        for invalid in ({}, [], ""):
            with self.subTest(invalid=invalid):
                result = workflow.check_project(self.root, self.trust, fresh_evidence=invalid, require_real=True)
                self.assertFalse(result["may_complete"])
                self.assertEqual(result["status"], "error")

    def test_symlinked_local_state_never_writes_outside(self):
        self.approve()
        target = self.base / "outside"
        target.mkdir()
        local = self.root / ".specmd/local"
        for child in local.iterdir():
            child.unlink()
        local.rmdir()
        local.symlink_to(target, target_is_directory=True)
        result = self.run_fixture()
        self.assertEqual(result["status"], "error")
        self.assertFalse((target / "evidence.json").exists())


if __name__ == "__main__":
    unittest.main()
