# SpecMD — proposta de produto

**Estado:** concepção de produto para revisão humana, preservando o contexto das decisões. Já existe uma implementação experimental 0.2.0; o [estado atual](implementation-status.md) e o [handoff](../HANDOFF.md) distinguem código, evidências e lacunas. Estes documentos não constituem contrato aprovado. O nome SpecMD foi escolhido pelo usuário.

Este documento registra o entendimento desenvolvido na conversa de descoberta. “Confirmado na conversa” significa que uma direção foi solicitada ou explicitamente adotada durante a discussão; não significa que o usuário aprovou esta redação, os cenários ou uma futura implementação.

## Problema

No desenvolvimento com agentes de IA, a intenção do usuário, a documentação, o código e os testes podem divergir. A presença de uma especificação no repositório não garante que o agente a consultou, a interpretou corretamente ou preservou suas restrições ao fazer uma mudança.

A divergência também ocorre no sentido inverso: o agente pode criar um comportamento que não foi solicitado, escrever testes para esse comportamento e apresentar a tarefa como concluída. Os testes passam a proteger uma premissa introduzida pelo próprio agente. Documentar essa premissa depois registra a decisão, mas não a autoriza.

Exemplo: um pedido de cadastro com e-mail resulta em uma implementação que aceita apenas e-mails corporativos. Se o agente cria testes para essa restrição, código e testes concordam entre si, mas a mudança continua sem uma origem reconhecida na intenção do usuário.

O problema não começou com agentes. A hipótese de produto é que a velocidade e a autonomia do desenvolvimento agêntico aumentam a necessidade de tornar essas divergências visíveis antes da conclusão de uma tarefa.

## Público e trabalho a realizar

O público inicial são desenvolvedores e equipes que usam agentes de programação, especialmente em fluxos com Claude Code e Codex, e precisam revisar o que esses agentes entregam.

O trabalho a realizar é: **permitir que um agente conclua uma mudança somente quando houver um contrato humano aceito para o escopo e evidências atuais de que a implementação corresponde aos cenários aplicáveis, expondo comportamentos adicionais sem origem reconhecida.**

O sistema deve ajudar o humano a responder:

1. Qual comportamento estou aceitando e o que mudou desde o último aceite?
2. De onde veio cada obrigação relevante implementada?
3. Quais cenários foram verificados para esta versão do código?
4. O que impede a conclusão e qual ação resolve a pendência?

## Direções confirmadas na conversa

- **Markdown como fonte canônica.** Requisitos, explicações e cenários Gherkin ficam nos arquivos `.md` do projeto. Nenhum arquivo `.feature` é exigido no repositório ou como etapa necessária da execução. O desenho deve consumir os blocos dos Markdown por parser/AST e um adaptador em memória; a viabilidade de cada executor ainda precisa ser demonstrada.
- **Aceite humano obrigatório.** Criação ou alteração de documentação e cenários dentro do escopo protegido exige revisão e aceite, inclusive quando a especificação é escrita junto com o agente.
- **Aceite vinculado à versão.** Um hash determinístico identifica o conteúdo relevante. Uma versão modificada precisa de novo aceite; o agente não pode aprovar sua própria mudança.
- **Rastreabilidade nos dois sentidos.** Cada requisito aplicável precisa de implementação e evidência; cada mudança relevante de comportamento precisa de origem reconhecida ou deve ser apresentada como proposta pendente.
- **Classificação explícita.** Um Markdown pode conter requisitos, ser informativo ou misturar trechos dos dois tipos. A dispensa de cenários exige uma decisão humana vinculada ao conteúdo revisado.
- **Inventário incremental.** Conhecer os Markdown existentes, seus hashes e classificações permite evitar análises semânticas repetidas. Arquivos informativos continuam monitorados para detectar mudanças.
- **Bloqueio de conclusão.** Pendências precisam ser visíveis ao agente, inclusive como `waiting_human_review`. Hooks e adaptadores devem aplicar a regra onde o host permitir; um gate protegido é necessário para impedir integração fora do controle do agente.
- **Auditoria e diff.** O usuário precisa ver o que mudou, quem propôs e quem efetivamente aprovou, distinguindo metadados Git de identidade autenticada.
- **Núcleo reutilizável.** Uma CLI e adaptadores de host devem compartilhar a política, sem presumir APIs ou capacidades idênticas entre Claude Code e Codex.

Os requisitos detalhados e seus cenários estão em [requirements.md](requirements.md). O formato de documentos e identificadores será descrito em [format.md](format.md).

## Fluxo proposto

O fluxo abaixo registra a intenção de produto. A versão experimental já possui comandos e estados, descritos no [guia rápido](quickstart.md); adequação da experiência e implantação protegida ainda precisam de validação.

