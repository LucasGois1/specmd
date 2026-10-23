# Adaptador Java / Cucumber-JVM

Bridge experimental real com Cucumber-JVM `8.0.4`, Gherkin `42.0.1` transitivo
e Java 21. Recebe JSON do núcleo SpecMD e fornece cada bloco Gherkin em memória
por `Resource` / `FeatureParser` / `Runtime.withFeatureSupplier`. Não depende de
arquivos `.feature`, temporários ou versionados, e não presume que Cucumber
interpreta Markdown nativamente.

## Preparar e executar

```sh
bash prepare.sh
bash build.sh
bash run.sh --glue specmd.example < input.json
python3 ../../research/workflow/probe_bridges.py --java-runner ./run.sh
```

`prepare.sh` usa Maven para resolver dependências fixadas e grava os artefatos
locais em `.work`. Pode exigir rede. `SPECMD_MAVEN_COMMAND`,
`SPECMD_MAVEN_SETTINGS` e `SPECMD_MAVEN_REPO` permitem selecionar um Maven e
cache já existentes sem instalação global. `build.sh` usa o módulo compilador
do JDK; uma instalação somente JRE sem `jdk.compiler` não é suficiente.

Também é possível compilar o projeto com Maven. Para o runtime, inclua o bridge,
suas dependências e as classes de passos no classpath.

## Integrar passos da aplicação

O exemplo `specmd.example.Steps` chama a função real
`specmd.example.Application.add` e faz uma asserção do resultado. Para seu
projeto, compile as classes de testes/aplicação e aponte seu pacote:

```sh
SPECMD_JAVA_EXTRA_CLASSPATH=/caminho/do/projeto/target/test-classes:/caminho/do/projeto/target/classes \
  bash run.sh --glue com.example.steps < input.json
```

Pacotes `--glue` podem ser repetidos. Registre todos os passos necessários;
o bridge não gera implementações nem oferece passos universais. Ele não lê
`cucumber.properties` nem aplica filtros de cenário ou dry-run.

No `specmd.toml` schema2 do projeto, configure o comando do bridge já compilado:

```toml
[[runners]]
id = "java"
language = "java"
command = ["bash", "/caminho/specmd/adapters/java/run.sh", "--glue", "com.example.steps"]
timeout = 60
```

Se houver outros runners, distribua documentos com `paths` sem atribuir o mesmo cenário a dois motores.

## Protocolo e limites

Entrada schema 1: `features` contém `{path, block, line, content}`; `line` é a
primeira linha do corpo do bloco no Markdown. `expected_scenarios` contém
`{id, path, block, line}` com a linha do cabeçalho do cenário simples.
O cenário deve ter exatamente uma tag própria `@SMD-…-SCN-…`.

Saída stdout: um único JSON com `schema:1`, `mode:"real"`, `dry_run:false`,
`engine_failed`, `passed` e resultados com origem, status, `steps_executed` e
estados dos passos. Logs e saída normal do código de teste vão para stderr.
Exit 0 exige todos os cenários esperados passando uma única vez, com passos
executados e origem correspondente. Zero, IDs extras/duplicados, passos
indefinidos/ignorados/pendentes e resultados incompletos não viram sucesso.

O incremento suporta cenários simples e Background. Rule e Scenario Outline
são recusados antes da execução; instâncias de Examples não são creditadas ao
ID de template. Use um runner que suporte instâncias concretas para esses casos.

As classes usadas do Cucumber core têm visibilidade Java pública, mas não
devem ser tratadas como uma API estável de longo prazo. A integração está
fixada e precisa de regressão a cada atualização. Os passos executam código
do projeto e podem acessar seu ambiente como qualquer teste. Isolamento de
credenciais e proteção contra saídas inválidas permanecem responsabilidade do
chamador. Um relatório verde não é aceite humano nem prova de asserções fortes.

Fontes e experimentos anteriores: [pesquisa Java](../../research/java/README.md).
