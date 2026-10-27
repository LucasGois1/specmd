---
specmd:
  schema: 1
  id: SMD-DOC-POSITIONING
  kind: reference
  exemption_reason: "Comparative research and design recommendations; does not create accepted product requirements."
---

# Positioning and prior art

**Status:** documentary research for human review, consulted on October 22, 2026 in the America/Sao_Paulo time zone. The informational classification above is a proposal and does not constitute an accepted exemption. This survey does not implement integrations nor change the project's current requirements.

The goal is to evaluate overlap of concepts and engineering before building subsystems that already exist. Sources from the projects themselves and official documentation were consulted, with commits or tags pinned when available. This is not an exhaustive survey; the absence of a capability in the consulted excerpt does not show that it does not exist in the project or in its extensions.

## Research conclusion

The proposal has important prior art. Executable documentation in Markdown, specifications guiding agents, traceability between requirement and code, human review and gates with hashes already appear in existing tools. These elements, individually or in some combinations, do not support a claim of novelty for SpecMD.

The space to investigate is the usefulness of an integrated flow: the human accepts a version and a scope; documents and exemptions remain monitored; relevant changes have a recognized origin; scenario evidence corresponds to the current code; the agent receives an actionable gap before completing. This is a hypothesis of benefit and user experience, not an already demonstrated advantage nor a claim of exclusivity.

Conceptual or functional overlap does not prove that an alternative is mature, reliable or suitable for the intended environment. Nor does it invalidate SpecMD's usefulness: integration quality, maintenance and cost of use need to be evaluated in the experiments, separately from the existence of prior art.

## Official Markdown with Gherkin

