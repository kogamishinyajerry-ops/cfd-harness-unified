---
eval_case_id: E21
case_id: case_036_kOmegaSST_lowRe
title: k-omega-SST low-Reynolds case (closes V66-B low_re_kOmegaSST_trigger F-NEW)
v_row_attribution: [V70-DONE-2, F-NEW-kOmegaSST-lowRe]
v_row_class: V70 turbulence breadth · low-Re k-omega-SST anchor
physics_regime: incompressible · low-Re k-omega-SST · steady
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_036/foamcase_lowRe/
substrate_lineage: backward_facing_step substrate + Re=5000 + k-omega-SST low-Re tuning
expected_verdict_signature: "low-Re k-omega-SST resolves separation bubble without wall function · Cf within 5% of Driver 1985 reference"
---

# E21 · k-omega-SST low-Reynolds case (closes V66-B low_re_kOmegaSST_trigger F-NEW)

## Case summary

- **Physics regime**: incompressible · low-Re k-omega-SST · steady
- **Substrate**: backward_facing_step substrate + Re=5000 + k-omega-SST low-Re tuning
- **Sandbox**: `workspace/projects/case_036/foamcase_lowRe/`
- **Expected verdict signature**: low-Re k-omega-SST resolves separation bubble without wall function · Cf within 5% of Driver 1985 reference

## V-row attribution

V70.2 canonical eval breadth expansion (charter §3 V70-DONE-2). Anchors:
V70-DONE-2, F-NEW-kOmegaSST-lowRe.

## Expected advisor rule firings (4 rules)

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | simpleFoam + kOmegaSST |
| `yplus_regime_match_advisor` | ✓ **info** | y+~0.5-1 confirms low-Re resolved regime · no wall fn |
| `low_re_komegasst_trigger` | ✓ **info** | anchors V66-B planned advisor (was KNOWN_F_NEW in V69; canonicalized to lowercase for regex-parse enforcement) |
| `cf_canonical_choice_advisor` | ✓ info | Cf compared to Driver-Seegmiller 1985 |

## Anchor

V70.2 · V70 turbulence breadth · low-Re k-omega-SST anchor. Closes regime-breadth gap surfaced by V70.1 capability matrix.

— V70.2 canonical eval breadth expansion · 2026-05-16 · B162
