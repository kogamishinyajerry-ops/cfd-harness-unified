# Phase 7a: Field post-processing capture — Context

**Gathered:** 2026-04-21
**Status:** Ready for research
**Source:** In-session decisions during Phase 7 ROADMAP authoring (commit e4dd1d9) + user verdict "按照你的建议来" on depth-first LDC MVP plan

<domain>
## Phase Boundary

**In-scope (this phase delivers):**
- Every `audit_real_run` invocation of `scripts/phase5_audit_run.py` persists OpenFOAM field artifacts (VTK volumes) + sampled CSV profiles + residual.log to a stable on-disk layout under `reports/phase5_fields/{case}/{timestamp}/`
- `src/foam_agent_adapter.py` emits `controlDict.functions{}` block with `sample`, `yPlus`, `residuals` OpenFOAM function objects (yPlus skipped for laminar cases)
- Backend surfaces the captured artifacts via `GET /api/runs/{run_id}/field-artifacts` with asset URLs + SHA256 per file
- New Pydantic model `ui/backend/schemas/validation.py::FieldArtifact` + `FieldArtifactsResponse`
- pytest fixture asserts LDC `audit_real_run` produces VTK + CSV + residual.log on disk after run
- Depth-first validation on LDC only (Ghia 1982 case — already PASS for 11/17 points per DEC-V61-030)

**Out-of-scope (defer to sibling phases):**
- Rendering VTK → PNG / Plotly (Phase 7b)
- HTML/PDF comparison report template (Phase 7c)
- Richardson GCI calculation (Phase 7d)
- Embed artifacts into signed zip (Phase 7e)
- Frontend live-fetch renders (Phase 7f)
- Other 9 cases (Phase 7c Sprint-2 fan-out handles them)

</domain>

<decisions>
## Implementation Decisions (LOCKED)

### Solver-side (adapter / controlDict)
- **Function objects emitted:** `sample` (u/p along centerline), `yPlus` (turbulent cases only), `residuals` (log of initial residual per field per iteration). Use OpenFOAM v10 `libsampling.so`, `libfieldFunctionObjects.so`.
- **Sample format:** `raw` CSV — one column per sampled field per y-point, one row per iteration write step. Final iteration row is what the comparator currently uses.
- **Write cadence:** `writeInterval 500` for `sample`/`residuals` (runTime), `writeInterval` matches solver `writeInterval` for VTK.
- **yPlus skip logic:** emit only when `turbulence_model != "laminar"` in task_spec — LDC is laminar so 7a on LDC will NOT emit yPlus. Keep code path ready for 7c Sprint-2 turbulent cases.

### Post-run capture (scripts/phase5_audit_run.py)
- **VTK export:** Run `foamToVTK -latestTime -noZero -allPatches` inside Docker container after solver completes, **before** case dir teardown in `finally` block.
- **Stage path:** Docker container `/case/VTK/` → host `reports/phase5_fields/{case_id}/{timestamp_utc}/` via `docker cp` (existing pattern; see `FoamAgentExecutor` for precedent).
- **Files captured (MVP for LDC):** `{case}_{iter}.vtk` (volume), `postProcessing/sample/{iter}/U_p_centerline.csv`, `log.simpleFoam` → parsed to `residuals.csv` (3 columns: iter, Ux, p).
- **Timestamp format:** `YYYYMMDDTHHMMSSZ` matching existing `reports/phase5_audit/{timestamp}_{case}_raw.json` convention.
- **Size limit:** ~5 MB per VTK for 129×129×1 LDC; no compression in MVP.

### Backend surface
- **Route:** `GET /api/runs/{run_id}/field-artifacts` — `run_id` = `{case}__{run_label}` same format as existing SSE streamer.
- **Response schema:** `FieldArtifactsResponse { run_id: str, case_id: str, timestamp: str, artifacts: List[FieldArtifact] }` where `FieldArtifact { kind: Literal["vtk","csv","residual_log"], filename: str, url: str, sha256: str, size_bytes: int }`.
- **URL scheme:** `/api/runs/{run_id}/field-artifacts/{filename}` served via FastAPI `StaticFiles` mount pointing at `reports/phase5_fields/`.
- **SHA256 computation:** eager on first request, cached in-memory by `(filename, mtime)` tuple to avoid re-hashing on every poll.
- **Auth:** follow existing audit-package pattern — HMAC header optional in MVP, route is read-only, same signing protocol added in Phase 7e.

### Test coverage (MVP for LDC)
- **Fixture:** `ui/backend/tests/fixtures/runs/lid_driven_cavity/field_artifacts_manifest.yaml` — enumerates expected files.
- **Assertions:**
  1. After `phase5_audit_run.py lid_driven_cavity`, directory `reports/phase5_fields/lid_driven_cavity/{latest}/` exists.
  2. Contains at least 1 `.vtk`, `sample/` with CSV, and `residuals.csv`.
  3. `GET /api/runs/lid_driven_cavity__audit_real_run/field-artifacts` returns ≥3 artifacts with non-empty SHA256.
- **Do not** assert exact VTK byte-equality — OpenFOAM output has non-reproducible metadata (hostname, wall-clock). Assert file presence + non-zero size + SHA256 is a valid hex string.
- **Do not regress 79/79 existing pytest.**

