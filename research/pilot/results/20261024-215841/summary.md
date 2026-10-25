# Resultados do piloto

Gerado em 2026-10-25T02:02:57.098035+00:00 a partir de 108 sessões. Desenho e metas em [README](../../README.md).

## claude-haiku-5-5

| Métrica | Repositório comum | Só o plugin | Só instruções |
| --- | --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 100% | 17% | 0% |
| Intenção atendida | 100% | 94% | 94% |
| Regra documentada com cenários (critério registrado) | 89% | 94% | 100% |
| Documentação executável e verdadeira (critério registrado) | 89% | 94% | 100% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 100% | 100% | 100% |
| Intenção atendida após o turno 2 | 100% | 94% | 94% |
| Documentação executável após o turno 2 | 100% | 89% | 100% |
| Cenário existente alterado antes da confirmação | 33% | 0% | 0% |
| Tokens por sessão, mediana | 344,213 | 251,450 | 342,176 |
| Segundos por sessão, mediana | 117 | 107 | 123 |
| Custo por sessão, mediana em US$ | 0.0241 | 0.0170 | 0.0214 |

Hooks: p95 do PostToolUse / Stop na pior sessão: 4932 / 2746 ms; mediana dos p95: 1474.5 / 931.0 ms.

Por tarefa (Repositório comum / Só o plugin / Só instruções):

| Tarefa | Antes da confirmação | Intenção | Executável (corrigido) |
| --- | --- | --- | --- |
| T1 | 100% / 0% / 0% | 100% / 100% / 67% | 100% / 100% / 100% |
| T2 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T3 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T4 | 100% / 100% / 0% | 100% / 67% / 100% | 100% / 100% / 100% |
| T5 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T6 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |

## gpt-6-luna

| Métrica | Repositório comum | Só o plugin | Só instruções |
| --- | --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 100% | 22% | 0% |
| Intenção atendida | 100% | 100% | 100% |
| Regra documentada com cenários (critério registrado) | 72% | 78% | 72% |
| Documentação executável e verdadeira (critério registrado) | 67% | 78% | 67% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 94% | 100% | 94% |
| Intenção atendida após o turno 2 | 100% | 100% | 100% |
| Documentação executável após o turno 2 | 50% | 100% | 89% |
| Cenário existente alterado antes da confirmação | 33% | 17% | 0% |
| Tokens por sessão, mediana | 2,667,382 | 2,067,931 | 2,030,577 |
| Segundos por sessão, mediana | 255 | 260 | 228 |

Hooks: p95 do PostToolUse / Stop na pior sessão: 3525 / 2609 ms; mediana dos p95: 1084.0 / 792.0 ms.

Por tarefa (Repositório comum / Só o plugin / Só instruções):

| Tarefa | Antes da confirmação | Intenção | Executável (corrigido) |
| --- | --- | --- | --- |
| T1 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T2 | 100% / 33% / 0% | 100% / 100% / 100% | 67% / 100% / 100% |
| T3 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T4 | 100% / 100% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T5 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T6 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 67% |

