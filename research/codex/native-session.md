# Native sessions in Codex with a real LLM (24/10/2026)

Validation of [D-027](../../docs/decisions.md): the SpecMD plugin installed in the real Codex CLI, with a real model, on the four hook events.

## Environment

- Codex CLI `0.163.0`, authenticated with ChatGPT, `hooks` feature enabled.
- Model `gpt-6-luna`.
- Plugin installed from the repository's local marketplace: `codex plugin marketplace add <repo>` and `codex plugin add specmd@specmd-local`. The bundle comes from `scripts/build_codex_plugin.py`.
- Trust in the four handlers given by the user in `/hooks`, without the trust bypass.
- Run with `codex exec --json`, resuming the next turn with `codex exec resume <thread>`. To reduce noise, the runs turned off, through `-c`, the MCP servers of `config.toml` and the user's other plugins. The user's global instructions remained in effect.
- The hooks' output was observed through the optional `SPECMD_HOOK_LOG` log, because the JSON of `codex exec` does not show the hooks' output.

## What was observed

| D-027 point | Result |
| --- | --- |
| Available events | `/hooks` listed and trusted the plugin's `SessionStart`, `UserPromptSubmit`, `PostToolUse` and `Stop`. All four fired in the sessions. |
| `additionalContext` at the start | The agent cited SpecMD's instructions ("preciso confirmar os cenários antes de implementar", "I need to confirm the scenarios before implementing") in the first turn. |
| `additionalContext` after tools | `PostToolUse` returned "documentação alterada … mostre-os e peça confirmação" ("documentation changed … show them and ask for confirmation") after the `apply_patch` on `docs/cart.md`. |
| `Stop` with `decision: block` | With a failing scenario, `Stop` blocked; Codex handed control back to the agent, which asked the dev which rule applies (`request_user_input_async`); the next `Stop` let it finish with the summary. |
| Project root without `CLAUDE_PROJECT_DIR` | The hook used the session's directory; the state stayed in the project's `.specmd/local/`. |
| Four-turn script | Proposal before implementing; after "confirmo" ("I confirm"), implementation with `Stop` "5 cenários passando" ("5 scenarios passing") and a confirmation reminder; a contradictory request (fee) became a proposal; a new document became a scenario proposal before writing. |
| Latency | `PostToolUse` from 77 to 248 ms; `Stop` 105 to 141 ms without a run and 840 ms with a run; `SessionStart` 889 ms in the new project. |

## Observed limits

- **Activation:** in Codex, installation is per user. SpecMD only acts in repositories with `specmd.toml` or with the plugin enabled in the project's `.claude/settings`. On 26/10/2026, in a trusted project, a local `.codex/config.toml` with `[plugins."specmd@specmd-local"] enabled = false` made `codex plugin list --json` report the plugin as disabled inside the project and enabled outside it. This indicates that Codex applies plugin enablement per project, the equivalent of `.claude/settings.json`. Whether the hooks follow that state at runtime was not verified, because the hooks were disabled in `/hooks` at the time.
- **Updating requires new trust:** after `codex plugin add` with a new bundle, Codex stopped calling the hooks until the user reviewed them again in `/hooks`, even though the `trusted_hash` values in `config.toml` had not changed and the installed copy worked when called by hand. In a later observation (25/10/2026), each handler in `[hooks.state."specmd@specmd-local:…"]` also carried a `trusted_content_hash`, which is the hash of the plugin's content and explains the new review on each update, and an `enabled`. With `enabled = false`, `/hooks` shows nothing to trust and the hooks do not run until they are re-enabled there.
- **User environment:** the user's global instructions (for example, making a local commit) show up in the agent's behavior; they apply equally with and without SpecMD.
- **First run:** in a project without history, the first failure of a scenario receives the divergence guidance even when it was the agent that broke the code; the guidance says to ask the dev, which was the observed behavior.
