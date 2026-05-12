# Track C · Advisor e2e — Session 1 · case_010 DrivAer fastback LES

> **Date**: 2026-05-13
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: M6 row in ROADMAP carries `⚠ untested against real industrial cases`. Take one already-sediment case, run blind-mode advisor over raw inputs, score against ground truth.
> **Subject case**: `~/Desktop/case_010_drivaer_fastback_les/` v1 (last in 10-case roster · incompressible-LES root · DrivAer fastback half-vehicle)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Counter impact**: nil (Track C is a methodology validation arc, not a `autonomous_governance` DEC chain)

---

## 1. Protocol

**Blind-mode inputs read** (the engineer-equivalent surface before sediment was written):

- `scripts/build_cad.py` — geometric intent (12 named bodies, 2 intentional defects D1/D8)
- `case/log/01_blockMesh.log` — base mesh creation
- `case/log/02_surfaceFeatureExtract.log` — feature-edge extraction
- `case/log/03_snappyHexMesh.log` — sHM run (truncated 184 lines, mid Shell refinement iter 2)
- `case/system/snappyHexMeshDict` — mesh config
- `evidence/v1/check_mesh_summary.json` — mesh quality summary
- `evidence/v1/a2_d1_falsification.json` — A2 advisor output for D1 (0.35 mm side-mirror trim gap)
- `evidence/v1/thin_wall_d8_falsification.json` — thin_wall advisor for D8 (0.80 mm underbody plate)
- `evidence/v1/step_validation.json` — STEP body roster verification

**Deferred until after blind verdict** (ground truth):

- `evidence/v1/REPORT.md` — sub-session author's own writeup
- `.planning/methodology/industrial_case_solver_findings.md` § V43-V46 — corpus V-rows tied to case_010

## 2. Blind verdict (issued before reading REPORT.md / V-series)

Seven findings, severity tiered:

| # | Severity | Finding | Confidence |
|---|---|---|---|
| F1 | CRITICAL | STL coordinate-scale mismatch: STL in mm, blockMesh in m → STL bbox max 4610 m vs domain 60 m × 14 m × 23 m. Surface refinement 0 cells. Mesh contains no vehicle. | high (log evidence) |
| F2 | HIGH | `check_mesh_summary.json` reports `mesh_ok=true` despite all 6 geometry-derived wall patches (vehicle_body / wheels / mirror / trim / underbody) being **empty** post-castellation. Standard checkMesh metrics don't cover "patches that should have faces have zero faces". | high |
| F3 | MED | A2 D1 PASS is `[QUESTIONABLE]` — `_run_shared` returns hardcoded placeholder `bbox_overlap_fraction=1.0 / area_diff_fraction=0.0` regardless of actual gap distance. PASS confirms algorithm runs cleanly, not gap-defect detection capability. | high |
| F4 | VALIDATED | thin_wall D8 `severity=critical` at 3 refinement scenarios is consistent with prior 6-of-6 cross-topology arc; arc closes at this 7th case. | high |
| F5 | MED | sHM log truncated at 184 lines mid Shell refinement iter 2. Plausibly external interrupt (wall-clock / container kill); but the **operative observation** is that surface refinement iter 0 marked 0 cells and stopped — i.e. sHM was already doing nothing geometrically useful regardless of interrupt timing. | high |
| F6 | LOW | Even after scale fix, D1 0.35 mm defect is sub-cell at sHM levels (5,6) on 0.16 m base (effective cell ≈ 5 mm). Defect will be silently merged in mesh; A2-v2 would surface it pre-mesh but mesh itself cannot represent it without level 9+ local refinement. | high |
| F7 | LOW | The `mesh_ok` boolean criterion in `07_check_mesh.py` (and any extracted helper) is too permissive: it gates only on standard checkMesh internal-geometry metrics, not on "the intended geometry is actually present in the mesh". Generic post-mesh sanity layer is missing. | medium |

**Predicted root cause of v1 sHM no-snap**: STL exported by `01_extract_stl.py` (CadQuery `cq.exporters.export(..., exportType="STL")`) preserves the native mm unit of `build_cad.py`; `system/snappyHexMeshDict` `geometry { drivaer.stl { type triSurfaceMesh; … } }` block has **no** `scale (0.001 0.001 0.001)` transform; therefore sHM treats coordinates as m, and the vehicle sits at km-scale outside most of the domain.

