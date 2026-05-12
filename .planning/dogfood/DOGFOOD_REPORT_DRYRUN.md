# DOGFOOD REPORT — Dry Run · 2026-05-07

**Generated**: 2026-05-07 05:44:23 UTC
**Mode**: DRY RUN (scripted mock LLM + mock workbench)

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `backward_step` | `debug` | `claude-sonnet-4-6` | PASS | — | 4 | 2 | 4 | 0.00s |
| `backward_step` | `experienced_fluent` | `gpt-5.4` | PASS | — | 2 | 0 | 2 | 0.00s |
| `backward_step` | `novice` | `deepseek-chat` | PASS | — | 3 | 1 | 3 | 0.00s |
| `naca0012` | `debug` | `gpt-5.4` | PASS | — | 5 | 3 | 5 | 0.00s |
| `naca0012` | `experienced_fluent` | `deepseek-chat` | PASS | — | 3 | 1 | 3 | 0.00s |
| `naca0012` | `novice` | `claude-sonnet-4-6` | PASS | — | 4 | 2 | 4 | 0.00s |
| `pipe_expansion` | `debug` | `deepseek-chat` | PASS | — | 4 | 2 | 4 | 0.00s |
| `pipe_expansion` | `experienced_fluent` | `claude-sonnet-4-6` | PASS | — | 3 | 1 | 3 | 0.00s |
| `pipe_expansion` | `novice` | `gpt-5.4` | — | yes | 4 | 2 | 4 | 0.00s |

## Aggregate counts

- runs: **9**
- verdict pass: **8**
- verdict fail: **0**
- dropped: **1**
- critical findings: **0**
- warning findings: **1**
- info entries: **8**

## Critical backlog

_No critical items._


## Warning backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `pipe_expansion__novice__…` | `pipe_expansion` | `novice` | `explicit_drop` | persona explicitly dropped: 'axisymmetric BC type unclear from corpus; need more guidance' |


## Info entries (clean runs)

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__debug__an…` | `backward_step` | `debug` | `clean_run` | verdict passed; 2 advisor queries, 4 tool uses, 4 steps |
| 2 | `backward_step__experienc…` | `backward_step` | `experienced_fluent` | `clean_run` | verdict passed; 0 advisor queries, 2 tool uses, 2 steps |
| 3 | `backward_step__novice__d…` | `backward_step` | `novice` | `clean_run` | verdict passed; 1 advisor queries, 3 tool uses, 3 steps |
| 4 | `naca0012__debug__openai_…` | `naca0012` | `debug` | `clean_run` | verdict passed; 3 advisor queries, 5 tool uses, 5 steps |
| 5 | `naca0012__experienced_fl…` | `naca0012` | `experienced_fluent` | `clean_run` | verdict passed; 1 advisor queries, 3 tool uses, 3 steps |
| 6 | `naca0012__novice__anthro…` | `naca0012` | `novice` | `clean_run` | verdict passed; 2 advisor queries, 4 tool uses, 4 steps |
| 7 | `pipe_expansion__debug__d…` | `pipe_expansion` | `debug` | `clean_run` | verdict passed; 2 advisor queries, 4 tool uses, 4 steps |
| 8 | `pipe_expansion__experien…` | `pipe_expansion` | `experienced_fluent` | `clean_run` | verdict passed; 1 advisor queries, 3 tool uses, 3 steps |


## Dry-run caveat

This report is generated from SCRIPTED mock-LLM responses against a MOCK workbench transport. Backlog items reflect the script + deterministic verdict comparison; they do NOT capture real engineer-LLM friction. A live run (with `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `CODEX_RELAY_API_KEY` set and the workbench dev server up at `localhost:8000`) is required to surface real advisor signal-to-noise findings, mesh-import failures, convergence behavior, and persona-vs-workbench UX gaps.

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator