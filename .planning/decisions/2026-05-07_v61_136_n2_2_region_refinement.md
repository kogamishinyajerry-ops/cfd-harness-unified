---
decision_id: DEC-V61-136
title: N2.2 · Region refinement zones (box / sphere · gmsh Box+Ball+Min field combinator)
status: Accepted
parent_dec: V61-134
phase: N2
notion_sync_status: pending
codex_review_relay: crs (gpt-5.4 default)
codex_review_rounds: R0 CHANGES_REQUIRED → R1 CHANGES_REQUIRED → R2 APPROVE
codex_review_chain: /tmp/n22_r{0,1,2}_review.md (transient · committed in body)
implementation_commits: 09a46f6 → ee9c6be → 40ad395
---

# DEC-V61-136 · N2.2 Region Refinement Zones

## Status

**Accepted 2026-05-07** — Codex CRS gpt-5.4 review chain closed at
R2 APPROVE on commit `40ad395`.

## Codex review chain

| Round | Commit | Verdict | Findings → Disposition |
|---|---|---|---|
| R0 | `09a46f6` | CHANGES_REQUIRED | P1 ZoneNumberInput coercion blocks negative / partial decimal edits → fixed in R1; P2 zonesOpen gates submit → fixed in R1 |
| R1 | `ee9c6be` | CHANGES_REQUIRED | P2 draft-only states submit stale parent value → fixed in R2; 2× P2 manifest references (out-of-scope · pre-existing dirty working tree from prior report-engine session, not in commits) → noted, not addressed |
| R2 | `40ad395` | APPROVE | clean — "narrowly scoped to blurring the active element before submission so draft-only zone input states cannot diverge from the submitted mesh payload, and the added test covers that behavior" |

Within V133 round cap=3.

## Decision

Add engineer-driven volume refinement zones to the
`POST /api/import/{case_id}/mesh` route. Each zone is a box or sphere
with a level (1-3); gmsh tightens characteristic length to
`effective_lc * 2**(-level)` inside the zone via Box/Ball size fields,
all combined under a Min field as the background mesh.

Empty list / None preserves N2.1 behavior verbatim. Backend rejects
zones with no spatial overlap with the case AABB via
`failing_check=refinement_zone_invalid` (HTTP 422), distinct from
`gmsh_diverged`.

## Scope

**Backend** (~360 LOC):
- New schema `ui/backend/schemas/mesh_refinement.py`:
  - Discriminated-union `MeshRefinementZone` on `geometry`
    (`BoxRefinementZone` / `SphereRefinementZone`)
  - Pydantic validators: zero-extent bbox, negative radius, level
    out-of-range
  - `lc_scale_for_level()` pure helper (parity with frontend `level
    × 0.5/0.25/0.125` display labels)
- Schema extensions: `MeshRequest.refinement_zones` (Optional list);
  `FailingCheck` enum gains `refinement_zone_invalid`
- Pipeline: `mesh_imported_case` accepts and forwards zones; new
  `MeshPipelineError(failing_check="refinement_zone_invalid")` arm
  catches `RefinementZoneError` from gmsh_runner
- gmsh_runner:
  - New `RefinementZoneError(ValueError)` exception class
  - New helpers: `_geometry_aabb`, `_box_intersects_aabb`,
    `_sphere_intersects_aabb`, `_validate_refinement_zones`
  - `_gmsh_inline` validates zones against AABB after STL merge,
    BEFORE `mesh.generate(3)`; out-of-domain zone surfaces with
    structured zone-index + AABB diagnostic
  - Field setup: per-zone Box/Ball field with VIn/VOut/Thickness;
    combined under Min field; `setAsBackgroundMesh`
  - Catch-block ordering: `RefinementZoneError` re-raises BEFORE the
    generic `except Exception` catch-all (otherwise relabels as
    `GmshMeshGenerationError` → wrong failing_check)
  - Subprocess marshal: zones list → list-of-dicts via `.model_dump()`
    (same pattern as N2.1 `sizing_field`)
  - Subprocess queue: new `refinement_zone_error` kind tag
- Route: `_STATUS_FOR_FAILING_CHECK` gains `refinement_zone_invalid: 422`

**Frontend** (~330 LOC):
- Types: `BoxRefinementZone`, `SphereRefinementZone`, `MeshRefinementZone`,
  `RefinementLevel`, `REFINEMENT_LEVEL_MIN/MAX` exports; `MeshFailingCheck`
  gains `refinement_zone_invalid`
- API client `meshImported` gains optional 4th arg `refinementZones`;
  body strips the field when undefined / empty (preserves V135 wire
  shape)
- Step2Mesh:
  - New collapsed `<details>` section "Refinement zones (box / sphere)"
    with repeater list + add buttons + clear-all + Remove per row
  - `RefinementZoneRow` component dispatches on `geometry` for the
    geometry-specific inputs (bbox 6-tuple vs center+radius)
  - Client-side pre-flight: zero / inverted bbox extent · radius ≤ 0
  - `REJECTION_HINTS["refinement_zone_invalid"]` text guides engineer

