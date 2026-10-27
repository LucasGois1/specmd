# Implementation plan

> **Historical, predates [D-021](decisions.md).** This document describes the design with signed acceptance, authority, trust and implementation blocking, removed on 23/10/2026. For the current product, see [product](product.md) and [implementation status](implementation-status.md).

> Reference planning. The [implementation status](implementation-status.md) describes the current experimental version; production criteria are not met merely because code or simulated tests exist.

This plan turns the [product proposal](product.md) and the [requirements](requirements.md) into verifiable deliverables. Behavior changes discovered during implementation must go back to the contract for review; the backlog must not become a second source of requirements.

## Boundary of the first product

The MVP must demonstrate a complete flow: discover Markdown, identify classification gaps, help the user formulate scenarios, obtain acceptance of a version, suspend dependent behavioral implementation while that acceptance is pending, run the scenarios directly from the Markdown, and prevent completion or integration when acceptances or valid evidence are missing. Initial support must cover at least Java, Python and Go, with dedicated execution adapters and verified limits. The actual ability to suspend local actions must be demonstrated on the chosen host or declared as a limitation; the protected integration block remains mandatory.

Markdown is the canonical source. The user does not maintain `.feature` files, and execution cannot require creating them as a mandatory intermediate step. Integration with a real runner must be demonstrated through in-memory parsing and adaptation. If the chosen runner requires `.feature` files, the spike must record that incompatibility and evaluate another mechanism, without silently relaxing the requirement.

The agent may propose contracts, scenarios and exemptions. The acceptance authority remains separate from the agent's credentials. Local hooks guide and control the flow according to the platform's actual capability; a protected check enforces the integration policy.

## Implemented experiment and next validation

The [runner research](runner-feasibility.md) produced initial evidence of execution in Java, Python and Go. The local flow now integrates contract, browser review, signed decision, run and hooks; `specmd demo` creates a shopping cart with two scenarios to experiment with. The automated tests use synthetic decisions identified as fixtures.

The experimental core uses Python and Behave, with Java/Cucumber-JVM and Go/Godog bridges. Codex is the first host exercised; Claude has an adapter and protocol tests. Human validation in the user's environment, isolated authenticated authority and the comparative pilot are still needed.

The demonstration must allow completing with an accepted contract and successfully run scenarios; requesting new acceptance after a contract change; invalidating pertinent evidence after a code change; and rejecting mandatory scenarios that are missing, filtered, undefined or skipped. It must also allow waiting for human review and resuming the work without declaring an undue completion. The protected check remains necessary to evaluate attempts to bypass the local controls.

Include a task in which the agent invents a rule, writes green tests and proposes documenting it later. Evaluate whether the review exposes that decision and lets the human reject it, without promising infallible automatic detection. Compare the tasks against well-configured human review and CI, measuring misalignments, review effort and undue blocks according to the [validation plan](validation-plan.md).

The automated experiment demonstrates joint operation with a simulated agent actor and real application tests. The [integration guide](experimental-codex.md) separates protocol, installation and execution with a real model. A CI template and the `verify --require-real` mode do not install permission boundaries, branch rules or an authenticated human identity. The implementation does not represent human acceptance of a new contract version, nor does it validate the product's usefulness.

## Milestones and dependencies

