# SpecMD requirements and scenarios

**Status:** requirements of the direction defined in [D-021](decisions.md) (23/10/2026). SpecMD helps the agent keep the canonical documentation and the software aligned; it does not audit or approve. Requirements marked as **proposal** are not implemented yet; the [implementation status](implementation-status.md) distinguishes what exists.

The `SMD-REQ-*` and `SMD-SCN-*` IDs are stable. Requirements of the previous design (signed acceptance, authority, browser review, protected gate) were removed by D-021 and remain in the Git history.

## SMD-REQ-001 — Canonical Markdown and runs without `.feature`

Requirements and scenarios live in the same Markdown, which is the canonical source of the business rules. The run reads the scenarios from the Markdown and hands them to the engine in memory, without requiring `.feature` files in the project or generating them temporarily.

```gherkin
Feature: Documentation as the canonical source

  @SMD-REQ-001 @SMD-SCN-101
  Scenario: Run scenarios written in the Markdown
    Given a document with a requirement and its Gherkin scenario
    When the project's scenarios are run
    Then the result points to the path and the line of the scenario in the Markdown
    And no .feature file is created
```

## SMD-REQ-002 — Document discovery

Any Markdown in the project enters the analysis, including new files not yet versioned. Common project files (README, CHANGELOG, LICENSE, agent instructions) are left out by default. Other documents that do not describe system behavior (setup guides, notes) are left out by the optional `.specmdignore` at the root, with `.gitignore`-style patterns. The agent adds entries when it is clear and asks the developer when in doubt.

```gherkin
Feature: Document discovery

  @SMD-REQ-002 @SMD-SCN-102
  Scenario: New document enters the analysis
    Given a project with SpecMD active
    When the agent creates a Markdown file that is not versioned
    Then the document appears in the documentation analysis

  @SMD-REQ-002 @SMD-SCN-103
  Scenario: Reference document does not require scenarios
    Given a setup guide listed in .specmdignore
    When the documentation is analyzed
    Then the guide does not produce a scenario gap
```

## SMD-REQ-021 — Feedback on documentation without scenarios

After any work on Markdown, the agent receives the gaps of the changed document: requirement without a scenario, behavioral document without a Gherkin block, invalid Gherkin or duplicate IDs. The feedback guides the agent to confirm the requirements with the developer and write the scenarios, to add the document to `.specmdignore` when it does not describe behavior, or to ask the developer when in doubt.

```gherkin
Feature: Documentation without scenarios

  @SMD-REQ-021 @SMD-SCN-104
  Scenario: Requirement without a scenario right after the edit
    Given the agent wrote a requirement without a scenario
    When the edit tool finishes
    Then the agent receives the requirement and the line that need a scenario
    And the guidance to confirm the behavior with the developer

  @SMD-REQ-021 @SMD-SCN-105
  Scenario: Gap reminded once on finishing
    Given the documentation still has a requirement without a scenario
    When the agent tries to finish
    Then the agent receives the gap once
    And it can finish if it tries again without changes
```

## SMD-REQ-022 — New scenarios wait for the developer

Scenarios that are new or changed since the developer's last message may not have been seen by them. The agent is guided to show them and ask for confirmation before implementing. When only the documentation changed, the scenarios are not run on finishing and the developer sees a notice that there are scenarios awaiting their confirmation. When the code also changed, the scenarios are run (see SMD-REQ-023) and the feedback reminds the agent to confirm them, in case it has not done so yet. The confirmation is a message from the developer, without a signature or formal record; marking scenarios as `@wip` is also the developer's decision.

```gherkin
Feature: Developer confirmation

  @SMD-REQ-022 @SMD-SCN-106
  Scenario: New documentation awaits confirmation
    Given the agent wrote a new scenario without changing the code
    When the agent finishes
    Then the scenarios are not run
    And the developer is notified that there are scenarios awaiting their confirmation

  @SMD-REQ-022 @SMD-SCN-117
  Scenario: Scenario written together with the code is verified
    Given the developer confirmed in the chat the scenarios proposed by the agent
    When the agent writes the scenarios and the code in the next turn and finishes
    Then the scenarios are run
    And the feedback is a reminder to confirm with the developer the scenarios that changed in the turn

  @SMD-REQ-022 @SMD-SCN-107
  Scenario: A developer message marks the scenarios as seen
    Given the developer replied after seeing the scenarios
    When the agent changes the code and finishes
    Then the scenarios are run
```

