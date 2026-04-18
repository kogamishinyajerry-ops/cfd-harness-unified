## Case Summary

- Case ID: `backward_facing_step_steady`
- Name: `Backward-Facing Step`
- Description: `Driver & Seegmiller 1985`
- Solver: `simpleFoam`
- Turbulence Model: `k-epsilon`
- Mesh Strategy: `[DATA MISSING]`
- Key Parameters:
- `Re` = `7600`
- `expansion_ratio` = `1.125`
- Meta Source: `[DATA MISSING]`

## Gold Standard Reference

- Source: `Driver & Seegmiller 1985, AIAA J.`
- DOI: `10.2514/3.9086`

| Observable | Reference | Tolerance |
| --- | --- | --- |
| `reattachment_length` | `6.26` | `relative=0.1` |
| `cd_mean` | `2.08` | `relative=0.1` |
| `pressure_recovery` | `{'inlet': -0.9, 'outlet': 0.1, 'delta': 1.0}` | `relative=0.1` |
| `velocity_profile_reattachment` | `[{'x_H': 6.0, 'y_H': 0.5, 'u_Ubulk': 0.4}, {'x_H': 6.0, 'y_H': 1.0, 'u_Ubulk': 0.85}, {'x_H': 6.0, 'y_H': 2.0, 'u_Ubulk': 1.05}]` | `relative=0.1` |

## Results vs Reference

- Match Rate: `100.00%`
- Verification Overall: `PASS`

| Observable | Reference | Simulation | Direction | Within Tolerance |
| --- | --- | --- | --- | --- |
| `reattachment_length` | `6.26` | `6.3` | `Over` | `True` |
| `cd_mean` | `2.08` | `2.05` | `Under` | `True` |
| `pressure_recovery` | `{'inlet': -0.9, 'outlet': 0.1, 'delta': 1.0}` | `{'inlet': -0.88, 'outlet': 0.1, 'delta': 1.0}` | `Match` | `True` |
| `velocity_profile_reattachment` | `[{'x_H': 6.0, 'y_H': 0.5, 'u_Ubulk': 0.4}, {'x_H': 6.0, 'y_H': 1.0, 'u_Ubulk': 0.85}, {'x_H': 6.0, 'y_H': 2.0, 'u_Ubulk': 1.05}]` | `[0.41, 0.84, 1.04]` | `Match` | `True` |

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
