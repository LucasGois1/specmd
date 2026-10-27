# Feasibility of running Markdown contracts

**Status:** historical report of the research and of the local prototypes run on 22/10/2026, in the America/Sao_Paulo context. The evidence preserves UTC timestamps. The later experimental implementation includes core, plugins, signed decisions and integrated run; see the [current status](implementation-status.md) and the [handoff](../HANDOFF.md). This isolated study does not demonstrate authenticated human authority or deployment of a protected gate.

## Main result

It was possible to run real steps and code in **Java, Python and Go**, from scenarios extracted from Markdown, without requiring or materializing `.feature` files. Each ecosystem needed its own integration. No universal CLI argument to receive the whole Gherkin text was found or assumed.

A baseline of the **official Markdown with Gherkin in Cucumber.js** was also run. It confirms that executable Markdown documentation already exists and needs to be considered in the decision on reuse and positioning.

## Versions and proven mechanisms

| Ecosystem | Experiment versions | Input run | Main limit |
| --- | --- | --- | --- |
| Java | Cucumber-JVM 8.0.4, CommonMark 0.24.0, Java 21.0.12.1. | `FeatureParser.parseResource` with an in-memory stream and `Runtime.Builder.withFeatureSupplier`. | Uses public core classes; public visibility does not promise a stable extension for this use. |
| Python | Behave 1.3.3, markdown-it-py 4.0.0, Python 3.12.14. | `parse_feature` with a string and `ModelRunner.run_model`, with a registry of real steps. | Behave is not official Cucumber; the programmatic integration needs to be maintained and tested per version. |
| Go | Godog 0.16.0, Goldmark 1.7.13, Go 1.25.0. | Public API `Options.FeatureContents`, with Markdown source names and in-memory content. | Discovery by directory and input by content behave differently; do not assume equivalence with the CLI. |
| JavaScript, MDG baseline | Cucumber.js 13.3.0, Gherkin 42.0.1, Node 24.19.0. | Native CLI running the MDG syntax in `.feature.md` and in a `.md` passed explicitly. | MDG uses headings and lists; fenced `gherkin` blocks were not run natively in this test. |

These are verified versions, not a stable support matrix for any project, version or third-party integration.

## Evidence per language

### Java

The adapter used CommonMark to find two blocks in Portuguese, provided the Gherkin to the parser in memory and ran the Java steps on `Application.add`. It preserved URIs with the block and the line positions in the original Markdown.

- Two positive scenarios passed and called the application.
- An incorrect assertion failed; an undefined step was reported.
- An empty filter returned code 0 with zero scenarios.
- Dry-run returned code 0 and `PASSED` events for scenarios and steps, but did not run the application. The experimental gate refused the mode.
- Text as an argument, stdin and a `.md` path in the standard CLI did not run the scenarios in the modes tested.

[Java report](../research/java/README.md) and [structured results](../research/java/evidence/results.json).

### Python

The adapter used markdown-it-py to extract the blocks from a real file, prefixed lines in memory to preserve the origin and provided the models to Behave. The step definitions called a Python sum function with real assertions.

- Two positive blocks passed, with two calls to the application and source lines checked.
- An incorrect assertion produced a failure.
- An undefined step produced an error state in the scenario and `undefined`/`skipped` states in the steps.
- A filter that removed the scenarios left `engine_failed=false`, but no behaviour was run. The experimental gate refused.
- The CLI tests are recorded separately; an input provided to our adapter does not prove native Behave support for that input.

[Python report](../research/python/README.md) and [Markdown results](../research/python/evidence/results.json).

### Go

The adapter used Goldmark to extract Gherkin and Godog's `FeatureContents` API to run steps on Go sum and cancellation functions. The report associates the results with the tags and with the source map created by the extractor.

