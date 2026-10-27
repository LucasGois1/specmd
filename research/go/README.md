# Go experiment: canonical Markdown with Godog

This directory contains an isolated integration prototype, not the SpecMD implementation. It extracts Gherkin blocks from Markdown with Goldmark and hands them to Godog as in-memory content, without requiring or producing `.feature` files.

**Run:** the 11 probes of the extended matrix matched what was expected. Two real scenarios passed through the in-memory path; incorrect assertion, undefined step, pending step, incomplete filters and absence of scenarios were rejected by the gate. The state and the UTC date are in [evidence/summary.json](evidence/summary.json), with hashes of the sources run. This result is a technical proof restricted to the integration exercised.

## Pinned versions

- Godog: `v0.16.0`.
- Goldmark: `v1.7.13`.
- SDK used in the research environment: Go `1.25.0`, Linux/amd64, installed portably outside the repository.
- SHA-256 of the official file `go1.25.0.linux-amd64.tar.gz`, checked during preparation: `2852af0cb20a13139b3448992e69b868e50ed0f8a1e5940ee1de9e19a123b613`.

The direct dependencies are in [go.mod](go.mod); the resolved checksums go into `go.sum` after preparation. SDK, caches and the build binary must not be published.

## Reproduction

Use a real Go SDK; in this environment `/usr/bin/go` was not the Go compiler. The portable path was `/tmp/specmd-go-sdk/go/bin/go`.

In this document's folder, prepare the dependencies with network access:

```sh
GOTOOLCHAIN=local GOPATH=/tmp/specmd-go-path GOCACHE=/tmp/specmd-go-build-cache GOMODCACHE=/tmp/specmd-go-mod-cache /tmp/specmd-go-sdk/go/bin/go mod tidy
```

With the dependencies available, compile and run the matrix without access to the module proxy:

```sh
python3 run_experiment.py --go /tmp/specmd-go-sdk/go/bin/go --offline
```

The harness has a finite timeout for compilation and for each case. It writes JSON and logs to `evidence/`. Its final code `0` means that the observed results matched the matrix, including the deliberate failures. It does not mean that all scenarios passed nor that all cases were authorized by the gate.

## Execution path

1. Read [contract.md](contract.md), which contains two Gherkin blocks in Portuguese.
2. Build the Markdown AST with Goldmark and select `FencedCodeBlock` nodes of the `gherkin` language.
3. Identify scenario IDs and record document, block and tag line.
4. Hand the contents to Godog through `Options.FeatureContents`, using origin names such as `contract.md#gherkin-1`.
5. Run step definitions against the real functions in [system.go](system.go).
6. Record the runner's result separately from the experiment gate's decision.

Blank lines are prefixed to the in-memory content to keep the diagnostics' lines aligned with the original Markdown. This padding is an in-memory transformation; it does not create a separate Gherkin file. The fields `scenario_origins` and `observed_scenarios[].origin` are produced by the extractor and point to the line of the ID tag. They are distinct from the positions printed by Godog itself: the positive logs show `contract.md#gherkin-1:15` and `contract.md#gherkin-2:49`, the scenario lines.

The tags are used to select the experiment's cases. Extracting the fences uses the Markdown parser; interpreting the steps and the Gherkin syntax is up to Godog. The small search for IDs in the tags serves the prototype's traceability and does not constitute a Gherkin parser of its own.

## Intended matrix

| Case | Exercise | Expected gate |
| --- | --- | --- |
| `pass` | Addition and cancellation in distinct blocks, with two correct assertions. | Allow. |
| `failure` | The real sum is 5, but the scenario requires 99. | Reject. |
| `undefined` | A step has no registered definition. | Reject. |
| `pending` | A step returns `godog.ErrPending`; Godog reports one pending step and two skipped. | Reject. |
| `filtered` | A filter excludes all expected scenarios. | Reject, even if the runner returns 0. |
| `partial` | Only one of the two required scenarios is selected. | Reject, even if the runner returns 0. |
| `zero` | A Gherkin block has a feature, but no scenario. | Reject. |
| `no-gherkin` | Markdown contains no Gherkin. | Reject before invoking the runner. |
| adapter stdin | The adapter itself receives Markdown through stdin and runs the positive cases. | Allow. |

