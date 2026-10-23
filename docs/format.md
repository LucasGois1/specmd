---
specmd:
  schema: 1
  id: SMD-DOC-FORMAT
  kind: mixed
---

# Formato documental e suporte atual

> **Histórico, anterior à [D-021](decisions.md).** Este documento descreve o desenho com aceite assinado, autoridade, trust e bloqueio de implementação, removido em 23/10/2026. Para o produto atual, veja [produto](product.md) e [estado da implementação](implementation-status.md).

O SpecMD implementa um formato experimental de contratos Markdown e um lifecycle de revisão, assinatura e execução. O scanner continua sendo um preflight estrutural: isoladamente não executa cenários, não valida uma pessoa e não libera conclusão. O fluxo integrado combina esse inventário com aceites e evidências separados. Consulte o [estado de implementação](implementation-status.md) para distinguir capacidades implementadas, validações realizadas e limites de implantação.

Os requisitos do produto estão em [requirements.md](requirements.md). A classificação deste próprio documento também é uma proposta, não uma dispensa ou um aceite concedido pelo agente.

## Markdown como fonte canônica

O contrato é um arquivo Markdown comum, com narrativa, metadados e cenários Gherkin no mesmo documento. Não há uma sintaxe de arquivo proprietária nem uma segunda especificação editável.

A execução deve consumir os blocos diretamente do Markdown. O fluxo previsto é:

```text
Markdown → AST de Markdown → blocos Gherkin → representação executável em memória
         → adaptador do runner → resultados associados ao documento original
```

Arquivos `.feature` não são exigidos do usuário, não são mantidos como fonte paralela e não devem ser uma etapa obrigatória, mesmo temporária, para executar o contrato. O adaptador precisa integrar o conteúdo extraído ao mecanismo de execução. Os [protótipos de runners](runner-feasibility.md) demonstraram caminhos de integração em memória; não se presume que o Cucumber aceite qualquer Markdown nativamente.

## Dois esquemas diferentes

O `schema` da configuração do projeto e o `specmd.schema` do frontmatter têm responsabilidades diferentes:

| Local | Versões atuais | Responsabilidade |
| --- | --- | --- |
| `specmd.toml`, na raiz | `schema = 1` ou `schema = 2` | Ativação do projeto e capacidades do lifecycle. |
| Frontmatter de cada Markdown | `specmd.schema: 1` | Identidade e classificação declarada do documento. |

O schema 1 de configuração preserva o preflight inicial, com cenários simples e sem autorização de conclusão. Ele aceita somente `schema = 1`. O schema 2 acrescenta identidade do projeto, configuração de runners, rastreabilidade e política de evidências; também habilita `Rule` e expansão de `Scenario Outline` no scanner. Um contrato usado por um projeto schema 2 continua com **frontmatter schema 1**.

Exemplo mínimo de configuração schema 2:

```toml
schema = 2
project_id = "meu-projeto"
repository_id = "github.com/equipe/meu-projeto"

[traceability]
map = ".specmd/traceability.json"
policy = "strict"
```

`project_id` é obrigatório nesse esquema. `repository_id` é opcional e identifica logicamente o repositório entre checkouts; os recibos usam essa identidade com prefixo interno `repo:`. Sua declaração não comprova propriedade nem consulta uma conta GitHub. Sem ela, o fallback de identidade usa o caminho local do projeto, adequado à demonstração, mas sem a mesma portabilidade para CI.

Os demais campos aceitos no schema 2 são `runners` e `evidence`; opções desconhecidas são rejeitadas. Os formatos e comandos do lifecycle estão no [quickstart](quickstart.md). A ausência de `specmd.toml` mantém o scanner inativo; uma configuração presente e inválida produz erro.

## Metadados do Markdown

O formato de blocos abaixo é uma hipótese de integração, não uma reivindicação de novidade em Markdown executável. O projeto oficial [Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) já define cenários usando cabeçalhos e listas em arquivos `.feature.md`. Essa extensão continua sendo Markdown e não exige uma fonte `.feature` paralela. A [pesquisa](../research/README.md) deve decidir como reaproveitar esse trabalho e qual compatibilidade adotar, antes de estabilizar uma convenção própria.

O frontmatter usa YAML convencional:

```yaml
specmd:
  schema: 1
  id: SMD-EX-DOC-001
  kind: behavioral
```

| Campo | Significado implementado no formato experimental |
| --- | --- |
| `schema` | Versão do esquema de metadados. Permite evoluir o formato com migração explícita. |
| `id` | Identificador estável do documento, independente do título. Deve ser único no escopo do projeto. |
| `kind` | Classificação proposta: `behavioral`, `reference` ou `mixed`. |
| `exemption_reason` | Justificativa exigida quando `kind` for `reference`. Sua presença não concede a dispensa. |

Um documento descoberto sem classificação é tratado pelo sistema como pendente. Esse estado pode ser representado no inventário sem escrever automaticamente metadados no arquivo do usuário.

