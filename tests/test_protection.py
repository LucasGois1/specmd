"""Confirmed scenarios are protected and ignored documents that gain rules are reported."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from specmd import hooks
from specmd.demo import create_demo

SECOND_REQUIREMENT = """## CART-REQ-002 — Carrinho vazio

Um carrinho sem itens deve ter total de zero centavos.

```gherkin
# language: pt
Funcionalidade: Carrinho vazio

  Cenário: Consultar um carrinho vazio
    Dado um carrinho vazio
    Quando eu consultar o total do carrinho
    Então o total deve ser 0 centavos
```
"""


class HookCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="specmd-protection-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "cart"
        create_demo(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        environment = patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)
        self.hook("SessionStart")
        self.hook("UserPromptSubmit")

    def hook(self, event, **extra):
        return hooks.handle_hook({"hook_event_name": event, **extra})

    def edit(self, path, old, new):
        target = self.root / path
        text = target.read_text()
        self.assertIn(old, text)
        target.write_text(text.replace(old, new))

    def after_edit(self, path):
        reply = self.hook("PostToolUse", tool_name="Edit", tool_input={"file_path": str(self.root / path)})
        return reply.get("hookSpecificOutput", {}).get("additionalContext", "")


class ProtectedScenarioTests(HookCase):
    def test_changed_expectation_reaches_the_agent_and_the_developer(self):  # SMD-SCN-123
        self.edit("docs/cart.md", "Então o total deve ser 500 centavos", "Então o total deve ser 510 centavos")
        line = 'docs/cart.md:14 "Somar dois itens" — Então o total deve ser 500 centavos → Então o total deve ser 510 centavos'
        self.assertIn(line, self.after_edit("docs/cart.md"))
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 5)")
        reply = self.hook("Stop")
        self.assertNotIn("decision", reply)
        self.assertIn("cenários alterados nesta resposta", reply["systemMessage"])
        self.assertIn(line, reply["systemMessage"])
        self.assertIn("2 cenários passando", reply["systemMessage"])

    def test_only_the_changed_steps_are_shown(self):
        self.edit("docs/cart.md", "itens de 200 e 300 centavos\n    Então o total deve ser 500",
                  "itens de 200 e 310 centavos\n    Então o total deve ser 510")
        context = self.after_edit("docs/cart.md")
        self.assertIn('"Somar dois itens" — Então o total deve ser 500 centavos → Então o total deve ser 510 centavos; '
                      "Quando eu adicionar itens de 200 e 300 centavos → Quando eu adicionar itens de 200 e 310 centavos",
                      context)
        self.assertNotIn("Dado um carrinho vazio", context)

    def test_removed_scenario_wip_tag_and_removed_requirement(self):  # SMD-SCN-124
        self.edit("docs/cart.md", SECOND_REQUIREMENT, "")
        self.edit("docs/cart.md", "  Cenário: Somar dois itens", "  @wip\n  Cenário: Somar dois itens")
        context = self.after_edit("docs/cart.md")
        self.assertIn('"Consultar um carrinho vazio" — removido ou renomeado', context)
        self.assertIn('"Somar dois itens" — marcado @wip', context)
        self.assertIn("requisito CART-REQ-002 (docs/cart.md:20) — removido", context)
        self.assertIn("restaure os cenários", context)
        message = self.hook("Stop")["systemMessage"]
        for text in ("removido ou renomeado", "marcado @wip", "requisito CART-REQ-002"):
            self.assertIn(text, message)

    def test_expectation_adjusted_to_failing_code_comes_back_once(self):  # SMD-SCN-125
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 5)")
        self.assertEqual(self.hook("Stop")["decision"], "block")  # 510 instead of 500
        self.edit("docs/cart.md", "Então o total deve ser 500 centavos", "Então o total deve ser 510 centavos")
        reply = self.hook("Stop", stop_hook_active=True)
        self.assertEqual(reply["decision"], "block")
        self.assertIn("o valor esperado de cenários que falhavam mudou junto com o código", reply["reason"])
        self.assertIn("Então o total deve ser 500 centavos → Então o total deve ser 510 centavos", reply["reason"])
        self.assertIn("Total observado 510; esperado 500)", reply["reason"])
        self.assertIn("restaure o cenário", reply["reason"])
        allowed = self.hook("Stop", stop_hook_active=True)
        self.assertNotIn("decision", allowed)
        self.assertIn("cenários alterados nesta resposta", allowed["systemMessage"])

    def test_change_to_a_passing_scenario_is_only_reported(self):  # SMD-SCN-126
        self.edit("app.py", "self.prices.append(price_cents)", "self.prices.append(price_cents + 0)")
        self.assertIn("2 cenários passando", self.hook("Stop")["systemMessage"])
        self.hook("UserPromptSubmit")
        self.edit("docs/cart.md", "Então o total deve ser 500 centavos", "Então o total deve ser 510 centavos")
        self.edit("app.py", "price_cents + 0", "price_cents + 5")
        reply = self.hook("Stop")
        self.assertNotIn("decision", reply)
        self.assertIn("500 centavos → Então o total deve ser 510 centavos", reply["systemMessage"])

    def test_ignoring_a_document_reports_its_scenarios_and_rules(self):
        (self.root / ".specmdignore").write_text("docs/cart.md\n")
        context = self.after_edit(".specmdignore")
        self.assertIn('"Somar dois itens" — removido ou renomeado', context)
        self.assertIn("requisito CART-REQ-001 (docs/cart.md:6) — removido", context)
        self.assertIn("docs/cart.md está no .specmdignore, mas agora declara CART-REQ-001, CART-REQ-002, "
                      "um bloco Gherkin", context)

    def test_new_developer_message_resets_the_baseline(self):
        self.edit("docs/cart.md", "Então o total deve ser 500 centavos", "Então o total deve ser 510 centavos")
        self.hook("UserPromptSubmit")
        self.assertNotIn("cenários da última mensagem", self.after_edit("docs/cart.md"))


class IgnoredDocumentTests(HookCase):
    def test_requirement_written_in_an_ignored_document_is_reported(self):  # SMD-SCN-127
        (self.root / ".specmdignore").write_text("docs/setup.md\n")
        (self.root / "docs/setup.md").write_text("# Setup\n\nInstale as dependências.\n")
        self.after_edit("docs/setup.md")
        self.edit("docs/setup.md", "Instale", "## PAG-REQ-009 — Tentativas\n\nInstale")
        context = self.after_edit("docs/setup.md")
        self.assertIn("docs/setup.md está no .specmdignore, mas agora declara PAG-REQ-009", context)
        self.assertIn("Mova a regra para um documento de comportamento ou tire o arquivo do .specmdignore "
                      "(ou use !docs/setup.md). Em dúvida, pergunte ao dev.", context)
        self.edit("docs/setup.md", "Instale", "```gherkin\nFuncionalidade: X\n```\n\nInstale")
        self.assertIn("agora declara um bloco Gherkin", self.after_edit("docs/setup.md"))

    def test_existing_example_in_an_ignored_readme_is_not_reported(self):  # SMD-SCN-128
        (self.root / "README.md").write_text("# Demo\n\n```gherkin\nFuncionalidade: Exemplo\n```\n")
        self.hook("SessionStart")
        self.edit("README.md", "# Demo", "# Demo do carrinho")
        self.assertEqual(self.after_edit("README.md"), "")
        self.edit("README.md", "# Demo do carrinho", "# Demo do carrinho\n\n## Funcionalidade: Outra")
        self.assertIn("README.md é ignorado por padrão pelo SpecMD, mas agora declara títulos Gherkin (MDG)",
                      self.after_edit("README.md"))

    def test_the_warning_does_not_block_the_end_of_the_turn(self):  # SMD-SCN-129
        (self.root / ".specmdignore").write_text("docs/setup.md\n")
        (self.root / "docs/setup.md").write_text("# Setup\n")
        self.after_edit("docs/setup.md")
        (self.root / "docs/setup.md").write_text("# Setup\n\n## PAG-REQ-009 — Tentativas\n")
        self.assertIn("PAG-REQ-009", self.after_edit("docs/setup.md"))
        self.assertNotIn("decision", self.hook("Stop"))


if __name__ == "__main__":
    unittest.main()
