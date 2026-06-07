---
eval_case_id: E22
case_id: case_037_rhoCentralFoam_supersonic
title: rhoCentralFoam supersonic wedge M=2.0 (closes advisor-without-anchor gap)
v_row_attribution: [V70-DONE-2, GAP-rhoCentralFoam-anchor]
v_row_class: V70 compressibility breadth · supersonic anchor
physics_regime: compressible · supersonic · steady · oblique shock
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_037/foamcase_supersonic/
substrate_lineage: θ-β-M oblique-shock relation (Anderson, Modern Compressible Flow Ch.4 / NACA Report 1135) + wedge geometry θ=15° + M_inf=2.0
expected_verdict_signature: "oblique shock angle β≈45.34° (analytical θ-β-M relation, weak root) · post-shock M2≈1.446 · ≤3% error vs analytical"
correction: "DEC-V61-232: β≈42° → β≈45.34° (42° corresponds to θ=12.36°, not 15°; weak-shock β for M=2.0/θ=15° is 45.34°). Substrate re-cited AGARD AR-211 (experimental) → θ-β-M relation (the wedge gold is analytical/inviscid, not experimental). See knowledge/gold_standards/wedge_oblique_shock.yaml."
---

# E22 · rhoCentralFoam supersonic wedge M=2.0 (closes advisor-without-anchor gap)

## Case summary

- **Physics regime**: compressible · supersonic · steady · oblique shock
- **Substrate**: θ-β-M oblique-shock relation (Anderson, *Modern Compressible Flow* Ch.4 / NACA Report 1135) + wedge geometry θ=15° + M_inf=2.0
- **Sandbox**: `workspace/projects/case_037/foamcase_supersonic/`
- **Expected verdict signature**: oblique shock angle β≈45.34° (analytical θ-β-M relation, weak root) · post-shock M2≈1.446 · ≤3% error vs analytical
  - **Correction (DEC-V61-232)**: the prior β≈42° was wrong — β=42° corresponds to θ=12.36°, not the stated 15° wedge. The correct weak-shock β for M=2.0, θ=15° is **45.34°** (strong-shock root 79.83°). M2≈1.45 was already correct. The analytical reference now lives in `knowledge/gold_standards/wedge_oblique_shock.yaml`, re-derived by `tests/p4/test_wedge_oblique_shock_gold.py`.

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
