---
specmd:
  schema: 1
  id: SMD-DOC-FORMAT
  kind: mixed
---

# Formato proposto dos documentos

Este documento descreve uma proposta de formato para o SpecMD. Não existe, neste estágio, parser, runner ou aprovação humana autenticada implementada. Os campos e convenções abaixo precisam ser validados no protótipo e revisados antes de serem estabilizados como uma API.

Os requisitos do produto estão em [requirements.md](requirements.md). A classificação deste próprio documento também é uma proposta, não uma dispensa ou um aceite concedido pelo agente.

## Markdown como fonte canônica

O contrato é um arquivo Markdown comum, com narrativa, metadados e cenários Gherkin no mesmo documento. Não há uma sintaxe de arquivo proprietária nem uma segunda especificação editável.

A execução deve consumir os blocos diretamente do Markdown. O fluxo previsto é:

```text
Markdown → AST de Markdown → blocos Gherkin → representação executável em memória
         → adaptador do runner → resultados associados ao documento original
```

Arquivos `.feature` não são exigidos do usuário, não são mantidos como fonte paralela e não devem ser uma etapa obrigatória, mesmo temporária, para executar o contrato. O adaptador precisa integrar o conteúdo extraído ao mecanismo de execução. A viabilidade dessa integração com um runner concreto é a primeira investigação técnica descrita no [roadmap](roadmap.md); não se presume que o Cucumber aceite Markdown nativamente.

## Metadados propostos

O formato de blocos abaixo é uma hipótese de integração, não uma reivindicação de novidade em Markdown executável. O projeto oficial [Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) já define cenários usando cabeçalhos e listas em arquivos `.feature.md`. Essa extensão continua sendo Markdown e não exige uma fonte `.feature` paralela. A [pesquisa](../research/README.md) deve decidir como reaproveitar esse trabalho e qual compatibilidade adotar, antes de estabilizar uma convenção própria.

O frontmatter usa YAML convencional:

```yaml
specmd:
  schema: 1
  id: SMD-EX-DOC-001
  kind: behavioral
```

| Campo | Significado proposto |
| --- | --- |
| `schema` | Versão do esquema de metadados. Permite evoluir o formato com migração explícita. |
| `id` | Identificador estável do documento, independente do título. Deve ser único no escopo do projeto. |
| `kind` | Classificação proposta: `behavioral`, `reference` ou `mixed`. |
| `exemption_reason` | Justificativa exigida quando `kind` for `reference`. Sua presença não concede a dispensa. |

Um documento descoberto sem classificação é tratado pelo sistema como pendente. Esse estado pode ser representado no inventário sem escrever automaticamente metadados no arquivo do usuário.

Não há campo de frontmatter que conceda aprovação. Um agente pode editar esses metadados, propor classificações e justificar dispensas; a autoridade continua sendo o [registro de aceite protegido](approval-and-trust.md), vinculado ao conteúdo e ao escopo revisados. Um campo como `approved: true` não substitui esse registro.

### Comportamental: `behavioral`

Contém obrigações sobre entradas, saídas, permissões, efeitos externos ou outros comportamentos do produto. Exige requisitos identificados e cenários associados. O exemplo completo está em [cancellation.contract.md](../examples/cancellation.contract.md).

### Informativo: `reference`

Não estabelece obrigações comportamentais do produto no conteúdo revisado. Exige justificativa e aceite da classificação. Pode conter instruções de uso de ferramentas da equipe, contexto ou referências, desde que essa descrição corresponda ao conteúdo efetivo.

O exemplo [editor-setup.reference.md](../examples/editor-setup.reference.md) não contém Gherkin deliberadamente. Continua pendente até haver aceite externo da versão apresentada. Uma alteração posterior no texto ou na justificativa exige nova revisão conforme a política definida.

### Misto: `mixed`

Contém conteúdo informativo e seções que estabelecem obrigações. Para a proposta inicial, as seções comportamentais usam cabeçalhos com IDs de requisitos, e seus blocos Gherkin ficam na própria seção. A parte informativa não precisa receber cenários artificiais.

Um `README` com instruções de instalação e regras de negócio é um caso possível. Declarar o documento inteiro como informativo não deve dispensar as regras de negócio de identificação, revisão e verificação. A granularidade por seção ainda precisa ser exercitada no protótipo.

## Requisitos e cenários identificáveis

A convenção inicial é:

- Documento: `SMD-EX-DOC-001` nos exemplos.
- Requisito: cabeçalho como `## SMD-EX-REQ-001 — Título da obrigação`.
- Vínculo no Gherkin: tag `@SMD-EX-REQ-001` no cenário ou na funcionalidade que o contém.
- Cenário: tag própria e estável, como `@SMD-EX-SCN-001`.

