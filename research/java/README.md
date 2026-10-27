# Research run: Cucumber-JVM from Markdown

Local SpecMD feasibility experiment, carried out on 22/10/2026 in the user's context (`America/Sao_Paulo`). The run artifacts record their instant in UTC, which already corresponds to 23/10. It is not an implementation of the product, of human acceptance or of protected blocking.

## Result

**It was possible to run real Cucumber-JVM steps, over real application code, supplying scenarios extracted from Markdown in memory, without creating `.feature` files.** The path uses core APIs and requires an adapter; the standard CLI neither receives the Gherkin text as an argument nor runs it from stdin in the modes tried.

The trial uses Cucumber-JVM **8.0.4**, official release of 02/10/2026, commit [`8a14d94caae7b51f79d60a4a738f69147ad6dbfe`](https://github.com/cucumber/cucumber-jvm/tree/8a14d94caae7b51f79d60a4a738f69147ad6dbfe). It uses CommonMark Java **0.24.0** to identify the fenced blocks and OpenJDK **21.0.12.1** to compile and run. Maven **3.9.9** resolves the dependencies; Gherkin **42.0.1** and Messages **34.2.1** are transitive dependencies of this Cucumber version. The 24 resolved jars have their SHA-256 in [dependency-checksums.json](evidence/dependency-checksums.json).

## Evidence obtained

Results of a real run of `bash run.sh`:

| Case | Cucumber exit code | Scenarios finished | Calls to the application | Research gate decision |
| --- | --- | --- | --- | --- |
| Two scenarios in Portuguese, in two blocks of the same `.md` | 0 | 2 | 2 | Eligible. |
| Deliberately wrong assertion: expect `6` for `2 + 3` | 1 | 1, `FAILED` | 1 | Rejected. |
| Step without definition | 1 | 1, `UNDEFINED` | 0 | Rejected. |
| Filter that removes all required scenarios | 0 | 0 | 0 | Rejected. |
| Dry-run | 0 | 2, aggregated as `PASSED` | 0 | Rejected: dry-run mode, without running the application, despite `PASSED` events. |

The dry-run showed an important peculiarity: in this version the aggregated events of the scenario **and of the steps** were `PASSED`, even though the application was not called. The probe collects `TestStepFinished`, in addition to `TestCaseFinished`, checks the expected and finished set, and rejects the dry-run configuration. Exit code zero and `PASSED` events, in isolation, do not prove execution. In the undefined step case, the real events were `PASSED`, `UNDEFINED` and `SKIPPED`.

This is consistent with the official source: [TestCase selects the DRY_RUN mode](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/TestCase.java#L51-L59), [ExecutionMode returns PASSED](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/ExecutionMode.java#L15-L19) and [dryRunStep does not run the step](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runner/PickleStepDefinitionMatch.java#L71-L74).

The **harness exit code was 0 because the positive and negative results matched the experiment's expectations**. That does not turn deliberate failures into conformance: each case preserves the runner's exit code and the separate gate decision. The gate predicate is specific to these fixtures and also checks for one expected call to the application per scenario; it is not a general proof of test quality.

The physical inventory of this folder contained **zero `.feature` files before and after**. The adapter does not write that extension, not even temporarily. The scenarios are parsed from `ByteArrayInputStream`.

Artifacts:

- [results.json](evidence/results.json): versions, UTC instant, fixture hashes, expected scenarios, observed scenarios and steps, URIs, lines, CLI results and separate decisions.
- [run.log](evidence/run.log): summary actually emitted by the harness.
- [dependency-checksums.json](evidence/dependency-checksums.json): identity of the jars used.

## How the adapter works

1. CommonMark identifies only the fenced blocks whose info string is exactly `gherkin`.
2. Each block receives a URI such as `specmd:///fixtures/passing.md#block-1`. The fragment distinguishes blocks of the same documentation and avoids treating them as a single source in URI-based maps.
3. Empty lines are prepended to the block's text to preserve the lines of the original document.
4. A `Resource` supplies that URI and a `ByteArrayInputStream` to `FeatureParser.parseResource`.
5. `Runtime.builder().withFeatureSupplier(...)` receives the list of already parsed features, replacing the usual discovery by paths.
6. The Java backend finds the steps in [Steps.java](src/main/java/specmd/research/Steps.java), which call [Application.add](src/main/java/specmd/research/Application.java) and check the result with a real assertion.
7. Runner events preserve the scenario's identity, URI and line. The probe compares the required IDs, the events and the observed calls.

The positive scenarios were reported at lines **13 and 28** of [passing.md](fixtures/passing.md), belonging to blocks 1 and 2. The failure and undefined step cases were reported at line **8** of their respective Markdown files. The harness also checks that each reported position corresponds to the line with the scenario name in the original file.

The complete code is in [Probe.java](src/main/java/specmd/research/Probe.java). The Markdown documentation remains the editable artifact that contains the behavior; there is no `.feature` copy to keep in sync.

## CLI: tests actually performed

The probe launched separate `io.cucumber.core.cli.Main` processes, with the real steps and a listener on the classpath. It supplied the same addition Gherkin text as:

| Input tried | Observation |
| --- | --- |
| One positional argument containing the whole text | Exit 1; the text was interpreted as a nonexistent path (`path must exist`). |
| stdin, with the `-` argument | Exit 1; `Unknown option: -`. |
| stdin, without a path | Exit 0; zero scenarios finished and zero calls to the application. |
| Path `fixtures/passing.md` | Exit 0; zero scenarios finished and zero calls to the application. |

The arguments, stdin used, outputs and observed codes are in the JSON. A counter in [CliCounter.java](src/main/java/specmd/research/CliCounter.java) records the real events when the runtime does get initialized. The absence of that counter in the two CLI parsing failures is not counted as a scenario run.

These observations correspond to the pinned CLI and version. They do not mean that no adapter, JUnit engine or third-party integration can offer another input.

## Public APIs in Java and stability

The points used have `public` visibility in Java: `Runtime.Builder.withFeatureSupplier`, `FeatureSupplier`, `FeatureParser.parseResource` and `Resource`. That makes the integration possible without reflection or modification of the jars. **Public visibility is not the same as a stable extension promised for this use.** They are core classes; its [official README](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/README.md#L4-L7) discourages the usual direct dependency.

The adapter will have to pin versions, test core upgrades and take on the maintenance cost. The overload that takes a `String` in `GherkinMessagesFeatureParser` is deprecated; the probe prefers the `Resource`/`InputStream` path.

## Markdown with Gherkin is not this format

The official proposal [Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/v42.0.1/MARKDOWN_WITH_GHERKIN.md) uses a specific Markdown grammar, with headings and lists. It does not mean that any Markdown with fenced blocks is executable by the CLI.

In the Java parser of version **42.0.1**, the [official source](https://github.com/cucumber/gherkin/blob/v42.0.1/java/src/main/java/io/cucumber/gherkin/GherkinParser.java#L64-L80) says explicitly that `.feature.md` is not supported and uses `TEXT_X_CUCUMBER_GHERKIN_PLAIN`. The note in that version's MDG document limits the announced support to JavaScript. That is why this trial extracts standard Gherkin from the blocks and supplies the text in memory. A URI ending in `.md` does not make the parser interpret Markdown automatically.

## Reproduction

Requirements: Linux/POSIX shell, Java with the `jdk.compiler` module available, Python 3, curl and tar. The recorded trial used Java 21. It requires neither a global installation nor `sudo`.

```sh
cd research/java
bash prepare-dependencies.sh
bash run.sh
```

The first command needs network access to Maven Central. If Maven is not installed, it downloads Maven 3.9.9 over HTTPS to `.work/tools` (or `SPECMD_JAVA_CACHE`), verifies the published SHA-512 and configures the session proxy when present. It neither writes nor prints credentials. Maven configures connection/read timeouts; in restricted environments, network authorization must be granted through the environment's mechanism before the run.

Once the jars are prepared, `run.sh` compiles and runs without downloading dependencies. It uses `java -m jdk.compiler/com.sun.tools.javac.Main` because the observed environment contains the compiler module, but not the `javac` binary on the `PATH`. The `.work/` files and the caches are ignored in Git. The script updates the sanitized evidence in this folder.

## Official sources consulted

| Pinned source | Information used |
| --- | --- |
| [Release 8.0.4](https://github.com/cucumber/cucumber-jvm/releases/tag/v8.0.4) | Version and release researched. |
| [Runtime.Builder](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/Runtime.java#L175-L178) and [supplier selection](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/Runtime.java#L262-L267) | Inject already parsed features and avoid discovery by paths. |
| [FeatureSupplier](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/FeatureSupplier.java#L7-L9) | Supplier of `List<Feature>`. |
| [FeatureParser](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/feature/FeatureParser.java#L31-L46) and [Resource](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/resource/Resource.java#L10-L24) | URI and in-memory content stream. |
| [CLI USAGE](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/resources/io/cucumber/core/options/USAGE.txt#L1) and [argument parser](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/options/CommandlineOptionsParser.java#L197-L205) | Input by path/URI, and not by scenario text or `-`. |
| [FeatureIdentifier](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/feature/FeatureIdentifier.java#L42-L43) | Normal discovery restricts the extension to `.feature`. |
| [ExitStatus](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-core/src/main/java/io/cucumber/core/runtime/ExitStatus.java#L49-L62) | Zero results can produce success; `SKIPPED` status does not force failure. |
| [BOM](https://github.com/cucumber/cucumber-jvm/blob/8a14d94caae7b51f79d60a4a738f69147ad6dbfe/cucumber-bom/pom.xml) | Pinned transitive Gherkin and Messages. |
| [Gherkin Java 42.0.1](https://github.com/cucumber/gherkin/blob/v42.0.1/java/src/main/java/io/cucumber/gherkin/GherkinParser.java#L64-L80) | MDG is not supported by this Java parser. |
| [CommonMark Java 0.24.0](https://github.com/commonmark/commonmark-java/tree/commonmark-parent-0.24.0) | Markdown parser and source span support used in the adapter. |

## Demonstrated limits and next tests

- The proof covers these fixtures, this stack and these versions; not universal Cucumber support.
- It does not implement accepted classification, human authority, signing, protected policy or an integration gate.
- The research gate rejects the known negative cases; it does not prove that any assertion is sufficient or that all intent was specified.
- A synthetic URI with a fragment and preserved lines worked in the collected events. Compatibility with all formatters, IDEs and file links was not tested.
- The extractor accepts only blocks with the exact info string `gherkin`. Marking non-executable examples, mixed sections and SpecMD's final metadata still need design.
- Scenario Outline, Background, tables, doc strings, application hooks, parallelism, syntax errors and advanced deduplication were not exercised in this minimum. The parser's support for a feature does not replace its end-to-end validation in the adapter.
- No scenario in this experiment represents human acceptance of the product. The evidence shows execution and technical limits, not authorization to change contracts.
