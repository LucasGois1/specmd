---
specmd:
  schema: 1
  id: SMD-DOC-EXPERIMENTAL-CODEX
  kind: mixed
---

# Experimental integration with Codex

> **Historical, predating [D-021](decisions.md).** This document describes the design with signed acceptance, authority, trust and implementation blocking, removed on 23/10/2026. For the current product, see [product](product.md) and [implementation status](implementation-status.md).

The adapter presents the state of the SpecMD flow to the agent: documentation, review of a version, traceability and run evidence. The [quickstart](quickstart.md) lets you try this cycle first through the CLI and the browser.

The project remains experimental. `demo_passed` represents a local demonstration, without proving an isolated human authority. The `passed` path requires a fresh real run, external trust provisioned as protected and a strict policy. Deploying this separation depends on the operator and the environment; see Acceptance and trust (removed by [D-021](decisions.md)).

## Integration evidence

Codex CLI `0.163.0` recognized, installed and enabled `specmd@specmd-local`. Trials on the real executable observed `SessionStart`, `PostToolUse` and `Stop`, including a change made by a tool and the update of the observed hash. The backend provided simulated deterministic HTTP responses. This proves dispatch and host control paths; it does not demonstrate reasoning or compliance with the instructions by an LLM.

The attempts with the configured model service returned `401`. The initial read-only filesystem block was overcome when the environment became writable. Human granting of trust through the `/hooks` interface remains an experience to be validated separately.

The evidence in [research/codex](../research/codex/README.md) identifies sources and bundles. Later changes to the lifecycle require new validation; the success of an old bundle does not automatically prove the current revision. See the [implementation status](implementation-status.md).

## Prepare and install

Use a clone of the desired revision, Python 3.11 or later and a Codex installation with writable user state. From the clone:

```sh
SPECMD_SOURCE="$PWD"
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" "$SPECMD_SOURCE/scripts/build_codex_plugin.py"
codex plugin marketplace add "$SPECMD_SOURCE"
codex plugin add specmd@specmd-local
```

The builder generates `dist/codex-plugin` from an allowlist. The original virtualenv provides the dependencies and is not copied into the package. Start Codex from a process that inherits `SPECMD_PYTHON`. Marketplace and installation persist Codex state. The bundle manifest identifies content, without granting trust.

After changing the source, generate the bundle again and update the installation through the host's flow. The installed copy does not automatically follow the clone.

## Review the handlers

Open Codex in the test project and use `/hooks`. Check package, command, interpreter and events before granting trust through the normal interface. Start a new session to also observe the start event.

| Event | Action |
| --- | --- |
| `SessionStart` | Query the state and provide context about gaps. |
| `PreToolUse` | Check authorization before the tools covered by the policy. |
| `PostToolUse` | Reassess the project and update the observed state after tools. |
| `Stop` | Check completion and translate the result into the host's protocol. |

`PreToolUse` was added in this evolution and has protocol tests; it is not part of the earlier native proofs of the three events. The reach of the policy and its effects on the current host need their own validation.

While acceptance is missing, the local policy allows reads and recognized documentation changes, and denies code changes and unknown commands. Combined shells are conservatively refused. Open the review in a human terminal following the quickstart; do not rely on the agent launching review commands while the block is active. A valid acceptance returns the tools to the host's normal policy. This heuristic can produce undue blocks and needs to be evaluated in your flow.

Trusting the handler authorizes running the integration. Accepting a SpecMD proposal agrees to a version of the contract. These decisions have different records and scopes. The agent must wait for the user's contractual decision.

The native trust hash that was researched identifies the normalized declaration of the handler, including the command; it does not necessarily cover the bytes of every script called. Package integrity, authority and CI require additional controls.

## Project and states

The opt-in is `specmd.toml`. Schema 1 keeps the initial scanner and does not offer a completion path. Schema 2 configures identity, runners, traceability and evidence. Use the disposable project from the [quickstart](quickstart.md) before configuring an existing project.

The Markdown contains canonical requirements and Gherkin. The Python run receives in-memory blocks and loads real steps; it does not create `.feature`. Informational classifications and justifications are also part of the snapshot subject to review. New, changed or removed Markdown requires reconciling that version.

The hook queries the state; the CLI provides the explicit operations of preparing a review, opening the interface, running and auditing. The package does not silently create a protected authority.

In `waiting_human_review`, the adapter returns control for the user's decision. For fixable gaps, the first `Stop` may produce block feedback; if the host comes back with `stop_hook_active: true`, the adapter returns control to avoid endless repetition. The gap remains.

`.specmd/local/status.json` is a rebuildable observation. Codex's `turn.completed` indicates the end of the turn; it does not replace SpecMD's `status`, `may_complete`, `verification_mode` and `assurance`. A `demo_passed` result must be presented as a demonstration. Protected integration uses `verify --require-real` with external authority and a fresh run.

Hooks do not prevent all the work of an agent that can also edit scripts, configuration or authority. CI needs to run trusted verification code, with rules protected by the operator. The existence of a workflow in the repository does not prove that deployment.

## Documentation scenarios

The IDs below preserve the earlier guide. These specific blocks have no human acceptance nor a demonstrated link to executed steps.

### SMD-PREFLIGHT-REQ-001 — Identify changes to the contract

A new observation identifies changes in the bytes. The earlier acceptance does not automatically authorize another version.

```gherkin
@SMD-PREFLIGHT-REQ-001
Feature: Document identity
  @SMD-PREFLIGHT-SCN-001
  Scenario: Change a previously accepted document
    Given a project with an accepted contract for an identified version
    When the bytes of that contract are changed
    Then the observed contractual version should change
    And the new version should await review before completion
```

### SMD-PREFLIGHT-REQ-002 — Separate valid structure from approval

Declared classification and valid syntax do not record human agreement.

```gherkin
@SMD-PREFLIGHT-REQ-002
Feature: Classification review
  @SMD-PREFLIGHT-SCN-002
  Scenario: Inspect a reference not yet accepted
    Given a project with a valid informational document and justification
    And no valid decision about the proposed version
    When the document structure is inspected
    Then the flow should await human review
    And completion should remain unauthorized
```

### SMD-PREFLIGHT-REQ-003 — Return control without erasing gaps

Returning to the user allows the gap to be resolved, without granting approval.

```gherkin
@SMD-PREFLIGHT-REQ-003
Feature: Stop control
  @SMD-PREFLIGHT-SCN-003
  Scenario: Keep a block after feedback
    Given a document with gaps and a first block response
    When the host repeats the stop with the stop hook already active
    Then the adapter should return control to the user
    And the task should remain pending
```
