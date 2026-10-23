# Pesquisa de viabilidade dos runners

Esta investigação responde à exigência de executar cenários canônicos em Markdown em projetos Java, Python e Go, sem exigir arquivos `.feature`. Os protótipos são experimentos reproduzíveis, não o produto implementado, nem evidências de aceite humano dos contratos deste repositório.

## Perguntas a testar

1. A CLI do runner aceita conteúdo Gherkin como argumento ou entrada padrão, ou interpreta os argumentos como caminhos?
2. Existe API que aceite texto, modelos ou conteúdo em memória sem precisar materializar `.feature`?
3. Essa API é pública/documentada, ou depende de componentes internos sujeitos a mudança?
4. Passos reais executam código da linguagem e produzem resultados distintos para sucesso, falha e passo indefinido?
5. Como cenários filtrados, ignorados ou inexistentes afetam o exit code? É necessário um gate adicional?
6. É possível preservar a origem em `.md`, os IDs e a posição do bloco?
7. Qual formato e mecanismo devem ser reaproveitados em vez de reinventados?

## Experimentos por ecossistema

| Diretório | Hipótese investigada | Resultado obtido |
| --- | --- | --- |
| [java](java/) | Cucumber-JVM com fornecedor de cenários em memória. | Executado com 8.0.4; positivos e negativos corresponderam às expectativas. |
| [python](python/) | Behave com parsing de texto e modelo executável em memória. | Executado com 1.3.3 e markdown-it-py; Behave não é Cucumber oficial. |
| [go](go/) | Godog com conteúdo de features fornecido por API. | Executado com 0.16.0, incluindo filtros, stdin do adaptador e filesystem virtual. |
| [javascript-mdg](javascript-mdg/) | Baseline do Markdown with Gherkin oficial em Cucumber.js. | MDG nativo confirmado em 13.3.0; blocos fenced não executaram cenários. |

O [estudo consolidado](../docs/runner-feasibility.md) distingue resultados, APIs, riscos de manutenção e limites do que foi demonstrado. Os protótipos não constituem suporte produtivo nem implementam aceite humano.

## Critério de evidência

O caso positivo deve executar implementações reais dos passos e código da linguagem. Parsing isolado ou simulação de runner não é suficiente. Os casos negativos precisam registrar o resultado real da engine e a decisão do gate; o harness pode terminar com sucesso por ter observado corretamente uma falha esperada.

Para receber OK, não basta `exit code 0`: o conjunto de cenários exigidos precisa estar efetivamente executado com resultado aprovado. Ausência de cenários ou filtragem não pode virar sucesso silencioso.

As versões, comandos, entradas e limitações precisam permanecer reproduzíveis. Dependências, SDKs e caches baixados não são parte da fonte canônica nem devem ser publicados junto aos resultados.

## Antecedente oficial já identificado

[Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) define um dialeto Markdown com cabeçalhos, listas e arquivos `.feature.md`. A documentação consultada indica suporte na implementação JavaScript do parser. Isso não estabelece suporte nativo equivalente em todo runner ou linguagem.

Sua sintaxe difere de blocos Gherkin em cercas de código. Um `.feature.md` é um Markdown e pode continuar sendo a fonte canônica; não é uma cópia `.feature` paralela. A comparação precisa avaliar compatibilidade e reaproveitamento, sem inventar uma distinção de produto baseada apenas no nome do arquivo.

O parser produz estruturas de cenários; a engine ainda precisa ligá-las às implementações dos passos e executá-las. A passagem de mensagens ou ASTs entre ecossistemas não é presumida como uma interface universal.

## Relação com o projeto

- [Requisitos](../docs/requirements.md)
- [Formato proposto](../docs/format.md)
- [Arquitetura](../docs/architecture.md)
- [Plano de validação](../docs/validation-plan.md)
- [Posicionamento e antecedentes](../docs/positioning.md)

Os resultados desta investigação devem atualizar o roadmap e as hipóteses de produto. Nenhuma documentação de antecedente, sozinha, demonstra a qualidade de sua implementação ou a vantagem do SpecMD.
