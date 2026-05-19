---
eval_case_id: E30
case_id: case_045_2D_symmetry_empty
title: 2D extrusion canonical · empty + symmetry BC anchor
v_row_attribution: [V70-DONE-2, BC-coverage-2D]
v_row_class: V70 BC breadth · 2D extrusion patterns
physics_regime: incompressible · laminar · steady · 2D
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_045/foamcase_2D/
substrate_lineage: lid_driven_cavity 2D extruded form · empty front/back · checks 2D handling consistency
expected_verdict_signature: "results identical to 3D 1-cell-thick equivalent ±0.5%"
---

# E30 · 2D extrusion canonical · empty + symmetry BC anchor

## Case summary

- **Physics regime**: incompressible · laminar · steady · 2D
- **Substrate**: lid_driven_cavity 2D extruded form · empty front/back · checks 2D handling consistency
- **Sandbox**: `workspace/projects/case_045/foamcase_2D/`
- **Expected verdict signature**: results identical to 3D 1-cell-thick equivalent ±0.5%

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, BC-coverage-2D.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | icoFoam |
| `bc_type_validator` | ✓ **info** | empty patches front/back · 2D handling correct |
| `symmetry_validator` | ✓ info | symmetry BC matches mirrored solution |
| `dimensionality_check` | ✓ info | 2D extrusion with 1-cell depth |

## Anchor

V70.2 · V70 BC breadth · 2D extrusion patterns. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
