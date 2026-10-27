---
description: Adopts SpecMD in a project that already has documentation, one document at a time
---

Lead the adoption of SpecMD in this repository with the developer. The existing Markdown documentation becomes the canonical source, with Gherkin scenarios in the document itself.

1. At the project root, list what is missing:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/specmd_cli.py" adopt --root "$(pwd)"
   ```

   The result lists, in path order, the documents without scenarios and the requirements without a scenario. Those ignored by default (README, CHANGELOG, agent instructions) and those in `.specmdignore` are already left out. Do not sort or discard documents on a hunch.

2. Show the list to the developer and ask which documents do not describe system behavior (setup guides, notes, technical decisions). Write exactly the ones they name into `.specmdignore` at the root. The others are behavior documentation.

3. Handle one document at a time. Read the document, propose the requirements (heading with an ID, such as `## PAY-REQ-001 — Refund`) and the Gherkin scenarios that express the rules written in it, with concrete examples. Point out ambiguities (limits, rounding, exceptions). Show them to the developer and continue only after their confirmation; then move on to the next document.

4. After the confirmation, write the scenarios in the document and implement the steps. When you finish, SpecMD runs the scenarios and reports what is missing or failing.

5. If a scenario fails because the code does something else, that is a divergence between documentation and code. Do not fix it on your own: show the developer what the documentation says and what the code does, and ask which one holds.

To know what is still missing, in any session, run the command from step 1 again: the progress is the state of the documentation and of `.specmdignore` itself. Tagging scenarios `@wip` is the developer's decision.
