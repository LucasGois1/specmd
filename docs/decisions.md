# Design decisions and open questions

This record consolidates the discussion that originated the project. The guidelines below were expressed during the design; this is not equivalent to an authenticated receipt of acceptance of the content of these files. The technical details remain proposals for review and experimentation.

## Guidelines from the discussion

| ID | Guideline | Consequence |
| --- | --- | --- |
| D-001 | Markdown is the canonical source. | Explanation, requirements and scenarios stay in the `.md`; no editable `.feature` copy is needed. |
| D-002 | The run must not depend on `.feature` files. | Demonstrate parsing and adaptation in memory; do not assume native Cucumber support for Markdown. |
| D-003 | Alignment needs to be verified in both directions. | Relate requirements to the implementation, and relevant behavior changes to a recognized intent. |
| D-004 | Documenting an assumption does not authorize it. | Distinguish agreed behavior, agent proposal and behavior merely observed in the legacy code. |
| D-005 | The contract needs explicit human acceptance. | Bind the decision to the version presented, including for the specification written together. |
| D-006 | Changing contractual documentation or scenarios requires a new review. | The previously accepted version does not automatically authorize a new version. |
| D-007 | Changing code requires renewing the relevant evidence. | Preserve the acceptance when the intent did not change; avoid repeated human approvals for implementation attempts. |
| D-008 | The agent cannot issue its own acceptance. | Separate the permissions to propose, to accept and to apply the gate. |
| D-009 | Content, review and authorship need traceability. | Use content identity, diff, Git history and authenticated identity of the events. |
| D-010 | Documents can be behavioral, informational or mixed. | Require scenarios for the behavioral obligations and acceptance for the informational exemption. |
| D-011 | A Gherkin exemption is not an exclusion from the inventory. | Monitor informational documents to detect changes that require review. |
| D-012 | Hooks must improve the experience with agents. | Connect analyses to supported events, without assuming equivalence between Claude Code and Codex. |
| D-013 | Waiting for the user is a legitimate state. | Allow handing control back without marking completion or entering blocking loops. |
| D-014 | The analysis must be incremental. | Reuse valid results, while keeping reconciliation and invalidation correct. |
| D-015 | The index does not grant approval. | Treat inventory and cache as derived, rebuildable data. |
| D-016 | Automatic classification is auxiliary. | Separate deterministic checks from semantic suggestions and human decisions. |
| D-017 | The name chosen by the user is SpecMD. | Use `specmd` as the name of the repository and of the proposed interface. Global availability of the brand or package was not verified. |
| D-018 | Initial support needs to cover at least Java, Python and Go. | Research and test real adapters per language before stabilizing the architecture; do not assume a universal Cucumber parameter. |
| D-019 | The user asked to investigate the overlap with Markdown with Gherkin before moving forward. | The research found additional prior art; compare reuse and the smallest integration needed, without assuming novelty or an advantage of an independent product. |
| D-020 | The user wants to test SpecMD locally in Codex with a real agent. | Prepare installation and trials in a test instance of Codex; the presence of the CLI is not equivalent to the installation of the SpecMD adapter nor to the validation of its blocks. |
| D-021 | On 23/10/2026, the user redefined the product: SpecMD is an assistant, not an audit. | Replaces D-005 and D-008 and the signed acceptance of D-006/D-009. The developer's confirmation is a reply in the conversation; the plugin runs deterministic checks and sends feedback back without ending the session. Authority, trust, signatures, browser review, protected `verify` and implementation blocking were removed. See the section below. |
| D-022 | On 24/10/2026, the user chose to optimize performance for projects with thousands of files, including running only the affected scenarios. | Per-document cache, code fingerprint through Git and scenario selection by coverage. Implemented; see [implementation status](implementation-status.md). |
| D-023 | Warn when a confirmed scenario is weakened or removed. | Diff against the scenarios as of the developer's last message; sends back to the agent only on the strong signal. Implemented in SMD-REQ-028. |
| D-024 | Warn when an ignored document starts declaring rules. | Notice only, when the file changes. Implemented in SMD-REQ-029. |
| D-025 | Legacy adoption through a command that starts from the existing documentation. | Lists all documents, the developer filters with the agent and the scenarios are born one document at a time. Implemented in SMD-REQ-030; `@wip` remains the developer's decision. |
| D-026 | Support MDG (`.feature.md`) following the official specification. | Conversion to Gherkin in memory, preserving the lines. Implemented in SMD-REQ-031. |
| D-027 | Validate Codex with a real LLM and the new events. | Depends on authentication and on the user trusting the hooks. Run on 24/10/2026; see [native sessions in Codex](../research/codex/native-session.md). |
| D-028 | Measure the value of SpecMD in a comparative pilot. | Strong comparison group and evaluation by hidden acceptance tests. First round run on 24/10/2026 with claude-haiku-5-5 and gpt-6-luna; see [pilot](../research/pilot/README.md). |
| D-029 | On 27/10/2026, the user asked to translate the whole repository into English, so that more people can use the plugin. | Code, documentation and research are in English. The plugin's messages are in English by default, and `language = "pt"` in `specmd.toml` keeps them in Portuguese. Recorded evidence (fixtures, logs and pilot results) stays as it was recorded. Implemented in SMD-REQ-032. |

