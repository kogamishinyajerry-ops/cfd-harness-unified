# DOGFOOD REPORT — Live R4 · post-B-ext.1+2 · 2026-05-07

**Generated**: 2026-05-07 07:10:34 UTC
**Mode**: LIVE

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `imported_2026-05-07T06-43-27Z_8b79bea1` | `novice` | `deepseek-chat` | — | — | 22 | 2 | 26 | 194.52s |
| `imported_2026-05-07T06-42-01Z_33088ef4` | `experienced_fluent` | `deepseek-chat` | — | — | 14 | 0 | 20 | 85.89s |
| `imported_2026-05-07T06-46-42Z_00bad215` | `debug` | `deepseek-chat` | — | — | 16 | 1 | 21 | 140.01s |

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
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T06-43-27Z_8b79bea1` | `novice` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-42-01Z_33088ef4` | `experienced_fluent` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 3 | `pipe_expansion__debug__d…` | `imported_2026-05-07T06-46-42Z_00bad215` | `debug` | `budget_exceeded` | budget_check phase=input_tokens exceeded |


## Info entries (clean runs)

_No info items._


## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator