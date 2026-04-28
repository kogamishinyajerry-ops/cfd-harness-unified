# Codex review · M-VIZ Tier-A bundle · Round 4 · 2026-04-28

**Scope reviewed**: M-VIZ Steps 3-6 + Round-1/2/3 fixes (`4811c27` · `8c72a65` · `12baa5e`)

**Reviewed against**: `origin/main`

## Verdict

**Round-3 R3 #1 + R3 #2 RESOLVED** + **1 NEW P2 finding**: dispose
order in viewport_kernel leaks DOM listeners across mount/unmount.

## Round-3 findings · status

| # | Finding | Round-4 status |
|---|---------|---------------|
| R3 #1 | Unused `afterEach` import broke typecheck | RESOLVED |
| R3 #2 | Trackball interactor style leaked per kernel mount | RESOLVED |

## New finding

### [P2] R4 #1 — Interactor DOM listeners leak across mount cycles

**Position**: `ui/frontend/src/visualization/viewport_kernel.ts:103-109`

**Problem**: dispose() called `interactor.delete()` BEFORE `grw.delete()`.
But vtkGenericRenderWindow.delete is a macro chain that calls
`setContainer(undefined)` which in turn calls
`interactor.unbindEvents(model.container)` against the old container —
this is what actually removes the DOM keyup/pointer event listeners.

If the interactor is deleted first, its internal `container` ref is
cleared, so the subsequent `unbindEvents` becomes a no-op. DOM
listeners then accumulate on every mount/unmount cycle. For our
recruitment use case (stranger uploads N STLs in one session), N
mount/unmount cycles leak N × multiple listeners on `document` and
`window`.

Verified via `node_modules/.../GenericRenderWindow.js`:
```js
publicAPI.setContainer = el => {
  if (model.container) {
    model.interactor.unbindEvents(model.container);  // listener cleanup
  }
  ...
};
publicAPI.delete = macro.chain(publicAPI.setContainer, ..., publicAPI.delete);
```

**Suggested fix**: tear down the GenericRenderWindow before deleting
the interactor.

**Resolution**: applied. Reordered dispose to: actor → mapper → reader
→ **grw → interactor** (grw moved before interactor). Comment in
dispose() documents the path-dependency. interactor.delete() remains
in the chain (but after grw.delete) to release any residual vtk
handles; by that point unbindEvents has already run.

## Verification

- Frontend typecheck: clean
- Frontend tests: 29/29 pass (no test changes; behavior preserved)
- spec_v2 §AC#8 budget: unchanged (no module additions)

## Round-5 plan

Run Round-5 Codex to confirm:
- Round-4 R4 #1 RESOLVED
- No new findings introduced

If Round-5 returns APPROVE / APPROVE_WITH_COMMENTS with no new
blockers, M-VIZ bundle is merge-ready.

## Rounds tracking

| Round | Findings | Resolution |
|-------|----------|-----------|
| 1     | 3 P2     | Fixed in `4811c27` |
| 2     | 1 P2 (new) + R1 RESOLVED | Fixed in `8c72a65` |
| 3     | 1 P1 + 1 P3 (new) + R2 RESOLVED | Fixed in `12baa5e` |
| 4     | 1 P2 (new) + R3 RESOLVED | Fixed in this commit |

## Counter

DEC-V61-094 counter remains at 59. Will only advance on the post-merge
implementation DEC after Codex APPROVE.
