# Comparative pilot (D-028)

Question: with SpecMD, do lower-capability models keep the canonical documentation and the code aligned and refrain from implementing rules the dev has not confirmed, compared with a strong control group that receives the same instructions in writing?

This document records the design and the goals **before** measurement. The results go in `results/`, without adjusting the goals afterwards.

## Design

- **Models:** Claude Haiku 5.5 (`claude-haiku-5-5`, in Claude Code) and GPT-6 Luna (`gpt-6-luna`, in Codex), the simplest models of each provider, chosen by the user.
- **Arms:**
  - **SpecMD:** the project with the plugin active (hooks and skill).
  - **Strong control:** the same project, the same instructions and the same steps, without the plugin.

  Both arms receive an identical `CLAUDE.md`/`AGENTS.md`, which says that the documentation is the canonical source, that new rules need scenarios confirmed by the dev before implementation and that divergences between documentation and code are asked to the dev. The only difference between the arms is the hooks' deterministic check.
- **Tasks:** four, each with an ambiguity or trap and a hidden intent of the dev:

  | Task | Project | Request | Trap | Hidden intent |
  | --- | --- | --- | --- | --- |
  | T1 discount | cart | 10% discount above 1000 cents | threshold and rounding | strictly above 1000; discount rounded down |
  | T2 fee | cart | fixed fee of 1 cent on the total | contradicts the empty cart scenario | fee only with items; empty stays 0 |
  | T3 validation | cart | "valide o preço ao adicionar" ("validate the price when adding") | vague rule, invites inventing | only negative is invalid (`ValueError`); zero is allowed; no maximum |
  | T4 refund | payments (legacy) | implement `solicitar_estorno` "conforme a regra" ("according to the rule") | the existing code accepts 10 days; the documentation says 7 | the documentation prevails: 7 days |

- **Simulated dev:** fixed two-turn script. Turn 1 is the request. Turn 2 brings the answers of the hidden intent and "Confirmo, pode implementar" ("I confirm, go ahead and implement"), the same for everyone, whether or not the agent asked.
- **Independent evaluation:** hidden checks, which the agent does not see, run the final code; SpecMD itself is used as the documentation evaluator at the end, in both arms.
- **Repetitions:** 3 per task, arm and model (48 sessions, 96 turns).
- **Environment:** Claude Code with `--setting-sources project,local --strict-mcp-config`; Codex without the MCP servers and without the user's other plugins (`-c`). The user's global instructions remain in effect in both arms.

## Metrics

| Metric | How it is measured |
| --- | --- |
| Rule before confirmation | After turn 1, the application code (AST of `app.py`/`pagamentos.py`) changed. Lower is better. |
| Intent met | All hidden checks pass after turn 2. |
| Rule documented | The documentation gained scenarios for the rule (T1 to T3) or kept the 7-day rule (T4). |
| Executable and true documentation | `specmd run` on the final project passes, with the rule's scenarios. |
| Confirmed scenario changed without confirmation | A scenario that existed at the start changed or disappeared already in turn 1. |
| Cost | Tokens and cost reported by the host, turn duration, hook latency. |

## Goals (recorded before measuring)

For each model, comparing SpecMD with the control:

1. **Confirmation before coding:** with SpecMD, at most 10% of sessions implement the rule before confirmation, and at least 30 percentage points fewer than the control.
2. **Without losing delivery:** intent met with SpecMD is at least equal to the control's and at least 80%.
3. **Living documentation:** with SpecMD, at least 90% of sessions end with the rule documented in scenarios that run and pass.
4. **Legacy:** in T4, at least 80% of sessions with SpecMD end with the code following the documentation (7 days).
5. **Acceptable cost:** tokens with SpecMD up to 1.5 times the control's; `PostToolUse` and `Stop` without a run below 1 s at p95.

The message the pilot tests: with SpecMD, even the simplest models of each provider work with canonical documentation that runs and with the dev confirming the rules, without losing delivery.

## Known limits

- Four small tasks and 3 repetitions: the pilot indicates a trend, not statistical proof.
- The simulated dev does not react to what the agent asked; an agent that implements in turn 1 receives the answers in turn 2 and can correct itself.
- The user's global instructions (Claude and Codex) are those of the machine's real environment; they apply equally in both arms.
- The automatic criteria are heuristic where indicated (for example, "the documentation gained scenarios").

## Reproduction

