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
CHK-2 (revised per Gate COND-4): hard fail if new max non-orthogonality `> 71.0 deg`; soft warn if `> 70.0 deg` (annotate in commit message but do not reject); baseline current `68.9527`
CHK-3: aerofoil `y+ min >= 30.0` (no buffer-band faces)
CHK-4: aerofoil `y+ max <= 300.0` (no log-law overshoot)
CHK-5: `Cp rel_err at x/c=0.0 <= 25%` target / `<= 35%` pass; current baseline `52.9%`
CHK-6: `Cp rel_err at x/c=0.3 <= 20%` target / `<= 30%` pass; current baseline `32.4%`
CHK-7: `Cp rel_err at x/c=1.0 <= 25%` target / `<= 35%` pass; current baseline `45.5%`
CHK-8: `knowledge/gold_standards/naca0012_airfoil.yaml` byte-identical pre/post
CHK-9: `src` diff `<= 50` lines by `wc -l` on unified diff body
CHK-10: `pytest tests/` => `>= 211` pass, no new failures
CHK-11: all other 9 whitelist cases smoke-rerun `checkMesh` verdict unchanged: `ldc`, `bfs`, `cylinder`, `turbulent_flat_plate`, `plane_channel`, `impinging_jet`, `rayleigh_benard`, `DHC`, `pipe`
CHK-12 (per Gate COND-2): buffer-band face count on aerofoil patch == `0` (strict equality; count faces with `y+ < 30` from post-fix `yplus_profile.csv`)
CHK-13 (per Gate COND-3): Cp three-point average relative error `(|err_0| + |err_0.3| + |err_1.0|) / 3` ≤ `20%` target / ≤ `28%` pass; current baseline average = `(52.9 + 32.4 + 45.5) / 3 = 43.6%`

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

## §F Gate COND-1..4 Closure Record (2026-04-18)

### §F.1 COND-1 — wall BC type verification (PASS)

Preserved case: `/tmp/cfd-harness-cases/ldc_1720_1776471699394/0/{k,omega,nut}`.
Aerofoil wall patch `type` fields (raw, verbatim):

- `0/k`:     `aerofoil { type kqRWallFunction;  value uniform 3.7500000000000003e-05; }`
- `0/omega`: `aerofoil { type omegaWallFunction; value uniform 0.11180339887498948; }`
- `0/nut`:   `aerofoil { type nutkWallFunction;  value uniform 0; }`

Interpretation: all three are standard high-Re wall-function variants. No
low-Re form detected (no `kLowReWallFunction`, no `nutLowReWallFunction`, no
`omegaWallFunction` with low-Re switch, no `fixedValue=0` on `k`). The
Fix Plan direction (path W: push `y+_min ≥ 30` while staying `≤ 300`) is
consistent with the as-built wall-treatment contract. COND-1 → PASS.

### §F.2 COND-2/3/4 — CHK revisions (applied in §A.4)

- COND-2: CHK-12 added (buffer-band face count == 0, strict)
- COND-3: CHK-13 added (Cp three-point avg rel_err ≤ 20% target / ≤ 28% pass;
  baseline avg = 43.6%)
- COND-4: CHK-2 split into hard-fail (`>71°`) / soft-warn (`>70°`)

All four conditions now closed; awaiting final Gate APPROVE before dispatching
the blockMeshDict edit to Codex.

## §G Post-Fix Results (2026-04-18, 2-phase dispatch)

### §G.1 Execution Record

- Phase A: Codex applied §A.1 unified diff to `src/foam_agent_adapter.py` L5177-L5199
  (`12+/12-`, 24 lines). Phase-A CHK-A1..A6 all PASS; `src/` left dirty.
- Phase B: Orchestrator (opus47-main) ran `/tmp/run_naca0012_keepcase.py` on host
  Python 3 with shutil.rmtree monkey-patch. NACA0012 Docker E2E success
  (`success=True, is_mock=False, elapsed=19.7s`). Preserved case:
  `/tmp/cfd-harness-cases/ldc_51585_1776491271745`.
  Docker `checkMesh` + `simpleFoam -postProcess -func yPlus` + TaskRunner-level
  ComparisonResult collected from host. Artifacts:
    - `reports/naca0012_airfoil/artifacts/checkmesh_postfix.log`
    - `reports/naca0012_airfoil/artifacts/yplus_postfix.csv`