The experiment's gate requires running the expected IDs exactly once, a positive result and an appropriate return from the runner. The expected list is explicit in the matrix; it is not inferred only from the scenarios that the runner decided to run.

The `no-gherkin` case is negative because this matrix requires behavioral IDs and offers no accepted exemption. It does not represent the product's handling of an informational document with a valid human classification and exemption; that mechanism is outside the prototype.

## Content API and virtual filesystem

`godog.Options` and `godog.Feature` are exported public names, although they are aliases of internally defined types. The prototype imports only `github.com/cucumber/godog`; it does not import `internal` packages. The `FeatureContents` option has an official comment documenting the delivery of content as bytes. Since the version is `0.x`, universal or indefinite stability is not presumed.

The `bytes` path installs an `fs.FS` that rejects any `Open`. The cases run recorded **zero opens** on that runner filesystem, demonstrating that the contents were consumed through the in-memory API.

Two probes were also run with `testing/fstest.MapFS`, from the standard library:

| Transport | Godog input | Observed result |
| --- | --- | --- |
| `bytes` | `FeatureContents`, with `.md#gherkin-N` names. | Two scenarios pass; no access to the runner's filesystem. |
| `vfs` | `Options.FS` with contents extracted in memory and explicit `.md#gherkin-N` paths. | Two scenarios pass, without physical `.feature` files. |
| `vfs-dir` | The same virtual filesystem, but with discovery through the `.` directory. | Zero scenarios and runner `0`; gate rejects. |

The difference is explained by the source: directory discovery filters on the `.feature` suffix, while an explicit path is opened and interpreted as Gherkin without requiring that extension. That does not make Godog a parser of fenced Markdown: the VFS probes receive Gherkin already extracted from the `.md` by the adapter.

`FeatureContents` is the most direct path validated in this experiment. The VFS alternative was also proven with explicit paths, but a directory scan does not find those Markdown names.

## Native CLI: source inspected, no direct execution

In version `v0.16.0`, the official `godog run` command declares itself deprecated and recommends integration with `testing.T`. Its documentation presents arguments as feature paths. The code forwards stdin to the generated binary, but that, by itself, does not implement Gherkin text input through stdin.

Reading the flag binding and the parser paths together showed no CLI option that populates `FeatureContents` from an argument string or from stdin. This is a conclusion from inspecting the pinned version; **the official CLI was neither compiled nor exercised in this experiment**. The stdin support that was run belongs to the adapter in `main.go`, which reads Markdown and calls the public API.

## Limits

- `-source -` is an interface implemented in this adapter. It does not demonstrate native stdin support in the Godog CLI.
- The programmatic use of Godog is specific to this version and this ecosystem. It does not imply equivalent support in Cucumber-JVM, Cucumber.js or other runners.
- The prototype does not implement human acceptance, signatures, a complete inventory, protection against malicious editing of the gate or protected CI integration.
- The positive result proves the behavior of the examples exercised, without demonstrating the completeness of the requirements.
- Deliberately incorrect scenarios in this research document are instruments of the experiment; they are not new accepted product requirements.

## Official sources for checking

- [Godog v0.16.0 release](https://github.com/cucumber/godog/releases/tag/v0.16.0).
- [Options in version v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/options.go).
- [Options and feature contents in version v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/internal/flags/options.go).
- [Public `Feature` alias, test_context.go](https://github.com/cucumber/godog/blob/v0.16.0/test_context.go#L371-L372).
- [Godog execution in version v0.16.0](https://github.com/cucumber/godog/blob/v0.16.0/run.go).
- [Parser: directory filter and byte reading](https://github.com/cucumber/godog/blob/v0.16.0/internal/parser/parser.go).
- [CLI: arguments, deprecation and stdin forwarding](https://github.com/cucumber/godog/blob/v0.16.0/cmd/godog/internal/cmd_run.go).
- [Runner flags](https://github.com/cucumber/godog/blob/v0.16.0/internal/flags/flags.go).
- [Goldmark v1.7.13](https://github.com/yuin/goldmark/tree/v1.7.13).
- [Official Go 1.25.0 SDK file](https://go.dev/dl/go1.25.0.linux-amd64.tar.gz).

The Godog sources cited above were inspected in the local module obtained by the toolchain, with version and checksums from `go.sum`. The adapter's content, VFS and stdin paths were run; the analysis of the native CLI was static only.
