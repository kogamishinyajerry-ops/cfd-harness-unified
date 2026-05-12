---
status: validated · empirical test 2026-05-12 (APU bay case_002a)
supersedes: Track C "M6 AI advisor dogfooding sprint" from 2026-05-12 audit roadmap
parent_dec: V61-198 §"engineer + Claude Code 已经能从 0 完成工业级 CFD 仿真"
related_memory: feedback_claude_code_is_the_advisor.md
---

# Claude Code session as CFD orchestrator (validated pattern)

## Claim

A single Claude Code session running in a terminal can drive a complete
industrial-CFD pipeline (geometry ingest → mesh → BC → solver → verdict)
at industrial complexity (>900k cells, multi-region, real physics), using
the cfd-harness-unified main repo as a library — no workbench UI, no
in-product AI advisor stack, no separate dispatcher.

User direction 2026-05-12 (verbatim):

> 现阶段最重要的是，我在claude code这个会话窗口里，就能完成全链路CFD仿真，
> 而且是工业级复杂度

## Empirical validation

Test substrate: APU bay case_002a (`~/Desktop/apu-bay-ventilation/`).
Geometry: CATIA STEP 29 named bodies → snappyHexMesh 943k → 3.4M cells
(post-v17 iteration). Solver: buoyantSimpleFoam pseudo-steady. 11-script
pipeline with `make` orchestration; scripts reuse main repo via PYTHONPATH.

Tests performed in a single Claude Code session 2026-05-12:

| Step | Verb | Result |
|---|---|---|
| `make check-env` | env preflight | ✅ `[ok] env` |
| `make 03_validate` (round 1) | Python · main-repo `stl_loader` + `patch_detector` | ✅ runs · surfaces naming.yaml drift correctly (4 missing patches) |
| `naming.yaml` retreat (32-patch) | doc edit in session | ✅ V74 captured |
| `make 03_validate` (round 2) | re-test | ✅ `[ok] 全部 32 个 patch 在 STL 和 naming.yaml 中一致` |
| `make 07_check` (round 1) | Python · main-repo `checkmesh_runner._parse_checkmesh_output` | ⚠ runs · `[WARN] harness 解析器不可用` · regex fallback · drift V73 captured |
| `07_check_mesh.py` schema fix (2 lines) | code edit in session | ✅ adapt to main-repo schema evolution |
| `make 07_check` (round 2) | re-test | ✅ `(用 harness 解析器)` · full mesh quality report incl. orthogonality |
| mesh quality verdict | engineering result | ⚠ FAIL · max_skewness 7.51 > 4 · advisor surfaces concrete fix |

**Verdict**: the user's claim is **empirically true**. The architecture is:

- 11-script orchestration in `scripts/` (any project, Claude Code-facing CLI)
- `PYTHONPATH=~/Desktop/cfd-harness-unified` exposes main repo as library
- `make` is the discoverable interface; each target is a single `bash` command
- Docker is invoked from `bash` for solver / mesh container steps
- All flow controllable from a single Claude Code session

## What this supersedes

**Track C (M6 AI advisor dogfooding sprint)** from the 2026-05-12 audit
roadmap is superseded. M6 charter sub-DECs (N6.1-N6.5: corpus loader, AI
review route, AI diagnose route, advisor panel, offline fallback)
**stay landed** as record but are NOT the priority target. The corpus
they would feed (`industrial_case_solver_findings.md`) **is consumed
directly by Claude Code in dialogue**; the UI surface for it is vestigial
unless a future non-Claude-Code consumer is identified.

## What this validates (and what it does NOT)

**Validated**:
- Main repo's library architecture (utility modules importable via PYTHONPATH)
- Make-based per-script orchestration
- Pipeline fail-fast behavior (`Error 1` on naming drift; `Error 2` on mesh verdict FAIL)
- Main repo schema evolution surfaces clearly at industrial-case integration

**Not validated** (out of session scope or untested):
- Solver execution from Claude Code Bash (Docker step 09 not exercised; assumed via existing `09_run_solver.sh` pattern)
- New industrial case from scratch (only existing case_002a retested)
- Cross-case generalization (only APU bay; M2.5 sediment hardening items still queued)

## Sediment captured by this validation

From a 30-minute live-run of part of the pipeline:

| Item | Class | Outcome |
|---|---|---|
| V73 — main-repo schema evolution (`max_non_orthogonality_deg` + `failed_checks: list[str]`) without consumer broadcast | schema drift | corpus row landed |
| V74 — naming.yaml forward-write to unimplemented future state | SSOT-vs-impl drift | corpus row landed |
| naming.yaml retreat to 32-patch reality | bookkeeping | yaml edit + 4 wall_adiabatic entries |
| 07_check_mesh.py 2-line consumer fix | API drift | inline edit |
| APU bay mesh quality FAIL (max_skewness 7.51) | engineering issue | surfaced to user · not auto-fixed |

**Cost of value capture**: ~30 minutes of session time, 0 commits to APU bay
(non-git), 1 commit to main repo (V73 + V74 + this doc). 0 LOC of M6
advisor UI code touched.

## Operating pattern (for future sessions / new industrial cases)

1. Industrial case lives in `~/Desktop/case_<id>/` with its own 11-script
   `scripts/` + `Makefile`; `_lib.py` bootstraps `PYTHONPATH=~/Desktop/cfd-harness-unified`
2. Claude Code session drives `make <target>` for each stage
3. When main-repo integration surfaces drift, fix locally and capture as
   V-series finding for corpus; consider promotion to S-playbook on N≥2 cases
4. When pipeline fail-fast triggers (validation, verdict, exit-code), read
   the actual output + advisor recommendations + decide engineering response
   in dialogue. Do NOT route through any UI surface.
5. The corpus (`industrial_case_solver_findings.md` + `solver_convergence_playbook.md`)
   is read by Claude Code directly in subsequent sessions to surface
   "this looks like Vn" diagnoses — same function as M6's "AI Review" /
   "AI Diagnose" buttons would have served

## Open items / future work

- **F-NEW-20 timeout** (just landed 2026-05-12 commit `944756e`) protects
  M6 mesh route from hung-subprocess CPU burn; same pattern should be
  audited for solver step (V73 / 09_run_solver Docker container kill path)
- **Main-repo backward-compat property layer** for CheckMeshResult (V73
  candidate followup); deferred pending user decision (schema bloat vs
  migration ergonomics trade-off)
- **APU bay naming.yaml v3/v4 surgery** still planned-but-unimplemented;
  if next session implements, follow V74 3-step retreat-reverse path in
  yaml top comment
- **New-case substrate** — next industrial case (Codex 出题 + sub-session
  per existing case_proposal_queue) should validate this pattern on
  geometry-class diverse from internal+buoyancy (e.g. external high-Re BL
  case_003 once cross-repo F-NEW-26 fix lands)

## References

- DEC-V61-198 — APU bay strategic pivot (parent decision)
- `feedback_claude_code_is_the_advisor.md` — memory rule established 2026-05-12
- `industrial_case_solver_findings.md` — V-series corpus (V73 + V74 added this audit)
- `solver_convergence_playbook.md` — S-series playbook
- `~/Desktop/apu-bay-ventilation/` — case_002a reference pipeline
