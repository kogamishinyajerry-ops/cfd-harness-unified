## Case Summary

- Case ID: `rayleigh_benard_convection`
- Name: `Rayleigh-Bénard Convection (Ra=10^6)`
- Description: `Chaivat et al. 2006`
- Solver: `buoyantFoam`
- Turbulence Model: `laminar`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Ra` = `1000000`
- `Pr` = `0.71`
- `aspect_ratio` = `2.0`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Chaivat et al. 2006`
- DOI: `10.1016/j.ijheatmasstransfer.2005.07.039`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `nusselt_number` | `10.5` | `relative=0.15` |

## Results vs Reference

- Match Rate: `100.00%`
- Verification Overall: `PASS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `nusselt_number` | `10.5` | `10.5` | `Match` | `True` |

## Attribution Analysis

- Primary Cause: `solver_settings`
- Confidence: `MEDIUM`
- Suggested Follow-up: `Stabilize iteration history before trusting numerical comparisons.`
## CorrectionSpec Record

> suggest-only, not auto-applied

- Primary Cause: `solver_settings`
- Confidence: `MEDIUM`
- Suggested Correction: `Stabilize iteration history before trusting numerical comparisons.`

## Project Progress

- Cases Complete: `7/15`
- Progress Ratio: `46.67%`
- AutoVerify Reports Present: `9`

## Verdict

- Verification Verdict: `PASS_WITH_DEVIATIONS`
- Convergence Status: `OSCILLATING`
- Physics Status: `WARN`
