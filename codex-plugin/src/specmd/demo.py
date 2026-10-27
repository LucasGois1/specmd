"""Create a small runnable project whose rules live in Markdown scenarios."""

from __future__ import annotations

from pathlib import Path

from .messages import text as t


def initial_config() -> str:
    return (
        "# SpecMD configuration. Every key is optional; without this file the defaults apply.\n"
        "# language = \"pt\"          # SpecMD's messages in Portuguese (default: English)\n"
        "# gherkin_language = \"pt\"  # Gherkin keywords in Portuguese when a block has no # language: line\n"
        "# wip_tags = [\"wip\"]\n\n"
        "[run]\non_stop = true\n\n"
        "[[runners]]\nid = \"python\"\nlanguage = \"python\"\nsteps = \"tests/steps\"\ntimeout = 60\n"
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


@given("an empty cart")
def empty_cart(context):
    context.cart = Cart()


@when("I add items of {first:d} and {second:d} cents")
def add_items(context, first, second):
    context.cart.add(first)
    context.cart.add(second)
    context.total = context.cart.total()


@when("I check the cart total")
def read_total(context):
    context.total = context.cart.total()


@then("the total should be {expected:d} cents")
def assert_total(context, expected):
    assert context.total == expected, f"Observed total {context.total}; expected {expected}"
'''

CONTRACT = '''# Cart

Business rules of the cart. The scenarios below each requirement are the
specification and the acceptance test at the same time.

## CART-REQ-001 — Add up items

The cart total must equal the sum of the item prices, in cents.

```gherkin
# language: en
Feature: Cart total

  Scenario: Add two items
    Given an empty cart
    When I add items of 200 and 300 cents
    Then the total should be 500 cents
```

## CART-REQ-002 — Empty cart

A cart without items must have a total of zero cents.

```gherkin
# language: en
Feature: Empty cart

  Scenario: Check an empty cart
    Given an empty cart
    When I check the cart total
    Then the total should be 0 cents
```
'''


def create_demo(destination: Path) -> dict:
    requested = Path(destination).expanduser()
    if requested.is_symlink():
        raise ValueError(t("The demo destination cannot be a symbolic link.",
                           "O destino da demonstração não pode ser um link simbólico."))
    root = requested.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError(t("The destination must be new or an empty directory; no file is overwritten.",
                           "O destino deve ser novo ou um diretório vazio; nenhum arquivo será sobrescrito."))
    files = {
        "specmd.toml": initial_config(),
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
        "message": "Demo project created. Open the agent in the folder and ask for a rule change.",
    }