Não há campo de frontmatter que conceda aprovação. Um agente pode editar esses metadados, propor classificações e justificar dispensas; a autoridade continua sendo o registro de aceite protegido (removido por [D-021](decisions.md)), vinculado ao conteúdo e ao escopo revisados. Um campo como `approved: true` não substitui esse registro.

### Comportamental: `behavioral`

Contém obrigações sobre entradas, saídas, permissões, efeitos externos ou outros comportamentos do produto. Exige requisitos identificados e cenários associados. O exemplo completo está em [cancellation.contract.md](../examples/cancellation.contract.md).

### Informativo: `reference`

Não estabelece obrigações comportamentais do produto no conteúdo revisado. Exige justificativa e aceite da classificação. Pode conter instruções de uso de ferramentas da equipe, contexto ou referências, desde que essa descrição corresponda ao conteúdo efetivo.

O exemplo [editor-setup.reference.md](../examples/editor-setup.reference.md) não contém Gherkin deliberadamente. Continua pendente até haver aceite externo da versão apresentada. Uma alteração posterior no texto ou na justificativa exige nova revisão conforme a política definida.

O scanner bloqueia `reference` quando encontra cabeçalhos explícitos de requisito ou cercas Gherkin: é um conflito de classificação, não uma dispensa automática. Para ensinar Gherkin sem declarar um bloco executável, use uma cerca literal `markdown` ou `text`. A classificação e a justificativa integram o conteúdo versionado apresentado no fluxo de assinatura; o YAML não concede o aceite.

### Misto: `mixed`

Contém conteúdo informativo e seções que estabelecem obrigações. Para autoria, mantenha os cenários junto dos requisitos que descrevem; a parte informativa não precisa receber cenários artificiais. O scanner extrai os cabeçalhos e vincula tags explicitamente declaradas no inventário. Ele ainda não determina, a partir da posição ou do significado de um parágrafo, que toda obrigação daquela seção foi declarada.

Um `README` com instruções de instalação e regras de negócio é um caso possível. Declarar o documento inteiro como informativo não deve dispensar as regras de negócio de identificação, revisão e verificação. A suficiência da classificação e dos exemplos permanece uma decisão de revisão.

## Requisitos e cenários identificáveis

A convenção inicial é:

- Documento: `SMD-EX-DOC-001` nos exemplos.
- Requisito: cabeçalho como `## SMD-EX-REQ-001 — Título da obrigação`.
- Vínculo no Gherkin: tag `@SMD-EX-REQ-001` no cenário ou na funcionalidade que o contém.
- Cenário: tag própria e estável, como `@SMD-EX-SCN-001`.

O prefixo `SMD-EX` identifica exemplos fictícios e evita confusão com os requisitos `SMD-REQ` do próprio SpecMD. O formato exato dos identificadores é uma convenção proposta; a regra relevante é a unicidade e a estabilidade dos vínculos.

Tags de requisito são herdadas da funcionalidade e, no schema 2, da regra e dos exemplos aplicáveis. Um cenário pode estar associado a mais de um requisito. A identidade `SMD-…-SCN-…` deve ser uma tag própria do cenário ou do Outline; uma tag de identidade somente na funcionalidade não substitui essa declaração.

### Rule e Scenario Outline no schema 2

O scanner schema 2 percorre cenários dentro de `Rule`/`Regra` e expande as linhas de `Scenario Outline`/`Esquema do Cenário`. Cada instância recebe uma identidade derivada:

```text
<ID da tag do Outline>:row:<índice dos Exemplos>:<índice da linha de dados>

SMD-EX-SCN-001:row:1:1
SMD-EX-SCN-001:row:1:2
SMD-EX-SCN-001:row:2:1
```

Os índices começam em 1; o cabeçalho da tabela não conta como linha de dados. O registro mantém `template_id`, `example_index`, `row_index`, `definition_line` e `line`. `definition_line` aponta para a declaração do Outline; `line` aponta para a linha concreta da tabela no Markdown. O documento mantém apenas a tag-base, sem precisar escrever as identidades derivadas manualmente.

Outline sem exemplos concretos não satisfaz o requisito. Identidades-base duplicadas e instâncias duplicadas são bloqueadas. No schema 1, Rule e Outline continuam sendo recusados explicitamente para preservar o contrato do preflight inicial. O suporte estrutural do scanner não implica suporte de todos os executores; um bridge pode recusar uma capacidade sem tratá-la como teste aprovado.

A presença de um bloco Gherkin qualquer não cobre automaticamente todas as obrigações da prosa. O verificador pode exigir vínculos para os requisitos explicitamente declarados; encontrar obrigações ainda não declaradas depende de análise assistida e revisão humana.

## Extração e parsing

O scanner usa MarkdownIt para localizar cercas de código pela árvore de Markdown. Em documentos comportamentais ou mistos, uma cerca cujo primeiro identificador é `gherkin` declara um bloco de cenários. Gherkin é parseado a partir de texto em memória; nenhum `.feature` intermediário é necessário.

