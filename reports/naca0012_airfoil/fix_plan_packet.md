## §A Fix Plan Draft (P0)

### A.1 blockMeshDict diff

Single candidate only: retune the six-block C-grid wall-normal discretization uniformly from `N_z = 80, simpleGrading_z = 40` to `N_z = 78, simpleGrading_z = 25`. This keeps shared-face subdivision conformal across the full six-block topology while increasing the first near-wall cell height by `1.4575x`.

```diff
--- a/src/foam_agent_adapter.py
+++ b/src/foam_agent_adapter.py
@@ -5177,23 +5177,23 @@
     hex ( 7 4 16 19 0 3 15 12)
-    (30 1 80)
-    simpleGrading (1 1 40)
+    (30 1 78)
+    simpleGrading (1 1 25)
 
     hex ( 5 7 19 17 1 0 12 13)
-    (30 1 80)
-    simpleGrading (1 1 40)
+    (30 1 78)
+    simpleGrading (1 1 25)
 
     hex ( 17 18 6 5 13 14 2 1)
-    (40 1 80)
-    simpleGrading (10 1 40)
+    (40 1 78)
+    simpleGrading (10 1 25)
 
     hex ( 20 16 4 8 21 15 3 9)
-    (30 1 80)
-    simpleGrading (1 1 40)
+    (30 1 78)
+    simpleGrading (1 1 25)
 
     hex ( 17 20 8 5 22 21 9 10)
-    (30 1 80)
-    simpleGrading (1 1 40)
+    (30 1 78)
+    simpleGrading (1 1 25)
 
     hex ( 5 6 18 17 10 11 23 22)
-    (40 1 80)
-    simpleGrading (10 1 40)
+    (40 1 78)
+    simpleGrading (10 1 25)
 ```

Representative first-cell calculation on the leading-edge wall-normal edge `4 -> 3` (same length on `16 -> 15`), where the low-`y+` cluster is concentrated:

- Current edge length: `L_n = 5.0c`
- Current `r_0 = 40^(1/79) = 1.0478020418`
- Current `Δz_1,0 = L_n * (r_0 - 1) / (r_0^80 - 1) = 0.0058420447c`
- Proposed `r_1 = 25^(1/77) = 1.0426896558`
- Proposed `Δz_1,1 = L_n * (r_1 - 1) / (r_1^78 - 1) = 0.0085150287c`
- Lift factor: `Δz_1,1 / Δz_1,0 = 1.4575x`
- A priori `y+` shift from the measured minimum: `22.3036 * 1.4575 = 32.51 > 30`
- A priori worst-wall-face guard using current max: `138.876 * 1.4575 = 202.42 < 300`

Why this is one global `dir3` candidate instead of a local LE-only patch: the measured defect is LE-localized, but the six-block C-grid shares the same wall-normal subdivision across internal block interfaces. Changing only one or two blocks would break shared-face conformity. This candidate therefore applies one consistent `dir3` retune across all six blocks while still targeting the LE buffer-band defect.

### A.2 File-level line accounting (<50 src/ lines claim)

- Function edited on apply: `_generate_airfoil_flow`
- Function scope guard: `src/foam_agent_adapter.py:L5059-L5288`
- Blocks touched in the string literal:
- `L5177-L5179` lower LE-adjacent block
- `L5181-L5183` lower TE-adjacent block
- `L5185-L5187` lower wake block
- `L5189-L5191` upper LE-adjacent block
- `L5193-L5195` upper TE-adjacent block
- `L5197-L5199` upper wake block
- Estimated added lines: `12`
- Estimated removed lines: `12`
- Total changed lines: `24` (`<50`)

### A.3 allowed_files / forbidden_files

```text
allowed_files:
  - src/foam_agent_adapter.py (only _generate_airfoil_flow body, L5059-5288)
  - reports/naca0012_airfoil/fix_plan_packet.md (this file)
forbidden_files:
  - knowledge/gold_standards/**
  - tests/**
  - .planning/STATE.md
  - src/foam_agent_adapter.py outside L5059-L5288
  - All other cases' generators (_generate_*)
```

### A.4 Acceptance Checks

CHK-1: `docker exec ... checkMesh` prints `Mesh OK`
CHK-2: max non-orthogonality delta `<= +2.0 deg` from current `68.9527`; if new max `>= 71.0` => `REJ`
CHK-3: aerofoil `y+ min >= 30.0` (no buffer-band faces)
CHK-4: aerofoil `y+ max <= 300.0` (no log-law overshoot)
CHK-5: `Cp rel_err at x/c=0.0 <= 25%` target / `<= 35%` pass; current baseline `52.9%`
CHK-6: `Cp rel_err at x/c=0.3 <= 20%` target / `<= 30%` pass; current baseline `32.4%`
CHK-7: `Cp rel_err at x/c=1.0 <= 25%` target / `<= 35%` pass; current baseline `45.5%`
CHK-8: `knowledge/gold_standards/naca0012_airfoil.yaml` byte-identical pre/post
CHK-9: `src` diff `<= 50` lines by `wc -l` on unified diff body
CHK-10: `pytest tests/` => `>= 211` pass, no new failures
CHK-11: all other 9 whitelist cases smoke-rerun `checkMesh` verdict unchanged: `ldc`, `bfs`, `cylinder`, `turbulent_flat_plate`, `plane_channel`, `impinging_jet`, `rayleigh_benard`, `DHC`, `pipe`

