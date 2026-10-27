# Evolution round results

Generated at 2026-10-27T18:24:53.401975+00:00 from 20 runs of 5 requests each; agent `claude-haiku-5-5`, simulated developer `claude-sonnet-5-5` (realistic). Design and goals in [README](../../README.md).

| Metric | Plain repository | Plugin only | Instructions only | Traditional repository |
| --- | --- | --- | --- | --- |
| All hidden checks pass at the end | 2/5 | 5/5 | 4/5 | 2/5 |
| Legacy loyalty bug fixed | 2/5 | 5/5 | 4/5 | 2/5 |
| Fee kept out of the free-shipping limit | 5/5 | 5/5 | 5/5 | 5/5 |
| Fee kept out of the loyalty points | 5/5 | 5/5 | 5/5 | 5/5 |
| No invented price rule | 5/5 | 5/5 | 5/5 | 5/5 |
| Own check passing at the end (scenarios or unit tests) | 2/5 | 5/5 | 4/5 | 2/5 |
| Hidden checks passing at the end, mean | 97% | 100% | 99% | 97% |
| Regressions introduced, mean per run | 0.0 | 0.0 | 0.0 | 0.0 |
| Regressions left at the end, mean per run | 0.0 | 0.0 | 0.0 | 0.0 |
| Rules stated correctly in the documentation (judge), mean | 82% | 100% | 96% | 67% |
| Outdated rules in the documentation (judge), mean | 0.2 | 0.0 | 0.4 | 0.2 |
| Mutation score of the project's own check, mean | 84% | 96% | 94% | 88% |
| Requests coded in the first turn, mean | 100% | 28% | 0% | 100% |
| Agent turns per run, mean | 8.4 | 11.6 | 12.4 | 8.6 |
| Developer corrections per run, mean | 1.6 | 3.2 | 2.4 | 1.2 |
| Agent tokens per run, median | 1,256,636 | 1,447,298 | 1,568,095 | 1,105,101 |
| Agent cost per run, median in US$ | 0.061 | 0.086 | 0.079 | 0.050 |
| Simulated developer cost per run, median in US$ | 0.038 | 0.067 | 0.073 | 0.037 |

Hooks: median of the per-run p95: PostToolUse 1767 ms, Stop 912 ms.

Hidden checks at the end, runs passing per check:

| Check | Plain repository | Plugin only | Instructions only | Traditional repository |
| --- | --- | --- | --- | --- |
| add up items | 5/5 | 5/5 | 5/5 | 5/5 |
| discount above the threshold | 5/5 | 5/5 | 5/5 | 5/5 |
| discount at the threshold | 5/5 | 5/5 | 5/5 | 5/5 |
| discount rounded down | 5/5 | 5/5 | 5/5 | 5/5 |
| empty cart shipping | 5/5 | 5/5 | 5/5 | 5/5 |
| empty cart total | 5/5 | 5/5 | 5/5 | 5/5 |
| exactly the limit pays shipping | 5/5 | 5/5 | 5/5 | 5/5 |
| fee does not count for free shipping | 5/5 | 5/5 | 5/5 | 5/5 |
| free shipping above the limit | 5/5 | 5/5 | 5/5 | 5/5 |
| loyalty points above 5000 | 5/5 | 5/5 | 5/5 | 5/5 |
| negative price rejected | 5/5 | 5/5 | 5/5 | 5/5 |
| no discount below the threshold | 5/5 | 5/5 | 5/5 | 5/5 |
| no loyalty points at exactly 5000 | 2/5 | 5/5 | 4/5 | 2/5 |
| no maximum price | 5/5 | 5/5 | 5/5 | 5/5 |
| shipping below the limit | 5/5 | 5/5 | 5/5 | 5/5 |
| summary has total, shipping and points | 5/5 | 5/5 | 5/5 | 5/5 |
| total with the fee near the shipping limit | 5/5 | 5/5 | 5/5 | 5/5 |
| zero price allowed | 5/5 | 5/5 | 5/5 | 5/5 |

Per request: first-turn coding / turns, mean (Plain repository / Plugin only / Instructions only / Traditional repository):

| Request | First-turn coding | Turns |
| --- | --- | --- |
| S1 | 5/5 / 1/5 / 0/5 / 5/5 | 2.8 / 3.2 / 3.0 / 2.2 |
| S2 | 5/5 / 0/5 / 0/5 / 5/5 | 1.4 / 2.0 / 2.6 / 1.6 |
| S3 | 5/5 / 0/5 / 0/5 / 5/5 | 1.8 / 2.0 / 2.4 / 2.2 |
| S4 | 5/5 / 5/5 / 0/5 / 5/5 | 1.4 / 2.0 / 2.4 / 1.2 |
| S5 | 5/5 / 1/5 / 0/5 / 5/5 | 1.0 / 2.4 / 2.0 / 1.4 |
