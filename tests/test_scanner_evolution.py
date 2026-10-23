"""Regression tests for opt-in schema 2, source extraction and advisory caches."""

import json
from pathlib import Path
import tempfile
import unittest

from behave.parser import parse_feature

from specmd.config import ConfigError, load_config
from specmd.core import extract_features, inspect_project


def document(body, kind="behavioral", identifier="SMD-DOC-001"):
    reason = '  exemption_reason: "Guia do editor"\n' if kind == "reference" else ""
    return (
        "---\nspecmd:\n  schema: 1\n"
        f"  id: {identifier}\n  kind: {kind}\n{reason}---\n\n{body}"
    )


SIMPLE = """## SMD-REQ-001 — Soma

```gherkin
# language: pt
@SMD-REQ-001
Funcionalidade: Soma
  @SMD-SCN-001
  Cenário: Somar valores
    Dado números 1 e 2
    Então a soma é 3
```
"""

OUTLINE = """## SMD-REQ-001 — Soma

```gherkin
# language: pt
@SMD-REQ-001
Funcionalidade: Soma
  @SMD-SCN-001
  Esquema do Cenário: Somar <n>
    Dado o número <n>
    Então o resultado é <n>
    Exemplos: primeiro conjunto
      | n |
      | 1 |
      | 2 |
    Exemplos: segundo conjunto
      | n |
      | 3 |
```
"""


class SchemaTwoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "specmd.toml"
        self.config.write_text('schema = 2\nproject_id = "example-project"\n', encoding="utf-8")

    def write(self, text, name="contract.md"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def kinds(self, result):
        return {finding["kind"] for finding in result["findings"]}

    def test_supported_schema_two_configuration(self):
        self.config.write_text('''schema = 2
project_id = "example-project"
repository_id = "github.com/example/project"
[[runners]]
id = "python-local"
language = "python"
command = ["python", "worker.py"]
steps = "steps.py"
paths = ["contracts/*.md"]
timeout = 30
[traceability]
map = ".specmd/traceability.json"
policy = "strict"
[evidence]
allow_mock = false
max_age_seconds = 60
''', encoding="utf-8")
        loaded = load_config(self.root)
        self.assertEqual(loaded["schema"], 2)
        self.assertEqual(loaded["runners"][0]["command"], ["python", "worker.py"])
        self.assertFalse(loaded["evidence"]["allow_mock"])
        self.assertEqual(loaded["repository_id"], "github.com/example/project")

    def test_command_arguments_preserve_empty_and_surrounding_whitespace(self):
        self.config.write_text('''schema = 2
project_id = "project"
[[runners]]
id = "custom"
language = "custom"
command = ["python", "-c", " print('literal') ", ""]
''', encoding="utf-8")
        loaded = load_config(self.root)
        self.assertEqual(loaded["runners"][0]["command"][-2:], [" print('literal') ", ""])

    def test_invalid_schema_two_configuration_is_rejected(self):
        base = 'schema = 2\nproject_id = "project"\n'
        cases = [
            'schema = 2\n', 'schema = 2\nproject_id = " "\n',
            base + 'exclusions = []\n', base + 'runners = "python"\n',
            base + 'repository_id = " "\n',
            base + '[[runners]]\nid = "x"\n',
            base + '[[runners]]\nid="x"\nlanguage="python"\nextra=true\n',
            base + '[[runners]]\nid="x"\nlanguage="python"\ncommand=[]\n',
            base + '[[runners]]\nid="x"\nlanguage="python"\ntimeout=true\n',
            base + '[[runners]]\nid="x"\nlanguage="python"\npaths=[1]\n',
            base + '[[runners]]\nid="x"\nlanguage="python"\n[[runners]]\nid="x"\nlanguage="java"\n',
            base + '[traceability]\nmap = []\n',
            base + '[traceability]\npolicy = "guess"\n',
            base + '[traceability]\nexclusions = []\n',
            base + '[evidence]\nallow_mock = "true"\n',
            base + '[evidence]\nmax_age_seconds = 0\n',
            base + '[evidence]\nunknown = true\n',
        ]
        for text in cases:
            with self.subTest(config=text):
                self.config.write_text(text, encoding="utf-8")
                with self.assertRaises(ConfigError):
                    load_config(self.root)
                result = inspect_project(self.root)
                self.assertEqual(result["status"], "error")
                self.assertFalse(result["may_complete"])

    def test_rule_inherits_feature_and_rule_requirement_tags(self):
        source = document("""## SMD-REQ-001 — Acesso
## SMD-REQ-002 — Validação
```gherkin
# language: pt
@SMD-REQ-001
Funcionalidade: Regras
  @SMD-REQ-002
  Regra: Validar operação
    @SMD-SCN-001
    Cenário: Operação válida
      Dado uma entrada válida
      Então a operação é permitida
```
""")
        self.write(source)
        result = inspect_project(self.root)
        self.assertEqual(result["status"], "waiting_human_review")
        scenario = result["documents"][0]["scenarios"][0]
        self.assertEqual(scenario["requirements"], ["SMD-REQ-001", "SMD-REQ-002"])
        self.assertIn("Cenário:", source.splitlines()[scenario["line"] - 1])
        self.assertNotIn("passed", scenario)

    def test_outline_expands_rows_with_unique_concrete_identities(self):
        source = document(OUTLINE)
        self.write(source)
        result = inspect_project(self.root)
        self.assertEqual(result["status"], "waiting_human_review")
        scenarios = result["documents"][0]["scenarios"]
        self.assertEqual([item["id"] for item in scenarios], [
            "SMD-SCN-001:row:1:1", "SMD-SCN-001:row:1:2", "SMD-SCN-001:row:2:1",
        ])
        self.assertEqual({item["template_id"] for item in scenarios}, {"SMD-SCN-001"})
        self.assertEqual(len({item["line"] for item in scenarios}), 3)
        for item in scenarios:
            self.assertIn("|", source.splitlines()[item["line"] - 1])
            self.assertIn("Esquema do Cenário:", source.splitlines()[item["definition_line"] - 1])
        self.assertIn("Somar 3", scenarios[2]["name"])
        self.assertFalse(result["may_complete"])

    def test_outline_inside_rule_keeps_requirement_inheritance(self):
        body = """## SMD-REQ-001 — Acesso
## SMD-REQ-002 — Regra
```gherkin
# language: pt
@SMD-REQ-001
Funcionalidade: Regras
  @SMD-REQ-002
  Regra: Valores
    @SMD-SCN-001
    Esquema do Cenário: Valor <n>
      Dado o valor <n>
      Então o valor é válido
      Exemplos:
        | n |
        | 1 |
```
"""
        self.write(document(body))
        result = inspect_project(self.root)
        self.assertEqual(result["status"], "waiting_human_review")
        self.assertEqual(result["documents"][0]["scenarios"][0]["requirements"], ["SMD-REQ-001", "SMD-REQ-002"])

    def test_empty_outline_examples_do_not_satisfy_a_requirement(self):
        for body in [
            OUTLINE.split("    Exemplos:")[0].split("    Exemplos: primeiro conjunto")[0] + "```\n",
            OUTLINE.replace("      | 1 |\n", "").replace("      | 2 |\n", "").replace("      | 3 |\n", ""),
        ]:
            with self.subTest(body=body):
                self.write(document(body))
                result = inspect_project(self.root)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("scenarios_missing", self.kinds(result))
                self.assertIn("requirement_uncovered", self.kinds(result))

    def test_outline_template_cannot_reuse_a_simple_scenario_identity(self):
        self.write(document(SIMPLE + OUTLINE.replace("## SMD-REQ-001 — Soma\n", "")))
        result = inspect_project(self.root)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("scenario_id_duplicate", self.kinds(result))

    def test_reference_cannot_hide_explicit_requirements_or_gherkin(self):
        for body in ("## SMD-REQ-001 — Regra\n", SIMPLE):
            with self.subTest(body=body):
                self.write(document(body, kind="reference"))
                result = inspect_project(self.root)
                self.assertEqual(result["status"], "blocked")
                self.assertIn("classification_conflict", self.kinds(result))

    def test_extract_features_preserves_source_lines_and_creates_no_feature_file(self):
        source = document(SIMPLE)
        self.write(source)
        inspection = inspect_project(self.root)
        blocks = extract_features(self.root, inspection)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["path"], "contract.md")
        self.assertEqual(blocks[0]["content"].splitlines()[blocks[0]["line"] - 1], "# language: pt")
        feature = parse_feature(blocks[0]["content"], filename=blocks[0]["path"])
        self.assertIn("Cenário:", source.splitlines()[feature.scenarios[0].line - 1])
        self.assertEqual(list(self.root.rglob("*.feature")), [])

    def test_extract_features_rejects_stale_content_or_inventory(self):
        self.write(document(SIMPLE))
        inspection = inspect_project(self.root)
        self.write(document("Informação\n", kind="reference", identifier="SMD-DOC-002"), "new.md")
        with self.assertRaises(ValueError):
            extract_features(self.root, inspection)
        inspection = inspect_project(self.root)
        self.write(document(SIMPLE + "\nTexto alterado.\n"))
        with self.assertRaises(ValueError):
            extract_features(self.root, inspection)

    def test_default_scan_does_not_create_cache(self):
        self.write(document(SIMPLE))
        inspect_project(self.root)
        self.assertFalse((self.root / ".specmd").exists())

    def test_advisory_cache_cannot_remove_validation_errors(self):
        self.write(document("## SMD-REQ-001 — Sem cenário\n"))
        initial = inspect_project(self.root, use_cache=True)
        cache_files = list((self.root / ".specmd" / "cache").glob("*.json"))
        self.assertEqual(len(cache_files), 1)
        payload = json.loads(cache_files[0].read_text(encoding="utf-8"))
        payload["findings"] = []
        payload["authority"] = True
        payload["document"]["requirements"] = []
        cache_files[0].write_text(json.dumps(payload), encoding="utf-8")
        observed = inspect_project(self.root, use_cache=True)
        self.assertEqual(observed, initial)
        self.assertEqual(observed["status"], "blocked")
        self.assertIn("gherkin_missing", self.kinds(observed))
        self.assertFalse(json.loads(cache_files[0].read_text(encoding="utf-8"))["authority"])

    def test_corrupt_cache_is_repaired_without_changing_scan(self):
        self.write(document(SIMPLE))
        initial = inspect_project(self.root, use_cache=True)
        cache_file = next((self.root / ".specmd" / "cache").glob("*.json"))
        cache_file.write_text("not JSON", encoding="utf-8")
        self.assertEqual(inspect_project(self.root, use_cache=True), initial)
        self.assertEqual(json.loads(cache_file.read_text(encoding="utf-8"))["schema"], 1)

    def test_cache_key_changes_with_source_content(self):
        self.write(document(SIMPLE))
        before = inspect_project(self.root, use_cache=True)
        self.write(document(SIMPLE + "\nContexto adicional.\n"))
        after = inspect_project(self.root, use_cache=True)
        self.assertNotEqual(before["manifest_sha256"], after["manifest_sha256"])
        self.assertEqual(len(list((self.root / ".specmd" / "cache").glob("*.json"))), 2)

    def test_cache_does_not_write_through_a_symlink(self):
        self.write(document(SIMPLE))
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside)
            try:
                (self.root / ".specmd").symlink_to(target, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("Symlinks indisponíveis nesta plataforma")
            result = inspect_project(self.root, use_cache=True)
            self.assertEqual(result["status"], "waiting_human_review")
            self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
