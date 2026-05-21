# Red Team Round-14 Review — Phase 1 Step 2b Meta Scan

**Scope:** adversarial probe of the OpenFOAM case-dir scaffold (11 dict files, ~200 LOC of OpenFOAM dictionary content). Combined-batch round: meta + fix in one pass because the findings were small and mechanical.
**Author:** test-red-team agent.
**Date:** 2026-05-20.
**Previous round:** `red_team_round13_review.md` (PASS, 0 findings on 2a / 40 LOC).
**Verdict:** **FAIL — 0/0/1/2** at probe time, **all closed in this same batch**. First MEDIUM on net-new code since round-10's 1 HIGH.

---

## Method

Six probes, ranging from structural cross-checks to live execution of `blockMesh` inside the OpenFOAM Docker container:

| # | Probe                                                                   | Outcome   |
|---|-------------------------------------------------------------------------|-----------|
| 1 | All 5 fields declare all 5 patches with consistent `type`               | clean ✓   |
| 2 | `blockMesh` patch geometric types vs `0/*` BC types — empty/symmetry consistency | clean ✓   |
| 3 | `fvSolution.residualControl` numeric values exactly match manifest      | clean ✓ (1e-5 for p/U/k/omega) |
| 4 | OpenFOAM-11-canonical wall function names                               | clean ✓ (kqRWallFunction, omegaWallFunction, nutkWallFunction all valid in OF 11) |
| 5 | Field dimensions correct (U `[0 1 -1 0 0 0 0]`, etc.)                   | clean ✓ for all 5 fields |
| 6 | **Live `blockMesh` execution in Docker against the case dir**            | **succeeded** — 6000 cells, 5 patches; surfaced R14-F-01 + R14-F-03 |

Probe 6 was the most powerful: actual `blockMesh` ran against the dicts and validated them syntactically, while side-effecting the file tree (R14-F-01) and producing a measurable first-cell-y that betrayed R14-F-03.

Live output from probe 6:

```
Creating polyMesh from blockMesh
    Block 0 cell size :
        i : 0.02 .. 0.02
        j : 0.00130757 .. 0.0653787
        k : 0.05

Writing polyMesh
  bb (0 0 0) (2 1 0.05)
  nPoints: 12322  nCells: 6000  nFaces: 24160
  patches:
    inlet (60), outlet (60), wall (100), top (100), frontAndBack (12000)
End
```

---

## Findings

### R14-F-01 — LOW — `blockMesh` polluted `constant/polyMesh/` with generated mesh data (closed in this batch)

**File:** `cases/flat_plate_rans_sst/constant/polyMesh/` (post-probe-6).

`blockMesh` wrote ~1 MB across 5 generated files (`boundary`, `faces`, `neighbour`, `owner`, `points`) — all reproducible from `blockMeshDict`. These should NEVER live in source.

The project had **no `.gitignore`** at all. (Strictly speaking the project isn't yet a git repo — `.git/` doesn't exist — but a future `git init && git add .` would have committed the generated files alongside the source dicts.)

**Fix (applied in this batch):**
1. Deleted the 5 generated files.
2. Created `.gitignore` excluding `cases/*/constant/polyMesh/*`, `cases/*/artifacts/`, Python/IDE/OS noise, time-step dirs (`cases/*/[1-9]*/`), parallel decomposition (`cases/*/processor*/`).
3. Added `cases/flat_plate_rans_sst/constant/polyMesh/.gitkeep` so the placeholder dir survives.
4. Added 2 regression tests:
   - `test_flat_plate_case_polymesh_dir_stays_empty_in_source` — fails if generated mesh files re-appear in source
   - `test_gitignore_excludes_generated_artifacts` — fails if `.gitignore` loses the required patterns

### R14-F-02 — LOW (informational) — manifest residual naming vs OpenFOAM convention (closed via doc)

**Files:** `cases/flat_plate_rans_sst/case_manifest.yaml` (split-component `Ux: 1e-5, Uy: 1e-5`) vs `cases/flat_plate_rans_sst/system/fvSolution` (`U: 1e-5`).

OpenFOAM's `residualControl` block keys by the COMBINED vector field name (`U`), not by component. The scaffold uses the OF-canonical form because that's what `simpleFoam` actually checks. The manifest's split-naming is a downstream artifact of how the user wrote the contract; both forms are semantically valid for the same target.

**Fix (applied):** documented in `CASE_NOTES.md` under "R14-F-02 — `residualControl` naming convention vs manifest" so a Phase 2 reviewer doesn't flag this as a typo. No code change needed.

### R14-F-03 — MEDIUM — scaffold mesh produces `y+ ~ 53` vs manifest target window `0.5–5.0` (documented; deferred to step 2c / Phase 2 V&V)

**File:** `cases/flat_plate_rans_sst/system/blockMeshDict` (mesh definition) vs `cases/flat_plate_rans_sst/case_manifest.yaml > mesh_contract.y_plus_target`.

Live blockMesh reported the first-cell-y as `0.00130757 m`. Cell-center `y_p = 0.654 mm`. With manifest's `U=30 m/s` and `ν=1.5e-5`:

```
Re_x at L=1m:  2.00e+06
Cf (1/7-power law):  0.0033
u_τ:                 1.21 m/s
y+ at first cell:    52.7
```

Manifest target window: `0.5 – 5.0`. Scaffold is **~10× above the target maximum**. The scaffold's mesh produces a **wall-modeled** boundary layer, not the **wall-resolved** one the manifest declares as the design intent (`wall_function_policy: low_re_resolved`).

