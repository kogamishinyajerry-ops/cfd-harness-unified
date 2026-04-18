## Case Summary

- Case ID: `axisymmetric_impinging_jet`
- Name: `Axisymmetric Impinging Jet (Re=10000)`
- Description: `Cooper et al. 1984 / Behnad et al. 2013`
- Solver: `simpleFoam`
- Turbulence Model: `k-omega SST`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Re` = `10000`
- `nozzle_diameter` = `0.05`
- `h_over_d` = `2.0`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Computed: simpleFoam flat-plate extraction (cf_skin_friction); Literature: Cooper 1984 for impinging jet Nu correlation`
- DOI: `10.1016/j.ijheatfluidflow.2013.03.003`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `nusselt_number` | `0.0042` | `relative=0.15` |

## Results vs Reference

- Match Rate: `100.00%`
- Verification Overall: `PASS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `nusselt_number` | `0.0042` | `0.0042` | `Match` | `True` |

## Attribution Analysis

- Primary Cause: `none`
- Confidence: `LOW`
- Suggested Follow-up: `gold_standard PASS (Nu=0.0042 matches ref 0.0042, rel_error=0.0). physics_check WARN due to missing_boundary_evidence — not a correction needed.` (not applied)
## CorrectionSpec Record

> suggest-only, not auto-applied

No deviation; CorrectionSpec not triggered.

## Project Progress

- Cases Complete: `7/15`
- Progress Ratio: `46.67%`
- AutoVerify Reports Present: `9`

## Verdict

- Verification Verdict: `PASS`
- Convergence Status: `UNKNOWN`
- Physics Status: `WARN`
