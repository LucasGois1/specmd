# Evolution round results

Generated at 2026-10-27T16:10:45.098975+00:00 from 15 runs of 5 requests each; agent `claude-haiku-5-5`, simulated developer `claude-sonnet-5-5`. Design and goals in [README](../../README.md).

| Metric | Plain repository | Plugin only | Instructions only |
| --- | --- | --- | --- |
| All hidden checks pass at the end | 5/5 | 5/5 | 5/5 |
| Legacy loyalty bug fixed | 5/5 | 5/5 | 5/5 |
| Fee kept out of the free-shipping limit | 5/5 | 5/5 | 5/5 |
| Fee kept out of the loyalty points | 5/5 | 5/5 | 5/5 |
| No invented price rule | 5/5 | 5/5 | 5/5 |
| Documentation executable and true at the end | 5/5 | 5/5 | 5/5 |
| Hidden checks passing at the end, mean | 100% | 100% | 100% |
| Regressions introduced, mean per run | 0.0 | 0.0 | 0.0 |
| Regressions left at the end, mean per run | 0.0 | 0.0 | 0.0 |
| Mutation score of the documented scenarios, mean | 90% | 98% | 100% |
| Requests coded in the first turn, mean | 100% | 24% | 0% |
| Agent turns per run, mean | 7.6 | 10.8 | 12.2 |
| Developer corrections per run, mean | 1.8 | 2.4 | 2.0 |
| Agent tokens per run, median | 1,155,681 | 1,345,854 | 1,667,051 |
| Agent cost per run, median in US$ | 0.051 | 0.070 | 0.091 |
| Simulated developer cost per run, median in US$ | 0.043 | 0.064 | 0.082 |

Hooks: median of the per-run p95: PostToolUse 734 ms, Stop 633 ms.

Hidden checks at the end, runs passing per check:

| Check | Plain repository | Plugin only | Instructions only |
| --- | --- | --- | --- |
| add up items | 5/5 | 5/5 | 5/5 |
| discount above the threshold | 5/5 | 5/5 | 5/5 |
| discount at the threshold | 5/5 | 5/5 | 5/5 |
| discount rounded down | 5/5 | 5/5 | 5/5 |
| empty cart shipping | 5/5 | 5/5 | 5/5 |
| empty cart total | 5/5 | 5/5 | 5/5 |
| exactly the limit pays shipping | 5/5 | 5/5 | 5/5 |
| fee does not count for free shipping | 5/5 | 5/5 | 5/5 |
| free shipping above the limit | 5/5 | 5/5 | 5/5 |
| loyalty points above 5000 | 5/5 | 5/5 | 5/5 |
| negative price rejected | 5/5 | 5/5 | 5/5 |
| no discount below the threshold | 5/5 | 5/5 | 5/5 |
| no loyalty points at exactly 5000 | 5/5 | 5/5 | 5/5 |
| no maximum price | 5/5 | 5/5 | 5/5 |
| shipping below the limit | 5/5 | 5/5 | 5/5 |
| summary has total, shipping and points | 5/5 | 5/5 | 5/5 |
| total with the fee near the shipping limit | 5/5 | 5/5 | 5/5 |
| zero price allowed | 5/5 | 5/5 | 5/5 |

Per request: first-turn coding / turns, mean (Plain repository / Plugin only / Instructions only):

| Request | First-turn coding | Turns |
| --- | --- | --- |
| S1 | 5/5 / 1/5 / 0/5 | 2.4 / 2.6 / 2.8 |
| S2 | 5/5 / 0/5 / 0/5 | 1.4 / 2.0 / 2.2 |
| S3 | 5/5 / 0/5 / 0/5 | 1.8 / 2.0 / 2.4 |
| S4 | 5/5 / 5/5 / 0/5 | 1.0 / 2.2 / 2.4 |
| S5 | 5/5 / 0/5 / 0/5 | 1.0 / 2.0 / 2.4 |
