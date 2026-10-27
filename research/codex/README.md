# Preparing the local integration with Codex

Status: plugin installed by the real Codex CLI and dispatch of its hooks demonstrated with a deterministic local backend. **There was no real LLM model response in this trial.** The attempt with the configured service failed on authentication; human trust through the interface remains a separate proof.

| Layer | Current evidence |
| --- | --- |
| Core and adapter | [49 unit tests](evidence/unit-tests.json) passed. |
| CLI/bootstrap | The same 11 cases passed on the [source](evidence/preflight-integration.json) and on the [bundle](evidence/bundle-integration.json). |
| Marketplace/plugin | [Real installation](evidence/installed-plugin.json), `installed: true`, `enabled: true`, version `0.1.0`, three hooks listed. |
| Trial trust | Confirmed by native listing, restricted to session flags; persistent trust unchanged. |
| Native host control | [Two cases passed](evidence/native-fixture-results.json) with simulated local HTTP responses and handlers instrumented through flags. |
| Dispatch of the installed plugin | [Three cases passed](evidence/installed-dispatch.json) using the package from the cache, without inline handlers; they include a change by a real tool and simulated HTTP responses. |
| Configured model service | [Real attempt](evidence/runtime-results.json) returned `401`; the stop cycle was not completed. |
| Human `/hooks` and contractual acceptance | Not performed; cannot be inferred from session trust. |

## Checks run

The executable `/opt/codex/bin/codex` answers `codex-cli 0.163.0`. Help, discovery, installation and runtime commands were run. The first attempts failed with a read-only filesystem; after the environment became writable, the marketplace and the plugin were installed. The timeline below preserves the initial failures and distinguishes the host run with simulated responses from the attempt with a real model service. No authentication files were inspected.

Reproducing the local collection:

```sh
python3 research/codex/probe_cli.py
```

The five commands and their outputs are in [evidence/cli-help.json](evidence/cli-help.json). The PATH aliases warning on a read-only filesystem was kept in the evidence; it did not prevent the help commands. The path and permission of a future installation need to be checked in the environment where it will happen.

## Installation supported by the CLI

The CLI has `plugin` and accepts a local or Git marketplace:

```text
codex plugin marketplace add <SOURCE>
codex plugin add <PLUGIN>@<MARKETPLACE>
```

`SOURCE` can be a local path, `owner/repo[@ref]`, an HTTPS Git URL or an SSH Git URL. The marketplace command offers `--ref`, `--sparse` and JSON output. The install command also accepts `PLUGIN --marketplace MARKETPLACE`.

The help does not show an option for per-project installation scope; the official schema describes `marketplaces` as user entries. The installer source uses the store in Codex home and calls `set_user_plugin_enabled`; a configuration profile does not automatically redirect that store.

## Local package and discovery proof

The initial package uses the paths recognized by the host:

- [Local marketplace](../../.agents/plugins/marketplace.json): `specmd-local`, with local source `./dist/codex-plugin` pointing to a generated bundle.
- [Plugin manifest](../../.codex-plugin/plugin.json): `specmd`, version `0.1.0`, hooks in `./hooks/hooks.json`.
- [Hooks declaration](../../hooks/hooks.json): synchronous `SessionStart`, `PostToolUse` and `Stop` handlers, with a 30-second timeout.

The handlers call the package's script through `PLUGIN_ROOT`, a variable actually injected by the host. The source also provides the alias `CLAUDE_PLUGIN_ROOT`; no `CODEX_PLUGIN_ROOT` variable was found on that path. The interpreter uses `SPECMD_PYTHON` when defined and `python3` as the default. The commands of this initial packaging use POSIX shell syntax.

Before registering or installing the marketplace, generate the bundle from the canonical sources:

```sh
python3 scripts/build_codex_plugin.py
```

The builder includes only `.codex-plugin/plugin.json`, `hooks/hooks.json`, `scripts/codex_hook.py`, `src/specmd/*.py` and `pyproject.toml`. It adds a SHA-256 build manifest, without granting acceptance or trust. The result goes to `dist/codex-plugin`, ignored by Git. No second copy of the sources is kept in the repository.

This content boundary is necessary: the `0.163.0` installer calls `copy_dir_recursive`, which walks directories and copies files without consulting `.gitignore`. Pointing the marketplace at the root would also copy `.venv`, `.git` and research artifacts; symbolic links are not copied by that function, which could also leave a copied venv incomplete. The bundle avoids that cost and contains no dependencies, caches or Git files.

The observed build included nine files, totaling 29,058 bytes of sources, plus the manifest. The fingerprint and the individual hashes are in the discovery evidence. The fingerprint identifies the bundle's content, not a human approval.

`SPECMD_PYTHON` must point to the absolute interpreter of the original development environment, outside the bundle and the plugin cache. The venv can stay at the root of the local clone, as long as it is not copied into the package. The installed script loads the bundle's own `src`; the external interpreter provides its dependencies.

Since `dist/` is generated and not versioned, registering this repository directly as a remote Git marketplace does not, by itself, produce an installable package. The validated flow is local clone, installation of dependencies, bundle build and registration of the local marketplace. Remote distribution with a published bundle will be a step of its own.

Discovery was run by Codex itself, with invocation-only configuration:

```sh
codex -c 'marketplaces.specmd-local.source_type="local"' -c 'marketplaces.specmd-local.source="/workspace/specmd"' plugin list --marketplace specmd-local --available --json
```

The result was code `0`, plugin `specmd@specmd-local`, version `0.1.0`, source `/workspace/specmd/dist/codex-plugin`, `installed: false` and `enabled: false`. The output is in [evidence/local-marketplace-discovery.json](evidence/local-marketplace-discovery.json), including hashes of the builder and the bundle. This proves the host's recognition of the marketplace and the manifest, without proving script execution or installation.

To install in a user environment with writable configuration, the supported interfaces are `codex plugin marketplace add /path/to/specmd` and `codex plugin add specmd@specmd-local`. These steps persist user state. `HOME` or `CODEX_HOME` were not redirected to work around environment restrictions.

## Initial history: installation prevented by the filesystem

After authorization to install the concrete package, the absence of a marketplace with the same name was checked. `codex plugin marketplace list --json` returned an empty list, as shown in [evidence/marketplace-before-install.json](evidence/marketplace-before-install.json).

The official command `codex plugin marketplace add /workspace/specmd --json` returned code `1`:

```text
failed to create marketplace install directory /run/codex-environment/codex-home/.tmp/marketplaces: Read-only file system (os error 30)
```

The output is in [evidence/marketplace-add-attempt.json](evidence/marketplace-add-attempt.json). In that attempt, the registration was not completed and the plugin installation did not proceed. The user directory was not remapped. Discovery being available with overrides was evidence distinct from installation.

## Effective installation and hooks listing

With the environment later writable, the official marketplace and plugin commands ran successfully. [installed-plugin.json](evidence/installed-plugin.json) records `specmd@specmd-local` installed and enabled, version `0.1.0`, with the installed copy matching the canonical sources.

The native listing recognized the three handlers `SessionStart`, `PostToolUse` and `Stop`, initially untrusted. Session-restricted flags made the reviewed handlers trusted in the listing, without changing persistent trust. This proves installation and recognition; it does not yet prove their dispatch nor human interaction through the `/hooks` screen. `HOME` and `CODEX_HOME` were preserved.

## Hooks confirmed in the version's schema

The official schema `rust-v0.163.0` defines these events:

`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact` and `Interrupt`.

There is configuration for command and MCP handlers; the schema also declares prompt/agent variants. Presence in the schema does not demonstrate that any combination was exercised in this environment. For SpecMD, the first candidates are session start, detection after tools and the completion decision through `Stop`.

The official plugin manifest has a `hooks` component, with inline declaration or a reference to files. The configuration exposes state with `enabled` and `trusted_hash`. An excerpt of the schema, with source URL and blob, is in [evidence/schema-excerpt.json](evidence/schema-excerpt.json).

## Trust and control: source and scope of the trials

The official source of `config_rules.rs` accepts hook state changes only from the user and session-flag layers. Project and plugin layers can declare hooks, but cannot write that user state.

This layering rule does not, by itself, establish an authority out of the agent's reach: if the agent controls the user configuration or the invocation flags, the separation must be enforced by the environment. The later trials requested trust restricted to the concrete handlers and checked `trustStatus` through the native listing. No bypass flag was used, nor was a human UI action presented as performed.

In the `Stop` implementation, a handler authorized to apply control effects can block the stop via JSON with `decision: "block"` and a non-empty reason. There is also handling of exit `2` with a reason on stderr. The source itself has a test case indicating that exit `2` without a reason does not block. Therefore, blindly translating any non-zero code of the future SpecMD CLI into a block would be incorrect.

