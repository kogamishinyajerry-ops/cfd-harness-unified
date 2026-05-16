---
eval_case_id: E24
case_id: case_039_SpalartAllmaras_stall
title: Spalart-Allmaras NACA0012 stall α=18° (5th turbulence model anchor)
v_row_attribution: [V70-DONE-2, GAP-SA-anchor]
v_row_class: V70 turbulence breadth · Spalart-Allmaras anchor
physics_regime: incompressible · separated flow · S-A 1-equation model
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_039/foamcase_SA_stall/
substrate_lineage: naca0012 substrate + α=18° (stall regime) + Spalart-Allmaras
expected_verdict_signature: "Cl_max ≈ 1.10 at α≈17° · post-stall trend matches NASA TMR S-A reference ±8%"
---

# E24 · Spalart-Allmaras NACA0012 stall α=18° (5th turbulence model anchor)

## Case summary

- **Physics regime**: incompressible · separated flow · S-A 1-equation model
- **Substrate**: naca0012 substrate + α=18° (stall regime) + Spalart-Allmaras
- **Sandbox**: `workspace/projects/case_039/foamcase_SA_stall/`
- **Expected verdict signature**: Cl_max ≈ 1.10 at α≈17° · post-stall trend matches NASA TMR S-A reference ±8%

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, GAP-SA-anchor.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | simpleFoam |
| `turbulence_model_advisor` | ✓ **info** | S-A 1-eq · anchor (5th model) |
| `separation_resolution_advisor` | ✓ warn | α=18° fully-separated · model fidelity gap warning |
| `yplus_regime_match_advisor` | ✓ info | y+~1 wall-resolved |

## Anchor

V70.2 · V70 turbulence breadth · Spalart-Allmaras anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
