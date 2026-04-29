# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 1

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED solve-stream preflight/multi-run correctness is unsafe, and /bc/render is missing mesh-render input hardening`
**Tokens**: 186,130
**Account**: ksnbdajdjddkdd@gmail.com (plus, 71%)
**Commits reviewed**: `0c849c648b1c..fa5d98f` (5 commits in this arc, 17 in cadence range)

---

## Findings

### 1. HIGH — solve-stream preflight is inside generator, returns 200 then breaks
**File**: `ui/backend/routes/case_solve.py:149` + `ui/backend/services/case_solve/solver_streamer.py:170`

`stream_icofoam()` is a generator, so the failure-mapping code at lines 170-243 only executes when `StreamingResponse` begins iterating. Container down / Docker SDK broken / staging failure produces a started SSE response and then an iterator exception or broken stream, not the structured HTTP rejection the route comment promises.

**Verbatim fix**: Move lines 170-243 of `stream_icofoam()` into a non-generator `_prepare_stream_icofoam(...)` helper, call that helper in the route before constructing `StreamingResponse`, and only return the streaming generator after preflight succeeds.

### 2. HIGH — abort/restart race: no run-generation guard, shared container_work_dir
**File**: `ui/frontend/src/pages/workbench/step_panel_shell/SolveStreamContext.tsx:148` + `ui/backend/services/case_solve/solver_streamer.py:200`

Frontend "abort" only aborts the fetch reader; it does not stop the solver. Backend always uses the same `container_work_dir` derived from `case_host_dir.name`. Failure mode: navigate-away/remount can leave run A alive, run B starts in same directory, both race on `log.icoFoam` + time dirs + pulled-back artifacts. Frontend has no run-generation guard, so stale `done`/`error` from older invocation can mutate state after a newer `start()`.

**Verbatim fix**: Introduce a per-case solve lock or server-issued `run_id`; reject concurrent `solve-stream` with `409 solve_already_running`, use `container_work_dir = f'{CONTAINER_WORK_BASE}/{case_host_dir.name}-{run_id}'`, and gate all frontend state writes on `if (runIdRef.current !== localRunId) return`.

### 3. MED — /bc/render missing /mesh/render symlink-containment hardening
**File**: `ui/backend/services/render/bc_glb.py:141` vs `ui/backend/services/render/mesh_wireframe.py:86`

`points`, `faces`, and `boundary` are opened directly via `is_file()/read_text()/parse_*`, so a symlink under `constant/polyMesh/` can escape the case dir and be read. The route's final `cache_path.resolve(...).relative_to(...)` check only protects the OUTPUT file, not the inputs.

**Verbatim fix**: Add a `_bc_source_files(polymesh_dir, case_dir) -> (points, faces, boundary)` helper identical in shape to `mesh_wireframe._polymesh_source_files`, `resolve(strict=True)` all three inputs, require `relative_to(case_root)`, pass resolved paths into `parse_points`, `parse_faces`, `_read_boundary_patches`.

### 4. MED — malformed boundary ranges silently truncated, returns partial 200 GLB
**File**: `ui/backend/services/render/bc_glb.py:175`

`if face_idx >= len(faces): continue` turns a corrupt `startFace/nFaces` into a partial 200 GLB instead of `422 parse_error`. User sees an incomplete BC scene with no explicit error; tests still pass on the happy cube fixture.

**Verbatim fix**: Replace the `continue` with `raise BcRenderError(failing_check='parse_error', message=f'boundary patch {name!r} references face {face_idx} but faces has length {len(faces)}')`.

---

## Non-blocking observations

**glTF packing OK**: 4-byte chunk padding, index/position buffer-view offsets, accessor counts, `alphaMode: BLEND` on translucent materials all structurally correct.

**vtk.js cleanup OK**: `AbortController` cleanup in `Viewport.tsx:102` + `importer.delete()` ownership in `viewport_kernel.ts:78`.

## Coverage gaps Codex flagged

- 7 bc_glb tests cover only happy-path + missing polyMesh/boundary + 200/404/409
- Missing: unsafe case IDs, symlink escape, malformed boundary, 422 parse_error path, cache rebuild/atomic-write, byte-stable cache hits, glTF invariants
- **No backend tests for `/api/import/<id>/solve-stream`**
- **No frontend tests for `SolveStreamContext` / `LiveResidualChart`** — the new SSE surface is effectively untested

## Backward-compat note

`/bc-overlay.png` still served in `case_visualize.py:55` while frontend Step 3 now uses `/bc/render`. Looks intentional as legacy fallback but DEC wording around "replaces" is stale.

## Verbatim-exception eligibility (per RETRO-V61-001 5-condition test)

| Finding | LOC est | Files | Public API | Verbatim eligible |
|---|---|---|---|---|
| #1 preflight refactor | ~70 (move) | 1-2 | No | **NO** (>20 LOC) |
| #2 run-id system | ~50-80 | 2-3 | YES (new 409) | **NO** (>20 LOC + new error class) |
| #3 symlink hardening | ~30 (helper) | 1 | No | borderline; per pattern from mesh_wireframe |
| #4 partial-GLB raise | 1-3 | 1 | No | **YES** |

Most fixes need a real implementation arc, not verbatim-exception path.
