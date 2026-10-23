# Pesquisa executada: Cucumber-JVM a partir de Markdown

Experimento local de viabilidade do SpecMD, realizado em 22/10/2026 no contexto do usuário (`America/Sao_Paulo`). Os artefatos de execução registram seu instante em UTC, que já corresponde a 23/10. Não é uma implementação do produto, de aceite humano ou de bloqueio protegido.

## Resultado

**Foi possível executar passos Cucumber-JVM reais, sobre código de aplicação real, fornecendo cenários extraídos de Markdown em memória, sem criar arquivos `.feature`.** O caminho usa APIs do core e exige um adaptador; a CLI padrão não recebe o texto Gherkin como argumento nem o executa a partir de stdin nos modos ensaiados.

O ensaio usa Cucumber-JVM **8.0.4**, release oficial de 02/10/2026, commit [`8a14d94caae7b51f79d60a4a738f69147ad6dbfe`](https://github.com/cucumber/cucumber-jvm/tree/8a14d94caae7b51f79d60a4a738f69147ad6dbfe). Usa CommonMark Java **0.24.0** para identificar os blocos fenced e OpenJDK **21.0.12.1** para compilar e executar. O Maven **3.9.9** resolve as dependências; Gherkin **42.0.1** e Messages **34.2.1** são transitivas dessa versão do Cucumber. Os 24 jars resolvidos têm seus SHA-256 em [dependency-checksums.json](evidence/dependency-checksums.json).

## Evidência obtida

Resultados de uma execução real de `bash run.sh`:

| Caso | Exit code Cucumber | Cenários finalizados | Chamadas à aplicação | Decisão do gate de pesquisa |
| --- | --- | --- | --- | --- |
| Dois cenários em português, em dois blocos do mesmo `.md` | 0 | 2 | 2 | Elegível. |
| Asserção deliberadamente errada: esperar `6` para `2 + 3` | 1 | 1, `FAILED` | 1 | Recusado. |
| Passo sem definição | 1 | 1, `UNDEFINED` | 0 | Recusado. |
| Filtro que remove todos os cenários obrigatórios | 0 | 0 | 0 | Recusado. |
| Dry-run | 0 | 2, agregados como `PASSED` | 0 | Recusado: modo dry-run, sem execução da aplicação, apesar de eventos `PASSED`. |

O dry-run demonstrou uma particularidade importante: nesta versão os eventos agregados do cenário **e dos passos** foram `PASSED`, embora a aplicação não tenha sido chamada. O probe coleta `TestStepFinished`, além de `TestCaseFinished`, confere o conjunto esperado e finalizado, e recusa a configuração dry-run. Exit code zero e eventos `PASSED`, isoladamente, não comprovam execução. No caso de passo indefinido, os eventos reais foram `PASSED`, `UNDEFINED` e `SKIPPED`.

Isso é compatível com a fonte oficial: [TestCase seleciona o modo DRY_RUN](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/TestCase.java#L51-L59), [ExecutionMode retorna PASSED](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/ExecutionMode.java#L15-L19) e [dryRunStep não executa o passo](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/PickleStepDefinitionMatch.java#L71-L74).

O **exit code do harness foi 0 porque os resultados positivos e negativos corresponderam às expectativas do experimento**. Isso não transforma falhas deliberadas em conformidade: cada caso preserva o exit code do runner e a decisão separada do gate. O predicado do gate é específico destes fixtures e observa também uma chamada esperada à aplicação por cenário; não é uma prova geral de qualidade dos testes.

O inventário físico desta pasta continha **zero arquivos `.feature` antes e depois**. O adaptador não grava essa extensão nem temporariamente. Os cenários são parseados a partir de `ByteArrayInputStream`.

Artefatos:

- [results.json](evidence/results.json): versões, instante UTC, hashes dos fixtures, cenários esperados, cenários e passos observados, URIs, linhas, resultados da CLI e decisões separadas.
- [run.log](evidence/run.log): resumo efetivamente emitido pelo harness.
- [dependency-checksums.json](evidence/dependency-checksums.json): identidade dos jars utilizados.

## Como o adaptador funciona

1. CommonMark identifica apenas os blocos fenced cujo info string é exatamente `gherkin`.
2. Cada bloco recebe uma URI como `specmd:///fixtures/passing.md#block-1`. O fragmento diferencia blocos da mesma documentação e evita tratá-los como uma única fonte em mapas baseados em URI.
3. Linhas vazias são antepostas ao texto do bloco para preservar as linhas do documento original.
4. Um `Resource` fornece essa URI e um `ByteArrayInputStream` ao `FeatureParser.parseResource`.
5. `Runtime.builder().withFeatureSupplier(...)` recebe a lista de features já parseadas, substituindo a descoberta usual por caminhos.
6. O backend Java encontra os passos em [Steps.java](src/main/java/specmd/research/Steps.java), que chamam [Application.add](src/main/java/specmd/research/Application.java) e verificam o resultado com uma asserção real.
7. Eventos do runner preservam identidade, URI e linha do cenário. O probe compara os IDs obrigatórios, os eventos e as chamadas observadas.

Os cenários positivos foram reportados nas linhas **13 e 28** de [passing.md](fixtures/passing.md), pertencentes aos blocos 1 e 2. Os casos de falha e passo indefinido foram reportados na linha **8** de seus respectivos Markdown. O harness também confere que cada posição reportada corresponde à linha com o nome do cenário no arquivo original.

O código completo está em [Probe.java](src/main/java/specmd/research/Probe.java). A documentação Markdown continua sendo o artefato editável que contém o comportamento; não existe cópia `.feature` para manter em sincronia.

## CLI: testes realmente realizados

O probe lançou processos separados de `io.cucumber.core.cli.Main`, com os passos e um listener reais no classpath. Forneceu o mesmo texto Gherkin de soma como:

| Entrada ensaiada | Observação |
| --- | --- |
| Um argumento posicional contendo o texto inteiro | Exit 1; o texto foi interpretado como um caminho inexistente (`path must exist`). |
| stdin, com argumento `-` | Exit 1; `Unknown option: -`. |
| stdin, sem caminho | Exit 0; zero cenários finalizados e zero chamadas à aplicação. |
| Caminho `fixtures/passing.md` | Exit 0; zero cenários finalizados e zero chamadas à aplicação. |

Os argumentos, stdin utilizado, saídas e códigos observados estão no JSON. Um contador em [CliCounter.java](src/main/java/specmd/research/CliCounter.java) registra os eventos reais quando o runtime chega a ser inicializado. Ausência desse contador nas duas falhas de parsing da CLI não é contabilizada como execução de cenário.

Essas observações correspondem à CLI e versão fixadas. Não significam que nenhum adaptador, engine JUnit ou integração de terceiros possa oferecer outra entrada.

## APIs públicas em Java e estabilidade

Os pontos usados têm visibilidade `public` no Java: `Runtime.Builder.withFeatureSupplier`, `FeatureSupplier`, `FeatureParser.parseResource` e `Resource`. Isso torna a integração possível sem reflexão ou modificação dos jars. **Visibilidade pública não equivale a uma extensão estável prometida para este uso.** São classes do core; seu [README oficial](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/README.md#L4-L7) desencoraja a dependência direta usual.

O adaptador deverá fixar versões, testar a atualização do core e assumir o custo de manutenção. O overload que recebe `String` em `GherkinMessagesFeatureParser` está depreciado; o probe prefere o caminho `Resource`/`InputStream`.

## Markdown with Gherkin não é este formato

A proposta oficial [Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/v42.0.1/MARKDOWN_WITH_GHERKIN.md) usa uma gramática Markdown específica, com cabeçalhos e listas. Ela não significa que qualquer Markdown com blocos fenced seja executável pela CLI.

No parser Java da versão **42.0.1**, a [fonte oficial](https://github.com/cucumber/gherkin/blob/v42.0.1/java/src/main/java/io/cucumber/gherkin/GherkinParser.java#L64-L80) diz explicitamente que `.feature.md` não é suportado e usa `TEXT_X_CUCUMBER_GHERKIN_PLAIN`. A nota do documento MDG dessa versão limita o suporte anunciado a JavaScript. Por isso, este ensaio extrai Gherkin padrão dos blocos e fornece o texto em memória. A URI terminar em `.md` não faz o parser interpretar Markdown automaticamente.

## Reprodução

Requisitos: Linux/POSIX shell, Java com o módulo `jdk.compiler` disponível, Python 3, curl e tar. O ensaio registrado usou Java 21. Não exige instalação global nem `sudo`.

```sh
cd research/java
bash prepare-dependencies.sh
bash run.sh
```

O primeiro comando precisa de rede para Maven Central. Se Maven não estiver instalado, baixa Maven 3.9.9 para `/tmp/specmd-java-tools` (ou `SPECMD_JAVA_CACHE`), verifica o SHA-512 publicado e configura o proxy de sessão quando presente. Não escreve nem imprime credenciais. O Maven configura timeouts de conexão/leitura; em ambientes restritos, a autorização de rede deve ser concedida pelo mecanismo do ambiente antes da execução.

Depois de preparados os jars, `run.sh` compila e executa sem baixar dependências. Usa `java -m jdk.compiler/com.sun.tools.javac.Main` porque o ambiente observado contém o módulo de compilação, mas não o binário `javac` no `PATH`. Os arquivos `.work/` e os caches estão ignorados no Git. O script atualiza as evidências sanitizadas desta pasta.

## Fontes oficiais consultadas

| Fonte fixada | Informação utilizada |
| --- | --- |
| [Release 8.0.4](https://github.com/cucumber/cucumber-jvm/releases/tag/v8.0.4) | Versão e release pesquisadas. |
| [Runtime.Builder](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/Runtime.java#L175-L178) e [seleção do fornecedor](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/Runtime.java#L262-L267) | Injetar features já parseadas e evitar descoberta por paths. |
| [FeatureSupplier](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/FeatureSupplier.java#L7-L9) | Fornecedor de `List<Feature>`. |
| [FeatureParser](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/feature/FeatureParser.java#L31-L46) e [Resource](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/resource/Resource.java#L10-L24) | URI e stream de conteúdo em memória. |
| [USAGE da CLI](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/resources/io/cucumber/core/options/USAGE.txt#L1) e [parser de argumentos](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/options/CommandlineOptionsParser.java#L197-L205) | Entrada por path/URI, e não pelo texto de cenário ou `-`. |
| [FeatureIdentifier](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/feature/FeatureIdentifier.java#L42-L43) | Descoberta normal restringe extensão a `.feature`. |
| [ExitStatus](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/ExitStatus.java#L49-L62) | Zero resultados pode gerar sucesso; status `SKIPPED` não força falha. |
| [BOM](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-bom/pom.xml) | Gherkin e Messages transitivos fixados. |
| [Gherkin Java 42.0.1](https://github.com/cucumber/gherkin/blob/v42.0.1/java/src/main/java/io/cucumber/gherkin/GherkinParser.java#L64-L80) | MDG não é suportado por esse parser Java. |
| [CommonMark Java 0.24.0](https://github.com/commonmark/commonmark-java/tree/commonmark-parent-0.24.0) | Parser Markdown e suporte a source spans usados no adaptador. |

## Limites demonstrados e próximos testes

- A prova cobre estes fixtures, esta stack e estas versões; não suporte universal a Cucumber.
- Não implementa classificação aceita, autoridade humana, assinatura, política protegida ou gate de integração.
- O gate de pesquisa recusa os casos negativos conhecidos; não prova que qualquer asserção é suficiente ou que toda intenção foi especificada.
- URI sintética com fragmento e linhas preservadas funcionou nos eventos coletados. Compatibilidade com todos os formatters, IDEs e links de arquivos não foi testada.
- O extrator aceita apenas blocos com info string exata `gherkin`. Marcação de exemplos não executáveis, seções mistas e os metadados finais do SpecMD ainda precisam de desenho.
- Scenario Outline, Background, tabelas, doc strings, hooks de aplicação, paralelismo, erro de sintaxe e deduplicação avançada não foram exercitados neste mínimo. O suporte do parser a um recurso não substitui sua validação ponta a ponta no adaptador.
- Nenhum cenário deste experimento representa aceite humano do produto. As evidências mostram execução e limites técnicos, não autorização para alterar contratos.
