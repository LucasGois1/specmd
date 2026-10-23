# Plano de validação

> **Histórico, anterior à [D-021](decisions.md).** Este documento descreve o desenho com aceite assinado, autoridade, trust e bloqueio de implementação, removido em 23/10/2026. Para o produto atual, veja [produto](product.md) e [estado da implementação](implementation-status.md).

> Plano de validação do produto ainda não concluído. Há protótipos de runners e testes automatizados do ciclo experimental, registrados no [estudo técnico](runner-feasibility.md), no [estado atual](implementation-status.md) e no [handoff](../HANDOFF.md). Parte dos casos determinísticos já é exercitada em fixtures; a sessão humana com agente real e o piloto comparativo continuam necessários. Esses resultados não representam aceites dos contratos reais nem validação de utilidade do produto.

O plano avalia duas questões diferentes: se o mecanismo aplica corretamente as regras declaradas e se seu uso melhora o desenvolvimento com agentes. Um gate tecnicamente correto pode produzir pouca utilidade ou interrupções excessivas; uma boa experiência não substitui a integridade do aceite.

O contrato a verificar está em [requisitos](requirements.md). Este documento organiza experimentos e evidências, sem acrescentar requisitos silenciosamente. Dúvidas de comportamento devem voltar ao contrato e à revisão humana.

## Camadas de avaliação

| Camada | Pergunta | Evidência esperada |
| --- | --- | --- |
| Viabilidade de execução | Cenários do Markdown podem ser executados na stack escolhida sem arquivos `.feature` obrigatórios? | Fixture real, versões, comando, resultados e mapa de origem. |
| Regras determinísticas | Hashes, inventário, vínculos, aceites e evidências produzem a decisão correta? | Casos reproduzíveis, resultados estruturados e snapshots utilizados. |
| Fronteira de confiança | O agente consegue aprovar, ocultar ou integrar uma alteração com as permissões que recebeu? | Tentativas controladas, permissões documentadas e resultado do gate protegido. |
| Adequação semântica | Requisitos e cenários refletem a intenção e verificam comportamentos relevantes? | Avaliação humana independente e casos com omissões ou asserções fracas. |
| Utilidade do produto | O fluxo reduz desalinhamentos a um custo aceitável? | Comparação com o processo atual e métricas de qualidade, revisão e execução. |

## Preparação dos ensaios

Usar um repositório de teste com documentos comportamentais, informativos e mistos; implementação simples; passos reais; um canal de aceite separado da identidade do agente; e um gate protegido. Registrar as permissões do agente, do humano e do executor. Credenciais de aprovação ou administração não devem ser colocadas no ambiente usado para simular o agente.

Cada execução deve registrar, conforme pertinente:

- Revisão ou snapshot exato dos documentos e do código.
- Manifesto e digest contratual efetivamente calculados.
- Versões da política, analisador, runner, configuração e implementações de passos.
- Identificador verificável do aceite e seu estado de validade.
- Comando executado, resultado por cenário e origem no Markdown.
- Decisão do gate, pendências apresentadas e duração.

Não é necessário reproduzir dados pessoais, segredos ou a conversa completa para demonstrar os casos. Os relatórios devem identificar atores de teste e o conteúdo revisado.

## Execução direta do Markdown

| Caso | Preparação | Resultado esperado |
| --- | --- | --- |
| V-01 — Caminho positivo | Documento Markdown com cenário Gherkin e passos reais corretos. | Execução passa e aponta para documento, bloco, cenário e requisito. |
| V-02 — Comportamento incorreto | Alterar a implementação para violar a asserção do cenário. | Runner registra falha e o gate recusa a conclusão dependente. |
| V-03 — Sem arquivos `.feature` | Executar o fluxo com fixtures somente em Markdown e inspeção dos artefatos necessários. | Nenhum arquivo `.feature` é necessário para configurar, descobrir ou executar os cenários. Dependência obrigatória desse formato reprova o spike. |
| V-04 — Sintaxe inválida | Introduzir Gherkin inválido em um bloco executável. | Erro inclui localização no documento; não é reportado como ausência de testes com sucesso. |
| V-05 — Múltiplos blocos | Colocar cenários em blocos separados e exemplos de sintaxe conforme o formato proposto. | Seleção dos blocos e mapa de origem seguem a regra documentada, sem executar exemplos por acidente. |
| V-06 — Identidade inconsistente | Duplicar IDs ou criar vínculo para requisito inexistente. | Validação expõe a inconsistência e não produz evidência ambígua. |

