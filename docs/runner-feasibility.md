# Viabilidade de executar contratos Markdown

**Estado:** pesquisa e protótipos locais executados em 22/10/2026, no contexto America/Sao_Paulo. As evidências preservam timestamps UTC. Não existe ainda núcleo produtivo, plugin de agente, autoridade de aceite ou gate protegido implementado.

## Resultado principal

Foi possível executar passos e código reais em **Java, Python e Go**, a partir de cenários extraídos de Markdown, sem exigir ou materializar arquivos `.feature`. Cada ecossistema precisou de uma integração própria. Não foi encontrado nem presumido um argumento universal de CLI para receber todo o texto Gherkin.

Também foi executado um baseline do **Markdown with Gherkin oficial em Cucumber.js**. Ele confirma que documentação Markdown executável já existe e precisa ser considerada na decisão de reaproveitamento e posicionamento.

## Versões e mecanismos comprovados

| Ecossistema | Versões do experimento | Entrada executada | Limite principal |
| --- | --- | --- | --- |
| Java | Cucumber-JVM 8.0.4, CommonMark 0.24.0, Java 21.0.12.1. | `FeatureParser.parseResource` com stream em memória e `Runtime.Builder.withFeatureSupplier`. | Usa classes públicas do core; visibilidade pública não promete uma extensão estável para esse uso. |
| Python | Behave 1.3.3, markdown-it-py 4.0.0, Python 3.12.14. | `parse_feature` com string e `ModelRunner.run_model`, com registry de passos reais. | Behave não é Cucumber oficial; a integração programática precisa ser mantida e testada por versão. |
| Go | Godog 0.16.0, Goldmark 1.7.13, Go 1.25.0. | API pública `Options.FeatureContents`, com nomes de origem Markdown e conteúdo em memória. | Descoberta por diretório e entrada por conteúdo têm comportamentos diferentes; não presumir equivalência com o CLI. |
| JavaScript, baseline MDG | Cucumber.js 13.3.0, Gherkin 42.0.1, Node 24.19.0. | CLI nativa executando a sintaxe MDG em `.feature.md` e em `.md` passado explicitamente. | MDG usa cabeçalhos e listas; blocos fenced `gherkin` não foram executados nativamente neste teste. |

Essas são versões verificadas, não uma matriz de suporte estável para qualquer projeto, versão ou integração de terceiros.

## Evidências por linguagem

### Java

O adaptador usou CommonMark para encontrar dois blocos em português, forneceu o Gherkin ao parser em memória e executou os passos Java sobre `Application.add`. Preservou URIs com bloco e posições das linhas no Markdown original.

- Dois cenários positivos passaram e chamaram a aplicação.
- Asserção incorreta falhou; passo indefinido foi reportado.
- Filtro vazio retornou código 0 com zero cenários.
- Dry-run retornou código 0 e eventos `PASSED` de cenários e passos, mas não executou a aplicação. O gate experimental recusou o modo.
- Texto como argumento, stdin e caminho `.md` na CLI padrão não executaram os cenários nos modos testados.

[Relatório Java](../research/java/README.md) e [resultados estruturados](../research/java/evidence/results.json).

### Python

O adaptador usou markdown-it-py para extrair os blocos de um arquivo real, prefixou linhas em memória para preservar a origem e forneceu os modelos ao Behave. As definições de passos chamaram uma função Python de soma com asserções reais.

- Dois blocos positivos passaram, com duas chamadas à aplicação e linhas de origem conferidas.
- Asserção incorreta produziu falha.
- Passo indefinido produziu estado de erro no cenário e estados `undefined`/`skipped` nos passos.
- Filtro que removeu os cenários deixou `engine_failed=false`, mas nenhum comportamento foi executado. O gate experimental recusou.
- Os testes de CLI são registrados separadamente; uma entrada fornecida ao nosso adaptador não comprova suporte nativo do Behave a essa entrada.

[Relatório Python](../research/python/README.md) e [resultados do Markdown](../research/python/evidence/results.json).

### Go

O adaptador usou Goldmark para extrair Gherkin e a API `FeatureContents` do Godog para executar passos sobre funções Go de soma e cancelamento. O relatório associa os resultados às tags e ao mapa de origem criado pelo extrator.

- Dois cenários positivos em blocos distintos passaram.
- Falha de asserção, passo indefinido e passo pendente foram recusados.
- Filtro vazio, execução parcial e funcionalidade sem cenários puderam produzir código 0; o gate experimental recusou a ausência das obrigações esperadas.
- Entrada Markdown por stdin funcionou na interface própria do adaptador; isso não estabelece suporte de stdin no CLI nativo.
- A execução por conteúdo funcionou com um filesystem que recusava leituras, registrando zero acessos ao filesystem do runner.
- Um filesystem virtual com caminhos explícitos Markdown funcionou; a descoberta por diretório ignorou esses nomes sem extensão `.feature`.