## SMD-REQ-023 — Run after a code change and actionable feedback

When files that are not Markdown have changed since the last run, finishing runs the scenarios affected by the change (see SMD-REQ-027), including the ones written in the same turn. Each scenario that does not pass goes back to the agent with the path, the line, the step, the error message and, for steps without an implementation, a snippet ready to start from. Without a code change in the session, no run is required.

```gherkin
Feature: Run after a code change

  @SMD-REQ-023 @SMD-SCN-108
  Scenario: Code that contradicts the documentation
    Given confirmed scenarios that used to pass
    When the agent changes the code and a scenario starts failing
    Then the agent receives the scenario, the step and the error message

  @SMD-REQ-023 @SMD-SCN-109
  Scenario: Step without an implementation
    Given a confirmed scenario with a step without an implementation
    When the agent finishes after changing the code
    Then the agent receives the step and an implementation snippet to start from

  @SMD-REQ-023 @SMD-SCN-110
  Scenario: Conversation without a code change
    Given a session in which the code did not change
    When the agent finishes
    Then no scenario is run
```

## SMD-REQ-027 — Only the scenarios affected by the change

In large projects, running every scenario on each finish takes minutes. On finishing, the plugin runs only the scenarios the change can affect: those that executed a changed function, those that read a changed file, the new or changed ones, the ones that were failing and the ones that never ran. The feedback says how many scenarios were left out. It runs all of them when the module level of a Python file used by the scenarios changes (imports, constants, decorators, signatures), when the steps or the configuration change, and when there is no coverage: Java, Go, Python earlier than 3.12 or a project without Git. Scenarios that start processes or open network connections are always run. Dependencies outside the Python code, such as environment variables or database state, may escape the selection; `specmd run` runs all the scenarios and serves as a safety net in CI, and `specmd run --affected` applies the same selection as finishing. Origin: [D-022](decisions.md), confirmed by the user on 24/10/2026.

```gherkin
Feature: Running only the affected scenarios

  @SMD-REQ-027 @SMD-SCN-118
  Scenario: A change in a function runs only the scenarios that use it
    Given verified scenarios of two rules implemented in different functions
    When the agent changes the body of one of the functions and finishes
    Then only the scenarios that executed that function are run
    And the feedback reports how many scenarios were left out

  @SMD-REQ-027 @SMD-SCN-119
  Scenario: A module-level change runs all of them
    Given verified scenarios
    When the agent changes a constant, an import or the signature of a function and finishes
    Then all the scenarios are run

  @SMD-REQ-027 @SMD-SCN-120
  Scenario: A scenario that was failing is run again
    Given a scenario that failed in the last run
    When the agent changes a file that this scenario does not execute and finishes
    Then the scenario that was failing is run again

  @SMD-REQ-027 @SMD-SCN-121
  Scenario: Without coverage, all of them run
    Given a Go project with the Godog bridge configured
    When the agent changes the code and finishes
    Then all the scenarios are run

  @SMD-REQ-027 @SMD-SCN-122
  Scenario: The CLI runs all of them
    Given verified scenarios
    When the developer runs specmd run
    Then all the scenarios are run
```

## SMD-REQ-028 — Protected confirmed scenarios

The scenarios as of the developer's last message are the baseline for comparison. When the agent removes one of them, changes a `Then` (the expected value), changes a `Given` or `When`, marks one with `@wip` or removes a requirement, it receives the exact diff right after the edit, and the developer sees the same summary when the agent finishes, even if everything passes. The notice is informative, including when the developer themselves asked for the change. Finishing is sent back to the agent, once, only on the strong signal of adjusting the test to the code: the scenario was failing in the last run and the agent changed its expected value and the code in the same turn. Origin: [D-023](decisions.md), confirmed by the user on 24/10/2026.