**Tests** (~120 LOC backend + ~80 LOC frontend):
- `ui/backend/tests/test_mesh_refinement_zones.py` — 40 unit + route
  tests (schema, AABB helpers, validation, route plumbing, pipeline
  precedence with sizing_field, route 422 translation)
- `ui/backend/tests/test_meshing_gmsh.py` — 3 callsites updated for
  new `refinement_zones` keyword arg
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step2Mesh.test.tsx`
  — 6 new tests (default-collapsed, add-box-zone wire payload, add-
  sphere-zone with radius edit, zero-extent client-side rejection,
  refinement_zone_invalid backend rejection hint, Remove button)
- `StepPanelShell.test.tsx` — 1 callsite updated for 4-arg meshImported

## Acceptance (V130 Principle B four-question gate)

| # | Question | Answer |
|---|---|---|
| 1 | LLM-offline reachability? | ✅ Engineer adds zones via form inputs in Step 2; no LLM call required. `LLM_PROVIDER=disabled` env preserves full mesh control flow. |
| 2 | Clear artifacts output? | ✅ Same `polyMesh/` + `imported.msh` + `MeshSummary` JSON as N2.1; refinement zone effects are visible in checkMesh output (cell-size delta verifiable). |
| 3 | TrustGate / completeness / audit explainable? | ✅ MeshQualityCard re-fetches post-mesh with new polyMesh; the response carries `mesh_mode_used` (preset / custom labels unchanged); `MeshRequest` body becomes part of the run's audit record. |
| 4 | AI advisory only? | ✅ No new mutating route (POST `/api/import/{case_id}/mesh` is unchanged at the V132 registry layer; refinement_zones is a new field on the existing schema). No AI surface added; engineer types values. V132 `MUTATING_ROUTES` registry unchanged. |

## Tests

- `ui/backend/tests/test_mesh_refinement_zones.py` — 40/40 ✅
- `ui/backend/tests/test_meshing_gmsh.py` (existing + 3 callsite fixes) — 35/35 ✅
- `ui/backend/tests/test_mesh_sizing_field.py` (N2.1 regression) — 16/16 ✅
- `ui/backend/tests/test_ai_advisor_contract.py` (V132 envelope) — 14/14 ✅
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/Step2Mesh.test.tsx` — 20/20 ✅
- Full frontend suite — 277/277 ✅
- Frontend `tsc --noEmit` — clean
- Pre-existing failures (9, on origin/main: codex_cadence test stale per V133, physics_contract render text drift, etc.) unaffected

## Risk

**Class**: medium (geometry validation edge cases; bbox out-of-domain
rejection; gmsh field combinator).

**Mitigations**:
- AABB validation rejects zero-overlap zones with structured 422
  before expensive `gmsh.model.mesh.generate(3)` runs
- Pydantic enforces zero-extent / negative-radius / level-out-of-range
  at request time (FastAPI 422 before pipeline call)
- 50M cell-budget hard cap unchanged (refinement zones can multiply
  cells; cell_budget guard catches the result regardless of how many
  zones the engineer adds)
- Subprocess marshalling discipline mirrored from N2.1 (list-of-dicts,
  not pickled pydantic models)
- Catch-block ordering verified by integration test: route 422 with
  `failing_check=refinement_zone_invalid` end-to-end, NOT collapsed
  to `gmsh_diverged`

## Out of scope (deferred)

- STL-bounded zone (snappyHexMesh `refinementSurfaces` / gmsh Distance
  field on a secondary triangulated surface) — N2.3+ territory
- Viewport bbox overlay rendering (zones are textual-form only in v0;
  a 3D bbox/sphere overlay can land in N2.2-extend without backend
  changes)
- AI advisor-suggested zones (N6 territory; gated by V132 contract —
  must remain GET-only / advisory)
- Multi-engine prism + zones (N2.3 introduces snappyHexMesh; zones
  configured here will continue to work unchanged because Min field
  combinator runs in the gmsh pre-stage)

## References

- DEC-V61-130 — V130 strategic pivot (workbench-first / AI-as-advisor)
- DEC-V61-132 — N1.2 MUTATING_ROUTES registry + behavioral contract
- DEC-V61-133 — V2.3 governance simplification (slim 6-field DEC schema)
- DEC-V61-134 — N2 phase charter
- DEC-V61-135 — N2.1 sizing field (precedent for subprocess marshalling
  + custom-label discipline)
- `.planning/strategic/n2_kickoff/spec_2026-05-07.md` §3.2 — N2.2 spec
- `.planning/strategic/blueprint_v3_2026-05-07.md` — Blueprint v3
  four-question gate

## confidence

**med** (initial) → **calibrated honest**. Schema + plumbing was
mechanical (high), but the frontend ZoneNumberInput correctness was
genuinely tricky — Codex caught the controlled-input numeric-coercion
issue (R0 P1) and the disclosure-vs-data UX confusion (R0 P2), then
caught a second-order draft-state submission issue (R1 P2) that the
R0 fix introduced. 3 rounds at the V133 ceiling is honest signal that
this surface deserved review; would not have caught any of these
solo. Counter-impact +1 (autonomous_governance: true).
