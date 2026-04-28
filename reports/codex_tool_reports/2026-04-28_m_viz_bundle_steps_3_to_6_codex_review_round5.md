# Codex review · M-VIZ Tier-A bundle · Round 5 · 2026-04-28

**Scope reviewed**: M-VIZ Steps 3-6 + Round-1/2/3/4 fixes

**Reviewed against**: `origin/main`

## Verdict

**Round-4 R4 #1 RESOLVED** + **1 NEW P3 finding**: incorrect pan-modifier
in Viewport help text.

## Round-4 finding · status

| # | Finding | Round-5 status |
|---|---------|---------------|
| R4 #1 | Interactor DOM listeners leak across mount cycles | RESOLVED |

## New finding

### [P3] R5 #1 — Wrong modifier key in pan hint

**Position**: `ui/frontend/src/visualization/Viewport.tsx:121`

**Problem**: Help text said `drag to rotate · wheel to zoom · ⌥drag to pan`,
but vtk's default `vtkInteractorStyleTrackballCamera` (installed by
GenericRenderWindow) maps `Alt/Option + drag` to **spin**, not pan.
Pan is `Shift + drag`. Users following the on-screen hint would get
the opposite behavior when trying to reposition the mesh.

**Suggested fix**: rewrite the hint to match the actual key map.

**Resolution**: applied. Hint now reads `drag to rotate · wheel to
zoom · shift+drag to pan · ⌥drag to spin`. Both modifiers documented
explicitly so users don't have to guess which is which.

## Verification

- Frontend typecheck: clean
- Frontend tests: 29/29 pass (no test changes; copy is presentational)
- No bundle delta

## Round-6 plan

Run Round-6 Codex to confirm:
- Round-5 R5 #1 RESOLVED
- No new findings introduced

Codex quota note: Pro account is at 19% headroom (under cx-auto's 20%
threshold). Round-6 may need a temporary `cx-auto 10` override or wait
for the quota window to roll. Plus accounts in pool are all at 100%
secondary-window usage (locked out).

## Rounds tracking

| Round | Findings | Resolution |
|-------|----------|-----------|
| 1     | 3 P2     | Fixed in `4811c27` |
| 2     | 1 P2 (new) + R1 RESOLVED | Fixed in `8c72a65` |
| 3     | 1 P1 + 1 P3 (new) + R2 RESOLVED | Fixed in `12baa5e` |
| 4     | 1 P2 (new) + R3 RESOLVED | Fixed in `b5e560b` |
| 5     | 1 P3 (new) + R4 RESOLVED | Fixed in this commit |

Pattern: each round resolves the prior finding + surfaces one new
finding. Findings are getting strictly less severe (P2 → P2 → P1+P3 →
P2 → P3) as the bundle stabilizes. Round 6 expectation: APPROVE or
zero findings.

## Counter

DEC-V61-094 counter remains at 59.
