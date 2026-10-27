---
specmd:
  schema: 1
  id: SMD-DOC-HANDOFF-LOCAL-AGENT
  kind: reference
  exemption_reason: "Continuation context, earlier decisions, evidence and validation walkthrough; does not replace the canonical requirements or grant acceptance."
---

# Handoff — SpecMD for the local agent

> **Historical, predating [D-021](docs/decisions.md).** This document describes the design with signed acceptance, authority, trust and implementation blocking, removed on 23/10/2026. For the current product, see [product](docs/product.md) and [implementation status](docs/implementation-status.md).

Document prepared at Lucas's request to transfer the context of the discovery, research and implementation to the agent that will work on his computer. Access to the original conversation is not required.

**Reference date of this handoff:** 23/10/2026. Public repository: [LucasGois1/specmd](https://github.com/LucasGois1/specmd). The experimental implementation **0.2.0** was merged into `main` by [PR #1](https://github.com/LucasGois1/specmd/pull/1), in merge `352c8323f701cefaca2fca4f8d42952e2de07fbd`. The code verified before the merge is at `e24142308b2e98904eff062012918fb89060d065`; the merge's file tree was checked and was identical to that commit's.

The current result is an experimental cycle usable for testing the experience. It is not a production product with authenticated human identity, permission isolation and demonstrated usefulness. Lucas's request was to implement the flow for him to try out, accepting tests with simulated agents when a real session with a model was not available.

## 1. Where to start

Read [AGENTS.md](AGENTS.md), this handoff, the [implementation status](docs/implementation-status.md) and the [quickstart guide](docs/quickstart.md). Then consult the [requirements with scenarios](docs/requirements.md) and the documents specific to the area you will work on.

The product and planning documents preserve earlier intentions and proposals. Historical questions in those texts do not mean that the whole implementation is still pending. To assert a current capability, check the corresponding code, version and evidence. Do not redo all the research or reimplement the core before exercising what exists.

The next useful delivery is a local session with Lucas: install, review a contract, accept or reject a version, run scenarios, provoke changes and observe how the agent responds. In parallel, the pending SonarQube issues need to be triaged. The next delivery does not need to be a bigger platform.

## 2. The problem behind the idea

Lucas develops software with AI agents. Models and tools have improved, but keeping intent, documentation, implementation and tests aligned remains hard. Putting specs in the repository brings the context closer to the code and makes discovery easier via `rg`, text search and navigation. That does not guarantee that the agent finds, reads or correctly interprets each obligation.

We discussed two directions of misalignment:

1. **Omission or incorrect interpretation:** a requirement exists, but the agent forgets a condition or implements a different interpretation.
2. **Invented behavior:** the agent creates a rule nobody requested, writes tests that protect it and delivers green code. The developer later finds a restriction that was not agreed anywhere.

Example discussed: the user asks for sign-up by email; the agent decides to accept only corporate emails. Tests for that restriction do not turn it into a legitimate product decision. Writing the documentation afterwards does not authorize the rule either: the proposal must be presented and an applicable human decision obtained.

The central hypothesis is to improve the experience with agents by making explicit the relationship between **recognized intent → accepted contract → implemented behavior → current evidence**. The goal is to reduce errors and review effort, with interruptions that are understandable and recoverable.

We are not claiming that all software documents are Markdown or that executable documentation was invented here. Markdown was chosen as the authoring format and canonical source of this project.

## 3. Directions Lucas set

| Direction | Reason and consequence |
| --- | --- |
| Canonical Markdown | Explanations, requirements and Gherkin scenarios live in the same document. Avoid a second editable specification that could diverge. |
| No dependency on `.feature` | Running must not require `.feature` files maintained separately, nor their mandatory temporary generation. The engines receive content in memory. |
| Verifiable scenarios | A behavioral requirement must not be considered incorporated just because it was described. It must be linked to verification run against the implementation. |
| Traceability in both directions | Expose requirements without evidence and behavior changes without a recognized origin. |
| Explicit human acceptance | Applies both to specs written together with the agent and to changes it proposes proactively during development. |
| Acceptance per version | A deterministic hash identifies the reviewed content. Modifying a contract or scenario requires a new applicable decision. |
| Preserve acceptance when only the code changes | New attempts to implement the same intent require renewing evidence, not asking for product agreement repeatedly. |
| Avoid self-approval | The agent may propose and implement; the effective acceptance authority must stay outside its permissions. A hash alone does not solve this. |
| Document classification | Behavioral Markdown requires scenarios; informational content may be exempted, with justification and review. There are mixed documents. |
| Inventory and monitoring | Discover all of the project's own Markdown files, including new ones not tracked by Git. An exemption does not make the document disappear from the inventory. |
| Incremental performance | Avoid repeated work when possible, with correct invalidation. Cache is derived and never grants acceptance. |
| Hooks for agents | Use events actually supported by Codex and Claude Code for feedback and blocks where possible. |
| Legitimate human wait | Handing control back for a decision is not the same as completing the task. Avoid `Stop` loops. |
| Audit | Show what changed, who proposed and who decided, distinguishing declared Git authorship from authenticated human identity. |
| Java, Python and Go | The three languages are part of the initial execution scope; each integration needs its own proof. |

The chosen name was **SpecMD**, with repository and CLI `specmd`. Global brand/package availability and the license were not resolved. Do not invent a license decision.

These directions are conversation context. They do not constitute signed acceptance receipts for the files of this repository. A PR merge and authorization to write documentation do not replace those receipts either.

## 4. What we investigated and what the research resolved

### Markdown with Gherkin and overlap with other tools

Lucas asked whether the project already existed under another name and asked for a reflection before proceeding. The research is in [positioning.md](docs/positioning.md), with sources pinned by version/commit.

| Precedent | What we learned | Consequence for SpecMD |
| --- | --- | --- |
| Official Markdown with Gherkin, MDG | Executable Markdown documentation already exists. The syntax uses headings/lists and the `.feature.md` convention. | Do not claim novelty just for combining Markdown and execution. `.feature.md` is still Markdown; its name alone does not violate the restriction against a parallel `.feature`. |
| Cucumber.js with MDG | The baseline ran MDG on `.feature.md` and on explicit `.md`. Plain Markdown with a `gherkin` fence ended with exit 0 and zero scenarios. | Syntax, discovery, parsing and effective execution are different checks. Do not assume native support for SpecMD's blocks. |
| Tracey | Traceability of requirements, implementation/tests, stale references and integration with agents have a close precedent. | Evaluate reuse before creating another tracking system. |
| Gauge and Concordion | Executable examples and specifications in documents also came earlier. | Changing the authoring syntax does not demonstrate value on its own. |
| Spec Kit and OpenSpec | Proposal, review and spec-driven implementation, plus extensions, already cover parts of the flow. | Compare complete flows and well-configured compositions. |
| GitHub reviews and CI | Authenticated reviews, approval invalidation and required checks can provide important parts of the authority and the gate. | Reuse existing mechanisms when they deliver the needed separation of permissions. |
| spec-gates and other extensions | There is overlap with executable Markdown, hashes, attestations and agent/Git/CI gates. | Secondary engineering reference; do not assume maturity or incompatibility without testing. |

**Important correction:** Tracey is implemented in Rust, but it is not specific to analyzing only Rust. The language registry in the consulted snapshot includes Java, Go and Python. The README omitted Python, although the source included it. It was an inspection of analysis/traceability support; it was not proof of BDD execution nor of functional parity across languages.

Lucas questioned the reliability of spec-gates because it had few stars at the time. The appropriate conclusion was not to use it as a reference of proven maturity. Star count does not demonstrate quality, reliability or real adoption; do not repeat an old count as current fact.

**Positioning conclusion:** there is substantial overlap. We did not demonstrate exclusivity, superiority, or that no existing tool addresses the problem. Nor did we run a composition that proves everything is already solved. The candidate value is the integrated experience of preserving intent during the agent's work. That remains a hypothesis to measure.

If a small integration on top of existing tools does the job at equal or lower cost, SpecMD can become a plugin/preset. There is no need to justify an independent platform at any cost.

### How to run without `.feature`

We did not find, nor assume, a universal CLI argument that accepts the whole scenario text in every ecosystem. We reused the existing engines and their programmatic entry points.

| Language | Path exercised | Current limits |
| --- | --- | --- |
| Python | Markdown extraction → `behave.parser.parse_feature` → `ModelRunner`, in a subprocess, with real steps. | Behave is not official Cucumber. The worker does not load the project's `environment.py`, Behave settings or filters. |
| Java | In-memory Gherkin via `Resource`/`FeatureParser` and `Runtime.withFeatureSupplier`, with Cucumber-JVM glue. | A public core API does not mean a stable extension contract. The current bridge supports simple scenarios and Background; it rejects Rule/Outline. |
| Go | `godog.Options.FeatureContents`, with the project's step initializer. | Directory/CLI discovery is not equivalent to in-memory input. The current bridge supports simple scenarios and Background; it rejects Rule/Outline. |

The schema2 scanner and the Python runner support Rule and Scenario Outline instances. The scanner accepting a structure does not require every engine to support it. Concrete example IDs use `<scenario-ID>:row:<group>:<line>`.

The steps call the application code and make assertions; collecting Gherkin does not by itself produce adequate tests. A runner with exit 0, zero scenarios or dry-run does not grant the OK. The Java research even observed dry-run with `PASSED` events without any call to the application: that is a deliberate negative case of the gate.

Details and versions are in [runner-feasibility.md](docs/runner-feasibility.md), [research](research/README.md) and [adapters](adapters/README.md).

## 5. What exists in the code now

| Area | File/entry point | Current responsibility |
| --- | --- | --- |
| CLI | [cli.py](src/specmd/cli.py) | `init`, `demo`, `inventory`, `review`, `run`, `check`, `status`, `audit`, `verify`, hook adapters. |
| Configuration | [config.py](src/specmd/config.py) | Strict reading/validation of `specmd.toml`; legacy schema1 and schema2 for the full flow. |
| Inventory and parsing | [core.py](src/specmd/core.py) | Markdown, frontmatter, hashes, IDs, requirements/scenarios, origin, validations and in-memory extraction. |
| Review cycle and evidence | [workflow.py](src/specmd/workflow.py) | Proposal, applicable decision, traceability, code snapshot, run, invalidation, completion and audit. |
| Signatures and trust | authority.py (removed by [D-021](docs/decisions.md)) | Ed25519, key authorization per context, external current decision, rejection/revocation and repository identity. |
| Local review | review_server.py (removed by [D-021](docs/decisions.md)) | Loopback HTTP, full text/verified diff, configuration/links, accept/reject and refusal of an obsolete version. |
| Execution | [runner.py](src/specmd/runner.py), [behave_worker.py](src/specmd/behave_worker.py) | Subprocesses, JSON protocol, exact expected set, effective steps, timeout and Python worker. |
| Native bridges | [Java](adapters/java/README.md), [Go](adapters/go/README.md) | Code and examples to integrate the applications' real steps into these engines. |
| Codex and Claude | [codex.py](src/specmd/codex.py), [claude.py](src/specmd/claude.py) | Translation of states into the hosts' hook protocol. |
| Pre-implementation | pretool.py (removed by [D-021](docs/decisions.md)) | Conservative local policy to allow reads/docs and deny implementation actions while acceptance is missing. |
| Demonstration | [demo.py](src/specmd/demo.py) | Disposable cart project, two requirements/scenarios, implementation, steps and external demonstration authority. Does not automatically accept the contract. |
| Bundle | [build_codex_plugin.py](scripts/build_codex_plugin.py) | Generates the package from an allowlist, with manifests/hooks/bootstrap and Python modules. |
| Tests and reports | [test_local.py](scripts/test_local.py), [tests](tests), [research/workflow](research/workflow/README.md) | Reproducible local validation and explicit scope of the evidence. |
| CI | [specmd.yml](.github/workflows/specmd.yml) | Python suite, real Java/Go bridges and contract verification conditioned on the opt-in at the root. |

### Inventory, classification and links

- Discovers `.md` and `.markdown`, including files not yet tracked by Git. Does not use `.gitignore` as an automatic contractual exemption.
- There are fixed prunings of dependency directories, caches, `.git`, `.specmd`, builds etc. These are implementation choices to review, not an already validated universal scope policy.
- Frontmatter uses `specmd.schema: 1`, ID and `kind: behavioral|reference|mixed`. That schema is not the same number as the `specmd.toml` schema.
- `reference` requires a justification. A reference with explicit requirements or executable Gherkin produces a classification conflict. This does not detect every obligation written in prose.
- SHA-256 uses exact bytes, including line endings. The manifest incorporates paths and the configuration hash; the workflow also binds the traceability map.
- `.specmd/traceability.json` links files to requirement/scenario IDs. Strict policy requires links for the recognized source/test files. This makes the declared origin reviewable, without proving semantic equivalence.
- Changed classification and links become part of the new identity subject to review. They are not a way for the agent to exempt itself.
- The current cache is **advisory** and the source is still reanalyzed. Do not announce that the incremental performance gain has already been delivered.

### Acceptance, context and audit

- The review shows the complete Markdown files, diffs, classifications, justifications, configuration and links. The diff baseline is validated by proposal/receipt and external trust; it does not depend only on the local “last acceptance” cache.
- Ed25519 binds decision, project/repository, hash/manifest, proposal, declared reviewer and moment. Signing does not automatically authenticate a person.
- The trust store is external to the project. `latest_decisions` records the current decision; rejecting a version invalidates the previous acceptance of that proposal. Keys can be revoked.
- The optional `repository_id` provides a portable logical identity (`repo:<repository_id>`). `workspace_root` is the physical root used to check local boundaries. Without a logical identity, the fallback is the absolute path of the checkout, which is unsuitable for freely carrying receipts between machines.
- A Git name or a name typed into the form is a declaration. The system returns `human_authenticated: false`; no production human login/OAuth service is implemented.
- An audit kept in the repository can be erased by whoever controls the repository. Reliable preservation depends on an external record and an access policy.

### Artifacts and what can go into Git

| Path | Meaning |
| --- | --- |
| `specmd.toml` | Opt-in, identity and configuration of the target project. |
| Project Markdown | Canonical source of the behavior and the scenarios. |
| `.specmd/traceability.json` | Declared links, part of the reviewable version. |
| `.specmd/reviews/*.json` | Proposals/snapshots, with no acceptance authority on their own. |
| `.specmd/approvals/*.json` | Signed receipts; valid only if verified by applicable external trust and the current decision. |
| `.specmd/local/` and `.specmd/cache/` | Rebuildable observed state, local evidence and cache; they should stay out of usual version control. |
| External authority directory | In the demo it contains the private key and the trust. Never version a private key or treat that location as isolated just because it is outside the clone. |

Do not carry keys, credentials, Codex configuration or fixture receipts from this environment to Lucas's computer.

## 6. How to interpret the states

| State | Interpretation |
| --- | --- |
| `inactive` | Project without opt-in. It is not a contractual OK. |
| `error` | The verification could not be determined, or there is invalid configuration/input. |
| `blocked` | Unsatisfactory structure, origin/links or run. |
| `waiting_human_review` | The current version requires an applicable decision. Hand control back to the human, without declaring completion. |
| `awaiting_evidence` | There is an applicable acceptance, but a current run is missing or the evidence became stale/expired. |
| `demo_passed` | The demonstration cycle satisfied its criteria; `may_complete: true` holds in this local context. |
| `passed` | Fresh real-run path, trust configured as protected and strict traceability. Presupposes a trusted deployment. |

Key points:

- A project `schema = 1` keeps the old preflight, without a completion path. `schema = 2` enables the integrated cycle.
- `demo_passed` uses `verification_mode: "demo"` and `assurance: "local_demo"`. It may have `test_mode: "real"`: real tests do not turn demonstration authority into authenticated human approval.
- A `mock` runner requires explicit opt-in and never satisfies `verify --require-real`.
- `verify` and `check --require-real` perform a new real verification. An old local JSON report does not grant a protected `passed` on its own.
- A `protected` field in the trust does not create operating-system isolation, human identity or branch protection. The verifier cannot prove that its own deployment assumptions are true.
- In gate commands, code 0 represents applicable success; 1 represents a gap/block and 2 an error/inactivity. Do not treat `inventory` or review preparation with exit 0 as approval.
- The host's `turn.completed` means the turn ended; it does not replace SpecMD's verdict.

## 7. What was actually validated

| Evidence | Recorded result | What it does not prove |
| --- | --- | --- |
| [Local suite](research/workflow/evidence/local-tests.json) | 187 tests passed, no skips. Includes real local HTTP, signatures and Python execution, plus mocks/fixtures. | It does not demonstrate that a person read/accepted the real contracts, nor that an LLM respected the hooks. |
| [Native integration](research/workflow/evidence/native-bridges.json) | Six cases with real engines: success, failing assertion and undefined step in Java and Go, via the core. | It is not a certification of every project, version or format of those languages. |
| Go tests | The bridge's `go test ./...` passed; the example build and the run through the core passed. | It does not measure product usefulness. |
| [Preflight in the bundle](research/workflow/evidence/bundle-preflight.json) | 11 compatibility cases checked. | Repeating the same cases in source/bundle does not create 22 independent product scenarios. |
| [Codex 0.2.0 installation](research/workflow/evidence/codex-installation.json) | Package installed in this environment and 21 files checked against the bundle. | This revision did not get a new complete native rehearsal of all hooks with a real model. |
| [Earlier Codex research](research/codex/README.md) | The real Codex 0.163.0 executable dispatched `SessionStart`, `PostToolUse` and `Stop` with a deterministic HTTP backend; a real tool changed a temporary contract. | A deterministic backend is not an LLM. Proof from an earlier revision does not automatically cover the current code. |
| Current `PreToolUse` and Claude | Policy/protocol and bootstrap tests. | Current native dispatch, Claude installation and the human experience still need a local rehearsal. |
| [PR #1 Actions](https://github.com/LucasGois1/specmd/actions/runs/39949649507) | Jobs `tests-and-contracts` and `native-bridges` passed. | The external authority step was `skipped`, because there was no `specmd.toml` at the root of SpecMD itself. |

The acceptance fixtures use identities such as a synthetic reviewer, in disposable temporary directories. They are authorized tests of the mechanism, not acceptances by Lucas. `scripts/test_local.py` explicitly records `real_llm_executed: false` and `human_review_performed: false`.

Three concrete regressions were found and fixed during the implementation:

1. Old Python bytecode, with a still-valid timestamp/size, could mask a changed source. The worker uses a new temporary cache prefix per run; `-B` alone would not prevent reading the old `.pyc`.
2. `fresh_evidence={}` could fall through to the cache and be interpreted as a fresh run. Selection now distinguishes `None` from invalid input, with validation of the report.
3. A valid documentation patch with an empty context line was denied by the pre-tool gate. The parser was fixed and gained a regression test.

Preserve these tests when refactoring.

### Known pending issue: SonarQube

PR #1 was merged at Lucas's request through the normal GitHub flow. At the merge check, the tests were green, but the SonarQube quality gate was failing. The merge work neither fixed nor waived it.

The local agent should check the current state and triage the findings, without confusing “test passed” with “the whole quality analysis passed”. Among the findings observed were research probe paths/outputs, installation/lock of Python dependencies, and HTTP on the loopback interface. Evaluate the flow and context of each one: do not declare them all false positives, nor change the architecture just to silence a rule. Do not mark issues as resolved without evidence.

[PR and discussions](https://github.com/LucasGois1/specmd/pull/1) · [SonarQube Cloud](https://sonarcloud.io/dashboard?id=LucasGois1_specmd)

## 8. This conversation's environment versus Lucas's computer

The Codex CLI mentioned earlier was installed/run **in this conversation's work environment**. That statement does not mean anything was installed on Lucas's personal computer.

In that environment, the real CLI was available. The session attempt with the configured model service failed with `401`, before completing the cycle with an LLM. That is why we used a deterministic backend and protocol simulations. The correct conclusion is not “we could not run the CLI”, but “we did not validate the experience with a real authenticated model in that environment”.

There was also a historical phase with a read-only Codex home, overcome when the environment became writable. Do not treat it as a block inherent to the product or to the local computer.

On Lucas's computer, check versions, authentication and existing capabilities. Do not assume Codex/Claude/Python/JDK/Go/Maven are installed, nor reuse paths such as `/workspace`, `/run/codex-environment/...` or temporary SDKs from the research. Do not remap `HOME`/`CODEX_HOME` to reproduce an installation; use the host's normal mechanisms and preserve the existing configuration.

## 9. Portable walkthrough to get started locally

The commands below assume a POSIX shell. Native Windows has not been verified yet. No model credential is needed for the automated tests and for the demo through the CLI/browser.

### Installation and regression

If there is no local clone yet:

```sh
git clone https://github.com/LucasGois1/specmd.git
cd specmd
git switch main
```

If it already exists, inspect its state and local changes before updating; do not overwrite existing work.

```sh
SPECMD_SOURCE="$PWD"
python3 -m venv "$SPECMD_SOURCE/.venv"
"$SPECMD_SOURCE/.venv/bin/python" -m pip install -e "$SPECMD_SOURCE"
export SPECMD_PYTHON="$SPECMD_SOURCE/.venv/bin/python"
"$SPECMD_PYTHON" -m specmd --version
"$SPECMD_PYTHON" scripts/test_local.py
```

Use Python 3.11 or later. The default report is `.specmd/local/test-report.json`, with no acceptance authority. The historical snapshot recorded 187 tests; the count may change in future revisions, so record the commit and the result actually obtained.

### Demo without automatic acceptance

Create new directories outside the clone. Example with a new temporary base:

```sh
SPECMD_DEMO_BASE="$(mktemp -d)"
SPECMD_DEMO_ROOT="$SPECMD_DEMO_BASE/cart"
SPECMD_DEMO_AUTHORITY="$SPECMD_DEMO_BASE/cart-authority"
"$SPECMD_PYTHON" -m specmd demo --dest "$SPECMD_DEMO_ROOT"
export SPECMD_TRUST_STORE="$SPECMD_DEMO_AUTHORITY/trust.json"
"$SPECMD_PYTHON" -m specmd check --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd review --root "$SPECMD_DEMO_ROOT" --prepare
```

Before accepting, `check` must stay pending and return a non-zero code. The demo refuses to overwrite non-empty directories or existing keys. Do not delete data to force a repeat: choose new directories.

Open the review for Lucas:

```sh
"$SPECMD_PYTHON" -m specmd review --root "$SPECMD_DEMO_ROOT" \
  --authority "$SPECMD_DEMO_AUTHORITY" --trust "$SPECMD_TRUST_STORE"
```

The server listens on loopback on a random port. `--no-open` lets you open the URL manually. The session token is in the URL fragment and is used by the browser; do not publish that session link as shared evidence.

**Accepting or rejecting is Lucas's action.** The agent must not call the acceptance API or the signing function on his behalf to complete the human test. Do not change the trust to `protected` as a shortcut. The synthetic tests that do this in fixtures are not a recipe for production use.

After the decision, stop the server with Ctrl+C when appropriate. If there was a rejection, adjust the proposal and return to the review; the task remains pending. After an applicable acceptance, run:

```sh
"$SPECMD_PYTHON" -m specmd run --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd check --root "$SPECMD_DEMO_ROOT"
"$SPECMD_PYTHON" -m specmd audit --root "$SPECMD_DEMO_ROOT"
```

The expected local positive result is `demo_passed`, with real application tests. Confirm that `verify --require-real` still rejects the demonstration authority.

Do not run `specmd init` at the root of this repository just to reproduce the demo: the root contains documentation and research fixtures, and has not yet received a contractual opt-in for all that content. Use a separate target project.

### Install and test the Codex plugin

At the root of the clone, examine the local CLI and whether a marketplace with the same name exists before changing an installation:

```sh
codex --version
codex plugin --help
codex plugin marketplace list --json
"$SPECMD_PYTHON" "$SPECMD_SOURCE/scripts/build_codex_plugin.py"
codex plugin marketplace add "$SPECMD_SOURCE"
codex plugin add specmd@specmd-local
```

Start Codex in the demo project from a terminal that inherits an absolute `SPECMD_PYTHON` and `SPECMD_TRUST_STORE`. The normal way to start, after setting the variables, is:

```sh
cd "$SPECMD_DEMO_ROOT"
codex
```

Lucas must review the handlers in `/hooks` and decide whether to trust them through the normal interface. Trusting a hook and accepting a contract are distinct decisions. Do not fabricate that human action, disable trust or use bypass flags to declare the UX validated.

The marketplace points to `dist/codex-plugin`; that artifact is ignored by Git and needs a local build. Installing directly from a remote without the artifact is not a resolved distribution flow. Codex copies the installed package: edits in the clone do not automatically update the cache. Rebuilding and updating/reinstalling must use the host's flow.

The bundle does not contain `.venv`, dependencies, `.git`, caches or the Java/Go builds. The selected virtualenv provides the dependencies. The Python worker is the file next to the runner of the same copy, to avoid mixing code from one bundle with another editable checkout.

Both manifests use a single `hooks/hooks.json` with `SessionStart`, `PreToolUse`, `PostToolUse` and `Stop`; the command resolves the root via `PLUGIN_ROOT` (Codex) or `CLAUDE_PLUGIN_ROOT` (Claude Code), because Claude Code also loads that file by default. POSIX shell hooks and specific host versions need their own validation. See [experimental-codex.md](docs/experimental-codex.md) and [integrations.md](docs/integrations.md).

While acceptance is missing, `PreToolUse` allows recognized reads/docs and denies implementation and unknown/complex shells. Because it is conservative, it may block legitimate commands, including the review launcher. Open the review in a human terminal; record that friction instead of silencing the gate. After a valid acceptance, the tools return to the host's normal policy.

### Validate Java, Go and Claude

For Java: JDK 21 with a compiler and Maven; for Go: SDK 1.25.0 in the current experiment. Follow [adapters/java](adapters/java/README.md) and [adapters/go](adapters/go/README.md), compiling and registering the application's real steps. The Go module uses an example path, with no stabilized public distribution. There are no universal, automatically generated steps.

After the builds, the [probe](research/workflow/probe_bridges.py) reproduces the positive and negative cases through the core. Each runner must receive its own set of documents; assigning the same scenario to two runners is an error.

Claude has a manifest and an adapter. After this handoff, headless Claude Code 2.1.309 sessions with a real model exercised the native dispatch ([research/claude](research/claude/README.md)); marketplace installation, trust and the interactive UX have not been exercised yet. Check the version and documentation of the local CLI before claiming support. Do not infer operational equivalence just because the JSON formats in the tests look similar.

## 10. Scenarios we want to validate with Lucas

This matrix organizes follow-up rehearsals. It does not replace the canonical scenarios in [requirements.md](docs/requirements.md) and does not declare that all the behaviors below have already been demonstrated with a human and a real LLM.

### Contract, documents and resumption

| Case | Test action | What to observe |
| --- | --- | --- |
| H-01 — First contact | Start without acceptance, ask the agent to implement the demo contract. | Clear gap, editable documents, dependent implementation blocked and no claim of completion. |
| H-02 — Reading and acceptance | Lucas reads the text/diff, accepts and resumes the agent. | The decision applies to the version presented; the scenarios run; the final message identifies demonstration mode. |
| H-03 — Rejection | Lucas rejects the proposal or asks for an adjustment. | The task remains pending; the agent discusses the doubt and does not turn rejection into agreement. |
| H-04 — Contract changed | After acceptance, the agent adds a scenario or changes a normative sentence. | New hash and new review; the previous acceptance does not release the change. |
| H-05 — Version changed on screen | Modify the document while the previous review is open. | Stale acceptance refused, with an instruction to reload/review. |
| H-06 — Code/test only | Change the implementation or a step while keeping the contract. | Acceptance preserved when applicable; old evidence invalidated and a new run required. |
| H-07 — New document | Add unclassified Markdown, including untracked files. | It enters the inventory and exposes the gap; it does not disappear for not being in Git. |
| H-08 — No Gherkin | Propose a behavioral document without scenarios. | Require discussion/formulation of the examples; do not silently invent product decisions. |
| H-09 — Legitimate reference | Add an editor guide with no software behavior. | Propose a justified exemption, obtain a decision on the version and keep monitoring it. |
| H-10 — Reference that gains an obligation | Add a product rule to an exempted document. | The change requires review; a `reference` declaration is not semantic proof that there are no requirements. |
| H-11 — Mixed/removal/rename | Review a mixed document, remove or rename a contract. | Show the changes and the impact on identity/paths, avoiding silent reuse of the acceptance. |
| H-12 — Continuity | End and reopen a session with a gap; try a subagent when relevant. | State rebuilt, waiting distinct from completion and no `Stop` loop. |

### Adequacy of behavior and verification

| Case | Test action | What to observe |
| --- | --- | --- |
| H-13 — Omission | Request a change with two conditions and induce implementation of only one. | Check whether the gap reaches the review and the evidence. An incomplete contract can also fail to represent the intent. |
| H-14 — Invented rule | Ask for sign-up by email and observe whether the agent introduces “corporate only”, writes green tests and tries to document it afterwards. | Expose the restriction as a proposal, allow human rejection and do not use green tests as authorization. If there is no documentation change, the current core does not guarantee detection of the hidden semantics. |
| H-15 — Test without origin | Create a new test file for undocumented behavior. | Strict policy flags the missing link. If the agent links the file to an existing broad requirement, the link alone does not demonstrate legitimacy: review the behavior. |
| H-16 — Weak assertion | Remove an assertion or let a step pass without verifying an effect. | Recognize the engine's limit. Measure the need for additional review/mutation; do not announce automatic semantic protection. |
| H-17 — Incomplete run | Produce zero scenarios, an empty filter, omission, duplication, an undefined step, skipped/pending or dry-run. | None of these results satisfies the expected behavioral obligations. |
| H-18 — Real failure | Break the sum implementation. | Failing assertion and completion blocked; a favorable exit code on its own is not enough. |
| H-19 — Origin and examples | Exercise multiple blocks, origin lines and Outline/Rule in Python. | The result matches the expected instances; Java/Go reject what they do not support yet. |
| H-20 — Old/unstable evidence | Change code/configuration after or during the run; expire evidence. | An old result does not authorize the new snapshot; a change during the run discards the result. |
| H-21 — Infrastructure | Missing runner, timeout, invalid JSON output or unavailable dependency. | Explain the failure without fabricating implementation, success or approval. |

### Trust, integration and usability

| Case | Test action | What to observe |
| --- | --- | --- |
| H-22 — Cache/local state | Delete the cache or change local observation/evidence. | Rebuilding and validation; no local JSON grants protected completion. Demo mode is not a boundary against a malicious agent with the same identity. |
| H-23 — Invalid receipt | Change the signature/hash, copy a receipt to another project/repository, use a revoked key or replay after rejection. | Verification refuses inapplicable/stale decisions. |
| H-24 — Another checkout | Reproduce the logical identity at a different CI path. | Portable `repository_id` and physical root kept separate, without accepting trust inside the checkout. |
| H-25 — Removal of the opt-in | Remove the configuration after an activation observation. | The hook preserves the gap on the observed path. This is no guarantee against deleting configuration, state and integration under the same permission. |
| H-26 — Native hooks | Exercise the four current events in Codex and, later, Claude. | Real payloads/effects, human trust, event order, resumption and no false completion. |
| H-27 — Excessive blocking | Try a legitimate read or documentation edit and open a review. | Measure false blocks, clarity of the reason and the recovery path; do not disable the policy to declare success. |
| H-28 — Independent CI | Ignore local hooks and try to merge an incompatible change in a prepared environment. | Only a truly protected gate/verifier can demonstrate blocking outside the agent. The current demo does not prove this case. |
| H-29 — Information only | Task/project with a legitimately exempted reference and no applicable BDD obligations. | Decide the applicability policy before implementing. The current runner rejects zero scenarios; there is no general positive path to complete a purely informational task. |
| H-30 — Parallel work and cost | Two agents/documents, tests that generate artifacts and a larger repository. | Concurrent reviews, task scope versus the whole project, false stale results and reanalysis cost still need investigation. |

Record what happens in the software, what the agent tells the user and what Lucas understood. A technically correct refusal that is impossible to resolve through the UX is still a product problem.

## 11. Gaps that must not disappear in the next summary

1. **Production authentication and human isolation:** no login/OAuth/protected service has been delivered. An external local key may remain accessible to the same user as the agent. Do not call this “anti-bypass solved”.
2. **Protected enforcement:** the YAML, the trust and the verifier must not be modifiable by the agent itself or by the PR under review. Arbitrarily running the PR's verifier does not establish the independent authority we want. Branch protection and the expected origin of the checks still depend on deployment.
3. **Current native experience:** installing a plugin, trusting its handler and observing four events in a real session are different steps. The 0.2.0 revision still needs that complete local proof with Lucas.
4. **Semantic equivalence:** a map by file/IDs does not prove that every implemented rule was requested, nor that a broad requirement justifies every restriction. AI can help flag suspicions, without authorizing requirements by inference.
5. **Assertion quality:** a bridge or step can lie or be weak. Tests run code with the process's permissions; a subprocess is not a sandbox for hostile code.
6. **Applicability and granularity:** the current flow is conservative about the project and its inventory. Per-task scope, backlog, unaffected obligations, references and approval by subset are not stabilized.
7. **Performance:** the advisory cache does not avoid reparsing; broad snapshots may be costly or flag changes in artifacts. Exclusions, dependencies and incremental invalidation need data and a reliable policy.
8. **Compatibility/distribution:** Java/Go have a grammar subset and their own builds and steps; Claude/Windows and remote installation of the bundle still have limits. Do not announce universal support.
9. **Quality/security:** the SonarQube quality gate failing at merge, the dependencies/lock and the findings need real triage. The existing tests do not replace that step.
10. **Value validation:** there is no completed comparative pilot, measured quality gain, superiority over alternatives or commercial validation.

License, distribution, numeric goals for the pilot and the final choice of production authority also remain open. Do not create these decisions silently during a technical implementation.

### Opportunities after the core

The planning records possible expansions, with no commitment that all of them belong in the MVP:

- PR review organized by requirement: what changed in the contract, in the implementation and in the evidence of each obligation.
- Continuity across sessions and coordination of multiple agents over shared obligations.
- Impact analysis and stale references across documents, modules and tests.
- Review of assertion strength and mutation tests targeted at the scenarios.
- Turning incidents into regression scenarios, with the rule's origin and justification.
- Adapters for API, architecture, accessibility and performance checks.
- Release readiness and relevant evidence after deploy.
- Comparison of agents/models by how well they meet the intent, human effort and cost.

Legacy adoption also needs to distinguish behavior that is merely observed from intent that was actually accepted. Generating documentation from existing tests can help with the inventory, but does not automatically legitimize every rule they preserve. Expansion should respond to problems from the pilot, without turning the backlog itself into a new implicit source of requirements.

## 12. Suggested order for continuing

1. **Recognize the local state:** commit, changes, versions, available authentication, existing configurations and the repository's current checks. Read the rules before changing code.
2. **Reproduce the baseline:** suite and isolated demo. Do not change expectations just to get green. Check the regressions mentioned above.
3. **Triage SonarQube:** distinguish material problems, hotspots and context-dependent alerts; fix/retest what is appropriate. Do not present the earlier merge as an endorsement of those findings.
4. **Rehearse with Lucas:** review/acceptance/rejection and documentation/code changes, then the current hooks in an authenticated Codex. Record blocks and messages. Extend to Claude without assuming compatibility.
5. **Resolve the smallest necessary trust boundary:** compare using GitHub reviews/CI with a custom authority. Demonstrate real separation of permissions before promising production protection.
6. **Compare usefulness:** repeat equivalent tasks against a strong baseline and shrink the project if the smaller integration does the job.
7. **Optimize/expand based on the results:** performance, per-task scope, assertions and additional runner features should respond to observed problems.

The user prefers concrete progress and gets frustrated by repeated, unnecessary confirmations. Do authorized reads, tests and reversible fixes autonomously. That does not give the agent authority to grant the human acceptance of the product itself: when a real decision is needed, explain the gap and hand control back to Lucas.

## 13. How to evaluate whether the idea is worth it

The pilot must compare SpecMD with **well-configured documentation/specs, execution, human review and CI**. When relevant, add existing SDD/traceability tools such as Tracey/Spec Kit/OpenSpec. Do not compare only against an agent with no documentation and no tests, nor build an artificially complex baseline to favor the proposal.

Use similar tasks and human evaluation independent of the gate report. Include a legitimate change, an omitted requirement, an extra rule, a weakened test, a reference that acquires an obligation and an environment failure. Define gain criteria and cost tolerance before analyzing results.

Measure at least:

- Deliveries that respect the intent, and divergences that make it to completion.
- Omissions/extra rules noticed by the human, even when docs/code/tests agree with each other.
- Active review time, number of interactions and rework.
- Correct and undue blocks, with their cause and how recovery happened.
- Cost of installation, documentation maintenance, execution and reanalysis.

Continuation criterion: reduce errors and/or effort at an acceptable cost compared with the strong baseline. If the alternatives or a small extension deliver the same result, reduce SpecMD to that integration. If the cost of classifying/re-approving exceeds the rework avoided, reassess the hypothesis. Lucas has not accepted any numeric goal yet.

## 14. Suggested record for the local rehearsals

Create your own evidence identified as a rehearsal, preferably in ignored local state or in a sanitized report. Do not overwrite historical reports to pretend they were run on the local machine.

| Field | What to record |
| --- | --- |
| Technical identity | Commit, SpecMD/host/language versions, system and commands. |
| Actors and mode | Real human or fixture; real LLM or simulated backend; demonstration trust or isolated deployment. |
| Case | Matrix ID, original intent and the change introduced. |
| Snapshot | Hash of the relevant contract, code/configuration and evidence. |
| Observation | SpecMD state, the agent's message and Lucas's reaction/understanding. |
| Evaluation | Expected/observed result, time, false block and remaining divergences. |
| Limit | What was not exercised or cannot be concluded from that rehearsal. |

Do not record tokens, private keys, unnecessary personal data or sensitive application content in the reports.

## 15. Prompt to hand to the local agent

Copy the text below into the new session, adjusting only the clone path when necessary:

> You are continuing the public project LucasGois1/specmd. Read AGENTS.md and HANDOFF.md in full, then docs/implementation-status.md and docs/quickstart.md. The problem is aligning human intent, accepted Markdown contract, implementation and evidence during development with agents. Requirements and Gherkin stay in the same Markdown; do not introduce a dependency on .feature files, including temporary ones. There is already an experimental 0.2.0 implementation merged into main, with Python/Java/Go runners and tests described in the handoff. Do not restart the research or claim that everything is in production. Check the local commit, tools and configuration, reproduce the suite and prepare a demo separate from the clone. I want to test the experience with you and review the contracts personally. Never issue acceptance on my behalf, copy fixture receipts or turn local_demo into a protected guarantee. Help me exercise review, rejection, contract/code changes, invented rules and the current hooks, recording real results and limits. Also check the pending SonarQube issues. Before expanding the solution, preserve the handoff's decisions and scenarios and compare the gain with well-configured existing tools. Proceed with the necessary reversible work; when it depends on a real human decision about the contract, show the version and the gap and hand control back to me.

## 16. References to go deeper without losing the thread

| Question | Document |
| --- | --- |
| Why does the project exist? | [Product](docs/product.md) and [decisions](docs/decisions.md). |
| Which obligations and scenarios were recorded? | [Requirements](docs/requirements.md). |
| How to write/classify contracts? | [Format](docs/format.md). |
| How do the cycle and trust work? | [Architecture](docs/architecture.md) and acceptance/trust (removed by [D-021](docs/decisions.md)). |
| Where is there current capability and where is there a proposal? | [Status](docs/implementation-status.md), code and evidence for the version. |
| How to install and rehearse? | [Quickstart](docs/quickstart.md), [Codex](docs/experimental-codex.md) and [integrations](docs/integrations.md). |
| Why not use `.feature`, and how were the engines tested? | [Feasibility](docs/runner-feasibility.md), [research](research/README.md) and [adapters](adapters/README.md). |
| What already exists in the ecosystem? | [Positioning](docs/positioning.md). |
| What remains to measure/deliver? | [Validation](docs/validation-plan.md), [roadmap](docs/roadmap.md) and the gaps in this handoff. |
| How do the index and the cache relate to approval? | [Indexing](docs/indexing.md). |

This handoff is a context transfer. The contract, its human review and the corresponding evidence remain distinct artifacts.
