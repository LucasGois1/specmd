# Plano de implementação

> Rascunho de planejamento. Nenhum marco abaixo representa funcionalidade implementada, suporte de plataforma verificado ou aceite humano do contrato final.

Este plano transforma a [proposta de produto](product.md) e os [requisitos](requirements.md) em entregas verificáveis. Alterações de comportamento descobertas durante a implementação devem voltar ao contrato para revisão; o backlog não deve se tornar uma segunda fonte de requisitos.

## Fronteira do primeiro produto

O MVP deve demonstrar um fluxo completo: descobrir Markdown, identificar pendências de classificação, ajudar o usuário a formular cenários, obter aceite de uma versão, suspender implementação comportamental dependente enquanto esse aceite estiver pendente, executar os cenários diretamente do Markdown e impedir a conclusão ou integração quando faltarem aceites ou evidências válidas. O suporte inicial precisa contemplar pelo menos Java, Python e Go, com adaptadores de execução próprios e limites verificados. A capacidade real de suspender ações locais deve ser demonstrada no host escolhido ou declarada como limitação; o bloqueio protegido de integração permanece obrigatório.

O Markdown é a fonte canônica. O usuário não mantém arquivos `.feature`, e a execução não pode exigir sua criação como etapa intermediária obrigatória. A integração com um runner real deve ser demonstrada por parsing e adaptação em memória. Se o runner escolhido exigir arquivos `.feature`, o spike deve registrar essa incompatibilidade e avaliar outro mecanismo, sem flexibilizar silenciosamente o requisito.

O agente pode propor contratos, cenários e dispensas. A autoridade de aceite permanece separada de suas credenciais. Hooks locais orientam e controlam o fluxo conforme a capacidade real da plataforma; uma checagem protegida aplica a política de integração.

## Próximo experimento proposto

A [pesquisa dos runners](runner-feasibility.md) já produziu evidências iniciais de execução em Java, Python e Go. O próximo experimento deve integrar o fluxo em um caso pequeno, como cancelamento de pedido, com poucos requisitos e cenários no mesmo Markdown.

A recomendação para a primeira fatia é reutilizar Go/Godog, cuja API pública de conteúdo em memória funcionou no protótipo. Isso não remove Java e Python do MVP nem estabiliza automaticamente o formato ou a stack do núcleo. O primeiro ambiente de agentes deve ser escolhido após verificar seus hooks; o canal real de aceite precisa manter a autoridade humana fora das permissões do agente.

A demonstração deve permitir concluir com contrato aceito e cenários executados com sucesso; pedir novo aceite após mudança contratual; invalidar evidências pertinentes após mudança de código; e recusar cenários obrigatórios ausentes, filtrados, indefinidos ou ignorados. Deve também permitir aguardar revisão humana e retomar o trabalho sem declarar uma conclusão indevida. A checagem protegida permanece necessária para avaliar tentativas de contornar os controles locais.

Incluir uma tarefa em que o agente inventa uma regra, escreve testes verdes e propõe documentá-la depois. Avaliar se a revisão expõe essa decisão e permite ao humano rejeitá-la, sem prometer detecção automática infalível. Comparar as tarefas com revisão humana e CI bem configurados, medindo desalinhamentos, esforço de revisão e bloqueios indevidos conforme o [plano de validação](validation-plan.md).

Esse experimento demonstra o funcionamento conjunto e inicia a avaliação de utilidade. Os componentes acima ainda não estão implementados; esta recomendação não representa aceite humano de uma nova versão contratual.

## Marcos e dependências

