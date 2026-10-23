# Dispatch nativo no Claude Code

Este experimento carrega o plugin SpecMD em sessões reais do Claude Code, com modelo real, sobre projetos novos criados por `specmd demo`. Ele registra quais hooks o host despacha e que feedback o SpecMD devolve ao agente.

## Como reproduzir

Na raiz, depois de `pip install -e .` e com o CLI `claude` autenticado:

```sh
python scripts/build_codex_plugin.py
python research/claude/probe_headless.py
```

O relatório padrão fica em `.specmd/local/claude-headless.json`; `--record` grava a evidência versionada em `evidence/`. `--use-clone` carrega o plugin do próprio clone em vez do bundle. O executável `claude` vem do `PATH`, o intérprete é o que roda o probe e o modelo é fixo (`haiku`): nenhum argumento escolhe comandos ou caminhos arbitrários. Cada execução cria demos novos em um diretório temporário e consome uma pequena cota do modelo.

A sessão usa `claude -p` com `--plugin-dir`, `--setting-sources project,local`, `--strict-mcp-config` e `--permission-mode acceptEdits`. As duas primeiras opções isolam o plugin de hooks, plugins e servidores MCP das configurações do usuário.

## Casos

| Caso | Pedido ao agente | O que se verifica |
| --- | --- | --- |
| `documentation_gap` | Documentar uma regra de frete sem alterar código. | Os hooks despacham sem falha e o feedback sobre `docs/frete.md` chega ao agente (pendência ou pedido de confirmação dos cenários). |
| `code_breaks_scenario` | Somar uma taxa de 1 centavo no total. | Os cenários documentados falham e o `Stop` devolve o cenário, o passo e o erro ao agente. |
| `implement_confirmed` | Implementar cenários já confirmados, com um passo ainda sem implementação. | O `Stop` executa os cenários; o estado final é registrado. |

Em todos os casos: plugin carregado, `SessionStart` e `Stop` despachados, nenhuma falha de hook e nenhuma resposta que encerre a sessão.

## Evidência registrada

[evidence/headless-dispatch.json](evidence/headless-dispatch.json) identifica a versão do Claude Code, o modelo, os hooks despachados, o feedback devolvido e o estado final de cada caso. Caminhos locais foram substituídos por marcadores e outros plugins locais aparecem só como contagem.

Numa execução desta investigação (Claude Code 2.1.309, `claude-haiku-5-5`), o agente:
- escreveu a regra de frete já com cenários, os apresentou e pediu confirmação, apontando a ambiguidade de "acima de 10000";
- ao ver os cenários do carrinho falharem por causa da taxa, não alterou a documentação e perguntou se a regra mudou;
- implementou o passo do cupom até os três cenários passarem.

Esse comportamento é do modelo naquela execução; o probe verifica o despacho e o feedback dos hooks, não garante como outro modelo responderá.

## Limites

- O modo `-p` não exibe o diálogo de confiança do workspace e não há um dev real respondendo ao agente.
- A instalação por marketplace não foi exercitada; o plugin foi carregado apenas para a sessão.
- Hooks e plugins das configurações do usuário foram excluídos.
