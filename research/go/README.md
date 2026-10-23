# Experimento Go: Markdown canônico com Godog

Este diretório contém um protótipo isolado de integração, não a implementação do SpecMD. Ele extrai blocos Gherkin de Markdown com Goldmark e os entrega ao Godog por conteúdo em memória, sem exigir ou produzir arquivos `.feature`.

**Executado:** os 11 probes da matriz ampliada coincidiram com o esperado. Dois cenários reais passaram pelo caminho em memória; asserção incorreta, passo indefinido, pendência, filtros incompletos e ausência de cenários foram recusados pelo gate. O estado e a data UTC estão em [evidence/summary.json](evidence/summary.json), com hashes das fontes executadas. Esse resultado é uma prova técnica restrita à integração exercitada.

## Versões fixadas

- Godog: `v0.16.0`.
- Goldmark: `v1.7.13`.
- SDK usado no ambiente de pesquisa: Go `1.25.0`, Linux/amd64, instalado de forma portátil fora do repositório.
- SHA-256 do arquivo oficial `go1.25.0.linux-amd64.tar.gz`, conferido na preparação: `2852af0cb20a13139b3448992e69b868e50ed0f8a1e5940ee1de9e19a123b613`.

As dependências diretas estão em [go.mod](go.mod); os checksums resolvidos ficam em `go.sum` após a preparação. SDK, caches e binário de build não devem ser publicados.

## Reprodução

Use um SDK Go real; neste ambiente `/usr/bin/go` não era o compilador Go. O caminho portátil foi `/tmp/specmd-go-sdk/go/bin/go`.

Na pasta deste documento, prepare as dependências com acesso à rede:

```sh
GOTOOLCHAIN=local GOPATH=/tmp/specmd-go-path GOCACHE=/tmp/specmd-go-build-cache GOMODCACHE=/tmp/specmd-go-mod-cache /tmp/specmd-go-sdk/go/bin/go mod tidy
```

Com as dependências disponíveis, compile e execute a matriz sem acesso ao proxy de módulos:

```sh
python3 run_experiment.py --go /tmp/specmd-go-sdk/go/bin/go --offline
```

O harness tem timeout finito de compilação e de cada caso. Ele grava JSON e logs em `evidence/`. Seu código final `0` significa que os resultados observados coincidiram com a matriz, inclusive as falhas deliberadas. Isso não significa que todos os cenários passaram nem que todos os casos foram autorizados pelo gate.

## Caminho de execução

1. Ler [contract.md](contract.md), que contém dois blocos Gherkin em português.
2. Construir o AST Markdown com Goldmark e selecionar nós `FencedCodeBlock` da linguagem `gherkin`.
3. Identificar IDs de cenário e registrar documento, bloco e linha da tag.
4. Entregar os conteúdos ao Godog por `Options.FeatureContents`, usando nomes de origem como `contract.md#gherkin-1`.
5. Executar step definitions contra as funções reais em [system.go](system.go).
6. Registrar o resultado do runner separadamente da decisão do gate do experimento.

Linhas em branco são prefixadas ao conteúdo em memória para manter o alinhamento das linhas dos diagnósticos com o Markdown original. Esse padding é uma transformação em memória; não cria um arquivo Gherkin separado. Os campos `scenario_origins` e `observed_scenarios[].origin` são produzidos pelo extrator e apontam para a linha da tag de ID. São distintos das posições impressas pelo próprio Godog: os logs positivos mostram `contract.md#gherkin-1:15` e `contract.md#gherkin-2:49`, linhas dos cenários.

As tags são usadas para selecionar os casos do experimento. A extração das cercas usa o parser Markdown; a interpretação dos passos e da sintaxe Gherkin cabe ao Godog. A pequena busca de IDs nas tags serve à rastreabilidade do protótipo e não constitui um parser Gherkin próprio.

## Matriz pretendida

| Caso | Exercício | Gate esperado |
| --- | --- | --- |
| `pass` | Soma e cancelamento em blocos distintos, com duas asserções corretas. | Permitir. |
| `failure` | A soma real é 5, mas o cenário exige 99. | Recusar. |
| `undefined` | Um passo não possui definição registrada. | Recusar. |
| `pending` | Um passo retorna `godog.ErrPending`; Godog relata um passo pendente e dois skipped. | Recusar. |
| `filtered` | Filtro exclui todos os cenários esperados. | Recusar, inclusive se o runner retornar 0. |
| `partial` | Apenas um dos dois cenários obrigatórios é selecionado. | Recusar, inclusive se o runner retornar 0. |
| `zero` | Bloco Gherkin tem funcionalidade, mas nenhum cenário. | Recusar. |
| `no-gherkin` | Markdown não contém Gherkin. | Recusar antes de invocar o runner. |
| stdin do adaptador | O próprio adaptador recebe Markdown por stdin e executa os casos positivos. | Permitir. |

