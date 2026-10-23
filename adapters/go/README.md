# Adaptador Go / Godog

Integração experimental real com Godog `v0.16.0`. O chamador envia os blocos
Gherkin extraídos dos Markdown por JSON; o pacote os executa em memória por
`godog.Options.FeatureContents`. Nenhum `.feature` é criado ou descoberto.

## Integrar com a aplicação

O ponto de integração é `Run(input, ScenarioInitializer)`, ou `Serve(stdin,
stdout, ScenarioInitializer)` para um subprocesso usado pelo núcleo SpecMD.
Registre os passos reais da sua aplicação no initializer; o exemplo em
`cmd/specmd-example` chama uma função `Add` e verifica seu resultado.

```go
func main() {
    os.Exit(specmdgodog.Serve(os.Stdin, os.Stdout, initializeMySteps))
}
```

O módulo usa um caminho de exemplo (`example.com/specmd/adapters/go`). Dentro
de outro módulo, use um `replace` para este diretório até definir o caminho de
distribuição. A biblioteca não oferece um conjunto universal de passos.

```sh
go test ./...
go build -o specmd-go-example ./cmd/specmd-example
./specmd-go-example < input.json
```

Requer Go `1.25.0` e as dependências fixadas em `go.mod`/`go.sum`. A primeira
resolução de dependências pode exigir rede; não instale ferramentas globalmente.

No `specmd.toml` schema2 do projeto, configure seu executável com os passos registrados:

```toml
[[runners]]
id = "go"
language = "go"
command = ["/caminho/specmd-go-runner"]
timeout = 60
```

Se houver outros runners, distribua documentos com `paths` sem atribuir o mesmo cenário a dois motores.

## Protocolo

Entrada schema 1: `features` contém `{path, block, line, content}`; `line` é a
primeira linha do corpo do bloco no Markdown. `expected_scenarios` contém
`{id, path, block, line}`; aqui `line` é a linha do cabeçalho do cenário.
O ID deve ser uma tag própria `@SMD-…-SCN-…` do cenário.

Saída: um único objeto JSON com `schema:1`, `mode:"real"`, `dry_run:false`,
`engine_failed`, `passed` e resultados com origem, status, `steps_executed` e
estados de cada passo. Logs do runner vão para stderr. Exit code 0 só ocorre
quando todos os cenários esperados passam, exatamente uma vez, com passos
executados. IDs ausentes, extras, duplicados e origens divergentes falham.

Este incremento aceita cenários simples e Background. Rule e Scenario Outline
são recusados explicitamente, inclusive quando o chamador envia IDs de
instâncias de Examples. Não há filtros por tags ou dry-run no protocolo.

O initializer e os passos são código confiado pelo desenvolvedor: podem ler e
alterar o ambiente como qualquer teste de aplicação. `Serve` redireciona stdout
normal do Go para stderr, mas código que escreve diretamente no descritor pode
contornar isso; o chamador precisa recusar saída extra ou inválida.

Esse relatório é evidência de execução, não aceite humano nem autorização de
conclusão. Passos vazios ou asserções fracas continuam exigindo revisão. O gate
do núcleo deve vincular a evidência ao contrato, código e configuração atuais.
