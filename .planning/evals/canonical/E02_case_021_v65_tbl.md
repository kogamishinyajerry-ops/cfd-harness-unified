---
eval_case_id: E02
case_id: case_021_v65
title: NASA TMR flat plate · Cf-canonical-choice witness (V103)
v_row_attribution: [V103]
v_row_class: LANDED (B81)
physics_regime: incompressible turbulent BL · NASA TMR canonical
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_021/foamcase_v65/
substrate_lineage: NASA TMR turbulentFlatPlate (Wieghardt 1944 ZAMM)
expected_verdict_signature: "kOmegaSST + I=0.5% at Re_x ∈ [4e6, 1.92e7] expected Cf max |Δ%| < 12% vs Wieghardt · cross-canonical PS over-predicts ~5% · SG under-predicts ~3%"
---

# E02 · case_021_v65 NASA TMR flat plate (V103 Cf-canonical-choice)

## Case summary

- **Geometry**: 2.0m × 1.0m × 0.01m flat plate · NASA TMR turbulentFlatPlate substrate
- **Mesh**: 209k cells · 10-block grading · y+ ≤ 1.5 at first inlet station
- **Operating point**: U_∞ = 69.4 m/s · ν = 1.5e-5 m²/s · Re_L = 9.26e6
- **Solver**: simpleFoam steady RANS · kOmegaSST · I=0.5%
- **Stations**: Re_x ∈ [4e6, 1.92e7] across 5 sample locations

## V-row attribution

**V103 (LANDED B81)**: Cf canonical-choice depends on Re_x band. Cherry-pick risk is real — reporting against only most-favorable canonical hides systematic delta. Triple-canonical reporting (Wieghardt, PS, SG) is mandatory.

- **Wieghardt 1944**: experimental gold standard · valid Re_x < 5e6
- **Prandtl-Schlichting eq 21.11**: 0.0592·Re_x⁻⁰·² · valid Re_x < ~1e7
- **Schultz-Grunow 1941**: (2·log₁₀Re_x - 0.65)⁻²·³ · valid 5e6 < Re_x < 5e7

## Expected advisor rule firings

| Rule | Expected fire | Severity | Why |
|---|---|---|---|
| `inlet_outlet_validator` | ✓ | info | freestream BC |
| `solver_block_advisor` | ✓ | info | simpleFoam + kOmegaSST |
| `unit_detector` | ✓ | info | SI throughout |
| `urf_advisor` | ✓ | info | URF defaults adequate |
| **`cf_canonical_choice_advisor` (V103 NEW)** | ✓ | **warn** | **Re_x range [4e6, 1.92e7] spans cross-canonical zone — triple-canonical report required** |
| **`yplus_regime_match_advisor` (NEW)** | ✓ | info | y+ ≤ 1.5 in kOmegaSST low-Re band (in_band) |
| `low_re_kOmegaSST_trigger_advisor` | ✗ | — | Re_x > 3e6 zone, not low-Re trigger |

**Expected fire count**: 5-6 / 14 advisors. Headline: `cf_canonical_choice_advisor` warns on cross-zone Re_x range.

## Expected verdict pattern

```yaml
verdict: strict-FULL (V64-A) → re-validated under V103 with cross-canonical report
cf_check:
  - Re_x=4.0e6: Cf_OF / Cf_Wieghardt = 0.96 (-4%) · Cf_PS = 1.02 (+2%) · Cf_SG = 0.99 (-1%)
  - Re_x=9.5e6: Cf_OF / Cf_Wieghardt = 0.92 (-8%) · Cf_PS = 0.98 (-2%) · Cf_SG = 0.94 (-6%)
  - Re_x=1.92e7: Cf_OF / Cf_Wieghardt = 0.88 (-12%) · Cf_PS = 0.95 (-5%) · Cf_SG = 0.91 (-9%)
v_rows_validated: [V103]
advisor_signals: [cf_canonical_choice_warn cross-zone, yplus_regime_info in_band]
```

## Why this case anchors V103

Single-canonical reporting (just Wieghardt) hides systematic over/under-prediction at outer Re_x stations. Triple-canonical report exposes the picture: PS over-predicts at high Re_x while SG under-predicts; the truth bracket reveals the model's actual behavior.

## Anti-regression check

If only 1 canonical reported in eval log → `cf_canonical_choice_advisor` failed to fire → V103 coverage broken → REGRESSION.

If `yplus_regime_match_advisor` reports y+~1.5 as "dead zone" → wrong regime band logic → REGRESSION.

— B102 · V66-B Done #2 eval-case detail · 2026-05-16
