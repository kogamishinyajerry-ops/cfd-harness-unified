---
eval_case_id: E23
case_id: case_038_rhoPimpleFoam_transonic_transient
title: rhoPimpleFoam transonic transient · NACA0012 M=0.8 buffet (compressible-transient)
v_row_attribution: [V70-DONE-2, GAP-rhoPimpleFoam-anchor]
v_row_class: V70 compressibility breadth · transient compressible anchor
physics_regime: compressible · transonic · transient · shock-induced separation
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_038/foamcase_buffet/
substrate_lineage: NACA0012 transonic case substrate + α=4° + M=0.78 buffet onset
expected_verdict_signature: "shock-induced separation onset · pressure oscillation freq ~110 Hz · matches Jacquin et al. 2009 buffet experiment ±10%"
---

# E23 · rhoPimpleFoam transonic transient · NACA0012 M=0.8 buffet (compressible-transient)

## Case summary

- **Physics regime**: compressible · transonic · transient · shock-induced separation
- **Substrate**: NACA0012 transonic case substrate + α=4° + M=0.78 buffet onset
- **Sandbox**: `workspace/projects/case_038/foamcase_buffet/`
- **Expected verdict signature**: shock-induced separation onset · pressure oscillation freq ~110 Hz · matches Jacquin et al. 2009 buffet experiment ±10%

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, GAP-rhoPimpleFoam-anchor.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | rhoPimpleFoam · pressure-velocity coupling for compressible transient |
| `compressibility_regime_advisor` | ✓ **info** | M=0.78 transonic + transient mode |
| `timestep_validator` | ✓ info | CFL < 1 for shock capture |
| `turbulence_model_advisor` | ✓ info | k-omega-SST appropriate for transonic BL |

## Anchor

V70.2 · V70 compressibility breadth · transient compressible anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