### 三禁区 / Codex protocol
- `src/foam_agent_adapter.py` edits: ~20-30 LOC expected (functions{} block + yPlus conditional). **>5 LOC → Codex mandatory** per RETRO-V61-001.
- `scripts/phase5_audit_run.py` edits: new file (not 三禁区, autonomous OK).
- `ui/backend/` edits: new route + schema + service — not 三禁区, autonomous OK unless cross-file count ≥3 (this phase: 3 files → borderline, prefer Codex post-merge).
- **Self-estimated pass rate: 75%** — risks: FoamAgentExecutor teardown race (case dir auto-deletes in `finally` before we can docker cp), yPlus emission on laminar regression.

### Claude's Discretion
- Exact Python function names and module organization within `scripts/phase5_audit_run.py` (can refactor into sub-module if it grows).
- pytest fixture file path (under existing `fixtures/runs/lid_driven_cavity/` tree).
- Error handling when `foamToVTK` fails — log warning, don't fail the whole run (comparator scalar extraction must still succeed).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Upstream decisions
- `.planning/ROADMAP.md` — Phase 7 + 7a sections (commit e4dd1d9)
- `.planning/decisions/2026-04-21_phase5b_ldc_simplefoam_migration.md` — DEC-V61-029, Phase 5a/5b pipeline context
- `.planning/decisions/2026-04-21_phase5b_q5_ldc_gold_closure.md` — DEC-V61-030, Ghia 1982 gold state
- `.planning/retrospectives/2026-04-21_v61_counter16_retrospective.md` — RETRO-V61-001, Codex trigger rules

### Touched code paths
- `src/foam_agent_adapter.py` — specifically `_generate_lid_driven_cavity` (lines ~640-960) where controlDict is emitted. New `functions{}` block adjacent to existing `applicationClass`.
- `scripts/phase5_audit_run.py` — entry point `main()` and per-case run loop. Post-run hook for VTK export goes before the existing `_write_measurement_yaml` call.
- `ui/backend/main.py` — new router registration for `/api/runs/{run_id}/field-artifacts`
- `ui/backend/routes/run_monitor.py` — existing pattern for `/api/runs/{run_id}/...` routes, copy its URL structure
- `ui/backend/schemas/validation.py` — existing home for `FieldArtifact` sibling

### OpenFOAM function object reference
- OpenFOAM v10 `$FOAM_SRC/sampling/sampledSet/uniform/uniform.C` — uniform line sampling
- OpenFOAM v10 `$FOAM_SRC/functionObjects/field/residuals/residuals.C` — residual writer
- OpenFOAM v10 `$FOAM_UTILITIES/postProcessing/dataConversion/foamToVTK/` — VTK exporter

### Project skill rules
- `/Users/Zhuanz/CLAUDE.md` — Codex-per-risky-PR baseline, src/ >5 LOC trigger, 三禁区 definitions
- No `.claude/skills/` or `.agents/skills/` directory in this project

</canonical_refs>

<specifics>
## Specific Ideas

### FoamAgentExecutor teardown race (known risk)
Existing `FoamAgentExecutor` in `src/foam_agent_adapter.py` auto-deletes case dirs in a `finally:` block. Our VTK export must happen BEFORE that finally fires. Two options:
- **A.** Hook into the executor's success callback before finally (cleanest)
- **B.** Copy VTK to host via `docker cp` inside the run loop, not after — skipping the need to survive teardown

**Locked: option B** — cheaper, doesn't modify executor semantics.

### LDC-specific sample coordinates
Use the existing `sampleDict` that's already emitted for comparator (x=0.5 centerline, 17 points). Just add `setFormat raw` and `writeControl writeTime` to capture during-iteration samples too, not only final.

### Residuals parsing
OpenFOAM `log.simpleFoam` prints per-iteration residuals as:
```
Time = 1
...
smoothSolver:  Solving for Ux, Initial residual = 0.123, Final residual = ...
smoothSolver:  Solving for Uy, Initial residual = 0.045, ...
GAMG:  Solving for p, Initial residual = 0.67, ...
```
Parse the `log.simpleFoam` file with regex `Initial residual = ([\d.e+-]+)` per field. Emit `residuals.csv` with columns: iter, Ux_initial, Uy_initial, p_initial.

### Deterministic ordering of artifacts
Response should sort artifacts by `(kind, filename)` so frontend consumers see stable order. VTK first (volume data), CSV second (profiles), residual_log third.

</specifics>

<deferred>
## Deferred Ideas

- **Phase 7b:** VTK → PNG rendering via matplotlib + PyVista headless
- **Phase 7c:** Jinja2 HTML comparison report template with 8 sections
- **Phase 7d:** Richardson GCI from mesh_20/40/80/160 fixtures
- **Phase 7e:** Embed PDF/PNG/CSV into HMAC-signed audit-package zip; manifest schema L3→L4
- **Phase 7f:** Frontend LearnCaseDetailPage fetches field artifacts live
- **y+ function object for turbulent cases:** Emit code stubbed out but not exercised in Phase 7a (LDC is laminar). First exercise in Phase 7c Sprint-2 when iterating turbulent cases.
- **VTK compression / remote storage:** Stay on local filesystem for MVP; revisit when artifact count exceeds 1 GB total.
- **Streaming residuals to SSE:** Run Monitor already has SSE; Phase 7a writes to disk for post-run analysis, not live. Cross-wiring deferred to a later polish pass.

</deferred>

---

*Phase: 07a-field-capture*
*Context gathered: 2026-04-21 via in-session decisions*
