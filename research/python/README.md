# Python: in-memory Gherkin with Behave

Experimental research, not a production implementation. **Behave is a BDD runner for Python; it is not official Cucumber.** Sharing Gherkin and depending on packages named `cucumber-*` does not make these runners equivalent.

The experiment uses **Behave 1.3.3**, Python 3.12.14 and **markdown-it-py 4.0.0**. The transitive versions actually observed are in [requirements.lock](requirements.lock). That file pins versions, but contains no hashes of the distributions and must not be presented as a supply chain check.

## Real Markdown: extended result

[probe_markdown.py](probe_markdown.py) was run against the canonical file [addition.md](addition.md), using the real `MarkdownIt` parser to locate Gherkin fences. Each selected block was parsed as a string by Behave, with prefixed empty lines to preserve the Markdown line numbers. The run used in-memory models and real step implementations, without writing `.feature`.

| Case | Observed result | `engine_failed` | Experimental gate |
| --- | --- | --- | --- |
| Two blocks in Portuguese | Two scenarios `passed`, two calls to the addition function | `false` | Allows |
| Expected 99 for the sum 2 + 3 | Scenario `failed`, assertion fails | `true` | Rejects |
| Step without implementation | Scenario `error`; steps `passed`, `undefined`, `skipped` | `true` | Rejects |
| Filter that excludes all scenarios | Two scenarios `skipped`, no call to the addition function | `false` | Rejects |

The [complete evidence](evidence/results.json) contains the SHA-256 hash of the Markdown, hashes of the scripts, expected and observed IDs, per-step results, calls to the implementation and origin `addition.md#block-N`. The positive scenarios point to lines **9 and 21** of the document; the negative ones to **33 and 43**. The match with `Cenário:` (Scenario) lines in the file was checked in the probe.

The filtered case is important evidence: the engine's failure boolean can be `false` without any behavior having been run. The experimental gate also requires the expected set of passed IDs and the expected calls to the implementation. These IDs were supplied by the experiment; they were neither inferred automatically from the prose nor approved by a human acceptance mechanism.

The harness finished with code **zero**, since the four cases produced the expected results, including the three rejections. That code does not mean that the negative scenarios passed. The evidence found no `.feature` files in the researched tree. The script contains no step that writes that type of file; the later file survey is not a complete monitor of all the process's syscalls.

## Minimal string probe

The [minimal probe](probe_minimal.py) passed Gherkin text in Portuguese to `behave.parser.parse_feature(text, filename="probe.md")`, registered real step implementations and ran the model with `ModelRunner.run_model()`. The implementation exercised was the real function `add(a, b)`. The [minimal evidence](evidence/minimal.json) preserves the results and the script's hash.

| Case | Scenario result | `engine_failed` return |
| --- | --- | --- |
| Sum 2 + 3, expected 5 | `passed` | `false` |
| Sum 2 + 3, expected 99 | `failed` | `true` |

No `.feature` file was needed on that path. The name `probe.md` is an origin identifier supplied to the parser; the minimal probe works with a string and does not, by itself, demonstrate extraction from a real Markdown document.

`run_model()` returns a **failure boolean**, not a process exit status. The probe process can finish with code zero while showing an expected failure. That means the diagnostic program ran, not that the negative scenario passed nor that a product gate should let it through.

## Conventional CLI: attempts actually run

[cli_probe.py](cli_probe.py) runs the Behave module in an empty temporary directory, supplying the same text in three ways:

| Attempt | Observed CLI exit status | Observed behavior |
| --- | --- | --- |
| Complete text as a positional argument | `1` | Interpreted as a path; `ConfigError` looking for the steps directory. |
| Text through stdin, without a positional argument | `1` | Looks for the conventional `features` directory; does not run the supplied text. |
| Text through stdin, `-` argument | `1` | Looks for the path `-`; does not run the supplied text. |

These observations document the commands tested, in the context described. They do not prove that a custom runner or another CLI configuration is impossible. The successful path in this experiment was the in-memory model API, not native CLI support for Markdown.

The [CLI evidence](evidence/cli.json) distinguishes the engine's real exit status from the harness's exit status. The harness finishes with zero when it observes the three expected rejections and no `.feature` in the temporary directory. Temporary paths were replaced by `<TMPDIR>`; no credential is collected.

## Reproduction

In an environment with access to the package index, the version-reproducible installation can be done with:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.lock
.venv/bin/python probe_minimal.py
.venv/bin/python probe_markdown.py
.venv/bin/python cli_probe.py --output evidence/cli.json
```

In this environment, the main executor provisioned the dependencies outside the repository in `/tmp/specmd-python-probe`. The commands actually run for the probes were:

```sh
PYTHONPATH=/tmp/specmd-python-probe python3 probe_minimal.py
PYTHONPATH=/tmp/specmd-python-probe python3 probe_markdown.py
PYTHONPATH=/tmp/specmd-python-probe python3 cli_probe.py --output evidence/cli.json
```

The `.venv` directory, bytecode and caches are ignored. There is no need to publish the run environment nor temporary files.

## Integration surfaces and fragility

- `parse_feature()` accepts Unicode text and an origin name. This is confirmed in the code of the pinned version and in the probe run.
- `ModelRunner` runs already built model objects. The class and `run_model()` are available in the `behave.runner` module, without a private prefix; that does not constitute a promise of stability, across versions, of the coupling used here.
- `StepRegistry.add_step_definition()` allows registering steps for that model without creating a conventional tree of feature files. The probe uses an isolated registry per case.
- The configuration, the models, their states and the hooks still belong to Behave's implementation. A production adapter needs compatibility tests and explicit supported versions.
- The conventional `Runner` class includes path discovery, step loading and file parsing. The experiment uses `ModelRunner` so as not to depend on that discovery.
- An official Gherkin parser produces representations of the document; it is not, by itself, equivalent to a step runner. No official parser replaced the Behave engine in this probe.

The Markdown with Gherkin support described by the Cucumber project is a syntax proposal different from the Gherkin fences discussed in SpecMD. The existence of that documentation does not demonstrate Markdown support in Behave.

## Primary sources

The Behave sources below were consulted at tag **v1.3.3**, corresponding to the version run:

1. [Parser: `parse_feature(text, language=None, filename=None)`](https://github.com/behave/behave/blob/v1.3.3/behave/parser.py#L77).
2. [Execution model: `ModelRunner`](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L657).
3. [Running models and computing the failure boolean: `run_model`](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L915).
4. [Conventional runner and path discovery](https://github.com/behave/behave/blob/v1.3.3/behave/runner.py#L996).
5. [Official markdown-it-py project, tag v4.0.0](https://github.com/executablebooks/markdown-it-py/tree/v4.0.0). The tag consulted points to commit `c62983f1554124391b47170180e6c62df4d476ca`.
6. [Markdown with Gherkin, in the official Cucumber repository](https://github.com/cucumber/gherkin/blob/main/MARKDOWN_WITH_GHERKIN.md). This reference on `main` is contextual and not a pinned dependency of the experiment.

## Scope

The probes confirm the limited feasibility of extracting blocks from real Markdown and running Behave models in memory, including a failing assertion, an undefined step and the rejection of a fully filtered run, without `.feature`. They do not establish universal compatibility with Cucumber, stable support for all Gherkin constructs, authenticated human acceptance or the sufficiency of a real product's checks. Rules, backgrounds, scenario outlines, a document without scenarios and hooks that mark scenarios as skipped were not exercised in this Python matrix. Scenario selection, filters and non-run states must remain explicit in any later adapter.
