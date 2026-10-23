"""Create a runnable local demonstration without approving its contract."""

from __future__ import annotations

import json
from pathlib import Path
import shlex


def initial_config(project_id: str) -> str:
    return (
        "# Contratos e classificações ainda exigem revisão; esta configuração não concede aceite.\n"
        "schema = 2\n"
        f"project_id = {json.dumps(project_id, ensure_ascii=False)}\n\n"
        "[[runners]]\nid = \"python\"\nlanguage = \"python\"\nsteps = \"tests/steps\"\ntimeout = 60\n\n"
        "[traceability]\nmap = \".specmd/traceability.json\"\npolicy = \"strict\"\n\n"
        "[evidence]\nallow_mock = false\nmax_age_seconds = 86400\n"
    )


APP = '''"""Small cart implementation exercised by the Markdown contract."""


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

CONTRACT = '''---
specmd:
  schema: 1
  id: SMD-DEMO-DOC-001
  kind: behavioral
---

# Contrato do carrinho

Este é um contrato proposto para experimentar o fluxo local. Ainda exige aceite
humano; a criação da demonstração não aprova seus requisitos ou cenários.

## SMD-DEMO-REQ-001 — Somar itens

O total do carrinho deve corresponder à soma dos preços dos itens, em centavos.

## SMD-DEMO-REQ-002 — Carrinho vazio

Um carrinho sem itens deve ter total de zero centavos.

```gherkin
# language: pt
Funcionalidade: Total do carrinho

  @SMD-DEMO-REQ-001 @SMD-DEMO-SCN-001
  Cenário: Somar dois itens
    Dado um carrinho vazio
    Quando eu adicionar itens de 200 e 300 centavos
    Então o total deve ser 500 centavos

  @SMD-DEMO-REQ-002 @SMD-DEMO-SCN-002
  Cenário: Consultar um carrinho vazio
    Dado um carrinho vazio
    Quando eu consultar o total do carrinho
    Então o total deve ser 0 centavos
```
'''


def create_demo(destination: Path, authority_dir: Path | None = None) -> dict:
    requested = Path(destination).expanduser()
    if requested.is_symlink():
        raise ValueError("O destino da demonstração não pode ser um link simbólico.")
    root = requested.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("O destino deve ser novo ou um diretório vazio; nenhum arquivo será sobrescrito.")
    authority = Path(authority_dir).expanduser() if authority_dir is not None else root.with_name(root.name + "-authority")
    if authority.is_symlink():
        raise ValueError("A autoridade não pode ser um link simbólico.")
    authority = authority.resolve()
    if authority == root or authority.is_relative_to(root):
        raise ValueError("A autoridade e suas chaves precisam ficar fora do projeto.")
    if authority.exists() and (not authority.is_dir() or any(authority.iterdir())):
        raise ValueError("A autoridade deve usar um diretório novo ou vazio, sem sobrescrever chaves existentes.")

    project_id = root.name or "specmd-demo"
    requirements = ["SMD-DEMO-REQ-001", "SMD-DEMO-REQ-002"]
    scenarios = ["SMD-DEMO-SCN-001", "SMD-DEMO-SCN-002"]
    links = {"requirements": requirements, "scenarios": scenarios}
    files = {
        "specmd.toml": initial_config(project_id),
        "app.py": APP,
        "docs/cart.md": CONTRACT,
        "tests/steps/cart_steps.py": STEPS,
        ".specmd/traceability.json": json.dumps({"schema": 1, "files": {
            "app.py": links, "tests/steps/cart_steps.py": links}}, ensure_ascii=False, indent=2) + "\n",
        ".gitignore": ".specmd/local/\n.specmd/cache/\n__pycache__/\n",
    }
    root.mkdir(parents=True, exist_ok=True)
    from .authority import initialize_authority
    authority_result = initialize_authority(authority, project_id, str(root))
    trust_value = authority_result.get("trust_store") or authority_result.get("trust_path")
    if not trust_value:
        raise ValueError("A autoridade não informou o caminho de sua raiz de confiança.")
    trust = Path(trust_value).resolve()
    if trust.is_relative_to(root):
        raise ValueError("A raiz de confiança da demonstração não pode ficar no projeto.")
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            stream.write(content)
    review = shlex.join(["specmd", "review", "--root", str(root), "--authority", str(authority), "--trust", str(trust)])
    run = shlex.join(["specmd", "run", "--root", str(root), "--trust", str(trust)])
    return {
        "status": "demo_created", "may_complete": False, "root": str(root),
        "project_id": project_id, "authority": str(authority), "trust_store": str(trust),
        "verification_mode": "demo", "assurance": "local_demo",
        "message": "Projeto e autoridade LOCAL DE DEMONSTRAÇÃO criados. Nenhum contrato foi aceito e nenhum cenário foi executado. Revise o conteúdo antes de decidir.",
        "files": sorted(files), "next_commands": {"review": review, "run_after_acceptance": run},
        "limitations": ["Quem controla a autoridade local pode emitir aceites. Este setup não cria uma autoridade isolada do agente.",
                        "O modo require-real não é satisfeito apenas por esta autoridade de demonstração."],
    }
