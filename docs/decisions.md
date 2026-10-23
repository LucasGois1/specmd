# Decisões de concepção e questões em aberto

Este registro consolida a discussão que originou o projeto. As diretrizes abaixo foram expressas durante a concepção; isso não equivale a um recibo autenticado de aceite do conteúdo destes arquivos. Os detalhes técnicos continuam sendo propostas para revisão e experimentação.

## Diretrizes da discussão

| ID | Diretriz | Consequência |
| --- | --- | --- |
| D-001 | Markdown é a fonte canônica. | Explicação, requisitos e cenários permanecem no `.md`; nenhuma cópia editável `.feature` é necessária. |
| D-002 | A execução não deve depender de arquivos `.feature`. | Demonstrar parsing e adaptação em memória; não assumir suporte nativo de Cucumber a Markdown. |
| D-003 | O alinhamento precisa ser verificado nos dois sentidos. | Relacionar requisitos à implementação e mudanças relevantes de comportamento a uma intenção reconhecida. |
| D-004 | Documentar uma suposição não a autoriza. | Distinguir comportamento acordado, proposta do agente e comportamento apenas observado no legado. |
| D-005 | O contrato precisa de aceite humano explícito. | Vincular a decisão à versão apresentada, inclusive na especificação escrita em conjunto. |
| D-006 | Alterar documentação contratual ou cenários exige nova revisão. | A versão aceita anterior não autoriza automaticamente uma nova versão. |
| D-007 | Alterar código exige renovar evidências pertinentes. | Preservar o aceite quando a intenção não mudou; evitar aprovações humanas repetidas para tentativas de implementação. |
| D-008 | O agente não pode emitir seu próprio aceite. | Separar as permissões de propor, aceitar e aplicar o gate. |
| D-009 | Conteúdo, revisão e autoria precisam de rastreabilidade. | Usar identidade de conteúdo, diff, histórico Git e identidade autenticada dos eventos. |
| D-010 | Documentos podem ser comportamentais, informativos ou mistos. | Exigir cenários das obrigações comportamentais e aceite da dispensa informativa. |
| D-011 | Dispensa de Gherkin não é exclusão do inventário. | Monitorar documentos informativos para detectar mudanças que exijam revisão. |
| D-012 | Hooks devem melhorar a experiência com agentes. | Conectar análises a eventos suportados, sem presumir equivalência entre Claude Code e Codex. |
| D-013 | Aguardar o usuário é um estado legítimo. | Permitir devolução de controle sem marcar conclusão ou entrar em ciclos de bloqueio. |
| D-014 | A análise deve ser incremental. | Reutilizar resultados válidos, mantendo reconciliação e invalidação corretas. |
| D-015 | O índice não concede aprovação. | Tratar inventário e cache como dados derivados e reconstruíveis. |
| D-016 | A classificação automática é auxiliar. | Separar checagens determinísticas de sugestões semânticas e decisões humanas. |
| D-017 | O nome escolhido pelo usuário é SpecMD. | Usar `specmd` como nome do repositório e da interface proposta. Disponibilidade global de marca ou pacote não foi verificada. |
| D-018 | O suporte inicial precisa contemplar pelo menos Java, Python e Go. | Pesquisar e testar adaptadores reais por linguagem antes de estabilizar a arquitetura; não presumir um parâmetro universal de Cucumber. |
| D-019 | O usuário solicitou investigar sobreposição com Markdown with Gherkin antes de avançar. | A pesquisa encontrou antecedentes adicionais; comparar reutilização e a menor integração necessária, sem presumir novidade ou vantagem de um produto independente. |

## Escolhas técnicas propostas

Estas escolhas são hipóteses de implementação, sujeitas à validação:

- Núcleo CLI independente, com saída estruturada e adaptadores pequenos para cada agente.
- Markdown comum com frontmatter e blocos Gherkin identificados.
- SHA-256 dos bytes dos documentos e manifesto determinístico contendo caminhos e hashes.
- Aceites externos autenticados, ou artefatos assinados cuja autoridade permaneça fora do alcance do agente.
- Evidência de execução vinculada ao contrato, código, testes, configuração e ambiente pertinentes.
- Checagem protegida de integração além dos hooks locais.
- Índice local reconstruível; começar com armazenamento simples antes de otimizar consultas.
- Escopo e política protegidos para impedir autoisenção, exclusões silenciosas ou substituição do verificador.

## Decisões ainda abertas

| Questão | Como decidir |
| --- | --- |
| Licença | Decisão explícita do mantenedor; visibilidade pública não escolhe uma licença automaticamente. |
| Linguagem e distribuição do núcleo | Comparar integração do parser/runner, instalação e manutenção. |
| Runner inicial | Spike demonstrando execução em memória, origem no Markdown e resultados estruturados. |
| Primeiro agente integrado | Verificar APIs e hooks reais, suas versões e capacidade de bloquear eventos. |
| Interface e armazenamento de aceites | Demonstrar identidade, conteúdo exato revisado, revogação e separação de credenciais. |
| Granularidade dos aceites | Comparar aceite por documento, requisito ou conjunto, sem perder o contexto aprovado. |
| Política de reaproveitamento de aceites | Definir efeitos de renomeação, retorno a conteúdo antigo, mudança de contexto e revogação. |
| Política de bloqueio | Definir o que pausa implementação, conclusão da tarefa ou integração, e o alcance das dependências. |
| Requisitos não funcionais | Escolher adaptadores específicos quando Gherkin não for o mecanismo adequado. |
| Compatibilidade de formato | Comparar MDG oficial com blocos Gherkin cercados e estabilizar schema somente após testes; não criar um dialeto concorrente por padrão. |

## Evoluções a considerar após o núcleo

- Contexto da tarefa preparado a partir dos contratos aplicáveis.
- Revisão de mudanças orientada a requisitos, evidências e alterações de contrato.
- Continuidade entre sessões e agentes com pendências e evidências atuais.
- Conversão de incidentes e bugs em cenários de regressão e justificativas registradas.
- Análise de impacto com cobertura e incertezas explícitas.
- Testes de mutação direcionados para avaliar a força das verificações.
- Comparação de agentes por atendimento aos critérios, retrabalho e esforço de revisão.
- Verificadores de compatibilidade, acessibilidade, arquitetura e desempenho.

Essas capacidades não integram automaticamente o MVP. Sua inclusão depende de demonstrar benefício no [plano de validação](validation-plan.md) e de manter a sequência do [roadmap](roadmap.md).