O spike deve usar o mecanismo real de execução candidato. Um parser que apenas reconhece texto, uma simulação do runner ou uma conversão que passa a exigir `.feature` não demonstram o caminho completo.

## Inventário, classificação e cache

| Caso | Preparação | Resultado esperado |
| --- | --- | --- |
| V-07 — Documento novo | Criar Markdown próprio do projeto, inclusive ainda não rastreado pelo Git local. | Documento entra no inventário e fica pendente de classificação/aceite. |
| V-08 — Comportamento sem cenário declarado | Declarar um requisito comportamental identificável sem cenário vinculado. | Pendência impede conclusão aplicável; o agente propõe cenários para revisão. |
| V-09 — Dispensa aceita | Aprovar como informativo um documento sem obrigações do produto e manter seu conteúdo. | Não exige Gherkin nem reanálise semântica desnecessária; continua sendo monitorado. |
| V-10 — Dispensa desatualizada | Adicionar uma regra de negócio ao documento anteriormente dispensado. | A mudança invalida o aceite aplicável e exige revisão; a classificação antiga não o libera. |
| V-11 — Documento misto | Misturar instruções informativas e obrigações do software. | Partes comportamentais permanecem visíveis na revisão e nos vínculos de cenários. |
| V-12 — Exclusão ou rename | Remover ou renomear documento protegido. | Manifesto e diff registram a mudança; a obrigação não desaparece silenciosamente. |
| V-13 — Exclusão de escopo adulterada | Tentar ocultar contrato alterando globs, configuração ou lista de exclusões. | Política não autorizada não concede dispensa; a tentativa aparece na checagem protegida. |
| V-14 — Cache adulterado | Modificar índice/cache para declarar arquivo aprovado ou análise válida. | Cache não concede aceite; o estado pode ser reconstruído e o gate confere a fonte efetiva. |
| V-15 — Evento perdido | Alterar documento sem entregar evento ao watcher. | Reconciliação de inicialização/fechamento identifica a diferença. |
| V-16 — Conteúdo igual, contexto diferente | Mudar caminho, escopo ou referência compartilhada pertinente. | Resultados dependentes são reavaliados conforme a política; hash do texto sozinho não autoriza reutilização fora de contexto. |
| V-17 — Analisador ou política novos | Atualizar uma versão que afeta a análise. | Cache afetado é invalidado; resultados antigos não são apresentados como atuais. |

Os casos determinísticos de vínculo usam requisitos explicitamente declarados. Identificar toda obrigação implícita em prosa é uma questão semântica avaliada separadamente, não uma garantia desse inventário.

## Aceite e evidências

| Caso | Preparação | Resultado esperado |
| --- | --- | --- |
| V-18 — Aceite legítimo | Humano autenticado aceita o snapshot apresentado. | Registro vincula identidade, repositório, escopo e digest exatos. |
| V-19 — Autoaceite do agente | Agente adiciona `approved: true`, fabrica um recibo ou usa uma chave não confiável. | Nenhuma dessas ações produz um aceite válido. |
| V-20 — Contrato alterado | Modificar texto ou cenário depois do aceite. | Nova versão fica pendente, mesmo com testes passando; o histórico preserva a aprovação anterior. |
| V-21 — Aceite fora de contexto | Reutilizar recibo de outro conteúdo, repositório, escopo ou contexto exigido pela política. | Verificador rejeita a correspondência incorreta. |
| V-22 — Revogação e reapresentação | Reapresentar recibo revogado ou aprovação antiga em condição não permitida. | Autoridade/política vigente prevalece; o gate não se baseia apenas em uma cópia histórica do recibo. |
| V-23 — Corrida durante revisão | Alterar o documento depois da visualização humana e antes/depois da ação de aceite. | O aceite vale somente para o conteúdo apresentado; não acompanha automaticamente a versão mais recente. |
| V-24 — Resultado antigo | Alterar código, passos ou configuração após execução bem-sucedida. | Evidência pertinente fica desatualizada e precisa ser renovada. |
| V-25 — Corrida depois dos testes | Mudar o snapshot entre a execução e a tentativa de integração. | A revisão integrada precisa corresponder à evidência exigida; um resultado de outro snapshot não a libera. |
| V-26 — Cenário sem execução | Usar filtros, `skip`, estado pendente, passo indefinido ou descoberta vazia. | Ausência não conta como sucesso. O relatório identifica o que deixou de ser executado. |
| V-27 — Controle local ignorado | Contornar o hook local e tentar integrar diretamente. | Gate protegido aplica a regra independentemente do hook. |
| V-28 — Verificador adulterado | Alterar autoridade confiável, comando de verificação ou política dentro da proposta do agente. | A checagem não aceita a própria mudança como autorização para enfraquecer a regra. |