- Phase C: did NOT occur. Because post-fix CHK-3/5/6/7/12/13 FAIL (see §G.2),
  dispatch contract forbids commit. Orchestrator reverted src/ via
  `git checkout -- src/foam_agent_adapter.py`. No src/ change persisted.

### §G.2 CHK Verdict Table

| Check | Threshold | Pre-fix | Post-fix | Verdict |
|---|---|---:|---:|:---:|
| CHK-1  | checkMesh "Mesh OK" | OK | OK | **PASS** |
| CHK-2  | non-ortho ≤ 71° hard / ≤ 70° soft | 68.95° | 68.91° | **PASS** (no warn) |
| CHK-3  | y+_min ≥ 30.0 | 22.30 | 23.61 | **FAIL** (−6.39 from target) |
| CHK-4  | y+_max ≤ 300.0 | 138.88 | 200.69 | PASS |
| CHK-5  | Cp rel_err @ x/c=0.0 ≤ 35% | 52.9% | 42.14% | **FAIL** (−7.14 from pass) |
| CHK-6  | Cp rel_err @ x/c=0.3 ≤ 30% | 32.4% | 32.17% | **FAIL** (marginal, −2.17 from pass) |
| CHK-7  | Cp rel_err @ x/c=1.0 ≤ 35% | 45.5% | 44.79% | **FAIL** (−9.79 from pass) |
| CHK-8  | gold-std yaml byte-identical | — | sha256 identical | PASS |
| CHK-9  | src diff ≤ 50 lines | — | 24 lines | PASS |
| CHK-10 | pytest ≥ 211 pass | 211 | 211 | PASS (10 pre-existing notion-env fails) |
| CHK-11 | 9-case checkMesh smoke | — | not run (FAIL already triggered) | N/A |
| CHK-12 | buffer-band face count == 0 | 10/120 | **12/120** | **FAIL** (worsened by +2) |
| CHK-13 | Cp 3-pt avg rel_err ≤ 28% | 43.6% | 39.7% | **FAIL** (−11.7 from pass) |

**6 of 13 CHK fail → REJECT per contract. No commit created.**

### §G.3 Post-Fix Mesh / y+ / Cp Evidence

checkmesh_postfix.log (quote):
- cells: 15600 (pre-fix 16000, −400 from N_z 80→78)
- hexahedra: 15600
- aerofoil: 120 faces (unchanged)
- max aspect ratio: **74.3374** (pre-fix 108.35 — improved)
- max skewness: **1.02707** (pre-fix 1.12683 — improved)
- max non-orthogonality: **68.9106** (pre-fix 68.9527 — marginally improved)
- verdict: "Mesh OK"

yplus_postfix.csv (n=120):
- min = **23.6085** (pre-fix 22.3036; lift factor 1.0585×)
- max = **200.687**  (pre-fix 138.876; lift factor 1.4451×)
- median = **162.7435** (pre-fix 112.933; lift factor 1.4410×)
- mean = **142.6213** (pre-fix 104.332; lift factor 1.3670×)
- band split: **12/108/0/0** (pre-fix 10/110/0/0)

Cp comparison (vs gold standard tolerance 20%):
- x/c=0.0: actual Cp=0.5786, expected 1.0000, rel_err=**42.14%** (pre-fix 52.9%)
- x/c=0.3: actual Cp=−0.3391, expected −0.5000, rel_err=**32.17%** (pre-fix 32.4%)
- x/c=1.0: actual Cp=0.1104, expected 0.2000, rel_err=**44.79%** (pre-fix 45.5%)
- 3-point avg = **39.7%** (pre-fix 43.6%)

### §G.4 Root-Cause Analysis of Fix Under-Performance

Mean y+ lift factor matches a priori prediction (1.37× measured vs 1.46× predicted;
~6% gap attributable to the −2 cells in N_z and local geometric effects).
However, the y+_min face did NOT lift proportionally:
- predicted: 22.30 × 1.4575 = **32.51**
- measured: **23.61**
- under-performance: measured lift 1.059× vs predicted 1.4575× (27% shortfall)

