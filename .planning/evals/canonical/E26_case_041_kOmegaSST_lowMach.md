---
eval_case_id: E26
case_id: case_041_kOmegaSST_lowMach
title: k-omega-SST low-Mach near-incompressible (weakly-compressible regime anchor)
v_row_attribution: [V70-DONE-2, GAP-weakly-compressible]
v_row_class: V70 compressibility breadth · weakly-compressible anchor
physics_regime: weakly-compressible · low-Mach · k-omega-SST · steady
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_041/foamcase_lowMach/
substrate_lineage: Heated cavity benchmark · M~0.05 · isothermal compressible (low-Mach limit) + k-omega-SST
expected_verdict_signature: "results match incompressible counterpart ±1% · validates low-Mach compressible-solver branch"
---

# E26 · k-omega-SST low-Mach near-incompressible (weakly-compressible regime anchor)

## Case summary

- **Physics regime**: weakly-compressible · low-Mach · k-omega-SST · steady
- **Substrate**: Heated cavity benchmark · M~0.05 · isothermal compressible (low-Mach limit) + k-omega-SST
- **Sandbox**: `workspace/projects/case_041/foamcase_lowMach/`
- **Expected verdict signature**: results match incompressible counterpart ±1% · validates low-Mach compressible-solver branch

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, GAP-weakly-compressible.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | rhoSimpleFoam · low-Mach branch |
| `compressibility_regime_advisor` | ✓ **info** | M~0.05 weakly-compressible regime |
| `inlet_outlet_validator` | ✓ info | fixedFluxPressure for low-Mach |
| `turbulence_model_advisor` | ✓ info | k-omega-SST with wall-resolved |

## Anchor

V70.2 · V70 compressibility breadth · weakly-compressible anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
