---
eval_case_id: E28
case_id: case_043_LES_backstep
title: LES Smagorinsky backstep ReH=5000 (LES anchor · opens KNOWN_F_NEW LES gap)
v_row_attribution: [V70-DONE-2, F-NEW-LES-anchor]
v_row_class: V70 turbulence breadth · LES anchor
physics_regime: incompressible · LES · transient · sub-grid Smagorinsky
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_043/foamcase_LES_backstep/
substrate_lineage: backward_facing_step substrate · ReH=5000 · LES Smagorinsky C_s=0.17
expected_verdict_signature: "reattachment length x_r/H ≈ 6.0 ± 0.3 · matches Le-Moin 1997 LES reference"
---

# E28 · LES Smagorinsky backstep ReH=5000 (LES anchor · opens KNOWN_F_NEW LES gap)

## Case summary

- **Physics regime**: incompressible · LES · transient · sub-grid Smagorinsky
- **Substrate**: backward_facing_step substrate · ReH=5000 · LES Smagorinsky C_s=0.17
- **Sandbox**: `workspace/projects/case_043/foamcase_LES_backstep/`
- **Expected verdict signature**: reattachment length x_r/H ≈ 6.0 ± 0.3 · matches Le-Moin 1997 LES reference

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, F-NEW-LES-anchor.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | pimpleFoam LES · sub-grid model active |
| `turbulence_model_advisor` | ✓ **info** | Smagorinsky LES · C_s=0.17 |
| `mesh_resolution_advisor` | ✓ warn | LES Δx+/Δy+/Δz+ < 50/1/30 criterion · check spectra |
| `statistics_averaging_advisor` | ✓ info | ≥15 flow-through times for LES |

## Anchor

V70.2 · V70 turbulence breadth · LES anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
