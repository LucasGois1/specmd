---
specmd:
  schema: 1
  id: SMD-DOC-QUICKSTART
  kind: reference
  exemption_reason: "Instruções de uso do protótipo, sem requisitos adicionais do produto."
---

# Experimentar SpecMD localmente

Use Python 3.11 ou superior e o CLI `claude` autenticado.

## Atalho com make

Na raiz do clone:

| Comando | O que faz |
| --- | --- |
| `make setup` | Cria `.venv`, instala as dependências e gera o plugin em `dist/codex-plugin`. |
| `make demo` | Cria um demo novo em `~/specmd-demo/<data-hora>/cart`, já com `git init`. |
| `make agent` | Abre o Claude Code no último demo com o plugin carregado só nessa sessão. |
| `make status` | Resume o estado do último demo. |
| `make run` | Executa os cenários do último demo e resume o resultado. |
| `make test` | Roda a suíte local. |
| `make init REPO=…` | Prepara um repositório seu para o SpecMD. |

`DEMO_HOME` muda a pasta dos demos. `CLAUDE_ARGS` repassa opções ao `claude`, por exemplo `--setting-sources project,local` para não carregar hooks e plugins das suas configurações. Cada `make demo` cria uma pasta nova; demos anteriores não são apagados.

## No seu repositório

```sh
make init REPO=/caminho/do/seu/repo
```

Isso cria `specmd.toml` e `.specmdignore` (se não existirem), adiciona `.specmd/local/` ao `.gitignore` e declara no `.claude/settings.json` o marketplace do SpecMD com o plugin habilitado, preservando o que já existe. Faça commit desses arquivos. Quem abrir o Claude Code no repositório e confiar na pasta recebe o plugin. Rodar de novo não muda nada.

Sem o clone: dentro do Claude Code no seu repositório, `claude plugin install specmd --marketplace LucasGois1/specmd --scope project` e depois `/specmd:init`.

## Um roteiro de teste

1. `make demo` e `make agent`.
2. Peça uma regra nova: "adicione desconto de 10% para totais acima de 1000 centavos". O agente deve escrever o requisito e os cenários no Markdown e pedir sua confirmação. Se ele escrever documentação sem cenários, o SpecMD avisa.
3. Confirme. O agente implementa; ao concluir, os cenários são executados e qualquer falha volta para ele com o passo e o erro.
4. Peça algo que contrarie a documentação, por exemplo "some uma taxa de 1 centavo no total". Os cenários existentes falham e o agente deve perguntar se a regra mudou.

## Sem make

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m specmd demo --dest /caminho/novo/cart
cd /caminho/novo/cart && git init -q
SPECMD_PYTHON=/caminho/do/specmd/.venv/bin/python claude --plugin-dir /caminho/do/specmd
```

Comandos do CLI, todos com `--root` (padrão: diretório atual):

| Comando | Resultado |
| --- | --- |
| `specmd init` | Prepara o repositório: `specmd.toml`, `.specmdignore`, `.gitignore` e o plugin no `.claude/settings.json`. |
| `specmd inventory` | Documentos, requisitos, cenários e pendências da documentação. |
| `specmd check` | Pendências e o resultado da última execução, se ainda atual. |
| `specmd run` | Executa os cenários e guarda o resultado para os hooks. |

Códigos de saída: 0 sem pendências, 1 documentação pendente ou cenários falhando, 2 erro ou projeto sem `specmd.toml`.

## Formato

Um documento só precisa de cenários em blocos ```gherkin; frontmatter é opcional. Requisitos podem ter ID no título (`## PAG-REQ-001 — Estorno`) e os cenários logo abaixo ficam ligados a eles. Markdown que não descreve comportamento vai para o `.specmdignore`. Detalhes em [formato](format.md).

O `specmd.toml` pode ser vazio; para executar cenários Python, declare um runner:

```toml
[[runners]]
id = "python"
language = "python"
steps = "tests/steps"
```

Java e Go usam um `command` de bridge; veja [adapters](../adapters/README.md).

## Codex

O mesmo `hooks/hooks.json` serve ao Codex. Gere o bundle com `python scripts/build_codex_plugin.py`, instale pelo marketplace local e revise os handlers em `/hooks`, seguindo [o guia](experimental-codex.md). Os eventos novos ainda não foram exercitados nativamente no Codex.