**Mechanism**: The y+_min face sits at the leading-edge projection onto
NACA0012.obj (x/c ≈ 0). At that location the first-cell wall-normal thickness
is not determined by the far-field edge grading alone, but by the OBJ surface
projection curvature and the block-corner geometry. The uniform dir3 grading
retune lifts the far-field-dominated cells (shown by the 1.44× median/max lift)
but leaves the LE-projection-dominated cells mostly unchanged.

Additional observation: buffer-band count INCREASED from 10 to 12. This happens
because the new coarser first cell moves 2 additional faces (previously just
above y+=30) into the buffer band, while the LE cluster is structurally stuck
below 30. The fix moved the boundary in the wrong direction for the tail of
the distribution.

Cp improvements (3-pt avg 43.6% → 39.7%, ~10% rel_err reduction at x/c=0.0)
are real but small, consistent with the ~16% of faces still in or near buffer
layer. A priori estimate assumed 0% buffer; achieved 10%.

### §G.5 Recommended Next Paths (for Gate review)

Uniform dir3 grading alone cannot simultaneously satisfy CHK-3 (y+_min ≥ 30)
without either (a) making the far-field cells much coarser (violating y+_max ≤ 300
at the pressure-peak faces) or (b) changing the block topology to decouple
LE-adjacent cells from wake cells.

Candidate paths for next Gate cycle:
- **W1-revised**: non-uniform z-direction — split each block's grading into
  zones (near-wall fine, mid-span stretched). OpenFOAM supports this via
  multi-grading blocks. Est. 40-60 src/ lines. Would allow LE-specific lift.
- **L (low-Re rewrite)**: abandon wall-function, target y+ < 1 everywhere.
  Requires both mesh refinement (N_z 80 → ~300 with aggressive wall grading)
  AND wall BC rewrites (kqRWallFunction → kLowReWallFunction;
  nutkWallFunction → nutLowReWallFunction; omegaWallFunction with LRN switch).
  Large scope (~150+ src/ lines, multi-phase Gate).
- **H (hybrid topology)**: O-grid LE cap + C-grid wake. Major rewrite of
  _generate_airfoil_flow; several hundred lines. Separate Tier 1 Gate.
- **EX (accept current)**: accept 39.7% avg rel_err as known limitation,
  document in gold_standards/ as `known_deviations` — but this requires
  tolerance annotation change, which is a separate Gate trigger anyway.

Recommended next action: escalate to Notion Opus 4.7 Gate for Wave 3 verdict
and path selection. This Fix Plan Draft is insufficient; a new Fix Plan
Packet under W1-revised or L is required.

## §E Applicability Note

Phase A (Codex apply) executed and reverted per contract. No src/ change
persisted. Post-fix evidence captured in `reports/naca0012_airfoil/artifacts/`.
Wave 3 closeout escalated to Gate.

## §H Fix Plan Packet v2 (path H: hybrid LE edge grading, draft-only)

Gate verdict at `thread://41cc6894-2bed-814f-974b-0003bba02ff6/345c6894-2bed-804b-8721-00a9913925d1`
rejected path W and selected path H. This section is draft-only and closes the
seven new preconditions without changing `src/`, `tests/`, fixtures, or gold
standards. It references §G.4 as the root-cause basis: the failing `y+_min`
faces are LE-projection-dominated on `NACA0012.obj`, so the repair must act on
the LE edge parameterization rather than re-running another uniform `dir3`
retune.

### §H.1 COND-H1..H7 closure

COND-H1: Answer: the current `NACA0012` case already uses the `kOmegaSST`
automatic wall-treatment path and this packet keeps it unchanged. In the
generator, `0/k` uses `kqRWallFunction`, `0/omega` uses
`omegaWallFunction`, and `0/nut` uses `nutkWallFunction`
(`src/foam_agent_adapter.py:L5600-L5673`). The OpenFOAM source-tag reference is
`OpenFOAM-10`, specifically
`src/MomentumTransportModels/momentumTransportModels/derivedFvPatchFields/wallFunctions/omegaWallFunctions/omegaWallFunction/omegaWallFunctionFvPatchScalarField.H`,
which states that `omegaWallFunction` constrains omega for both low- and
high-Re models and, by default (`blended false`), uses the standard switch
between viscous- and log-region values based on `yPlusLam` from the
corresponding `nutWallFunction`. `nutkWallFunction` is the matching high-Re
wall-function viscosity BC, not `nutLowReWallFunction`. Therefore path L is
out-of-scope here: the selected fix changes mesh edge grading only and retains
the existing automatic SST wall treatment.

