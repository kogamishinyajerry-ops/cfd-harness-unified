---
eval_case_id: E17
case_id: case_035_SA_yp1
title: case_035 SA y+=1 DOUBLE-FULL (V103 + V107 anti-fire validation)
v_row_attribution: [V103, V107_anti-fire]
v_row_class: LANDED (B94)
physics_regime: incompressible TBL · NASA TMR canonical · SA model
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_035/foamcase_v65/SA_variant/
substrate_lineage: OpenFOAM 2312 turbulentFlatPlate + Spalart-Allmaras override
expected_verdict_signature: "SA + y+=1 on NASA TMR substrate · max |Δ%| 2.23% W + 6.76% SG · DOUBLE-CANONICAL FULL · 4× better than kOmegaSST B91"
---

# E17 · case_035 SA y+=1 DOUBLE-FULL (V103 + V107 anti-fire validation)

## Case summary

- **Physics regime**: incompressible TBL · NASA TMR canonical · SA model
- **Substrate**: OpenFOAM 2312 turbulentFlatPlate + Spalart-Allmaras override
- **Sandbox**: `workspace/projects/case_035/foamcase_v65/SA_variant/`
- **Expected verdict signature**: SA + y+=1 on NASA TMR substrate · max |Δ%| 2.23% W + 6.76% SG · DOUBLE-CANONICAL FULL · 4× better than kOmegaSST B91

## V-row attribution

**V103**: see V69.1 split of B104/B105 batched docs — V-row landing history preserved in `.planning/methodology/advisor_rules_v66b_expansion.md`.

## Expected advisor rule firings

| Rule | Expected fire | Why |
|---|---|---|
| `inlet_outlet_validator` | ✓ info | |
| `solver_block_advisor` | ✓ info | simpleFoam + SA |
| `unit_detector` | ✓ info | |
| `urf_advisor` | ✓ info | |
| `cf_canonical_choice_advisor` | ✓ warn | cross-zone Re_x [1e6, 5e6] |
| `low_re_kOmegaSST_trigger_advisor` | ✗ ANTI-FIRE | SA model, not kOmegaSST — anti-fire is correct (avoid false positive) |
| `yplus_regime_match_advisor` | ✓ info | y+ 0.90 in SA optimal band (≤1 preferred) |

## Anchor

SA is the workaround recommended by V107 for low-Re BL. This case validates the workaround works (4× better than B91 kOmegaSST). Anti-fire on `low_re_kOmegaSST_trigger_advisor` validates rule selectivity.

— V69.1 split from B104/B105 batched · 2026-05-16