| Milestone | Objective | Dependencies | Verifiable output |
| --- | --- | --- | --- |
| R0 — Reuse and positioning | Map what MDG, SDD tools, traceability, reviews and existing gates already solve. | [Background research](positioning.md) and a comparable setup of the problem. | Overlap map and gap hypothesis; no in-house subsystem is presumed necessary. |
| M0 — Execution feasibility | Demonstrate real scenarios coming from Markdown in Java, Python and Go, without mandatory `.feature` files. | Selection of parser and runner candidates per language. | In each language: a scenario that passes, another that fails, an undefined step and correctly reported origin; an absence of scenarios does not get an OK. |
| M1 — Minimum technical decisions | Choose the core stack, the runners and the first agent environment, prioritizing reuse. | R0, M0 results and verification of platform capabilities. | Recorded decisions, versions pinned for the prototype, reused components and documented limitations. |
| M2 — Core and inventory | Produce a deterministic inventory and manifest of the in-scope documents. | M1 and initial discovery policy. | The same revision generates the same manifest; additions, changes, deletions and renames are identified. |
| M3 — Classification and review | Represent behavioral, informational, mixed and pending documents. | M2 and format proposal. | A new document and a changed document generate a gap; an exemption depends on valid acceptance of the version. |
| M4 — Authenticated acceptance | Bind a human decision to the reviewed content and scope. | M2, M3 and definition of the trusted authority. | The agent cannot issue a valid acceptance with its own permissions; changed content does not inherit the previous acceptance. |
| M5 — Extraction and execution | Integrate parsing, IDs, source map and the Java, Python and Go adapters demonstrated in M0. | M0, M1 and a format stabilized for the MVP. | Normalized per-scenario results point to document, block and requirement in all three languages; there is no `.feature` copy to maintain. |
| M6 — Evidence and completion decision | Relate accepted contract, executed code and current results. | M4 and M5. | An old result, a skipped scenario, a missing step or a pending contract prevent a valid completion according to the policy. |
| M7 — First adapter | Connect the core to a verified agent environment. | M6 and capability matrix of the chosen environment. | The flow allows human review and resumption, distinguishes waiting from completion and does not enter hook loops. |
| M8 — Protected integration | Enforce the same policy outside the agent's control. | M6 and definition of permissions in the Git/CI provider. | Ignoring local hooks does not allow integrating a revision that violates the protected gate. |
| M9 — Product pilot | Compare the flow with the current development process. | M7, M8 and an evaluation protocol defined in advance. | Data on incorrect completions, human review, undue blocks and the mechanism's cost. |

M4 and M5 can advance in parallel once the necessary format is agreed. M7 should only promise blocks that the environment actually offers. M8 may require infrastructure or configuration outside the repository; that dependency must be explicit in the pilot.

## Work for each milestone

### M0 — Technical spike that precedes committing to a stack

- Create a Markdown fixture with Gherkin and real step implementations in the candidate stack.
- Extract blocks with a Markdown parser, preserving positions in the original file.
- Interpret Gherkin and feed the execution mechanism in memory, using supported interfaces or explicitly taking on the cost of maintaining an adapter.
- Demonstrate positive, negative and undefined-step results, with correspondence between tags and origin.
- Verify that no `.feature` file is needed to configure or run the fixture.
- Record versions, APIs used, limitations and maintenance risk. Do not present this experiment as a complete integration with Claude Code or Codex.

### M2–M3 — Discovery and classification before expensive analysis

- Define an initial scope of the project's own documents and a protected policy for excluding dependencies and generated files.
- Include new documents not yet tracked by Git in local work.
- Compute hashes over well-defined content and generate the manifest with deterministic serialization.
- Keep the local index rebuildable and separate from acceptances.
- Record the proposed classification, the requirements and the known relations, without treating an AI suggestion as a human decision.
- Invalidate analyses affected by changes in content, context, policy, analyzer or shared references.
- Allow review by coherent set of changes, with access to the full content and the original diff.

### M4 — Approval of an identifiable version

- Choose an authenticated channel in which the agent can request, but not grant, acceptance.
- Associate the decision with the user's identity, repository, scope, reviewed hash, presented revision and the moment of the action.
- Define how to check validity and revocation, and which rule applies to re-presenting a previously accepted version.
- Protect the trusted authorities and the verification policy against changes made by the agent itself.
- Keep the acceptance of a previous version in the history without using it to authorize new content.
- Treat Gherkin exemptions as decisions subject to the same version binding.

### M5–M6 — Verification without a second documentary source

- Validate syntax, the identity of requirements and scenarios, and declared links.
- Distinguish an executable block from a syntax example according to the [proposed format](format.md).
- Relate results to the contract, code revision, step implementations, configuration and runner used.
- Expose scenarios that are not found, filtered, skipped, pending or without implementation. An absence of execution does not count as success.
- Invalidate pertinent evidence after changes to the code or to the test mechanism.
- Make visible contract and test changes that could weaken the obligation.
- Explain the reach of the evidence: running scenarios does not prove the completeness of the specification nor the quality of all assertions.