COND-H2: Answer: the repair acts only on the two LE-adjacent aerofoil patch
segments that own the failing windows `face_index 24-29` and `114-119`
(`yplus_profile.csv`). Those windows are the LE-end six faces of the two
30-face LE patch blocks generated by:
- lower LE block: `hex ( 7 4 16 19 0 3 15 12)` (`src/foam_agent_adapter.py:L5177-L5179`)
- upper LE block: `hex ( 20 16 4 8 21 15 3 9)` (`src/foam_agent_adapter.py:L5189-L5191`)

The explicit path-H grading scheme is:
- keep all six blocks at `(N_z = 80, simpleGrading_z = 40)` for wall-normal
  compatibility and keep blocks 2/3/5/6 unchanged
- change only the two LE blocks from uniform tangential spacing to a LE-end
  edge ratio of `R_LE = 6.0` across their 30 aerofoil faces
- apply the same `R_LE = 6.0` on the matching outer-cap edges of those same
  two blocks so the internal block mapping stays smooth
- leave shared interfaces to the mid-chord blocks at the existing `30 x 80`
  subdivision; no block count change, no new vertices, no OBJ edit

Decoupling method from mid-chord blocks: this candidate re-parameterizes only
the two LE boundary edge-pairs inside the existing LE blocks; it does NOT alter
the four non-LE blocks, the wake blocks, or any shared block-interface cell
counts. Compatibility with `NACA0012.obj`: the same projected aerofoil edges
stay projected (`4-7`, `16-19`, `8-4`, `20-16`), the LE tip remains anchored at
vertex `4/16`, and no surface geometry file or projection target changes.

COND-H3: Answer: the a priori `y+` contract for path H is stricter than the CHK
floor/ceiling and carries headroom. With `R_LE = 6.0` over 30 LE faces, the
LE-end six-face window grows by `1.8365x` versus the current uniform spacing
while the other four blocks stay at baseline. Predicted segmented bands:
- LE blocks (`24-29`, `114-119`): `y+ = 41.0 .. 63.0`
- mid-chord blocks: `y+ = 92 .. 145`
- TE / wake-adjacent blocks: `y+ = 55 .. 140`
- global contract: `y+_min = 41.0 >= 40` and `y+_max <= 145 < 250`

COND-H4: Answer: a priori buffer-band prediction is `0/120` faces in
`5 < y+ < 30`. All currently sub-30 faces live inside the two LE six-face
windows; the predicted LE minimum after path H is `41.0`, so the entire current
buffer cluster is lifted clear of the band without pushing any other segment
near the `y+_max` ceiling.

COND-H5: Answer: the a priori Cp contract for path H, with headroom relative to
CHK-5/6/7/13, is:
- LE (`x/c = 0.0`): `rel_err <= 22%`
- mid (`x/c = 0.3`): `rel_err <= 18%`
- TE (`x/c = 1.0`): `rel_err <= 18%`
- 3-point average: `<= 19.3%`

Reasoning: Wave 3 v1 already showed that even the wrong lever (uniform `dir3`)
improved the LE point from `52.9%` to `42.14%`. Path H directly targets the
measured LE-projection defect while restoring `0/120` buffer faces under the
existing SST automatic wall treatment, so the packet adopts conservative values
well below the pass thresholds (`35/30/35/28`) and still above the literature
best-case values noted in §C.2.

COND-H6: Answer: cross-case regression protection is explicit. Touchfile
whitelist for the future apply round:
- `src/foam_agent_adapter.py` only
- function scope: `_generate_airfoil_flow`
- edit scope inside that function: the `blockMeshDict` generation block only,
  specifically the two LE block grading entries and any immediately adjacent
  helper literals/comments needed to render them

Future apply-round git whitelist proof:
- `git diff --name-only <rollback-SHA>..HEAD -- src tests knowledge .planning`
  must return only `src/foam_agent_adapter.py`
- `git diff --name-only <rollback-SHA>..HEAD -- ':!src/foam_agent_adapter.py'`
  must be empty
- `OF-01/02/03` `blockMeshDict`, `system`, and `constant` baselines stay
  zero-touch because no generator outside `_generate_airfoil_flow` is in scope

