# M-PANELS · Interactive Face-Naming Feature Request

**Date captured**: 2026-04-28
**Source**: CFDJerry direct request after M-VIZ Step-7 visual smoke
**Status**: Captured · NOT scoped into a milestone yet · target milestone = M-PANELS

---

## Requirement (verbatim from CFDJerry)

> 我在想，如果3D的CAD预览可以交互，例如我可以选中某个面，然后命名名称，
> 增加描述，会不会提升产品能力？如果你觉得这个功能不急着现在设计，也请
> 告知我。记住我的需求即可，开发安排还是按照你的建议来。

Translated requirement: enable engineers to **click a face on the 3D
viewport, assign it a name, and add a description**, so the named
patch can drive boundary-condition setup downstream. CFDJerry defers
the development schedule to Claude's recommendation but asks that
the requirement be remembered.

## Why this matters (product framing)

This is the **ParaView / ANSYS Workbench / Star-CCM+ standard**
interaction pattern: pick a face → name it (e.g. "inlet" / "outlet" /
"wall_no_slip") → BC selector in a downstream step references the
named patch. It collapses the geometry-import → BC-setup gap that
currently forces engineers to either:

1. Pre-name solids in CAD before STL export (multi-solid ASCII STL
   path · already supported by M5.0 ingest), OR
2. Hand-edit `case_manifest.yaml` after import (works but breaks the
   engineer-driven flow promised by Pivot Charter Addendum 3 §3.b).

For binary-STL imports or single-solid imports, neither path A nor B
is good UX. Interactive face-pick directly in the viewport is the
right primitive.

## Why NOT now (recommendation: defer to M-PANELS)

The feature spans three milestones, and building it before M-PANELS
locks in UX decisions in isolation:

### Backend (M-RENDER-API scope)
- `POST /api/cases/<id>/patches` — rename face groups, persist into
  `case_manifest.yaml` + `<case_dir>/constant/triSurface/<patch>.stl`
  (one STL per patch, the OpenFOAM convention M6.0/sHM expects)
- Triangle-id → patch-name lookup table for the viewport to consume
- Patch metadata schema (name + description + maybe tags like
  "inlet"/"outlet"/"wall" for downstream BC autopopulation)

### Renderer (M-VIZ.advanced scope)
- vtk.js cell-picker on the actor (vtkCellPicker + click handler)
- Hover-highlight on triangle/face groups (visual affordance)
- Triangle ID → backend patch lookup
- Visual differentiation of named vs. unnamed patches (color coding)

### UX (M-PANELS scope)
- Step 2 ("Geometry & Boundaries") is the natural surface
- Task-Panel (right side) shows the patch list + form
- Click face → form opens with current name (or "default")
- BC step (Step 3) consumes named patches as the BC target list

Building any of these in isolation — e.g. a viewport-only face-picker
in M-VIZ.advanced now — commits to UX decisions (overlay vs context
menu? hover-highlight color? group-pick lasso? rectangle select?)
without the surrounding step-panel context, with high redo risk
once M-PANELS lands.

## Recommendation

**Carry as a Tier-A candidate in M-PANELS scope when its kickoff DEC
is drafted** (after M-RENDER-API closes per Addendum 3 hard ordering).

If the CAD-export workaround proves painful for the Path-A stranger
recruit before M-PANELS lands, we can elevate this to an
**M-VIZ.bc-pick fast-track milestone** between M-RENDER-API and
M-PANELS — but only with explicit recruitment-pressure signal. The
default plan is M-PANELS-integrated.

## Forward checklist (when M-PANELS kickoff is drafted)

- [ ] Tier-A scope item: face-pick from viewport
- [ ] Tier-A scope item: Task-Panel patch-list + name+description form
- [ ] Tier-A scope item: backend patch-rename endpoint with persistence
- [ ] Tier-B scope item: BC-step consumes named patches
- [ ] Failure modes: pick-conflict on overlapping faces · ambiguous
  triangle ownership when STL has shared edges · undo/redo for
  accidental rename · what happens if engineer renames a patch the
  M5.0 ingest already named (e.g. multi-solid ASCII STL upload that
  came in pre-named)?
- [ ] Tradeoff: vtkCellPicker performance on >50k-triangle imports —
  spatial indexing? · same dependency as M-RENDER-API.perf
- [ ] CAD-side guardrail: still document the multi-solid ASCII STL
  workaround so engineers who already prefer that flow keep using it

## Linked requirement context

- M5.0 already supports multi-solid ASCII STL with named patches
  (existing workaround) — `multi_solid_ascii_stl` in
  `ui/backend/tests/conftest.py` + `test_geometry_ingest.py`
- Pivot Charter Addendum 3 §3.b (engineer-driven · no auto-advance)
  — face-pick + name is canonical engineer-driven step
- M-VIZ Tier-A landed read-only viewport (DEC-V61-094); interactive
  face-pick is explicitly a Tier-B item deferred per spec_v2 §Tier B
- Path-A engagement: stranger using binary STL without pre-naming will
  hit this gap; if surfaced before M-PANELS, treat as recruitment
  signal to fast-track