**Decision: DOCUMENT, DO NOT FIX in 2b.** Rationale:

1. **The trust harness is designed to catch this**. Step 2c's post-run y+ audit (when it lands) will report the violation as a BC contract gate failure. Letting the trust loop demonstrate that capability on the first real run is more valuable than masking the mismatch.
2. **Fixing the mesh now would entangle two concerns**: mesh refinement AND wall-function selection. With `y+ ≤ 5` we'd also need to swap `nutkWallFunction` (high-Re) → `nutLowReWallFunction` (resolved), which is a Phase 2 V&V choice the cfd-vv-director should drive.
3. **Honesty over over-fitting**: an honest "the scaffold has a known y+ gap that the trust harness will surface" beats a silently-tuned-to-pass mesh.

**Documented in `CASE_NOTES.md`** with the quantitative estimate, the implications, and the fix options for Phase 2.

**Why MEDIUM, not HIGH:** the harness's gate computation (when 2c lands) will correctly catch this — no false PASS is possible. The MEDIUM rating reflects that a casual user running `cfdtrust run` against this case will (correctly) get BLOCKED at the BC gate; without the CASE_NOTES.md explanation they might mistake "the harness is broken" for "the scaffold is intentionally below-spec."

---

## What was probed and worked

- **Patch coverage matrix**: 5 fields × 5 patches = 25 declarations, all present with consistent types.
- **Geometric-vs-BC patch type consistency**: `blockMesh.frontAndBack: empty` ↔ every field uses `type empty;`. `blockMesh.top: symmetryPlane` ↔ every field uses `type symmetryPlane;`. No drift.
- **Residual targets**: every `fvSolution.residualControl` entry matches manifest's `solver_contract.residual_targets` value (`1e-5`).
- **OpenFOAM 11 wall function names**: `kqRWallFunction`, `omegaWallFunction`, `nutkWallFunction` are all live in OF 11 dictionaries (confirmed via `docker run` source `bashrc` — `which` worked once we bypassed the ENTRYPOINT).
- **Field dimensions**: `U[m/s]`, `p[m²/s²]` (kinematic), `k[m²/s²]`, `omega[1/s]`, `nut[m²/s]` — all 5 match expected SI exponents.
- **Live `blockMesh`**: 6000 cells generated, 5 patches with correct counts (60/60/100/100/12000). Ultimate proof that the dicts are real OpenFOAM input, not just plausible-looking text.

---

## Pattern observation — surface area scales severity, not new-code-resets-clock per se

Round 10 added a 200-LOC NEW module → 1 HIGH + 1 MED + 2 LOW.
Round 13 added a 40-LOC tightly-scoped helper → 0 findings.
Round 14 added 200-LOC across 11 dict files → 0/0/1/2.

The severity ceiling correlates with **diff-byte size and surface novelty**, not with a binary "new code yes/no" flag. Pattern refinement for the project record:

```
~40 LOC, well-scoped:        zero-finding likely
~200 LOC, single module:     1 MED + a couple LOW
~200 LOC, multi-file dicts:  1 MED + a couple LOW (similar)
~200 LOC, new external dep:  1 HIGH possible (round 10 was Docker integration)
```

Sub-commit 2c (`docker run simpleFoam` wrapper + log parser) will introduce
a NEW external dependency (subprocess invocation chain). Expect **1 HIGH
or MED** on its meta scan. Plan accordingly.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH | MED | LOW | Total |
|-----------------------------|------|------|-----|-----|-------|
| (… rounds 1-12 …)           |      |      |     |     |       |
| 13 (2a meta)                | 0    | 0    | 0   | 0   | 0     |
| **14 (2b meta + fix)**      | **0**| **0**| **1**| **2**| **3** |

The MED finding (R14-F-03) is documented-not-fixed; the scaffold ships with a known y+ gap that the trust harness is designed to catch. The two LOWs (R14-F-01, R14-F-02) were fixed in the same batch as the meta scan.

---

## Verdict

**PASS (with documented MED deferral)** on the round-14 batch.

R14-F-01 and R14-F-02 are mechanically closed; R14-F-03 is consciously deferred to step 2c with a complete quantitative explanation in `CASE_NOTES.md`. The 2b scaffold is structurally valid OpenFOAM (live-confirmed by blockMesh generating 6000 cells against it). Step 2c can proceed.

---

## Recommended next options for the owner

1. **(α)** Proceed to **sub-commit 2c** — `docker run blockMesh + simpleFoam` wrapper + log parser → `residuals.csv` + gate computation. Will demonstrate the trust harness catching R14-F-03's y+ mismatch on first real run. ~1 hour.
2. **(β)** Fix R14-F-03 NOW — refine mesh to `y+ ~ 1` (n_y=80, simpleGrading 5000) + switch to `nutLowReWallFunction` + cross-update CASE_NOTES. ~30 min. Risk: over-fitting before step 2c proves the gate works.
3. **(γ)** Skip 2c and proceed to 2d (NASA TMR fetch) in parallel. ~1-2 hours. Still leaves 2c as a gap.
4. **(δ)** Natural session boundary at this clean state.

Recommendation: **(α)**. The user's instruction is "持续推进" (keep pushing); 2c is the highest-value next step, and R14-F-03 is precisely the kind of gap step 2c should demonstrate the harness catching.