The `PreToolUse` implementation also has a blocking result, including a deny permission decision and handling of exit `2` with a reason. This event was studied in the source, but was not exercised by SpecMD in this trial. The observed execution of `SessionStart` and `Stop` is described separately below.

The official TUI has the `/hooks` command, described as lifecycle hook management. Interaction with that screen and the human granting of trust were not exercised. A trust hash may be handler-specific; assigning it through configuration remains an act of trust, not an operation the plugin can perform on behalf of the human.

In the inspected source, the trust hash is computed over the normalized identity of the handler's configuration — event, matcher and command — and not over the bytes of every external script called. Changing a script while keeping the command declaration may preserve that identity. Package integrity and contract acceptance require their own controls; they cannot be automatically attributed to Codex's trust mechanism.

Hook trust is not equivalent to SpecMD's acceptance of requirements. The former authorizes running an integration; the latter must record agreement with a specific version of the contract. The adapter must preserve this difference, allow handing control back while waiting for the user and keep the protected check in CI as an independent guarantee.

## Initial history: runtime prevented by the filesystem

The first attempts of `codex app-server --stdio` and `codex exec` could not initialize the host because of a read-only filesystem. The original evidence remains in [runtime-discovery-failure.json](evidence/runtime-discovery-failure.json) and [runtime-startup-attempt.json](evidence/runtime-startup-attempt.json). These attempts produced neither hook dispatch nor model responses.

An attempt was made to redirect only SQLite and operational logs, without changing `HOME`, `CODEX_HOME` or the location of authentication, but that did not remove the need to write to the original directory. The source also resolves an `installation_id` file with a write; the observed message does not identify the exact syscall that failed. The candidate hashes of that first attempt came from reading the source, not from a native `hooks/list` response; the provenance remains recorded in the historical JSON.

After the environment became writable, native discovery and the trials below became possible. The old failures do not describe the current state and were not rewritten as positive results.

## Native discovery and attempt with a real model service

The harness [probe_runtime.py](probe_runtime.py) started receiving a real `hooks/list` listing, without creating a thread or turn in the discovery step. The response uses a flat list with camelCase metadata. The concrete commands and hashes are in [runtime-discovery.json](evidence/runtime-discovery.json); that file does not grant trust by itself.

The authorized trial used session-restricted trust and checked it through the native listing. The harness passes the trust state map in a way that preserves the full keys returned by the host; it does not depend on interpreting those keys as dotted TOML paths. The persistent trust configuration was not changed.

In the attempt with the configured model service, the host started the thread and ran `SessionStart`, but received `401 Unauthorized` with a message that the authentication could not be interpreted. There was no model response nor a `Stop` call. [runtime-results.json](evidence/runtime-results.json) records the failure of the trial's expectations; [runtime-hook-events.jsonl](evidence/runtime-hook-events.jsonl) records the initial event observed, without copying private transcripts.

This is an authentication failure of the real attempt, not evidence that the hook cycle passed with an LLM. No authentication files were read or replaced to work around it.

The harness keeps discovery and execution separate:

```sh
# Discover the concrete handlers without running hooks or the model.
.venv/bin/python research/codex/probe_runtime.py --discover

# After reviewing and authorizing these specific handlers for the trial:
.venv/bin/python research/codex/probe_runtime.py --run \
  --reviewed-hooks research/codex/evidence/runtime-discovery.json
```

The run depends on a working model service and may incur billed usage. The normal installation guide still asks for review through the `/hooks` interface; this harness's restricted flags are an explicit trial mechanism, and do not represent a human UI action that was performed.

## Host control with deterministic responses

[probe_native_fixture.py](probe_native_fixture.py) started the **real Codex executable** with a local HTTP endpoint that returns Responses API events and fixed text. There was no model inference. The endpoint recorded only the necessary metadata, without inspecting authentication headers or storing the content of the requests.

The first trial used handlers instrumented through session flags, forwarding native payloads to the same SpecMD adapter. The instrumentation made it possible to count the events, as recorded in [native-fixture-results.json](evidence/native-fixture-results.json) and [native-fixture-hook-events.jsonl](evidence/native-fixture-hook-events.jsonl):

| Case | `SessionStart` | `Stop` | Requests to the simulated backend | Final state |
| --- | --- | --- | --- | --- |
| `blocked` | 1 | 2 | 2 | `blocked`, `may_complete: false` |
| `waiting` | 1 | 1 | 1 | `waiting_human_review`, `may_complete: false` |