### M7–M8 — Integration with agents and policy enforcement

- Document the events actually available and their capabilities: observe, provide feedback, interrupt an action or block a transition.
- Run discovery and cheap checks during the work and reserve more expensive verifications for relevant changes and completion points.
- Explicitly represent `waiting_human_review`. Returning control to the user in that state is allowed; declaring the task complete is not.
- Apply the pre-implementation gate to behavioral work that depends on a pending contract; distinguish real blocking from guidance and record host limitations.
- Reconcile the effective state at closing, without relying only on a watcher's events or on the cache.
- Configure the protected check over the revision that will be integrated and test attempts to bypass the local hooks.
- Document what the local installation cannot guarantee when the agent controls its own environment.

## MVP exit criteria

- [ ] There is an end-to-end demonstration with scenarios run directly from the Markdown.
- [ ] The Java, Python and Go execution adapters have verified versions and limits; parsing alone does not count as execution.
- [ ] It is not necessary to maintain or materialize `.feature` files to use this demonstration.
- [ ] New, changed and exempted documents have distinct and traceable states.
- [ ] The user reviews the exact content to which their acceptance will be bound.
- [ ] The agent cannot produce that acceptance with the credentials available in the declared installation scenario.
- [ ] Completion requires applicable acceptance and current evidence, with explicit failures and absences.
- [ ] The waiting-for-the-user state causes neither a false completion nor a stop loop.
- [ ] Pre-implementation suspension has been demonstrated on the chosen host, or its lack of support has been declared, without promising nonexistent local prevention.
- [ ] The first adapter has verified capabilities, without presuming equivalence between Claude Code and Codex.
- [ ] The protected gate identifies violations even when the local hooks are not used.
- [ ] The deterministic cases and the semantic limits of the [validation plan](validation-plan.md) have been exercised and recorded.

These items are planned criteria. The boxes remain unchecked until the corresponding evidence and review exist.

## Expansions after the pilot

The following opportunities are outside the initial commitment, unless there is an explicit scope decision:

- A second agent adapter, reusing the core and the policy.
- PR review organized by requirement, behavior change and evidence.
- Continuity across sessions and coordination of obligations among multiple agents.
- Impact suggestions based on relations between documents, modules and tests.
- Targeted mutation testing and assisted review of assertion strength.
- Turning incidents into regression scenarios and recording rationales.
- Adapters for API, accessibility, architecture and performance checks.
- Comparison of agents and models by how well they meet the criteria, human effort and cost.
- Release readiness views and pertinent post-deploy checks.

Each expansion must justify the observed problem, reuse the existing links and show a net benefit relative to the maintenance effort. There is no intent to simultaneously build a requirements platform, a complete orchestrator and a general-purpose test suite.

## Decisions still open

| Decision | What needs to be resolved |
| --- | --- |
| Initial stack and runner | Choice after demonstrating real in-memory execution and viable adapter maintenance. |
| First agent environment | Selection after verifying the APIs and capabilities of the candidate versions. |
| Acceptance authority | In-house service, Git provider mechanism or another authenticated solution with separation of permissions. |
| Hosting model | Define what can operate locally and which authority/verifier must exist out of the agent's reach. |
| Reuse and revocation policy | Establish the validity of old acceptances, context, scope and revocations. |
| Scope of the block | Task, dependent work or the entire project, in addition to the integration block. |
| Syntax and granularity | Stabilize document versus section, marking of executable blocks and allowed references. |
| License | Choose explicitly before announcing terms of use or distribution. |
| Pilot goals | Define usefulness and cost thresholds before analyzing the results. |

## References

- [Requirements and scenarios](requirements.md)
- [Architecture](architecture.md)
- Acceptance and trust boundaries (removed by [D-021](decisions.md))
- [Document format](format.md)
- [Index and incremental processing](indexing.md)
- [Agent integrations](integrations.md)
- [Validation plan](validation-plan.md)
