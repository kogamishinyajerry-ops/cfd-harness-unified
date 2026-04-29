# Codex pre-merge review · DEC-V61-097 Phase-1A · Round 3

**Date**: 2026-04-29
**Verdict**: `Codex-verified: CHANGES_REQUIRED immediate disconnect after the first start SSE still bypasses the new finally and leaks _active_runs`
**Tokens**: 97,032
**Account**: mahbubaamyrss@gmail.com (plus, 96% pre-run)
**Commits reviewed**: round-2 closure commit `3ddc098`

---

## Findings

### HIGH — `start` yield was OUTSIDE the new outer try/finally
**File**: `ui/backend/services/case_solve/solver_streamer.py:401, 418, 519`

Round 2 wrapped the streaming loop in an outer try/finally — but the very first `yield _sse("start", ...)` happened at line 401, BEFORE the `try:` at line 418. If the iterator is closed while suspended on that first yield (immediate client disconnect, FastAPI cancellation right after the first SSE byte), the cleanup never arms. The run is already claimed in the route's `_prepare_stream_icofoam` call before `StreamingResponse` is even constructed, so an immediate-disconnect-after-start strands `_active_runs[case_id]` permanently.

My round-2 test was **wrong** for this case — it pulled two events (`next(gen)` twice) before closing, by which point execution was already inside the try. Round-3 Codex caught this gap.

**Fix applied (round-4 commit)**:
- Moved the `start` yield INSIDE the outer try/finally.
- Added a new test `test_generator_close_releases_run_id_after_first_yield` that consumes ONLY the start event then `gen.close()` — the exact path that was leaking.
- Renamed the existing test to `..._mid_loop` and kept it for complementary coverage.

---

## Codex's positive observations on round 3

> `bc_glb` looks closed: `_bc_source_files()` runs before cache freshness at `bc_glb.py:428`; `_build_bc_glb_bytes()` re-resolves at `bc_glb.py:192`; no other repo callsite besides `geometry_render.py:171`. The stale rename is fixed at `bc_glb.py:161`; no other stale `{boundary}` ref remains in the file.

So R3.1 (cache-hit symlink containment) and the LOW regression (boundary→boundary_path rename) are both confirmed closed. Only the SSE finally-coverage gap remains.

## Notes

Codex couldn't rerun pytest in its sandbox (`No usable temporary directory found`). I ran the suite locally — 65 backend tests pass with the round-4 fix.
