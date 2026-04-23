---
decision_id: DEC-V61-050
title: LDC true multi-dimensional validation · independent physical observables · v_centerline + streamfunction + vortex cores
status: IMPLEMENTATION_COMPLETE (all 4 batches landed 2026-04-23 · pending post-merge Codex review)
commits_in_scope:
  - 1d3505c feat(ldc): batch 1 — v_centerline (Ghia Table II) as independent observable
  - 2fb9c44 feat(ldc): batch 2 — streamfunction ψ extraction infrastructure
  - 8475c29 feat(ldc): batch 3 — primary vortex (x_c, y_c, ψ_min) wired to D7
  - TBD feat(ldc): batch 4 — secondary vortices BL/BR wired to D8
codex_verdict: PENDING (batch 1 post-merge Codex review triggered by "CFD new observable + adapter >5 LOC + comparator extension")
autonomous_governance: true
autonomous_governance_counter_v61: 37
external_gate_self_estimated_pass_rate: 0.70
codex_tool_report_path: (pending post-batch-1 Codex review)
notion_sync_status: synced 2026-04-23T13:50 (page_id=34bc6894-2bed-818e-a692-cab52be61282, Status=Accepted, https://www.notion.so/DEC-V61-050-LDC-true-multi-dimensional-validation-4-independent-Ghia-observables-34bc68942bed818ea692cab52be61282)
github_sync_status: pushed (1f1ff6b on origin/main, 4-commit arc)
related:
  - DEC-V61-049 (LDC single-case pilot · 5-dim Compare tab honesty footer noted this DEC as the "true 6-dim expansion" successor — V61-049 only promoted existing back-end data; V61-050 adds NEW physical observables)
  - DEC-V61-030 (Q-5 Path A u_centerline Ghia Table I correctness fix · establishes the "gold YAML must be Ghia-faithful" precedent)
  - This DEC **extends** V61-049 by adding genuinely independent
    dimensions. V61-049's Compare tab achieved 5 "views" but 4 of
    them (D2-D5) were all refractions of the single u_centerline
    observable. V61-050 adds v_centerline (already independent of u),
    then streamfunction-derived vortex cores (also independent).
    After all 4 batches, the Compare tab surfaces **4 genuinely
    orthogonal physical observables** from Ghia 1982: u(y) on vertical
    centerline, v(x) on horizontal centerline, primary vortex core
    (x_c, y_c, ψ_min), secondary vortex cores BL/BR.
---

## Context

User request (2026-04-23): "真 5 维必须做" — after DEC-V61-049 batch C landed a multi-dimensional Compare tab, the honesty footer conceded that 4 of 5 dimensions (D2-D5) were different views on the same u_centerline data, not independent physical observables. V61-049's gate was UI promotion; V61-050's gate is adding real independent observables.

## Problem statement

Lid-driven cavity (Ghia 1982 Re=100) has at least **four** independent gold-standard observables in the literature:

| # | observable | Ghia table | axis indexed by | independence |
|---|---|---|---|---|
| 1 | u(y) on vertical centerline x=0.5 | Table I | y ∈ [0,1] | u_centerline — already validated (V61-030) |
| 2 | v(x) on horizontal centerline y=0.5 | Table II | x ∈ [0,1] | v_centerline — independent of u (different axis, different velocity component) |
| 3 | primary vortex center (x_c, y_c) + ψ_min | Table III | 2D argmin of ψ | streamfunction-derived, independent of line-probes |
| 4 | secondary vortices BL + BR | Table III | 2D local extrema of ψ | sub-cellular eddies near corners |

Pre-V61-050, only #1 is exercised by the audit comparator. Items #2-#4 are stored in `knowledge/gold_standards/lid_driven_cavity.yaml` but flagged `satisfied_by_current_adapter=false` with documented reasons (wrong axis labels, wrong values, no extractor). The Compare tab honesty footer says so in plain text.

## Scope

### Batch 1 · v_centerline (this batch — landed)

1. **Gold YAML fix** — Replace the prior mislabelled v_centerline block (axis label "y" but values were Ghia Table II x-indexed) with Ghia's **native 17-point non-uniform x grid** (no interpolation) + exact Table II v values. Source cross-verified against `scripts/flow-field-gen/generate_contours.py:103-110` which encoded the same 17 points for the literature-reference visualization since DEC-V61-007.
2. **Precondition flip** — `physics_contract.physics_precondition[3]` `satisfied_by_current_adapter: false → true` with evidence_ref citing post-hoc VTK interpolation. `contract_status: SATISFIED_FOR_U_AND_V_CENTERLINE`.
3. **Post-hoc VTK populator** — `scripts/populate_ldc_v_centerline_post_hoc.py`: idempotent script loading the existing `reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK/*.vtk` volume and interpolating U at 17 Ghia-native x points + 129 uniform render points onto the y=0.05 (physical) line. Writes both `sample/1000/vCenterline.xy` (legacy path the comparator reads) and `postProcessing/sets/1024/vCenterline_U.xy` + `vCenterlineGold_U.xy` (modern path the updated generator would write). **No simpleFoam re-run needed** — the underlying audit field is the same; we're just sampling a line the old generator didn't emit.
4. **Generator update** — `src/foam_agent_adapter.py::_emit_phase7a_function_objects` adds a `vCenterline` lineUniform function object so future LDC runs produce v_centerline natively (no post-hoc step needed for new fixtures).
5. **Backend comparator** — `ui/backend/services/comparison_report.py::build_report_context` now computes `metrics_v_centerline` + `paper_v_centerline` when gold has a `v_centerline` block and the fixture has a `vCenterline.xy`. `_load_sample_xy` gained a `value_col` parameter (default 1 for u; 2 for v_y on a horizontal line).
6. **Frontend D6 panel** — `LearnCaseDetailPage.tsx::MultiDimensionComparePanel` adds a D6 section rendering v_centerline verdict + L²/L∞/max/RMS + per-point dev. Dimension counter in header incremented. Honesty footer updated: v_centerline is now GREEN (supported); primary_vortex_location remains RED (batch 3 scope).

### Batch 2 · ψ streamfunction extraction (scoped)

Solve ∇²ψ = −ω_z on the structured cavity mesh, OR integrate U_x dy along rows (U_x = ∂ψ/∂y) to build ψ(x, y) from the existing VTK U field. New helper module `ui/backend/services/psi_extraction.py`. Output: `ψ.xy` gridded array on the fixture mesh, cached per fixture.

### Batch 3 · primary vortex (x_c, y_c) + ψ_min (scoped)

argmin ψ over the interior → (x_c, y_c). Gold YAML fix: (0.5000, 0.7650) → (0.6172, 0.7344) with ψ_min = −0.103423 from Ghia Table III. New comparator dim `metrics_primary_vortex` with 2D position error in normalized units + strength match.

### Batch 4 · secondary vortices BL/BR (scoped)

Detect local ψ extrema in the corners (x<0.2 & y<0.2 for BL; x>0.8 & y<0.2 for BR). Gold YAML: new v4 block listing Ghia Table III values for Re=100. Relaxed tolerance (0.1–0.2) because sub-cellular eddies are finite-grid sensitive.

## Batch 1 concrete delta (this commit)

- `knowledge/gold_standards/lid_driven_cavity.yaml` — v_centerline block rewrite + header note + precondition flip
- `scripts/populate_ldc_v_centerline_post_hoc.py` — NEW · 152 LOC · idempotent post-hoc populator (13/17 gold points within ±5%, L2=0.00406, max |dev|=5.73% — within tolerance)
- `src/foam_agent_adapter.py::_emit_phase7a_function_objects` — add second lineUniform set (~8 LOC)
- `ui/backend/services/comparison_report.py` — `_load_sample_xy` value_col param + `_load_ldc_v_gold()` helper + v metrics wiring in `build_report_context` (~60 LOC)
- `ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx` — ComparisonReportContext type expansion + D6 panel + honesty footer rewrite (~60 LOC)

Total batch 1: ~280 LOC + 1 gold YAML rewrite + 1 new script.

## Known limitations / honesty footer

- **max_dev_pct = 2923% at x=1 endpoint** — `_compute_metrics` divide-by-zero guard uses 1e-9 floor when gold=0.0, which blows up at the two wall endpoints where Ghia v = 0 exactly. Per-point n_pass (12/17 in API, 13/17 in the populator sanity check) is still honest because the fail count is dominated by the 4-5 interior points between x=0.23 and x=0.94 where measured vs gold finite-grid discrepancy is ~5-7%, not by the endpoints. Fix is a separate small PR (not batch 1 scope): bump the divide-by-zero floor to 1e-3 to match the populator's sanity-check convention, or switch to absolute-error-only reporting at the walls.
- **Post-hoc interpolation vs native sampling** — The populator does linear sampling from the volume VTK via pyvista; this is less accurate than OpenFOAM's native `sample` function object (which does proper cell-interpolation on the full mesh). The residual ~5% deviation in the interior is partially this interpolation error, not simulation error. Batch 2+ will either re-run the fixture (expensive, changes fixture commit-sha pin) or live with the artifact.
- **primary_vortex_location still wrong** — Gold YAML still lists (0.5000, 0.7650) which does not match Ghia Re=100. Honesty footer on Compare tab D6 calls this out explicitly. Fix is batch 3 scope.

## Exit gate

- Batch 1: user re-visits `/learn/cases/lid_driven_cavity`, Compare tab shows D1-D6 with v_centerline PASS 12/17 + honesty footer showing only primary_vortex_location as RED. Codex post-merge review (triggered by "CFD new observable + adapter >5 LOC + comparator extension") returns APPROVE or APPROVE_WITH_COMMENTS.
- Batches 2-4: separate exit gates per batch. Batch 3 gates on vortex-location verdict rendering. Batch 4 gates on BL/BR corner detection + Ghia Table III comparison. All 4 together → contract_status: "FULLY_SATISFIED_ALL_4_GHIA_TABLES".

## Rejected alternatives

- **Re-run simpleFoam** to get native `vCenterline` sample — rejected: would change fixture timestamp (currently pinned 20260421T082340Z with commit-sha to fixture provenance in the audit chain) + costs 2-3 hours + does not improve the gold-comparator math. Post-hoc interpolation is honest about its error bars.
- **Interpolate Ghia Table II to a uniform 17-point x grid** (to match u_centerline's uniform y grid for code symmetry) — rejected: linear interpolation over Ghia's 0.2344→0.5 gap underestimates the curve by ~20%. Ghia's native non-uniform points deliberately cluster where the curve varies steepest. Honesty demands using Ghia's own grid.
- **Collapse batches 2-4 into one commit** — rejected: streamfunction extraction (batch 2) is infrastructure that batches 3-4 both depend on. Landing it separately makes the dependency chain obvious and keeps each commit reviewable.
