---
name: specmd
description: SpecMD conventions for documentation with BDD scenarios. Use when writing or changing behavior documentation, requirements or Gherkin scenarios, when deciding whether a Markdown file needs scenarios, or when SpecMD reports gaps or failing scenarios.
---

# Working with SpecMD

The Markdown documentation is the canonical source of the business rules. The Gherkin scenarios live in the document itself and are both the specification and the acceptance test. Do not create `.feature` files.

## Writing behavior documentation

- Describe each rule in a document. A requirement can have an ID in its heading, with any prefix: `## PAY-REQ-001 — Refund within 7 days`.
- Right below the requirement, write a ```gherkin block with concrete scenarios (real values, edge cases). The scenarios below a requirement heading are linked to it; a `@PAY-REQ-001` tag changes the link.
- English is Gherkin's default. When writing scenarios in another language, declare it in the block, for example `# language: pt`.
- Scenarios that should not be enforced yet are tagged `@wip`, but only when the developer decides. Do not tag `@wip` on your own: scenarios awaiting confirmation are already not enforced.

## Confirming with the developer

- After writing or changing scenarios, show them to the developer and ask whether they are correct before implementing. Point out ambiguities (limits, rounding, exceptions).
- Do not change an existing scenario to make the code pass without confirming with the developer: if the requested code contradicts the documentation, ask whether the rule changed.
- If the existing code contradicts the documentation, do not fix either one on your own: show the difference to the developer and ask which one holds.

## Markdown with Gherkin

- A `*.feature.md` file uses Cucumber's MDG format: keywords as headings (`### Scenario:`), steps as list items (`* Given …`), tables indented by 2 to 5 spaces and free prose between them. Do not use ```gherkin blocks in these files: there, a fenced block after a step is the step's text.
- MDG does not accept `# language:`; the language comes from `gherkin_language` in `specmd.toml`.

## Markdown that does not describe behavior

- README, CHANGELOG, setup guides, notes and technical ADRs go into `.specmdignore` at the root (`.gitignore`-style patterns).
- When that is clearly the case, add it yourself. When in doubt, ask the developer whether the document needs scenarios; if it describes behavior, recommend writing them.

## SpecMD feedback

- After you edit Markdown, SpecMD points out documents without scenarios, requirements without a scenario and invalid Gherkin.
- If you remove a scenario, change what it expects, tag it `@wip` or remove a requirement, SpecMD shows the change to you and to the developer. If a failing scenario had its expected value changed together with the code, it asks you to restore the scenario, unless the developer asked for the change.
- If a document in `.specmdignore` starts declaring requirements or scenarios, move the rule to a behavior document or take the file out of `.specmdignore`.
- In a project with existing documentation, `/specmd:adopt` lists the documents without scenarios. Sort out with the developer what goes into `.specmdignore` and handle one document at a time. If a scenario that never passed fails because the code does something else, that is a divergence: ask the developer which one holds before changing either.
- When you finish an implementation, it runs the scenarios affected by the change and reports the scenario, the step, the line, the error message and, for steps without an implementation, a snippet to start from. Implement until it is green.
- To check at any time, without installing anything, use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" check --root "$(pwd)"` (gaps and last run) or `... run --root "$(pwd)"` (runs every scenario; with `--affected`, only the ones affected by the change). The session start shows the same command with the full path.
