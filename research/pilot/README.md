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

## Resultados (24/10/2026)

Rodada completa: 48 sessões, em `results/20261024-203151/`. Dados brutos em `runs.jsonl`, reavaliação em `runs-reevaluated.jsonl` e quadro em `summary.md`.

Duas correções, feitas às claras depois da rodada:

- **Critério de documentação:** o critério registrado exigia cenários novos nas tarefas T1 a T3. Na T2, porém, a regra da taxa fica documentada ao atualizar o cenário existente (de 500 para 501), e os dois braços do Codex fizeram isso. O critério corrigido aceita cenários novos ou alterados. As duas versões aparecem no quadro.
- **Falha de infraestrutura:** uma sessão do Codex (T3, SpecMD, repetição 2) teve o turno 2 encerrado pelo host sem resposta (código 1, sem tokens) e foi repetida.

| Métrica | Haiku 5.5: SpecMD / controle | GPT-6 Luna: SpecMD / controle |
| --- | --- | --- |
| Regra antes da confirmação | 0% / 0% | 8% / 8% |
| Intenção atendida | 92% / 92% | 100% / 100% |
| Documentação executável e verdadeira (critério corrigido) | 83% / 100% | 100% / 100% |
| Cenário existente alterado antes da confirmação | 0% / 0% | 8% / 0% |
| Tokens por sessão, mediana | 167 mil / 241 mil | 1,14 mi / 1,20 mi |
| p95 do `PostToolUse` / `Stop` na pior sessão | 1.440 / 272 ms | 1.055 / 726 ms |

### Metas

| Meta | Resultado |
| --- | --- |
| 1. Confirmação antes de codar: no máximo 10% e 30 pontos abaixo do controle | **Não atingida.** O limite de 10% foi cumprido (0% e 8%), mas o controle teve o mesmo resultado; as instruções escritas bastaram nestas tarefas. |
| 2. Intenção atendida no mínimo igual ao controle e acima de 80% | **Atingida** nos dois modelos (92% e 100%, iguais ao controle). |
| 3. Documentação executável e verdadeira em pelo menos 90% | **Atingida no GPT-6 Luna (100%); não atingida no Haiku 5.5 (83%)**, por um defeito do SpecMD (abaixo). |
| 4. Legado (T4) em pelo menos 80% | **Atingida** (100% nos dois modelos), mas o controle também chegou a 100%. |
| 5. Custo: tokens até 1,5 vez o controle e hooks abaixo de 1 s no p95 | **Tokens atingida:** as sessões com SpecMD usaram menos tokens. **Latência não atingida:** o `PostToolUse` passou de 1 s no p95 da pior sessão; a máquina estava com carga alta durante a rodada. |

### O que o piloto mostrou

- **Controle forte bastou nestas tarefas.** Com um `CLAUDE.md`/`AGENTS.md` dizendo o mesmo que o SpecMD injeta, os dois modelos pequenos perguntaram antes de implementar e documentaram a regra. Nestas quatro tarefas curtas, a checagem determinística não acrescentou acerto mensurável.
- **Defeito encontrado: falso positivo de divergência.** Na T2 com o Haiku, a taxa quebrou o cenário antigo "Somar dois itens" (500). Como o projeto era novo e não tinha histórico, o SpecMD tratou a falha como "cenário que nunca passou" e orientou a perguntar ao dev sobre divergência. O agente parou para perguntar, em vez de atualizar o cenário que a confirmação já implicava; isso aconteceu em 2 das 3 sessões. A falha era consequência da mudança do próprio agente, não legado.
- **Sem custo extra:** as sessões com SpecMD usaram menos tokens que o controle nos dois modelos.

### Limites desta rodada

- Tarefas curtas, de dois turnos, com o dev simulado já dando as respostas no turno 2.
- O controle recebe por escrito as mesmas convenções que o SpecMD injeta. Isso mede o valor da checagem determinística sobre instruções que já existem, não o valor de instalar o SpecMD num repositório comum.
- Carga alta na máquina durante a rodada (uma VM e outro servidor em execução), o que afeta a latência.
