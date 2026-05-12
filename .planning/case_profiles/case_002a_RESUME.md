# case_002a · APU bay buoyantSimpleFoam · RESUME

**Last session**: 2026-05-12 (full-day mesh quality investigation arc · v27 → v33 → reverted to v32)
**Status**: Mesh quality structurally explored across 7 intervention classes. **v32 = best mesh state** (3.10M cells, max_skewness 6.875, 20 skew faces, 3 failed checks). Verdict still FAIL because max_skewness > 4 PASS threshold, but **98.2% skew face reduction** from v27 baseline (1119 → 20). All non-trivial mesh-tuning levers empirically exhausted; remaining residue is on complex CAD bodies (body_4 40%, body_8, Frame_1, beam_*, body_6/7/11) that cannot be safely cleaned without industrial-CAD remeshing tools or relaxed sHM controls.

**Strategic context**: This case_002a arc validated DEC-V61-198 §"Run-and-correct" pillar — Claude Code session window drove a complete industrial-scale mesh debug end-to-end across 6 mesh iterations + 1 reverted attempt, sedimenting 6 V-findings (V73-V78) into the corpus. The strategic claim "Claude Code drives industrial CFD" is empirically validated for geometry ingest + mesh build + mesh debug + sediment. **Not yet validated**: solver execution from Claude Code Bash (DEC-V61-198 "Not validated" item still open).

## Full mesh arc 2026-05-12

| iter | intervention | cells | max_skew | skew faces | dominant patch | V-ref |
|---|---|---|---|---|---|---|
| v27 | baseline (May 10) | 3.42M | 7.999 | 1119 | APU_door 95% | — |
| v28 | F1: APU_door refinement (3,4)→(2,3) | 2.60M | 7.999 | 570 | APU_door 90% | V75 |
| v29 | F2: APU_door drop from sHM dict | 2.42M | 7.997 | 149 | apu_geom_APU_door 62% | V75 (default-patch trap) |
| v30 | F2.1: APU_door body removed from STL | 2.42M | **7.624** | 56 | Outer_Surf 57% | V75 (wall broken) |
| v31 | F3a: Outer_Surf refinement (1,2)→(2,3) | 3.10M | 7.829 | 30 | firewall_behind 23% + body_4 23% | V76 (squeezing balloon) |
| **v32** | **F4a: 6 simple shells isotropic-remeshed** | **3.10M** | **6.875** | **20** | body_4 40% | V77 (bimodal remesh) |
| v33 | F5: bbox shell-hole punch — **REVERTED** | 3.97M | 7.966 | 69 | Outer_Surf 38% + Inner_Surf 29% | V78 (negative finding) |

## V73-V78 corpus (landed in `.planning/methodology/industrial_case_solver_findings.md` today)

- **V73**: `CheckMeshResult` schema drift (`max_non_orthogonality` → `_deg`); backward-compat `@property` aliases shipped to main repo + APU bay consumer updated. **Closed.**
- **V74**: `inputs/naming.yaml` SSOT forward-write trap — documented "v3 STL surgery 32→30 patches" past-tense but surgery never implemented; retreat to 32-patch actual state with 4 wall_adiabatic entries. **Closed.**
- **V75**: Three independent levers for skew-hotspot bodies: (a) refinement level (count down, wall pegged); (b) sHM dict drop (default-patch trap — sHM auto-creates `<geom>_<bodyname>`); (c) STL body deletion (only intervention that actually drops the body — 8.0 wall broken at v30). Empirically proven.
- **V76**: "Squeezing the balloon" — after V75 fixes the dominant-hotspot patch, per-patch refinement bumps move prominence between patches; cannot deliver PASS. Decision tree: dominant patch ≥80% → V75 surgery; 30-80% → mixed; <30% → V76 territory, switch class (remesh all OR relax controls).
- **V77**: Isotropic remesh is bimodal — works on simple shells (Inner_Surf, Outer_Surf, firewall_*, farfield, apu_intake: median aspect 26→1.94, near-equilateral); destroys complex feature bodies (body_4 64576→1 tri!; body_6/8 lose 97-99%). Per-body classification needed. `PyMeshLab meshing_isotropic_explicit_remeshing` with `collapseflag=True` is the lever; adaptive+no-collapse is the safer mode for complex bodies but expensive.
- **V78 (negative finding)**: bbox-based shell-hole "surgery" to clean CAD overlap BACKFIRES — sHM handles continuous CAD interpenetration better than jagged hole boundaries. v33 regression: max_skewness 6.87→7.97, skew 20→69. **The 33-pair intersection map was a red herring** — overlap was NOT the dominant skew source; complex body_4 (40% of v32 skew) was. Safety rule: STL edits must produce SMOOTH boundaries (Boolean on closed meshes), never approximate bbox deletion on open shells.

## Current state of artifacts

**APU bay project (`~/Desktop/apu-bay-ventilation/`, non-git):**

