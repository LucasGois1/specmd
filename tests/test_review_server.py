"""HTTP boundary tests with a fake workflow, not real human acceptance."""

import copy
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from specmd.review_server import build_server


class ReviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.authority = self.root / "external-demo-authority"
        self.trust = self.root / "trust.json"
        self.proposal = {
            "id": "version-a", "project_id": "demo-project", "repository": "local-demo",
            "contract_sha256": "contract-digest",
            "documents": [{
                "path": "docs/contract.md", "id": "SMD-DOC-1", "kind": "reference",
                "sha256": "document-digest", "exemption_reason": "Guia do editor <não é regra>",
                "requirements": [{"id": "SMD-REQ-1", "line": 8}],
                "scenarios": [{"id": "SMD-SCN-1", "name": "Cenário <seguro>", "line": 12,
                               "requirements": ["SMD-REQ-1"]}],
                "previous_text": "# Antes\nTexto antigo\n",
                "text": '# Depois\nTexto integral\n<script>alert("doc")</script>\n',
            }],
            "removed_documents": [{"path": "removed.md", "previous_text": "Texto removido <tag>"}],
            "config_text": 'schema = 2\nproject_id = "demo-project"\n',
            "traceability": {"path": ".specmd/traceability.json", "entries": {
                "src/application.py": {"requirements": ["SMD-REQ-1"], "scenarios": ["SMD-SCN-1"]},
            }},
            "git_provenance": {"declared_git_author": "Pessoa <declarada>", "commit": "example-commit"},
        }
        self.workflow = Mock()
        self.workflow.get_review.side_effect = lambda root, trust_path=None: copy.deepcopy(self.proposal)
        self.workflow.check_project.return_value = {"status": "waiting_human_review", "may_complete": False}
        self.workflow.accept_review.return_value = {"status": "accepted_pending_execution"}
        self.patcher = patch("specmd.review_server._workflow", return_value=self.workflow)
        self.patcher.start()
        self.server = build_server(self.root, self.authority, self.trust)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.patcher.stop()
        self.temporary.cleanup()

    def request(self, method, path="/", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode("utf-8")
        connection.close()
        return result

    def accept(self, data=None, headers=None):
        values = {"proposal_id": "version-a", "reviewer": "Pessoa de teste", "read_confirmed": True}
        if data:
            values.update(data)
        request_headers = {
            "Origin": self.server.base_url,
            "X-SpecMD-Review-Token": self.server.review_token,
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)
        return self.request("POST", "/api/accept", json.dumps(values), request_headers)

    def test_get_renders_full_source_diff_metadata_and_escaped_content_without_accepting(self):
        status, headers, body = self.request("GET")
        self.assertEqual(status, 200)
        self.assertIn("Texto integral", body)
        self.assertIn("Texto antigo", body)
        self.assertIn("SMD-REQ-1", body)
        self.assertIn("SMD-SCN-1", body)
        self.assertIn("Justificativa da dispensa proposta", body)
        self.assertIn("schema = 2", body)
        self.assertIn("src/application.py", body)
        self.assertIn("Mapa de rastreabilidade completo", body)
        self.assertIn("Pessoa &lt;declarada&gt;", body)
        self.assertIn("Texto removido &lt;tag&gt;", body)
        self.assertIn("&lt;script&gt;alert(&quot;doc&quot;)&lt;/script&gt;", body)
        self.assertNotIn('<script>alert("doc")</script>', body)
        self.assertNotIn(self.server.review_token, body)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.workflow.accept_review.assert_not_called()
        self.workflow.run_project.assert_not_called()

    def test_token_is_only_in_review_url_fragment_and_script_clears_fragment(self):
        url = urlsplit(self.server.review_url)
        self.assertEqual(url.query, "")
        self.assertEqual(url.fragment, "token=" + self.server.review_token)
        _, _, body = self.request("GET")
        self.assertIn("window.history.replaceState", body)
        self.assertIn("X-SpecMD-Review-Token", body)
        self.assertIn("mesmo usuário", body)

    def test_get_status_does_not_accept_or_expose_token(self):
        status, _, body = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["may_complete"], False)
        self.assertNotIn(self.server.review_token, body)
        self.workflow.check_project.assert_called_once_with(self.root, trust_path=self.trust)
        self.workflow.accept_review.assert_not_called()

    def test_get_cannot_trigger_acceptance(self):
        status, _, _ = self.request("GET", "/api/accept")
        self.assertEqual(status, 404)
        self.workflow.accept_review.assert_not_called()

    def test_missing_or_wrong_token_does_not_accept(self):
        for token in ("", "wrong-token"):
            with self.subTest(token=token):
                status, _, _ = self.accept(headers={"X-SpecMD-Review-Token": token})
                self.assertEqual(status, 403)
        self.workflow.accept_review.assert_not_called()

    def test_cross_site_and_null_origins_do_not_accept(self):
        for origin in ("https://example.invalid", "null", ""):
            with self.subTest(origin=origin):
                status, _, _ = self.accept(headers={"Origin": origin})
                self.assertEqual(status, 403)
        self.workflow.accept_review.assert_not_called()

    def test_dns_rebinding_host_is_rejected_even_with_valid_origin_and_token(self):
        status, _, _ = self.accept(headers={"Host": "attacker.invalid"})
        self.assertEqual(status, 403)
        self.workflow.accept_review.assert_not_called()

    def test_non_json_and_query_token_are_rejected(self):
        status, _, _ = self.accept(headers={"Content-Type": "text/plain"})
        self.assertEqual(status, 415)
        status, _, _ = self.request("GET", "/?token=" + self.server.review_token)
        self.assertEqual(status, 400)
        self.workflow.accept_review.assert_not_called()

    def test_read_declaration_and_reviewer_are_required_without_fabricating_identity(self):
        for values in ({"read_confirmed": False}, {"read_confirmed": 1}, {"reviewer": "  "}):
            with self.subTest(values=values):
                status, _, _ = self.accept(values)
                self.assertEqual(status, 400)
        self.workflow.accept_review.assert_not_called()

    def test_stale_version_returns_conflict_without_accepting(self):
        self.request("GET")
        self.proposal["id"] = "version-b"
        status, _, body = self.accept()
        self.assertEqual(status, 409)
        self.assertIn("mudou", json.loads(body)["error"])
        self.workflow.accept_review.assert_not_called()

    def test_workflow_snapshot_recheck_failure_is_returned_as_conflict(self):
        self.workflow.accept_review.side_effect = ValueError("O contrato mudou durante o aceite.")
        status, _, body = self.accept()
        self.assertEqual(status, 409)
        self.assertIn("mudou", json.loads(body)["error"])

    def test_explicit_acceptance_calls_workflow_for_displayed_version_only(self):
        status, _, body = self.accept({"reviewer": "  Pessoa de teste  "})
        self.assertEqual(status, 200)
        self.workflow.accept_review.assert_called_once_with(
            self.root, "version-a", self.authority, "Pessoa de teste", decision="accept",
        )
        self.assertEqual(json.loads(body)["result"]["status"], "accepted_pending_execution")
        self.assertNotIn(self.server.review_token, body)
        self.workflow.run_project.assert_not_called()

    def test_explicit_rejection_is_not_inferred_as_acceptance(self):
        self.workflow.accept_review.return_value = {"status": "rejected", "may_complete": False}
        status, _, body = self.accept({"decision": "reject"})
        self.assertEqual(status, 200)
        self.workflow.accept_review.assert_called_once_with(
            self.root, "version-a", self.authority, "Pessoa de teste", decision="reject",
        )
        self.assertEqual(json.loads(body)["result"]["status"], "rejected")
        self.workflow.run_project.assert_not_called()

    def test_rejection_controls_require_same_explicit_read_declaration(self):
        status, _, _ = self.accept({"decision": "reject", "read_confirmed": False})
        self.assertEqual(status, 400)
        self.workflow.accept_review.assert_not_called()
        _, _, body = self.request("GET")
        self.assertIn('name="decision" value="reject"', body)

    def test_unknown_decision_does_not_accept(self):
        status, _, _ = self.accept({"decision": "automatic"})
        self.assertEqual(status, 400)
        self.workflow.accept_review.assert_not_called()

    def test_invalid_documents_show_status_without_acceptance_controls(self):
        self.workflow.get_review.side_effect = ValueError("Documentos precisam de classificação <pendente>.")
        self.workflow.check_project.return_value = {"status": "blocked", "may_complete": False}
        status, _, body = self.request("GET")
        self.assertEqual(status, 200)
        self.assertIn("&lt;pendente&gt;", body)
        self.assertNotIn('<form id="accept-form">', body)
        self.workflow.accept_review.assert_not_called()

    def test_public_or_non_literal_listener_is_rejected(self):
        for host in ("0.0.0.0", "192.0.2.1", "::", "example.invalid"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                build_server(self.root, self.authority, self.trust, host=host)


if __name__ == "__main__":
    unittest.main()