```gherkin
Feature: Protected confirmed scenarios

  @SMD-REQ-028 @SMD-SCN-123
  Scenario: Changed expected value shows up for the agent and for the developer
    Given a scenario that existed at the developer's last message
    When the agent changes the expected value in the Then
    Then the agent receives the scenario with the previous and the new value right after the edit
    And the developer sees the same summary when the agent finishes, even with everything passing

  @SMD-REQ-028 @SMD-SCN-124
  Scenario: Removed scenario, scenario marked as @wip or removed requirement
    Given scenarios and requirements that existed at the developer's last message
    When the agent removes a scenario, marks another one with @wip and removes a requirement
    Then the agent and the developer see the removed scenario, the marked scenario and the removed requirement

  @SMD-REQ-028 @SMD-SCN-125
  Scenario: Expectation adjusted to make the code pass goes back to the agent
    Given a scenario that failed in the last run
    When the agent changes its expected value and the code in the same turn and finishes
    Then the agent receives, once, the request to restore the scenario if the developer did not ask for the change

  @SMD-REQ-028 @SMD-SCN-126
  Scenario: A change in a scenario that was passing is only reported
    Given a scenario that was passing
    When the agent changes its expected value and the code and finishes
    Then the developer sees the summary of the change
    And the agent finishes without being sent back again
```

## SMD-REQ-029 — Ignored document that gains a rule

Ignored documents, whether through `.specmdignore` or the default patterns, are still read lightly. When one of them changes and starts having a requirement heading (`…-REQ-…`), a Gherkin block or a heading with a Gherkin keyword (MDG), the agent is notified right after the edit, with the two ways out: move the rule to a behavior document or take the document out of `.specmdignore` (or use `!path`), asking the developer when in doubt. A document that already had these elements does not produce a notice when another part of it changes. It is only a notice: finishing is not blocked because of it. Origin: [D-024](decisions.md), confirmed by the user on 24/10/2026.

```gherkin
Feature: Ignored document that gains a rule

  @SMD-REQ-029 @SMD-SCN-127
  Scenario: Requirement written in an ignored document
    Given a setup guide listed in .specmdignore
    When the agent adds a requirement heading or a Gherkin block to the guide
    Then the agent is notified that the document is ignored
    And receives the ways out: move the rule or take the document out of .specmdignore, asking the developer when in doubt

  @SMD-REQ-029 @SMD-SCN-128
  Scenario: Old example does not produce a notice
    Given an ignored README that always had a Gherkin example
    When the agent edits another part of the README
    Then no notice is given

  @SMD-REQ-029 @SMD-SCN-129
  Scenario: Notice does not block finishing
    Given an ignored document that gained a requirement
    When the agent finishes
    Then finishing is not blocked because of it
```

## SMD-REQ-030 — Adoption in a legacy project

In a project that already has documentation, `/specmd:adopt` (or `specmd adopt`) lists all the analyzed documents that do not have scenarios yet or have requirements without a scenario, in path order, with no guess about which ones seem to have rules. The documents ignored by default and the ones the team already put in `.specmdignore` are left out. The agent presents the list to the developer, who says which ones do not describe behavior; the agent writes those to `.specmdignore`. Then the agent handles one document at a time: it proposes requirements and scenarios, asks for confirmation and follows the normal cycle of steps, run and feedback. There is no adoption-specific state: running the list again shows what is missing. When a scenario that never passed fails and the product code it executes was not changed in the session, the feedback reminds that, if the code already existed and does something else, it is a divergence between documentation and code, and the agent asks the developer which of the two holds before changing either one. Without coverage (Java, Go, Python earlier than 3.12), the guidance applies to scenarios that are new or changed since the developer's last message. When a scenario that already existed at the developer's last message breaks because the agent changed the code it executes, it is not a divergence: the feedback guides the agent to update the scenario if the developer confirmed the new rule, or to adjust the code. The steps (`tests/steps`, `environment.py`) do not count as product code. Fix approved by the user on 24/10/2026, after the [pilot](../research/pilot/README.md). Marking `@wip` is still the developer's decision. Origin: [D-025](decisions.md), confirmed by the user on 24/10/2026.