COND-H7: Answer: scope budget remains inside the new hard cap. Planned apply
diff budget is `<= 36` unified-diff body lines and hard-capped at `<= 70`,
which also stays inside the inherited `src/** diff <= 80 lines` guard. The
touchfile whitelist remains exactly one source location:
`src/foam_agent_adapter.py::_generate_airfoil_flow` `blockMeshDict` generation
block only.

### §H.diff — draft unified diff sketch (not applied in this round)

```diff
--- a/src/foam_agent_adapter.py
+++ b/src/foam_agent_adapter.py
@@ -5176,24 +5176,34 @@
-    // simpleGrading avoids block-interface inconsistencies caused by edgeGrading.
+    // Path H draft: retain global dir3=40 and re-grade only the two
+    // LE-adjacent projected edge pairs so the LE-end six-face windows
+    // (24-29 and 114-119 in yplus_profile.csv ordering) no longer collapse
+    // into the NACA0012.obj nose projection.
+    le_edge_ratio = 6.0
+    le_lower_grading = "edgeGrading (6 1 1 6 6 1 1 6 40 40 40 40)"
+    le_upper_grading = "edgeGrading (6 1 1 6 6 1 1 6 40 40 40 40)"
     hex ( 7 4 16 19 0 3 15 12)
     (30 1 80)
-    simpleGrading (1 1 40)
+    {le_lower_grading}

     hex ( 5 7 19 17 1 0 12 13)
     (30 1 80)
     simpleGrading (1 1 40)

     hex ( 17 18 6 5 13 14 2 1)
     (40 1 80)
     simpleGrading (10 1 40)

     hex ( 20 16 4 8 21 15 3 9)
     (30 1 80)
-    simpleGrading (1 1 40)
+    {le_upper_grading}

     hex ( 17 20 8 5 22 21 9 10)
     (30 1 80)
     simpleGrading (1 1 40)

     hex ( 5 6 18 17 10 11 23 22)
     (40 1 80)
     simpleGrading (10 1 40)
```

Interpretation of the draft sketch:
- `6` is the LE-end tangential bias on the two LE aerofoil edge-pairs and on
  their matching outer-cap edge-pairs in the same blocks
- `1` preserves the unmodified internal / spanwise edge ratios
- `40` keeps the existing wall-normal grading on the four LE block normal edges
- blocks 2/3/5/6 remain byte-for-byte identical to the current generator

### §H.apriori — numeric predictions to be checked before any future apply

Mesh / `y+` predictions:
- current LE six-face minimum = `22.3036`
- path-H LE lift factor = `1.8365x` from `R_LE = 6.0`
- predicted LE minimum = `22.3036 * 1.8365 = 40.95`
- current LE six-face maximum = `34.2680`
- predicted LE maximum = `34.2680 * 1.8365 = 62.92`
- predicted global `y+_min / y+_max` = `40.95 / <=145`
- predicted buffer-band faces = `0/120`

Cp predictions:
- `x/c = 0.0`: `<= 22%`
- `x/c = 0.3`: `<= 18%`
- `x/c = 1.0`: `<= 18%`
- 3-point average: `<= 19.3%`

### §H.2 Apply / verification contract

The apply-round verification plan is unchanged from Wave 3 v1. Re-run
`CHK-1 .. CHK-13` exactly as written in §A.4, with no threshold relaxation and
no new waiver language. In particular:
- keep `CHK-2` hard fail at `> 71.0 deg` and soft warn at `> 70.0 deg`
- keep `CHK-3`, `CHK-4`, and `CHK-12` strict on `y+` / buffer-band outcomes
- keep `CHK-5`, `CHK-6`, `CHK-7`, and `CHK-13` at the existing pass thresholds
- keep `CHK-8`, `CHK-10`, and `CHK-11` unchanged
- keep rollback-SHA = current `HEAD`
- keep future execution trailer unchanged:
  `Execution-by: codex-gpt54`
  `Gate-approve: thread://41cc6894-2bed-814f-974b-0003bba02ff6/345c6894-2bed-804b-8721-00a9913925d1`

Draft-round guard: this section does not authorize `src/` edits. It only
documents the path-H candidate that would be eligible for a later apply cycle
if and only if the packet itself receives Gate approval.
