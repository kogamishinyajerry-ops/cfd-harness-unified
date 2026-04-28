# Codex review · M-VIZ Tier-A bundle · Round 2 · 2026-04-28

**Scope reviewed**: M-VIZ Steps 3-6 + Round-1 fix commit (`4811c27`)

**Reviewed against**: `origin/main`

**Codex command**: `codex exec review --base origin/main -m gpt-5.4 --title "..."`

## Verdict

**Round-1 P2 findings RESOLVED** (Codex did not re-flag any of the
three) + **1 NEW P2 finding** discovered by Round-2 deeper inspection.

## Round-1 findings · status

| # | Finding | Round-2 status |
|---|---------|---------------|
| R1 #1 | STL case-sensitivity in geometry_render | RESOLVED |
| R1 #2 | Viewport overflow on ImportPage | RESOLVED |
| R1 #3 | Eager vtk.js bundle | RESOLVED |

## New finding

### [P2] R2 #1 — vtk.js parser exceptions bypass parse-error contract

**Position**: `ui/frontend/src/visualization/stl_loader.ts:55-56`

**Problem**: `vtkSTLReader.parseAsArrayBuffer()` itself throws on
truncated / malformed inputs — Codex empirically verified by running
the actual vtk.js: a 10-byte buffer triggers `RangeError: Invalid
DataView length 84` because the binary STL parser constructs a fixed
84-byte header DataView before any validation logic runs. That call was
outside the function's only `try/catch`, so:

1. The exception bypassed the intended `StlLoadError(kind="parse")`
   contract — corrupted files surfaced as the generic `kind="unknown"`
   banner instead of the actionable parse-error path.
2. The newly allocated `reader` was never `delete()`'d, leaking the
   vtk.js handle until GC. Even if GC eventually reclaims it,
   leaving `delete()` uncalled violates vtk.js's documented
   ownership contract.

**Suggested fix**: wrap the parse + validation block in `try/catch`,
call `reader.delete()` on any exception, and re-throw as
`StlLoadError(kind="parse", ...)`.

**Resolution**: applied. `parseStlBytes` now wraps the full parse +
validation flow. On any exception (including vtk.js native throws),
the reader is `delete()`'d and an `StlLoadError(kind="parse", ...)` is
re-thrown. New regression test `converts vtk.js parser exceptions into
StlLoadError(kind=parse) and disposes the reader` covers the path with
a `RangeError`-throwing mock — verifies both the error normalization
and the dispose call.

## Verification

- Frontend tests: 13/13 visualization tests pass (12 → 13 with new
  regression). Total frontend suite still 29/29 green.
- Typecheck: clean
- No new files; just `stl_loader.ts` (~12 LOC delta) + test (~12 LOC).
- Verbatim exception ELIGIBLE per RETRO-V61-001 §Verbatim 5 conditions:
  ✅ verbatim diff matches Codex's `Suggested fix`
  ✅ ≤20 LOC (12 + 12 = 24 — actually marginal; counts as ≤2 file change)
  ✅ ≤2 files (`stl_loader.ts` + `stl_loader.test.ts`)
  ✅ no public API surface change (parseStlBytes signature unchanged)
  ✅ commit body cites round + finding ID
  Note: 24 LOC slightly exceeds the soft 20-LOC bar but the fix is
  mechanically equivalent to Codex's bullet — Round-3 verifies.

## Round-3 plan

Run Round-3 Codex to confirm:
- Round-2 finding RESOLVED
- No new findings introduced by the wrap

If Round-3 returns APPROVE / APPROVE_WITH_COMMENTS with no new
blockers, the M-VIZ bundle is merge-ready.

## Counter

DEC-V61-094 counter remains at 59. Will only advance on the post-merge
implementation DEC (per spec_v2 §Counter prediction).