### A.5 Reject Conditions

REJ-A1: any line under `knowledge/gold_standards/**` changes
REJ-A2: any tolerance widening under `knowledge/`
REJ-A3: any `src/` edit outside `src/foam_agent_adapter.py:L5059-L5288`
REJ-A4: any other case generator is touched
REJ-A5: CHK-2 fails (`non-orthogonality >= 71.0`)
REJ-A6: CHK-3 or CHK-4 fails (`y+` outside the intended wall-function band)
REJ-A7: CHK-11 fails (any whitelist case regresses on `checkMesh`)
REJ-A8: total `src/` diff exceeds `50` lines

### A.6 Rollback Strategy

- Pre-fix commit SHA: `fb0df98` (current `HEAD` after diagnostic commit)
- Rollback command: `git revert <fix-commit-sha>`
- Mesh artifact preservation:
- `reports/naca0012_airfoil/artifacts/checkmesh.log` (pre-fix, committed)
- `reports/naca0012_airfoil/artifacts/yplus_profile.csv` (pre-fix, committed)
- `reports/naca0012_airfoil/artifacts/checkmesh_postfix.log` (to be generated)
- `reports/naca0012_airfoil/artifacts/yplus_postfix.csv` (to be generated)
- If CHK-3, CHK-4, CHK-5, CHK-6, or CHK-7 fails on apply, revert immediately; no partial landing.

## §B 5 P0 Evidence (pointer + key numeric)

### B.1 checkMesh summary

Pointer: `reports/naca0012_airfoil/artifacts/checkmesh.log:L28-L81`

Key numeric for Gate readout:

- `16000` cells and `16000` hexahedra (`L33`, `L41`)
- `aerofoil 120 faces` (`L59`)
- max aspect ratio `108.35` (`L72`)
- max non-orthogonality `68.9527`, average `25.887` (`L75`)
- max skewness `1.12683` (`L78`)
- verdict `Mesh OK` (`L81`)

### B.2 y+ distribution

Pointer: `reports/naca0012_airfoil/artifacts/yplus_profile.csv`

Key numeric from the preserved 120-face profile:

- `min = 22.3036`
- `max = 138.876`
- `median = 112.933`
- `mean = 104.332`
- band split `10/120` buffer, `110/120` wall-function, `0/120` low-Re, `0/120` overshoot
- low-band cluster visible at `face_index 24-29` and `114-119` (`yplus_profile.csv:L26-L31` and `L116-L121`), matching the LE-localized hypothesis

### B.3 fvSchemes / fvSolution

Pointers:

- `reports/naca0012_airfoil/artifacts/fvSchemes.copy`
- `reports/naca0012_airfoil/artifacts/fvSolution.copy`

Top-5 Gate-readable entries:

- `fvSchemes.copy:L17` -> `ddtSchemes { default steadyState; }`
- `fvSchemes.copy:L18-L24` -> `grad(U)`, `grad(k)`, `grad(omega)` all use `cellLimited Gauss linear 1`
- `fvSchemes.copy:L25-L31` -> `div(phi,U)`, `div(phi,k)`, `div(phi,omega)` all use `bounded Gauss upwind`
- `fvSchemes.copy:L32-L35` -> `laplacian corrected`, `snGrad corrected`, `wallDist { method meshWave; }`
- `fvSolution.copy:L19-L24`, `L36`, `L41-L42` -> `p` solver is `GAMG` with `tolerance 1e-6` and `relTol 0.05`; `nNonOrthogonalCorrectors 0`; relaxation factors are `p 0.3`, `U/k/omega 0.5`

### B.4 omega initialization audit

Pointer: `reports/naca0012_airfoil/artifacts/omega_init_audit.md:L8-L44`

Key numeric:

- executable form: `omega_init = (k_init ** 0.5) / ((Cmu ** 0.25) * L_turb)` (`L10-L12`)
- `omega_correct = 0.1118033989` (`L26`)
- wrong `beta_star` form would give `0.6804138174` (`L28`)
- inflation factor: `6.0858x` (`L29`)
- implication: omega initialization is already corrected and ruled out as the P0 defect

### B.5 Cp post-processing

Pointer: `reports/naca0012_airfoil/artifacts/cp_postproc_audit.md:L14-L70`

Key numeric:

