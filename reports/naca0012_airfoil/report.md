## Case Summary

- Case ID: `naca0012_airfoil`
- Name: `NACA 0012 Airfoil External Flow`
- Description: `Thomas 1979 / Lada & Gostling 2007`
- Solver: `simpleFoam`
- Turbulence Model: `k-omega SST`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Re` = `3000000`
- `angle_of_attack` = `0.0`
- `chord_length` = `1.0`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Thomas 1979 / Lada & Gostling 2007`
- DOI: `10.1017/S0001924000001169`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `pressure_coefficient` | `[{'x': 0.0, 'Cp': 1.0}, {'x': 0.1, 'Cp': -0.3}, {'x': 0.3, 'Cp': -0.5}, {'x': 0.5, 'Cp': -0.2}, {'x': 0.7, 'Cp': 0.0}, {'x': 1.0, 'Cp': 0.2}]` | `relative=0.2` |

## Results vs Reference

- Match Rate: `0.00%`
- Verification Overall: `PASS_WITH_DEVIATIONS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `pressure_coefficient` | `[{'x_over_c': 0.0, 'Cp': 1.0}, {'x_over_c': 0.3, 'Cp': -0.5}, {'x_over_c': 1.0, 'Cp': 0.2}]` | `extracted` | `Match` | `False` |

## Attribution Analysis

Attribution report not yet generated.

## CorrectionSpec Record

> suggest-only, not auto-applied

No deviation; CorrectionSpec not triggered.

## Project Progress

- Cases Complete: `7/15`
- Progress Ratio: `46.67%`
- AutoVerify Reports Present: `9`

## Verdict

- Verification Verdict: `PASS_WITH_DEVIATIONS`
- Convergence Status: `CONVERGED`
- Physics Status: `PASS`