1. O sistema reconcilia o inventário de Markdown com o snapshot do projeto e identifica arquivos novos, modificados, removidos ou renomeados.
2. O agente sugere classificação e, quando há obrigações, redige ou atualiza cenários no próprio Markdown. Inferências são apresentadas como propostas, com sua origem e suas dúvidas.
3. O humano recebe a versão exata, o diff e as mudanças de comportamento. Pode aceitar, pedir ajustes ou classificar conteúdo como informativo. Nenhuma dessas decisões é simulada pelo agente.
4. O canal confiável registra o aceite para conteúdo, caminhos e escopo específicos. A edição de um contrato aceito cria uma nova versão pendente.
5. A implementação e as evidências são relacionadas aos requisitos e cenários aplicáveis. Resultados antigos, cenários ignorados e obrigações sem origem aparecem como pendências.
6. O gate verifica o snapshot que será concluído ou integrado e devolve um resultado legível por humanos e ferramentas. A necessidade de aceite humano produz `waiting_human_review`, sem um loop de novas tentativas de autopreenchimento.

Um usuário não precisa escrever Gherkin pessoalmente. A interação deve permitir revisar regras e exemplos de negócio em linguagem legível, mantendo acesso ao texto exato aceito.

## Limites da garantia

O aceite registra concordância com uma formulação específica. Ele não prova compreensão integral, qualidade do requisito ou completude da intenção do usuário.

Um cenário presente e aprovado pode ter uma implementação de verificação fraca. Cenários passando demonstram apenas as condições exercitadas, no ambiente e no snapshot registrados. Verificar steps, asserções, dependências e configuração continua necessário.

Análise por IA pode sugerir requisitos omitidos, classificações suspeitas e comportamentos sem origem. Ela é heurística: não substitui o aceite autenticado nem constitui prova de cobertura semântica completa.

O hash identifica conteúdo; não autentica uma pessoa nem impede sozinho um bypass. A garantia de que o agente não pode aceitar a própria mudança depende de separar suas permissões das permissões do aprovador e do gate. O modelo está em [approval-and-trust.md](approval-and-trust.md).

Hooks não são considerados equivalentes entre hosts e não garantem, por si, controle sobre toda forma de encerrar uma sessão, editar o repositório ou integrar código. As limitações deverão aparecer em [integrations.md](integrations.md).

## Recorte proposto para o MVP

- Um repositório e uma política explícita de escopo protegido.
- Markdown com cenários Gherkin embutidos, IDs estáveis e interpretação por parser.
- Inventário, hashes, classificação humana e diff entre versão aceita e proposta.
- Um mecanismo autenticado de aceite fora da autoridade do agente, escolhido depois de validar a fronteira de confiança.
- Uma CLI com resultados estruturados, um adaptador de agente inicial e um gate de integração protegido.
- Adaptadores de execução cuja integração em memória seja comprovada por um spike antes de anunciar suporte.
- Suporte inicial a Java, Python e Go, com pesquisa e execução reais por linguagem antes de estabilizar os adaptadores. Uma engine não implica compatibilidade universal entre runtimes.
- Evidências ligadas ao snapshot, aos cenários e à versão do verificador.

Essa lista é proposta de implementação, não um compromisso de compatibilidade já demonstrada. A composição técnica está em [architecture.md](architecture.md), o inventário em [indexing.md](indexing.md) e a sequência de entrega em [roadmap.md](roadmap.md).

Não se pretende no MVP converter automaticamente toda documentação legada, comprovar toda propriedade descrita em linguagem natural, exigir aprovação de cada decisão interna de implementação ou substituir revisão humana, testes existentes e controles do provedor Git.

## Oportunidades adjacentes

As mesmas relações entre requisitos, snapshots e evidências podem sustentar revisão de PR por obrigação, continuidade entre sessões e agentes, análise de impacto e prontidão de release. Essas expansões devem ser avaliadas depois do núcleo. A primeira adjacência sugerida é um relatório de revisão que mostre mudanças de contrato e evidências por requisito.

A hipótese comercial ainda está aberta. Será preciso verificar frequência e custo das divergências, redução de revisão manual, precisão dos alertas e custo dos bloqueios indevidos. O desenho experimental está em [validation-plan.md](validation-plan.md).

A [pesquisa de antecedentes](positioning.md) encontrou sobreposição com documentação executável, rastreabilidade e gates existentes. O projeto deve comparar reutilização e integração antes de construir um formato, índice ou mecanismo de aprovação próprio. O ganho de experiência e qualidade ainda precisa ser demonstrado contra um baseline bem configurado.

## Questões ainda abertas

- Qual executor permite consumir os cenários extraídos dos Markdown em memória, sem exigir `.feature`, com relatórios adequados?
- Qual canal de aceite autenticado entrega separação real de permissões no ambiente inicial?
- Quais eventos e controles cada host oferece e quais limitações terão de ser comunicadas?
- Como selecionar requisitos aplicáveis e obrigações de preservação sem tornar uma tarefa responsável pelo backlog inteiro?
- Qual o limite inicial entre decisão técnica interna e mudança de contrato observável?
- Qual política de exceções, falhas de ambiente e verificação manual será aceitável sem permitir autoaprovação?
- Como medir o ganho de qualidade em comparação com testes, revisão e CI já usados pela equipe?

Nenhuma resposta pendente deve ser apresentada como capacidade implementada ou aceite humano deste repositório.
