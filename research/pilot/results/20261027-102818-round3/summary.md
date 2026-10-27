# Pilot results

Generated at 2026-10-27T14:34:13.758211+00:00 from 90 sessions. Design and goals in [README](../../README.md).

## claude-haiku-5-5

| Metric | Common repository | Plugin only | Instructions only |
| --- | --- | --- | --- |
| Rule before confirmation (lower is better) | 83% | 0% | 0% |
| Application code changed in turn 1 (any change) | 100% | 17% | 0% |
| Intent met | 100% | 100% | 77% |
| Rule documented with scenarios (registered criterion) | 80% | 83% | 97% |
| Documentation executable and true (registered criterion) | 80% | 83% | 97% |
| Rule documented with scenarios (corrected criterion) | 100% | 100% | 100% |
| Documentation executable and true (corrected criterion) | 100% | 100% | 100% |
| Intent met after turn 2 | 100% | 100% | 77% |
| Documentation executable after turn 2 | 100% | 100% | 97% |
| Existing scenario changed before confirmation | 33% | 0% | 0% |
| Tokens per session, median | 328,694 | 241,460 | 288,803 |
| Seconds per session, median | 131 | 100 | 120 |
| Cost per session, median in US$ | 0.0191 | 0.0157 | 0.0180 |

Hooks: PostToolUse / Stop p95 in the worst session: 2776 / 1861 ms; median of the p95s: 646.0 / 486.5 ms.

Per task (Common repository / Plugin only / Instructions only):

| Task | Before confirmation | Intent | Executable (corrected) |
| --- | --- | --- | --- |
| T1 | 100% / 0% / 0% | 100% / 100% / 60% | 100% / 100% / 100% |
| T2 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T3 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T4 | 0% / 0% / 0% | 100% / 100% / 0% | 100% / 100% / 100% |
| T5 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |
| T6 | 100% / 0% / 0% | 100% / 100% / 100% | 100% / 100% / 100% |

