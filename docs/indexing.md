# Inventory and incremental analysis

> **Historical, predating [D-021](decisions.md).** This document describes the design with signed acceptance, authority, trust and implementation blocking, removed on 23/10/2026. For the current product, see [product](product.md) and [implementation status](implementation-status.md).

> Status: deterministic inventory and local snapshots implemented experimentally. The cache is advisory and the source is always reanalysed. Trustworthy parsing reuse, incremental semantic analysis and performance gains have not been demonstrated yet. See the [implementation status](implementation-status.md).

SpecMD discovers the project's documents and produces an inventory of paths, content and declared relations. The intended evolution is to avoid unnecessary reinterpretation; the current increment prioritizes rebuilding and checking the source before any decision.

The goal is to save reading, parsing, model calls and check runs, while preserving the detection of new documents and of changes that require review.

## Three separate responsibilities

| Responsibility | Content | Authority |
| --- | --- | --- |
| Inventory | Paths, observed content, declared classification and known relations. | Describes the state found; can be rebuilt. |
| Acceptance | Authenticated identity, scope and exact version approved by the human. | Comes from the protected approval mechanism. |
| Analysis cache | Currently, snapshots of the extracted documents and diagnostics with source/parser identity. | Advisory: not used to skip validating the source nor to grant acceptance. |

An analysed document may remain unapproved. An approved document may need a new analysis because a dependency or policy changed. Deleting or editing the local index cannot turn a gap into an approval.

The trust contracts are detailed in Acceptance and trust (removed by [D-021](decisions.md)); the overall composition is in [Architecture](architecture.md).

## Discovery and scope

The scanner is only activated when a `specmd.toml` exists at the root. The schema 1 configuration preserves the simple preflight and accepts only `schema = 1`. The schema 2 configuration requires `project_id`, accepts an optional `repository_id` and adds runners, traceability and evidence policy. Each document's front matter remains `specmd.schema: 1`; these are distinct schemas, described in [Documentation format](format.md).

In the current increment, discovery uses a sorted `os.walk`, considers `.md` and `.markdown` with a case-insensitive extension and includes local files not yet added to Git. There are no exclusions configurable by the agent. Directories with fixed names are pruned:

```text
.git .hg .svn .venv venv node_modules target __pycache__ .specmd
.pytest_cache .mypy_cache .ruff_cache build dist
```

Symbolic links to documents and directories within the scope are refused and not followed. These prunings are part of the implementation and must be included in the verifier's review; they are not a dynamic exclusion policy already approved by a human.

The inventory must consider:

- Documents versioned in Git.
- New local documents, including before they are added to Git.
- Staged and unstaged changes during the session.
- Removals and renames.
- Changes to the discovery policy and to the exclusions.

A configurable exclusion policy with path, justification, versioning and acceptance is a design evolution. It is not available as a mechanism to remove files from analysis in this increment.

`.gitignore` serves the Git flow and does not replace SpecMD's discovery. The project's own Markdown in non-pruned directories is found even when it is not versioned or has been ignored by Git. Ignoring a document in Git does not grant a contractual exemption.

The manifest paths are relative and use the `/` separator. The path takes part in the digest: removing or renaming a document changes the identity of the set, even if its bytes stay the same. There is no promise of equivalence between paths that differ only in case on different file systems.

## Classification and analysis cost

| Situation | Monitoring | Analysis required |
| --- | --- | --- |
| Behavioural, accepted and unchanged | Check identity and relevant relations. | The current scanner redoes the parsing; trustworthy reuse is an evolution. |
| Behavioural, changed | Record the new version and invalidate the applicable acceptance. | Reanalyse the affected obligations, scenarios and relations. |
| Informational with accepted exemption, unchanged | Keep verifying the content identity. | Does not require Gherkin; the scanner still checks metadata and explicit content. No AI semantic analysis is implemented. |
| Informational, changed | Make the new version pending. | Reassess classification and justification; the text may have acquired behaviour rules. |
| New or unclassified | Add to the inventory as pending. | Propose a classification and submit the decision to the user. |
| Out of scope by the current fixed prunings | The policy is in the verifier's version. | Do not traverse the pruned content. Accepted configurable exclusions are still future design. |

The Gherkin exemption is not the same as exclusion from the inventory. An accepted informational guide remains monitored, because a future edit may introduce a business rule.

Mixed documents require links for their behavioural parts. The classification of the whole file cannot hide an obligation contained in a section. The format of these declarations is proposed in [Documentation format](format.md).

A `reference` document with an explicit requirement heading or a Gherkin fence produces a classification conflict and a structural block. Acceptance of the exemption is part of the versioned review and signing flow, not a self-assigned property in the index.

## Inventory entry

An entry implemented by the scanner contains path, SHA-256, ID, classification, requirements with lines and scenarios with IDs, blocks, lines, links and step count. That count does not indicate a run. In schema 2, an Outline generates instances `<base_id>:row:<example>:<data line>`; each one keeps its base identity and the declaration line, plus the concrete table line. Requirements inherited through Rule and Examples remain explicit in the records.

The lifecycle associates acceptances and evidence separately. The evolution of the inventory aims to also make it possible to retrieve:

- Stable document identifier and observed path.
- Hash of the observed content and reference to the source snapshot.
- Declared classification, accepted version and review status.
- Identifiers of the requirements and scenarios found.
- References to other documents, shared rules and known components.
- Versions of policy, parser and analysers used in the derived results.
- Related diagnostics and evidence, with their validity inputs.