## D-021 — Assistant, not audit (23/10/2026)

The user described the expected use with an example: a payment system developed with agents. The agent writes the project documentation; a check verifies whether it has usage scenarios; if it does not, the agent receives that feedback and talks to the developer to confirm the requirements and write the scenarios in the document itself. The agent asks whether everything is right, the developer confirms and the agent implements. At the end, an analysis checks whether the scenarios exist and pass; whatever is missing goes back to the agent.

Consequences:

- The documentation with embedded scenarios is the canonical source of the business rules; there is no parallel `.feature` to diverge.
- There is no documentation phase: any work on Markdown triggers the analysis. Not every Markdown describes system behavior; those stay out of the analysis and the agent asks the developer when in doubt.
- Scenarios that are new or changed since the developer's last message are not required until the developer sees them; the run is required when the code changes.
- The feedback is deterministic and bounded: the same feedback repeated, or the repetition limit, lets the agent stop. Internal errors become warnings.
- The plugin must load by itself when someone opens the agent in the repository (planned delivery).

Rows D-005, D-006, D-008 and D-009 of the table above, the technical choices about authenticated acceptances and the open decisions about interface, granularity and reuse of acceptances remain as history.

## Evolutions chosen (24/10/2026)

With the D-021 minimum validated in real sessions, the user chose evolutions D-022 to D-028 and approved the detailing below, with the corrections indicated. Nothing in this section is implemented. Each item becomes its own PR; its requirements and scenarios go into [requirements.md](requirements.md) and are confirmed by the user before the implementation. Agreed order:

1. Performance (D-022).
2. Weakened or removed scenario (D-023) and ignored document that gains a rule (D-024).
3. Legacy adoption (D-025).
4. MDG (D-026).
5. Codex with a real LLM (D-027), when the user can authenticate and trust the hooks.
6. Comparative pilot (D-028), when the previous items are stable.

### D-022 — Performance in large projects

Today each `PostToolUse` rereads and reanalyzes every Markdown file, the code fingerprint runs `lstat` on every file and the `Stop` runs every scenario. In projects with thousands of files this grows with the repository, not with the change.

Decided:

- **Per-document cache** in `.specmd/local/`, local and rebuildable: a document with the same content reuses the previous analysis; only the links between documents (duplicate IDs, requirements without a scenario) are recomputed over the whole set.
- **Code fingerprint through Git:** the current commit plus the changed or new files, instead of examining the whole repository.
- **Only the affected scenarios:** each run records the files exercised by each scenario. On finishing, the scenarios that touch changed files, the new or changed ones and the ones that never ran are run. Without coverage available, everything runs, as today; that is the case of Java and Go at first, and their coverage (JaCoCo, `go test -cover`) is left for later.
- **Safety net:** the full run remains available through the CLI and in CI. The selection can be wrong (dynamic import, configuration file read at run time), and the feedback says when only part of the scenarios ran.
- **Benchmark** in a synthetic repository on the order of 5 thousand Markdown files and 50 thousand files, measured before and after. Goal: `PostToolUse` under 300 ms.

Decided with the user on 24/10/2026, with the scenarios of [SMD-REQ-027](requirements.md): the `Stop` and `specmd run --affected` run only the affected ones; `specmd run` runs all of them. The feedback reports how many scenarios were left out. The selection is per function, not per file: every file imported by the steps shows up as used by every scenario. A change in the steps, in `environment.py`, in the configuration or at the module level runs all of them; scenarios that start processes or open connections always run.

### D-023 — Weakened or removed scenario

When the agent deletes a scenario or changes the expected value of a `Then` so that the code passes, today this goes unnoticed.

Decided:

