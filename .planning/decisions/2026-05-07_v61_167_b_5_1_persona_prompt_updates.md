---
decision_id: DEC-V61-167
title: B.5.1 · Persona prompt updates — reference real workbench routes (/state-preview, /completeness, /api/openapi.json fallback)
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-167 · B.5.1 · Persona Prompt Updates

## Scope

Address findings F1 (partial · persona-side) and F4 from
DOGFOOD_REPORT_LIVE.md by updating B.2 persona system prompts:

- Replace `/api/cases/{id}/state` references with `/state-preview`
- Add `/api/cases/{id}/completeness` as the canonical "where am I"
  endpoint (returns step-by-step progress, the actual mental model
  for "case state")
- Add `/api/openapi.json` as a discovery fallback when route 404s
  accumulate
- Note that workbench mixes `/api/cases/{id}/...` for queries with
  `/api/import/{id}/...` for mutations — this is non-obvious and
  worth surfacing in the prompt to save persona discovery turns

## Surface delivered

- `scripts/dogfood/personas/prompts/novice.md` — updated
- `scripts/dogfood/personas/prompts/experienced_fluent.md` — updated
- `scripts/dogfood/personas/prompts/debug.md` — updated

Guardrail markers preserved (validate_prompt still passes).

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Prompts continue to mandate offline continuity (`llm_available: false` → continue with rule-based) |
| Q2 | Artifacts output? | ✅ No artifact change |
| Q3 | TrustGate / completeness / audit explainable? | ✅ No advisor contract change |
| Q4 | AI advisory only (no mutating call)? | ✅ All updated routes are GET; advisory-only contract preserved |

## Verification

- All persona prompts continue to pass `validate_prompt()` (5 guardrail markers)
- 158/158 dogfood tests pass

## Confidence

`high` — pure content edit; no new code paths. Charter §"per Opus
confidence" applies.

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-164 · B.2 persona library
- `.planning/dogfood/DOGFOOD_REPORT_LIVE.md` §F1 + §F4
