---
decision_id: DEC-V61-174
title: B-ext.2 · F7 STL patch discovery — surface face-annotations / face-index / patch-classification in /actions catalogue + Step 4 prerequisite docs
status: Accepted
parent_dec: V61-172
phase: B-extend
notion_sync_status: pending
---

# DEC-V61-174 · B-ext.2 · Patch Discovery Surfacing

## Scope

Address F7 (R3 root cause for `pipe_expansion/debug` Step 4 setup-bc
400): single-shell STLs land as one `defaultFaces` patch; persona had
no path to split it before Step 4.

## Surface delivered

- `ui/backend/routes/actions_catalogue.py`:
  - 3 new query catalogue entries:
    - `patch_classification` → GET `/api/cases/{id}/patch-classification`
    - `face_annotations` → GET `/api/cases/{id}/face-annotations`
    - `face_index` → GET `/api/cases/{id}/face-index`
  - Step 4 `setup_bc` description rewritten to flag the
    `defaultFaces`-only prerequisite + show the split workflow
    (face-index → face-annotations PUT → setup-bc)

- `scripts/dogfood/personas/prompts/{novice,experienced_fluent,debug}.md`:
  - All 3 prompts now include "Step 4 prerequisite — patch-split"
    section explaining the split workflow

- `ui/backend/tests/test_actions_catalogue.py`:
  - 2 new tests:
    - All 3 F7 query routes present in catalogue
    - setup_bc description mentions `defaultfaces` + `patch-classification` +
      `face-annotations`

## V130 / V132 contract

- The 3 new catalogue entries are GET (read-only); not added to
  `MUTATING_ROUTES`
- Catalogue ENUMERATES PUT `/face-annotations` + PUT
  `/patch-classification` (already in V132 MUTATING_ROUTES) but does
  not call them; persona invokes them via `http_post` (which the
  workbench translates to PUT — see executor)
- V132 contract test 21/21 still passes (Layer-A/B/C unchanged)

> Note on http_post → PUT: workbench tools currently expose only
> `http_get` and `http_post` to personas. PUT routes are accessible
> via the OpenAPI fallback if persona insists on the canonical method;
> for B-ext.2 we accept that personas may need to fall back to a
> generic POST or use openapi.json for PUT body shape. Adding
> `http_put` to the tool surface is B-ext-future scope.

## Four-question gate

| # | Q | A |
|---|---|---|
| Q1 | LLM offline → engineer can complete? | ✅ Catalogue entries are static; descriptions are self-contained |
| Q2 | Artifacts? | ✅ ActionsCatalogue wire shape unchanged (added entries) |
| Q3 | Audit explainable? | ✅ Each entry has description + URL with case_id substituted |
| Q4 | AI advisory only? | ✅ All 3 new entries GET; existing PUT routes already in V132 set |

## Verification

- 16/16 actions_catalogue tests pass (14 from B.5 + 2 new)
- 22/22 persona library tests pass (no regression from prompt edits)

## Confidence

`high` — content-only change to a hand-curated catalogue + 3
read-only routes that already existed.

## Notes

- F5 ↔ F7 coupling (per Kogami P2-1) addressed: BC `example_body`
  uses generic patch names (inlet/outlet/wall); persona prompts now
  guide them to split first via face-annotations
- `face-index`, `face-annotations`, `patch-classification` already
  exist as workbench routes; no new endpoints introduced
- HTTP method gap on personas (no `http_put`) acknowledged — if R4
  shows persona blocked specifically because PUT isn't reachable
  via `http_post`, scope a B-ext.4 with `http_put` tool

## References

- DEC-V61-172 · B-extend charter (parent)
- DEC-V61-173 · B-ext.1 (sister fix)
- `.planning/dogfood/DOGFOOD_REPORT_LIVE_PROGRESSION.md` §F7
- `.planning/reviews/kogami/b_arc_strategic_retro_2026-05-07/review.md` P2-1 (F5↔F7)
