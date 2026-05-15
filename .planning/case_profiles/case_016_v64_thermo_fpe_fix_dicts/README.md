# case_016 v64 thermo-FPE fix dict bundle (v3)

Substrate-side fix for shock-startup thermo-FPE crash documented in
`DEC-V64-A-sub-M-VAL-CASE-016-FULL` B53 v2 PARTIAL retro.

## Crash signature recap (v2 → v3 target)

v2 B53 attempt: `sigFpe` (FE_DIVBYZERO / FE_INVALID) in
`libfluidThermophysicalModels.so` frame #4 during PIMPLE iter 2 of timestep 28
at simulated `t = 1.24 ms`. Root cause: `sutherlandTransport::mu(T) =
A*sqrt(T) / (1 + Ts/T)` diverges when shock-startup transient lets cell-local T
overshoot to T < Ts (110.4 K) or T → 0.

## v3 fix (substrate-only · advisor stack untouched)

| Slot | v2 (B53) | v3 (this bundle) | Mechanism |
|---|---|---|---|
| `system/fvOptions` | NOT PRESENT | NEW · `limitTemperature` [110, 2000] K on `all` cells | `EEqn.H` calls `fvOptions.correct(he)` after solve; clamps T via energy back-conversion |
| `system/controlDict` deltaT | 0.0001 | **1e-6** | slow-ramp startup (10-100× smaller initial dt) |
| `system/controlDict` maxCo | 1.0 | **0.3** | tighter Co cap reduces per-timestep energy excursion |
| `system/controlDict` maxDeltaT | 1e-4 | **5e-5** | halved alongside maxCo |
| `system/fvSolution` | unchanged | unchanged | URF 0.7 already conservative; PIMPLE `pMinFactor 0.5`/`pMaxFactor 1.5` p-limiter retained |
| `constant/thermophysicalProperties` | sutherland + hConst | unchanged | sutherland kept — now safe because fvOptions clamps T |
| `constant/turbulenceProperties` | LES + kOmegaSSTIDDES | unchanged | LES IDDES kept for cavity-acoustics |

No mesh change. No advisor change. Same Docker image
`opencfd/openfoam-default:2312` (arm64-native).

## Files

- `system/fvOptions` — limitTemperature fvOption (NEW)
- `system/controlDict` — modified (deltaT, maxCo, maxDeltaT)
- `system/fvSchemes` — unchanged
- `system/fvSolution` — unchanged
- `system/{blockMeshDict, decomposeParDict, meshQualityDict, snappyHexMeshDict}` — unchanged
- `constant/thermophysicalProperties` — unchanged (sutherland)
- `constant/turbulenceProperties` — unchanged (LES + kOmegaSSTIDDES)
- `constant/g` — unchanged

## Reverse condition

If v3 still crashes thermo-FPE → root cause is NOT just shock-startup transient T
overshoot. Likely deeper: mesh-resolution-induced numerical artifact OR
turbulence model interaction (LES + sutherland under-relaxation). PARTIAL v3
verdict, advisor stack extension queued.

If v3 reaches `t >= 0.0352 s` (Welch mode-1 minimum window) cleanly →
acoustic FFT extraction + Heller-Bliss comparison feasible → FULL verdict
provided Δ < tolerance.
