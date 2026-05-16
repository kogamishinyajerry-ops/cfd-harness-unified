---
eval_case_id: E18
case_id: case_035_SA_yp5
title: case_035 SA y+=5 within-iter FULL (V103 + F-NEW-within-iter-residual)
v_row_attribution: [V103, F-NEW-within-iter-residual-qualifier]
v_row_class: LANDED (B97)
physics_regime: incompressible TBL · SA model · y+=5 mesh variant
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_035/foamcase_v65/SA_yp5_variant/
substrate_lineage: same NASA TMR substrate, different mesh grading=300
expected_verdict_signature: "SA + y+=5 · max |Δ%| 5.33% W + 2.79% SG · within-iter residual qualifier (Ux ~3e-4, not strict 1e-5)"
---

# E18 · case_035 SA y+=5 within-iter FULL (V103 + F-NEW-within-iter-residual)

## Case summary

- **Physics regime**: incompressible TBL · SA model · y+=5 mesh variant
- **Substrate**: same NASA TMR substrate, different mesh grading=300
- **Sandbox**: `workspace/projects/case_035/foamcase_v65/SA_yp5_variant/`
- **Expected verdict signature**: SA + y+=5 · max |Δ%| 5.33% W + 2.79% SG · within-iter residual qualifier (Ux ~3e-4, not strict 1e-5)

## V-row attribution

**V103**: see V69.1 split of B104/B105 batched docs — V-row landing history preserved in `.planning/methodology/advisor_rules_v66b_expansion.md`.

## Expected advisor rule firings

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info | |
| `solver_block_advisor` | ✓ info | simpleFoam + SA |
| `unit_detector` | ✓ info | |
| `urf_advisor` | ✓ info | |
| `cf_canonical_choice_advisor` | ✓ warn | |
| `low_re_kOmegaSST_trigger_advisor` | ✗ ANTI-FIRE | SA, not kOmegaSST |
| `yplus_regime_match_advisor` | ✓ **warn** (LOW) | y+ ~5 with SA = acceptable but not optimal (LOW severity per rule signature) |
| `residual_gate_qualifier_advisor` | ✗ MISSING | F-NEW gap — within-iter qualifier not yet rule |

## Anchor

y+=5 validates SA + nutUSpaldingWallFunction handles up-to-5 zone. F-NEW-residual-gate-qualifier captured as V13x-7 candidate (within-iter residual classification advisor).

— V69.1 split from B104/B105 batched · 2026-05-16
