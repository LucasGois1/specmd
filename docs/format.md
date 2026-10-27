# Documentation format

The documentation is plain Markdown. SpecMD reads the ```gherkin blocks of each document and runs them in memory; there is no `.feature` file to maintain.

## Which documents are included

Every Markdown file in the project (`.md` and `.markdown`), including new files not yet versioned, except:

- files ignored by Git;
- dependency and build directories (`node_modules`, `.venv`, `build`, `dist` and similar) and the `.specmd/` state;
- project files that rarely describe behaviour: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `LICENSE*`, `NOTICE*`, `AUTHORS*`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.github/`, `.claude/` and `.codex/`;
- whatever matches `.specmdignore` at the root, which is optional.

A `!README.md` line in `.specmdignore` brings back a file ignored by default. `.specmdignore` uses `.gitignore`-style patterns: comments with `#`, `!` to negate, a trailing `/` for directories, a leading or middle `/` to anchor at the root, `*`, `?` and `**`. It lists the Markdown that does not describe system behaviour:

```gitignore
README.md
CHANGELOG.md
docs/setup/
notes/**/*.md
```

The agent creates the file and adds entries when it is clear that the document does not describe behaviour, and asks the developer when in doubt.

## What a document needs

At least one ```gherkin block with scenarios. Front matter is optional and ignored.

Requirements with an ID are optional and recommended. A heading that starts with an ID ending in `-REQ-…` declares the requirement; the prefix is free:

````markdown
## PAY-REQ-001 — Refund within 7 days

A payment can be refunded within 7 calendar days.

```gherkin
Feature: Refund

  Scenario: Refund on the sixth day
    Given a payment made 6 days ago
    When the customer requests the refund
    Then the refund should be approved
```
````

## Markdown with Gherkin (`.feature.md`)

A `*.feature.md` file is read in Cucumber's official [Markdown with Gherkin](https://github.com/cucumber/gherkin/blob/main/MARKDOWN_WITH_GHERKIN.md) format, instead of fenced blocks:

- keywords are Markdown headings (`# Feature:`, `## Rule:`, `### Scenario:`, `### Scenario Outline:`, `#### Examples:`, `## Background:`);
- steps are list items (`* Given …` or `- When …`);
- tables are GFM tables indented by 2 to 5 spaces;
- a fenced block right after a step is the step's text (Doc String); elsewhere, it is prose;
- tags go between backticks on the line above the keyword (`` `@fast` ``);
- any other line is prose. The file is one feature; without a `Feature` heading, the first line gives the name.

MDG has no `# language:`: the language comes from `gherkin_language` in `specmd.toml`. Headings with a requirement ID work as in the other documents, including the `Rule` one:

````markdown
# Feature: Refunds

A payment can be refunded within 7 calendar days.

## Rule: PAY-REQ-001 — Refund within 7 days

### Scenario: Refund on the sixth day
* Given a payment made 6 days ago
* When the customer requests the refund
* Then the refund should be approved
````

## Link between scenario and requirement

- A scenario is linked to the requirement of the nearest heading above its block. Subheadings inside the section (for example `### Scenarios`) keep the link.
- A `@…-REQ-…` tag on the scenario, the rule or the feature replaces the link by position.
- Scenarios before any requirement belong to the document as a whole.
- A requirement without a scenario is a gap, and so is a tag that points to a nonexistent requirement.

## Scenario identity

- Without a tag, the ID is `path::scenario name`. Repeated names in the same document get `#2`, `#3` and so on.
- A `@…-SCN-…` tag defines a stable ID, which must be unique in the project. A scenario accepts at most one.
- Each `Examples` row of a `Scenario Outline` becomes an instance `ID:row:<example>:<line>`.

## Language and work-in-progress scenarios

- `# language: pt` in the block sets the Gherkin language (here, Portuguese); `gherkin_language = "pt"` in `specmd.toml` sets the project default.
- `language = "pt"` in `specmd.toml` shows SpecMD's own messages in Portuguese; the default is English. It does not change the Gherkin language.
- Scenarios with a tag from `wip_tags` (default `@wip`) appear in the documentation but are neither run nor required. Marking `@wip` is the developer's decision; the agent is instructed not to mark it on its own.

## specmd.toml

Optional. Without it the defaults below apply; SpecMD is active in a repository when the plugin is enabled in the project or local scope (`enabledPlugins` in `.claude/settings.json` or `.claude/settings.local.json`) or when a `specmd.toml` exists.

```toml
language = "en"             # SpecMD's messages: "en" (default) or "pt"
gherkin_language = "pt"
wip_tags = ["wip"]

[run]
on_stop = true      # run the scenarios on completion, when the code changed
timeout = 120

[[runners]]
id = "python"
language = "python"
steps = "tests/steps"            # environment.py lives in the parent directory
python = ".venv/bin/python"      # optional
```

- Without `[[runners]]`, the first existing directory among `tests/steps`, `features/steps` and `steps` becomes a Python runner.
- The Python runner uses, in this order: the runner's `python`, `$VIRTUAL_ENV`, the project's `.venv` or `venv`, as long as it can import `behave`. If none works, it uses the plugin's interpreter.
- With several runners, each scenario goes to the first one whose `paths` match the document.
- Java and Go use `command` with the bridge; see [adapters](../adapters/README.md).
- Keys from the earlier design (`project_id`, `repository_id`, `traceability`, `evidence`) are accepted and ignored.
