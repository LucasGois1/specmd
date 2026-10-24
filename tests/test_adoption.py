"""Legacy adoption starts from the existing documentation (SMD-REQ-030)."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from specmd import hooks, workflow
from specmd.cli import main
from specmd.demo import create_demo

REPOSITORY = Path(__file__).resolve().parents[1]
COVERED = "## LEG-REQ-002 — Coberto\n\n```gherkin\nFeature: B\n  Scenario: Coberto\n    Given um passo\n```\n"
DISCOUNT = """
## CART-REQ-003 — Desconto

```gherkin
# language: pt
Funcionalidade: Desconto

  Cenário: Desconto acima de 1000 centavos
    Dado um carrinho vazio
    Quando eu adicionar itens de 600 e 500 centavos
    Então o total deve ser 990 centavos
```
"""


class AdoptionListTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-adopt-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for path, content in {
            "README.md": "# Projeto\n",
            "docs/setup.md": "# Setup\n",
            "docs/time.md": "# Notas do time\n",
            "docs/estornos.md": "# Estornos\n\nPagamentos podem ser estornados em até 7 dias.\n",
            "docs/cobranca.md": "## LEG-REQ-001 — Sem cenário\n\nTexto.\n\n" + COVERED,
            "docs/pronto.md": "## LEG-REQ-003 — Pronto\n\n```gherkin\nFeature: C\n  Scenario: Pronto\n    Given um passo\n```\n",
            ".specmdignore": "docs/time.md\n",
        }.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def adopt(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["adopt", "--root", str(self.root)])
        return code, json.loads(output.getvalue())

    def test_lists_every_document_without_scenarios_in_path_order(self):  # SMD-SCN-130
        code, result = self.adopt()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "adoption")
        self.assertEqual([item["path"] for item in result["pending"]],
                         ["docs/cobranca.md", "docs/estornos.md", "docs/setup.md"])
        self.assertEqual(result["pending"][0]["requirements_without_scenarios"], ["LEG-REQ-001"])
        self.assertEqual((result["documents"], result["documented"]), (4, 2))

    def test_documents_the_developer_ignores_leave_the_list(self):  # SMD-SCN-131
        (self.root / ".specmdignore").write_text("docs/time.md\ndocs/setup.md\n", encoding="utf-8")
        self.assertNotIn("docs/setup.md", [item["path"] for item in self.adopt()[1]["pending"]])

    def test_the_command_guides_one_document_at_a_time(self):  # SMD-SCN-132
        text = (REPOSITORY / "commands/adopt.md").read_text(encoding="utf-8")
        for expected in ("specmd_cli.py\" adopt", "Trate um documento por vez", "só siga depois da confirmação",
                         "Grave no `.specmdignore`", "Não corrija sozinho", "Marcar cenários com `@wip` é decisão do dev"):
            self.assertIn(expected, text)


class DivergenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-divergence-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        environment = patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)

    def hook(self, event):
        return hooks.handle_hook({"hook_event_name": event})

    def test_new_scenario_contradicting_existing_code_suggests_asking_the_dev(self):  # SMD-SCN-133
        self.assertTrue(workflow.run_project(self.root)["run"]["passed"])
        with (self.root / "docs/cart.md").open("a", encoding="utf-8") as stream:
            stream.write(DISCOUNT)
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")
        (self.root / "app.py").write_text((self.root / "app.py").read_text() + "\n# revisado\n")
        reason = self.hook("Stop")["reason"]
        self.assertIn('1 cenário nunca passou ("Desconto acima de 1000 centavos")', reason)
        self.assertIn("é divergência entre documentação e código: pergunte ao dev qual vale antes de mudar "
                      "qualquer um dos dois", reason)

    def test_regression_in_a_scenario_that_passed_has_no_divergence_hint(self):
        self.assertTrue(workflow.run_project(self.root)["run"]["passed"])
        app = self.root / "app.py"
        app.write_text(app.read_text().replace("sum(self.prices)", "sum(self.prices) + 1"))
        run = workflow.run_project(self.root)["run"]
        self.assertEqual(run["never_passed"], [])
        self.assertNotIn("divergência", hooks._format_failures(run))


if __name__ == "__main__":
    unittest.main()
