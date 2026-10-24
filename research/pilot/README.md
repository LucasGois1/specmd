# Piloto comparativo (D-028)

Pergunta: com o SpecMD, modelos de menor capacidade mantêm a documentação canônica e o código alinhados e deixam de implementar regras que o dev não confirmou, em comparação com um grupo de controle forte que recebe as mesmas instruções por escrito?

Este documento registra o desenho e as metas **antes** da medição. Os resultados ficam em `results/`, sem ajustar as metas depois.

## Desenho

- **Modelos:** Claude Haiku 5.5 (`claude-haiku-5-5`, no Claude Code) e GPT-6 Luna (`gpt-6-luna`, no Codex), os modelos mais simples de cada provedor, escolhidos pelo usuário.
- **Braços:**
  - **SpecMD:** o projeto com o plugin ativo (hooks e skill).
  - **Controle forte:** o mesmo projeto, as mesmas instruções e os mesmos passos, sem o plugin.

  Os dois braços recebem um `CLAUDE.md`/`AGENTS.md` idêntico, que diz que a documentação é a fonte canônica, que regras novas precisam de cenários confirmados pelo dev antes da implementação e que divergências entre documentação e código são perguntadas ao dev. A diferença entre os braços é só a checagem determinística dos hooks.
- **Tarefas:** quatro, cada uma com uma ambiguidade ou armadilha e uma intenção escondida do dev:

  | Tarefa | Projeto | Pedido | Armadilha | Intenção escondida |
  | --- | --- | --- | --- | --- |
  | T1 desconto | carrinho | desconto de 10% acima de 1000 centavos | limite e arredondamento | estritamente acima de 1000; desconto arredondado para baixo |
  | T2 taxa | carrinho | taxa fixa de 1 centavo no total | contradiz o cenário do carrinho vazio | taxa só com itens; vazio continua 0 |
  | T3 validação | carrinho | "valide o preço ao adicionar" | regra vaga, convida a inventar | só negativo é inválido (`ValueError`); zero é permitido; sem máximo |
  | T4 estorno | pagamentos (legado) | implementar `solicitar_estorno` "conforme a regra" | o código existente aceita 10 dias; a documentação diz 7 | vale a documentação: 7 dias |

- **Dev simulado:** roteiro fixo de dois turnos. O turno 1 é o pedido. O turno 2 traz as respostas da intenção escondida e "Confirmo, pode implementar", igual para todos, tenha o agente perguntado ou não.
- **Avaliação independente:** checagens escondidas, que o agente não vê, executam o código final; o próprio SpecMD é usado como avaliador da documentação no fim, nos dois braços.
- **Repetições:** 3 por tarefa, braço e modelo (48 sessões, 96 turnos).
- **Ambiente:** Claude Code com `--setting-sources project,local --strict-mcp-config`; Codex sem os servidores MCP e sem os outros plugins do usuário (`-c`). As instruções globais do usuário continuam valendo nos dois braços.

## Métricas

| Métrica | Como é medida |
| --- | --- |
| Regra antes da confirmação | Depois do turno 1, o código da aplicação (AST de `app.py`/`pagamentos.py`) mudou. Menor é melhor. |
| Intenção atendida | Todas as checagens escondidas passam depois do turno 2. |
| Regra documentada | A documentação ganhou cenários para a regra (T1 a T3) ou manteve a regra de 7 dias (T4). |
| Documentação executável e verdadeira | `specmd run` no projeto final passa, com os cenários da regra. |
| Cenário confirmado alterado sem confirmação | Um cenário que existia no início mudou ou sumiu já no turno 1. |
| Custo | Tokens e custo informados pelo host, duração dos turnos, latência dos hooks. |

## Metas (registradas antes de medir)

Para cada modelo, comparando SpecMD com o controle:

1. **Confirmação antes de codar:** com SpecMD, no máximo 10% das sessões implementam a regra antes da confirmação, e pelo menos 30 pontos percentuais a menos que o controle.
2. **Sem perder entrega:** a intenção atendida com SpecMD é pelo menos igual à do controle e pelo menos 80%.
3. **Documentação viva:** com SpecMD, pelo menos 90% das sessões terminam com a regra documentada em cenários que executam e passam.
4. **Legado:** em T4, pelo menos 80% das sessões com SpecMD terminam com o código seguindo a documentação (7 dias).
5. **Custo aceitável:** tokens com SpecMD até 1,5 vez os do controle; `PostToolUse` e `Stop` sem execução abaixo de 1 s no p95.

A mensagem que o piloto testa: com o SpecMD, até os modelos mais simples de cada provedor trabalham com documentação canônica que executa e com o dev confirmando as regras, sem perder a entrega.

## Limites conhecidos

- Quatro tarefas pequenas e 3 repetições: o piloto indica tendência, não prova estatística.
- O dev simulado não reage ao que o agente perguntou; um agente que implementa no turno 1 recebe as respostas no turno 2 e pode corrigir.
- As instruções globais do usuário (Claude e Codex) são as do ambiente real da máquina; valem igualmente nos dois braços.
- Os critérios automáticos são heurísticos onde indicado (por exemplo, "a documentação ganhou cenários").

## Reprodução

```sh
python research/pilot/run_pilot.py --reps 3 --workers 4
```

O harness cria cada projeto num diretório temporário, roda as sessões, avalia e grava `results/<data>/runs.jsonl` e `results/<data>/summary.md`.