References to acceptances are resolved in the trusted mechanism; a local field such as `approved: true` is not proof. A relation inferred by AI must be distinguished from a declared or confirmed relation. The absence of a relation in the index does not demonstrate absence of impact.

## Content identity

The contractual identity follows the rule described in Acceptance and trust (removed by [D-021](decisions.md)). The implementation computes SHA-256 of the bytes actually read from the checkout, without normalizing line endings or reinterpreting the meaning of the Markdown. The scanner manifest has `schema: 1`, `config_sha256` and the sorted list of `path`/`sha256` pairs, serialized as UTF-8 JSON with sorted keys and compact separators.

In schema 2, the workflow also includes `traceability_sha256`, bound to the map at `.specmd/traceability.json` by default. The `.specmd` folder is outside Markdown discovery, but that map is read explicitly by the lifecycle: changing it changes the contractual version and invalidates the corresponding evidence. The path can be set in `traceability.map`; the strict policy requires code/test links to known requirements and scenarios.

`repository_id` makes it possible to bind receipts to a logical identity that is stable across checkouts, without using the absolute path as the main identity. This field does not prove ownership of the repository nor make a cache trustworthy.

Modification date, file size and system events can reduce work during a session, but they are hints. The protected gate needs to check content identities on the effective snapshot, without relying exclusively on that metadata.

A rename changes the path and possibly the scope. Even a future content-based parsing reuse will not be able to reuse the acceptance automatically.

## Implemented cache and its limits

`inspect_project(root)` does not write a cache. The explicit option `use_cache=True` enables snapshots in `.specmd/cache`. The current key includes the document's SHA-256, path, configuration schema and a fingerprint of the scanner/Behave/MarkdownIt/PyYAML version.

These files can be edited locally by the agent. For that reason, the scanner **always reads and reanalyses the source** before deciding. Tampered content or invalid JSON in the cache does not remove diagnostics, does not grant approval and does not mark scenarios as run. The snapshot is updated when it differs from the rebuilt analysis; cache failures do not change the inspection result. Symbolic cache directories are not used for writing.

This mechanism provides derived records for incremental evolution, but **does not yet deliver the gain of avoiding parsing**. No AI semantic cache, inferred dependencies, persistent watcher or automatic cleanup of old entries is implemented as an optimization.

## Planned invalidation for trustworthy reuse

Each type of analysis must declare its inputs. A conceptual key may include:

```text
content + relevant context + policy + analyser + dependencies
```

This does not fix a serialization schema. The implementation must document which inputs each cache uses and produce reproducible results for the deterministic checks.

| Change | Results to invalidate |
| --- | --- |
| Document text | Parsing and content-dependent analyses; acceptance of the new version becomes pending. |
| Path or scope | Selection and context-sensitive analyses; reassess the acceptance binding. |
| Referenced document | Analyses that used that reference. |
| Classification or exclusion | Applicability decisions and affected results. |
| Policy or analyser version | Results computed under the previous version, according to their inputs. |
| Code, steps, fixtures or run configuration | Affected test evidence, even if the documents are intact. |

When trustworthy reuse exists, invalidating the whole semantic cache after a policy change is an acceptable conservative choice. Later optimizations need to preserve the same decision as full processing; the current version avoids this risk by reanalysing the source.

The document parsing cache and the test run cache are distinct. An unchanged document does not make current a test result run against another version of the code, environment or runner.

## Intended incremental cycle

The flow below describes the desired evolution, not an optimization already demonstrated:

1. Discover differences since the last observed state.
2. Update the inventory, removing obsolete entries and adding new files.
3. Recompute the necessary identities.
4. Locate results affected by content, context or dependencies.
5. Reuse only results whose inputs remain valid.
6. Run new analyses and present gaps to the agent adapter.

Watchers are useful triggers, but events can be lost. A write by a shell, another tool or another agent can also modify the project. For that reason, startup, task closing and CI require reconciliation with the real state of the scope.

The current implementation reconciles the inventory and redoes the structural parsing. Before extraction for running, `extract_features` checks a fresh inspection, rejects an earlier manifest that has become outdated and delivers the blocks in memory with padded lines to preserve the origin in the `.md`.

## Determinism and AI assistance

These are deterministic checks: discovering files by policy, comparing hashes, validating references and IDs, checking Gherkin syntax and relating evidence to the declared snapshots.

These are planned heuristic analyses: suggesting a classification, finding possible requirements in prose, pointing out gaps between text and scenarios and suggesting impact relations. The current scanner does not run a model to make these inferences. When available, such suggestions will support the review, without automatically establishing the completeness of the contract or granting an exemption.

Markdown remains the canonical source. Parsing and indexing must not require `.feature` files, including as a mandatory temporary step of the run. The index may keep a derived representation of the Gherkin blocks in memory or in a rebuildable cache, keeping the origin in the `.md`.

## Measurement and evolution

A future optimization must compare full and incremental processing over the same snapshots. The approve/block decision needs to be equivalent for the deterministic checks. The current tests verify that a tampered cache does not change the decision and that new, changed, removed or renamed content changes the inventory when applicable; they do not constitute a performance benchmark.

Measure discovery, reading and parsing time, reuse rate, avoided model calls, reconciliation duration and divergences between the two forms of processing. Test cases and experiments are in the [Validation plan](validation-plan.md).

The format of a trustworthy reuse and the need for a local database must be chosen after observing volume, concurrency and rebuild cost. They are derived data; the contractual history and the acceptances need to remain retrievable without this cache. The [implementation status](implementation-status.md) records the operational limits of the lifecycle and of the current verifiers.
