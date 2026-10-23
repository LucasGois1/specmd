"""Approval integrity, context, revocation and honest local-demo boundaries."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from specmd.authority import create_review, initialize_authority, sign_approval, verify_approval
from specmd.core import inspect_project


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="specmd-authority-")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name).resolve()
        self.root = base / "project"
        self.root.mkdir()
        self.authority = base / "external-authority"
        (self.root / "specmd.toml").write_text("schema = 1\n", encoding="utf-8")
        (self.root / "contract.md").write_text("# Texto exato revisado\n", encoding="utf-8")
        self.config = {"project_id": "test-project"}
        self.inspection = inspect_project(self.root)
        self.proposal = create_review(self.root, self.inspection, self.config)
        self.initialized = initialize_authority(self.authority, "test-project", self.root)
        self.trust_path = self.authority / "trust.json"
        self.expected = {key: self.proposal[key] for key in (
            "project_id", "repository", "contract_sha256", "manifest", "proposal_sha256",
        )}

    def trust(self):
        return json.loads(self.trust_path.read_text(encoding="utf-8"))

    def write_trust(self, value):
        self.trust_path.write_text(json.dumps(value), encoding="utf-8")

    def sign(self, decision="accept"):
        return sign_approval(self.proposal, self.authority, "Pessoa do ensaio", decision)

    def verify(self, envelope, expected=None, trust_path=None):
        return verify_approval(envelope, trust_path or self.trust_path, expected or self.expected)

    def test_explicit_initialization_is_external_private_and_demo(self):
        self.assertEqual(self.initialized["mode"], "local_demo")
        self.assertEqual((self.authority / "private.key").stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.root / "private.key").exists())
        self.assertEqual(self.trust()["latest_decisions"], {})
        with self.assertRaisesRegex(ValueError, "sobrescrito"):
            initialize_authority(self.authority, "test-project", self.root)

    def test_initialization_inside_repo_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "fora do repositório"):
            initialize_authority(self.root / ".specmd/authority", "test-project", self.root)
        self.assertFalse((self.root / ".specmd").exists())

    def test_initializer_does_not_claim_protected_authority(self):
        with self.assertRaisesRegex(ValueError, "provisionado"):
            initialize_authority(self.authority.parent / "other", "test-project", self.root, mode="protected")

    def test_review_is_deterministic_and_captures_exact_utf8(self):
        repeated = create_review(self.root, self.inspection, self.config)
        self.assertEqual(repeated, self.proposal)
        snapshot = self.proposal["documents"][0]
        self.assertEqual(snapshot["text"], "# Texto exato revisado\n")
        self.assertEqual(hashlib.sha256(snapshot["text"].encode()).hexdigest(), snapshot["sha256"])
        self.assertEqual(self.proposal["id"], self.proposal["proposal_sha256"])

    def test_review_rejects_document_changed_after_inspection(self):
        (self.root / "contract.md").write_text("Mudou.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "mudou"):
            create_review(self.root, self.inspection, self.config)

    def test_review_rejects_configuration_changed_after_inspection(self):
        (self.root / "specmd.toml").write_text("schema = 1\n# mudança\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "configuração mudou"):
            create_review(self.root, self.inspection, self.config)

    def test_signature_round_trip_is_honestly_labeled(self):
        envelope = self.sign()
        result = self.verify(envelope)
        self.assertTrue(result["valid"])
        self.assertTrue(result["approved"])
        self.assertEqual(result["trust_mode"], "local_demo")
        self.assertFalse(result["human_authenticated"])
        self.assertEqual(result["claims"]["reviewer"], "Pessoa do ensaio")
        self.assertEqual(self.trust()["latest_decisions"][self.proposal["proposal_sha256"]], result["envelope_sha256"])

    def test_ui_annotations_do_not_change_signed_proposal_identity(self):
        enriched = deepcopy(self.proposal)
        enriched["previous_text"] = "Contexto visual anterior."
        enriched["documents"][0]["metadata"] = {"kind": "reference"}
        enriched["documents"][0]["previous_text"] = "Antes."
        envelope = sign_approval(enriched, self.authority, "Pessoa do ensaio")
        self.assertTrue(self.verify(envelope)["approved"])

    def test_tampered_presented_document_is_not_signable(self):
        tampered = deepcopy(self.proposal)
        tampered["documents"][0]["text"] = "Texto diferente."
        with self.assertRaisesRegex(ValueError, "texto apresentado"):
            sign_approval(tampered, self.authority, "Pessoa")

    def test_tampered_proposal_identity_is_rejected(self):
        tampered = deepcopy(self.proposal)
        tampered["project_id"] = "different"
        with self.assertRaisesRegex(ValueError, "identidade da proposta"):
            sign_approval(tampered, self.authority, "Pessoa")

    def test_payload_tampering_invalidates_signature(self):
        envelope = self.sign()
        envelope["payload"]["reviewer"] = "Outra pessoa"
        with self.assertRaisesRegex(ValueError, "Assinatura"):
            self.verify(envelope)

    def test_wrong_contract_project_or_repository_is_rejected(self):
        envelope = self.sign()
        replacements = {"contract_sha256": "0" * 64, "project_id": "another-project",
                        "repository": str(self.root.parent / "different-repository")}
        for key, replacement in replacements.items():
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "não corresponde"):
                expected = {**self.expected, key: replacement}
                self.verify(envelope, expected)

    def test_wrong_signing_key_is_rejected(self):
        envelope = self.sign()
        envelope["key_id"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "não é confiável"):
            self.verify(envelope)

    def test_revoked_key_is_rejected(self):
        envelope = self.sign()
        trust = self.trust()
        trust["keys"][0]["revoked"] = True
        self.write_trust(trust)
        with self.assertRaisesRegex(ValueError, "revogada"):
            self.verify(envelope)

    def test_key_authorization_is_bound_to_project_and_repository(self):
        envelope = self.sign()
        for field, value in (("project_id", "unrelated"), ("repository", str(self.root.parent))):
            with self.subTest(field=field):
                trust = self.trust()
                trust["keys"][0]["authorizations"][0][field] = value
                self.write_trust(trust)
                with self.assertRaisesRegex(ValueError, "não está autorizada"):
                    self.verify(envelope)
                trust["keys"][0]["authorizations"][0] = {
                    "project_id": "test-project", "repository": str(self.root),
                }
                self.write_trust(trust)

    def test_trust_in_repository_is_never_an_authority(self):
        envelope = self.sign()
        inside = self.root / "trust.json"
        inside.write_bytes(self.trust_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "fora do repositório"):
            self.verify(envelope, trust_path=inside)

    def test_rejection_supersedes_acceptance_in_external_registry(self):
        accepted = self.sign()
        accepted_digest = self.verify(accepted)["envelope_sha256"]
        rejected = self.sign("reject")
        self.assertEqual(rejected["payload"]["previous_approval_sha256"], accepted_digest)
        result = self.verify(rejected)
        self.assertTrue(result["valid"])
        self.assertFalse(result["approved"])
        self.assertEqual(result["decision"], "reject")
        with self.assertRaisesRegex(ValueError, "decisão atual"):
            self.verify(accepted)

    def test_protected_trust_requires_a_current_external_decision(self):
        envelope = self.sign()
        trust = self.trust()
        trust["mode"] = "protected"  # Provisioned by this test, not proof of deployment isolation.
        trust.pop("latest_decisions")
        self.write_trust(trust)
        with self.assertRaisesRegex(ValueError, "decisão atual"):
            self.verify(envelope)

    def test_operator_provisioned_protected_record_still_does_not_prove_human_login(self):
        envelope = self.sign()
        trust = self.trust()
        trust["mode"] = "protected"
        self.write_trust(trust)
        result = self.verify(envelope)
        self.assertTrue(result["approved"])
        self.assertEqual(result["trust_mode"], "protected")
        self.assertFalse(result["human_authenticated"])

    def test_duplicate_json_keys_in_trust_are_rejected(self):
        envelope = self.sign()
        self.trust_path.write_text('{"schema":1,"schema":1}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicada"):
            self.verify(envelope)

    def test_verification_does_not_generate_missing_authority(self):
        envelope = self.sign()
        missing = self.authority.parent / "missing" / "trust.json"
        with self.assertRaises(ValueError):
            self.verify(envelope, trust_path=missing)
        self.assertFalse(missing.parent.exists())

    def test_nan_in_signed_data_is_not_canonical_json(self):
        tampered = deepcopy(self.proposal)
        tampered["manifest"]["extra"] = float("nan")
        with self.assertRaisesRegex(ValueError, "JSON canônica"):
            sign_approval(tampered, self.authority, "Pessoa")

    def portable_proposal(self):
        config = {**self.config, "repository_id": "github.com/example/specmd"}
        proposal = create_review(self.root, self.inspection, config)
        directory = self.authority.parent / "portable-authority"
        initialize_authority(directory, config["project_id"], proposal["repository"], workspace_root=self.root)
        return config, proposal, directory

    def test_logical_repository_acceptance_is_portable_between_checkouts(self):
        config, proposal, directory = self.portable_proposal()
        envelope = sign_approval(proposal, directory, "Pessoa")
        moved = self.root.parent / "checkout-in-ci"
        shutil.copytree(self.root, moved)
        reviewed_in_ci = create_review(moved, inspect_project(moved), config)
        self.assertEqual(reviewed_in_ci["id"], proposal["id"])
        self.assertNotEqual(reviewed_in_ci["workspace_root"], proposal["workspace_root"])
        expected = {key: reviewed_in_ci[key] for key in (
            "project_id", "repository", "contract_sha256", "manifest", "proposal_sha256", "workspace_root",
        )}
        self.assertTrue(verify_approval(envelope, directory / "trust.json", expected)["approved"])

    def test_other_logical_repository_is_rejected(self):
        _, proposal, directory = self.portable_proposal()
        envelope = sign_approval(proposal, directory, "Pessoa")
        expected = {**self.expected, "repository": "repo:github.com/other/project", "workspace_root": str(self.root)}
        with self.assertRaisesRegex(ValueError, "repository atual"):
            verify_approval(envelope, directory / "trust.json", expected)

    def test_logical_repository_requires_workspace_for_external_trust_check(self):
        _, proposal, directory = self.portable_proposal()
        envelope = sign_approval(proposal, directory, "Pessoa")
        expected = {key: proposal[key] for key in ("project_id", "repository", "contract_sha256")}
        with self.assertRaisesRegex(ValueError, "workspace_root"):
            verify_approval(envelope, directory / "trust.json", expected)

    def test_trust_inside_checkout_is_rejected_even_with_logical_repository(self):
        _, proposal, directory = self.portable_proposal()
        envelope = sign_approval(proposal, directory, "Pessoa")
        inside = self.root / "trust.json"
        inside.write_bytes((directory / "trust.json").read_bytes())
        expected = {**proposal, "workspace_root": str(self.root)}
        with self.assertRaisesRegex(ValueError, "fora do repositório"):
            verify_approval(envelope, inside, expected)

    def test_repository_identifier_rejects_ambiguous_whitespace(self):
        for value in (" github.com/example/specmd", "github.com/example/\nproject", "repo:already-prefixed"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                create_review(self.root, self.inspection, {**self.config, "repository_id": value})


if __name__ == "__main__":
    unittest.main()
