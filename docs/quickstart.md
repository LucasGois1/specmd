---
specmd:
  schema: 1
  id: SMD-DOC-QUICKSTART
  kind: reference
  exemption_reason: "Usage instructions for the prototype, with no additional product requirements."
---

# Try SpecMD locally

Use Python 3.11 or later and an authenticated `claude` CLI.

## Shortcut with make

At the root of the clone:

| Command | What it does |
| --- | --- |
| `make setup` | Creates `.venv`, installs the dependencies and generates the plugin in `codex-plugin/`. |
| `make demo` | Creates a new demo in `~/specmd-demo/<date-time>/cart`, already with `git init`. |
| `make agent` | Opens Claude Code in the latest demo with the plugin loaded for that session only. |
| `make status` | Summarizes the state of the latest demo. |
| `make run` | Runs the scenarios of the latest demo and summarizes the result. |
| `make test` | Runs the local test suite. |
| `make init REPO=…` | Enables the plugin for the team in one of your repositories. |

`DEMO_HOME` changes the demos folder. `CLAUDE_ARGS` passes options on to `claude`, for example `--setting-sources project,local` to avoid loading hooks and plugins from your own settings. Each `make demo` creates a new folder; earlier demos are not deleted.

## In your repository

Inside Claude Code, in your repository:

```
/plugin marketplace add LucasGois1/specmd
/plugin install specmd@specmd        → project or local scope
```

Installed in the project or local scope, the plugin is already active, with the defaults:
- every Markdown file is analysed, except `README.md`, `CHANGELOG.md`, `AGENTS.md`, `CLAUDE.md`, `LICENSE*`, `.github/` and similar;
- the Python steps in `tests/steps`, `features/steps` or `steps` are used to run the scenarios.

An installation only in the user scope does not activate repositories on its own.

For the team: `/specmd:init` (or `make init REPO=…` from this clone) declares the marketplace and enables the plugin in the project's `.claude/settings.json`, without touching anything else. Commit that file; whoever opens Claude Code in the repository and trusts the folder gets the plugin.

In a project that already has documentation, `/specmd:adopt` drives the adoption: it lists the documents without scenarios, you say which ones do not describe behaviour (they go into `.specmdignore`) and the agent proposes the scenarios one document at a time, with your confirmation. If a new scenario fails because the code does something else, it asks which of the two is right.

Local state lives in `.specmd/local/`, which ignores itself in Git.

The plugin does not pin a version in the manifest, so each commit on SpecMD's `main` is a new version. With the marketplace declared by `/specmd:init` (`autoUpdate: true`), Claude Code updates on its own. In a marketplace added by hand, use `/plugin marketplace update specmd`, then `claude plugin update specmd@specmd` and `/reload-plugins`.

## A test script

1. `make demo` and `make agent`.
2. Ask for a new rule: "add a 10% discount for totals above 1000 cents". The agent should write the requirement and the scenarios in the Markdown and ask for your confirmation. If it writes documentation without scenarios, SpecMD warns about it.
3. Confirm. The agent implements; on completion, the scenarios are run and any failure goes back to it with the step and the error.
4. Ask for something that contradicts the documentation, for example "add a 1 cent fee to the total". The existing scenarios fail and the agent should ask whether the rule changed.

## Without make

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m specmd demo --dest /path/to/new/cart
cd /path/to/new/cart && git init -q
SPECMD_PYTHON=/path/to/specmd/.venv/bin/python claude --plugin-dir /path/to/specmd
```

CLI commands, all with `--root` (default: current directory):

| Command | Result |
| --- | --- |
| `specmd init` | Declares the marketplace and enables the plugin in the project's `.claude/settings.json`. |
| `specmd inventory` | Documents, requirements, scenarios and documentation gaps. |
| `specmd check` | Gaps and the result of the last run, if still current. |
| `specmd run` | Runs all scenarios and stores the result for the hooks. |
| `specmd adopt` | Documents without scenarios and requirements without a scenario, in path order, for legacy adoption. |
| `specmd run --affected` | Runs only the scenarios affected by the change since the last run, as on completion. |

Exit codes: 0 no gaps, 1 documentation gaps or failing scenarios, 2 error or project without `specmd.toml`.

## Format

A document only needs scenarios in ```gherkin blocks; front matter is optional. Requirements may have an ID in the heading (`## PAY-REQ-001 — Refund`) and the scenarios right below are linked to them. Markdown that does not describe behaviour goes into `.specmdignore`. Details in [format](format.md).

`specmd.toml` is optional. Without `[[runners]]`, the Python steps in `tests/steps`, `features/steps` or `steps` are used; for another directory, declare:

```toml
[[runners]]
id = "python"
language = "python"
steps = "tests/steps"
```

Java and Go use a bridge `command`; see [adapters](../adapters/README.md).

## Codex

The same `hooks/hooks.json` serves Codex. The `specmd` marketplace (`.agents/plugins/marketplace.json`) points to the bundle versioned in `codex-plugin/`, generated from the sources by `scripts/build_codex_plugin.py`.

Installation, once:

```sh
codex plugin marketplace add LucasGois1/specmd
codex plugin add specmd@specmd
```

Update:

```sh
codex plugin marketplace upgrade specmd
codex plugin add specmd@specmd
```

To test a local clone, replace `LucasGois1/specmd` with the path of the clone.

After installing or updating, open `codex`, run `/hooks` and trust the four handlers of `specmd@specmd`; also check that they are enabled. Codex stores the hash of the plugin content together with the trust, so each update asks for a new review.

In Codex, the plugin is installed per user; SpecMD acts in projects that have a `specmd.toml` or that enable it in their own `.codex/config.toml` (`specmd init` writes that entry; Codex only reads the configuration of trusted projects). See the [native sessions in Codex](../research/codex/native-session.md).
