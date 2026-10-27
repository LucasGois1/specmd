---
specmd:
  schema: 1
  id: SMD-DOC-INTEGRATIONS
  kind: reference
  exemption_reason: "Integration guide and limits; canonical requirements remain in requirements.md."
---

# Integrations with agents and CI

> **Historical, predating [D-021](decisions.md).** This document describes the design with signed acceptance, authority, trust and implementation blocking, removed on 23/10/2026. For the current product, see [product](product.md) and [implementation status](implementation-status.md).

The experimental core shares inventory, review, run and decision between the CLI and the adapters. Start with the [quickstart](quickstart.md) and see the [implementation status](implementation-status.md).

| Component | Responsibility |
| --- | --- |
| Scanner | Markdown inventory, declared classification, IDs/Gherkin and deterministic manifest. |
| Review | Snapshot, full text, diffs and explicit decision bound to the version. |
| Authority | Signing and verification using trust external to the project; local demonstration mode. |
| Runners | In-memory blocks, subprocesses and exact matching of the expected instances. |
| Lifecycle | Association of acceptance, contract, code, tests, configuration, traceability and run. |
| Adapter | Translation of the states into host events and responses. |
| CI | `verify --require-real` with external trust and a verifier protected by the operator. |

The separation between authority and the agent's code depends on external permissions. A valid signature proves possession of a key and integrity of the signed content; it does not, by itself, prove human identity, reading or correctness of the requirements.

## Canonical run

The Markdown keeps requirements and scenarios together. The scanner delivers blocks with path, block, line and content; the bridge runs their in-memory representation. No step requires writing a `.feature`, not even a temporary one.

Python uses real Behave and the project's steps in a subprocess. It does not automatically load `behave.ini`, filters, dry-run or `environment.py`. Java and Go use explicitly configured bridge commands. Check each executor's subset: accepting `Rule` or Outline in the scanner does not guarantee universal execution.

The bridge's JSON protocol uses `schema: 1`, `features` and `expected_scenarios`. The output reports mode, dry-run, engine failure, instances, origin and steps. The core refuses invalid JSON, timeout, non-zero process, missing/duplicate/unknown IDs, divergent origin and pending, undefined or skipped scenarios or steps. Zero scenarios do not satisfy the contract.

`language: "mock"` requires `evidence.allow_mock: true` and keeps a simulated result. A bridge can lie about the run: its code, the steps and the verifier also need review and operational protection.

## CLI and states

Schema 1 preserves the initial scanner; schema 2 enables review, traceability and run. The CLI offers `inventory`, `review`, `run`, `check`, `status`, `audit` and `verify`; `demo` prepares a disposable project. `review --prepare` generates a proposal without accepting it.

| State | Interpretation |
| --- | --- |
| `inactive` | No opt-in and no completion decision. |
| `error` | Verification or configuration could not be determined. |
| `blocked` | Unsatisfactory structure, links, policy or run. |
| `waiting_human_review` | The version requires a valid decision; return control to the person responsible. |
| `awaiting_evidence` | A current run for the accepted snapshot is missing. |
| `demo_passed` | Demonstration flow satisfied; `demo` mode, `local_demo` assurance. |
| `passed` | Fresh real run, protected external trust and strict traceability. |

The JSON also exposes `may_complete`. In `demo_passed`, that field holds in the demonstration context and does not clear production integration. The host ending a turn does not replace the core's verdict.

## Codex and Claude Code

The package declares `SessionStart`, `PreToolUse`, `PostToolUse` and `Stop` in a single `hooks/hooks.json`, shared by Codex and Claude Code. The command resolves the root through `PLUGIN_ROOT`, injected by Codex, or through `CLAUDE_PLUGIN_ROOT`, injected by Claude Code. Start and post-tool present the state; pre-tool checks authorization; stop provides feedback or returns control. The [Codex guide](experimental-codex.md) covers build, installation and review of the handlers in `/hooks`.

In CLI `0.163.0`, trials with the executable and package installed observed dispatch, a change made by a tool and resumption after a block. The responses came from a simulated deterministic HTTP backend. The real model service returned `401`; interpretation by an LLM and human granting of trust through the UX still require their own proof. Evidence identifies its bundles; changes to the lifecycle need to be revalidated.

The earlier native proofs cover `SessionStart`, `PostToolUse` and `Stop`. The new `PreToolUse` has protocol tests and requires separate confirmation in the host; the coverage of those trials is not attributed to it.

Trusting the hook and accepting the contract are distinct decisions. The plugin must not grant its own acceptance. The handler's native hash does not automatically guarantee the bytes of every script it calls.

In Claude Code 2.1.309, headless sessions with a real model and the plugin loaded through `--plugin-dir` dispatched the four events; `PreToolUse` denied a code edit before acceptance and `Stop` returned control ([evidence](../research/claude/README.md)). Claude Code loads `hooks/hooks.json` from the plugin root even when the manifest points to another file, which is why the Claude manifest does not declare a second path. The trust dialog, interactive UX, installation through a marketplace and coexistence with the user's hooks remain untested; equivalence with Codex is not assumed.

## Review in the browser

The local interface shows full text, classifications, exemption justifications, requirements, scenarios, hashes and diffs against the last accepted snapshot. The decision requires a declared identifier and explicit confirmation. A proposal changed during the review must be reloaded.

Loopback and a session token protect the local interaction; they do not authenticate a person against another process of the same user. The authority outside the project may remain accessible to the agent through system permissions. This flow does not declare `human_authenticated`.

The full experience of a person reading, deciding and resuming the agent remains a necessary validation. HTTP tests of the interface do not demonstrate that someone read the contract.

## CI and protected boundary

The example workflow calls `specmd verify --require-real` for activated projects, using external trust provisioned by the operator. This path requires a valid approval for the snapshot, a fresh real run and strict traceability. Cache and mock are not enough.

The command does not constitute a secure deployment by itself. The agent or the reviewed change must not be able to control the trusted verifier, the key, the trust store or the rules that make the check mandatory. Branch protection and operational separation need review on the chosen platform.

See [Architecture](architecture.md), Acceptance and trust (removed by [D-021](decisions.md)), [Requirements](requirements.md) and [Validation plan](validation-plan.md).
