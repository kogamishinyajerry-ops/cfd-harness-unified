---
eval_case_id: E01
case_id: case_004_v4
title: NREL Phase VI rotor MRF (chord-axis convention witness)
v_row_attribution: [V101]
v_row_class: LANDED (B81 case_004_v4)
physics_regime: rotor MRF · incompressible · low-speed wind turbine
status: ACTIVE_EVAL
sandbox_path: workspace/projects/case_004/foamcase_v4/
substrate_lineage: NREL Phase VI blind comparison (Hand 2001 NREL/TP-500-29494)
expected_verdict_signature: "MRF rotor at 7 m/s · chord-axis convention with normal-to-chord = thrust direction · expected Cp r/R=0.30 0.85±0.05 · 0.63 1.40±0.10 · 0.95 0.55±0.05"
---

# E01 · case_004_v4 NREL Phase VI MRF (V101 chord-axis convention)

## Case summary

- **Geometry**: NREL Phase VI 2-bladed S809 rotor · R=5.029m · 7° pitch · 72 RPM
- **Operating point**: U_∞=7 m/s · ρ=1.225 kg/m³ · ν=1.5e-5 m²/s
- **Solver**: simpleFoam + MRFZone · steady RANS · kOmegaSST
- **Mesh**: ~2.4M cells · O-grid around blade · 3 azimuthal sectors with rotational periodicity OR full 2-blade

## V-row attribution

**V101 (LANDED B81)**: chord-axis convention — rotor pressure-side force decomposition requires **normal-to-chord** axis for thrust, not global Z. Cherry-picking global-Z gives Cp errors > 15% at outboard stations.

- Witnesses: case_004_v3 (B79 prep), case_004_v4 (B81 PARTIAL strict-FULL on inner 70% span)
- Reference: Hand 2001 NREL/TP-500-29494 Tables 4-8 · §3.3 pressure tap convention

## Expected advisor rule firings

| Rule | Expected fire | Severity | Why |
|---|---|---|---|
| `face_orientation_advisor` | ✓ | warn | MRF zone face orientation critical (V101 root cause) |
| `urf_advisor` | ✓ | info | rotor MRF needs URF ≤ 0.5 for U, 0.3 for k/omega |
| `solver_block_advisor` | ✓ | info | simpleFoam + MRFProperties dict required |
| `mesh_quality_advisor` | maybe | info | non-orthogonality at hub junction often > 65° |
| `cf_canonical_choice_advisor` | ✗ | — | rotor 3D, not 2D BL |
| `low_re_kOmegaSST_trigger_advisor` | ✗ | — | Re_c at outboard ~5e5 but not flat BL |
| `yplus_regime_match_advisor` | maybe | info | if y+ target documented, fires info |

**Expected fire count**: 3-4 / 14 advisors.

## Expected verdict pattern

```yaml
verdict: PARTIAL (inner 70% span strict-FULL · outboard 30% PARTIAL due to dynamic stall)
cf_or_cp_check:
  - r/R=0.30: Cp_max within ±5% NREL Hand 2001
  - r/R=0.63: Cp_max within ±10% (transition zone)
  - r/R=0.95: Cp_max within ±20% (tip vortex region, MRF inadequate)
v_rows_validated: [V101]
advisor_signals: [face_orientation_warn, urf_info, solver_block_info]
```

## Why this case anchors V101

The chord-axis convention finding ONLY surfaces when rotor pressure data exists across multiple radial stations. Flat-plate cases never trigger this. case_004 is the canonical witness — re-running this case must re-fire `face_orientation_advisor` to prevent V101 regression.

## Anti-regression check

If `face_orientation_advisor` fails to fire on E01 → V101 advisor coverage broken → REGRESSION.

— B102 · V66-B Done #2 eval-case detail · 2026-05-16
