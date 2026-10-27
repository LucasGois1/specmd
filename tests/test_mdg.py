"""Markdown with Gherkin files are read line for line (SMD-REQ-031).

The fixtures are in Portuguese on purpose: they exercise `gherkin_language`.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest

from specmd import mdg, workflow
from specmd.core import _REQUIREMENT_HEADING, inspect_project
from specmd.runner import _features

DOCUMENT = """# Funcionalidade: Estornos

Prosa explicando a regra, com um [link](https://example.com).

## Regra: PAG-REQ-001 — Estorno em até 7 dias

Um pagamento pode ser estornado em até 7 dias corridos.

`@rapido`
### Cenário: Estorno no sexto dia
* Dado um pagamento feito há 6 dias
* Quando o cliente pedir o estorno
* Então o estorno deve ser aprovado

### Esquema do Cenário: Prazo
* Dado um pagamento feito há <dias> dias
* Quando o cliente pedir o estorno
* Então o estorno deve ser <resultado>

#### Exemplos:

  | dias | resultado |
  | ---- | --------- |
  | 7    | aprovado  |
  | 8    | recusado  |

## PAG-REQ-002 — Mensagem

```
Um exemplo em prosa, não é cenário.
```

### Cenário: Mensagem do estorno
* Dado a mensagem
  ```
  Estorno aprovado
  ```
* Então a mensagem contém "aprovado"
"""
STEPS = '''from behave import given, then, when

from estornos import pode_estornar


@given("um pagamento feito há {dias:d} dias")
def payment(context, dias):
    context.dias = dias


@when("o cliente pedir o estorno")
def ask(context):
    context.ok = pode_estornar(context.dias)


@then("o estorno deve ser aprovado")
def approved(context):
    assert context.ok


@then("o estorno deve ser recusado")
def refused(context):
    assert not context.ok


@given("a mensagem")
def message(context):
    context.mensagem = context.text


@then('a mensagem contém "{texto}"')
def contains(context, texto):
    assert texto in context.mensagem, context.mensagem
'''


class ConversionTests(unittest.TestCase):
    def test_lines_are_preserved_and_prose_disappears(self):
        converted = mdg.convert(DOCUMENT, "pt", _REQUIREMENT_HEADING)
        lines = converted.text.splitlines()
        self.assertEqual(len(lines), len(DOCUMENT.splitlines()))
        self.assertEqual(lines[0], "# language: pt")
        self.assertEqual(lines[1], "Funcionalidade: Estornos")
        self.assertEqual(lines[2], "")  # prose
        self.assertEqual(lines[8], "@rapido")
        self.assertEqual(lines[9], "Cenário: Estorno no sexto dia")
        self.assertEqual(lines[10], "Dado um pagamento feito há 6 dias")
        self.assertEqual((lines[21], lines[22], lines[23]), ("| dias | resultado |", "", "| 7    | aprovado  |"))
        self.assertEqual(lines[29], "")  # fenced block in prose is not a doc string
        self.assertEqual((lines[34], lines[35], lines[36]), ('"""', "  Estorno aprovado", '"""'))
        self.assertEqual([item["id"] for item in converted.requirements], ["PAG-REQ-001", "PAG-REQ-002"])

    def test_unindented_tables_and_unknown_list_items_are_prose(self):
        converted = mdg.convert("# Feature: X\n\n## Scenario: Y\n* Given a\n- not a step\n| a |\n", None, _REQUIREMENT_HEADING)
        self.assertEqual(converted.text.splitlines()[3:], ["Given a", "", ""])

    def test_without_feature_heading_the_first_line_names_it(self):
        converted = mdg.convert("Cálculo de frete\n\n## Scenario: Y\n* Given a\n", None, _REQUIREMENT_HEADING)
        self.assertEqual(converted.text.splitlines()[0], "Feature: Cálculo de frete")


class MarkdownWithGherkinTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-mdg-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for path, content in {"specmd.toml": 'gherkin_language = "pt"\n', "docs/estornos.feature.md": DOCUMENT,
                              "tests/steps/estornos_steps.py": STEPS,
                              "estornos.py": "def pode_estornar(dias):\n    return dias <= 7\n"}.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def scenarios(self):
        report = inspect_project(self.root)
        self.assertEqual(report["status"], "ready", report["findings"])
        return {item["name"]: item for item in report["documents"][0]["scenarios"]}

    def test_mdg_document_runs_with_origin_in_the_markdown(self):  # SMD-SCN-134
        run = workflow.run_project(self.root)["run"]
        self.assertTrue(run["passed"], run)
        self.assertEqual(run["scenarios"], 4)
        self.assertEqual(self.scenarios()["Estorno no sexto dia"]["line"], 10)
        self.assertFalse(list(self.root.rglob("*.feature")))
        (self.root / "estornos.py").write_text("def pode_estornar(dias):\n    return dias <= 10\n")
        failures = workflow.run_project(self.root)["run"]["failures"]
        self.assertEqual([(item["path"], item["line"]) for item in failures], [("docs/estornos.feature.md", 25)])

    def test_rule_with_an_identifier_is_a_requirement(self):  # SMD-SCN-135
        scenarios = self.scenarios()
        self.assertEqual(scenarios["Estorno no sexto dia"]["requirements"], ["PAG-REQ-001"])
        self.assertEqual(scenarios["Mensagem do estorno"]["requirements"], ["PAG-REQ-002"])
        self.assertIn("rapido", scenarios["Estorno no sexto dia"]["tags"])

    def test_fenced_block_after_a_step_is_its_doc_string(self):  # SMD-SCN-136
        (self.root / "docs/estornos.feature.md").write_text(DOCUMENT.replace('contém "aprovado"', 'contém "recusado"'))
        failures = workflow.run_project(self.root)["run"]["failures"]
        self.assertEqual([item["name"] for item in failures], ["Mensagem do estorno"])
        self.assertIn("Estorno aprovado", failures[0]["steps"][0]["error"])

    def test_missing_language_is_pointed_out(self):  # SMD-SCN-137
        (self.root / "specmd.toml").write_text("")
        report = inspect_project(self.root)
        messages = [item["message"] for item in report["findings"] if item["kind"] == "gherkin_missing"]
        self.assertEqual(len(messages), 1)
        self.assertIn("the language comes from `gherkin_language` in specmd.toml", messages[0])

    def test_bridges_receive_the_configured_language_in_the_text(self):
        (self.root / "docs/estornos.feature.md").unlink()
        (self.root / "docs/regras.md").write_text("# Regras\n\n```gherkin\nFuncionalidade: R\n  Cenário: C\n    Dado um passo\n```\n")
        inspection = inspect_project(self.root)
        self.assertEqual(inspection["status"], "ready", inspection["findings"])
        feature = _features(self.root, inspection, language="pt")[0][0]
        self.assertEqual((feature["line"], feature["content"].splitlines()[0]), (3, "# language: pt"))

    def test_fenced_gherkin_in_another_language_gets_a_hint(self):
        (self.root / "specmd.toml").write_text("")
        (self.root / "docs/estornos.feature.md").unlink()
        (self.root / "docs/regras.md").write_text("```gherkin\nFuncionalidade: R\n  Cenário: C\n    Dado um passo\n```\n")
        messages = [item["message"] for item in inspect_project(self.root)["findings"]]
        self.assertTrue(any("declare `# language: <code>`" in message for message in messages), messages)


if __name__ == "__main__":
    unittest.main()
