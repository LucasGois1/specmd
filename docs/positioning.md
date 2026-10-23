---
specmd:
  schema: 1
  id: SMD-DOC-POSITIONING
  kind: reference
  exemption_reason: "Pesquisa comparativa e recomendações de concepção; não cria requisitos de produto aceitos."
---

# Posicionamento e antecedentes

**Estado:** pesquisa documental para revisão humana, consultada em 22 de outubro de 2026 no fuso America/Sao_Paulo. A classificação informativa acima é proposta e não constitui dispensa aceita. Este levantamento não implementa integrações nem altera os requisitos vigentes do projeto.

O objetivo é avaliar sobreposição de conceitos e engenharia antes de construir subsistemas que já existem. Foram consultadas fontes dos próprios projetos e documentação oficial, com commits ou tags fixados quando disponíveis. Não se trata de um levantamento exaustivo; ausência de uma capacidade no trecho consultado não demonstra que ela inexista no projeto ou em suas extensões.

## Conclusão da pesquisa

A proposta tem antecedentes importantes. Documentação executável em Markdown, especificação guiando agentes, rastreabilidade entre requisito e código, revisão humana e gates com hashes já aparecem em ferramentas existentes. Esses elementos, individualmente ou em algumas combinações, não sustentam uma afirmação de novidade do SpecMD.

O espaço a investigar é a utilidade de um fluxo integrado: o humano aceita uma versão e um escopo; documentos e dispensas continuam monitorados; mudanças relevantes têm origem reconhecida; evidências dos cenários correspondem ao código atual; o agente recebe uma pendência acionável antes de concluir. Essa é uma hipótese de benefício e experiência de uso, não uma vantagem já demonstrada nem uma afirmação de exclusividade.

Sobreposição conceitual ou funcional não comprova que uma alternativa seja madura, confiável ou adequada ao ambiente pretendido. Também não invalida a utilidade do SpecMD: qualidade da integração, manutenção e custo de uso precisam ser avaliados nos experimentos, separadamente da existência de antecedentes.

## Markdown with Gherkin oficial

O [documento oficial MDG no commit `0c50fc12112d9400892a760ee7302b232a466cb8`](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) descreve cenários em Markdown renderizável: usa `.feature.md`, cabeçalhos para os elementos Gherkin, listas para passos e tags entre crases. Também descreve renderização com resultados e anexos via Cucumber Messages. Portanto, juntar prosa, cenários e resultados em Markdown tem antecedente direto no próprio ecossistema Cucumber.

| Aspecto | MDG no documento consultado | Proposta atual do SpecMD |
| --- | --- | --- |
| Entrada | Dialeto Markdown com extensão `.feature.md`. | Markdown do projeto com blocos fenced `gherkin`. |
| Estrutura dos cenários | Cabeçalhos e listas Markdown. | Gherkin clássico dentro das cercas, extraído por parser. |
| Fonte de apresentação | Documento Markdown original, relacionado aos resultados. | Documento original e mapa de origem de cada bloco/cenário. |
| Portabilidade documentada | A nota limita o suporte descrito ao parser JavaScript, versão 19 ou posterior. | Java, Python e Go exigem validação própria de parser e integração com executor. |

A nota de suporte pertence ao snapshot citado: não permite extrapolar suporte atual de todos os parsers, descoberta por todos os runners ou compatibilidade universal. Ela também não demonstra impossibilidade de adaptar outros ecossistemas.

O [baseline posteriormente executado](../research/javascript-mdg/README.md) confirmou MDG nativo em Cucumber.js 13.3.0: descoberta de `.feature.md`, execução explícita de `.feature.md` e de `.md` comum, além de falha de asserção real. O Markdown com blocos fenced teve código 0 e zero cenários. As [provas de viabilidade nas outras linguagens](runner-feasibility.md) usaram adaptação em memória e não constituem suporte nativo uniforme à sintaxe MDG.

`.feature.md` continua sendo um arquivo Markdown; esse sufixo, por si, não cria o arquivo `.feature` intermediário proibido pelo desenho. A diferença relevante é a sintaxe de entrada e sua integração com o runtime. Um bloco fenced com Gherkin clássico não deve ser anunciado como MDG nativo sem um teste de compatibilidade.

O mesmo documento informa que o AST MDG omite descrições da prosa. Logo, a identidade do contrato do SpecMD precisa continuar baseada no Markdown original, com narrativa e metadados, e não apenas no AST executável. A sintaxe de cenários não cobre sozinha a política de classificação e aceite pretendida.