O mapa de origem registra a linha da tag extraída. Essa informação não deve ser confundida com uma propriedade de linha diretamente fornecida pelo tipo de cenário no callback do Godog.

[Relatório Go](../research/go/README.md) e [resumo estruturado](../research/go/evidence/summary.json).

### Baseline MDG em JavaScript

Com Cucumber.js 13.3.0 e passos reais:

| Entrada | Resultado observado |
| --- | --- |
| MDG em `.feature.md`, caminho explícito | Um cenário passou. |
| MDG em `.feature.md`, descoberta padrão | Um cenário passou. |
| MDG em `.md` comum, caminho explícito | Um cenário passou. |
| MDG com expectativa deliberadamente errada | Um cenário falhou por asserção. |
| Markdown comum com cerca `gherkin` | Código 0, zero cenários executados. |

A convenção documental `.feature.md` facilita descoberta; o teste mostra que esta versão também executa MDG em um `.md` explicitamente indicado. Isso não implica descoberta automática de todo Markdown nem suporte a qualquer sintaxe embutida.

[Relatório MDG](../research/javascript-mdg/README.md) e [resultados sanitizados](../research/javascript-mdg/results/13.3.0.json).

## O que significa analisar código e executar testes

Gherkin descreve exemplos. O parser interpreta a estrutura e o runner liga os passos às suas implementações. São essas implementações que chamam o código do produto e verificam seus efeitos.

Portanto, coletar um cenário não produz automaticamente uma verificação correta da aplicação. O agente ou desenvolvedor ainda precisa implementar os passos e suas asserções, e a revisão precisa avaliar seu alcance. Rastreabilidade estática, análise de mudanças e execução são mecanismos complementares.

O SpecMD não precisa criar uma nova engine BDD. Um desenho possível é um núcleo que identifica contrato e cenários aplicáveis, lança o adaptador da linguagem e normaliza as evidências devolvidas por runtimes existentes.

## Como decidir o OK

O gate de produção proposto deve verificar, no mínimo:

1. Existe aceite humano válido para conteúdo, classificação e escopo atuais.
2. O conjunto de cenários obrigatórios é conhecido antes de aplicar filtros de execução.
3. Os cenários exigidos foram efetivamente executados, sem omissões, duplicações ou resultados indevidos.
4. A execução não é apenas parsing, descoberta, simulação ou dry-run.
5. Os resultados pertencem ao contrato, código, testes, configuração e ferramentas pertinentes à revisão avaliada.
6. Passos indefinidos, pendentes, ignorados e falhas não foram convertidos silenciosamente em sucesso.

Uma tarefa exclusivamente informativa com dispensa válida pode não ter cenários obrigatórios. Os casos negativos de ausência nos protótipos têm obrigações comportamentais esperadas; não estabelecem uma regra de exigir Gherkin em documentos dispensados.

Os gates experimentais são predicados específicos dos fixtures, inclusive com contadores de chamadas à aplicação. Eles demonstram os casos negativos conhecidos, não uma prova geral de suficiência dos testes nem uma fronteira de confiança protegida.

## Decisão de arquitetura a investigar

Reaproveitar parsers e engines existentes; manter o Markdown original como identidade contratual; separar formato de autoria, adaptador de execução, evidência e autoridade de aceite.

Comparar a sintaxe oficial MDG com blocos Gherkin clássicos antes de estabilizar o formato. O suporte direto em JavaScript não é portabilidade automática para Java, Python ou Go. Os adaptadores de extração demonstrados não exigem inventar outra gramática Gherkin, mas têm custos de manutenção e compatibilidade.

A [pesquisa de posicionamento](positioning.md) também encontrou sobreposição com Tracey, Spec Kit/OpenSpec e spec-gates. A existência de adaptadores viáveis não comprova novidade nem benefício de produto: a próxima decisão deve comparar a menor integração necessária com ferramentas existentes bem configuradas.

## Limites e próximo nível de validação

Não foram implementados nem demonstrados neste estudo: autoridade humana separada, proteção contra bypass de integração, plugins Claude/Codex, aceites reais de documentos, inventário de produção ou ganho mensurado de qualidade.

Os protótipos também não cobrem toda a gramática e todo o ciclo de vida dos runners. Outlines, tabelas, doc strings, hooks de aplicação, paralelismo e integrações com projetos existentes precisam de validação adicional antes de anunciar suporte. A evidência atual demonstra viabilidade técnica dos caminhos ensaiados.
