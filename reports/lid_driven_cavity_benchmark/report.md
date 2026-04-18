## Case Summary

- Case ID: `lid_driven_cavity_benchmark`
- Name: `Lid-Driven Cavity`
- Description: `Ghia et al. 1982`
- Solver: `icoFoam`
- Turbulence Model: `laminar`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Re` = `100`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Ghia et al. 1982, J. Comput. Phys.`
- DOI: `10.1016/0021-9991(82)90058-4`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `u_centerline` | `[{'y': 0.0625, 'u': -0.03717}, {'y': 0.125, 'u': -0.04192}, {'y': 0.1875, 'u': -0.04124}, {'y': 0.25, 'u': -0.03667}, {'y': 0.3125, 'u': -0.02799}, {'y': 0.375, 'u': -0.01641}, {'y': 0.4375, 'u': -0.00289}, {'y': 0.5, 'u': 0.02526}, {'y': 0.5625, 'u': 0.07156}, {'y': 0.625, 'u': 0.1191}, {'y': 0.6875, 'u': 0.17285}, {'y': 0.75, 'u': 0.33304}, {'y': 0.8125, 'u': 0.46687}, {'y': 0.875, 'u': 0.65487}, {'y': 0.9375, 'u': 0.84927}, {'y': 1.0, 'u': 1.0}]` | `relative=0.05` |
| `v_centerline` | `[{'y': 0.125, 'v': -0.04939}, {'y': 0.1875, 'v': -0.06203}, {'y': 0.25, 'v': -0.06904}, {'y': 0.3125, 'v': -0.0708}, {'y': 0.375, 'v': -0.06629}, {'y': 0.4375, 'v': -0.05259}, {'y': 0.5, 'v': 0.05454}, {'y': 0.5625, 'v': 0.06406}, {'y': 0.625, 'v': 0.0692}, {'y': 0.6875, 'v': 0.06878}, {'y': 0.75, 'v': 0.06021}, {'y': 0.8125, 'v': 0.04404}, {'y': 0.875, 'v': 0.02429}]` | `relative=0.05` |
| `primary_vortex_location` | `{'vortex_center_x': 0.5, 'vortex_center_y': 0.765, 'u_min': {'value': -0.03717, 'location_y': 0.0625}}` | `relative=0.05` |

## Results vs Reference

- Match Rate: `100.00%`
- Verification Overall: `PASS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `u_centerline` | `[{'y': 0.0625, 'u': -0.03717}, {'y': 0.125, 'u': -0.04192}, {'y': 0.1875, 'u': -0.04124}, {'y': 0.25, 'u': -0.03667}, {'y': 0.3125, 'u': -0.02799}, {'y': 0.375, 'u': -0.01641}, {'y': 0.4375, 'u': -0.00289}, {'y': 0.5, 'u': 0.02526}, {'y': 0.5625, 'u': 0.07156}, {'y': 0.625, 'u': 0.1191}, {'y': 0.6875, 'u': 0.17285}, {'y': 0.75, 'u': 0.33304}, {'y': 0.8125, 'u': 0.46687}, {'y': 0.875, 'u': 0.65487}, {'y': 0.9375, 'u': 0.84927}, {'y': 1.0, 'u': 1.0}]` | `[-0.037, -0.0415, -0.041, -0.0362, -0.0275, -0.016, -0.00289, 0.0255, 0.071, 0.1185, 0.172, 0.332, 0.466, 0.654, 0.848, 0.999]` | `Match` | `True` |
| `v_centerline` | `[{'y': 0.125, 'v': -0.04939}, {'y': 0.1875, 'v': -0.06203}, {'y': 0.25, 'v': -0.06904}, {'y': 0.3125, 'v': -0.0708}, {'y': 0.375, 'v': -0.06629}, {'y': 0.4375, 'v': -0.05259}, {'y': 0.5, 'v': 0.05454}, {'y': 0.5625, 'v': 0.06406}, {'y': 0.625, 'v': 0.0692}, {'y': 0.6875, 'v': 0.06878}, {'y': 0.75, 'v': 0.06021}, {'y': 0.8125, 'v': 0.04404}, {'y': 0.875, 'v': 0.02429}]` | `[-0.0488, -0.0615, -0.0686, -0.0701, -0.0658, -0.052, 0.054, 0.0635, 0.0688, 0.068, 0.0595, 0.0438, 0.024]` | `Match` | `True` |
| `primary_vortex_location` | `{'vortex_center_x': 0.5, 'vortex_center_y': 0.765, 'u_min': {'value': -0.03717, 'location_y': 0.0625}}` | `{'vortex_center_x': 0.5005, 'vortex_center_y': 0.764, 'u_min': {'value': -0.03717, 'location_y': 0.0625}}` | `Match` | `True` |

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