- **Baseline for comparison:** the scenarios as they were at the developer's last message. The hook now stores the content of the scenarios, not only the fingerprint.
- **Distinguished changes:** removed scenario, changed `Then`, changed `Given` or `When`, added `@wip` and removed requirement.
- **Notice:** after the edit, the agent receives the exact diff; on finishing, the developer sees the same summary, even if everything passes. The notice is informative, including when the developer themselves asked for the change.
- **Sent back to the agent, once,** only on the strong signal: the scenario was failing in the last run, the agent changed its expected value and the code changed in the same turn.

### D-024 — Ignored document that gains a rule

Decided:

- Ignored files, whether through `.specmdignore` or the default patterns, are still read lightly, only to detect a `…-REQ-…` heading, a Gherkin block or an MDG keyword.
- The notice is issued only when the file changes and starts having one of these. A README that always had a Gherkin example does not produce a notice.
- The notice offers two ways out: take the file out of `.specmdignore` (or use `!path`) or move the rule to a behavior document. When in doubt, the agent asks the developer.
- Notice only; it does not send work back to the agent on finishing.

### D-025 — Legacy adoption

The user corrected the initial proposal: the plugin does not sort or filter documents by heuristics (words such as "must" or "cannot", numbers, limits). The decided flow:

1. A specific command (proposed name: `/specmd:adopt`) lists all the Markdown files of the project, except the ones ignored by default and the entries the team already has in `.specmdignore`.
2. The agent presents the list to the developer and separates with them what is behavior documentation. Whatever the developer says to ignore, the agent writes to `.specmdignore`.
3. With that filter done, the agent analyzes one document at a time, proposes requirements and scenarios and shows them to the developer for confirmation.
4. After the confirmation, the existing loop follows: steps, run and feedback until it passes.
5. **Divergence between documentation and code:** if a scenario fails because the code does something else, the agent does not fix it alone. It asks the developer which of the two is right.

Open:

- Adoption progress: decided on 24/10/2026 that there is no adoption-specific state; the documentation and `.specmdignore` are enough to resume.
- `@wip` in the adoption: decided on 24/10/2026 that it remains the developer's decision; the agent implements the steps of one document before moving on.
- A failure in a scenario that never passed comes with the divergence guidance (ask the developer which one holds), approved with SMD-REQ-030.

### D-026 — MDG (`.feature.md`)

The official specification ([MARKDOWN_WITH_GHERKIN.md](https://github.com/cucumber/gherkin/blob/main/MARKDOWN_WITH_GHERKIN.md)) and the reference tokenizer in JavaScript were checked on 24/10/2026:

- **Extension:** `.feature.md` is mandatory.
- **Prose:** the format is a superset of GitHub Flavored Markdown and allows prose. Lines that are not Gherkin (paragraphs, images, links) are ignored by the parser.
- **Keywords and steps:** keywords as Markdown headings (`# Feature`, `## Rule`, `### Scenario`, `Scenario Outline`, `Examples`, `Background`); steps as list items (`*` or `-`).
- **Tables and Doc Strings:** tables in GFM format, indented by 2 to 5 spaces; fenced blocks are Doc Strings.
- **Tags:** in backticks, on the line above the keyword.
- **Structure:** one feature per file; the `Feature` heading is optional.
- **Language:** there is no `# language:`. The language is defined globally.
- **Support:** the official parser exists only in JavaScript; Behave, Cucumber-JVM and Godog do not read the format.

Decided:

- **Scope:** `*.feature.md` is read as MDG; the other `.md` files keep using fenced blocks marked as `gherkin`. In a `.feature.md`, a fenced block is a Doc String, as in the specification, and the two styles do not mix in the same file.
- **Conversion:** SpecMD converts MDG into classic Gherkin in memory, preserving the line numbers. Engines and bridges do not change.
- **Language:** comes from `gherkin_language` in `specmd.toml`.
- **Requirements:** headings that are not keywords, such as `## PAY-REQ-001 — Refund`, are prose for MDG and still count as a requirement by their position.

Open:

- Requirement ID in the `Rule` heading: accepted, decided on 24/10/2026.
- Languages: all of Gherkin's languages, through `gherkin_language`, decided on 24/10/2026. The Java and Go bridges do not read the protocol's `language` field; SpecMD inserts the `# language:` header in the text sent to them.

### D-027 — Codex with a real LLM

Decided:

- Check in the installed version of Codex:
  - the available events, including `UserPromptSubmit`;
  - whether `Stop` accepts `decision: block`;
  - whether `additionalContext` works at session start and after tools.
- Test the project root without `CLAUDE_PROJECT_DIR`.
- Repeat the four-turn script already exercised in Claude Code.
- User dependencies: Codex authentication on the machine and trusting the hooks through `/hooks`, which is a human action.

Run on 24/10/2026 with Codex 0.163 and `gpt-6-luna`: the four events, `additionalContext` at the start and after tools, and the `Stop` block worked; see [native sessions in Codex](../research/codex/native-session.md).

Open: how to activate SpecMD in Codex without the project's `.claude/settings` (today, through `specmd.toml`, or through an equivalent Codex mechanism).

### D-028 — Comparative pilot

Decided:

- **Tasks:** 6 to 10, in two example apps (cart and payments), with planted traps: an ambiguous limit, a rule that contradicts the documentation and a request that tries to invent a rule.
- **Strong comparison group:** the same repository, the same documentation, the same tests and a `CLAUDE.md` that says to keep the documentation up to date, without SpecMD.
- **Simulated developer with hidden intent:** a script, or an LLM playing the developer, answers according to a specification the agent does not see.
- **Independent evaluation:** hidden acceptance tests encode the real intent.
- **Metrics:**
  - invented rules that got through;
  - omissions;
  - turns until done;
  - false blocks;
  - hook latency (p50 and p95);
  - tokens and cost.
- **Repetitions:** 3 to 5 per task.

Open:

- Which models to use, which determines the cost.
- The goals, defined before measuring.

### Ideas raised and not chosen for now

They remain available for future choices:

- behavior change without documentation ("invented rule") detected on finishing;
- a marker for Gherkin examples that must not run;
- CI and a per-requirement report on the PR;
- a bug becomes a regression scenario;
- task context with the related requirements;
- guidance to turn vague prose into a scenario;
- Windows;
- reusing the ecosystem (Spec Kit, OpenSpec, Tracey);
- mutation testing on the scenarios;
- verifiers beyond Gherkin;
- comparison between agents;
- release readiness.

## Proposed technical choices

These choices are implementation hypotheses, subject to validation:

- Independent CLI core, with structured output and small adapters for each agent.
- Plain Markdown with front matter and identified Gherkin blocks.
- SHA-256 of the documents' bytes and a deterministic manifest containing paths and hashes.
- Authenticated external acceptances, or signed artifacts whose authority stays out of the agent's reach.
- Run evidence bound to the relevant contract, code, tests, configuration and environment.
- Protected integration check beyond the local hooks.
- Rebuildable local index; start with simple storage before optimizing queries.
- Protected scope and policy to prevent self-exemption, silent exclusions or replacement of the verifier.

## Decisions still open

| Question | How to decide |
| --- | --- |
| License | Explicit decision by the maintainer; public visibility does not choose a license automatically. |
| Language and distribution of the core | Compare parser/runner integration, installation and maintenance. |
| Initial runner | Spike demonstrating in-memory runs, origin in the Markdown and structured results. |
| First integrated agent | Prioritize preparing local tests in Codex, verifying version, APIs, hooks and the real ability to block events before announcing support. |
| Acceptance interface and storage | Demonstrate identity, exact reviewed content, revocation and separation of credentials. |
| Acceptance granularity | Compare acceptance per document, requirement or set, without losing the approved context. |
| Acceptance reuse policy | Define the effects of renaming, reverting to old content, context change and revocation. |
| Blocking policy | Define what pauses implementation, task completion or integration, and the reach of the dependencies. |
| Non-functional requirements | Choose specific adapters when Gherkin is not the appropriate mechanism. |
| Format compatibility | Addressed by D-026: fenced blocks in plain `.md` files and official MDG in `.feature.md` files, with no competing dialect. The open points of D-026 remain. |

## Evolutions to consider after the core

- Task context prepared from the applicable contracts.
- Change review oriented by requirements, evidence and contract changes.
- Continuity across sessions and agents with current gaps and evidence.
- Conversion of incidents and bugs into regression scenarios and recorded justifications.
- Impact analysis with explicit coverage and uncertainties.
- Targeted mutation testing to assess the strength of the checks.
- Comparison of agents by how well they meet the criteria, rework and review effort.
- Compatibility, accessibility, architecture and performance verifiers.

These capabilities are not automatically part of the MVP. Their inclusion depends on demonstrating benefit in the [validation plan](validation-plan.md) and on keeping the sequence of the [roadmap](roadmap.md).
