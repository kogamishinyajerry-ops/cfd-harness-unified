# DOGFOOD REPORT — Live R3 · post-B.5.5 (schema examples + budget) · 2026-05-07

**Generated**: 2026-05-07 06:22:04 UTC
**Mode**: LIVE

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `imported_2026-05-07T06-17-20Z_e1d25514` | `novice` | `deepseek-chat` | — | — | 19 | 2 | 28 | 158.74s |
| `imported_2026-05-07T06-16-18Z_c32b5a81` | `experienced_fluent` | `deepseek-chat` | — | — | 11 | 0 | 14 | 61.95s |
| `imported_2026-05-07T06-19-58Z_c13f5397` | `debug` | `deepseek-chat` | — | — | 10 | 1 | 16 | 89.23s |

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
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T06-17-20Z_e1d25514` | `novice` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-16-18Z_c32b5a81` | `experienced_fluent` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 3 | `pipe_expansion__debug__d…` | `imported_2026-05-07T06-19-58Z_c13f5397` | `debug` | `budget_exceeded` | budget_check phase=input_tokens exceeded |


## Info entries (clean runs)

_No info items._


## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator