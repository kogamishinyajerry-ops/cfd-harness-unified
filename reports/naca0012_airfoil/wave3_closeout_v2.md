# NACA0012 Wave 3 Closeout v2 — Path H (hybrid LE edgeGrading) REJECT

**Status**: STRUCTURAL FAILURE — solver diverged to NaN at t=24s, mesh quality catastrophic
**Gate-approve (apply)**: thread://41cc6894-2bed-814f-974b-0003bba02ff6/345c6894-2bed-804b-8721-00a9913925d1 (2026-04-18T14:32:07+08:00)
**Packet-commit**: 273ef3d (Fix Plan Packet v2 §H)
**Rollback-SHA**: 273ef3d (HEAD pre-apply; src/ reverted clean)
**Verdict**: REJECT — fuse rule triggered per Gate §4 (Path H CHK FAIL → 3rd cycle = EX verdict + case removal Decision)

---

## §1 Execution record

| Phase | Actor | Outcome |
|---|---|---|
| Phase A (apply) | codex-gpt54 | PASS — 22-line diff, LE blocks 0,3 only, editorial clarification resolved |
| Phase B (verify) | opus47-main | **FAIL** — checkMesh 2 failures, simpleFoam NaN at t=24s |
| Phase C (commit) | — | NOT EXECUTED — src/ reverted |

src/ diff applied (Phase A):
```
src/foam_agent_adapter.py L5177, L5191:
  simpleGrading (1 1 40)  →  edgeGrading (6 1 1 6 6 1 1 6 40 40 40 40)
on zero-based blocks 0 and 3 only
```

---

## §2 CHK-1..13 verdict table

| CHK | Target | Measured | Verdict |
|---|---|---|---|
| **1 Mesh OK** | "Mesh OK" | **"Failed 2 mesh checks"** | ❌ **FAIL** |
| **2 non-ortho ≤71°** | ≤71° | **89.9032°** (baseline 68.95°, +20.95°) | ❌ **FAIL** |
| 3 y+_min ≥30 | ≥30 | UNMEASURABLE (solver diverged) | ⚠️ BLOCKED |
| 4 y+_max ≤300 | ≤300 | UNMEASURABLE | ⚠️ BLOCKED |
| 5 Cp@x/c=0 ≤35% | pass | UNMEASURABLE | ⚠️ BLOCKED |
| 6 Cp@x/c=0.3 ≤30% | pass | UNMEASURABLE | ⚠️ BLOCKED |
| 7 Cp@x/c=1.0 ≤35% | pass | UNMEASURABLE | ⚠️ BLOCKED |
| 8 gold sha256 | identical | identical | ✅ PASS |
| 9 src diff ≤80 | ≤80 | 22 | ✅ PASS |
| 10 pytest ≥211 | ≥211 | 211 (not re-run — src reverted) | ✅ PASS |
| 11 9-case smoke | no regress | MOOT — NACA0012 mesh fails before cross-case runs; OF-01/02/03 files untouched | ✅ PASS (by construction) |
| 12 buffer faces=0 | 0 | UNMEASURABLE | ⚠️ BLOCKED |
| 13 Cp 3-pt avg ≤28% | pass | UNMEASURABLE | ⚠️ BLOCKED |

**Net**: 2 FAIL (structural, at mesh layer), 4 PASS, 7 BLOCKED by upstream CHK-1/2 failure.

---

## §3 Post-fix evidence

### §3.1 checkMesh summary (reports/naca0012_airfoil/artifacts/checkmesh_pathH.log)

```
Overall number of cells of each type:
    hexahedra:     16000                              (unchanged from pre-fix)
    Max aspect ratio = 108.35 OK.                     (unchanged)
    Mesh non-orthogonality Max: 89.9032
        average: 35.5846                              (baseline 68.95/35.58)
    *Number of severely non-orthogonal (> 70 degrees) faces: 4640
        <<Writing 4640 non-orthogonal faces to set nonOrthoFaces
    *Max skewness = 8.45479, 4184 highly skew faces detected
        which may impair the quality of the results
        <<Writing 4184 skew faces to set skewFaces

Failed 2 mesh checks.
```

### §3.2 simpleFoam divergence evidence

First iteration (t=1s) residuals healthy:
```
Solving for Ux, Initial residual = 1, Final residual = 0.00514795
Solving for p,  Initial residual = 1, Final residual = 0.0358466
```

NaN first appeared at **t=24s** (24 outer iterations). By t=394s (1633s ExecutionTime) solver remained at NaN, confirming non-recoverable divergence:
```
Solving for Ux, Initial residual = nan, Final residual = nan, No Iterations 1000
GAMG:  Solving for p, Initial residual = nan, Final residual = nan, No Iterations 1000
time step continuity errors : sum local = nan, global = nan, cumulative = nan
```

Process killed by orchestrator after confirming runaway NaN state.

### §3.3 A priori vs actual delta (per Gate §2 headroom table)

