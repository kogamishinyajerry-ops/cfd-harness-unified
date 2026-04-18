## Case Summary

- Case ID: `differential_heated_cavity`
- Name: `Differential Heated Cavity (Natural Convection)`
- Description: `Dhir 2001 / Ampofo & Karayiannis 2003`
- Solver: `buoyantFoam`
- Turbulence Model: `k-omega SST`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Ra` = `10000000000`
- `aspect_ratio` = `1.0`
- `Pr` = `0.71`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Dhir 2001 / Ampofo & Karayiannis 2003`
- DOI: `10.1016/S0140-7007(02)00085-4`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `nusselt_number` | `30` | `relative=0.15` |

## Results vs Reference

- Match Rate: `0.00%`
- Verification Overall: `FAIL`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `nusselt_number` | `30` | `5.85` | `Under` | `False` |

## Attribution Analysis

- Primary Cause: `mesh_insufficient_for_Ra`
- Confidence: `MEDIUM`
- Suggested Follow-up: `IN_PROGRESS_FIX`
## CorrectionSpec Record

> suggest-only, not auto-applied

- Primary Cause: `mesh_insufficient_for_Ra`
- Confidence: `MEDIUM`
- Suggested Correction: `IN_PROGRESS_FIX`

## Project Progress

- Cases Complete: `7/15`
- Progress Ratio: `46.67%`
- AutoVerify Reports Present: `9`

## Verdict

- Verification Verdict: `FAIL`
- Convergence Status: `CONVERGED`
- Physics Status: `PASS`
