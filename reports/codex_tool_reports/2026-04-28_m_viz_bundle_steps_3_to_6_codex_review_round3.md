# Codex review · M-VIZ Tier-A bundle · Round 3 · 2026-04-28

**Scope reviewed**: M-VIZ Steps 3-6 + Round-1 fix (`4811c27`) + Round-2 fix (`8c72a65`)

**Reviewed against**: `origin/main`

**Codex command**: `codex exec review --base origin/main -m gpt-5.4 --title "..."`

## Verdict

**Round-2 R2 #1 RESOLVED** (Codex did not re-flag the parse-exception
wrap or reader dispose) + **2 NEW findings**: 1 P1 (BLOCKING) + 1 P3.

## Round-2 finding · status

| # | Finding | Round-3 status |
|---|---------|---------------|
| R2 #1 | vtk.js parse exceptions bypass parse-error contract | RESOLVED |

## New findings

### [P1] R3 #1 — Unused `afterEach` import breaks frontend CI

**Position**: `ui/frontend/src/visualization/__tests__/stl_loader.test.ts:4`

**Problem**: Round-2 fix renamed the `afterEach(() => ...)` block to
`beforeEach(() => ...)` but left `afterEach` in the named import.
`ui/frontend/tsconfig.json` enables `noUnusedLocals: true` and includes
test sources, so `npm run typecheck` and `npm run build` fail with
`TS6133: 'afterEach' is declared but its value is never read`. Vitest
runs green because vitest doesn't enforce tsconfig flags, but the
build pipeline does — the patch could not pass CI as committed.

I locally reproduced the typecheck failure (Codex was right) — earlier
"clean typecheck" output was likely served from incremental cache.

**Suggested fix**: drop `afterEach` from the import statement.

**Resolution**: applied. Import is now `import { describe, expect, it,
vi, beforeEach } from "vitest"`. Typecheck + build both clean post-fix.

### [P3] R3 #2 — Trackball interactor style leaked on every kernel mount

**Position**: `ui/frontend/src/visualization/viewport_kernel.ts:47-48`

**Problem**: `vtkGenericRenderWindow.newInstance` already installs a
`vtkInteractorStyleTrackballCamera` on its interactor (verified via
`grep` of `node_modules/@kitware/vtk.js/Rendering/Misc/GenericRenderWindow.js`:
`model.interactor.setInteractorStyle(vtkInteractorStyleTrackballCamera.newInstance())`).
The kernel's `attachTrackballInteractor`-equivalent code created a
second trackball style and called `interactor.setInteractorStyle(...)`
on it, which:

1. Replaced the original default style without freeing it (silent leak)
2. The replacement style was never `.delete()`'d on dispose

Net effect: every Viewport mount/unmount cycle leaked two vtk objects.
Across the recruitment use case (stranger uploads N STLs in one
session) this leaks 2N objects. Not a P0 today but compounds with M-VIZ
follow-ups (mesh wireframe, contour rendering) all spawning kernels.

**Suggested fix**: rely on the GenericRenderWindow default trackball
style instead of installing a second one.

**Resolution**: applied. Removed `vtkInteractorStyleTrackballCamera`
import + the explicit `setInteractorStyle` call. Comment in
`createKernel` documents the path-dependency on
GenericRenderWindow's internal default — if vtk.js ever changes that
default in a future version, this kernel needs an explicit install.
Behavior preserved for users (trackball/orbit camera still active).

## Verification

- Frontend typecheck: clean (P1 fix)
- Frontend tests: 29/29 pass (no test changes; behavior preserved)
- Frontend production build: clean
  - main chunk: 1,060 KB / 349 KB gzipped (unchanged from round-2)
  - Viewport chunk: 687 KB / 190 KB gzipped (unchanged)
- spec_v2 §AC#8 tiered budget: all clear

## Round-4 plan

Run Round-4 Codex to confirm:
- Round-3 R3 #1 (unused import) RESOLVED
- Round-3 R3 #2 (trackball leak) RESOLVED
- No new findings introduced

## Rounds tracking

| Round | Findings | Resolution |
|-------|----------|-----------|
| 1     | 3 P2     | Fixed in `4811c27` |
| 2     | 1 P2 (new) + R1 RESOLVED | Fixed in `8c72a65` |
| 3     | 1 P1 + 1 P3 (new) + R2 RESOLVED | Fixed in this commit |

## Counter

DEC-V61-094 counter remains at 59. Will only advance on the post-merge
implementation DEC after Codex APPROVE.