- `case/constant/triSurface/cleaned_combined.stl` — **v32 state** (290 MB, 6 isotropic-remeshed simple shells + verbatim complex bodies; APU_door dropped per V75 F2.1)
- `case/constant/triSurface/cleaned_combined.v32_pre_punch.stl` — same as current (backup before failed v33)
- `case/constant/triSurface/cleaned_combined.v31_pre_remesh.stl` — pre-V77 state (long-strip simple shells)
- `case/constant/triSurface/cleaned_combined.v29_pre_apu_door_drop.stl` — pre-V75 F2.1 (304 MB, contains APU_door)
- `case/constant/polyMesh/` — **v32 polyMesh** (3.10M cells; F4a-remeshed shells)
- 6 backup polyMesh dirs preserved (v24, v26.2, v27 l34, v27incomplete, v32 remesh-shells, v33 blockonly)
- `case/system/snappyHexMeshDict` — v31 state (Outer_Surf level 2,3; APU_door blocks dropped; v28 comments trail)
- `config/case.yaml` — SSOT updated with APU_door drop narrative + v31 Outer_Surf bump comment
- `inputs/naming.yaml` — 32-patch (V74 retreat) + APU_door flagged "wall_adiabatic placeholder; future = mass_flow_inlet after STL surgery"

**cfd-harness-unified main (this repo):**

- `.planning/methodology/industrial_case_solver_findings.md` — V73-V78 landed (this is the corpus SSOT)
- `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md` — frontmatter synced
- `ui/backend/services/mesh_quality/checkmesh_runner.py` — V73 backward-compat properties
- `ui/backend/services/meshing_gmsh/gmsh_runner.py` + `pipeline.py` + `routes/mesh_imported.py` — F-NEW-20 timeout (944756e)
- `.planning/methodology/claude_code_session_as_cfd_orchestrator.md` — validated-pattern doc (supersedes M6 Track C)

## Open paths for next session

**Highest strategic value: validate solver execution from Claude Code Bash (closes DEC-V61-198 final "Not validated" item)**

1. **F4b · relax meshQualityControls + run solver** (2-4 hours background)
   - Edit `case/system/sHM` (or meshQualityDict): `maxSkewness 4 → 8` (accept v32 quality)
   - Run `make 08_bcs` (write BCs from naming.yaml)
   - Run `make 09_solve` (Docker buoyantSimpleFoam 1500 steps)
   - Watch convergence + write V79 (solver vs mesh-quality trade-off) findings regardless of outcome
   - This is the LAST UNVALIDATED ITEM in DEC-V61-198

**Other paths (lower priority):**

2. **F4a-adaptive on body_4** (~1.5 hour) — try `adaptive=True + collapseflag=False + 3mm target` on body_4 specifically (only remaining 40% hotspot). Smoke-tested on body_8 (217k→752k tri, median 26→4.39 but max 574). May or may not break PASS threshold.
3. **Switch to cfd-harness M2.5 sediment hardening queue** (6 items: freecadcmd hardening, STEP→STL pipeline, multi-solid handling, etc.). Reference: `.planning/ROADMAP.md` M2.5 section.
4. **case_002b APU bay CHT extension** — solid-fluid conjugate heat transfer on same geometry. `case_002b_apu_bay_cht.md` exists.
5. **case_003 follow-up** — F-NEW-25 multi-instance bridge mis-stitch still blocking case_003 e2e per its own RESUME. Independent arc from case_002a.

## Substrate notes

**Why max_skewness > 4 PASS threshold may be acceptable for production:**

- OpenFOAM's `meshQualityControls.maxSkewness` default is 4 (strict); industrial practice often allows 6-8 with appropriate numerical schemes
- buoyantSimpleFoam with limited grad + deferred correction handles skewness 5-7 routinely
- v32's max_skewness 6.87 is below the practical 8.0 sHM rejection wall; the 20 bad faces are isolated (not connected clusters)
- The right next step is **try the solver and see**, not push the mesh further (V76's "squeezing the balloon" diagnostic)

**Why NOT to pursue F4a-adaptive on body_4 next (recommendation):**

- body_4 has 64k tri in 0.46×0.86×0.75m bbox — feature scale ~7mm
- Adaptive remesh at 3mm target would balloon to ~200-400k tri (5x growth)
- Even if max_skewness drops below 4, V76 says next patch (Frame_1 or beam_*) becomes new hotspot
- ROI is lower than F4b solver attempt

## Plain-Chinese tl;dr (for cold reopen)

- 今天 APU bay case_002a 跑完了完整 7 轮 mesh 调试弧。结论：**v32 是最佳状态**（max_skewness 6.87，比 v27 的 7.999 改善 14%；坏面数 1119→20 少 98%）。再往下打都是边际收益。
- **6 个 V 工件 V73-V78 落库**，是工业 CFD 网格调试方法学的完整经验。V78 是反直觉的负面发现：**不该乱动 STL 就别动**——sHM 处理 CAD 自然重叠比处理我们手工凿的洞口更稳。
- **下一个最有价值的事**：放松 sHM 质量阈值（maxSkewness 4→8）+ 跑 09_solver，把 DEC-V61-198 里"Not validated · solver execution from Claude Code Bash"那条最后一项给关掉。这是"Claude Code 跑完整工业 CFD"战略主张的最后一块拼图。
- **不推荐**：继续在 body_4 上做 adaptive remesh——V76 已经证明会"挤气球"，问题会跑到下一个 patch。

## References

- `.planning/methodology/industrial_case_solver_findings.md` — V73-V78 + cross-cutting patterns
- `.planning/decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md` — parent DEC
- `.planning/methodology/claude_code_session_as_cfd_orchestrator.md` — validated pattern (this case_002a arc is its proof)
- `~/Desktop/apu-bay-ventilation/` — non-git project root
- Today's commit range: `175e928` (V73+V74 land) → `e25d0de` (V78 negative finding land); ~20 commits total on main