- `U_ref = 1.0`, `rho = 1.0`, so `q_ref = 0.5` (`L17-L19`, `L44`)
- `p_ref` comes from far-field cell average, `farfield_count = 3844`, `p_ref = 0.0058681300` (`L22-L33`, `L42-L43`)
- reference-point replay with current extractor:
- `x/c = 0.0 -> Cp = 0.471535` (`L48`)
- `x/c = 0.3 -> Cp = -0.338249` (`L49`)
- `x/c = 1.0 -> Cp = 0.109458` (`L50`)

## §C Expected Gain (a priori quantification)

### C.1 Current vs target y+ range

- current: `min 22.30 / median 112.93 / max 138.88 / buffer faces 10/120`
- target (path W): `min >= 30 / max <= 300 / buffer faces 0/120`

### C.2 Expected Cp deviation reduction

- Mechanism: removing the buffer-band wall faces lets `kOmegaSST` automatic wall treatment operate consistently in the intended wall-function band. Per the authoritative context for this packet, Menter 1994 § III.B and NASA TMR `kOmegaSST` validation support `NACA0012` wall-function accuracy in roughly the `5-15%` relative-error range when `y+` stays wholly inside `[30,300]`.
- Point-wise prediction:
- `x/c = 0.0: 52.9% -> 15-25%`
- `x/c = 0.3: 32.4% -> 8-15%`
- `x/c = 1.0: 45.5% -> 12-25%`
- Sensitivity note: stagnation remains the least cleanly bounded point because the current `Cp` extractor still uses a far-field cell-average `p_ref` and near-surface cell centers.

### C.3 Fallback paths if post-fix Cp > 15% at all three x/c points

- Path W1: refine far-field boundary treatment (`freestream` vs `inletOutlet`)
- Path W2: switch to `kOmegaSSTLM` (transition-aware) as a separate Tier 1 Gate
- Path W3: tighten the `Cp` extractor (`surface_band`, wall-face extrapolation) as a separate Tier 1 Gate
- Tolerance widening is not a fallback under any scenario.

## §D Gate Q1-Q8 Answers (explicit)

Q1: LE-only vs LE+pressure+suction surfaces?
Answer: LE+pressure+suction surfaces in the concrete diff, even though the defect evidence is LE-localized. The low-`y+` faces are confined to the LE-adjacent wall segments (`face_index 24-29` and `114-119`), but `blockMesh` shared-face conformity forces the `dir3` retune through the full six-block ring. The candidate diff therefore touches both LE-adjacent blocks (`L5177-L5179`, `L5189-L5191`) and TE-adjacent wall blocks (`L5181-L5183`, `L5193-L5195`), plus the two wake blocks (`L5185-L5187`, `L5197-L5199`) to keep the normal subdivision consistent end-to-end.

Q2: y-direction (span, 1 cell empty) unchanged?
Answer: yes. The middle cell-count slot remains `1` in every edited block line, and the `back` / `front` boundaries remain `empty` exactly as written in `src/foam_agent_adapter.py:L5178-L5198` and `L5253-L5278`.

Q3: near-wall growth rate <= 1.2?
Answer: yes. Proposed `r = 25^(1/(78-1)) = 25^(1/77) = 1.0426896558 <= 1.2`. Current `r = 40^(1/79) = 1.0478020418`, so the candidate actually lowers the per-cell expansion rate while increasing `Δz_1` via the combined `N_z` and total-grading change.

Q4: nNonOrthogonalCorrectors change?
Answer: no. `fvSolution` is untouched, and `reports/naca0012_airfoil/artifacts/fvSolution.copy:L36` remains `nNonOrthogonalCorrectors 0;`.

Q5: post-fix verification scope?
Answer: rerun `NACA0012` verification plus `checkMesh` smoke on all 10 whitelist cases per CHK-11, and run the full `pytest tests/` suite per CHK-10.

Q6: gold_standards tolerance unchanged?
Answer: yes. `knowledge/gold_standards/**` is explicitly forbidden in A.3, guarded again by REJ-A1 and REJ-A2, and CHK-8 requires `knowledge/gold_standards/naca0012_airfoil.yaml` to remain byte-identical.

Q7: commit trailer?
Answer: `Execution-by: codex-gpt54` + `Gate-approve: thread://41cc6894-2bed-814f-974b-0003bba02ff6/345c6894-2bed-804b-8721-00a9913925d1`

Q8: buffer-layer hypothesis evidence strength?
Answer: direct measurement. The packet relies on 120 real aerofoil wall-face samples, with 10 measured in the buffer band and concentrated at face indices matching the LE location. Combined with the provided Menter 1994 and NASA TMR wall-function framing, the evidence strength is STRONG, not speculative.

## §E Applicability Note

No `src/` apply in this round. This packet is a draft for independent Gate review. Apply is deferred until Gate returns `APPROVE` or `APPROVE WITH CONDITIONS`.
