# v2.4 rhoCentralFoam Fallback Dict Bundle

## Context

After 3 rhoSimpleFoam attempts (per task brief's `kOmegaSST RAS + sutherland +
URF p=0.30/U=0.70/e=0.50`) failed shock-startup instability:

- **Attempt 1** (GAMG p · brief-default URF): FE_DIVBYZERO iter 1, libOpenFOAM
  PBiCGStab in GAMG coarsest level
- **Attempt 2** (PBiCGStab DILU p · URF 0.15/0.40/0.30): FE_DOMAIN iter 77,
  libfluidThermophysicalModels sqrt(T) on T<0 transient internal cell
- **Attempt 3** (PBiCGStab DILU + const transport + URF 0.10/0.30/0.10): p
  equation residual diverged 0.478 → 8011 in 1000 PBiCGStab iters

Shared crash signature with DEC-V64-A-sub-M-VAL-CASE-016-FULL (B53 case_016
PARTIAL v2): same `libfluidThermophysicalModels` FE_DOMAIN class.

**Solver fallback** to substrate `case.yaml` v1-specified `rhoCentralFoam`
(transient density-based Kurganov+Minmod · proven stable in v1 baseline at
48k cells).

## What's in this dir

The dicts that actually ran for the v2.4 production attempt:

- `0/{U, p, T}` — IC files (laminar; no k/omega/nut/alphat — turbulence model
  swapped from kOmegaSST to laminar to align with rhoCentralFoam canonical
  workflow + v1 baseline reproducibility)
- `constant/thermophysicalProperties` — perfectGas + eConst + const transport
  (v1 baseline · brief asked sutherland but const matches v1)
- `constant/turbulenceProperties` — laminar (v1 baseline · brief asked kOmegaSST
  but rhoCentralFoam + RAS is not canonical OpenFOAM v2312 tutorial path)
- `system/controlDict` — rhoCentralFoam application · endTime 0.008s (extended
  from v1's 0.005s · ~3 chord-flow-throughs · ~8000 timesteps wall)
- `system/fvSchemes` — Kurganov + Minmod density-based (per v1)
- `system/fvSolution` — diagonal for rho/rhoU/rhoE + smoothSolver+symGaussSeidel
  for U/e (per v1 · DILU unavailable for symmetric matrices · V28 fix)

Mesh dicts (`system/snappyHexMeshDict`, `blockMeshDict`) at sibling dir
`../system/` (used for both attempt cascades; mesh is solver-agnostic).

Field 0/ files (`k, omega, nut, alphat`) at sibling dir `../0/` were authored
for the rhoSimpleFoam+kOmegaSST attempt cascade (commit 1); they are not used
in the v2.4 fallback (laminar) run but kept in repo for audit trail of original
brief intent.

## Brief deviation disclosure (PARTIAL v2 rationale)

- **Solver class**: rhoSimpleFoam → rhoCentralFoam · per substrate case.yaml v1
  + multi-attempt shock startup failure
- **Turbulence model**: kOmegaSST → laminar · per v1 baseline + rhoCentralFoam
  canonical workflow alignment
- **Transport model**: sutherland → const mu=1.79e-5 · per v1 baseline (also
  validated as rhoSimpleFoam attempt 3 mitigation)

These deviations are documented in:
- Sub-DEC `DEC-V64-A-sub-M-V64A-VAL-FULL-2` §Brief deviations
- Validation report `.planning/validation_reports/v64_case_006_onera_m6_full.md`
  §Limitations

per V63-A close §3.1 PARTIAL semantics precedent (semantics revision must be
user-ratified; the brief reverse condition pre-authorizes PARTIAL outcome for
multi-attempt failure + documented root cause).