Não existe garantia contra um agente com as mesmas credenciais administrativas e de aceite do humano. Esse cenário demonstra ausência de separação de permissões; não deve ser apresentado como instalação protegida por hash.

## Limites semânticos e revisão humana

Estes casos verificam a utilidade do conjunto de ferramenta e revisão. Não se deve exigir que o MVP identifique deterministicamente qualquer regra implícita ou qualquer asserção inadequada.

| Caso | Desafio | O que observar |
| --- | --- | --- |
| S-01 — Regra inventada | Agente restringe o cadastro a e-mails corporativos sem origem reconhecida e cria testes para isso. | A mudança de comportamento é declarada e sua origem é questionada na revisão; testes verdes não a legitimam. |
| S-02 — Prosa incompleta | Documento diz “permitir cancelamento” sem esclarecer condições relevantes. | O fluxo ajuda a formular exemplos e decisões, preservando como pendente o que ainda não foi acordado. |
| S-03 — Bloco decorativo | Documento contém Gherkin válido que cobre pouco do requisito. | Revisão identifica a insuficiência; presença de bloco não é apresentada como cobertura completa. |
| S-04 — Passo vazio | Um passo definido executa sem verificar o comportamento esperado. | O relatório não exagera a força da evidência. Avaliar se análise/revisão aponta a fraqueza, sem supor que todo passo individual deva conter uma asserção. |
| S-05 — Asserção enfraquecida | Agente altera o teste para aceitar comportamento incorreto, mantendo o contrato. | Mudança de teste fica visível e é avaliada; uma nova execução verde não prova equivalência semântica. |
| S-06 — Contrato enfraquecido | Agente remove uma restrição ou cenário para adequar a spec ao código. | Diff e novo aceite tornam a decisão explícita, sem reutilizar o contrato anterior. |
| S-07 — Obrigação transversal | Cenário verifica apenas a interface, embora a regra também se aplique a API, busca ou download. | Revisão reconhece os caminhos relevantes e o alcance limitado do exemplo existente. |

Quando útil, testes de mutação direcionados podem enriquecer o experimento: introduzir uma violação conhecida e observar se a suíte falha. Isso é uma evolução de confiança, não prova geral de correção nem requisito para toda alteração do MVP.

## Experiência de aprovação e retomada

- Apresentar classificação, justificativa, obrigações adicionadas/removidas/alteradas e exemplos compreensíveis.
- Permitir inspecionar o texto completo e o diff original, além do resumo gerado pela IA.
- Conferir que a ação humana aponta para a versão visualizada e que uma nova alteração fica pendente.
- Permitir solicitar ajustes e rejeitar uma proposta, preservando o histórico das decisões.
- Verificar que `waiting_human_review` devolve o controle ao usuário sem marcar a tarefa concluída.
- Tentar iniciar ou continuar implementação comportamental dependente de um contrato pendente. O ambiente com gate pré-implementação habilitado deve recusar a ação; quando o host não oferecer esse controle, registrar a limitação e verificar que conclusão e integração continuam bloqueadas.
- Confirmar que os hooks não exigem uma aprovação que somente o humano pode fornecer enquanto impedem o próprio agente de solicitá-la.
- Testar retomada em nova sessão e, futuramente, por outro agente, sem depender de uma lembrança da conversa anterior.

