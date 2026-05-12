---
decision_id: DEC-V61-170
title: B.5.5 · /actions example_body schema examples + persona budget bump (40 steps / 600k cumulative tokens)
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-170 · B.5.5 · Schema Examples + Budget Bump

## Scope

Address F5 (schema discoverability) surfaced by R2: personas got past
the route-discovery gap (B.5.1-B.5.3) but then hit 422
Unprocessable Entity on POST `/physics` because the persona didn't
know the `MaterialContract` / `RegimeContract` schema. They fell back
to fetching `/api/openapi.json` (50KB) which burned their token budget.

Plus a budget bump (180k → 600k cumulative tokens, 24 → 40 steps) to
let R3 personas drive further before the harness-side cap trips.

## Surface delivered

- `ui/backend/routes/actions_catalogue.py` — `ActionEntry` extended
  with optional `example_body: dict | None`. Hand-curated working
  JSON for POST `/mesh`, POST `/physics`, POST `/setup-bc`, POST `/solve`.
  Real `preset_id` values from `materials_library` / `regimes_library`.
- `scripts/dogfood/live_partial_run.py` — `max_steps=40`,
  `max_input_tokens=600_000`
- `ui/backend/tests/test_actions_catalogue.py` — 2 new tests:
  - every POST step (excluding import_geometry) has non-null example_body
  - physics example_body uses real preset_ids (not fabricated)

## R2 → R3 delta

R2 backward_step succeeded POST physics on attempt 4 of 4 (3× 422 + 1×
200) after fetching openapi.json. R3 backward_step succeeded POST
physics on attempt 4 of 4 from the example_body baseline + reached
Step 4 (POST setup-bc 200) — first cell to reach BC stage in any
iteration.

Other R3 progress: naca0012 reached Step 3 (physics 422 → eventually
exhausted budget). pipe_expansion reached Step 4 (setup-bc 400 — patch
discovery limitation surfaced as F7).

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Catalogue example_body is rule-based / static; no LLM dependency |
| Q2 | Artifacts output? | ✅ ActionsCatalogue wire shape extended (optional field; existing consumers unaffected) |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Examples reference real preset_ids; test asserts non-fabrication |
| Q4 | AI advisory only (no mutating call)? | ✅ Route is GET; catalogue describes mutations but does not call them |

## Verification

- 14/14 actions_catalogue tests pass (12 from B.5.3 + 2 new)
- 158/158 dogfood tests pass (no regression)
- 21/21 V132 contract tests pass

## Confidence

`high` — content addition + harness budget knob; no architectural
change.

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-169 · B.5.3 (extended)
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_R2.md` §F5
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md`
