# SpecMD — product

**Status:** direction defined in [D-021](decisions.md) (23/10/2026). The [implementation status](implementation-status.md) separates what already exists from what is planned.

## Problem

In development with AI agents, the developer's intent, the documentation, the code and the tests diverge easily. The agent forgets a condition, interprets a rule differently or invents a rule nobody asked for and writes tests that protect it. When the tests live in separate `.feature` files, the divergence gets one more place to happen: the `.feature` changes and the documentation does not, or the requirement changes and the scenarios fall behind.

## Proposal

SpecMD is a plugin for coding agents (Claude Code and Codex), installed in the repository, that keeps the canonical documentation and the software aligned through collaboration between the agent and the developer.

- The Markdown documentation, with embedded Gherkin scenarios, is the canonical source of the business rules. Requirement and acceptance test live in the same file.
- The plugin runs deterministic checks at key moments and sends objective feedback back to the agent, encouraging it to iterate and check before moving on.
- The one who defines what is right is the developer, through the documentation they confirmed in the conversation. The plugin neither approves nor audits; it verifies whether documentation and code agree.

## Flow

1. The developer talks to the agent, and the agent writes the documentation in the repository.
2. Any work on Markdown triggers the analysis. A document without scenarios goes back to the agent, which confirms the requirements with the developer and writes the scenarios, adds the document to `.specmdignore` when it does not describe behavior, or asks the developer when in doubt.
3. The agent shows the scenarios and asks whether everything is right. The confirmation is the developer's reply.
4. The agent implements. On finishing, the scenarios are run; the ones without an implementation or failing go back to the agent with the step and the error, until everything is green.

## Limits

- The scenarios verify what they describe. They do not prove that the documentation covers the developer's whole intent nor that the assertions of the steps are strong; that remains with human review, usually in the PR.
- The plugin helps a well-intentioned agent avoid mistakes; it does not stop an agent determined to get around it.
- Hooks are not equivalent across hosts; each integration is verified per platform and version.

## Prior art

Executable documentation, traceability and gates already exist in other tools ([research](positioning.md)). The value to demonstrate is the integrated experience: the documentation as the single source and feedback at the right moment during the agent's work.
