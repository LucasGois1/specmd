# Sessões nativas no Codex com LLM real (24/10/2026)

Validação da [D-027](../../docs/decisions.md): o plugin SpecMD instalado no Codex CLI real, com modelo real, nos quatro eventos de hook.

## Ambiente

- Codex CLI `0.163.0`, autenticado com ChatGPT, feature `hooks` habilitada.
- Modelo `gpt-6-luna`.
- Plugin instalado pelo marketplace local do repositório: `codex plugin marketplace add <repo>` e `codex plugin add specmd@specmd-local`. O bundle vem de `scripts/build_codex_plugin.py`.
- Confiança nos quatro handlers dada pelo usuário no `/hooks`, sem o bypass de confiança.
- Execução com `codex exec --json`, retomando o turno seguinte com `codex exec resume <thread>`. Para reduzir ruído, as execuções desligaram, por `-c`, os servidores MCP do `config.toml` e os outros plugins do usuário. As instruções globais do usuário continuaram valendo.
- O retorno dos hooks foi observado pelo registro opcional `SPECMD_HOOK_LOG`, porque o JSON do `codex exec` não mostra a saída dos hooks.

## O que foi observado

| Ponto da D-027 | Resultado |
| --- | --- |
| Eventos disponíveis | O `/hooks` listou e confiou `SessionStart`, `UserPromptSubmit`, `PostToolUse` e `Stop` do plugin. Os quatro dispararam nas sessões. |
| `additionalContext` no início | O agente citou as instruções do SpecMD ("preciso confirmar os cenários antes de implementar") no primeiro turno. |
| `additionalContext` depois de ferramentas | O `PostToolUse` devolveu "documentação alterada … mostre-os e peça confirmação" depois do `apply_patch` em `docs/cart.md`. |
| `Stop` com `decision: block` | Com um cenário falhando, o `Stop` bloqueou; o Codex devolveu o controle ao agente, que perguntou ao dev qual regra vale (`request_user_input_async`); o `Stop` seguinte deixou concluir com o resumo. |
| Raiz do projeto sem `CLAUDE_PROJECT_DIR` | O hook usou o diretório da sessão; o estado ficou em `.specmd/local/` do projeto. |
| Roteiro de quatro turnos | Proposta antes de implementar; após "confirmo", implementação com `Stop` "5 cenários passando" e lembrete de confirmação; pedido contraditório (taxa) virou proposta; documento novo virou proposta de cenários antes da escrita. |
| Latência | `PostToolUse` de 77 a 248 ms; `Stop` 105 a 141 ms sem execução e 840 ms com execução; `SessionStart` 889 ms no projeto novo. |

## Limites observados

- **Ativação:** no Codex, o plugin é habilitado por usuário. O SpecMD só age em repositórios com `specmd.toml` ou com o plugin habilitado no `.claude/settings` do projeto; continua em aberto um equivalente por projeto no Codex.
- **Atualização exige nova confiança:** depois de `codex plugin add` com um bundle novo, o Codex deixou de chamar os hooks até o usuário revisá-los de novo no `/hooks`, embora os `trusted_hash` do `config.toml` não tenham mudado e a cópia instalada funcionasse quando chamada à mão. Numa observação posterior (25/10/2026), cada handler em `[hooks.state."specmd@specmd-local:…"]` trazia também um `trusted_content_hash`, que é o hash do conteúdo do plugin e explica a nova revisão a cada atualização, e um `enabled`. Com `enabled = false`, o `/hooks` não mostra nada a confiar e os hooks não rodam até serem reativados ali.
- **Ambiente do usuário:** as instruções globais do usuário (por exemplo, fazer commit local) aparecem no comportamento do agente; elas valem igualmente com e sem o SpecMD.
- **Primeira execução:** num projeto sem histórico, a primeira falha de um cenário recebe a orientação de divergência mesmo quando foi o agente que quebrou o código; a orientação manda perguntar ao dev, o que foi o comportamento observado.
