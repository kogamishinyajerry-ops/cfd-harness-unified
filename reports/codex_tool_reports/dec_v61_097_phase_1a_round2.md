# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 2

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED disconnects still leak the per-case solve lock, and /bc/render hardening still bypasses containment on cache hits`
**Tokens**: 203,597
**Account**: mahbubaamyrss@gmail.com (plus, 96% pre-run)
**Commits reviewed**: round-1 closure commit `d657bed` on top of `001f778..fa5d98f`

---

## Findings

### R2.1 HIGH — disconnects still leak `_active_runs`
**File**: `ui/backend/services/case_solve/solver_streamer.py:401, 411, 510`

The first SSE `yield` happens at line 401 BEFORE any cleanup guard. The main stream loop has only `except Exception` (line 411) — no finally. The `_release_run()` lives only in the late summary's finally (line 510). A `GeneratorExit` raised at the start yield, mid-loop, or anywhere before the summary block skips that finally. Result: client disconnect mid-stream sticks the next solve on `409 solve_already_running` indefinitely.

**Fix applied (round-3 commit)**: wrapped the entire generator body (after `yield _sse("start", ...)`) in an outer try/finally that always runs `_release_run` + best-effort container cleanup, regardless of how the generator exits.

### R3.1 MED — `/bc/render` hardening bypassed on cache hit
**File**: `ui/backend/services/render/bc_glb.py:411` vs `mesh_wireframe.py:230`

`build_bc_render_glb()` checked cache freshness on the unresolved `points/faces/boundary` paths BEFORE calling `_bc_source_files()`. The `_is_cache_fresh()` helper ran `Path.stat()` on those raw paths, following any symlinks. So a symlink at `constant/polyMesh/points` pointing outside the case dir was honored on the cache-hit path — defeating the very containment that `_bc_source_files()` enforces on cache miss. The `mesh_wireframe` flow at `mesh_wireframe.py:230` resolves first.

**Fix applied (round-3 commit)**: moved `_bc_source_files()` BEFORE `_is_cache_fresh()` in `build_bc_render_glb()`. Cache freshness now checks already-resolved paths, so a symlink-escape attempt is rejected on cache-hit too.

### Regression LOW — `boundary` / `boundary_path` rename left a stale reference
**File**: `ui/backend/services/render/bc_glb.py:158`

The round-1 R3 fix renamed the parameter to `boundary_path`, but the no-patches error message still referenced the undefined `boundary`. An empty / unparsable boundary file used to raise `NameError` instead of `BcRenderError`.

**Fix applied (round-3 commit)**: replaced `{boundary}` with `{boundary_path}`. Empty boundary file now surfaces as `BcRenderError(no_boundary)` cleanly.

---

## Codex's positive observations on round 2

> R1's main closure is otherwise correct: preflight has moved out of the generator and is mapped synchronously in [case_solve.py](.../case_solve.py:158). R4's malformed-range raise also reaches 422 correctly via [bc_glb.py](.../bc_glb.py:218) and [geometry_render.py](.../geometry_render.py:147).

So R1 (HIGH) and R4 (MED) closures from round-1 work hold up under round-2 scrutiny.

## Coverage Codex still flagged

- generator close/abort (now covered: `test_generator_close_releases_run_id`)
- `solve-stream` route mapping under failure
- frontend stale-state via `genRef`
- cache-hit containment (now covered: `test_cache_hit_path_also_resolves_symlinks`)
- empty-boundary regression (now covered: `test_empty_boundary_raises_bc_render_error_not_nameerror`)

Frontend `SolveStreamContext` rAF/genRef still has no test. That's a known gap from round 1.
