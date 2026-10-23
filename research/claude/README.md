# Dispatch nativo no Claude Code

Este experimento carrega o plugin SpecMD em uma sessão real do Claude Code, com modelo real, sobre um `specmd demo` ainda sem aceite. Ele observa quais hooks o host despacha e o que o SpecMD decide. Não revisa nem aceita contratos.

## Como reproduzir

Na raiz, depois de `pip install -e .` e com o CLI `claude` autenticado:

```sh
python scripts/build_codex_plugin.py
python research/claude/probe_headless.py
```

O relatório padrão fica em `.specmd/local/claude-headless.json`; `--record` grava a evidência versionada em `evidence/`. `--use-clone` carrega o plugin do próprio clone em vez do bundle. O executável `claude` vem do `PATH`, o intérprete é o que roda o probe e o modelo é fixo (`haiku`): nenhum argumento escolhe comandos ou caminhos arbitrários. Cada execução cria demos novos em um diretório temporário e consome uma pequena cota do modelo.

A sessão usa `claude -p` com `--plugin-dir`, `--setting-sources project,local`, `--strict-mcp-config` e `--permission-mode acceptEdits`. As duas primeiras opções isolam o plugin de hooks, plugins habilitados e servidores MCP das configurações do usuário. `acceptEdits` mostra que o bloqueio de código vem do `PreToolUse` do SpecMD, e não de uma pergunta de permissão sem resposta.

## Casos

| Caso | Pedido | Expectativa |
| --- | --- | --- |
| `implement_request` | Implementar uma regra de desconto atualizando contrato e código. | Hooks despachados sem falha; código e steps intactos; `Stop` devolve o controle em `waiting_human_review`. Edições documentais são permitidas. |
| `forced_code_edit` | Usar `Edit` em `app.py` explicitamente. | A tentativa de `Edit` ocorre e é negada pelo `PreToolUse`; `app.py` permanece igual. |

## Evidência registrada

[evidence/headless-dispatch.json](evidence/headless-dispatch.json) registra Claude Code 2.1.309 e o modelo `claude-haiku-5-5` carregando o bundle gerado por `scripts/build_codex_plugin.py`. Os dois casos atenderam às expectativas: `SessionStart`, `PreToolUse`, `PostToolUse` e `Stop` foram despachados sem falhas, com um único handler SpecMD por ocorrência (um `PreToolUse` por ferramenta chamada e `PostToolUse` apenas para as não negadas); a edição de `app.py` foi negada; o `Stop` devolveu `continue: false`. Caminhos locais foram substituídos por marcadores e outros plugins locais aparecem só como contagem.

Uma execução anterior desta investigação mostrou que o Claude Code carrega `hooks/hooks.json` da raiz do plugin além do caminho declarado no manifesto. A declaração Codex dessa época dependia de `PLUGIN_ROOT`, ausente no Claude, e terminava com código 2; o host tratava isso como bloqueio de todas as ferramentas. Desde então há uma única declaração em `hooks/hooks.json`, que resolve a raiz por `PLUGIN_ROOT` ou `CLAUDE_PLUGIN_ROOT`.

## Limites

- O modo `-p` não exibe o diálogo de confiança do workspace. A experiência interativa e a decisão humana pela UX continuam sem evidência.
- A instalação por marketplace do Claude Code não foi exercitada; o plugin foi carregado apenas para a sessão.
- Hooks e plugins das configurações do usuário foram excluídos. A interação com eles precisa de ensaio próprio.
- O comportamento do modelo varia entre execuções. O resultado mostra o despacho dos hooks e as decisões do SpecMD nessas sessões, não uma garantia sobre como outro modelo responderá.
- Nenhum contrato foi aceito e a autoridade do demo é `local_demo`.
