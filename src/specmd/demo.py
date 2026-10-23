"""Create a small runnable project whose rules live in Markdown scenarios."""

from __future__ import annotations

from pathlib import Path


def initial_config() -> str:
    return (
        "# Configuração do SpecMD. Todas as chaves são opcionais.\n"
        "# gherkin_language = \"pt\"\n"
        "# wip_tags = [\"wip\"]\n\n"
        "[run]\non_stop = true\n\n"
        "[[runners]]\nid = \"python\"\nlanguage = \"python\"\nsteps = \"tests/steps\"\ntimeout = 60\n"
    )


DEFAULT_IGNORE = (
    "# Markdown que não descreve comportamento do sistema (padrões no estilo .gitignore).\n"
    "README.md\nCHANGELOG.md\nCONTRIBUTING.md\nCODE_OF_CONDUCT.md\nSECURITY.md\nLICENSE*\n.github/\n"
)


APP = '''"""Small cart implementation exercised by the Markdown documentation."""


class Cart:
    def __init__(self):
        self.prices = []

    def add(self, price_cents):
        self.prices.append(price_cents)

    def total(self):
        return sum(self.prices)
'''

STEPS = '''from behave import given, when, then

from app import Cart


@given("um carrinho vazio")
def empty_cart(context):
    context.cart = Cart()


@when("eu adicionar itens de {first:d} e {second:d} centavos")
def add_items(context, first, second):
    context.cart.add(first)
    context.cart.add(second)
    context.total = context.cart.total()


@when("eu consultar o total do carrinho")
def read_total(context):
    context.total = context.cart.total()


@then("o total deve ser {expected:d} centavos")
def assert_total(context, expected):
    assert context.total == expected, f"Total observado {context.total}; esperado {expected}"
'''

CONTRACT = '''# Carrinho

Regras de negócio do carrinho. Os cenários abaixo de cada requisito são a
especificação e o teste de aceitação ao mesmo tempo.

## CART-REQ-001 — Somar itens

O total do carrinho deve corresponder à soma dos preços dos itens, em centavos.

```gherkin
# language: pt
Funcionalidade: Total do carrinho

  Cenário: Somar dois itens
    Dado um carrinho vazio
    Quando eu adicionar itens de 200 e 300 centavos
    Então o total deve ser 500 centavos
```

## CART-REQ-002 — Carrinho vazio

Um carrinho sem itens deve ter total de zero centavos.

```gherkin
# language: pt
Funcionalidade: Carrinho vazio

  Cenário: Consultar um carrinho vazio
    Dado um carrinho vazio
    Quando eu consultar o total do carrinho
    Então o total deve ser 0 centavos
```
'''


def create_demo(destination: Path) -> dict:
    requested = Path(destination).expanduser()
    if requested.is_symlink():
        raise ValueError("O destino da demonstração não pode ser um link simbólico.")
    root = requested.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("O destino deve ser novo ou um diretório vazio; nenhum arquivo será sobrescrito.")
    files = {
        "specmd.toml": initial_config(),
        ".specmdignore": DEFAULT_IGNORE,
        "app.py": APP,
        "docs/cart.md": CONTRACT,
        "tests/steps/cart_steps.py": STEPS,
        ".gitignore": ".specmd/local/\n.specmd/cache/\n__pycache__/\n",
    }
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            stream.write(content)
    return {
        "status": "demo_created", "root": str(root), "files": sorted(files),
        "message": "Projeto de demonstração criado. Abra o agente na pasta e peça uma mudança de regra.",
    }
