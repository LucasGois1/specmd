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
| `make init REPO=…` | Habilita o plugin para o time num repositório seu. |

`DEMO_HOME` muda a pasta dos demos. `CLAUDE_ARGS` repassa opções ao `claude`, por exemplo `--setting-sources project,local` para não carregar hooks e plugins das suas configurações. Cada `make demo` cria uma pasta nova; demos anteriores não são apagados.

## No seu repositório

Dentro do Claude Code, no seu repositório:

```
/plugin marketplace add LucasGois1/specmd
/plugin install specmd@specmd        → escopo do projeto ou local
```

Instalado no escopo do projeto ou local, o plugin já está ativo, com os padrões:
- todo Markdown é analisado, menos `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`, `LICENSE*`, `.github/` e semelhantes;
- os passos Python em `tests/steps`, `features/steps` ou `steps` são usados para executar os cenários.

Uma instalação só no escopo de usuário não ativa repositórios sozinha.

Para o time: `/specmd:init` (ou `make init REPO=…` a partir deste clone) declara o marketplace e habilita o plugin no `.claude/settings.json` do projeto, sem mexer no resto. Faça commit desse arquivo; quem abrir o Claude Code no repositório e confiar na pasta recebe o plugin.

Num projeto que já tem documentação, `/specmd:adopt` conduz a adoção: lista os documentos sem cenários, você diz quais não descrevem comportamento (vão para o `.specmdignore`) e o agente propõe os cenários de um documento por vez, com sua confirmação. Se um cenário novo falha porque o código faz outra coisa, ele pergunta qual dos dois vale.

O estado local fica em `.specmd/local/`, que se ignora sozinho no Git.

O plugin não fixa versão no manifesto, então cada commit da `main` do SpecMD é uma versão nova. Com o marketplace declarado pelo `/specmd:init` (`autoUpdate: true`), o Claude Code atualiza sozinho. Num marketplace adicionado à mão, use `/plugin marketplace update specmd`, depois `claude plugin update specmd@specmd` e `/reload-plugins`.

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
| `specmd init` | Declara o marketplace e habilita o plugin no `.claude/settings.json` do projeto. |
| `specmd inventory` | Documentos, requisitos, cenários e pendências da documentação. |
| `specmd check` | Pendências e o resultado da última execução, se ainda atual. |
| `specmd run` | Executa todos os cenários e guarda o resultado para os hooks. |
| `specmd adopt` | Documentos sem cenários e requisitos sem cenário, em ordem de caminho, para a adoção em legado. |
| `specmd run --affected` | Executa só os cenários afetados pela mudança desde a última execução, como ao concluir. |

Códigos de saída: 0 sem pendências, 1 documentação pendente ou cenários falhando, 2 erro ou projeto sem `specmd.toml`.

## Formato

Um documento só precisa de cenários em blocos ```gherkin; frontmatter é opcional. Requisitos podem ter ID no título (`## PAG-REQ-001 — Estorno`) e os cenários logo abaixo ficam ligados a eles. Markdown que não descreve comportamento vai para o `.specmdignore`. Detalhes em [formato](format.md).

O `specmd.toml` é opcional. Sem `[[runners]]`, os passos Python em `tests/steps`, `features/steps` ou `steps` são usados; para outro diretório, declare:

```toml
[[runners]]
id = "python"
language = "python"
steps = "tests/steps"
```

Java e Go usam um `command` de bridge; veja [adapters](../adapters/README.md).

## Codex

O mesmo `hooks/hooks.json` serve ao Codex. Gere o bundle com `python scripts/build_codex_plugin.py`, instale pelo marketplace local e revise os handlers em `/hooks`, seguindo [o guia](experimental-codex.md). Os eventos novos ainda não foram exercitados nativamente no Codex.