- Two positive scenarios in distinct blocks passed.
- An assertion failure, an undefined step and a pending step were refused.
- An empty filter, a partial run and a feature without scenarios could produce code 0; the experimental gate refused the absence of the expected obligations.
- Markdown input through stdin worked in the adapter's own interface; this does not establish stdin support in the native CLI.
- Running by content worked with a filesystem that refused reads, recording zero accesses to the runner's filesystem.
- A virtual filesystem with explicit Markdown paths worked; discovery by directory ignored those names without a `.feature` extension.

The source map records the line of the extracted tag. This information must not be confused with a line property provided directly by the scenario type in the Godog callback.

[Go report](../research/go/README.md) and [structured summary](../research/go/evidence/summary.json).

### MDG baseline in JavaScript

With Cucumber.js 13.3.0 and real steps:

| Input | Observed result |
| --- | --- |
| MDG in `.feature.md`, explicit path | One scenario passed. |
| MDG in `.feature.md`, default discovery | One scenario passed. |
| MDG in a plain `.md`, explicit path | One scenario passed. |
| MDG with a deliberately wrong expectation | One scenario failed on an assertion. |
| Plain Markdown with a `gherkin` fence | Code 0, zero scenarios run. |

The `.feature.md` documentation convention makes discovery easier; the test shows that this version also runs MDG in a `.md` that is explicitly indicated. This does not imply automatic discovery of all Markdown nor support for any embedded syntax.

[MDG report](../research/javascript-mdg/README.md) and [sanitized results](../research/javascript-mdg/results/13.3.0.json).

## What analysing code and running tests means

Gherkin describes examples. The parser interprets the structure and the runner binds the steps to their implementations. It is these implementations that call the product code and verify its effects.

Therefore, collecting a scenario does not automatically produce a correct verification of the application. The agent or developer still needs to implement the steps and their assertions, and the review needs to assess their reach. Static traceability, change analysis and running are complementary mechanisms.

SpecMD does not need to create a new BDD engine. One possible design is a core that identifies the contract and the applicable scenarios, launches the language adapter and normalizes the evidence returned by existing runtimes.

## How to decide the OK

The proposed production gate must verify, at a minimum:

1. A valid human acceptance exists for the current content, classification and scope.
2. The set of mandatory scenarios is known before applying run filters.
3. The required scenarios were actually run, without omissions, duplications or improper results.
4. The run is not just parsing, discovery, simulation or dry-run.
5. The results belong to the contract, code, tests, configuration and tools relevant to the revision being assessed.
6. Undefined, pending and skipped steps and failures were not silently converted into success.

An exclusively informational task with a valid exemption may have no mandatory scenarios. The negative absence cases in the prototypes have expected behavioural obligations; they do not establish a rule of requiring Gherkin in exempted documents.

The experimental gates are predicates specific to the fixtures, including counters of calls to the application. They demonstrate the known negative cases, not a general proof that the tests are sufficient nor a protected trust boundary.

## Architecture decision to investigate

Reuse existing parsers and engines; keep the original Markdown as the contractual identity; separate authoring format, run adapter, evidence and acceptance authority.

Compare the official MDG syntax with classic Gherkin blocks before stabilizing the format. Direct support in JavaScript is not automatic portability to Java, Python or Go. The extraction adapters demonstrated do not require inventing another Gherkin grammar, but they have maintenance and compatibility costs.

The [positioning research](positioning.md) also found overlap with Tracey, Spec Kit/OpenSpec and spec-gates. The existence of feasible adapters does not prove novelty or product benefit: the next decision must compare the smallest integration needed with well-configured existing tools.

## Limits and next level of validation

The following were neither implemented nor demonstrated in this study: separate human authority, protection against integration bypass, Claude/Codex plugins, real document acceptances, production inventory or measured quality gain.

The prototypes also do not cover the whole grammar and the whole lifecycle of the runners. Outlines, tables, doc strings, application hooks, parallelism and integrations with existing projects need additional validation before announcing support. The current evidence demonstrates technical feasibility of the paths tried.
