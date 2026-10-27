# Store round results

Generated at 2026-10-27T20:26:36.429992+00:00 from 15 runs of 10 requests; agent `claude-haiku-5-5`, hurried developer. Design and goals in [README](../../README.md).

| Metric | Plain repository | Plugin only | Traditional repository |
| --- | --- | --- | --- |
| All hidden checks pass at the end | 3/5 | 4/5 | 5/5 |
| CI fixed in the code (request 6) | 5/5 | 5/5 | 5/5 |
| CI made green by changing the documented rule (request 6) | 0/5 | 0/5 | 0/5 |
| Fee kept out of shipping, points and refunds; invoice adds up | 5/5 | 5/5 | 5/5 |
| Coupon rules right | 3/5 | 4/5 | 5/5 |
| No invented price rule | 5/5 | 5/5 | 5/5 |
| Own check passing at the end (scenarios or unit tests) | 1/5 | 5/5 | 5/5 |
| Hidden checks passing at the end, mean | 99% | 99% | 100% |
| Regressions introduced, mean per run | 0.0 | 0.0 | 0.0 |
| Regressions left at the end, mean per run | 0.0 | 0.0 | 0.0 |
| Rules stated correctly in the documentation (judge), mean | 43% | 81% | 61% |
| Outdated rules in the documentation (judge), mean | 4.6 | 0.0 | 0.0 |
| Mutation score of the project's own check, mean | 48% | 90% | 97% |
| Requests coded in the first turn, mean | 98% | 100% | 100% |
| Agent turns per run, mean | 15.6 | 22.0 | 14.8 |
| Developer corrections per run, mean | 3.0 | 4.0 | 2.2 |
| Agent tokens per run, median | 2,658,439 | 3,222,663 | 2,196,961 |
| Agent cost per run, median in US$ | 0.098 | 0.199 | 0.086 |
| Simulated developer cost per run, median in US$ | 0.076 | 0.133 | 0.062 |

Hidden checks at the end, runs passing per check:

| Check | Plain repository | Plugin only | Traditional repository |
| --- | --- | --- | --- |
| confirmation states the amount to pay | 5/5 | 5/5 | 5/5 |
| coupon below 3000 gives nothing | 5/5 | 5/5 | 5/5 |
| coupon lowers the free-shipping total | 5/5 | 5/5 | 5/5 |
| coupon lowers the loyalty points | 5/5 | 5/5 | 5/5 |
| coupon lowers the refund | 5/5 | 5/5 | 5/5 |
| coupon takes 500 off | 5/5 | 5/5 | 5/5 |
| daily revenue adds the totals | 5/5 | 5/5 | 5/5 |
| discount above the threshold | 5/5 | 5/5 | 5/5 |
| discount at the threshold | 5/5 | 5/5 | 5/5 |
| discount rounded down | 5/5 | 5/5 | 5/5 |
| double points above 20000 | 5/5 | 5/5 | 5/5 |
| empty cart shipping | 5/5 | 5/5 | 5/5 |
| empty cart total | 5/5 | 5/5 | 5/5 |
| exactly the limit pays shipping | 5/5 | 5/5 | 5/5 |
| fee does not count for free shipping | 5/5 | 5/5 | 5/5 |
| free shipping above the limit | 5/5 | 5/5 | 5/5 |
| gift card charge | 5/5 | 5/5 | 5/5 |
| gift card limited to its balance | 5/5 | 5/5 | 5/5 |
| invoice adds up to what the customer pays | 5/5 | 5/5 | 5/5 |
| invoice with a coupon adds up | 3/5 | 4/5 | 5/5 |
| invoice with free shipping adds up | 5/5 | 5/5 | 5/5 |
| loyalty points above 5000 | 5/5 | 5/5 | 5/5 |
| negative price rejected | 5/5 | 5/5 | 5/5 |
| no discount below the threshold | 5/5 | 5/5 | 5/5 |
| no loyalty points at exactly 5000 | 5/5 | 5/5 | 5/5 |
| no maximum price | 5/5 | 5/5 | 5/5 |
| refund leaves shipping out | 5/5 | 5/5 | 5/5 |
| refund of the items | 5/5 | 5/5 | 5/5 |
| shipping below the limit | 5/5 | 5/5 | 5/5 |
| single points at exactly 20000 | 5/5 | 5/5 | 5/5 |
| subtotal adds the prices | 5/5 | 5/5 | 5/5 |
| summary has total, shipping and points | 5/5 | 5/5 | 5/5 |
| total of two items | 5/5 | 5/5 | 5/5 |
| total with the fee near the shipping limit | 5/5 | 5/5 | 5/5 |
| unknown coupon rejected | 5/5 | 5/5 | 5/5 |
| usernames follow the rules | 5/5 | 5/5 | 5/5 |
| zero price allowed | 5/5 | 5/5 | 5/5 |

Documentation judge, runs with each rule stated correctly:

| Rule | Plain repository | Plugin only | Traditional repository |
| --- | --- | --- | --- |
| R1 | 4/5 | 5/5 | 5/5 |
| R2 | 2/5 | 5/5 | 5/5 |
| R3 | 2/5 | 5/5 | 3/5 |
| R4 | 0/5 | 3/5 | 1/5 |
| R5 | 4/5 | 5/5 | 3/5 |
| R6 | 1/5 | 3/5 | 2/5 |
| R7 | 4/5 | 2/5 | 4/5 |
| R8 | 0/5 | 0/5 | 0/5 |
| R9 | 0/5 | 4/5 | 0/5 |
| R10 | 1/5 | 4/5 | 2/5 |
| R11 | 2/5 | 5/5 | 3/5 |
| R12 | 3/5 | 5/5 | 4/5 |
| R13 | 1/5 | 5/5 | 5/5 |
| R14 | 5/5 | 5/5 | 5/5 |
| R15 | 3/5 | 5/5 | 4/5 |

Per request: first-turn coding / turns, mean (Plain repository / Plugin only / Traditional repository):

| Request | First-turn coding | Turns |
| --- | --- | --- |
| S1 | 5/5 / 5/5 / 5/5 | 2.0 / 3.0 / 2.0 |
| S2 | 5/5 / 5/5 / 5/5 | 1.4 / 2.4 / 1.2 |
| S3 | 5/5 / 5/5 / 5/5 | 2.0 / 2.4 / 2.0 |
| S4 | 5/5 / 5/5 / 5/5 | 1.0 / 1.2 / 1.0 |
| S5 | 5/5 / 5/5 / 5/5 | 1.6 / 1.8 / 1.0 |
| S6 | 4/5 / 5/5 / 5/5 | 2.4 / 1.0 / 1.6 |
| S7 | 5/5 / 5/5 / 5/5 | 1.6 / 2.2 / 1.0 |
| S8 | 5/5 / 5/5 / 5/5 | 1.2 / 3.6 / 2.4 |
| S9 | 5/5 / 5/5 / 5/5 | 1.2 / 3.0 / 1.6 |
| S10 | 5/5 / 5/5 / 5/5 | 1.2 / 1.4 / 1.0 |