O prefixo `SMD-EX` identifica exemplos fictícios e evita confusão com os requisitos `SMD-REQ` do próprio SpecMD. O formato exato dos identificadores é uma convenção proposta; a regra relevante é a unicidade e a estabilidade dos vínculos.

Uma tag de requisito em uma funcionalidade aplica-se aos cenários daquela funcionalidade, conforme a herança de tags do Gherkin. Um cenário pode estar associado a mais de um requisito, desde que isso represente uma relação revisável e compreensível. Um requisito pode exigir vários cenários.

A presença de um bloco Gherkin qualquer não cobre automaticamente todas as obrigações da prosa. O verificador pode exigir vínculos para os requisitos explicitamente declarados; encontrar obrigações ainda não declaradas depende de análise assistida e revisão humana.

## Extração e parsing

A proposta inicial usa um parser de Markdown para localizar cercas de código, em vez de procurar apenas uma sequência de crases com expressão regular. Dentro de documentos comportamentais ou de seções comportamentais de documentos mistos, uma cerca com o identificador `gherkin` declara um bloco executável.

Cada bloco deve ser uma unidade Gherkin completa e parseável, com sua funcionalidade e seus cenários. Para português, a primeira linha do conteúdo é `# language: pt`. Não se deve depender da concatenação implícita de fragmentos incompletos distribuídos pelo arquivo.

Exemplos literais usados para ensinar o formato podem ficar dentro de cercas `markdown` ou `text`. Essas cercas não são cenários executáveis. A classificação como referência também não pode ser usada para esconder obrigações em exemplos: uma dúvida sobre seu significado deve aparecer na revisão.

São falhas detectáveis de forma determinística, após estabilização do esquema:

- Metadados inválidos ou classificação desconhecida.
- Documento comportamental sem blocos Gherkin aplicáveis.
- Gherkin com erro de sintaxe.
- IDs duplicados de documentos ou cenários no mesmo escopo.
- Tags que referenciam requisitos inexistentes no contrato aplicável.
- Requisitos declarados sem cenários associados.
- Cenários sem identidade estável ou sem vínculo com requisito.

Essas verificações não determinam se uma asserção é suficiente, se um cenário é representativo ou se uma obrigação foi autorizada. A diferença entre parsing, aceite e evidência está detalhada na [arquitetura](architecture.md).

## Origem dos resultados

O processamento deve preservar, para cada cenário:

- Caminho do documento e identidade do snapshot.
- Hash do conteúdo usado na execução.
- Identificador e posição do bloco no Markdown.
- ID do requisito e ID do cenário.
- Intervalo de origem necessário para apontar erros no documento, incluindo deslocamentos da cerca de código.
- Resultado do parsing, da ligação dos passos e da execução.

As linhas são uma ajuda de navegação; IDs e hashes identificam o objeto verificado. Se o documento mudar, os números de linha podem mudar, e o resultado antigo continua pertencendo ao snapshot anterior.

O relatório deve apontar para o Markdown original, não exigir que a pessoa encontre um arquivo intermediário. Erros de passos indefinidos ou falhas de asserção precisam preservar essa origem.

## Hash e aceite

Narrativa, frontmatter e cenários participam da identidade do conteúdo. A proposta inicial usa os bytes exatos da revisão Git de referência, sem normalização semântica que possa esconder mudanças. O manifesto inclui caminhos e hashes dos documentos no escopo, conforme [approval-and-trust.md](approval-and-trust.md).

Adicionar um cenário, remover uma obrigação, mudar a classificação ou editar uma justificativa cria um conteúdo que precisa ser confrontado com o aceite vigente. O agente não pode resolver a pendência escrevendo sua própria aprovação no arquivo.

Os exemplos deste repositório são propostas ilustrativas. Publicá-los não equivale a aprová-los, e a presença de Gherkin não indica que já existam implementações dos passos ou testes executados.

## Decisões para o protótipo

Antes de estabilizar o formato, devem ser validados:

1. O parser de Markdown e a API de integração do runner sem dependência de `.feature`.
2. A granularidade de documentos mistos e o vínculo entre cabeçalhos e blocos.
3. O esquema final de IDs, metadados, erros e mapas de origem.
4. O tratamento de referências entre documentos e da herança de tags.
5. O comportamento quando um requisito precisa de verificadores além dos cenários funcionais.

O [índice](indexing.md) acelera essas operações sem conceder aceites. As [integrações](integrations.md) apresentam as pendências ao agente e ao usuário. O [plano de validação](validation-plan.md) define os experimentos para testar a utilidade e os limites do mecanismo.