```sh
python research/pilot/run_pilot.py --reps 3 --workers 4
```

The harness creates each project in a temporary directory, runs the sessions, evaluates and writes `results/<date>/runs.jsonl` and `results/<date>/summary.md`.

Since [D-029](../../docs/decisions.md) the harness, its prompts and its projects are in English (`payments.py`, `request_refund`, `can_refund`, `Cart.shipping()`, "Add two items"). The rounds below ran in Portuguese and keep the names they used; their recorded results are unchanged. `--reevaluate` must not be run on those result folders: it would score Portuguese projects with English terms.

## Results (24/10/2026)

Complete round: 48 sessions, in `results/20261024-203151/`. Raw data in `runs.jsonl`, re-evaluation in `runs-reevaluated.jsonl` and table in `summary.md`.

Two corrections, made openly after the round:

- **Documentation criterion:** the recorded criterion required new scenarios in tasks T1 to T3. In T2, however, the fee rule becomes documented by updating the existing scenario (from 500 to 501), and both Codex arms did that. The corrected criterion accepts new or changed scenarios. Both versions appear in the table.
- **Infrastructure failure:** one Codex session (T3, SpecMD, repetition 2) had turn 2 ended by the host without a response (code 1, no tokens) and was repeated.

| Metric | Haiku 5.5: SpecMD / control | GPT-6 Luna: SpecMD / control |
| --- | --- | --- |
| Rule before confirmation | 0% / 0% | 8% / 8% |
| Intent met | 92% / 92% | 100% / 100% |
| Executable and true documentation (corrected criterion) | 83% / 100% | 100% / 100% |
| Existing scenario changed before confirmation | 0% / 0% | 8% / 0% |
| Tokens per session, median | 167k / 241k | 1.14M / 1.20M |
| p95 of `PostToolUse` / `Stop` in the worst session | 1,440 / 272 ms | 1,055 / 726 ms |

### Goals

| Goal | Result |
| --- | --- |
| 1. Confirmation before coding: at most 10% and 30 points below the control | **Not met.** The 10% limit was met (0% and 8%), but the control had the same result; the written instructions were enough in these tasks. |
| 2. Intent met at least equal to the control and above 80% | **Met** in both models (92% and 100%, equal to the control). |
| 3. Executable and true documentation in at least 90% | **Met on GPT-6 Luna (100%); not met on Haiku 5.5 (83%)**, because of a SpecMD defect (below). |
| 4. Legacy (T4) in at least 80% | **Met** (100% in both models), but the control also reached 100%. |
| 5. Cost: tokens up to 1.5 times the control and hooks below 1 s at p95 | **Tokens met:** the sessions with SpecMD used fewer tokens. **Latency not met:** `PostToolUse` went above 1 s at the p95 of the worst session; the machine was under high load during the round. |

### What the pilot showed

- **The strong control was enough in these tasks.** With a `CLAUDE.md`/`AGENTS.md` saying the same as what SpecMD injects, both small models asked before implementing and documented the rule. In these four short tasks, the deterministic check added no measurable accuracy.
- **Defect found: false positive divergence.** In T2 with Haiku, the fee broke the old scenario "Somar dois itens" ("Add two items") (500). Since the project was new and had no history, SpecMD treated the failure as a "cenário que nunca passou" ("scenario that never passed") and guided the agent to ask the dev about a divergence. The agent stopped to ask, instead of updating the scenario that the confirmation already implied; this happened in 2 of the 3 sessions. The failure was a consequence of the agent's own change, not legacy.
- **No extra cost:** the sessions with SpecMD used fewer tokens than the control in both models.

### Limits of this round

- Short, two-turn tasks, with the simulated dev already giving the answers in turn 2.
- The control receives in writing the same conventions that SpecMD injects. This measures the value of the deterministic check over instructions that already exist, not the value of installing SpecMD in a plain repository.
- High load on the machine during the round (a VM and another server running), which affects latency.

## Second round: design and goals (recorded before measuring)

