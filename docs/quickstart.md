---
specmd:
  schema: 1
  id: SMD-DOC-QUICKSTART
  kind: reference
  exemption_reason: "Instruções de uso do protótipo, sem requisitos adicionais do produto."
---

# Experimentar SpecMD localmente

Este roteiro cria um projeto descartável com contrato Markdown, implementação, steps reais e revisão no navegador. O aceite depende da sua ação explícita. A autoridade local não isola um agente com as mesmas permissões; `demo_passed` continua sendo uma demonstração.

## Instalar

Use Python 3.11 ou superior. A implementação experimental foi integrada à `main` pelo PR #1; o [handoff](../HANDOFF.md) transfere o contexto para a sessão local. Obtenha o código:

```sh
git clone https://github.com/LucasGois1/specmd.git
cd specmd
git switch main
```

A partir dessa revisão:

```sh
SPECMD_SOURCE="$PWD"
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" -m specmd --version
```

Mantenha `SPECMD_PYTHON` como caminho absoluto ao iniciar um agente que usará hooks.

Para executar toda a validação local sem conta de modelo, use `"$SPECMD_PYTHON" scripts/test_local.py`. O relatório separa agente/navegador simulados de assinaturas, HTTP e testes Python reais. As decisões automáticas ficam apenas nas fixtures descartáveis.

## Criar uma demonstração

Escolha diretórios novos. O projeto ficará em `/tmp/specmd-cart`, com autoridade local fora dele em `/tmp/specmd-cart-authority`:

```sh
"$SPECMD_PYTHON" -m specmd demo --dest /tmp/specmd-cart
export SPECMD_TRUST_STORE=/tmp/specmd-cart-authority/trust.json
"$SPECMD_PYTHON" -m specmd inventory --root /tmp/specmd-cart --format json
"$SPECMD_PYTHON" -m specmd check --root /tmp/specmd-cart --stage completion --format json
```

O projeto nasce sem aceite. A checagem deve apontar a pendência e retornar código não zero. Criar chaves, escrever o contrato ou preparar a proposta não registra concordância. Os requisitos fictícios da demonstração não são decisões sobre seu produto.

## Revisar

Para preparar e inspecionar a proposta sem aceitá-la:

```sh
"$SPECMD_PYTHON" -m specmd review --root /tmp/specmd-cart --prepare
```

Abra a interface local:

```sh
"$SPECMD_PYTHON" -m specmd review --root /tmp/specmd-cart \
  --authority /tmp/specmd-cart-authority \
  --trust "$SPECMD_TRUST_STORE"
```

Use a URL impressa se o navegador não abrir. Leia texto integral e diffs, confira classificações, dispensas, requisitos e cenários. Informe seu identificador e confirme o aceite apenas se concordar com aquela versão. O agente deve aguardar; este roteiro não automatiza essa decisão.

O nome é declarado, sem autenticação por provedor de identidade. O token do navegador é uma capacidade local. A assinatura vincula a decisão aos bytes revisados, sem comprovar leitura, compreensão ou isolamento contra outro processo do mesmo usuário.

Depois da decisão, encerre o servidor com `Ctrl+C`. O aceite ainda precisa ser acompanhado pelas evidências de execução.

## Executar e consultar

```sh
"$SPECMD_PYTHON" -m specmd run --root /tmp/specmd-cart --trust "$SPECMD_TRUST_STORE"
"$SPECMD_PYTHON" -m specmd check --root /tmp/specmd-cart --trust "$SPECMD_TRUST_STORE" --format json
"$SPECMD_PYTHON" -m specmd status --root /tmp/specmd-cart --trust "$SPECMD_TRUST_STORE"
"$SPECMD_PYTHON" -m specmd audit --root /tmp/specmd-cart --trust "$SPECMD_TRUST_STORE"
```

Python executa steps reais que chamam a aplicação. O Gherkin vem do Markdown em memória; não são criados `.feature`. Se os critérios demonstrativos passarem, o resultado será `demo_passed`, `verification_mode: "demo"` e `assurance: "local_demo"`. Esse resultado não habilita o gate protegido.

`audit` apresenta decisões e estado atual. A autoria declarada em Git não autentica a pessoa que concedeu o aceite.

## Exercitar mudanças

Edite uma frase do contrato Markdown da demonstração, sem aceitar a nova versão. `check` deve exigir revisão. Reabra a interface, leia o diff, decida sobre essa versão e execute `run` para renovar a evidência.

Altere depois somente a implementação ou um step. O contrato aceito pode continuar o mesmo, mas a evidência anterior fica obsoleta. `check` deve pedir execução; uma asserção falha mantém o bloqueio. Cenários indefinidos, ignorados, filtrados ou ausentes não contam como sucesso.

Adicionar, remover ou renomear Markdown altera o inventário. Alterar configuração ou rastreabilidade pode exigir revisão. Editar recibos, cache ou evidence JSON não substitui a decisão e a execução exigidas.

## Configurar um projeto existente

Primeiro inventarie e discuta contratos e referências. Schema 1 conserva a inspeção inicial; o lifecycle usa schema 2. Exemplo Python:

```toml
schema = 2
project_id = "meu-projeto"
repository_id = "github.com/minha-org/meu-projeto"

[[runners]]
id = "python"
language = "python"
steps = "tests/steps"
timeout = 60

[traceability]
map = ".specmd/traceability.json"
policy = "strict"
```

O mapa JSON usa `schema: 1` e `files` como mapa de caminhos relativos. Cada arquivo de código ou teste coberto pela política estrita exige requisitos existentes; os cenários indicados também precisam existir. Exemplo com IDs que devem estar no seu contrato:

```json
{
  "schema": 1,
  "files": {
    "app.py": {"requirements": ["SMD-APP-REQ-001"], "scenarios": ["SMD-APP-SCN-001"]},
    "tests/steps/cart.py": {"requirements": ["SMD-APP-REQ-001"], "scenarios": ["SMD-APP-SCN-001"]}
  }
}
```

Um vínculo torna a origem revisável; não prova equivalência semântica ou força das asserções. Uma regra nova proposta pelo agente ainda precisa ser discutida e aceita no contrato.

## Hooks e CI

Para Codex, gere o bundle, instale e revise os handlers pela UX normal em `/hooks`, seguindo [o guia](experimental-codex.md). Trust do hook e aceite contratual são decisões diferentes. Claude possui testes de protocolo, sem comprovação de execução nativa no host.

O comando protegido é:

```sh
"$SPECMD_PYTHON" -m specmd verify --root /caminho/do/projeto \
  --trust /caminho/externo/trust-provisionado.json --require-real
```

Ele exige confiança externa provisionada como protegida, rastreabilidade estrita e execução real fresca. A autoridade demonstrativa deste roteiro não satisfaz essa política. Alterar um campo para `protected` não cria isolamento: o operador precisa proteger chaves, trust, verificador e regras de CI.

Consulte [Estado de implementação](implementation-status.md) e [Integrações](integrations.md) antes de aplicar ao trabalho.
