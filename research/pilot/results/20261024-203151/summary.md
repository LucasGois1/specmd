# Resultados do piloto

Gerado em 2026-10-25T02:02:57.094376+00:00 a partir de 48 sessões. Desenho e metas em [README](../../README.md).

Sessões repetidas por falha de infraestrutura: T3 codex specmd rep 2 (turno sem resposta do host, código de saída 1).

## claude-haiku-5-5

| Métrica | Instruções + plugin | Só instruções |
| --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 0% | 0% |
| Intenção atendida | 92% | 92% |
| Regra documentada com cenários (critério registrado) | 100% | 100% |
| Documentação executável e verdadeira (critério registrado) | 83% | 100% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 83% | 100% |
| Cenário existente alterado antes da confirmação | 0% | 0% |
| Tokens por sessão, mediana | 166,541 | 241,235 |
| Segundos por sessão, mediana | 50 | 58 |
| Custo por sessão, mediana em US$ | 0.0094 | 0.0105 |

Hooks: p95 do PostToolUse / Stop na pior sessão: 1440 / 272 ms; mediana dos p95: 383.0 / 179.5 ms.

Por tarefa (Instruções + plugin / Só instruções):

| Tarefa | Antes da confirmação | Intenção | Executável (corrigido) |
| --- | --- | --- | --- |
| T1 | 0% / 0% | 67% / 67% | 100% / 100% |
| T2 | 0% / 0% | 100% / 100% | 33% / 100% |
| T3 | 0% / 0% | 100% / 100% | 100% / 100% |
| T4 | 0% / 0% | 100% / 100% | 100% / 100% |

## gpt-6-luna

| Métrica | Instruções + plugin | Só instruções |
| --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 8% | 8% |
| Intenção atendida | 100% | 100% |
| Regra documentada com cenários (critério registrado) | 75% | 75% |
| Documentação executável e verdadeira (critério registrado) | 75% | 75% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 100% | 100% |
| Cenário existente alterado antes da confirmação | 8% | 0% |
| Tokens por sessão, mediana | 1,142,888 | 1,196,026 |
| Segundos por sessão, mediana | 178 | 180 |

Hooks: p95 do PostToolUse / Stop na pior sessão: 1055 / 726 ms; mediana dos p95: 462.5 / 360.0 ms.

Por tarefa (Instruções + plugin / Só instruções):

| Tarefa | Antes da confirmação | Intenção | Executável (corrigido) |
| --- | --- | --- | --- |
| T1 | 0% / 0% | 100% / 100% | 100% / 100% |
| T2 | 33% / 0% | 100% / 100% | 100% / 100% |
| T3 | 0% / 33% | 100% / 100% | 100% / 100% |
| T4 | 0% / 0% | 100% / 100% | 100% / 100% |

