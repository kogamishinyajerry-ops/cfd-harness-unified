# DOGFOOD REPORT — Live Partial · 3 DeepSeek cells · 2026-05-07

**Generated**: 2026-05-07 05:55:47 UTC
**Mode**: LIVE

## Run roster

| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |
|---|---|---|---|---|---|---|---|---|
| `imported_2026-05-07T05-52-03Z_d1af546e` | `novice` | `deepseek-chat` | — | — | 24 | 1 | 24 | 84.10s |
| `imported_2026-05-07T05-51-11Z_1a21b358` | `experienced_fluent` | `deepseek-chat` | — | — | 23 | 0 | 23 | 51.81s |
| `imported_2026-05-07T05-53-27Z_6971b908` | `debug` | `deepseek-chat` | — | — | 21 | 2 | 21 | 108.16s |

## Aggregate counts

- runs: **3**
- verdict pass: **0**
- verdict fail: **0**
- dropped: **0**
- critical findings: **1**
- warning findings: **3**
- info entries: **0**

## Critical backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T05-52-03Z_d1af546e` | `novice` | `max_steps_reached` | persona did not converge within max_steps; n_steps=24 |


## Warning backlog

| # | Run | Case | Persona | Category | Detail |
|---|---|---|---|---|---|
| 1 | `backward_step__novice__d…` | `imported_2026-05-07T05-52-03Z_d1af546e` | `novice` | `budget_exceeded` | budget_check phase=max_steps exceeded |
| 2 | `naca0012__experienced_fl…` | `imported_2026-05-07T05-51-11Z_1a21b358` | `experienced_fluent` | `budget_exceeded` | budget_check phase=input_tokens exceeded |
| 3 | `pipe_expansion__debug__d…` | `imported_2026-05-07T05-53-27Z_6971b908` | `debug` | `budget_exceeded` | budget_check phase=input_tokens exceeded |


## Info entries (clean runs)

_No info items._

## Findings narrative · 2026-05-07

**Scope**: 3 of 9 charter cells executed live (DeepSeek V4 Pro only;
ANTHROPIC_API_KEY + CODEX_RELAY_API_KEY were unset). 0/3 cells
produced a verdict. All 3 ran to budget cap (max_steps_reached or
input_token_budget_exceeded) without reaching the post-processing
phase. **This is real friction, not harness failure** — it is exactly
the signal the B-arc was designed to surface.

### Top finding F1 (critical) · `/state` does not exist in the workbench

All 3 personas opened with `GET /api/cases/{case_id}/state` (the route
referenced in the B.2 persona system prompts and B.4 dry-run scripts).
The workbench actually exposes `/api/cases/{case_id}/state-preview`.
Each persona consumed multiple tool calls + LLM turns hunting for the
right endpoint before pivoting to `/cases/{id}/completeness` or
`/cases/{id}` (no suffix).

**Disposition (B.5 candidate)**: either (a) add `/state` as an alias
on the workbench, or (b) update the B.2 persona prompts to reference
`/state-preview` and `/completeness`. (a) is more honest — an
engineer's mental model says "state" not "state-preview".

### Top finding F2 (critical) · 5-step workflow taxonomy is not engineer-discoverable

Personas spent 20+ HTTP calls trying engineer-conventional sub-paths:
`/workflow`, `/workflow/step`, `/steps`, `/step1`, `/step1_mesh`,
`/mesh`, `/bc`, `/solver`, `/geometry`, `/actions`. **None of these
exist.** The actual workbench taxonomy mixes `/api/cases/{id}/...` for
queries (mesh-quality, completeness, dicts, results-summary) with
`/api/import/{id}/...` for mutations (mesh, setup-bc, solve). The
mismatch defeats the V3 promise that "the engineer drives the 5-step
workflow without needing to read the API spec first".

**Disposition (B.5 candidate)**: workbench should expose either a
discovery endpoint (`GET /api/cases/{id}/actions` returning available
step transitions with their canonical URLs) or unify the
import-vs-cases taxonomy. Alternatively, persona prompts should embed
explicit URL templates per step.

### Top finding F3 (warning) · personas hit `/physics` GET; workbench requires POST

The `experienced_fluent` persona on naca0012 tried `GET /api/cases/{id}/physics`
and got `405 Method Not Allowed`. They then POST'd a JSON body and got
`422 Unprocessable Entity` (body shape unknown without reading the
schema). Real engineers also expect to query physics state before
mutating it.

**Disposition (B.5 candidate)**: add a `GET /api/cases/{id}/physics`
read-only route; document the POST request body in the OpenAPI schema
description.

### Top finding F4 (info) · OpenAPI self-discovery works as a fallback

One persona (experienced_fluent on naca0012) discovered
`GET /api/openapi.json` mid-run and successfully read the spec. This
is a useful workaround pattern but the persona had already burned
~70% of its token budget by then. **B.5 candidate**: persona prompts
should explicitly mention `/api/openapi.json` as a discovery fallback
when route 404s accumulate.

### V130 advisory-only contract: no violations detected

Aggregator scan for "AI told me" / "advisor said so" / "auto-apply" /
"because the AI" / "because the advisor" patterns in persona rationale
text → **0 violations across 3 runs**. The persona system prompts
successfully held the engineer-as-applier line even under high
friction. This is a positive V130 signal worth preserving.

### Cost actuals

- Total LLM tokens: input ~568k, output ~8k across 3 runs
- DeepSeek pricing: ~$0.15-0.40 total
- Wall-clock: ~5 minutes for 3 sequential runs

### Coverage gap

The 6 unrun cells (Anthropic + gpt-5.4) are deferred until those API
keys are staged. Findings F1-F4 are likely model-agnostic (they're
workbench-side, not LLM-side), but the cross-Cartesian property
(charter §rationale) is unverified for those 6 cells.

### Recommended B.5 sequencing

1. **B.5.1** (critical, workbench-side, ~30 min) — add `/state` alias
   pointing at `/state-preview`; update persona prompts to also
   recommend `/completeness`
2. **B.5.2** (critical, workbench-side, ~2-4 hrs) — expose
   `GET /api/cases/{id}/actions` returning canonical next-step URLs;
   OR document URL templates in B.2 prompts
3. **B.5.3** (warning, workbench-side, ~30 min) — add `GET /physics`
   read-only route paired with the existing POST
4. **B.5.4** (info, prompt-side, ~10 min) — augment B.2 persona
   prompts to reference `/api/openapi.json` as a fallback discovery
   endpoint

After B.5.1-B.5.4, re-run the live partial (3 cells) to verify
verdicts can now land. If verdict pass rate is still ≤1/3, escalate
to a B-arc-extension charter rather than continuing B.5.

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-163 · B.1 harness
- DEC-V61-164 · B.2 personas
- DEC-V61-165 · B.3 case pool
- DEC-V61-166 · B.4 orchestration + this aggregator