```gherkin
Feature: Adoption in a legacy project

  @SMD-REQ-030 @SMD-SCN-130
  Scenario: List of documents for adoption
    Given a project with documents without scenarios, a README and a team .specmdignore
    When the developer asks for the adoption
    Then the agent receives all the documents without scenarios in path order
    And the list includes neither the documents ignored by default nor the ones in .specmdignore

  @SMD-REQ-030 @SMD-SCN-131
  Scenario: The developer chooses what to ignore
    Given the list of documents for adoption
    When the developer says that a setup guide does not describe behavior
    Then the agent adds the guide to .specmdignore
    And the guide leaves the list

  @SMD-REQ-030 @SMD-SCN-132
  Scenario: One document at a time
    Given behavior documents without scenarios
    When the agent conducts the adoption
    Then it proposes requirements and scenarios for one document and asks for confirmation before the next one

  @SMD-REQ-030 @SMD-SCN-133
  Scenario: Divergence between documentation and code
    Given a confirmed scenario that never passed and fails because the code, which the agent did not change, does something else
    When the agent receives the failure
    Then the feedback guides the agent to ask the developer which of the two holds, without fixing it alone

  @SMD-REQ-030 @SMD-SCN-138
  Scenario: An existing scenario broken by the agent's change is not a divergence
    Given a scenario that already existed and never ran
    When the agent changes the code it executes and the scenario fails
    Then the feedback does not suggest a divergence
    And it guides the agent to update the scenario if the developer confirmed the new rule, or to adjust the code
```

## SMD-REQ-031 — Markdown with Gherkin (`.feature.md`)

`*.feature.md` files are read in Cucumber's official Markdown with Gherkin (MDG) format: keywords as Markdown headings, steps as list items, GFM tables indented by 2 to 5 spaces, tags in backticks on the line above the keyword, and free prose between them. SpecMD converts the file into Gherkin in memory, line by line, and the engines run it without a `.feature` file. In a `.feature.md`, a fenced block right after a step is the step's text (Doc String); the other Markdown files keep using fenced `gherkin` blocks. MDG has no `# language:`: the language comes from `gherkin_language` in `specmd.toml`, and a file whose keywords are not in the configured language produces a warning that says so. Headings with a requirement ID link the scenarios below them, including the heading of a `Rule` (`## Rule: PAY-REQ-001 — Refund`). Origin: [D-026](decisions.md), confirmed by the user on 24/10/2026.

```gherkin
Feature: Markdown with Gherkin

  @SMD-REQ-031 @SMD-SCN-134
  Scenario: MDG document run with its origin in the Markdown
    Given a .feature.md file with prose, scenario headings and steps as list items
    And gherkin_language set in specmd.toml
    When the scenarios are run
    Then each result points to the line of the scenario in the .feature.md file
    And no .feature file is created

  @SMD-REQ-031 @SMD-SCN-135
  Scenario: A Rule with an ID becomes a requirement
    Given a heading "## Rule: PAY-REQ-001 — Refund" in a .feature.md file
    When the documentation is analyzed
    Then the rule's scenarios are linked to PAY-REQ-001

  @SMD-REQ-031 @SMD-SCN-136
  Scenario: A fenced block is a step argument
    Given a step followed by a fenced block in a .feature.md file
    When the scenario is run
    Then the step receives the content of the block as text

  @SMD-REQ-031 @SMD-SCN-137
  Scenario: A missing language is pointed out
    Given a .feature.md file in Portuguese without gherkin_language configured
    When the documentation is analyzed
    Then the agent is notified that in MDG the language comes from specmd.toml
```

## SMD-REQ-024 — Feedback that does not lock up the session

The plugin never ends the agent's session. The same feedback repeated without change, or the limit of four consecutive blocks, lets the agent finish; the count restarts with each developer message. Internal plugin errors become warnings.

```gherkin
Feature: Bounded feedback

  @SMD-REQ-024 @SMD-SCN-111
  Scenario: The same failure does not hold the agent back
    Given the agent received a failure on finishing
    When it tries to finish again with the same failure
    Then it can finish and the developer sees a summary

  @SMD-REQ-024 @SMD-SCN-112
  Scenario: An internal error becomes a warning
    Given the check fails because of an internal error
    When any hook runs
    Then the session continues and a warning is shown
```

