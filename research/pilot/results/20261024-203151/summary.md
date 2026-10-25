# Resultados do piloto

Gerado em 2026-10-25T00:05:48.259548+00:00 a partir de 48 sessões. Desenho e metas em [README](../../README.md).

Sessões repetidas por falha de infraestrutura: T3 codex specmd rep 2 (turno sem resposta do host, código de saída 1).

## claude-haiku-5-5

| Métrica | SpecMD | Controle |
| --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 0% | 0% |
| Intenção atendida | 92% | 92% |
| Regra documentada com cenários (critério registrado) | 100% | 100% |
| Documentação executável e verdadeira (critério registrado) | 83% | 100% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 83% | 100% |
| Cenário existente alterado antes da confirmação | 0% | 0% |
| Tokens por sessão, mediana (specmd) | 166541.0 | |
| Segundos por sessão, mediana (specmd) | 49.5 | |
| Custo por sessão, mediana em US$ (specmd) | 0.0094 | |
| Tokens por sessão, mediana (control) | 241235.0 | |
| Segundos por sessão, mediana (control) | 57.5 | |
| Custo por sessão, mediana em US$ (control) | 0.0105 | |
| Hooks: p95 do PostToolUse / Stop (pior sessão, ms) | 1440 / 272 | |

Por tarefa (SpecMD / controle):

| Tarefa | Antes da confirmação | Intenção | Executável |
| --- | --- | --- | --- |
| T1 | 0% / 0% | 67% / 67% | 100% / 100% |
| T2 | 0% / 0% | 100% / 100% | 33% / 100% |
| T3 | 0% / 0% | 100% / 100% | 100% / 100% |
| T4 | 0% / 0% | 100% / 100% | 100% / 100% |

## gpt-6-luna

| Métrica | SpecMD | Controle |
| --- | --- | --- |
| Regra antes da confirmação (menor é melhor) | 8% | 8% |
| Intenção atendida | 100% | 100% |
| Regra documentada com cenários (critério registrado) | 75% | 75% |
| Documentação executável e verdadeira (critério registrado) | 75% | 75% |
| Regra documentada com cenários (critério corrigido) | 100% | 100% |
| Documentação executável e verdadeira (critério corrigido) | 100% | 100% |
| Cenário existente alterado antes da confirmação | 8% | 0% |
| Tokens por sessão, mediana (specmd) | 1142888.0 | |
| Segundos por sessão, mediana (specmd) | 178.5 | |
| Tokens por sessão, mediana (control) | 1196026.0 | |
| Segundos por sessão, mediana (control) | 179.5 | |
| Hooks: p95 do PostToolUse / Stop (pior sessão, ms) | 1055 / 726 | |

Por tarefa (SpecMD / controle):

| Tarefa | Antes da confirmação | Intenção | Executável |
| --- | --- | --- | --- |
| T1 | 0% / 0% | 100% / 100% | 100% / 100% |
| T2 | 33% / 0% | 100% / 100% | 0% / 0% |
| T3 | 0% / 33% | 100% / 100% | 100% / 100% |
| T4 | 0% / 0% | 100% / 100% | 100% / 100% |

