---
eval_case_id: E27
case_id: case_042_DNS_channel_highRe
title: DNS plane channel Re_tau=590 (resolved-scale anchor high-Re)
v_row_attribution: [V70-DONE-2]
v_row_class: V70 turbulence breadth · DNS high-Re anchor
physics_regime: incompressible · DNS · transient · resolved-scale
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_042/foamcase_DNS_590/
substrate_lineage: plane_channel_flow Re_tau=180 substrate scaled to Re_tau=590 · Moser-Kim-Mansour 1999
expected_verdict_signature: "U+(y+) and uu_rms(y+) within 3% of MKM 1999 Re_tau=590 reference"
---

# E27 · DNS plane channel Re_tau=590 (resolved-scale anchor high-Re)

## Case summary

- **Physics regime**: incompressible · DNS · transient · resolved-scale
- **Substrate**: plane_channel_flow Re_tau=180 substrate scaled to Re_tau=590 · Moser-Kim-Mansour 1999
- **Sandbox**: `workspace/projects/case_042/foamcase_DNS_590/`
- **Expected verdict signature**: U+(y+) and uu_rms(y+) within 3% of MKM 1999 Re_tau=590 reference

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | pimpleFoam DNS · no model |
| `turbulence_model_advisor` | ✓ **info** | resolved-scale DNS · grid Δx+~10 Δz+~5 Δy+~0.5 |
| `mesh_resolution_advisor` | ✓ info | DNS spectra criterion |
| `statistics_averaging_advisor` | ✓ info | ≥20 flow-through times |

## Anchor

V70.2 · V70 turbulence breadth · DNS high-Re anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
