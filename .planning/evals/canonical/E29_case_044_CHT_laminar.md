---
eval_case_id: E29
case_id: case_044_CHT_laminar
title: chtMultiRegionFoam laminar substrate (conjugate heat transfer · laminar anchor)
v_row_attribution: [V70-DONE-2, case_002a-CHT-laminar]
v_row_class: V70 solver breadth · CHT-laminar anchor
physics_regime: incompressible · CHT · laminar · steady
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_044/foamcase_CHT_lam/
substrate_lineage: apu_bay_ventilation CHT substrate restricted to laminar fluid (no turbulence model)
expected_verdict_signature: "wall temperature profile matches steady conduction-convection coupled solution ±2°C"
---

# E29 · chtMultiRegionFoam laminar substrate (conjugate heat transfer · laminar anchor)

## Case summary

- **Physics regime**: incompressible · CHT · laminar · steady
- **Substrate**: apu_bay_ventilation CHT substrate restricted to laminar fluid (no turbulence model)
- **Sandbox**: `workspace/projects/case_044/foamcase_CHT_lam/`
- **Expected verdict signature**: wall temperature profile matches steady conduction-convection coupled solution ±2°C

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, case_002a-CHT-laminar.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | chtMultiRegionFoam · region-coupled |
| `turbulence_model_advisor` | ✓ info | laminar (fluid Re<1000 in narrow bay) |
| `region_coupling_validator` | ✓ **info** | fluid-solid interface temperature continuity |
| `compressibility_regime_advisor` | ✓ info | incompressible heat transfer |

## Anchor

V70.2 · V70 solver breadth · CHT-laminar anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
