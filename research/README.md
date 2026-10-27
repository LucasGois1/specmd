# Runner feasibility research

This investigation addresses the requirement to run canonical scenarios in Markdown in Java, Python and Go projects without requiring `.feature` files. The prototypes are reproducible experiments, not the implemented product, nor evidence of human acceptance of this repository's contracts.

## Questions to test

1. Does the runner's CLI accept Gherkin content as an argument or standard input, or does it interpret the arguments as paths?
2. Is there an API that accepts text, models or in-memory content without having to materialize `.feature`?
3. Is that API public/documented, or does it depend on internal components subject to change?
4. Do real steps run code of the language and produce distinct results for success, failure and undefined step?
5. How do filtered, ignored or nonexistent scenarios affect the exit code? Is an additional gate needed?
6. Is it possible to preserve the origin in `.md`, the IDs and the position of the block?
7. Which format and mechanism should be reused instead of reinvented?

## Experiments by ecosystem

| Directory | Hypothesis investigated | Result obtained |
| --- | --- | --- |
| [java](java/) | Cucumber-JVM with an in-memory scenario supplier. | Run with 8.0.4; positives and negatives matched expectations. |
| [python](python/) | Behave with text parsing and an in-memory executable model. | Run with 1.3.3 and markdown-it-py; Behave is not official Cucumber. |
| [go](go/) | Godog with feature content supplied by API. | Run with 0.16.0, including filters, adapter stdin and virtual filesystem. |
| [javascript-mdg](javascript-mdg/) | Baseline of the official Markdown with Gherkin in Cucumber.js. | Native MDG confirmed in 13.3.0; fenced blocks did not run scenarios. |

The [consolidated study](../docs/runner-feasibility.md) distinguishes results, APIs, maintenance risks and the limits of what was demonstrated. The prototypes do not constitute production support nor implement human acceptance.

## Preparing tests with agents

The [local Codex investigation](codex/README.md) records the CLI 0.163.0 already available, the marketplace installation interfaces and the reading of official sources on hooks and trust. Help and version commands were run; installing SpecMD, firing hooks and blocking in a real session remain pending.

The [native dispatch in Claude Code](claude/README.md) records headless sessions with a real model, the plugin loaded through `--plugin-dir` and the blocking of code before acceptance. The trust dialog, interactive UX and marketplace installation were not exercised.

## Evidence criterion

The positive case must run real step implementations and code of the language. Isolated parsing or runner simulation is not enough. The negative cases need to record the engine's real result and the gate's decision; the harness may finish successfully because it correctly observed an expected failure.

To get OK, `exit code 0` is not enough: the set of required scenarios must have actually been run with a passing result. Absence of scenarios or filtering cannot become silent success.

Versions, commands, inputs and limitations must remain reproducible. Downloaded dependencies, SDKs and caches are not part of the canonical source and must not be published together with the results.

## Official precedent already identified

[Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) defines a Markdown dialect with headings, lists and `.feature.md` files. The documentation consulted indicates support in the JavaScript implementation of the parser. That does not establish equivalent native support in every runner or language.

Its syntax differs from Gherkin blocks in code fences. A `.feature.md` is Markdown and can remain the canonical source; it is not a parallel `.feature` copy. The comparison must assess compatibility and reuse, without inventing a product distinction based only on the file name.

The parser produces scenario structures; the engine still needs to bind them to step implementations and run them. Passing messages or ASTs between ecosystems is not presumed to be a universal interface.

## Relation to the project

- [Requirements](../docs/requirements.md)
- [Proposed format](../docs/format.md)
- [Architecture](../docs/architecture.md)
- [Validation plan](../docs/validation-plan.md)
- [Positioning and precedents](../docs/positioning.md)

The results of this investigation should update the roadmap and the product hypotheses. No precedent documentation, by itself, demonstrates the quality of its implementation or SpecMD's advantage.
