# DOGFOOD REPORT — Live R2 · post-B.5 fixes · 3 DeepSeek cells · 2026-05-07

**Generated**: 2026-05-07 06:14:17 UTC
**Mode**: LIVE

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `imported_2026-05-07T06-09-08Z_e898154a` | `novice` | `deepseek-chat` | — | — | 11 | 2 | 16 | 109.38s |
| `imported_2026-05-07T06-08-26Z_944fa92f` | `experienced_fluent` | `deepseek-chat` | — | — | 9 | 0 | 11 | 42.22s |
| `imported_2026-05-07T06-10-58Z_a894375a` | `debug` | `deepseek-chat` | — | — | 9 | 2 | 15 | 106.99s |

## Aggregate counts

- runs: **3**
- verdict pass: **0**
- verdict fail: **0**
- dropped: **0**
- critical findings: **0**
- warning findings: **3**
- info entries: **0**

## Critical backlog

_No critical items._


## Warning backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T06-09-08Z_e898154a` | `novice` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-08-26Z_944fa92f` | `experienced_fluent` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 3 | `pipe_expansion__debug__d…` | `imported_2026-05-07T06-10-58Z_a894375a` | `debug` | `budget_exceeded` | budget_check phase=input_tokens exceeded |


## Info entries (clean runs)

_No info items._


## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator