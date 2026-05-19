---
eval_case_id: E22
case_id: case_037_rhoCentralFoam_supersonic
title: rhoCentralFoam supersonic wedge M=2.0 (closes advisor-without-anchor gap)
v_row_attribution: [V70-DONE-2, GAP-rhoCentralFoam-anchor]
v_row_class: V70 compressibility breadth · supersonic anchor
physics_regime: compressible · supersonic · steady · oblique shock
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_037/foamcase_supersonic/
substrate_lineage: AGARD AR-211 oblique shock benchmark + wedge geometry θ=15° + M_inf=2.0
expected_verdict_signature: "oblique shock angle β≈42° (analytical θ-β-M relation) · post-shock M2≈1.45 · ≤3% error vs analytical"
---

# E22 · rhoCentralFoam supersonic wedge M=2.0 (closes advisor-without-anchor gap)

## Case summary

- **Physics regime**: compressible · supersonic · steady · oblique shock
- **Substrate**: AGARD AR-211 oblique shock benchmark + wedge geometry θ=15° + M_inf=2.0
- **Sandbox**: `workspace/projects/case_037/foamcase_supersonic/`
- **Expected verdict signature**: oblique shock angle β≈42° (analytical θ-β-M relation) · post-shock M2≈1.45 · ≤3% error vs analytical

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, GAP-rhoCentralFoam-anchor.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | rhoCentralFoam · explicit central-upwind |
| `compressibility_regime_advisor` | ✓ **info** | supersonic M=2.0 anchors compressible-steady |
| `inlet_outlet_validator` | ✓ info | totalPressure + supersonic outflow |
| `shock_capture_quality_advisor` | ✓ info | minMod / vanLeer flux limiter |

## Anchor

V70.2 · V70 compressibility breadth · supersonic anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
