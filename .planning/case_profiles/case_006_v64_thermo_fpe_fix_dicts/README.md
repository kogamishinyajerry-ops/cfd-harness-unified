# case_006 v64 thermo-FPE fix dict bundle (v3)

Substrate-side fix for shock-startup thermo-FPE + p-equation divergence
documented in `DEC-V64-A-sub-M-V64A-VAL-FULL-2` B59 v2 PARTIAL retro.

## Crash signature recap (v2 attempts → v3 target)

B59 attempted 3 rhoSimpleFoam configurations, all crashed:

- Attempt 1 (GAMG p · URF 0.30/0.70/0.50 · sutherland): FE_DIVBYZERO at iter 1
- Attempt 2 (PBiCGStab DILU p · URF 0.15/0.40/0.30 · sutherland): FE_DOMAIN at iter 77, `sqrt(T)` on T<0
- Attempt 3 (PBiCGStab DILU + const transport + URF 0.10/0.30/0.10): p-eq residual diverged 0.478 → 8011 within 1000 PBiCGStab iters

Then fell back to v2.4 rhoCentralFoam + laminar (proven stable in v1 baseline).

Root cause hypothesis (per B59 F-NEW-5):
1. shock-startup transient cell-local T overshoot → sutherland mu(T) FPE
2. SIMPLE-style algorithm cannot handle freestream → transonic shock initialization without preconditioning

## v3 fix (substrate-only · advisor stack untouched)

| Slot | B59 attempt 3 | v3 (this bundle) | Mechanism |
|---|---|---|---|
| `system/fvOptions` | NOT PRESENT | NEW · `limitTemperature` [110, 2000] K on `all` cells | clamps T via `fvOptions.correct(he)` in rhoSimpleFoam EEqn |
| `constant/thermophysicalProperties` `transport` | const (downgraded) | **sutherland** (restored) | safe now because T is bounded by limitTemperature |
| `system/fvSolution` potentialFlow block | NOT PRESENT | NEW | enables potentialFoam pre-step |
| `scripts/v64_v3_run_solver.sh` | did not exist | NEW · 2-stage runner | (1) potentialFoam → smooth velocity IC; (2) rhoSimpleFoam |
| `system/fvSolution` URFs | p=0.10, U=0.30, e=0.10, rho=0.05 | unchanged | already maximally relaxed |
| `system/fvSolution` p solver | PBiCGStab DILU | unchanged | attempt-1 GAMG instability avoided |
| `system/fvSolution` SIMPLE rhoMin/rhoMax/pMin/pMax | retained | unchanged | rhoMin=0.1, rhoMax=3.0, pMin=30k, pMax=300k |
| `constant/turbulenceProperties` | RAS kOmegaSST | unchanged | per brief |
| `system/fvSchemes` | bounded upwind | unchanged | shock-capturing stable |

No mesh change (reuses B59 205k cell mesh). No advisor change. Same Docker
image.

## Files

- `system/fvOptions` — limitTemperature fvOption (NEW)
- `system/fvSolution` — modified (added potentialFlow + Phi solver block)
- `system/{controlDict, fvSchemes, decomposeParDict, snappyHexMeshDict}` — restored from B59 archive
- `constant/thermophysicalProperties` — modified (transport: const → sutherland)
- `constant/turbulenceProperties` — restored from B59 archive (RAS kOmegaSST)
- `0/{U, p, T, k, omega, nut, alphat}` — restored from B59 archive (kOmegaSST IC)
- `scripts/v64_v3_run_solver.sh` — NEW 2-stage runner

## Reverse condition

- If potentialFoam pre-step fails: substrate-side fix architecture failed; document
  + retro queue.
- If rhoSimpleFoam still crashes thermo-FPE after fvOptions: limitTemperature
  fvOption is NOT actually clamping T (config bug OR OpenFOAM 2312 EEqn does
  not call `fvOptions.correct(he)` for rhoSimpleFoam transonic path).
- If rhoSimpleFoam stabilizes but doesn't converge to residualControl ≤4/6 < 1e-4:
  PARTIAL v3 — fix unblocks FPE but underlying p-eq matrix conditioning is
  deeper; needs A1-extraction (ONERA D-section) + ≥1M mesh.
- If converges + Cp Δ < 15% at majority stations + shock position Δ < 5% chord:
  FULL verdict.
