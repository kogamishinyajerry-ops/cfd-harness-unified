## Case Summary

- Case ID: `differential_heated_cavity`
- Name: `Differential Heated Cavity (Natural Convection, Ra=10^6 benchmark)`
- Description: `de Vahl Davis 1983 / Dhir 2001`
- Solver: `buoyantFoam`
- Turbulence Model: `laminar`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Ra` = `1000000`
- `aspect_ratio` = `1.0`
- `Pr` = `0.71`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `de Vahl Davis 1983`
- DOI: `10.1002/fld.1650030305`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `nusselt_number` | `8.8` | `relative=0.1` |

## Results vs Reference

- Match Rate: `0.00%`
- Verification Overall: `FAIL`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `nusselt_number` | `8.8` | `11.3676` | `Over` | `False` |

## Attribution Analysis

- Primary Cause: `pending_stage_e_live_run`
- Confidence: `HIGH`
- Suggested Follow-up: `IN_PROGRESS_FIX`
## CorrectionSpec Record

> suggest-only, not auto-applied

- Primary Cause: `pending_stage_e_live_run`
- Confidence: `HIGH`
- Suggested Correction: `IN_PROGRESS_FIX`

## Project Progress

- Cases Complete: `7/15`
- Progress Ratio: `46.67%`
- AutoVerify Reports Present: `9`

## Verdict

- Verification Verdict: `FAIL`
- Convergence Status: `CONVERGED`
- Physics Status: `PASS`
