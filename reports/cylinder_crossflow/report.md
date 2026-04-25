## Case Summary

- Case ID: `cylinder_crossflow`
- Name: `Circular Cylinder Wake`
- Description: `Williamson 1996`
- Solver: `pimpleFoam`
- Turbulence Model: `laminar`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Re` = `100`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Williamson 1996, Annu. Rev. Fluid Mech.`
- DOI: `10.1146/annurev.fl.28.010196.002421`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `strouhal_number` | `0.164` | `relative=0.05` |
| `cd_mean` | `1.33` | `relative=0.05` |
| `cl_rms` | `0.048` | `relative=0.05` |
| `u_mean_centerline` | `[{'x_D': 1.0, 'u_Uinf': 0.83}, {'x_D': 2.0, 'u_Uinf': 0.64}, {'x_D': 3.0, 'u_Uinf': 0.55}, {'x_D': 5.0, 'u_Uinf': 0.35}]` | `relative=0.05` |

## Results vs Reference

- Match Rate: `100.00%`
- Verification Overall: `PASS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `strouhal_number` | `0.164` | `0.164` | `Match` | `True` |
| `cd_mean` | `1.33` | `1.31` | `Under` | `True` |
| `cl_rms` | `0.048` | `0.049` | `Over` | `True` |
| `u_mean_centerline` | `[{'x_D': 1.0, 'u_Uinf': 0.83}, {'x_D': 2.0, 'u_Uinf': 0.64}, {'x_D': 3.0, 'u_Uinf': 0.55}, {'x_D': 5.0, 'u_Uinf': 0.35}]` | `[0.82, 0.65, 0.56, 0.34]` | `Match` | `True` |

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

- Verification Verdict: `PASS`
- Convergence Status: `CONVERGED`
- Physics Status: `PASS`
