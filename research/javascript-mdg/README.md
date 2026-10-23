# Baseline: Markdown with Gherkin no Cucumber.js

> Estado: **baseline executado com Cucumber.js 13.3.0**. MDG foi descoberto e executado pelo CLI real; o caso negativo falhou por uma asserção executada. Isso não constitui implementação do produto nem suporte produtivo de seus plugins.

Este experimento distingue a existência do formato **Markdown with Gherkin (MDG)** da capacidade real de descoberta e execução no CLI do Cucumber.js. Ele usa um Markdown canônico `addition.feature.md`, sem arquivo `.feature` separado e sem conversão para esse formato.

## Ambiente observado

- Node: `v24.19.0`.
- npm: `11.9.0`.
- `@cucumber/cucumber`: `13.3.0`; `--version` retornou `13.3.0`.
- `@cucumber/gherkin` resolvido: `42.0.1`.
- `@cucumber/messages` resolvido: `34.2.1`.
- Engines declarados pelo runner: Node `22 || 24 || >=26`.
- Execução: `2026-10-23T02:16:07.680Z` a `2026-10-23T02:16:14.986Z`, correspondente à noite de 22/10/2026 em America/Sao_Paulo.

O fixture usa os cabeçalhos ingleses `Feature` e `Scenario` e passos em lista para investigar o formato MDG indicado pela fonte. Não se presume suporte a dialeto português, nem equivalência com um bloco cercado por três crases e marcado como `gherkin`.

## Fontes oficiais

- [Markdown with Gherkin, revisão fixada](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md).
- [Cucumber.js](https://github.com/cucumber/cucumber-js).
- [Pacote oficial Cucumber.js 13.3.0](https://www.npmjs.com/package/@cucumber/cucumber/v/13.3.0).
- [Pacote oficial Gherkin 42.0.1](https://www.npmjs.com/package/@cucumber/gherkin/v/42.0.1).

A indicação documental de suporte do parser JavaScript a partir da versão 19 não demonstra, sozinha, que o CLI de qualquer versão do Cucumber.js execute esse formato. Neste ensaio essa distinção foi verificada por execução do CLI real na versão fixada, sem adaptador Markdown próprio.

## Resultados observados

| Caso | Saída | Cenários | Passos | Conclusão limitada ao ensaio |
| --- | --- | --- | --- | --- |
| MDG `.feature.md`, caminho explícito | `0` | 1 | 3 passaram | Execução nativa confirmada. |
| MDG `.feature.md`, expectativa incorreta | `1` | 1 | 2 passaram, 1 falhou | `AssertionError`: 2 + 3 produziu 5, e o cenário exigia 6. |
| Descoberta padrão em `features/`, sem caminho explícito | `0` | 1 | 3 passaram | Descoberta nativa de `.feature.md` confirmada; caminho dos steps foi passado explicitamente. |
| Mesmo MDG em `.md` comum, caminho explícito | `0` | 1 | 3 passaram | Extensão `.feature.md` não foi obrigatória quando o caminho foi informado. |
| Gherkin em bloco cercado, `.md` comum explícito | `0` | 0 | 0 | O CLI não executou o bloco deste fixture; saída zero não significa cobertura. |

O teste não investigou descoberta padrão de qualquer `.md`, dialetos além do inglês, integração em outras linguagens nem funcionalidades de governança. Inspeção local do pacote instalado encontrou o glob padrão `features/**/*.{feature,feature.md}` em `lib/paths/paths.js`, coerente com a descoberta observada.

Evidências pequenas, sem dependências instaladas ou cópias de trabalho:

- [Resultados estruturados e comandos normalizados](results/13.3.0.json).
- [Saída dos cinco casos](results/13.3.0.log).
- [Versões resolvidas e digest do lockfile](results/dependency-versions.json).

Somente os caminhos absolutos do ambiente foram substituídos por marcadores. Status, contagens, códigos de saída e a mensagem da asserção foram preservados. O lockfile integral permanece no resultado local; o script o exporta em cada reprodução.

## O que o script verifica

Cada caso roda isoladamente, com uma implementação real de soma e asserção `node:assert/strict`:

1. MDG `.feature.md` com caminho explícito e resultado correto.
2. MDG `.feature.md` com caminho explícito e resultado incorreto: o resultado 6 é exigido para 2 + 3, cuja implementação retorna 5.
3. Descoberta padrão de `.feature.md` dentro de `features/`, sem caminho explícito.
4. Mesmo MDG como arquivo `.md` comum, com caminho explícito.
5. Gherkin tradicional cercado em bloco `gherkin`, em `.md` comum, com caminho explícito.

O script registra código de saída, saída do runner, relatório JSON e contagem de cenários/status. Código de saída zero com zero cenários **não conta como suporte**. Uma falha de parsing no caso negativo **não conta como teste comportamental que falhou**.

## Reprodução

Para pesquisar uma versão atual diferente, consultar e registrar o resultado; isso é separado da reprodução da versão fixada:

```sh
npm view @cucumber/cucumber version engines --json
```

Para reproduzir o baseline observado, informar a versão **exata**; o script não escolhe `latest` silenciosamente:

```sh
node research/javascript-mdg/run.mjs --version 13.3.0 --install
```

`--install` autoriza a tentativa de instalação no script; não substitui a permissão de rede do ambiente. Dependências ficam em diretório temporário separado do repositório. Cada processo tem timeout finito. O manifesto e lockfile da instalação são preservados junto aos resultados para reprodução.

Para repetir com a instalação já presente, omitir `--install`. Para escolher destinos fora do repositório:

```sh
node research/javascript-mdg/run.mjs --version 13.3.0 --cache-dir /tmp/specmd-mdg-cache --output-dir /tmp/specmd-mdg-results/13.3.0
```

Não é necessário criar arquivos `.feature`, nem manter dois documentos com o mesmo cenário. Os arquivos `.feature.md` deste ensaio continuam sendo Markdown.

## Verificações locais realizadas

Na preparação offline foram verificadas a sintaxe JavaScript, a ajuda do script e a função de soma, como registrado em [preparation.json](preparation.json). Posteriormente o agente principal instalou a versão fixada e executou os cinco casos. As evidências posteriores em `results/` registram o teste real de Cucumber e substituem a pendência inicial de execução.

## Relação com a proposta do produto

A execução nativa de MDG é um antecedente direto da ideia de documentação Markdown executável e reduz o trabalho necessário nessa camada. Portanto, executar cenários de Markdown não deve ser apresentado como uma novidade por si só.

Este resultado não demonstra mecanismos de aceite humano versionado, dispensa documental aprovada, rastreabilidade de mudanças, proteção contra autoaceite ou integração com hooks. Esses mecanismos precisam ser comparados e validados separadamente; este ensaio não estabelece novidade do conjunto de produto.

Há uma decisão concreta de formato: reutilizar MDG aproveita suporte já existente nessa versão do Cucumber.js. O formato anterior de blocos cercados `gherkin` exige outra integração, pois o fixture desse formato produziu zero cenários na execução direta testada. Não se deve tratar as duas sintaxes como equivalentes nem alterar o contrato do produto sem registrar essa decisão.