## SMD-REQ-025 — Context at session start

When a session opens, the agent receives a summary of the canonical documentation (documents with scenarios, gaps, last run) and the working conventions: where to write requirements and scenarios, when to ask the developer for confirmation, what to do with documents that do not describe behavior, and that, when the existing code contradicts the documentation, the agent does not fix either of the two alone and asks the developer which one holds (approved by the user on 25/10/2026, after the second round of the [pilot](../research/pilot/README.md)).

```gherkin
Feature: Initial context

  @SMD-REQ-025 @SMD-SCN-113
  Scenario: Summary when the session opens
    Given a project with documentation and scenarios
    When an agent session starts
    Then the agent receives the number of documents and scenarios
    And the SpecMD working conventions

  @SMD-REQ-025 @SMD-SCN-139
  Scenario: A divergence from the existing code becomes a question to the developer
    Given a project with SpecMD active
    When an agent session starts
    Then the conventions guide the agent not to fix the code or the documentation alone when one contradicts the other
    And to ask the developer which one holds
```

## SMD-REQ-032 — Message language

SpecMD's messages to the agent and to the developer (hooks, CLI and errors) are in English by default. A project that sets `language = "pt"` in `specmd.toml` gets them in Portuguese. This setting does not change the Gherkin language, which comes from `# language:` or from `gherkin_language` (decided on 27/10/2026, [D-029](decisions.md)).

```gherkin
Feature: Message language

  @SMD-REQ-032 @SMD-SCN-141
  Scenario: English by default
    Given a project with SpecMD active and no language in specmd.toml
    When an agent session starts
    Then the summary and the conventions are in English

  @SMD-REQ-032 @SMD-SCN-142
  Scenario: Portuguese on request
    Given a specmd.toml with language = "pt"
    When an agent session starts and a code change makes a scenario fail
    Then the summary, the conventions and the failure feedback are in Portuguese
```

## SMD-REQ-015 — Rebuildable local state

The plugin keeps only local observations in `.specmd/local/`: the last run, the scenarios seen by the developer, the count of blocks and a cache of the document analysis. Deleting this state is safe; it is rebuilt in the next session.

```gherkin
Feature: Local state

  @SMD-REQ-015 @SMD-SCN-114
  Scenario: Corrupted state is ignored
    Given an invalid local state file
    When the documentation is analyzed
    Then the analysis works as in a project without state
```

## SMD-REQ-026 — Per-repository installation

Installing the plugin at project or local scope already activates SpecMD in the repository, with the defaults; `specmd.toml` and `.specmdignore` are optional. `specmd init` (or `/specmd:init`) declares the SpecMD marketplace and enables the plugin in the project's shared configuration, so that each person on the team only needs to accept trust for the folder. In Codex, where the plugin is installed per user, the same command enables the plugin in the project's `.codex/config.toml`, and SpecMD is active in the trusted projects that enable it there, without `specmd.toml` (approved by the user on 27/10/2026). The dependencies come with the plugin; the machine needs Python 3.11 or later.

```gherkin
Feature: Per-repository installation

  @SMD-REQ-026 @SMD-SCN-115
  Scenario: Plugin loaded when the repository is opened
    Given a repository prepared by the init command
    When a developer opens the agent in the folder and trusts it
    Then the SpecMD plugin is loaded without manual installation

  @SMD-REQ-026 @SMD-SCN-140
  Scenario: The project enables SpecMD in Codex
    Given a repository prepared by the init command, without specmd.toml
    And the SpecMD plugin installed in the developer's Codex
    When the developer opens Codex in the trusted folder
    Then SpecMD is active in the project
```

## SMD-REQ-020 — Runs in Java, Python and Go

The scenarios run with existing engines: Behave in Python, Cucumber-JVM in Java and Godog in Go, each one receiving the Gherkin in memory with its origin in the Markdown. Each bridge declares the Gherkin subset it supports.

```gherkin
Feature: Engines per language

  @SMD-REQ-020 @SMD-SCN-116
  Scenario: A bridge runs a scenario with its origin in the Markdown
    Given a Go project with the Godog bridge configured
    When the scenarios are run
    Then each result points to the path and the line of the scenario in the Markdown
```
