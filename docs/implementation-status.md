---
specmd:
  schema: 1
  id: SMD-DOC-IMPLEMENTATION-STATUS
  kind: reference
  exemption_reason: "Estado da implementação e limites, sem acrescentar requisitos de comportamento."
---

# Estado de implementação

Versão 0.3.0, depois da mudança de direção [D-021](decisions.md): o SpecMD é um assistente que devolve feedback determinístico ao agente. O ciclo de aceite assinado, a autoridade, o trust, a revisão no navegador, o `verify` protegido e o bloqueio de implementação foram removidos.

| Área | Implementado | Limite |
| --- | --- | --- |
| Descoberta | Todo Markdown do projeto, inclusive não versionado; hashes por documento e impressão digital dos requisitos e cenários (`spec_fp`). | Frontmatter `specmd` ainda é obrigatório; IDs exigem o prefixo `SMD-`. O modelo simplificado (`.specmdignore`, IDs livres) é a próxima entrega. |
| Gherkin | Blocos cercados com requisitos, IDs, `Rule` e instâncias de `Scenario Outline` (schema 2). | MDG (`.feature.md`) não é lido. |
| Hooks | `SessionStart` (resumo e convenções), `UserPromptSubmit` (cenários vistos pelo dev), `PostToolUse` (pendências de documentação após a edição), `Stop` (pendências, cenários aguardando o dev, execução após mudança de código). | Dispatch nativo observado no Claude Code em modo headless ([evidência](../research/claude/README.md)); no Codex, os eventos novos não foram exercitados nativamente. A raiz do projeto vem de `CLAUDE_PROJECT_DIR` ou do diretório do processo do hook, nunca de caminhos do payload. |
| Feedback | Cenário, passo, linha, mensagem de erro e trecho pronto para passos sem implementação. Mesmo feedback repetido ou quatro devoluções deixam concluir; erros internos viram aviso. | Mensagens em pt-BR. |
| Execução | Python/Behave em subprocesso; bridges Java (Cucumber-JVM) e Go (Godog) pelo protocolo JSON. | O worker Python roda com o interpretador do plugin e não carrega `environment.py`; Java/Go recusam `Rule`/`Outline` e exigem tag de cenário `SMD-`. |
| Estado | `.specmd/local/state.json` com última execução, cenários vistos e contagem de devoluções; escrita atômica com lock. | Apenas POSIX (usa `fcntl`). |
| CLI | `init`, `inventory`, `check`, `run`, `demo` e os adaptadores de hook. | — |
| Instalação | `make agent` carrega o plugin só na sessão (`--plugin-dir`); bundle Codex por `scripts/build_codex_plugin.py`. | Instalação automática por repositório (marketplace + `.claude/settings.json`) é a entrega planejada. |

## Validações

A suíte local (`python -m unittest discover -s tests`) roda no macOS e no CI em Ubuntu e macOS. Os testes de hooks usam projetos reais criados por `specmd demo` e executam o Behave de verdade; os payloads dos hooks são simulados.

A evidência em [research/claude](../research/claude/README.md) registra sessões headless do Claude Code com modelo real exercitando documentação, código que contraria a documentação e implementação de cenários confirmados. O diálogo de confiança, a UX interativa e um dev real respondendo ao agente não foram exercitados ali.

Testes verdes não provam que os cenários representam toda a intenção do dev nem que as asserções são fortes; a documentação e os passos continuam precisando de revisão humana, normalmente no PR.