The block requested a continuation; the second stop handed control back. The human wait handed control back at the first stop. Ending the Codex turn did not release the task in SpecMD's state. The fixtures remained unchanged, except for the observed cache.

The host emitted a warning about missing metadata for the fictitious identifier `specmd-fixture` and about using fallback metadata. That warning is in the evidence; it does not represent discovery nor execution of a real LLM model.

## Dispatch of the installed plugin

A second trial, [probe_installed_dispatch.py](probe_installed_dispatch.py), used the package **installed in the Codex cache**, without declaring inline handlers. The listing recognized the plugin's three hooks and confirmed session-only trust. The cache hashes matched the canonical sources.

[installed-dispatch.json](evidence/installed-dispatch.json) records success in all three cases. In the block and wait cases, the first request contained the `SessionStart` context marker; there were two requests in the block case and one in the human wait case. The last event saved by the plugin itself was `Stop`, and the state remained at `may_complete: false`. The host returned code `0`, which means the trial ended, not contractual approval.

In the third case, the simulated backend emitted a function call and Codex ran the real tool `exec_command` to change a contract in a disposable temporary directory. Before the next response, `PostToolUse` recorded `modified: contract.md` and the new hash. The final stop kept `waiting_human_review` and `may_complete: false`. Thus, the three declared events were exercised by the installed plugin, without attributing model reasoning to the fixed responses.

The backend remained local and deterministic. This result proves the connection between installation, native dispatch and adapter for the exercised paths; it does not demonstrate that an LLM interpreted the instructions, that the trust UX was used or that there was human acceptance of a contract. The installation persisted the marketplace/plugin as enabled; hook trust was session-only, without changing persistent trust.

## Proofs that remain pending

- Human trust through the `/hooks` screen, distinct from the trust restricted to the trial.
- Complete flow with the real model service, prevented in this attempt by the `401`.
- Experience of resuming and correcting documents in real work.
- Separate human authority, integrated BDD execution and a protected CI gate, which do not exist in this increment.

The real installation and the controlled tests do not remove these limitations. The evidence must remain separated by layer, instead of using "it worked in Codex" as a substitute for all of them.

## Pinned official sources

- [Config schema, rust-v0.163.0](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/config.schema.json), blob `4aba1bab6cd2cbcc179a5de802731f2775c6bc88`.
- [Plugin manifest](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/plugin/src/manifest.rs), blob `30e6cda1734e3c7c991b3b6b7990d0c42e8b6b85`.
- [Authorized layers for hook state](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/config_rules.rs), blob `050932ecbbff46ef87a66753496e8036d5ed47e5`.
- [Stop handling](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/stop.rs), blob `be2be9100e356427b298f24872113852eab3862a`.
- [PreToolUse handling](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/events/pre_tool_use.rs), blob `e57b823a1c8673ff1f5fe291b13e3274a1967a8d`.
- [Marketplace and local source resolution](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/marketplace.rs), blob `2199fe4e1e937e239304e0bf26ab56b793f8409c`.
- [Installer and user activation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/manager.rs), blob `d4411b50da9f459bd8ba267b9c785247c131312d`.
- [Recursive package copy, without a Git filter](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core-plugins/src/store.rs#L736-L757), blob `087eae6d7b89fa230b3b0c44fcb5706000542cdd`.
- [Plugin variables and handler discovery/trust](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/hooks/src/engine/discovery.rs), blob `0c5a28ef35ef0fb54c7f0b99c7f23a680af18ae2`.
- [TUI `/hooks` command](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/tui/src/slash_command.rs), blob `afb372bb7b9bc4e6f32ee82d6f86c32b4c40b97d`.
- [Fingerprint algorithm](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/config/src/fingerprint.rs#L58-L72) and [normalized identity of the hooks](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/hooks/src/engine/discovery.rs#L768-L793).
- [Effect of Stop on turn continuation](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/core/src/session/turn.rs#L737-L766).
- [Listing hooks without running handlers](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/hooks/src/registry.rs#L304-L318).
- [Per-handler trust UI](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/bottom_pane/hooks_browser_view.rs#L243-L258) and [trust persistence in the user configuration](https://github.com/openai/codex/blob/83086188ae0614bd882818ff1aa23f3194962012/codex-rs/tui/src/hooks_rpc.rs#L58-L93).

The blobs identify the sources returned by the GitHub connector. The local evidence proves the installed version and the help interfaces; reading the source proves only the design observed in that revision.
