# Execution bridges

The core hands the Markdown's Gherkin blocks over in memory. It does not create `.feature` files.

- **Python:** `language = "python"`, directory `steps = "tests/steps"`; the included Behave worker runs the definitions in a subprocess. It supports simple scenarios, Rule and Scenario Outline examples in schema2. It does not load `environment.py` or filters from the project's Behave configuration.
- **[Java](java/README.md):** Cucumber-JVM bridge, with the project's glue and a configurable command.
- **[Go](go/README.md):** Godog library and example executable; the project registers its own steps.

Java/Go require an explicit build and command; see the limits of each bridge. The protocol is a single JSON object on stdin and a single JSON report on stdout. Log output must go to stderr.

schema1 input: `features[]` contains `path`, `block`, `line` and `content`; `expected_scenarios[]` contains expected IDs and origins. The output must declare `schema:1`, `mode:"real"`, `dry_run:false`, `engine_failed:false`, `passed:true` and `scenarios[]` with `id`, `path`, `block`, `line`, `status:"passed"` and `steps_executed` consistent with the number of steps in the contract. Any omission, extra scenario, duplicate, pending status or empty run blocks completion.

A test bridge can declare `language = "mock"` with `[evidence] allow_mock = true`. Its report must use `mode:"mock"` and never satisfies `verify --require-real`. A process that prints success is still code to be reviewed: the protocol cannot prove the strength of an assertion nor prevent a malicious implementation from lying. The gate depends on trusted execution and verifier.
