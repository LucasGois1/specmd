# Baseline: Markdown with Gherkin in Cucumber.js

> Status: **baseline run with Cucumber.js 13.3.0**. MDG was discovered and run by the real CLI; the negative case failed on an executed assertion. This does not constitute an implementation of the product nor production support for its plugins.

This experiment distinguishes the existence of the **Markdown with Gherkin (MDG)** format from the real discovery and execution capability of the Cucumber.js CLI. It uses a canonical Markdown file `addition.feature.md`, without a separate `.feature` file and without conversion to that format.

## Observed environment

- Node: `v24.19.0`.
- npm: `11.9.0`.
- `@cucumber/cucumber`: `13.3.0`; `--version` returned `13.3.0`.
- Resolved `@cucumber/gherkin`: `42.0.1`.
- Resolved `@cucumber/messages`: `34.2.1`.
- Engines declared by the runner: Node `22 || 24 || >=26`.
- Run: `2026-10-23T02:16:07.680Z` to `2026-10-23T02:16:14.986Z`, corresponding to the night of 22/10/2026 in America/Sao_Paulo.

The fixture uses the English headings `Feature` and `Scenario` and steps in a list to investigate the MDG format indicated by the source. Support for the Portuguese dialect is not presumed, nor equivalence with a block fenced by three backticks and marked as `gherkin`.

## Official sources

- [Markdown with Gherkin, pinned revision](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md).
- [Cucumber.js](https://github.com/cucumber/cucumber-js).
- [Official Cucumber.js 13.3.0 package](https://www.npmjs.com/package/@cucumber/cucumber/v/13.3.0).
- [Official Gherkin 42.0.1 package](https://www.npmjs.com/package/@cucumber/gherkin/v/42.0.1).

The documentary indication of support in the JavaScript parser from version 19 does not, by itself, demonstrate that the CLI of every Cucumber.js version runs this format. In this trial that distinction was checked by running the real CLI at the pinned version, without a custom Markdown adapter.

## Observed results

| Case | Exit | Scenarios | Steps | Conclusion limited to the trial |
| --- | --- | --- | --- | --- |
| MDG `.feature.md`, explicit path | `0` | 1 | 3 passed | Native execution confirmed. |
| MDG `.feature.md`, incorrect expectation | `1` | 1 | 2 passed, 1 failed | `AssertionError`: 2 + 3 produced 5, and the scenario required 6. |
| Default discovery in `features/`, without an explicit path | `0` | 1 | 3 passed | Native discovery of `.feature.md` confirmed; the steps path was passed explicitly. |
| Same MDG in a plain `.md`, explicit path | `0` | 1 | 3 passed | The `.feature.md` extension was not mandatory when the path was given. |
| Gherkin in a fenced block, explicit plain `.md` | `0` | 0 | 0 | The CLI did not run this fixture's block; exit zero does not mean coverage. |

The test did not investigate default discovery of any `.md`, dialects other than English, integration in other languages nor governance features. Local inspection of the installed package found the default glob `features/**/*.{feature,feature.md}` in `lib/paths/paths.js`, consistent with the observed discovery.

Small evidence files, without installed dependencies or working copies:

- [Structured results and normalized commands](results/13.3.0.json).
- [Output of the five cases](results/13.3.0.log).
- [Resolved versions and lockfile digest](results/dependency-versions.json).

Only the environment's absolute paths were replaced by placeholders. Statuses, counts, exit codes and the assertion message were preserved. The full lockfile remains in the local result; the script exports it on each reproduction.

## What the script checks

Each case runs in isolation, with a real addition implementation and a `node:assert/strict` assertion:

1. MDG `.feature.md` with an explicit path and a correct result.
2. MDG `.feature.md` with an explicit path and an incorrect result: the result 6 is required for 2 + 3, whose implementation returns 5.
3. Default discovery of `.feature.md` inside `features/`, without an explicit path.
4. Same MDG as a plain `.md` file, with an explicit path.
5. Traditional Gherkin fenced in a `gherkin` block, in a plain `.md`, with an explicit path.

The script records the exit code, the runner's output, the JSON report and the count of scenarios/statuses. Exit code zero with zero scenarios **does not count as support**. A parsing failure in the negative case **does not count as a behavioral test that failed**.

## Reproduction

To research a different current version, query and record the result; this is separate from reproducing the pinned version:

```sh
npm view @cucumber/cucumber version engines --json
```

To reproduce the observed baseline, give the **exact** version; the script does not silently pick `latest`:

```sh
node research/javascript-mdg/run.mjs --version 13.3.0 --install
```

`--install` authorizes the installation attempt in the script; it does not replace the environment's network permission. Dependencies go in a temporary directory separate from the repository. Each process has a finite timeout. The installation's manifest and lockfile are preserved together with the results for reproduction.

To repeat with the installation already present, omit `--install`. To choose destinations outside the repository:

```sh
node research/javascript-mdg/run.mjs --version 13.3.0 --cache-dir /tmp/specmd-mdg-cache --output-dir /tmp/specmd-mdg-results/13.3.0
```

There is no need to create `.feature` files, nor to keep two documents with the same scenario. The `.feature.md` files of this trial remain Markdown.

## Local checks performed

During offline preparation, the JavaScript syntax, the script's help and the addition function were checked, as recorded in [preparation.json](preparation.json). Later the main agent installed the pinned version and ran the five cases. The later evidence in `results/` records the real Cucumber test and replaces the initial pending run.

## Relation to the product proposal

Native MDG execution is a direct precedent of the idea of executable Markdown documentation and reduces the work needed in that layer. Therefore, running scenarios from Markdown must not be presented as a novelty by itself.

This result does not demonstrate mechanisms for versioned human acceptance, approved documentation exemption, change traceability, protection against self-acceptance or integration with hooks. Those mechanisms need to be compared and validated separately; this trial does not establish the novelty of the product as a whole.

There is a concrete format decision: reusing MDG takes advantage of support that already exists in this Cucumber.js version. The previous format of fenced `gherkin` blocks requires another integration, since the fixture in that format produced zero scenarios in the direct run tested. The two syntaxes must not be treated as equivalent, nor should the product contract be changed without recording that decision.