O gate do experimento exige a execução dos IDs esperados exatamente uma vez, resultado positivo e retorno adequado do runner. A lista esperada é explícita na matriz; ela não é deduzida apenas dos cenários que o runner decidiu executar.

O caso `no-gherkin` é negativo porque essa matriz exige IDs comportamentais e não oferece uma dispensa aceita. Ele não representa o tratamento do produto para um documento informativo com classificação e dispensa humanas válidas; esse mecanismo está fora do protótipo.

## API de conteúdo e filesystem virtual

`godog.Options` e `godog.Feature` são nomes públicos exportados, embora sejam aliases de tipos definidos internamente. O protótipo importa somente `github.com/cucumber/godog`; não importa pacotes `internal`. A opção `FeatureContents` possui comentário oficial documentando a entrega de conteúdo em bytes. Como a versão é `0.x`, não se presume estabilidade universal ou indefinida.

O caminho `bytes` instala um `fs.FS` que recusa qualquer `Open`. Os casos executados registraram **zero aberturas** nesse filesystem do runner, demonstrando que os conteúdos foram consumidos pela API em memória.

Também foram executados dois probes com `testing/fstest.MapFS`, da biblioteca padrão:

| Transporte | Entrada do Godog | Resultado observado |
| --- | --- | --- |
| `bytes` | `FeatureContents`, com nomes `.md#gherkin-N`. | Dois cenários passam; nenhum acesso ao filesystem do runner. |
| `vfs` | `Options.FS` com conteúdos extraídos em memória e caminhos `.md#gherkin-N` explícitos. | Dois cenários passam, sem arquivos físicos `.feature`. |
| `vfs-dir` | O mesmo filesystem virtual, mas com descoberta pelo diretório `.`. | Zero cenários e runner `0`; gate recusa. |

A diferença é explicada pela fonte: a descoberta por diretório filtra o sufixo `.feature`, enquanto um caminho explícito é aberto e interpretado como Gherkin sem exigir essa extensão. Isso não faz do Godog um parser de Markdown cercado: os probes de VFS recebem Gherkin já extraído do `.md` pelo adaptador.

`FeatureContents` é o caminho mais direto validado neste experimento. A alternativa VFS também foi comprovada com caminhos explícitos, mas uma varredura de diretório não encontra esses nomes Markdown.

## CLI nativo: fonte inspecionada, sem execução direta

Na versão `v0.16.0`, o comando oficial `godog run` se declara deprecated e recomenda integração com `testing.T`. Sua documentação apresenta argumentos como caminhos de features. O código encaminha stdin ao binário gerado, mas isso, isoladamente, não implementa entrada de texto Gherkin pelo stdin.

A leitura conjunta do binding de flags e dos caminhos do parser não mostrou uma opção CLI que popula `FeatureContents` a partir de uma string de argumento ou de stdin. Essa é uma conclusão da inspeção da versão fixada; **o CLI oficial não foi compilado nem exercitado neste experimento**. O suporte stdin executado pertence ao adaptador em `main.go`, que lê Markdown e chama a API pública.

## Limites

- `-source -` é uma interface implementada neste adaptador. Não demonstra suporte nativo de stdin no CLI do Godog.
- A utilização programática de Godog é específica desta versão e deste ecossistema. Não implica suporte equivalente em Cucumber-JVM, Cucumber.js ou outros runners.
- O protótipo não implementa aceite humano, assinaturas, inventário completo, proteção contra edição maliciosa do gate ou integração CI protegida.
- O resultado positivo comprova o comportamento dos exemplos exercitados, sem demonstrar a completude dos requisitos.
- Cenários deliberadamente incorretos neste documento de pesquisa são instrumentos do experimento; não são novos requisitos de produto aceitos.

## Fontes oficiais para conferência

- [Release Godog v0.16.0](https://github.com/cucumber/godog/releases/tag/v0.16.0).
- [Options na versão v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/options.go).
- [Opções e conteúdos de features na versão v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/internal/flags/options.go).
- [Alias público `Feature`, test_context.go](https://github.com/cucumber/godog/blob/v0.16.0/test_context.go#L371-L372).
- [Execução do Godog na versão v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/run.go).
- [Parser: filtro de diretório e leitura de bytes](https://github.com/cucumber/godog/blob/v0.16.0/internal/parser/parser.go).
- [CLI: argumentos, depreciação e encaminhamento de stdin](https://github.com/cucumber/godog/blob/v0.16.0/cmd/godog/internal/cmd_run.go).
- [Flags do runner](https://github.com/cucumber/godog/blob/v0.16.0/internal/flags/flags.go).
- [Goldmark v1.7.13](https://github.com/yuin/goldmark/tree/v1.7.13).
- [Arquivo oficial do SDK Go 1.25.0](https://go.dev/dl/go1.25.0.linux-amd64.tar.gz).

As fontes do Godog citadas acima foram inspecionadas no módulo local obtido pelo toolchain, com versão e checksums de `go.sum`. Os caminhos de conteúdo, VFS e stdin do adaptador foram executados; a análise do CLI nativo foi somente estática.