**Suggested fix paths** (any one closes F1):
1. Add `scale (0.001 0.001 0.001);` inside `geometry { drivaer.stl { … } }` in snappyHexMeshDict
2. Re-export STL in m: scale CadQuery shapes by 0.001 in `01_extract_stl.py` before `cq.exporters.export`
3. Rewrite STL: `surfaceTransformPoints -scale '(0.001 0.001 0.001)' drivaer.stl drivaer_m.stl`
4. Apply same transform to the eMesh path (`drivaer.eMesh` is in the same units the STL was extracted from)

## 3. Ground truth comparison

**REPORT.md** (subject case sub-session author's writeup): treats blockMesh + interrupted sHM as a "v1 mesh stage delivered"; F4 (initial mesh quality) reports `mesh_ok=True`, `nCells=4,644,000`, `max_skewness=3e-13`; lists the 6 domain patches and notes them as "all expected names" — **silent about the 6 wall patches** (vehicle_body etc.) that sHM registered but with zero faces. V44 candidate proposes "sHM refinement boxes near vehicle (level 4-5) + mirror (level 5-6) + wheels (level 4-5) + wake (level 3) projected to push total mesh to 15-25M" — projecting forward without checking whether v1's truncated sHM had actually started those surface refinements.

**V-series corpus** (`industrial_case_solver_findings.md` V43-V46, landed 2026-05-08):

- **V43** A2 D1 `[QUESTIONABLE]` 7-of-7 → matches my F3 exactly
- **V44** thin_wall D8 `[VALIDATED]` 7-topology → matches my F4 exactly
- **V45** First transient LES infrastructure (templates/writers landed) → I did not produce a blind finding on this (it's a forward-looking artifact-extraction marker, not a v1 defect)
- **V46** sHM interrupted iter 2 — root cause attributed to **base cell 0.16 m too fine** → projected 15-25M cells → single-process Mac docker can't finish → fix = bump base cell to 0.30 m

**V46 is wrong about the operative cause.** Coarsening base cell to 0.30 m would still produce a mesh with zero vehicle. Surface refinement iter 0 in the log marked exactly 0 cells (line: "Marked for refinement due to surface intersection: 0 cells. ... Selected for refinement: 0 cells (out of 4644000). Stopping refining since too few cells selected."). All the cell-count growth observed in Shell refinement iter 0-2 (4.6M → 4.86M → 6.55M → 1.9M-marked) is the `refine_wake_box` (level 3 inside (4.61 0 0)-(23.05 4.61 1.5)) inflating through `nCellsBetweenLevels=3` buffer cascade — independent of the STL.

The scale mismatch was missed because the verification path stopped at `checkMesh OK + nCells > 0`. The STL was loaded, regions parsed correctly (`Adding patches for surface regions: drivaer:vehicle_body ... underbody_sensor_cover_thin`), but the eMesh bounding box (sHM log line 39: `boundingBox: (0 -1.466716e-14 0.1025699) (4610 1120.85 1444.2791)`) was the load-bearing diagnostic and was not surfaced into the v1 audit JSON.

## 4. Score

| Blind finding | vs corpus | Verdict |
|---|---|---|
| F1 STL scale mismatch (root cause of v1 sHM no-snap) | corpus diagnoses different cause in V46 | **NEW** — V82 backfill |
| F2 mesh_ok despite empty wall patches | corpus + REPORT.md both miss | **NEW** — V83 backfill (methodology gap) |
| F3 A2 D1 questionable | V43 match | hit |
| F4 thin_wall D8 validated | V44 match | hit |
| F5 sHM log truncated | V46 partial match (different attribution) | partial |
| F6 D1 sub-cell post-fix | not in corpus | new methodology note (lower urgency) |
| F7 mesh_ok criterion too permissive | not in corpus | new methodology note (folds into V83) |

**Tally**: 2 hits + 1 partial + 2 new (V82, V83) + 2 methodology notes. The Track C session caught a load-bearing root-cause that the case-thread author's audit + V46 sediment both missed.

## 5. What this validates / what it doesn't

**Validates**:

- An M6-style advisor with **read access to corpus + raw case logs** can catch v1-stage bugs that the sub-session author's own audit + corpus sedimentation pipeline missed. Concrete evidence: V82 root cause.
- The "Claude Code session as the advisor" framing (per `feedback_claude_code_is_the_advisor.md`) is empirically defensible: a session with Read/Grep + V-series context produces a load-bearing finding within one session.
- The blind-mode protocol (read raw inputs, write verdict, **only then** read REPORT/V-rows) is necessary; otherwise the verdict gets contaminated.

**Does NOT validate**:

- An M6 RAG-backed advisor with vector retrieval rather than full-context read. This session used direct Read on the corpus + logs (~70k tokens of evidence loaded into reasoning context). A real M6 advisor route (`GET /api/cases/{id}/ai-review`) would have a tighter token budget and might miss F1 if the relevant log line wasn't retrieved.
- The N6.x route surfaces (V61-156..V61-161). N6 routes were landed but never been pointed at a real case; this session does not run them.
- That Claude Code session is the *right* advisor architecture in production. It just shows the **upper-bound advisor capability** when full corpus + log access is available — useful as a target for the actual M6 route to approach.

**Caveats**:

- Sample size = 1 case (case_010). Need ≥3 advisor e2e sessions across different solver classes to claim broad coverage.
- I had already read V32/V33/V34, V38/V40 from a survey grep before locking into case_010; some bias toward expecting "advisor placeholder" patterns is plausible. case_010-specific findings (F1/F2/F5) were not in my pre-grep scope.
- Track C sessions are expensive in main-context terms (this session loaded ~80k tokens of evidence). Not viable as routine M6 path — only as "the gold-standard advisor whose verdicts the cheaper route should approximate".

## 6. Concrete deliverables (this session)

1. V82 backfill — `industrial_case_solver_findings.md` § V82 STL coordinate-scale mismatch case_010 v1 root cause
2. V83 backfill — `industrial_case_solver_findings.md` § V83 `mesh_ok` doesn't cover "geometry-derived patches have zero faces" blind spot
3. V46 amendment — add cross-reference note pointing V46 readers to V82 for true root cause
4. ROADMAP M6 row — replace `⚠ untested against real industrial cases` with `⚠ untested as route; Claude-Code-session-as-advisor e2e validated on case_010 (2026-05-13, RETRO Track C session 1, surfaced V82+V83 missed by corpus)`
5. This retro file

**No source code changes this session.** F1's fix (scale transform in snappyHexMeshDict) is a per-case sub-session action; the main-project lesson (V82) is the cross-case pattern. If the same scale-mismatch pattern surfaces in another case (Pillar-2 trigger), then a `surface_scale_advisor` extraction sub-DEC under DEC-V61-198 becomes warranted.

## 7. Suggested next Track C sessions

- **Session 2**: case_011 plate-fin compact HX (internal-flow CHT, 16-mention cross-cuts cluster) — high V-row density makes scoring stricter
- **Session 3**: case_004 NREL Phase VI MRF (rotating machinery) — only V22/V23/V24 mentions; sparse coverage might surface gaps
- **Session 4**: case_009 Sandia Flame D (reacting) — V38-V41 cluster around mech-loader; advisor's chemistry coverage is novel

Pacing: at most 1 Track C session per week to avoid context-overload of main session. Each produces 0-2 new V-rows + retro; net throughput is corpus health and M6 calibration data, not feature velocity.

## 8. Cross-references

- **Parent feedback**: `feedback_claude_code_is_the_advisor.md` (M6 charter advisor button → replaced by Track C dogfooding)
- **Parent DEC**: V61-198 (industrial-case container pivot)
- **V-rows landed**: V82, V83 (this session)
- **V-row amended**: V46 (cross-reference added)
- **ROADMAP row**: M6 main-line table

## 9. V82 fix-verification appendix (2026-05-13 · post-retro within same session)

Per user direction "推进 A" after retro §6 landed, the V82 fix was tested in-place on case_010 sandbox to upgrade evidence from "log-inferred" to "measured":

**Fix path used** (option 3 in V82 row): OpenFOAM offline tool

```bash
cd ~/Desktop/case_010_drivaer_fastback_les/case
# backups
cp constant/triSurface/drivaer.stl    constant/triSurface/drivaer.stl.bak_mm
cp constant/triSurface/drivaer.eMesh  constant/triSurface/drivaer.eMesh.bak_mm
mkdir -p log/v1_baseline
cp log/01_blockMesh.log log/02_surfaceFeatureExtract.log log/03_snappyHexMesh.log log/v1_baseline/

# rewrite STL in m via OpenFOAM surfaceTransformPoints (preserves 6-solid block structure)
docker run --rm --entrypoint /bin/bash -v "$PWD:/case" -w /case \
  opencfd/openfoam-default:2312 -c "source /usr/lib/openfoam/openfoam2312/etc/bashrc; \
    surfaceTransformPoints -scale '(0.001 0.001 0.001)' \
      constant/triSurface/drivaer.stl constant/triSurface/drivaer_m.stl && \
    mv constant/triSurface/drivaer_m.stl constant/triSurface/drivaer.stl"

# re-extract feature edges in m
STAGE=features bash scripts/06_run_mesh.sh

# re-run sHM (interrupted at maxGlobalCells cap mid iter 3 — see V46)
STAGE=snappy   bash scripts/06_run_mesh.sh
```

**Before/after diagnostic comparison** (same `snappyHexMeshDict`):

| Diagnostic | v1 baseline (mm STL) | v1.5 fixed (m STL) |
|---|---|---|
| `eMesh boundingBox` | `(0, ~0, 0.10) (4610, 1120.85, 1444.28)` | `(0, ~0, 0.00010257) (4.61, 1.12085, 1.44428)` |
| Surface refinement iter 0 marked cells | **0** ("Stopping refining since too few cells selected") | **20,749 cells** (iter 1-4: 32,279 / 31,315 / 20,161 / 3) |
| Intersected edges trajectory | **0** throughout (all iterations) | 911 → 2,408 → 6,410 → 14,408 → 33,357 → 67,641 → 120k → 187k → 247k → 291k → **345k** |
| Cells per refinement level (final) | level 0 only (4.6M uniform hex) | levels 0/1/2/3/4/5/6 active (4.6M / 70k / 185k / 15.2M / 808k / 505k / 27k) |
| Total cell count (final) | 4,644,000 (= blockMesh exactly · no growth) | 21,437,177 (hit `maxGlobalCells=20,000,000` cap mid iter 3) |

**Conclusion**: V82 fix unambiguously works. sHM now actually snaps to the vehicle, mirror, wheels, and defects. The mesh genuinely contains the body geometry.

**Secondary obstruction revealed** (V46's legitimate finding, post-V82): base cell 0.16 m × full body refinement level (4, 5) + mirror (5, 6) explodes past the 20M-cell cap. Two paths forward (per V46 fix options): (1) coarsen base cell to 0.30 m (V46 recommendation), (2) raise `maxGlobalCells` to 30-40M and run parallel sHM. Neither is in scope for Track C session 1 (this would be a case_010 v2 sub-session deliverable).

**Evidence preserved in case_010 sandbox** (not in main repo):
- `case/log/v1_baseline/{01_blockMesh.log, 02_surfaceFeatureExtract.log, 03_snappyHexMesh.log}` — baseline mm-STL logs
- `case/log/{01_blockMesh.log, 02_surfaceFeatureExtract.log, 03_snappyHexMesh.log}` — v1.5 fixed m-STL logs (overwritten by re-run)
- `case/constant/triSurface/drivaer.stl.bak_mm` — original mm STL
- `case/constant/triSurface/drivaer.eMesh.bak_mm` — original mm eMesh
- `case/constant/triSurface/drivaer.stl` — current m STL
- `case/constant/triSurface/drivaer.eMesh` — current m eMesh

**Main repo deliverables** (this appendix):
- V82 status flipped `partial 2026-05-13` → `fix-verified 2026-05-13 · 1 case`
- Quick-lookup index V82 row updated with verification numbers
- V46 amendment stands (V82 is primary cause; V46 is now the legitimate active secondary)

**What this does NOT do**: case_010 v1.5 is not yet a sediment release in the case-thread sense — no v1.5 REPORT.md was written, no parts_manifest update, no full audit. To upgrade V82 from "fix-verified · 1 case" to "validated · cross-case", a 2nd case with the same scale pattern must surface independently (Pillar-2 trigger). case_007 (KCS, also CadQuery STL pipeline) is the highest-probability next candidate; main session should grep case_007 sHM log eMesh bbox before next dispatch.

— EOF —