| Marco | Objetivo | Dependências | Saída verificável |
| --- | --- | --- | --- |
| R0 — Reaproveitamento e posicionamento | Mapear o que MDG, ferramentas de SDD, rastreabilidade, reviews e gates existentes já resolvem. | [Pesquisa de antecedentes](positioning.md) e configuração comparável do problema. | Mapa de sobreposição e hipótese de lacuna; nenhum subsistema próprio é presumido necessário. |
| M0 — Viabilidade de execução | Demonstrar cenários reais vindos de Markdown em Java, Python e Go, sem arquivos `.feature` obrigatórios. | Seleção de candidatos a parser e runner por linguagem. | Em cada linguagem: cenário que passa, outro que falha, passo indefinido e origem corretamente reportada; ausência de cenários não recebe OK. |
| M1 — Decisões técnicas mínimas | Escolher a stack do núcleo, os runners e o primeiro ambiente de agentes, priorizando reutilização. | R0, resultados de M0 e verificação das capacidades das plataformas. | Decisões registradas, versões fixadas para o protótipo, componentes reaproveitados e limitações documentadas. |
| M2 — Núcleo e inventário | Produzir um inventário e manifesto determinísticos dos documentos no escopo. | M1 e política inicial de descoberta. | Mesma revisão gera o mesmo manifesto; adições, alterações, exclusões e renomeações são identificadas. |
| M3 — Classificação e revisão | Representar documentos comportamentais, informativos, mistos e pendentes. | M2 e proposta de formato. | Novo documento e documento alterado geram pendência; uma dispensa depende de aceite válido da versão. |
| M4 — Aceite autenticado | Vincular uma decisão humana ao conteúdo e escopo revisados. | M2, M3 e definição da autoridade confiável. | O agente não consegue emitir um aceite válido com suas próprias permissões; conteúdo alterado não herda o aceite anterior. |
| M5 — Extração e execução | Integrar parsing, IDs, mapa de origem e adaptadores Java, Python e Go demonstrados em M0. | M0, M1 e formato estabilizado para o MVP. | Resultados normalizados por cenário apontam para documento, bloco e requisito nas três linguagens; não há cópia `.feature` a manter. |
| M6 — Evidências e decisão de conclusão | Relacionar contrato aceito, código executado e resultados atuais. | M4 e M5. | Resultado antigo, cenário ignorado, passo ausente ou contrato pendente impedem uma conclusão válida conforme a política. |
| M7 — Primeiro adaptador | Conectar o núcleo a um ambiente de agentes verificado. | M6 e matriz de capacidades do ambiente escolhido. | Fluxo permite revisão humana e retomada, diferencia espera de conclusão e não entra em ciclos de hooks. |
| M8 — Integração protegida | Aplicar a mesma política fora do controle do agente. | M6 e definição das permissões no provedor Git/CI. | Ignorar hooks locais não permite integrar uma revisão que viole o gate protegido. |
| M9 — Piloto de produto | Comparar o fluxo com o processo atual de desenvolvimento. | M7, M8 e protocolo de avaliação definido previamente. | Dados sobre conclusões incorretas, revisão humana, bloqueios indevidos e custo do mecanismo. |

M4 e M5 podem avançar em paralelo depois que o formato necessário estiver acordado. M7 só deve prometer bloqueios que o ambiente realmente oferece. M8 pode exigir infraestrutura ou configuração fora do repositório; essa dependência precisa estar explícita no piloto.

## Trabalho de cada marco

### M0 — Spike técnico que precede o compromisso com uma stack

- Criar um fixture Markdown com Gherkin e implementações de passos reais na stack candidata.
- Extrair blocos por um parser de Markdown, preservando posições no arquivo original.
- Interpretar Gherkin e alimentar o mecanismo de execução em memória, usando interfaces suportadas ou assumindo explicitamente o custo de manter um adaptador.
- Demonstrar resultados positivos, negativos e de passos indefinidos, com correspondência entre tags e origem.
- Verificar que nenhum arquivo `.feature` é necessário para configurar ou executar o fixture.
- Registrar versões, APIs utilizadas, limitações e risco de manutenção. Não apresentar esse experimento como integração completa com Claude Code ou Codex.

### M2–M3 — Descoberta e classificação antes da análise cara

- Definir um escopo inicial de documentos próprios do projeto e uma política protegida de exclusão de dependências e arquivos gerados.
- Incluir documentos novos e ainda não rastreados pelo Git no trabalho local.
- Calcular hashes sobre conteúdo bem definido e gerar o manifesto em serialização determinística.
- Manter o índice local reconstruível e separado dos aceites.
- Registrar a classificação proposta, os requisitos e as relações conhecidas, sem tratar uma sugestão da IA como decisão humana.
- Invalidar análises afetadas por mudanças de conteúdo, contexto, política, analisador ou referências compartilhadas.
- Permitir revisão por conjunto coerente de mudanças, com acesso ao conteúdo completo e ao diff original.

### M4 — Aprovação de uma versão identificável

- Escolher um canal autenticado no qual o agente possa solicitar, mas não conceder, o aceite.
- Associar a decisão à identidade do usuário, repositório, escopo, hash revisado, revisão apresentada e momento da ação.
- Definir como consultar validade e revogação e qual regra vale para reapresentar uma versão anteriormente aceita.
- Proteger as autoridades confiáveis e a política de verificação contra alterações feitas pelo próprio agente.
- Manter o aceite de uma versão anterior no histórico sem usá-lo para autorizar conteúdo novo.
- Tratar dispensas de Gherkin como decisões sujeitas ao mesmo vínculo de versão.

### M5–M6 — Verificação sem segunda fonte documental

- Validar sintaxe, identidade de requisitos e cenários e vínculos declarados.
- Distinguir bloco executável de exemplo de sintaxe conforme o [formato proposto](format.md).
- Relacionar resultados ao contrato, revisão do código, implementações dos passos, configuração e runner utilizados.
- Expor cenários não encontrados, filtrados, ignorados, pendentes ou sem implementação. Ausência de execução não conta como sucesso.
- Invalidar evidências pertinentes depois de alterações no código ou no mecanismo de teste.
- Tornar visíveis mudanças de contrato e de testes que possam enfraquecer a obrigação.
- Explicar o alcance da evidência: executar cenários não prova a completude da especificação nem a qualidade de todas as asserções.