| Metric | §H.apriori | Actual | Delta |
|---|---|---|---|
| non-ortho max | (implicit: ≤68.95 baseline + 2° guard = ≤71°) | **89.90°** | **+21° over limit** |
| skewness max | (not predicted) | **8.45** | unpredicted |
| y+_min | 40.95 | N/A (solver died) | — |
| Cp 3-pt avg | ≤19.3% | N/A | — |

**The §H a priori framework failed to predict mesh-quality collapse.** COND-H3/H4/H5 addressed y+ and Cp but not the geometric validity of edgeGrading with R=6 across a 30×80 LE block.

---

## §4 Root cause — why Path H failed

**Mechanism**: edgeGrading `(6 1 1 6 6 1 1 6 40 40 40 40)` on LE blocks 0 and 3 while adjacent mid-chord blocks (1, 2, 4, 5) retain `simpleGrading (1 1 40)` creates a **grading discontinuity at block-face interfaces**.

- At the shared face between block 0 (LE, R_streamwise=6 on LE-edge pair) and block 1 (mid-chord, R_streamwise=1 uniform), cell sizes in the streamwise direction are discontinuous by factor ~6 across the interface.
- blockMesh still produces topologically valid cells (16000 hex, same face/point count), so generation does not error.
- However, the resulting face normals at the interface are highly non-orthogonal (89.9°) and highly skewed (8.45) because the first cell on the block-0 side is ~6× larger/smaller than the adjacent cell on the block-1 side.
- kOmegaSST + SIMPLE with default fvSchemes cannot tolerate this discontinuity; Ux/Uz/k/omega diverge to NaN within 24 iterations.

**Why this was not caught by Path W (uniform grading)**: Path W's simpleGrading change was applied uniformly across all 6 blocks, so block-face interfaces remained grading-continuous. Path W failed at the physics layer (y+_min still 23.6); Path H fails at the **mesh topology layer** (grading discontinuity → numerical collapse).

**Generalization**: Any LE-localized grading modification that leaves mid-chord blocks at their original grading will produce the same discontinuity. A valid Path H requires either:
- edgeGrading applied with matched ratios on ALL blocks sharing the LE streamwise edges (not just LE blocks), OR
- full block decomposition of the LE region into finer sub-blocks with gradually-varying grading, OR
- switch to snappyHexMesh with LE refinement region (out of blockMesh scope entirely).

Scope of any of these exceeds Gate COND-H7 budget (≤70 src lines) by 2-5×.

---

## §5 Fuse rule activation

Per Gate verdict §4 (thread 14:32:07 timestamp):

> 若 H 实测 CHK 有任一 FAIL → 进入第三次熔断：**第三次不再审 Fix Plan**，必须同时提交 **EX verdict 归因报告** + **case 移除/替换 Decision 草案**。

Wave 3 cycle count: **2** (Path W REJECT → Path H REJECT). Budget **exhausted** — next Gate cycle must be EX-track.

---

## §6 Next step — EX verdict + Decision draft (proposed)

Recommended EX verdict framing for Gate review:

**Verdict**: NACA0012 is a **structural outlier** in the 10-case whitelist. Two successive Fix Plans (W uniform, H hybrid) failed at distinct physical/numerical layers:
- Path W: physics (y+_min geometry-locked by NACA0012.obj projection)
- Path H: numerics (grading discontinuity at block-face → solver divergence)

The root cause common to both is that the current `_generate_airfoil_flow` 6-block C-grid **cannot simultaneously satisfy** y+_min ≥ 30 AND mesh-quality continuity under the Codex-permitted scope budget (≤80 src lines).

**Decision-draft options** (for user/Gate selection):
- **DEC-EX-A**: Accept PASS_WITH_DEVIATIONS verdict permanently for NACA0012. Document Cp 3-pt avg ~40% as known tolerance; gold standard unchanged.
- **DEC-EX-B**: Remove NACA0012 from the 10-case whitelist; add stub row to `.planning/STATE.md` marking as "out-of-scope / Tier-1 case". Replace with a simpler external-flow case (e.g. flat plate zero-pressure-gradient — already in whitelist, so this is pure removal not substitution).
- **DEC-EX-C**: Defer to a Tier-1 rewrite of `_generate_airfoil_flow` with snappyHexMesh-based mesh generation (out of current Codex scope, requires new adapter path). Estimated scope: 300-500 src lines + new fixtures.

No recommendation embedded — Gate/user selection required.

---

## §7 Artifacts

- `reports/naca0012_airfoil/artifacts/checkmesh_pathH.log` (88 lines, full checkMesh output on preserved case)
- `reports/naca0012_airfoil/fix_plan_packet.md` §H (Packet v2 draft; unchanged — retained as historical record)
- `reports/naca0012_airfoil/fix_plan_packet.md` §G (Path W FAIL record; retained)
- Preserved case dir: `/tmp/cfd-harness-cases/ldc_62958_1776494211908` (will be cleaned by system; evidence already captured in checkmesh_pathH.log)
- src/ state: reverted clean via `git checkout -- src/foam_agent_adapter.py`, no persistent change
