---
decision_id: DEC-V61-168
title: B.5.2 · Workbench /state alias to /state-preview + GET /physics read-only paired with existing POST
status: Accepted
parent_dec: V61-162
phase: B
notion_sync_status: pending
---

# DEC-V61-168 · B.5.2 · State Alias + GET Physics

## Scope

Address findings F1 (workbench-side) and F3 from
DOGFOOD_REPORT_LIVE.md:

- Add `GET /api/cases/{case_id}/state` as a thin alias delegating
  to `build_state_preview`. Engineer mental model says "state",
  not "state-preview" — the dogfood proved this.
- Add `GET /api/cases/{case_id}/physics` returning the current
  `constant/physicalProperties` + `constant/momentumTransport` dict
  texts (or `null` for each if not yet committed). Engineers expect
  query-before-mutate; today only POST exists.

## Surface delivered

- `ui/backend/routes/case_inspect.py` — new GET handler for
  `/cases/{case_id}/state` calling the same `build_state_preview`
  service; identical wire shape to `/state-preview`
- `ui/backend/routes/physics.py` — new GET handler for
  `/cases/{case_id}/physics` returning a `PhysicsStateResponse` with
  `material_dict_text: str | None`, `regime_dict_text: str | None`
- `ui/backend/tests/test_state_alias.py` — alias returns the same
  payload as state-preview
- `ui/backend/tests/test_get_physics.py` — pre-commit (None for
  both texts) + post-commit (full text) cases

## V130 / V132 contract

Both new routes are GET (read-only). Neither belongs in
`MUTATING_ROUTES` or `KNOWN_MUTATION_FUNCTIONS`. The existing
contract test (`test_ai_advisor_contract.py` Layer-A/B/C) does not
need modification — these routes are NOT in the AI dispatch surface
and are NOT mutation functions.

## Four-question gate

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Both routes are read-only, no LLM dependency |
| Q2 | Artifacts output? | ✅ State-preview wire shape unchanged; physics state returns existing dict text |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Both routes 100% derive from on-disk state; no AI inference |
| Q4 | AI advisory only (no mutating call)? | ✅ Both routes GET; not in MUTATING_ROUTES |

## Verification

- `pytest ui/backend/tests/test_state_alias.py` passes
- `pytest ui/backend/tests/test_get_physics.py` passes
- V132 contract test (`test_ai_advisor_contract.py`) still passes
  unchanged
- Live workbench responds 200 to `GET /api/cases/{id}/state` and
  `GET /api/cases/{id}/physics` with synthetic case scaffolds

## Confidence

`high` — both routes are thin reads of existing state.
- `/state` aliases an existing service function with no behavior change
- `/physics` GET reads files we already write via POST; no new I/O paths

## Codex pre-merge review

Per charter: B.5 fixes per fix risk. These two are GET-only reads;
no security boundary, no byte-repro impact, no ≥3 E2E failures.
Per Opus confidence (high) → no Codex round.

## Notes

- The `/state` alias is a SUPERSET of dogfood's expected behavior
  (returns the same enriched preview, including `next_action`
  query param). The simpler "just /state" matches engineer mental
  model without dropping any feature
- `GET /physics` returns `null` for un-written dicts rather than
  404 — engineer's Step 3 question is "what's currently committed?",
  and "nothing" is a valid answer

## References

- DEC-V61-162 · B-arc charter
- DEC-V61-167 · B.5.1 (sister fix on persona-side)
- `.planning/dogfood/DOGFOOD_REPORT_LIVE.md` §F1 + §F3
- DEC-V61-102 · existing `/state-preview` route
- DEC-V61-142 · existing POST `/physics` route
