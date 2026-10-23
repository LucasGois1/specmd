"""Behavioral tests for read-only document inspection and fail-closed status."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from specmd.core import inspect_project


def reference(document_id: str = "SMD-TST-DOC-001", reason: str = "Contexto da equipe.") -> str:
    return (
        "---\nspecmd:\n  schema: 1\n"
        f"  id: {document_id}\n  kind: reference\n"
        f"  exemption_reason: {reason!r}\n---\n\n# Referência\n\nContexto.\n"
    )


def behavioral(
    document_id: str = "SMD-TST-DOC-001",
    requirement_id: str = "SMD-TST-REQ-001",
    scenario_id: str = "SMD-TST-SCN-001",
    *,
    kind: str = "behavioral",
) -> str:
    return (
        "---\nspecmd:\n  schema: 1\n"
        f"  id: {document_id}\n  kind: {kind}\n---\n\n"
        f"# Contrato\n\n## {requirement_id} — Soma\n\n"
        "A soma deve preservar os valores especificados.\n\n"
        "```gherkin\n# language: pt\n"
        f"@{requirement_id}\nFuncionalidade: Somar valores\n\n"
        f"  @{scenario_id}\n  Cenário: Somar dois números\n"
        "    Dado os números 2 e 3\n"
        "    Quando a soma for calculada\n"
        "    Então o resultado deve ser 5\n```\n"
    )


class InspectProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="specmd-core-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def activate(self, text: str = "schema = 1\n") -> None:
        (self.root / "specmd.toml").write_text(text, encoding="utf-8")

    def write(self, path: str, content: str | bytes) -> Path:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")
        return target

    def report(self) -> dict:
        return inspect_project(self.root)

    def document(self, report: dict, path: str = "contract.md") -> dict:
        return next(item for item in report["documents"] if item["path"] == path)

    def assert_blocked(self, report: dict, kind: str | None = None) -> None:
        self.assertEqual(report["status"], "blocked", report)
        self.assertIs(report["may_complete"], False)
        self.assertTrue(report["findings"])
        if kind is not None:
            self.assertIn(kind, {finding["kind"] for finding in report["findings"]}, report)

    def assert_pending(self, report: dict) -> None:
        self.assertEqual(report["protocol_version"], 1)
        self.assertEqual(report["stage"], "completion")
        self.assertEqual(report["status"], "waiting_human_review", report)
        self.assertIs(report["may_complete"], False)
        kinds = {finding["kind"] for finding in report["findings"]}
        self.assertIn("authority_not_configured", kinds)
        self.assertIn("evidence_not_executed", kinds)

    def test_no_configuration_is_inactive_without_inspecting_documents(self) -> None:
        self.write("unknown.md", "# Sem classificação\n")
        report = self.report()
        self.assertEqual(report["status"], "inactive")
        self.assertIsNone(report["may_complete"])
        self.assertEqual(report["documents"], [])
        self.assertEqual(report["findings"], [])

    def test_invalid_configuration_fails_closed(self) -> None:
        for config in ("schema = 2\n", "schema = true\n", "schema = [\n", ""):
            with self.subTest(config=config):
                self.activate(config)
                report = self.report()
                self.assertEqual(report["status"], "error", report)
                self.assertIs(report["may_complete"], False)

    def test_configuration_cannot_add_exclusions(self) -> None:
        self.activate('schema = 1\nexclude = ["**/*.md"]\n')
        self.write("hidden.md", "# Requisito sem classificação\n")
        report = self.report()
        self.assertEqual(report["status"], "error", report)
        self.assertIs(report["may_complete"], False)

    def test_configuration_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="specmd-config-outside-") as outside:
            target = Path(outside) / "specmd.toml"
            target.write_text("schema = 1\n", encoding="utf-8")
            (self.root / "specmd.toml").symlink_to(target)
            report = self.report()
        self.assertEqual(report["status"], "error", report)
        self.assertIs(report["may_complete"], False)
        self.assertIn("config_symlink", {finding["kind"] for finding in report["findings"]})

    def test_valid_behavior_is_parsed_but_never_approved_or_executed(self) -> None:
        self.activate()
        self.write("contract.md", behavioral())
        report = self.report()
        self.assert_pending(report)
        document = self.document(report)
        self.assertEqual(document["id"], "SMD-TST-DOC-001")
        self.assertEqual(document["kind"], "behavioral")
        self.assertEqual(len(document["requirements"]), 1)
        self.assertEqual(len(document["scenarios"]), 1)
        self.assertEqual(document["scenarios"][0]["id"], "SMD-TST-SCN-001")
        self.assertNotEqual(document["scenarios"][0].get("status"), "passed")

    def test_reference_classification_does_not_confer_human_acceptance(self) -> None:
        self.activate()
        self.write("guide.md", reference())
        report = self.report()
        self.assert_pending(report)
        document = self.document(report, "guide.md")
        self.assertEqual(document["kind"], "reference")
        self.assertEqual(document["scenarios"], [])
        self.assertNotEqual(document.get("approval_status"), "approved")

    def test_frontmatter_cannot_self_approve(self) -> None:
        self.activate()
        content = reference().replace("  kind: reference\n", "  kind: reference\n  approved: true\n")
        self.write("guide.md", content)
        report = self.report()
        self.assertIs(report["may_complete"], False)
        self.assertNotEqual(report["status"], "completed")
        self.assertTrue(report["findings"])

    def test_reference_requires_nonempty_exemption_reason(self) -> None:
        self.activate()
        for content in (
            reference().replace("  exemption_reason: 'Contexto da equipe.'\n", ""),
            reference(reason=""),
            reference(reason="   "),
        ):
            with self.subTest(content=content):
                self.write("guide.md", content)
                self.assert_blocked(self.report())

    def test_unclassified_new_document_blocks_and_is_in_inventory(self) -> None:
        self.activate()
        self.write("new.md", "# Uma regra ainda não classificada\n")
        report = self.report()
        self.assert_blocked(report, "frontmatter_missing")
        self.assertEqual([item["path"] for item in report["documents"]], ["new.md"])

    def test_missing_or_invalid_metadata_blocks(self) -> None:
        self.activate()
        samples = (
            "# Sem frontmatter\n",
            "---\nother: true\n---\n# Sem specmd\n",
            behavioral().replace("  schema: 1\n", "  schema: true\n"),
            behavioral().replace("  id: SMD-TST-DOC-001\n", "  id: 17\n"),
            behavioral().replace("  kind: behavioral\n", "  kind: unknown\n"),
        )
        for content in samples:
            with self.subTest(content=content[:120]):
                self.write("contract.md", content)
                self.assert_blocked(self.report())

    def test_duplicate_yaml_keys_are_rejected(self) -> None:
        self.activate()
        content = reference().replace("  kind: reference\n", "  kind: behavioral\n  kind: reference\n")
        self.write("guide.md", content)
        self.assert_blocked(self.report(), "frontmatter_invalid")

    def test_non_string_classification_is_reported_without_type_error(self) -> None:
        self.activate()
        for value in ("[]", "{}"):
            with self.subTest(value=value):
                self.write("contract.md", behavioral().replace("  kind: behavioral\n", f"  kind: {value}\n"))
                self.assert_blocked(self.report(), "metadata_invalid")

    def test_invalid_utf8_is_reported_without_exception(self) -> None:
        self.activate()
        self.write("broken.md", b"# Documento\n\xff\n")
        self.assert_blocked(self.report(), "invalid_utf8")

    def test_case_insensitive_extensions_and_sorted_paths(self) -> None:
        self.activate()
        self.write("z.MD", reference("SMD-TST-DOC-003"))
        self.write("nested/b.MarkDown", reference("SMD-TST-DOC-002"))
        self.write("a.md", reference("SMD-TST-DOC-001"))
        self.write("ignored.txt", "# Nao é Markdown\n")
        report = self.report()
        self.assert_pending(report)
        self.assertEqual(
            [item["path"] for item in report["documents"]],
            ["a.md", "nested/b.MarkDown", "z.MD"],
        )

    def test_fixed_generated_and_dependency_directories_are_pruned(self) -> None:
        self.activate()
        self.write("guide.md", reference())
        for folder in (".git", ".venv", "venv", "node_modules", "target", "__pycache__", ".specmd"):
            self.write(f"{folder}/malformed.md", "# Não deve ser interpretado\n")
        report = self.report()
        self.assert_pending(report)
        self.assertEqual([item["path"] for item in report["documents"]], ["guide.md"])

    def test_exact_bytes_are_hashed_including_line_endings(self) -> None:
        self.activate()
        content = reference().encode("utf-8")
        target = self.write("guide.md", content)
        before = self.report()
        self.assertEqual(self.document(before, "guide.md")["sha256"], hashlib.sha256(content).hexdigest())
        target.write_bytes(content.replace(b"\n", b"\r\n"))
        after = self.report()
        self.assertNotEqual(before["manifest_sha256"], after["manifest_sha256"])

    def test_repeated_inspection_is_deterministic_and_read_only(self) -> None:
        self.activate()
        self.write("contract.md", behavioral())
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        first = self.report()
        second = self.report()
        after = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual(len(first["manifest_sha256"]), 64)

    def test_reference_content_change_invalidates_content_identity(self) -> None:
        self.activate()
        target = self.write("guide.md", reference())
        before = self.report()
        target.write_text(reference() + "\nNovo contexto.\n", encoding="utf-8")
        after = self.report()
        self.assertNotEqual(before["manifest_sha256"], after["manifest_sha256"])
        self.assert_pending(after)

    def test_new_removed_and_renamed_documents_change_manifest(self) -> None:
        self.activate()
        first = self.write("first.md", reference())
        original = self.report()
        second = self.write("second.md", reference("SMD-TST-DOC-002"))
        added = self.report()
        self.assertNotEqual(original["manifest_sha256"], added["manifest_sha256"])
        second.unlink()
        removed = self.report()
        self.assertEqual(original["manifest_sha256"], removed["manifest_sha256"])
        first.rename(self.root / "renamed.md")
        renamed = self.report()
        self.assertNotEqual(original["manifest_sha256"], renamed["manifest_sha256"])
        self.assertEqual(
            self.document(original, "first.md")["sha256"],
            self.document(renamed, "renamed.md")["sha256"],
        )

    def test_configuration_bytes_participate_in_manifest_identity(self) -> None:
        self.activate("schema=1\n")
        self.write("guide.md", reference())
        before = self.report()
        self.activate("schema = 1\n")
        after = self.report()
        self.assertNotEqual(before["manifest_sha256"], after["manifest_sha256"])

    def test_manifest_uses_canonical_utf8_json_and_exact_relative_paths(self) -> None:
        config = "schema = 1\n"
        content = reference().encode("utf-8")
        self.activate(config)
        self.write("docs/café.md", content)
        report = self.report()
        expected = {
            "schema": 1,
            "config_sha256": hashlib.sha256(config.encode("utf-8")).hexdigest(),
            "documents": [{"path": "docs/café.md", "sha256": hashlib.sha256(content).hexdigest()}],
        }
        encoded = json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(report["manifest"], expected)
        self.assertEqual(report["manifest_sha256"], hashlib.sha256(encoded).hexdigest())

    def test_manifest_is_independent_of_creation_order_and_absolute_root(self) -> None:
        self.activate()
        files = {
            "a.md": reference("SMD-TST-DOC-001"),
            "nested/z.md": reference("SMD-TST-DOC-002"),
        }
        for name in reversed(list(files)):
            self.write(name, files[name])
        first = self.report()
        with tempfile.TemporaryDirectory(prefix="specmd-other-root-") as other:
            second_root = Path(other)
            (second_root / "specmd.toml").write_text("schema = 1\n", encoding="utf-8")
            for name, content in files.items():
                target = second_root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            second = inspect_project(second_root)
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])

    def test_duplicate_document_ids_block(self) -> None:
        self.activate()
        self.write("first.md", reference())
        self.write("second.md", reference())
        self.assert_blocked(self.report(), "document_id_duplicate")

    def test_duplicate_requirement_ids_block(self) -> None:
        self.activate()
        content = behavioral().replace(
            "A soma deve preservar os valores especificados.",
            "## SMD-TST-REQ-001 — Outra declaração\n\nA soma deve preservar os valores especificados.",
        )
        self.write("contract.md", content)
        self.assert_blocked(self.report(), "requirement_id_duplicate")

    def test_duplicate_scenario_ids_block_across_documents(self) -> None:
        self.activate()
        self.write("first.md", behavioral())
        self.write(
            "second.md",
            behavioral("SMD-TST-DOC-002", "SMD-TST-REQ-002", "SMD-TST-SCN-001"),
        )
        self.assert_blocked(self.report(), "scenario_id_duplicate")

    def test_requirement_without_scenario_blocks(self) -> None:
        self.activate()
        self.write("contract.md", behavioral() + "\n## SMD-TST-REQ-002 — Sem cenário\n\nOutra regra.\n")
        self.assert_blocked(self.report(), "requirement_uncovered")

    def test_scenario_referencing_undeclared_requirement_blocks(self) -> None:
        self.activate()
        self.write("contract.md", behavioral().replace("@SMD-TST-REQ-001", "@SMD-TST-REQ-999"))
        self.assert_blocked(self.report(), "requirement_unknown")

    def test_scenario_requires_stable_id(self) -> None:
        self.activate()
        self.write("contract.md", behavioral().replace("  @SMD-TST-SCN-001\n", ""))
        self.assert_blocked(self.report(), "scenario_id_missing")

    def test_scenario_id_cannot_be_inherited_from_feature(self) -> None:
        self.activate()
        content = behavioral().replace(
            "@SMD-TST-REQ-001\nFuncionalidade",
            "@SMD-TST-REQ-001 @SMD-TST-SCN-001\nFuncionalidade",
        ).replace("  @SMD-TST-SCN-001\n", "")
        self.write("contract.md", content)
        self.assert_blocked(self.report(), "scenario_id_missing")

    def test_requirement_tag_can_be_local_to_scenario(self) -> None:
        self.activate()
        content = behavioral().replace("@SMD-TST-REQ-001\nFuncionalidade", "Funcionalidade")
        content = content.replace("  @SMD-TST-SCN-001", "  @SMD-TST-REQ-001 @SMD-TST-SCN-001")
        self.write("contract.md", content)
        report = self.report()
        self.assert_pending(report)
        self.assertEqual(
            self.document(report)["scenarios"][0]["requirements"],
            ["SMD-TST-REQ-001"],
        )

    def test_scenario_without_requirement_link_blocks(self) -> None:
        self.activate()
        self.write("contract.md", behavioral().replace("@SMD-TST-REQ-001\n", ""))
        self.assert_blocked(self.report(), "requirement_missing")

    def test_behavioral_document_requires_gherkin(self) -> None:
        self.activate()
        self.write("contract.md", behavioral().split("```gherkin", 1)[0])
        self.assert_blocked(self.report(), "gherkin_missing")

    def test_syntactically_invalid_gherkin_blocks(self) -> None:
        self.activate()
        self.write("contract.md", behavioral().replace("    Então o resultado deve ser 5\n", "    Então o resultado deve ser 5\n    texto inválido depois dos passos\n"))
        self.assert_blocked(self.report(), "gherkin_invalid")

    def test_feature_with_zero_scenarios_blocks(self) -> None:
        self.activate()
        prefix = behavioral().split("```gherkin", 1)[0]
        self.write("contract.md", prefix + "```gherkin\n# language: pt\nFuncionalidade: Sem cenários\n```\n")
        self.assert_blocked(self.report(), "scenarios_missing")

    def test_outline_is_rejected_explicitly_when_not_supported(self) -> None:
        self.activate()
        content = behavioral().replace("Cenário: Somar dois números", "Esquema do Cenário: Somar dois números")
        self.write("contract.md", content)
        self.assert_blocked(self.report(), "gherkin_unsupported")

    def test_literal_markdown_example_does_not_declare_requirement(self) -> None:
        self.activate()
        content = behavioral() + "\n```markdown\n## SMD-TST-REQ-999 — Apenas exemplo literal\n```\n"
        self.write("contract.md", content)
        self.assert_pending(self.report())

    def test_multiple_blocks_preserve_original_markdown_lines(self) -> None:
        self.activate()
        first = behavioral()
        second = (
            "\n## SMD-TST-REQ-002 — Outro exemplo\n\n"
            "```gherkin\n# language: pt\n@SMD-TST-REQ-002\n"
            "Funcionalidade: Outra soma\n"
            "  @SMD-TST-SCN-002\n  Cenário: Somar valores maiores\n"
            "    Dado os números 4 e 5\n"
            "    Quando a soma for calculada\n"
            "    Então o resultado deve ser 9\n```\n"
        )
        source = first + second
        self.write("contract.md", source)
        report = self.report()
        self.assert_pending(report)
        scenarios = self.document(report)["scenarios"]
        self.assertEqual(len(scenarios), 2)
        for scenario in scenarios:
            self.assertIn("Cenário:", source.splitlines()[scenario["line"] - 1])

    def test_mixed_document_can_include_reference_prose(self) -> None:
        self.activate()
        self.write("contract.md", behavioral(kind="mixed") + "\n## Contexto\n\nInformação adicional.\n")
        self.assert_pending(self.report())

    def test_symlinked_markdown_is_rejected_without_following(self) -> None:
        self.activate()
        with tempfile.TemporaryDirectory(prefix="specmd-outside-") as outside:
            external = Path(outside) / "external.md"
            external.write_text(reference(), encoding="utf-8")
            (self.root / "linked.md").symlink_to(external)
            report = self.report()
        self.assert_blocked(report, "symlink")
        self.assertTrue(any(item.get("path") == "linked.md" for item in report["findings"]))

    def test_symlinked_directory_is_rejected_without_discovering_external_files(self) -> None:
        self.activate()
        with tempfile.TemporaryDirectory(prefix="specmd-outside-dir-") as outside:
            external = Path(outside)
            (external / "external.md").write_text(reference(), encoding="utf-8")
            (self.root / "linked-dir").symlink_to(external, target_is_directory=True)
            report = self.report()
        self.assert_blocked(report, "symlink")
        self.assertFalse(any(item["path"].startswith("linked-dir/") for item in report["documents"]))
        self.assertTrue(any(item.get("path") == "linked-dir" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