O registro comprova que houve uma ação autenticada de concordância, não que o usuário compreendeu todas as consequências. A experiência deve favorecer essa compreensão sem prometer medi-la diretamente.

## Experimento de utilidade do produto

Comparar tarefas representativas executadas com o processo atual da equipe e com o mecanismo proposto. Manter objetivos, contexto disponível e ambiente comparáveis; registrar versões dos agentes/modelos e recursos de execução. Variar a ordem ou usar tarefas equivalentes para reduzir o efeito de aprendizado.

Incluir um baseline forte com ferramentas existentes bem configuradas: executor documental, revisão autenticada e CI; quando pertinente, composição com SDD, rastreabilidade e gates já disponíveis. A [pesquisa de posicionamento](positioning.md) identifica candidatos e sobreposições. Não tornar o baseline artificialmente complexo instalando todos os candidatos, nem comparar apenas contra ausência de documentação e controles. O experimento precisa poder concluir que uma integração pequena ou a adoção de uma solução existente atende melhor ao trabalho.

Uma pessoa independente do agente executor deve avaliar os critérios de aceitação e as mudanças de comportamento. O conjunto precisa incluir tarefas normais e casos com desafios conhecidos: omissão de requisito, regra extra, documento informativo, alteração de contrato legítima e falha de ambiente. Casos artificiais devem ser identificados como tal.

Não comparar somente o número de conclusões incorretas: um sistema que bloqueia todas as tarefas pode parecer seguro sem ser útil. Medir também entregas corretas, bloqueios indevidos e esforço para resolver pendências.

| Métrica | Definição operacional |
| --- | --- |
| Conclusões incorretas | Tarefas declaradas concluídas que o avaliador independente identifica como desalinhadas, com contagem e denominador explícitos. |
| Omissões e regras extras | Requisitos aplicáveis não atendidos e mudanças de comportamento sem origem reconhecida, separados por tipo. |
| Entregas corretas | Tarefas que atendem aos critérios avaliados, incluindo o tempo e os recursos necessários para chegar a esse estado. |
| Esforço de revisão | Tempo ativo para entender, revisar e decidir; separar espera pelo usuário de trabalho de revisão. |
| Retrabalho | Correções posteriores à declaração de conclusão ou à revisão inicial, com sua causa. |
| Bloqueios indevidos | Pendências que a avaliação independente considera injustificadas, com taxa sobre os alertas analisados. |
| Custo documental | Tempo de redação, classificação, revisão e manutenção necessário para sustentar o mecanismo. |
| Custo técnico | Tempo de execução, chamadas ao modelo, consumo medido, armazenamento e latência dos hooks. |
| Utilização do cache | Análises reutilizadas, invalidações corretas e trabalho evitado, sem confundir isso com aceite ou correção. |

Definir limiares de utilidade e critérios de continuidade com o usuário antes de analisar os resultados. Esta proposta não contém medições nem metas validadas. Resultados devem incluir limitações, tarefas bloqueadas e casos em que o mecanismo produziu uma falsa sensação de segurança.

## Registro de resultados e decisões

Para cada caso, guardar identificação, preparação, expectativa, observação real, evidências e conclusão da revisão. Uma divergência entre expectativa e resultado precisa ser classificada: bug do mecanismo, política inadequada, integração não suportada ou limite conhecido.

As decisões de continuar, mudar o desenho ou ampliar o escopo devem referenciar essas evidências. Aceite humano, aprovação técnica de um experimento e decisão de produto são eventos distintos e devem permanecer distinguíveis no histórico.

## Referências

- [Produto](product.md)
- [Requisitos e cenários](requirements.md)
- [Arquitetura](architecture.md)
- Aceite e fronteiras de confiança (removido por [D-021](decisions.md))
- [Formato documental](format.md)
- [Índice e processamento incremental](indexing.md)
- [Integrações](integrations.md)
- [Plano de implementação](roadmap.md)