The [official MDG document at commit `0c50fc12112d9400892a760ee7302b232a466cb8`](https://github.com/cucumber/gherkin/blob/0c50fc12112d9400892a760ee7302b232a466cb8/MARKDOWN_WITH_GHERKIN.md) describes scenarios in renderable Markdown: it uses `.feature.md`, headings for the Gherkin elements, lists for steps and tags in backticks. It also describes rendering with results and attachments via Cucumber Messages. Therefore, combining prose, scenarios and results in Markdown has direct prior art in the Cucumber ecosystem itself.

| Aspect | MDG in the consulted document | Current SpecMD proposal |
| --- | --- | --- |
| Input | Markdown dialect with the `.feature.md` extension. | The project's Markdown with fenced `gherkin` blocks. |
| Scenario structure | Markdown headings and lists. | Classic Gherkin inside the fences, extracted by a parser. |
| Presentation source | Original Markdown document, related to the results. | Original document and the source map of each block/scenario. |
| Documented portability | The note limits the described support to the JavaScript parser, version 19 or later. | Java, Python and Go require their own validation of the parser and of the integration with the executor. |

The support note belongs to the cited snapshot: it does not allow extrapolating current support by all parsers, discovery by all runners or universal compatibility. Nor does it demonstrate that other ecosystems cannot be adapted.

The [baseline executed later](../research/javascript-mdg/README.md) confirmed native MDG in Cucumber.js 13.3.0: discovery of `.feature.md`, explicit execution of `.feature.md` and of plain `.md`, plus a real assertion failure. The Markdown with fenced blocks had exit code 0 and zero scenarios. The [feasibility proofs in the other languages](runner-feasibility.md) used in-memory adaptation and do not constitute uniform native support for the MDG syntax.

`.feature.md` is still a Markdown file; that suffix, by itself, does not create the intermediate `.feature` file forbidden by the design. The relevant difference is the input syntax and its integration with the runtime. A fenced block with classic Gherkin must not be advertised as native MDG without a compatibility test.

The same document states that the MDG AST omits prose descriptions. Therefore, the identity of the SpecMD contract must remain based on the original Markdown, with narrative and metadata, and not only on the executable AST. The scenario syntax alone does not cover the intended classification and acceptance policy.

**Investigation recommendation:** compare MDG with fenced block extraction before stabilizing the format. Reuse the official grammar and representations whenever suitable. This research does not decide to migrate the current documents nor authorize a second canonical source.

## Other verified prior art

| Project or infrastructure | Documented capability | Implication for SpecMD |
| --- | --- | --- |
| [Gauge — writing specifications, commit `30362125`](https://github.com/getgauge/docs.gauge.org/blob/30362125c4176640ad04feaf7954d0bf42ccc31d/writing-specifications.rst) | Accepts `.md` or `.spec` specifications, with headings, scenarios and steps implemented in code. | Executable Markdown and narrative with scenarios are already an established solution. The presented syntax needs its own evaluation; equivalence with the proposed Gherkin blocks is not presumed. |
| [Concordion — Markdown instrumentation](https://concordion.org/instrumenting/java/markdown/) | Adds commands in Markdown links to connect examples, fixtures and assertions. | Running examples directly from a document also predates SpecMD. Changing the syntax is not, by itself, a product benefit. |
| [Tracey — README at commit `66008a85`](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/README.md) | Relates Markdown requirements to implementation and tests, identifies gaps and stale references, offers CLI/MCP/LSP, integration with Claude/Codex and version control hooks. | Bidirectional traceability, agent support and drift detection also have very close prior art. Evaluate integration before creating another index and annotation schema. |
| [GitHub — branch protection, commit `481d4e35`](https://github.com/github/docs/blob/481d4e35beb53953e277d0b11ba4a18f8c8ade4f/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md) | Required reviews, dismissal of stale approvals, approval of the most recent push by another person and required checks before merging. | Reviewer identity, change review and CI enforcement can reuse the provider. Do not presume the need to build an in-house acceptance service. |
| [Spec Kit — SDD at commit `27d14e20`](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/docs/reference/agentic-sdd.md) | Checklists under the reviewer's responsibility, consistency analysis across artifacts and specification-driven implementation. | “The specification must guide the agent” and “the implementer does not approve their own work” are already part of a documented flow. |
| [OpenSpec — README at commit `56ef0ac1`](https://github.com/Fission-AI/OpenSpec/blob/56ef0ac1fd2270e88d276b40da9f23ec0f9c6e96/README.md) | Requirements and scenarios in Markdown, proposals produced by the agent and human review before the code. | Proposing, reviewing and implementing specs is shared ground; the advantage needs to show up in how the flow operates. |

The [consulted Tracey documentation](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/README.md#version-tracking) also describes requirement versions and implementation references that become stale when the requirement changes. This is especially close to the problem of contract evolution. A verification annotation, however, is not by itself equivalent to a receipt of a current run; the policies actually available and how they compose need to be verified in the technical comparison.

Tracey is implemented in Rust, but it is not restricted to analyzing Rust projects. At the same pinned commit, its [central language registry](https://github.com/bearcove/tracey/blob/66008a85e22fc3d4e437a8e78fee4f5f99c644b0/crates/tracey-core/src/languages.rs#L108-L110) explicitly includes Go (`.go`), Java (`.java`) and Python (`.py`), with their own grammars and extractors. The README list omits Python, so it is not a complete description of that support in the source. This confirms analysis and traceability in those languages in the consulted snapshot, without demonstrating BDD/Gherkin execution or feature parity among them.

The [OpenSpec verification flow in the consulted snapshot](https://github.com/Fission-AI/OpenSpec/blob/56ef0ac1fd2270e88d276b40da9f23ec0f9c6e96/docs/workflows.md#L331-L374) evaluates completeness, correctness and coherence, including implemented requirements and covered scenarios. The flow itself documents that verification does not block archiving. This is a concrete difference in that flow, without demonstrating the absence of configurable or external gates in the whole ecosystem.

## The comparison must include extensions and compositions

[Spec Kit documents runtime events per integration](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/docs/reference/extensions.md#L297-L322), with different subsets per host. Therefore, a common core plus lifecycle adapters also has direct prior art.

Its [community catalog at the same commit](https://github.com/github/spec-kit/blob/27d14e20c187c1f2916540ea201ecbdc9f8ed588/extensions/catalog.community.json) serves for discovery, not as an audit of capabilities. The consulted entries were not marked as verified. The following descriptions were checked against the maintainers' own sources:

- [spec-gates `v0.4.1`](https://github.com/schwichtgit/spec-gates/blob/v0.4.1/README.md) describes a policy and a verifier shared across the agent, Git and CI boundaries, attestations with SHA-256 and executable criteria in Markdown `accept` blocks. It is a secondary engineering reference in this survey, with documented overlap; maturity, maintenance, adoption and operational reliability were not evaluated. The effective authority of human acceptance and the bypass paths also require specific evaluation.
- [spec-kit-bdd `v1.0.3`](https://github.com/RSginer/spec-kit-bdd/blob/v1.0.3/README.md) describes relations between specs and scenarios, but generates `features/*.feature` files and documents optional hooks. The documented form does not directly meet SpecMD's constraint of running without `.feature`; it may still provide lessons or adaptation points.
- [plan-review-gate `v1.0.0`](https://github.com/luno/spec-kit-plan-review-gate/blob/v1.0.0/README.md) requires the spec/plan to be merged through review before the tasks and documents a `--skip-review` option. The desired policy and the real permissions must be compared, instead of equating any gate with mandatory acceptance that the agent cannot bypass.

This prior art makes it inappropriate to position SpecMD merely as “executable Markdown with hooks, hashes and CI”. Nor does it justify concluding that an existing composition already meets every need: that must be demonstrated, with equivalent scope and configuration.

Repository stars do not prove quality, maturity or suitability. This comparison does not use a star count as evidence of those properties.

## Per-version acceptance: reuse before rebuilding

[GitHub's documented protections](https://github.com/github/docs/blob/481d4e35beb53953e277d0b11ba4a18f8c8ade4f/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md) can already require approval and dismiss it when the diff changes. The provider also allows restricting the expected source of a check and configuring how administrative bypass is handled. These capabilities depend on configuration and separation of permissions; they are not installed in this project just because they are mentioned here.

A manifest and its hash can identify the accepted documentation subset independently of new attempts in the code. That granularity must be compared with per-PR acceptance: per-document exemptions, renames, code revisions without a change of intent and local resumptions may call for an additional association layer. The benefit of keeping it only exists if it reduces re-approvals and ambiguity without weakening the existing control.

In the cited protection documentation, required checks may be considered satisfied in states such as `skipped` or `neutral`. Therefore, a favorable aggregate status does not prove that all mandatory scenarios were run. The SpecMD policy needs to verify the pertinent evidence, whether implemented as its own check or by reusing an existing verifier.

The hash is identity infrastructure. Trust comes from the provenance of the decision and of the run, from the permissions and from the protection of the verifier. Changing the hash function or creating JSON receipts is not a differentiator by itself.

## Advantage hypothesis to demonstrate

A testable formulation for SpecMD would be: **reduce the work and the errors needed to maintain, during the agent's activity, the correspondence between accepted human intent, scope documentation, behavior changes and current scenario evidence.**

The candidate dimensions need to be evaluated as a complete flow:

1. **Review at the right moment:** the agent delivers an identified proposal and enters `waiting_human_review`, without a blocking loop or a false completion.
2. **Versioned classification and exemptions:** informational and mixed documents receive explicit decisions; a change reopens the appropriate review, keeping the inventory up to date.
3. **Bidirectional provenance:** behavior changes without a recognized origin are exposed, in addition to requirements without implementation. Tracey and other traceability mechanisms must be part of the comparison.
4. **Evidence per scenario and snapshot:** a result is associated with the contract, code and verifier actually used; a skipped scenario or an old result does not satisfy the policy.
5. **Integration with existing runtimes:** preserve the origin in the Markdown and adapt Java, Python and Go without imposing an intermediate `.feature` file. Per-language compatibility remains an engineering question to validate.

No item on this list should be advertised as exclusive. The candidate value is the measurable reduction of friction and divergences when they are combined, with clear trust limits.

## Reuse, adapt and investigate

The recommendations below are proposals for the next architecture decision, not scope changes already accepted.

| Treatment | Components or decisions | Evidence needed before building |
| --- | --- | --- |
| Reuse | Gherkin grammar, official parsers and execution representations. | Demonstrate the input format and the source maps in the chosen runtime. |
| Reuse | Authenticated reviews, integration protections and Git provider checks. | Demonstrate that the agent's credential neither approves nor bypasses the policy. |
| Reuse | Existing hash, diff and Git implementations and result formats. | Reproducibly identify the snapshot and the necessary provenance chain. |
| Adapt, if there is a gap | Markdown block extraction or MDG input, IDs and binding to the results. | Compare integration effort and fidelity to the original document, without duplicating the contract. |
| Adapt, if there is a gap | Traceability, index and agent integration from tools such as Tracey, Spec Kit and OpenSpec. | Show which controls already meet the policy and which minimal extension is missing. |
| Investigate | Per-version human exemption, mixed content and per-scope acceptance independent of the attempts in the code. | Demonstrate usefulness and the absence of self-exemption in the compared configurations. |
| Investigate | Human waiting state, evidence validity and uniform enforcement across hosts. | Reproduce adverse cases, capability differences and failure recovery. |

A new runner, a new scenario language, an in-house identity service and a new traceability database must not be automatic consequences of the idea. Each subsystem would need to justify why a smaller integration does not do the job.

## Experimental comparison and reduction criteria

The [validation plan](validation-plan.md) must include a baseline with well-configured existing tools. Comparing only against an agent without documentation or without CI would overestimate the gain.

Experiment proposal:

- Set up a simple configuration with a specification runner, protected reviews and CI.
- Set up a composition of existing SDD, traceability and gates that covers as much of the needed policy as possible at the lowest reasonable cost. Do not install every project in the research just to make the baseline artificially complex.
- Compare that composition with the smallest SpecMD extension capable of filling the remaining gaps, on the same tasks and with the same agent.

The cases must include a rule invented by the agent, a contract change after acceptance, a new document, an informational document that acquires an obligation, evidence from another snapshot, a skipped scenario and an attempt to change the exclusion policy. The human evaluation must judge the desired behavior independently of the report produced by the tools.

Measure divergences that reach completion, correctly detected gaps, undue blocks, review time, number of human interactions, rework and installation/maintenance cost. Define gain criteria and cost limits before running the experiment; this document does not claim results nor set goals already accepted.

Reducing the scope or abandoning a subsystem will be the appropriate decision when:

- The existing composition delivers the same controls with equal or less effort: SpecMD can be just a plugin, preset or configuration package.
- MDG or another extension point serves the chosen format: avoid maintaining a competing parser or dialect without need.
- The remaining problem is only navigation and traceability: integrate a specialized tool before reproducing it.
- The provider's acceptance is sufficient for the real work: avoid creating an independent approval authority.
- The gain disappears when comparing with the strong baseline, or the review/classification cost exceeds the rework avoided: reduce the hypothesis or stop the standalone product.
- Permission separation or running without `.feature` is not viable in the chosen environment: declare the limitation and reassess the approach, without silently weakening the requirements.

The next useful result is a comparative demonstration of the gaps, not a broad claim of originality. The general decisions remain in [decisions.md](decisions.md), and the current requirements in [requirements.md](requirements.md).