### M7–M8 — Integração com agentes e aplicação da política

- Documentar os eventos efetivamente disponíveis e suas capacidades: observar, fornecer feedback, interromper uma ação ou bloquear uma transição.
- Executar descoberta e checks baratos durante o trabalho e reservar verificações mais caras para mudanças relevantes e pontos de conclusão.
- Representar explicitamente `waiting_human_review`. Devolver o controle ao usuário nesse estado é permitido; declarar a tarefa concluída não é.
- Aplicar o gate pré-implementação ao trabalho comportamental dependente de contrato pendente; distinguir bloqueio real de orientação e registrar limitações do host.
- Reconciliar o estado efetivo no fechamento, sem confiar apenas em eventos de um watcher ou no cache.
- Configurar a checagem protegida sobre a revisão que será integrada e testar tentativas de contornar os hooks locais.
- Documentar o que a instalação local não consegue garantir quando o agente controla o próprio ambiente.

## Critérios de saída do MVP

- [ ] Existe uma demonstração ponta a ponta com cenários executados diretamente do Markdown.
- [ ] Adaptadores de execução Java, Python e Go têm versões e limites verificados; parsing sozinho não conta como execução.
- [ ] Não é necessário manter nem materializar arquivos `.feature` para usar essa demonstração.
- [ ] Documentos novos, alterados e dispensados têm estados distintos e rastreáveis.
- [ ] O usuário revisa o conteúdo exato ao qual seu aceite será vinculado.
- [ ] O agente não pode produzir esse aceite com as credenciais disponíveis no cenário de instalação declarado.
- [ ] A conclusão exige aceite aplicável e evidências atuais, com falhas e ausências explícitas.
- [ ] O estado de espera por usuário não causa uma falsa conclusão nem um ciclo de encerramento.
- [ ] A suspensão pré-implementação foi demonstrada no host escolhido ou sua ausência de suporte foi declarada, sem prometer prevenção local inexistente.
- [ ] O primeiro adaptador tem capacidades verificadas, sem presumir equivalência entre Claude Code e Codex.
- [ ] O gate protegido identifica violações mesmo quando os hooks locais não são usados.
- [ ] Os casos determinísticos e os limites semânticos do [plano de validação](validation-plan.md) foram exercitados e registrados.

Esses itens são critérios planejados. As caixas permanecem desmarcadas até existirem evidências e revisão correspondentes.

## Expansões depois do piloto

As seguintes oportunidades ficam fora do compromisso inicial, salvo decisão explícita de escopo:

- Segundo adaptador de agente, reutilizando o núcleo e a política.
- Revisão de PR organizada por requisito, mudança de comportamento e evidências.
- Continuidade entre sessões e coordenação de obrigações entre múltiplos agentes.
- Sugestões de impacto a partir de relações entre documentos, módulos e testes.
- Testes de mutação direcionados e revisão assistida da força das asserções.
- Transformação de incidentes em cenários de regressão e registro de justificativas.
- Adaptadores para verificações de API, acessibilidade, arquitetura e desempenho.
- Comparação de agentes e modelos por atendimento aos critérios, esforço humano e custo.
- Visões de prontidão de release e verificações pertinentes após deploy.

Cada expansão deve justificar o problema observado, reutilizar os vínculos existentes e apresentar benefício líquido frente ao esforço de manutenção. Não se pretende construir simultaneamente uma plataforma de requisitos, um orquestrador completo e uma suíte geral de testes.

## Decisões ainda em aberto

| Decisão | O que precisa ser resolvido |
| --- | --- |
| Stack e runner inicial | Escolha após demonstrar execução real em memória e manutenção viável do adaptador. |
| Primeiro ambiente de agentes | Seleção após verificar APIs e capacidades das versões candidatas. |
| Autoridade de aceite | Serviço próprio, mecanismo do provedor Git ou outra solução autenticada com separação de permissões. |
| Forma de hospedagem | Definir o que pode operar localmente e qual autoridade/verificador precisa existir fora do alcance do agente. |
| Política de reaproveitamento e revogação | Estabelecer validade de aceites antigos, contexto, escopo e revogações. |
| Escopo do bloqueio | Tarefa, trabalho dependente ou projeto inteiro, além do bloqueio de integração. |
| Sintaxe e granularidade | Estabilizar documento versus seção, marcação de blocos executáveis e referências permitidas. |
| Licença | Escolher explicitamente antes de anunciar condições de uso ou distribuição. |
| Metas do piloto | Definir limiares de utilidade e custo antes de analisar os resultados. |

## Referências

- [Requisitos e cenários](requirements.md)
- [Arquitetura](architecture.md)
- [Aceite e fronteiras de confiança](approval-and-trust.md)
- [Formato documental](format.md)
- [Índice e processamento incremental](indexing.md)
- [Integrações com agentes](integrations.md)
- [Plano de validação](validation-plan.md)
