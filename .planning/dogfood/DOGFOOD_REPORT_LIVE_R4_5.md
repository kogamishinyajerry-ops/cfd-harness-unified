# DOGFOOD REPORT — Live R4.5 · tighter prune + 1.5M budget · 2026-05-07

**Generated**: 2026-05-07 07:10:34 UTC
**Mode**: LIVE

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `imported_2026-05-07T06-57-33Z_741f93f2` | `novice` | `deepseek-chat` | — | — | 50 | 2 | 63 | 393.41s |
| `imported_2026-05-07T06-50-16Z_41bbd2fb` | `experienced_fluent` | `deepseek-chat` | — | — | 50 | 1 | 58 | 436.93s |
| `imported_2026-05-07T07-04-06Z_e30dd0f5` | `debug` | `deepseek-chat` | — | — | 44 | 2 | 53 | 335.45s |

## Aggregate counts

- runs: **3**
- verdict pass: **0**
- verdict fail: **0**
- dropped: **0**
- critical findings: **3**
- warning findings: **3**
- info entries: **0**

## Critical backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T06-57-33Z_741f93f2` | `novice` | `max_steps_reached` | persona did not converge within max_steps; n_steps=50 |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-50-16Z_41bbd2fb` | `experienced_fluent` | `workbench_5xx` | workbench 5xx on /api/cases/imported_2026-05-07T06-50-16Z_41bbd2fb/results-summary |
| 3 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-50-16Z_41bbd2fb` | `experienced_fluent` | `max_steps_reached` | persona did not converge within max_steps; n_steps=50 |


## Warning backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T06-57-33Z_741f93f2` | `novice` | `budget_exceeded` | budget_check phase=max_steps exceeded |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T06-50-16Z_41bbd2fb` | `experienced_fluent` | `budget_exceeded` | budget_check phase=max_steps exceeded |
| 3 | `pipe_expansion__debug__d…` | `imported_2026-05-07T07-04-06Z_e30dd0f5` | `debug` | `budget_exceeded` | budget_check phase=input_tokens exceeded |


## Info entries (clean runs)

_No info items._


## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator