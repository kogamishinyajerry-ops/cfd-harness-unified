# NACA0012 Wave 3 Diagnostic v1

## §1 Scope & Constraints

This round regenerates the diagnostic from the authoritative preserved NACA0012 case at `/tmp/cfd-harness-cases/ldc_1720_1776471699394` and the real artifacts already written under `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/`. The legacy `ldc_` prefix is an executor naming artifact; `blockMeshDict` in the preserved case still points at `NACA0012.obj`, so the geometry context is the intended airfoil case.

This file remains read-only with respect to `/src`, `/tests`, and `/knowledge/gold_standards`. Closeout verification used `git diff HEAD -- src tests knowledge`, which returned empty output. No tolerance widening is proposed anywhere in this diagnostic.

## §2 checkMesh Summary

The authoritative `checkMesh -latestTime` output is captured at `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/checkmesh.log`. It corresponds to the preserved case at `/tmp/cfd-harness-cases/ldc_1720_1776471699394`, which is the real NACA0012 case despite the executor's legacy `ldc_` prefix.

Exact mesh summary from the log:
- `32480` points
- `64240` faces
- `16000` cells, all hexahedra
- boundary patches:
- `aerofoil`: `120` faces
- `inlet`: `200` faces
- `outlet`: `160` faces
- `back`: `16000` faces
- `front`: `16000` faces
- domain bounding box `(-5, -0.001, -2)` to `(5, 0.001, 2)`, confirming a 2D thin-span domain
- max non-orthogonality `68.9527` (average `25.887`)
- max skewness `1.12683`
- max aspect ratio `108.35`
- overall verdict: `Mesh OK`

Interpretation: the mesh is not topologically broken. Skewness is low and non-orthogonality stays just under the usual `70` degree action threshold, so the leading concern is not connectivity failure but near-wall placement and stretching around the aerofoil. The thin-span domain and the `120`-face aerofoil boundary confirm that the preserved artifacts are from the intended 2D NACA0012 setup.

## §3 y+ First-Layer Distribution

The authoritative aerofoil `y+` profile is captured at `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/yplus_profile.csv` with `120` face-indexed samples.

Exact statistics from the CSV:
- `min = 22.3036`
- `max = 138.876`
- `median = 112.933`
- `mean = 104.332`

Band split across the `120` aerofoil faces:
- buffer layer (`y+ < 30`): `10/120` (`8.3%`)
- wall-function band (`30 <= y+ <= 300`): `110/120` (`91.7%`)
- low-Re band (`y+ < 1`): `0/120`
- overshoot band (`y+ > 300`): `0/120`

Interpretation: the current setup is overwhelmingly in the wall-function regime, which matches `kOmegaSST` automatic wall treatment, but `10/120` faces fall into the buffer layer where neither a clean low-Re treatment nor a clean log-law wall function applies. That band split makes first-layer placement the primary suspect for the Cp error at stagnation / leading edge, where the benchmark miss is largest at `x/c = 0.0` (`52.9%` relative error). None of the faces are low-Re resolved, so the case is currently straddling regimes rather than committing to one.

## §4 fvSchemes / fvSolution Snapshot + Recent 5 Commits

The preserved case snapshots copied to `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fvSchemes.copy` and `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fvSolution.copy` confirm the current stabilized airfoil settings:
- `fvSchemes`: bounded upwind convection for `U/k/omega`, corrected Laplacian and snGrad, `wallDist { method meshWave; }`
- `fvSolution`: `p` GAMG with `tolerance 1e-6`, `relTol 0.05`, `p` field relaxation `0.3`, equation relaxation `0.5` for `U/k/omega`, `nNonOrthogonalCorrectors 0`

The required `git log -n 5 --oneline -- src/foam_agent_adapter.py` output is summarized in `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fv_recent_changes.md`. Those five commits all target turbulent flat plate or Rayleigh-Benard paths; none alters the airfoil `fvSchemes` / `fvSolution` block. The last substantive airfoil config changes remain:
- `5581a4b`: six-block x-z plane mesh redesign + current stabilized `fvSchemes` / `fvSolution`
- `b836f5e`: omega initialization formula correction

That matters because the current Cp deviation is not being introduced by a new regression in the recent-commit window. Evidence paths:
- `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fvSchemes.copy`
- `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fvSolution.copy`
- `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fv_recent_changes.md`

