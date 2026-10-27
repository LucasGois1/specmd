# Go / Godog adapter

Real experimental integration with Godog `v0.16.0`. The caller sends the Gherkin
blocks extracted from the Markdown files as JSON; the package runs them in
memory through `godog.Options.FeatureContents`. No `.feature` is created or
discovered.

## Integrating with the application

The integration point is `Run(input, ScenarioInitializer)`, or `Serve(stdin,
stdout, ScenarioInitializer)` for a subprocess used by the SpecMD core.
Register your application's real steps in the initializer; the example in
`cmd/specmd-example` calls an `Add` function and checks its result.

```go
func main() {
    os.Exit(specmdgodog.Serve(os.Stdin, os.Stdout, initializeMySteps))
}
```

The module uses an example path (`example.com/specmd/adapters/go`). Inside
another module, use a `replace` pointing to this directory until the
distribution path is defined. The library does not offer a universal set of
steps.

```sh
go test ./...
go build -o specmd-go-example ./cmd/specmd-example
./specmd-go-example < input.json
```

Requires Go `1.25.0` and the dependencies pinned in `go.mod`/`go.sum`. The first
dependency resolution may require network access; do not install tools globally.

In the project's schema2 `specmd.toml`, configure your executable with the registered steps:

```toml
[[runners]]
id = "go"
language = "go"
command = ["/path/to/specmd-go-runner"]
timeout = 60
```

If there are other runners, distribute documents with `paths` without assigning the same scenario to two engines.

## Protocol

schema 1 input: `features` contains `{path, block, line, content}`; `line` is the
first line of the block's body in the Markdown. `expected_scenarios` contains
`{id, path, block, line}`; here `line` is the line of the scenario's heading.
The ID must be the scenario's own `@SMD-…-SCN-…` tag.

Output: a single JSON object with `schema:1`, `mode:"real"`, `dry_run:false`,
`engine_failed`, `passed` and results with origin, status, `steps_executed` and
the states of each step. Runner logs go to stderr. Exit code 0 only occurs
when all expected scenarios pass, exactly once, with steps run. Missing,
extra and duplicate IDs and divergent origins fail.

This increment accepts simple scenarios and Background. Rule and Scenario Outline
are explicitly rejected, including when the caller sends IDs of Examples
instances. There are no tag filters or dry-run in the protocol.

The initializer and the steps are code trusted by the developer: they can read
and change the environment like any application test. `Serve` redirects Go's
normal stdout to stderr, but code that writes directly to the descriptor can
get around that; the caller must reject extra or invalid output.

This report is evidence of execution, not human acceptance nor authorization
to complete. Empty steps or weak assertions still require review. The core's
gate must bind the evidence to the current contract, code and configuration.