**Recomendação de investigação:** comparar MDG com a extração de blocos fenced antes de estabilizar o formato. Reutilizar a gramática e as representações oficiais sempre que adequadas. Esta pesquisa não decide migrar os documentos atuais nem autoriza uma segunda fonte canônica.

## Outros antecedentes verificados

| Projeto ou infraestrutura | Capacidade documentada | Implicação para o SpecMD |
| --- | --- | --- |
| [Gauge — escrita de especificações, commit `30362125`](https://github.com/getgauge/docs.gauge.org/blob/30362125c4176640ad04feaf7954d0bf42ccc31d/writing-specifications.rst) | Aceita especificações `.md` ou `.spec`, com cabeçalhos, cenários e passos implementados em código. | Markdown executável e narrativa com cenários já são uma solução estabelecida. A sintaxe apresentada precisa de avaliação própria; não se presume equivalência com os blocos Gherkin propostos. |
| [Concordion — instrumentação de Markdown](https://concordion.org/instrumenting/java/markdown/) | Acrescenta comandos em links Markdown para ligar exemplos, fixtures e asserções. | Executar exemplos diretamente de um documento também antecede o SpecMD. Trocar a sintaxe não é, por si, benefício de produto. |
| [Tracey — README no commit `66008a85`](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/README.md) | Relaciona requisitos Markdown com implementação e testes, identifica lacunas e referências obsoletas, oferece CLI/MCP/LSP, integração com Claude/Codex e hooks de versionamento. | Rastreabilidade nos dois sentidos, apoio a agentes e detecção de drift também têm antecedente muito próximo. Avaliar integração antes de criar outro índice e esquema de anotações. |
| [GitHub — proteção de branches, commit `481d4e35`](https://github.com/github/docs/blob/481d4e35beb53953e277d0b11ba4a18f8c8ade4f/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md) | Reviews obrigatórios, invalidação de aprovações desatualizadas, aprovação do último push por outra pessoa e checks exigidos antes de integrar. | Identidade de revisor, revisão de mudança e enforcement de CI podem reutilizar o provedor. Não presumir necessidade de construir um serviço próprio de aceite. |
| [Spec Kit — SDD no commit `27d14e20`](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/docs/reference/agentic-sdd.md) | Checklists sob responsabilidade do reviewer, análise de consistência entre artefatos e implementação orientada às especificações. | “A especificação deve orientar o agente” e “o implementador não se autoaprova” já fazem parte de um fluxo documentado. |
| [OpenSpec — README no commit `56ef0ac1`](https://github.com/Fission-AI/OpenSpec/blob/56ef0ac1fd2270e88d276b40da9f23ec0f9c6e96/README.md) | Requisitos e cenários em Markdown, propostas produzidas pelo agente e revisão humana antes do código. | Proposta, revisão e implementação de specs são terreno compartilhado; a vantagem precisa aparecer na operação do fluxo. |

A [documentação do Tracey consultada](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/README.md#version-tracking) também descreve versões de requisitos e referências de implementação que ficam obsoletas quando o requisito muda. Isso é especialmente próximo do problema de evolução contratual. Uma anotação de verificação, porém, não equivale por si a um recibo de execução atual; as políticas efetivamente disponíveis e sua composição precisam ser verificadas na comparação técnica.

O Tracey é implementado em Rust, mas não é restrito à análise de projetos Rust. No mesmo commit fixado, seu [registro central de linguagens](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/crates/tracey-core/src/languages.rs#L108-L110) inclui explicitamente Go (`.go`), Java (`.java`) e Python (`.py`), com gramáticas e extratores próprios. A lista do README omite Python, portanto não é uma descrição completa desse suporte no fonte. Isso confirma análise e rastreabilidade nessas linguagens no snapshot consultado, sem demonstrar execução BDD/Gherkin ou paridade de recursos entre elas.

O [fluxo de verificação do OpenSpec no snapshot consultado](https://github.com/Fission-AI/OpenSpec/blob/56ef0ac1fd2270e88d276b40da9f23ec0f9c6e96/docs/workflows.md#L331-L374) avalia completude, correção e coerência, incluindo requisitos implementados e cenários cobertos. O próprio fluxo documenta que a verificação não bloqueia o arquivamento. Essa é uma diferença concreta daquele fluxo, sem demonstrar ausência de gates configuráveis ou externos no ecossistema inteiro.

## A comparação precisa incluir extensões e composições

O [Spec Kit documenta eventos de runtime por integração](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/docs/reference/extensions.md#L297-L322), com subconjuntos diferentes por host. Portanto, núcleo comum mais adaptadores de ciclo de vida também tem antecedente direto.

Seu [catálogo comunitário no mesmo commit](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/extensions/catalog.community.json) serve para descoberta, não como auditoria das capacidades. As entradas consultadas não estavam marcadas como verificadas. As seguintes descrições foram conferidas nas fontes dos próprios mantenedores:

- [spec-gates `v0.4.1`](https://github.com/schwichtgit/spec-gates/blob/v0.4.1/README.md) descreve uma política e um verificador compartilhados nas fronteiras agente, Git e CI, attestations com SHA-256 e critérios executáveis em blocos `accept` de Markdown. É uma referência secundária de engenharia neste levantamento, com sobreposição documentada; maturidade, manutenção, adoção e confiabilidade operacional não foram avaliadas. A autoridade efetiva do aceite humano e os caminhos de bypass também exigem avaliação específica.
- [spec-kit-bdd `v1.0.3`](https://github.com/RSginer/spec-kit-bdd/blob/v1.0.3/README.md) descreve relações entre specs e cenários, mas gera arquivos `features/*.feature` e documenta hooks opcionais. A forma documentada não atende diretamente à restrição de execução sem `.feature` do SpecMD; ainda pode fornecer aprendizados ou pontos de adaptação.
- [plan-review-gate `v1.0.0`](https://github.com/luno/spec-kit-plan-review-gate/blob/v1.0.0/README.md) exige spec/plano integrados por revisão antes das tarefas e documenta uma opção `--skip-review`. É preciso comparar a política desejada e as permissões reais, em vez de equiparar qualquer gate a aceite obrigatório sem bypass pelo agente.

Esses antecedentes tornam inadequado posicionar o SpecMD apenas como “Markdown executável com hooks, hashes e CI”. Também não justificam concluir que uma composição existente já atende a todas as necessidades: isso precisa ser demonstrado, com escopo e configuração equivalentes.

Estrelas de repositório não comprovam qualidade, maturidade ou adequação. Esta comparação não usa uma contagem de estrelas como evidência dessas propriedades.

## Aceite por versão: reaproveitar antes de reconstruir

As [proteções documentadas do GitHub](https://github.com/github/docs/blob/481d4e35beb53953e277d0b11ba4a18f8c8ade4f/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md) já podem exigir aprovação e invalidá-la quando muda o diff. O provedor também permite restringir a origem esperada de um check e configurar o tratamento de bypass administrativo. Essas capacidades dependem de configuração e separação de permissões; não estão instaladas neste projeto por serem mencionadas aqui.

Um manifesto e seu hash podem identificar o subconjunto documental aceito independentemente de novas tentativas no código. Essa granularidade deve ser comparada ao aceite por PR: dispensas por documento, renomes, revisões do código sem mudança de intenção e retomadas locais podem pedir uma camada adicional de associação. O benefício de mantê-la só existe se reduzir reaprovações e ambiguidade sem enfraquecer o controle existente.

Na documentação de proteção citada, checks exigidos podem ser considerados atendidos em estados como `skipped` ou `neutral`. Logo, um status agregado favorável não comprova que todos os cenários obrigatórios foram executados. A política do SpecMD precisa verificar a evidência pertinente, seja implementada como check próprio, seja reutilizando um verificador existente.

O hash é infraestrutura de identidade. A confiança vem da procedência da decisão e da execução, das permissões e da proteção do verificador. Trocar a função de hash ou criar recibos JSON não é um diferencial por si só.

## Hipótese de vantagem a demonstrar

Uma formulação testável para o SpecMD seria: **reduzir o trabalho e os erros necessários para manter, durante a atividade do agente, a correspondência entre intenção humana aceita, documentação do escopo, mudanças de comportamento e evidências atuais de cenários.**

As dimensões candidatas precisam ser avaliadas como um fluxo completo:

1. **Revisão no momento certo:** o agente entrega uma proposta identificada e entra em `waiting_human_review`, sem loop de bloqueio ou falsa conclusão.
2. **Classificação e dispensas versionadas:** documentos informativos e mistos recebem decisões explícitas; uma alteração reabre a revisão apropriada, mantendo o inventário atualizado.
3. **Proveniência nos dois sentidos:** mudanças de comportamento sem origem reconhecida são expostas, além de requisitos sem implementação. Tracey e outros mecanismos de rastreabilidade devem compor o comparativo.
4. **Evidência por cenário e snapshot:** um resultado é associado ao contrato, código e verificador efetivamente utilizados; cenário ignorado ou resultado antigo não satisfaz a política.
5. **Integração com runtimes existentes:** preservar origem no Markdown e adaptar Java, Python e Go sem impor um arquivo `.feature` intermediário. Compatibilidade por linguagem permanece uma questão de engenharia a validar.

Nenhum item dessa lista deve ser anunciado como exclusivo. O candidato a valor é a redução mensurável de atrito e divergências ao combiná-los, com limites de confiança claros.

## Reaproveitar, adaptar e pesquisar

As recomendações abaixo são propostas para a próxima decisão de arquitetura, não mudanças de escopo já aceitas.

| Tratamento | Componentes ou decisões | Evidência necessária antes de construir |
| --- | --- | --- |
| Reaproveitar | Gramática Gherkin, parsers e representações de execução oficiais. | Demonstrar o formato de entrada e os mapas de origem no runtime escolhido. |
| Reaproveitar | Reviews autenticados, proteções de integração e checks do provedor Git. | Demonstrar que a credencial do agente não aprova nem contorna a política. |
| Reaproveitar | Implementações de hash, diff, Git e formatos de resultado existentes. | Identificar de forma reproduzível o snapshot e a cadeia de procedência necessária. |
| Adaptar, se houver lacuna | Extração de blocos Markdown ou entrada MDG, IDs e vinculação aos resultados. | Comparar esforço de integração e fidelidade ao documento original, sem duplicar o contrato. |
| Adaptar, se houver lacuna | Rastreabilidade, índice e integração com agentes de ferramentas como Tracey, Spec Kit e OpenSpec. | Mostrar quais controles já atendem à política e qual extensão mínima falta. |
| Pesquisar | Dispensa humana por versão, conteúdo misto e aceite por escopo independente das tentativas no código. | Demonstrar utilidade e ausência de autoisenção nas configurações comparadas. |
| Pesquisar | Estado de espera humana, validade de evidência e enforcement uniforme entre hosts. | Reproduzir casos adversos, diferenças de capacidade e recuperação de falhas. |

Um novo runner, uma nova linguagem de cenários, um serviço próprio de identidade e um novo banco de rastreabilidade não devem ser consequências automáticas da ideia. Cada subsistema precisaria justificar por que uma integração menor não resolve o trabalho.

## Comparação experimental e critérios de redução

O [plano de validação](validation-plan.md) deve incluir um baseline com ferramentas existentes bem configuradas. Comparar somente contra um agente sem documentação ou sem CI superestimaria o ganho.

Proposta de experimento:

- Estabelecer uma configuração simples com executor de especificações, reviews protegidos e CI.
- Estabelecer uma composição de SDD, rastreabilidade e gates existentes que cubra o máximo da política necessária com o menor custo razoável. Não instalar todos os projetos da pesquisa apenas para tornar o baseline artificialmente complexo.
- Comparar essa composição com a menor extensão SpecMD capaz de preencher as lacunas restantes, nas mesmas tarefas e com o mesmo agente.

Os casos devem incluir regra inventada pelo agente, mudança de contrato após aceite, documento novo, documento informativo que adquire obrigação, evidência de outro snapshot, cenário ignorado e tentativa de alterar a política de exclusão. A avaliação humana precisa julgar o comportamento desejado independentemente do relatório emitido pelas ferramentas.

Medir divergências que chegam à conclusão, pendências corretamente detectadas, bloqueios indevidos, tempo de revisão, número de interações humanas, retrabalho e custo de instalação/manutenção. Definir critérios de ganho e limites de custo antes de executar o experimento; este documento não afirma resultados nem fixa metas já aceitas.

Reduzir o escopo ou abandonar um subsistema será a decisão adequada quando:

- A composição existente entregar os mesmos controles com esforço igual ou menor: o SpecMD pode ser apenas um plugin, preset ou pacote de configuração.
- MDG ou outro ponto de extensão atender ao formato escolhido: evitar manter um parser ou dialeto concorrente sem necessidade.
- O problema restante for apenas navegação e rastreabilidade: integrar uma ferramenta especializada antes de reproduzi-la.
- O aceite do provedor for suficiente para o trabalho real: evitar criar uma autoridade de aprovação independente.
- O ganho desaparecer ao comparar com o baseline forte, ou o custo de revisão/classificação superar o retrabalho evitado: reduzir a hipótese ou interromper o produto autônomo.
- A separação de permissões ou a execução sem `.feature` não for viável no ambiente escolhido: declarar a limitação e reavaliar a abordagem, sem enfraquecer silenciosamente os requisitos.

O próximo resultado útil é uma demonstração comparativa das lacunas, não uma alegação ampla de originalidade. As decisões gerais continuam em [decisions.md](decisions.md), e os requisitos vigentes em [requirements.md](requirements.md).