## §5 omega Initialization Formula String-Level Audit

The kept source audit in `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/omega_init_audit.md` still shows that the executable omega initialization expression in `/src/foam_agent_adapter.py:5498` is:

```python
omega_init = (k_init ** 0.5) / ((Cmu ** 0.25) * L_turb)
```

With the current upstream definitions, that evaluates to `0.1118033989`. The historical wrong form using `beta_star = 0.09` would give `0.6804138174`, a `6.09x` inflation. That keeps omega initialization off the top of the suspect list: the formula bug was real, but the current code path already uses the corrected expression. The remaining issue in this area is comment drift, not an active physics-path defect.

## §6 Cp Post-Processing Formula Audit

The kept audit in `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/cp_postproc_audit.md` still resolves the current extractor behavior:
- `_extract_airfoil_cp` hard-codes `U_ref = 1.0`, `rho = 1.0`, so `q_ref = 0.5`
- `p_ref` is taken from a far-field cell-average inside the solved field, not from the gold-standard table
- the replayed extractor reproduces the report samples at `x/c = 0.0`, `0.3`, and `1.0`
- `/src/result_comparator.py:223-241` compares on `x/c`, so the benchmark match is coordinate-aware rather than index-only

That keeps Cp extraction smearing as a live secondary candidate: near-surface cell-center pressure plus a wide `surface_band` can still damp stagnation and suction extrema. The new real `y+` evidence is stronger, though, so extractor changes move behind first-layer targeting in the ranking.

## §7 Hypothesis Ranking + Fix Plan Draft

### Ranked hypotheses

1. **Top-1: buffer-layer / first-layer y+ band-split mismatch at the leading edge**
   - Evidence: `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/yplus_profile.csv` shows `10/120` aerofoil faces in `y+ < 30`, `110/120` in `30 <= y+ <= 300`, `0/120` in `y+ < 1`, and `0/120` above `300`.
   - Concentration: the minimum-`y+` faces are clustered near `x/c = 0` at face indices `25-29` and `115-119`, with the minimum value `22.3036`.
   - Mechanism: `kOmegaSST` automatic wall treatment is ill-defined in the buffer layer, so a mesh that is mostly wall-function-like but dips locally into `22.30 <= y+ < 30` is a direct candidate for leading-edge Cp distortion.
   - Why this ranks first: the largest Cp miss remains at stagnation / leading edge (`x/c = 0.0`, `52.9%` relative error), which matches the location where first-layer placement is most sensitive.

2. **Top-2: Cp extractor surface-band smearing**
   - Evidence: the prior audit in `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/cp_postproc_audit.md` remains valid: the extractor uses near-surface cell-center pressure, a far-field `p_ref`, and a permissive `surface_band`, all of which can damp extrema.
   - Why it ranks second: this remains plausible, but it is less direct than the newly measured buffer-layer split on the actual aerofoil wall.

3. **Top-3: non-orthogonality margin near the action threshold with `nNonOrthogonalCorrectors 0`**
   - Evidence: `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/checkmesh.log` reports max non-orthogonality `68.9527`, close to the usual `70` degree action threshold, while `/Users/Zhuanz/Desktop/cfd-harness-unified/reports/naca0012_airfoil/artifacts/fvSolution.copy` still shows `nNonOrthogonalCorrectors 0`.
   - Why it ranks third: the mesh still reports `Mesh OK`, so this looks like a numerical-margin amplifier rather than the primary source of the Cp error.

### Fix Plan Draft

- Primary change target: refine leading-edge wall-normal grading so the first-layer `y+` distribution stops straddling the buffer layer.
- Acceptance target for the mesh retune: push the current buffer-layer faces cleanly into one regime, preferably a consistent wall-function target with `y+ > 30` everywhere on the aerofoil, or otherwise a true low-Re target with `y+ < 1` where intended.
- Scope constraint: keep the implementation under `<50` changed lines in `src/`.
- Validation after the mesh-only change:
- regenerate the NACA0012 case artifacts
- confirm the aerofoil `y+` split no longer shows `10/120` faces in `y+ < 30`
- confirm no faces move above `y+ > 300`
- recheck Cp at `x/c = 0.0`, `0.3`, and `1.0`
- Explicit rejects:
- no tolerance widening
- no Cp extractor change as the first move
