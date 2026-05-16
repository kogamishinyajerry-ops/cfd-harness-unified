---
eval_case_id: E15
case_id: case_035_kEpsilon
title: kEpsilon at y+~1 wall-function mismatch (F-NEW-kEpsilon-wallfn-mismatch · B92 anti-pattern)
v_row_attribution: [F-NEW-kEpsilon-wallfn-mismatch]
v_row_class: V66-B yplus_regime_match LANDING witness
physics_regime: incompressible BL · WRONG model-mesh combination (kEpsilon at y+~1)
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_035/foamcase_v3/kEps_variant/
substrate_lineage: case_035 NASA TMR substrate + kEpsilon model + y+~1 mesh
expected_verdict_signature: "kEpsilon at y+~1 over-predicts Cf by 60-67% (wall function regime mismatch · B92 FAIL anti-pattern)"
---

# E15 · kEpsilon at y+~1 wall-function mismatch (F-NEW-kEpsilon-wallfn-mismatch · B92 anti-pattern)

## Case summary

- **Physics regime**: incompressible BL · WRONG model-mesh combination (kEpsilon at y+~1)
- **Substrate**: case_035 NASA TMR substrate + kEpsilon model + y+~1 mesh
- **Sandbox**: `workspace/projects/case_035/foamcase_v3/kEps_variant/`
- **Expected verdict signature**: kEpsilon at y+~1 over-predicts Cf by 60-67% (wall function regime mismatch · B92 FAIL anti-pattern)

## V-row attribution

**F-NEW-kEpsilon-wallfn-mismatch**: see V69.1 split of B104/B105 batched docs — V-row landing history preserved in `.planning/methodology/advisor_rules_v66b_expansion.md`.

## Expected advisor rule firings

| Rule | Expected fire | Why |
|---|---|---|
| `solver_block_advisor` | ✓ info | simpleFoam + kEpsilon |
| `inlet_outlet_validator` | ✓ info | |
| `yplus_regime_match_advisor` | ✓ **ERROR** | y+~1.2 in kEpsilon dead zone [5, 30] · B92 anti-pattern direct hit |
| `cf_canonical_choice_advisor` | ✓ warn | |
| `unit_detector` | ✓ info | |

## Anchor

F-NEW-kEpsilon-wallfn-mismatch · directly covered by `yplus_regime_match_advisor` (V66-B new advisor) → B92 anti-pattern now caught by advisor stack. **V13x-3 promotion candidate** (yplus_regime_match LANDING witnessed).

— V69.1 split from B104/B105 batched · 2026-05-16