Cada bloco deve ser uma unidade Gherkin completa e parseável, com sua funcionalidade e seus cenários. Para português, a primeira linha do conteúdo é `# language: pt`. Não se deve depender da concatenação implícita de fragmentos incompletos distribuídos pelo arquivo.

Exemplos literais usados para ensinar o formato podem ficar dentro de cercas `markdown` ou `text`. Essas cercas não são cenários executáveis. A classificação como referência também não pode ser usada para esconder obrigações em exemplos: uma dúvida sobre seu significado deve aparecer na revisão.

São falhas já detectadas de forma determinística pelo scanner:

- Metadados inválidos ou classificação desconhecida.
- Documento comportamental sem blocos Gherkin aplicáveis.
- Gherkin com erro de sintaxe.
- IDs duplicados de documentos ou cenários no mesmo escopo.
- Tags que referenciam requisitos inexistentes no contrato aplicável.
- Requisitos declarados sem cenários associados.
- Cenários sem identidade estável ou sem vínculo com requisito.
- Chaves YAML duplicadas, documentos sem classificação e dispensas sem justificativa.
- Documento `reference` com requisitos explícitos ou cercas Gherkin.
- Blocos sem cenários concretos e cenários sem passos.

Essas verificações não determinam se uma asserção é suficiente, se um cenário é representativo ou se uma obrigação foi autorizada. A diferença entre parsing, aceite e evidência está detalhada na [arquitetura](architecture.md).

## Origem dos resultados

O scanner preserva caminhos relativos, hashes, bloco e linhas de origem. A extração fornece strings preenchidas com linhas vazias antes do conteúdo para que o parser mantenha as posições originais do `.md`. O lifecycle associa a essa origem os resultados efetivamente executados. São informações distintas:

- Caminho do documento e identidade do snapshot.
- Hash do conteúdo usado na execução.
- Identificador e posição do bloco no Markdown.
- ID do requisito e ID do cenário.
- Linha da declaração ou da linha de exemplos, com o deslocamento da cerca de código.
- Resultado do parsing, da ligação dos passos e da execução.

O scanner atual registra linhas, não promete mapas completos de colunas ou intervalos de texto. Contagem de passos e parsing válido não são estados `passed`. As linhas ajudam na navegação; IDs e hashes identificam o objeto verificado. Se o documento mudar, os números de linha podem mudar, e o resultado antigo continua pertencendo ao snapshot anterior.

O relatório deve apontar para o Markdown original, não exigir que a pessoa encontre um arquivo intermediário. Erros de passos indefinidos ou falhas de asserção precisam preservar essa origem.

## Hash e aceite

Narrativa, frontmatter e cenários participam da identidade do conteúdo. O scanner implementado calcula SHA-256 dos bytes exatos lidos do checkout, sem normalização semântica. O manifesto contém caminhos, hashes dos documentos e hash dos bytes de `specmd.toml`. Conversões de finais de linha podem, portanto, mudar sua identidade; a revisão e o CI precisam conferir o snapshot efetivamente utilizado.

O workflow amplia o manifesto com a identidade do mapa de rastreabilidade, por padrão `.specmd/traceability.json`. Esse mapa associa arquivos de código/testes a requisitos e cenários existentes; mudar o mapa altera a versão contratual apresentada para aceite e a validade das evidências. Ele não é uma segunda fonte dos cenários: o conteúdo canônico continua no Markdown.

Adicionar um cenário, remover uma obrigação, mudar a classificação ou editar uma justificativa cria um conteúdo que precisa ser confrontado com o aceite vigente. O agente não pode resolver a pendência escrevendo sua própria aprovação no arquivo.

O fluxo de assinatura vincula a decisão à versão apresentada. Isso não autentica, sozinho, uma pessoa nem prova leitura; o isolamento das chaves e a autoridade de implantação continuam requisitos operacionais. O [estado atual](implementation-status.md) distingue o caminho demonstrativo do verificador protegido.

Os exemplos documentais continuam ilustrativos. Publicá-los não equivale a aprová-los, e a presença de Gherkin não indica que existam implementações dos passos daquele exemplo ou que ele tenha sido executado.

## Evolução e decisões pendentes

Antes de estabilizar o formato, devem ser validados:

1. Compatibilidade e limites dos runners em cada plataforma, além dos caminhos experimentais já executados sem `.feature`.
2. A granularidade de documentos mistos e o vínculo entre cabeçalhos e blocos.
3. O esquema final de IDs, metadados, erros e mapas de origem.
4. O tratamento de referências entre documentos e da herança de tags.
5. O comportamento quando um requisito precisa de verificadores além dos cenários funcionais.

O [índice](indexing.md) e seu cache são derivados, sem autoridade de aprovação; o cache atual sempre reanalisa a fonte e ainda não entrega reutilização confiável de parsing. As [integrações](integrations.md) apresentam as pendências ao agente e ao usuário. O [plano de validação](validation-plan.md) define os experimentos para testar a utilidade e os limites do mecanismo.
