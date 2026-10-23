---
specmd:
  schema: 1
  id: SMD-DOC-IMPLEMENTATION-STATUS
  kind: reference
  exemption_reason: "Estado experimental e limites, sem acrescentar requisitos de comportamento."
---

# Estado de implementação

Esta branch contém um lifecycle experimental: prepara revisão, registra decisões assinadas, verifica rastreabilidade e executa cenários em memória. A demonstração não estabelece autoridade humana isolada nem comprova CI protegido.

| Área | Implementado | Limite |
| --- | --- | --- |
| Inventário | Markdown, metadados, hashes dos bytes e manifesto com caminhos/configuração. | Classificação semântica exige revisão; podas são parte da implementação. |
| Gherkin | Requisitos, IDs, origem e blocos cercados; schema 2 com `Rule` e instâncias de Outline. | Parse válido não garante suporte de cada executor. |
| Cache | Registros de análise com identidade da fonte/parser. | Advisory: a fonte sempre é reanalisada; sem alegação de ganho de performance por reutilização confiável. |
| Revisão | Snapshot, texto integral, diff, classificação e decisão explícita no navegador. | Nome declarado e token não autenticam uma pessoa; experiência humana completa ainda precisa de validação. |
| Assinatura | Recibos vinculados à versão, chave autorizada, projeto e repositório; trust externo. | Posse de chave não prova leitura ou isolamento operacional. |
| Rastreabilidade | `.specmd/traceability.json`: schema 1, `files`, requisitos e cenários. | Vínculo declara origem, sem provar equivalência semântica. |
| Python | Behave real em subprocesso, steps, múltiplos blocos, Rule e linhas de Outline em memória. | Sem `environment.py` ou configuração Behave do projeto; subprocesso não é sandbox de código hostil. |
| Java/Go | Bridges Cucumber-JVM/Godog compilados e exercitados pelo núcleo, com sucesso, asserção falha e passo indefinido. | Cenários simples e Background; Rule/Outline explicitamente recusados nesses bridges. |
| Evidências | Snapshot de contrato, aceite, código, testes, configuração, vínculos e execução; invalidação por mudanças. | JSON local não é autoridade independente; CI precisa de verificador/bridges confiáveis. |
| Mock | Opt-in explícito, resultado simulado. | Não satisfaz `verify --require-real`. |
| Lifecycle | Espera de revisão/evidência, bloqueio, `demo_passed` e caminho protegido `passed`. | Sucesso demonstrativo não libera integração produtiva. |
| CLI | Demonstração, inventário, revisão, execução, checagem, status, auditoria e verificação. | Interface experimental; confira `--help` da revisão instalada. |
| Codex | Pacote com quatro eventos e adaptador; instalação/dispatch anterior observado no CLI 0.163.0. | Prova nativa dos três eventos anteriores com backend simulado; novo `PreToolUse` testado em protocolo. Serviço real retornou `401`. |
| Claude | Manifesto, adaptação e dispatch nativo headless dos quatro eventos no Claude Code 2.1.309 com modelo real ([evidência](../research/claude/README.md)). | Diálogo de trust, UX interativa, instalação por marketplace e hooks do usuário sem ensaio. |
| CI | Workflow de exemplo e `verify --require-real` com execução fresca. | Autoridade, verificador e regras protegidas precisam de provisionamento externo. |

## Interpretar sucesso

`demo_passed` usa `verification_mode: "demo"` e `assurance: "local_demo"`. Pode haver testes reais, mas a confiança local continua demonstrativa. Qualquer mock mantém essa distinção.

`passed` é reservado a execução real fresca, trust externo marcado como protegido e rastreabilidade estrita. Esses critérios são verificações do software. A proteção efetiva das chaves, trust e CI é uma responsabilidade de implantação que um campo JSON não comprova.

Aceite não prova implementação. Testes verdes não provam que os requisitos estão corretos ou que as asserções são suficientemente fortes. Contrato, steps e código continuam precisando de revisão.

## Validações pendentes

O relatório registrado em [research/workflow/evidence](../research/workflow/evidence/local-tests.json) passou **187 testes**, sem skips. A revisão atual tem 188 testes, executados no CI em Linux e macOS com dependências instaladas de `pylock.toml`. Os seis casos de integração nativa Java/Go também passaram nas expectativas positivas e negativas. Assinaturas, HTTP local e execução Python são reais; agente e decisões de navegador nos testes são fixtures simuladas. A versão 0.2.0 do pacote foi instalada no Codex deste ambiente, com arquivos conferidos contra o bundle. Os relatórios estão em [research/workflow/evidence](../research/workflow/evidence/); nenhum deles representa leitura ou aceite humano dos contratos reais.

A experiência de uma pessoa lendo, recusando, aceitando e retomando um agente ainda precisa de ensaios completos. A interação `/hooks` com trust humano exige evidência própria.

Testes nativos anteriores com backend simulado validam o dispatcher naquela revisão, sem testar interpretação por LLM. Nesta evolução, os protocolos são exercitados por simulação de agente; o pacote atual precisa de ensaio nativo completo no ambiente do usuário. Serviço de modelo real, plataformas adicionais, ampliação dos formatos Java/Go e implantação protegida de CI continuam escopos explícitos de validação.

Veja [Quickstart](quickstart.md), [Integrações](integrations.md), [Pesquisa](../research/README.md) e [Plano de validação](validation-plan.md). Artefatos de pesquisa identificam versões e snapshots; não constituem certificação de produção.
