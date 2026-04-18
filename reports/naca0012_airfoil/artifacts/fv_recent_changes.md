# fvSchemes / fvSolution Snapshot And Recent Changes

Snapshot source:
- `/reports/naca0012_airfoil/artifacts/fvSchemes.copy`
- `/reports/naca0012_airfoil/artifacts/fvSolution.copy`
- `/tmp/cfd-harness-cases/ldc_2749_1776430899314/system/{fvSchemes,fvSolution}`

Current airfoil snapshot:
- `fvSchemes`
  - `ddtSchemes.default = steadyState`
  - `grad(U/k/omega) = cellLimited Gauss linear 1`
  - `div(phi,U/k/omega) = bounded Gauss upwind`
  - `laplacianSchemes.default = Gauss linear corrected`
  - `snGradSchemes.default = corrected`
  - `wallDist.method = meshWave`
- `fvSolution`
  - `p = GAMG, tolerance 1e-6, relTol 0.05`
  - `U/k/omega = PBiCGStab + DILU, tolerance 1e-10, relTol 0.1`
  - `SIMPLE.residualControl = {p 1e-6, U/k/omega 1e-5}`
  - `SIMPLE.nNonOrthogonalCorrectors = 0`
  - `relaxationFactors.fields.p = 0.3`
  - `relaxationFactors.equations.{U,k,omega} = 0.5`

Required command output:

```text
git log -n 5 --oneline -- src/foam_agent_adapter.py
6411d0b fix(turbulent_flat_plate): Cf extractor wall-cell skip + Spalding fallback + gold ref update
9d843e9 fix(turbulent_flat_plate): mesh 20→80 y-cells with 4:1 wall grading
e7fa556 fix(rayleigh_benard_convection): reduce h URF 0.1→0.05 for thermal stability
335ef23 fix(turbulent_flat_plate): Cf extractor nut+gradient fallback + URF convergence fix
c3a1a4c fix: turbulent_flat_plate URF + comparator schema expansion
```

Read-through of those 5 commits:
- `6411d0b`: flat-plate Cf extractor only; no airfoil config change
- `9d843e9`: flat-plate mesh only; no airfoil config change
- `e7fa556`: Rayleigh-Benard URF tweak only
- `335ef23`: flat-plate Cf extractor + URF work only
- `c3a1a4c`: flat-plate URF work plus comparator schema expansion

Airfoil-specific commits just before the recent-5 window:
- `b836f5e fix(airfoil): correct omega initialization formula (beta_star → Cmu^0.25)`
  - Narrows to the airfoil init block around `/src/foam_agent_adapter.py:5485-5498`
- `5581a4b feat(naca0012): fix airfoil mesh geometry and Cp extraction`
  - Airfoil mesh redesign, direct `blockMesh` path, current `fvSchemes`/`fvSolution` stabilization, and x-axis-aware Cp comparison plumbing

Implication:
- The current airfoil `fvSchemes`/`fvSolution` snapshot has not changed during the most recent 5 `src/foam_agent_adapter.py` commits.
- The last substantive airfoil config change is still `5581a4b`.
- The last substantive airfoil initialization change is still `b836f5e`.
