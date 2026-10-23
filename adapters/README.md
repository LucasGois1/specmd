# Bridges de execução

O núcleo entrega os blocos Gherkin do Markdown em memória. Não cria arquivos `.feature`.

- **Python:** `language = "python"`, diretório `steps = "tests/steps"`; o worker Behave incluído executa as definições em subprocesso. Suporta cenários simples, Rule e exemplos de Scenario Outline no schema2. Não carrega `environment.py` ou filtros da configuração Behave do projeto.
- **[Java](java/README.md):** bridge Cucumber-JVM, com glue do projeto e comando configurável.
- **[Go](go/README.md):** biblioteca Godog e executável de exemplo; o projeto registra seus próprios passos.

Java/Go exigem build e comando explícitos; consulte os limites de cada bridge. O protocolo é um único objeto JSON no stdin e um único relatório JSON no stdout. Saída de logs deve ir para stderr.

Entrada schema1: `features[]` contém `path`, `block`, `line` e `content`; `expected_scenarios[]` contém IDs e origens esperadas. A saída deve declarar `schema:1`, `mode:"real"`, `dry_run:false`, `engine_failed:false`, `passed:true` e `scenarios[]` com `id`, `path`, `block`, `line`, `status:"passed"` e `steps_executed` coerente com a quantidade de passos do contrato. Qualquer omissão, cenário extra, duplicidade, status pendente ou execução vazia bloqueia a conclusão.

Um bridge de teste pode declarar `language = "mock"` com `[evidence] allow_mock = true`. Seu relatório precisa usar `mode:"mock"` e nunca satisfaz `verify --require-real`. Um processo que imprime sucesso continua sendo código a revisar: o protocolo não consegue provar a força de uma asserção nem impedir que uma implementação maliciosa minta. O gate depende de execução e verificador confiáveis.
