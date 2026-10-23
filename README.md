# SpecMD

Documentação canônica em Markdown, aceite humano versionado e evidências de execução para desenvolvimento com agentes de IA.

> **Estado do projeto:** concepção e planejamento. Este repositório documenta o produto a implementar. Ainda não há CLI, plugin, serviço de aceite ou executor funcional. A publicação destes documentos não constitui aceite contratual das versões aqui descritas.

## O problema

Agentes podem deixar de atender requisitos documentados, interpretar uma regra incorretamente ou introduzir comportamentos que ninguém solicitou. Um teste escrito pelo agente pode proteger uma suposição indevida e passar a funcionar como uma especificação implícita. Código, testes e documentação podem concordar entre si e ainda divergir da intenção do usuário.

O projeto propõe tornar explícita a relação entre **intenção reconhecida, contrato aceito, comportamento implementado e evidência atual de verificação**.

## A proposta

- Escrever explicações, requisitos e cenários Gherkin no mesmo Markdown.
- Executar os cenários a partir desse Markdown, sem depender de arquivos `.feature` mantidos pelo usuário ou de sua geração como etapa obrigatória.
- Identificar cada documento e requisito, mantendo vínculos com cenários e mudanças de comportamento.
- Exigir aceite humano autenticado para uma versão específica do contrato, inclusive suas classificações e dispensas.
- Detectar alterações por hashes determinísticos e invalidar aceites ou evidências conforme o que mudou.
- Impedir a conclusão de tarefas quando faltarem aceites ou verificações exigidas pela política.
- Integrar o mecanismo ao trabalho de agentes por adaptadores e hooks, com uma checagem protegida de integração.
- Manter um inventário incremental para evitar análises repetidas sem ignorar mudanças relevantes.

Gherkin é a linguagem dos cenários; Cucumber é um possível mecanismo de execução. **Não se presume suporte nativo de Cucumber a Markdown.** O primeiro experimento técnico precisa demonstrar a integração por parsing e adaptação em memória, preservando a origem dos cenários no `.md`.

## Fluxo pretendido

1. Descobrir os documentos próprios do projeto e aplicar a política de escopo.
2. Propor a classificação de documentos novos ou alterados.
3. Discutir ambiguidades e escrever cenários para os requisitos comportamentais.
4. Apresentar a versão e seu diff ao usuário para aceite.
5. Implementar o comportamento acordado e executar as verificações.
6. Relacionar resultados ao contrato e à revisão de código efetivamente verificados.
7. Liberar a conclusão somente quando as condições aplicáveis forem atendidas.

Documentos informativos podem receber dispensa de Gherkin, mas essa classificação também exige aceite e continua sendo monitorada. Um agente pode aguardar uma decisão humana sem declarar a tarefa concluída.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [Produto](docs/product.md) | Problema, público, proposta, limites e oportunidades. |
| [Requisitos e cenários](docs/requirements.md) | Obrigações identificadas e critérios de aceite em Gherkin no próprio Markdown. |
| [Formato documental](docs/format.md) | Proposta de metadados, IDs, blocos e documentos mistos. |
| [Arquitetura](docs/architecture.md) | Componentes, fluxos e vínculos entre contrato, aceite e evidência. |
| [Aceite e confiança](docs/approval-and-trust.md) | Hashes, identidades, permissões, auditoria e proteção contra bypass. |
| [Indexação](docs/indexing.md) | Inventário, cache, invalidação e reconciliação. |
| [Integrações](docs/integrations.md) | Núcleo CLI e adaptadores propostos para agentes e CI. |
| [Plano de implementação](docs/roadmap.md) | Marcos, dependências e entregas verificáveis. |
| [Plano de validação](docs/validation-plan.md) | Experimentos, casos negativos e métricas. |
| [Decisões e pendências](docs/decisions.md) | Diretrizes da discussão e escolhas ainda abertas. |

Exemplos de formato: [contrato comportamental](examples/cancellation.contract.md) e [documento informativo](examples/editor-setup.reference.md). São ilustrações sem aceite autenticado ou execução implementada.

## Limites das garantias

- Hash identifica conteúdo; autenticação e separação de permissões estabelecem quem pode aceitá-lo.
- Um bloco Gherkin presente não demonstra que todos os requisitos foram identificados.
- Testes passando demonstram os cenários exercitados, sem comprovar toda a intenção do usuário.
- Análise com IA pode sugerir lacunas e contradições; suas inferências não concedem aceite.
- Hooks locais ajudam a orientar o agente. Bloqueios contra bypass precisam de uma fronteira de permissões que o agente não possa alterar.
- A autoria declarada em um commit Git não substitui a identidade autenticada de quem submeteu ou aprovou a mudança.

## Como começar a implementação

Leia o [plano de implementação](docs/roadmap.md). O primeiro marco é provar a execução de um cenário definido em Markdown sem exigir `.feature`, antes de assumir uma integração específica de runner. Stack, primeiro adaptador, mecanismo de aprovação e licença permanecem em aberto.

Não há comandos de instalação ou execução disponíveis nesta etapa.