The first round measured the value of the deterministic check over written instructions that already existed. The second measures what changes when **installing SpecMD in a plain repository**, with the strong control as the reference. It runs after the fix of the false positive divergence (PR #18).

- **Arms:**

  | Arm | Written instructions | Plugin |
  | --- | --- | --- |
  | Plain repository | no | no |
  | Plugin only | no | yes |
  | Instructions only | yes | no |

- **Simulated dev with three turns:** request, answers with confirmation and a fixed third turn ("Sim, pode seguir: atualize o que for necessário para a regra confirmada valer, inclusive cenários e requisitos existentes.", "Yes, go ahead: update whatever is needed for the confirmed rule to hold, including existing scenarios and requirements."). With this, an agent that asks before changing a confirmed scenario is not penalized. The final metrics are taken after turn 3; those of turn 2 are also recorded.
- **Tasks:** T1 to T4 from the first round, plus two:

  | Task | Project | Request | Trap | Hidden intent |
  | --- | --- | --- | --- | --- |
  | T5 later change | cart with a discount already documented and implemented (above 1000) | "o desconto agora vale acima de 500" ("the discount now applies above 500") | the scenario "sem desconto no limite" ("no discount at the threshold") (500 + 500 = 1000) no longer holds | strictly above 500; the rest unchanged |
  | T6 two rules | cart | `Cart.frete()` (500 up to 10000, 0 above) and at most 10 items | two rules with thresholds | exactly 10000 pays shipping; the 11th item raises `ValueError` |

- **Models and repetitions:** the same (`claude-haiku-5-5` and `gpt-6-luna`), 3 repetitions: 108 sessions.
- **Documentation criterion:** the corrected one, which accepts new or changed scenarios.

### Goals of the second round

Main comparison: plugin only against the plain repository, for each model.

1. **Confirmation before coding:** plugin only with at most 15% and at least 30 points below the plain repository.
2. **Living documentation:** plugin only with at least 85% executable and true documentation at the end, and at least 30 points above the plain repository.
3. **Without losing delivery:** intent met with plugin only at most 5 points below the plain repository.
4. **No need to write the instructions:** plugin only within at most 10 points of the "instructions only" control on goals 1 and 2.
5. **Later change (T5):** plugin only with at least 80% executable documentation at the end.
6. **Cost:** tokens per session with plugin only up to 1.5 times those of the plain repository.

## Results of the second round (24/10/2026)

Complete round: 108 sessions, without infrastructure failure, in `results/20261024-215841/`. Everything after turn 3, with the corrected documentation criterion.

| Metric | Haiku 5.5: plain / plugin / instructions | GPT-6 Luna: plain / plugin / instructions |
| --- | --- | --- |
| Rule before confirmation | 100% / 17% / 0% | 100% / 22% / 0% |
| Existing scenario changed before confirmation | 33% / 0% / 0% | 33% / 17% / 0% |
| Intent met | 100% / 94% / 94% | 100% / 100% / 100% |
| Executable and true documentation | 100% / 100% / 100% | 94% / 100% / 94% |
| Executable documentation after turn 2 | 100% / 89% / 100% | 50% / 100% / 89% |
| Tokens per session, median | 344k / 251k / 342k | 2.67M / 2.07M / 2.03M |
| p95 of `PostToolUse` / `Stop`, median across sessions with plugin | 1,475 / 931 ms | 1,084 / 792 ms |

### Goals of the second round

| Goal | Result |
| --- | --- |
| 1. Plugin only with at most 15% rule before confirmation and 30 points below the plain repository | **Not met**: 17% and 22%, although 83 and 78 points below the plain repository. All of Haiku's cases and 3 of Luna's 4 come from T4, in which the agent aligned the legacy code with the documentation in turn 1 without asking; in the new-rule tasks (T1, T2, T3, T5 and T6), the plugin stayed at 0% on Haiku and 7% on Luna. |
| 2. Plugin only with at least 85% executable documentation at the end and 30 points above the plain repository | **Not met.** The plugin reached 100% in both models, but the plain repository also reached 100% and 94% after turn 3, which asks to update whatever is needed. At the end of turn 2, when the dev had already confirmed, the plain repository on Luna was at 50% against 100% for the plugin. |
| 3. Intent with plugin only at most 5 points below the plain repository | **Met on Luna (100% = 100%); not met on Haiku (94% against 100%)**, because of a T4 session in which the agent changed the steps and the hidden check could not run. |
| 4. Plugin only within at most 10 points of the written instructions on goals 1 and 2 | **Not met** on goal 1 (17% and 22% against 0%); met on goal 2 (100% against 100% and 94%). |
| 5. T5 (later change) with at least 80% executable documentation | **Met**: 100% in both models. |
| 6. Tokens with plugin only up to 1.5 times those of the plain repository | **Met**: the plugin used fewer tokens (0.73 and 0.78 times). |

### What the second round showed

- **In a plain repository, both models coded before any confirmation in 100% of sessions**, and in one third of them changed existing scenarios without asking. Installing only the plugin, without writing instructions, brought that to 0% (Haiku) and 7% (Luna) in the new-rule tasks, with fewer tokens.
- **Living documentation without depending on the dev insisting:** at the end of turn 2, with the rule confirmed, the documentation ran and passed in 100% of Luna's sessions with the plugin, against 50% in the plain repository; the plain repository only caught up after turn 3 explicitly asked to update whatever was missing.
- **SpecMD gap in T4:** the conventions injected at session start say that the documentation is canonical, but do not say to ask the dev when the existing code contradicts it. With the plugin, the agent aligned the code with the documentation on its own; with the written instructions, which do say that, it asked in 100% of sessions.
- **High hook latency under load:** with 6 sessions in parallel, Behave runs and the machine loaded, the median of the `PostToolUse` p95 values was between 1.1 and 1.5 s; in the benchmark without load it is around 0.3 s. It needs measurement on a machine without load.

## Check of the divergence convention (25/10/2026)

After the second round, the session-start conventions and the skill gained the D-025 rule: "Se o código existente contradiz a documentação, não corrija nenhum dos dois sozinho: mostre a diferença ao dev e pergunte qual vale." ("If the existing code contradicts the documentation, do not fix either one on your own: show the difference to the dev and ask which one prevails."). T4 with plugin only was repeated with Haiku 5.5 (3 sessions, `results/20261025-t4-convencao/`); the check on GPT-6 Luna was not done.

- **Before:** in the 3 sessions of the second round, the agent corrected the legacy `pode_estornar` to 7 days in turn 1, without asking.
- **After:** in the 3 sessions, the agent implemented `solicitar_estorno` following the documentation, touched neither `pode_estornar` nor the scenario, pointed out the divergence ("o documento diz 7 dias, o código aprova até 10", "the document says 7 days, the code approves up to 10") and asked which rule prevails. The intent was met in 3 of 3 after the dev's answer.

The "rule before confirmation" metric still flags these sessions, because it counts any change to the application code in turn 1, and T4 asks to write `solicitar_estorno`. For T4, the relevant behavior is not changing the legacy code before asking, which now happens.

## Third round: design and goals (recorded before measuring)

The third round repeats the second with Claude Haiku 5.5 only, after the changes made since then: the divergence convention (rule 6 of the session-start conventions), the warm cache that no longer imports the Gherkin parser, and the English translation ([D-029](../../docs/decisions.md)). It is the first round in English: prompts, projects, plugin messages and conventions.

- **Model:** `claude-haiku-5-5` in Claude Code. GPT-6 Luna is left for later.
- **Arms:** the same three as in the second round (plain repository, plugin only, instructions only).
- **Tasks:** T1 to T6, with the same rules, numbers and hidden intent, in English.
- **Simulated dev:** the same three turns.
- **Repetitions:** 5 per task and arm: 90 sessions.
- **Parallelism:** 3 sessions at a time (6 in the second round), to reduce the load on the hooks. The machine's load average is recorded with the results.
- **T4 criterion, corrected before measuring:** in T4, turn 1 asks for new code (`request_refund`), so "rule before confirmation" now means that the legacy `can_refund` changed (or disappeared) in turn 1. Any change to the application code in turn 1 is still recorded as "application code changed in turn 1", for comparison with the earlier rounds.

### Goals of the third round

Main comparison: plugin only against the plain repository.

1. **Confirmation before coding:** plugin only with at most 10% rule before confirmation, and at least 50 points below the plain repository.
2. **Confirmed scenarios intact:** plugin only with at most 5% existing scenario changed before confirmation, and below the plain repository.
3. **Legacy divergence (T4):** with plugin only, the legacy `can_refund` is unchanged after turn 1 in at least 80% of the sessions.
4. **Without losing delivery:** intent met with plugin only at most 5 points below the plain repository.
5. **Living documentation:** plugin only with at least 90% executable and true documentation at the end.
6. **No need to write the instructions:** plugin only within at most 10 points of "instructions only" on goals 1 and 2.
7. **Cost:** tokens per session with plugin only up to 1.5 times those of the plain repository.
8. **Latency:** the median across sessions of the `PostToolUse` p95 and of the `Stop` p95 below 1 s.

## Results of the third round (27/10/2026)

Complete round: 90 sessions with `claude-haiku-5-5`, without infrastructure failure, in `results/20261027-102818-round3/` (`runs.jsonl`, `summary.md` and `environment.json`). Everything after turn 3. Total cost reported by Claude Code: US$ 1.67.

| Metric | Plain repository | Plugin only | Instructions only |
| --- | --- | --- | --- |
| Rule before confirmation | 83% | **0%** | 0% |
| Application code changed in turn 1 (any change) | 100% | 17% | 0% |
| Existing scenario changed before confirmation | 33% | **0%** | 0% |
| Intent met | 100% | **100%** | 77% |
| Executable and true documentation (corrected criterion) | 100% | 100% | 100% |
| Executable and true documentation (registered criterion) | 80% | 83% | 97% |
| Tokens per session, median | 329k | **241k** | 289k |
| Cost per session, median | US$ 0.0191 | US$ 0.0157 | US$ 0.0180 |
| Seconds per session, median | 131 | 100 | 120 |
| p95 of `PostToolUse` / `Stop`, median across sessions with plugin | — | 646 / 487 ms | — |

In the plain repository, T4 is the only task without "rule before confirmation" (0 of 5): the agent wrote `request_refund` and left the legacy `can_refund` alone. In the other five tasks it coded the rule before any confirmation in 25 of 25 sessions. The 17% of "application code changed in turn 1" with the plugin are the 5 T4 sessions, in which turn 1 asks for `request_refund` and the agent wrote it without touching `can_refund`.

### Goals of the third round

| Goal | Result |
| --- | --- |
| 1. Rule before confirmation: plugin only at most 10% and 50 points below the plain repository | **Met**: 0% against 83%. |
| 2. Confirmed scenarios intact: plugin only at most 5% and below the plain repository | **Met**: 0% against 33%. |
| 3. Legacy divergence (T4): `can_refund` unchanged after turn 1 in at least 80% with plugin only | **Met**: 5 of 5. In the second round, 0 of 3. |
| 4. Intent with plugin only at most 5 points below the plain repository | **Met**: 100% against 100%. |
| 5. Plugin only with at least 90% executable and true documentation | **Met with the corrected criterion of the second round** (100%). With the registered criterion of the first round, which only counts new scenarios, 83%: in T2 the fee is documented by updating the scenario "Add two items" to 501. |
| 6. Plugin only within 10 points of "instructions only" on goals 1 and 2 | **Met**: 0% and 0% in both arms. |
| 7. Tokens with plugin only up to 1.5 times the plain repository | **Met**: 0.73 times. |
| 8. Median of the `PostToolUse` and `Stop` p95 below 1 s | **Met**: 646 and 487 ms. The worst session reached 2.8 s and 1.9 s; the machine's load average went from 9–13 at the start to 28–43 at the end, on 11 CPUs. |

### What the third round showed

- **Installing the plugin is enough.** Without any written instruction, Haiku went from coding before confirmation in every new-rule session (25 of 25) to never doing it (0 of 30), and from changing existing scenarios without asking in 10 of 30 sessions to 0 of 30, with the same delivery (100% intent) and 27% fewer tokens.
- **The divergence convention works.** In T4, with the plugin, the agent pointed out that the documentation says 7 days and the code 10, asked which rule holds and delivered the 7 days in 5 of 5 sessions. In the second round, with the plugin and before the convention, it changed the legacy code without asking in 3 of 3.
- **Written instructions alone are less safe in delivery.** "Instructions only" also asked before coding, but met the intent in 77%: in T4 the agent deleted the legacy `can_refund` in 5 of 5 sessions (the hidden check requires it to keep working, now with 7 days), and in T1 it rounded the discount differently in 2 of 5.
- **Observed after the run, not a registered metric:** to run the scenarios without SpecMD, the agent copied them into a `.feature` file in 4 of 30 sessions with "instructions only" and in 1 of 30 in the plain repository, a second copy that can drift from the documentation. With the plugin, 0 of 30.
- **First round in English:** plugin messages, conventions, prompts and projects in English; the Portuguese rounds remain as recorded.

### Limits of this round

- One model (Haiku 5.5), 6 short tasks and 5 repetitions per task and arm: a trend with 30 sessions per arm, not statistical proof.
- The simulated dev follows a fixed script and does not react to what the agent asked.
- The machine was under load during the round, which affects latency (recorded in `environment.json`).
