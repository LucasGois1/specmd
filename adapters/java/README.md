# Java / Cucumber-JVM adapter

Real experimental bridge with Cucumber-JVM `8.0.4`, transitive Gherkin `42.0.1`
and Java 21. It receives JSON from the SpecMD core and supplies each Gherkin
block in memory through `Resource` / `FeatureParser` / `Runtime.withFeatureSupplier`.
It does not depend on `.feature` files, temporary or versioned, and does not
presume that Cucumber interprets Markdown natively.

## Preparing and running

```sh
bash prepare.sh
bash build.sh
bash run.sh --glue specmd.example < input.json
python3 ../../research/workflow/probe_bridges.py --java-runner ./run.sh
```

`prepare.sh` uses Maven to resolve pinned dependencies and writes the local
artifacts to `.work`. It may require network access. `SPECMD_MAVEN_COMMAND`,
`SPECMD_MAVEN_SETTINGS` and `SPECMD_MAVEN_REPO` let you select an existing Maven
and cache without a global installation. `build.sh` uses the JDK's compiler
module; a JRE-only installation without `jdk.compiler` is not enough.

It is also possible to compile the project with Maven. For the runtime, include
the bridge, its dependencies and the step classes on the classpath.

## Integrating application steps

The example `specmd.example.Steps` calls the real function
`specmd.example.Application.add` and makes an assertion on the result. For your
project, compile the test/application classes and point to your package:

```sh
SPECMD_JAVA_EXTRA_CLASSPATH=/path/to/project/target/test-classes:/path/to/project/target/classes \
  bash run.sh --glue com.example.steps < input.json
```

`--glue` packages can be repeated. Register all the necessary steps; the bridge
neither generates implementations nor offers universal steps. It does not read
`cucumber.properties` nor apply scenario filters or dry-run.

In the project's schema2 `specmd.toml`, configure the command of the already compiled bridge:

```toml
[[runners]]
id = "java"
language = "java"
command = ["bash", "/path/to/specmd/adapters/java/run.sh", "--glue", "com.example.steps"]
timeout = 60
```

If there are other runners, distribute documents with `paths` without assigning the same scenario to two engines.

## Protocol and limits

schema 1 input: `features` contains `{path, block, line, content}`; `line` is the
first line of the block's body in the Markdown. `expected_scenarios` contains
`{id, path, block, line}` with the line of the simple scenario's heading.
The scenario must have exactly one own `@SMD-…-SCN-…` tag.

stdout output: a single JSON with `schema:1`, `mode:"real"`, `dry_run:false`,
`engine_failed`, `passed` and results with origin, status, `steps_executed` and
the states of the steps. Logs and normal output of the test code go to stderr.
Exit 0 requires all expected scenarios passing exactly once, with steps run
and a matching origin. Zero, extra/duplicate IDs, undefined/skipped/pending
steps and incomplete results do not become success.

The increment supports simple scenarios and Background. Rule and Scenario Outline
are rejected before execution; Examples instances are not credited to the
template ID. Use a runner that supports concrete instances for those cases.

The Cucumber core classes used have public Java visibility, but must not be
treated as a stable long-term API. The integration is pinned and needs
regression testing on each upgrade. The steps run the project's code and can
access its environment like any test. Credential isolation and protection
against invalid output remain the caller's responsibility. A green report is
neither human acceptance nor proof of strong assertions.

Earlier sources and experiments: [Java research](../../research/java/README.md).
