# SpecMD

Canonical Markdown documentation, with embedded BDD scenarios, kept aligned with the software while working with AI agents.

> **Status:** experimental (0.3.0). SpecMD is an assistant plugin for Claude Code and Codex: it runs deterministic checks and sends feedback back to the agent, without formal approval or auditing ([D-021](docs/decisions.md)). The [implementation status](docs/implementation-status.md) separates what exists from what is planned.

```bash
git clone https://github.com/LucasGois1/specmd.git
cd specmd
make setup    # .venv, dependencies and plugin
make demo     # new demo project in ~/specmd-demo
make agent    # Claude Code in the demo, with the SpecMD plugin loaded
make status   # demo status; make run runs the scenarios
```

In `make agent`, ask the agent for a rule change, for example "add a 10% discount for totals above 1000 cents". It writes the rule and the scenarios in the Markdown, asks for your confirmation, implements, and SpecMD runs the scenarios at the end.

## Use it in your repository

Inside Claude Code, in your repository:

```
/plugin marketplace add LucasGois1/specmd
/plugin install specmd@specmd        → choose the project or local scope
```

Done: SpecMD is now active in that repository, with the defaults. For the team to get the plugin automatically, run `/specmd:init` (or `make init REPO=…` from this clone) and commit `.claude/settings.json`; whoever opens Claude Code in the repository and trusts the folder gets the plugin.

In a project that already has documentation, `/specmd:adopt` drives the adoption: it lists the documents without scenarios, you say which ones do not describe behavior and the agent proposes the scenarios one document at a time.

`specmd.toml` and `.specmdignore` are optional, to adjust the behavior (see the [format](docs/format.md)). SpecMD's messages are in English; `language = "pt"` in `specmd.toml` switches them to Portuguese. The plugin needs Python 3.11 or later on the machine; the dependencies come with it.

## The problem

Agents forget conditions, interpret rules differently or invent rules nobody asked for, and write tests that protect them. With tests in separate `.feature` files, the documentation and the tests can also diverge from each other.

## How SpecMD helps

- **A single source.** Requirements and Gherkin scenarios live in the same Markdown, which is the business rule and the acceptance test at the same time. There is no `.feature` to maintain.
- **Feedback at the right moment.** After editing the documentation, the agent receives the gaps (requirement without a scenario, invalid Gherkin). New scenarios must be shown to the developer before the implementation. After changing the code, the scenarios are run and whatever fails comes back with the step and the error.
- **No lock-up.** The feedback repeats while it makes a difference; the same gap repeated, or four consecutive blocks, let the agent finish. Plugin errors become warnings.
- **Existing engines.** Python/Behave directly, and bridges for Cucumber-JVM (Java) and Godog (Go) through the same in-memory protocol ([adapters](adapters/README.md)).

## Documentation

| Document | Content |
| --- | --- |
| [Quickstart](docs/quickstart.md) | Installation, demo, commands and use with Claude Code. |
| [Implementation status](docs/implementation-status.md) | What exists, limits and validations. |
| [Product](docs/product.md) | Problem, proposal, flow and limits. |
| [Requirements and scenarios](docs/requirements.md) | SpecMD's obligations in Gherkin in the Markdown itself. |
| [Format](docs/format.md) | How to write documents, requirements, scenarios, `.specmdignore` and `specmd.toml`. |
| [Decisions](docs/decisions.md) | Guidelines and the D-021 change of direction. |
| [Runner research](research/README.md) | Prototypes and evidence per language. |
| [Native dispatch in Claude Code](research/claude/README.md) | Real headless sessions exercising the hooks. |
| [Positioning](docs/positioning.md) | Prior art and overlap with other tools. |

Documents from before D-021 (architecture, integrations, indexing, roadmap, validation plan, experimental Codex and the [HANDOFF](HANDOFF.md)) are marked as historical where they describe the signed acceptance.

## Tests

`python -m unittest discover -s tests` (or `make test`). The hook tests create real projects and actually run Behave; the hook payloads are simulated. The native bridges have their own checks in `adapters/`.
