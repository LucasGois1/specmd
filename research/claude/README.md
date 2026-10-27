# Native dispatch in Claude Code

This experiment loads the SpecMD plugin in real Claude Code sessions, with a real model, on new projects created by `specmd demo`. It records which hooks the host dispatches and what feedback SpecMD sends back to the agent.

## How to reproduce

At the root, after `pip install -e .` and with the `claude` CLI authenticated:

```sh
python scripts/build_codex_plugin.py
python research/claude/probe_headless.py
```

The default report goes to `.specmd/local/claude-headless.json`; `--record` writes the versioned evidence to `evidence/`. `--use-clone` loads the plugin from the clone itself instead of the bundle. The `claude` executable comes from `PATH`, the interpreter is the one running the probe and the model is fixed (`haiku`): no argument chooses arbitrary commands or paths. Each run creates new demos in a temporary directory and consumes a small model quota.

The session uses `claude -p` with `--plugin-dir`, `--setting-sources project,local`, `--strict-mcp-config` and `--permission-mode acceptEdits`. The first two options isolate the plugin from hooks, plugins and MCP servers of the user's settings.

## Cases

| Case | Request to the agent | What is checked |
| --- | --- | --- |
| `documentation_gap` | Document a shipping rule without changing code. | The hooks dispatch without failure and the feedback about `docs/shipping.md` (`docs/frete.md` in the recorded evidence, which predates the English translation) reaches the agent (a gap or a request to confirm the scenarios). |
| `code_breaks_scenario` | Add a 1-cent fee to the total. | The documented scenarios fail and `Stop` sends the scenario, the step and the error back to the agent. |
| `implement_confirmed` | Implement already confirmed scenarios, with one step still without implementation. | `Stop` runs the scenarios; the final state is recorded. |

In all cases: plugin loaded, `SessionStart` and `Stop` dispatched, no hook failure and no response that ends the session.

## Recorded evidence

[evidence/headless-dispatch.json](evidence/headless-dispatch.json) identifies the Claude Code version, the model, the dispatched hooks, the feedback sent back and the final state of each case. Local paths were replaced by placeholders and other local plugins appear only as a count.

In one run of this investigation (Claude Code 2.1.309, `claude-haiku-5-5`), the agent:
- wrote the shipping rule already with scenarios, presented them and asked for confirmation, pointing out the ambiguity of "acima de 10000" ("above 10000");
- on seeing the cart scenarios fail because of the fee, did not change the documentation and asked whether the rule had changed;
- implemented the coupon step until the three scenarios passed.

That behavior belongs to the model in that run; the probe checks the dispatch and the feedback of the hooks, and does not guarantee how another model will respond.

## Limits

- The `-p` mode does not show the workspace trust dialog and there is no real dev answering the agent.
- Marketplace installation was not exercised; the plugin was loaded only for the session.
- Hooks and plugins from the user's settings were excluded.
