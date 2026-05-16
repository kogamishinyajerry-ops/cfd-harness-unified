---
eval_case_id: E16
case_id: case_035_v65
title: NASA TMR turbulentFlatPlate kOmegaSST · 1st industrial FULL (B91)
v_row_attribution: [V103, V107_cross_fire]
v_row_class: LANDED + industrial-FULL benchmark
physics_regime: incompressible TBL · NASA TMR canonical · OpenFOAM tutorial substrate
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_035/foamcase_v65/
substrate_lineage: OpenFOAM 2312 tutorials/incompressible/simpleFoam/turbulentFlatPlate (NASA TMR Wieghardt 1944)
expected_verdict_signature: "kOmegaSST + y+=1 NASA TMR substrate · Cf max |Δ%| 9.19% Wieghardt · 5/5 strict-FULL residuals · 1st industrial FULL of V65-A arc"
---

# E16 · case_035_v65 NASA TMR kOmegaSST FULL (B91)

## Case summary

- **Geometry**: OpenFOAM 2312 tutorial turbulentFlatPlate substrate (NASA TMR canonical)
- **Mesh**: 16k cells · y+ avg 0.90 (purpose-built for low-Re y+~1 BL)
- **Operating point**: U_∞ = 69.4 m/s · ν = 1.5e-5 m²/s
- **Solver**: simpleFoam steady RANS · kOmegaSST · I=0.5%
- **Stations**: Re_x ∈ [1e6, 5e6] across 5 sample locations

## V-row attribution

This case is the **1st industrial FULL** of V65-A arc (B91). Validation lineage:
- **V103**: triple-canonical Cf reporting required (cross-zone Re_x)
- **V107 cross-fire**: low Re_x portion overlaps trigger zone [1e6, 3e6]

## Expected advisor rule firings

| Rule | Expected fire | Severity | Why |
|---|---|---|---|
| `inlet_outlet_validator` | ✓ | info | freestream + symmetry top |
| `solver_block_advisor` | ✓ | info | simpleFoam + kOmegaSST |
| `unit_detector` | ✓ | info | SI throughout |
| `urf_advisor` | ✓ | info | URF defaults work for canonical |
| **`cf_canonical_choice_advisor` (V103 NEW)** | ✓ | warn | Re_x range overlaps cross-canonical zone (W vs PS vs SG) |
| **`low_re_kOmegaSST_trigger_advisor` (V107 NEW)** | ✓ | **warn** | I=0.5% + Re_x ∈ [1e6, 3e6] partial overlap → expected ~10% under-pred at low-Re end |
| **`yplus_regime_match_advisor` (NEW)** | ✓ | info | y+ 0.90 in kOmegaSST low-Re band (in_band) |
| `face_orientation_advisor` | ✗ | — | 2D, no MRF |
| `mesh_quality_advisor` | ✗ | — | clean tutorial mesh |

**Expected fire count**: 4-5 (clean canonical) + 3 NEW V66-B = **7 / 14 advisors**.

## Expected verdict pattern (HISTORICAL · B91 LANDED)

```yaml
verdict: FULL (1st industrial FULL of V65-A · B91)
cf_check:
  - Re_x=1.0e6: Cf_OF / Cf_Wieghardt = 0.91 (-9.0%) [V107 low-Re under-pred predicted]
  - Re_x=2.0e6: Cf_OF / Cf_Wieghardt = 0.93 (-7.2%)
  - Re_x=3.0e6: Cf_OF / Cf_Wieghardt = 0.94 (-6.1%)
  - Re_x=4.0e6: Cf_OF / Cf_Wieghardt = 0.95 (-5.0%)
  - Re_x=5.0e6: Cf_OF / Cf_Wieghardt = 0.91 (-9.19%) [max delta]
residuals: 5/5 strict-FULL (Ux/Uy/p/k/omega < 1e-5)
yplus_avg: 0.90
v_rows_validated: [V103, V107_cross_fire]
advisor_signals:
  - cf_canonical_choice_warn
  - low_re_kOmegaSST_trigger_warn (predicted the observed under-pred)
  - yplus_regime_info in_band
```

## Why this case anchors industrial FULL benchmarking

E16 is the **substrate pivot** demonstration: when custom mesh attempts (B87/B88/B90) failed 3 times in a row chasing y+~1 BL on curved geometry, switching to OpenFOAM purpose-built NASA TMR substrate yielded FULL on first try. Methodology lesson: prefer canonical tutorial substrate over custom mesh for low-Re y+~1 BL.

## Anti-regression check

If `low_re_kOmegaSST_trigger_advisor` fails to fire → V107 advisor coverage broken → REGRESSION (the case is exactly its trigger condition).

If `cf_canonical_choice_advisor` fails to fire → V103 advisor coverage broken → REGRESSION.

If only 1 canonical reported in eval log → cherry-pick detected → REGRESSION.

## Cross-fire with E17/E18 (same substrate, different turbulence model / y+)

- **E17 (case_035_SA y+=1, B94)**: SA on same mesh · max |Δ%| 2.23% W + 6.76% SG · **DOUBLE-CANONICAL FULL** · 4× better than B91 (kOmegaSST)
- **E18 (case_035_SA y+=5, B97)**: SA on different mesh · max |Δ%| 5.33% W + 2.79% SG · within-iter residual qualifier

Three FULL benchmarks on same substrate with varying model/y+ demonstrate the advisor stack must distinguish them by `yplus_regime_match_advisor` + model class.

— B102 · V66-B Done #2 eval-case detail · 2026-05-16
