---
eval_case_id: E25
case_id: case_040_pimpleFoam_kEpsilon_transient
title: pimpleFoam k-epsilon transient channel (transient k-epsilon anchor)
v_row_attribution: [V70-DONE-2, F-NEW-kEpsilon-transient]
v_row_class: V70 turbulence × steadiness · transient k-epsilon
physics_regime: incompressible · k-epsilon RANS · transient
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_040/foamcase_pimple_kEps/
substrate_lineage: plane_channel_flow substrate + k-epsilon + pimpleFoam (transient) + statistics-averaging window
expected_verdict_signature: "time-averaged U+(y+) matches steady-state simpleFoam k-epsilon ±2% after t/τ=50 averaging"
---

# E25 · pimpleFoam k-epsilon transient channel (transient k-epsilon anchor)

## Case summary

- **Physics regime**: incompressible · k-epsilon RANS · transient
- **Substrate**: plane_channel_flow substrate + k-epsilon + pimpleFoam (transient) + statistics-averaging window
- **Sandbox**: `workspace/projects/case_040/foamcase_pimple_kEps/`
- **Expected verdict signature**: time-averaged U+(y+) matches steady-state simpleFoam k-epsilon ±2% after t/τ=50 averaging

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, F-NEW-kEpsilon-transient.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | pimpleFoam · transient with PIMPLE coupling |
| `turbulence_model_advisor` | ✓ info | k-epsilon with high-Re wall fn (y+~30) |
| `statistics_averaging_advisor` | ✓ info | ≥10 flow-through times before averaging starts |
| `yplus_regime_match_advisor` | ✓ info | y+~30 confirms wall-fn regime |

## Anchor

V70.2 · V70 turbulence × steadiness · transient k-epsilon. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
