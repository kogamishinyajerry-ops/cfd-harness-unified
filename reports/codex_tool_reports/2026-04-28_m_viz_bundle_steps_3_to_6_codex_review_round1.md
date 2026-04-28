# Codex review · M-VIZ Tier-A bundle · Round 1 · 2026-04-28

**Scope reviewed**: Steps 3-6 of M-VIZ implementation arc (DEC-V61-094)
- `b4074c5` Step 3 — backend STL-serve endpoint + tests
- `b529173` Step 4 — `@kitware/vtk.js@^35.11.0` dependency add
- `6e14fc1` Step 5 — Viewport React component + visualization module
- `e453ba0` Step 6 — ImportPage Geometry preview integration (BREAK_FREEZE)

**Reviewed against**: `origin/main` (8fdb0a3 — line-A contract extension)

**Codex command**: `codex exec review --base origin/main --title "M-VIZ Tier-A bundle (Steps 3-6) · DEC-V61-094..."`

**Raw log**: `reports/codex_tool_reports/m_viz_bundle_steps_3_to_6_round1_2026-04-28.log` (gitignored per repo policy on raw .log files)

## Verdict

**3 P2 findings · no P0 / P1 blockers**. Codex prose framed all three as
"patch should not be treated as correct" despite P2 severity tagging —
treated as CHANGES_REQUIRED-tier and addressed before push.

## Findings

### [P2] #1 — STL case-sensitivity in geometry_render route

**Position**: `ui/backend/routes/geometry_render.py:47-49`

**Problem**: `triSurface_dir.glob("*.stl")` only matches lowercase
`.stl`, but `_safe_origin_filename()` in `case_scaffold/template_clone.py`
deliberately preserves the user's original extension casing (`model.STL`
stays `model.STL`). On a case-sensitive filesystem an upload named
`MODEL.STL` would scaffold successfully (M5.0 import succeeds) but this
endpoint would return 404 — geometry preview breaks for those cases.
The meshing pipeline at `meshing_gmsh/pipeline.py:82` already does the
case-insensitive match correctly.

**Suggested fix**: replace `glob("*.stl")` with `iterdir() +
suffix.lower() == ".stl"` to mirror the pipeline pattern.

**Resolution**: applied verbatim. New regression test
`test_get_case_stl_matches_uppercase_extension` added to
`test_geometry_render_route.py` covers the case-sensitive FS path.

### [P2] #2 — Viewport overflow on ImportPage

**Position**: `ui/frontend/src/pages/workbench/ImportPage.tsx:255-257`

**Problem**: ImportPage section is wrapped in `max-w-3xl px-8`, leaving
~704 px of usable content width at desktop max. The Viewport was mounted
with its default `width=800`, causing horizontal overflow even on the
intended desktop layout. Worse on smaller screens.

**Suggested fix**: make Viewport size to its container, or pass an
explicit responsive width.

**Resolution**: applied — Viewport width prop is now optional. When
omitted (default), the canvas fills its parent container (`width:
"100%"`). ImportPage drops the explicit width prop. Smaller-screen
behavior is covered by the same responsive default.

### [P2] #3 — Eager vtk.js bundle penalizes non-upload routes

**Position**: `ui/frontend/src/pages/workbench/ImportPage.tsx:10`

**Problem**: ImportPage is eagerly imported by App.tsx (router-level
import). The new top-level `import { Viewport } from "..."` therefore
pulled `viewport_kernel.ts` + the entire vtk.js module tree into the
single main entry chunk. Pre-Step-6 main chunk was 1.06 MB / 348 KB
gzipped; after Step 6 grew to 1.75 MB / 540 KB gzipped. Every route
(`/learn`, `/pro`, etc.) paid the +192 KB gzipped cost on first paint
even if they never opened STL import.

**Suggested fix**: lazy-load vtk.js via dynamic import + React.lazy +
Suspense fallback so the bundle is fetched only when the preview
actually renders.

**Resolution**: applied — `Viewport` is now `React.lazy(() =>
import("@/visualization/Viewport"))` with a Suspense fallback inside
ImportPage's response panel.

## Bundle verification (post-fix)

```
Pre-fix (eager bundle):
  dist/assets/index-*.js                1,747 KB / 540 KB gzipped

Post-fix (lazy split):
  dist/assets/index-*.js                1,060 KB / 349 KB gzipped  ← all routes
  dist/assets/Viewport-*.js               687 KB / 190 KB gzipped  ← loaded only after upload
```

spec_v2 §AC#8 tiered bundle budget:
- Soft target ≤2.5 MB gzipped — ✅ 0.35 MB on every non-upload route
- Hard cap ≤4 MB gzipped — ✅
- Individual chunk ≤2 MB — ✅ Viewport chunk = 0.19 MB

## Round-2 plan

- All 3 fixes are applied per Codex's suggested fix bullets
- New regression test for finding #1
- Tests + typecheck + production build all clean
- Round-2 Codex review will verify the fixes didn't introduce new
  regressions and that all 3 findings are RESOLVED

## Counter

DEC-V61-094 counter remains at 59 until per-implementation-arc Codex
returns APPROVE/APPROVE_WITH_COMMENTS in Round 2 (autonomous_governance
counter advances on the implementation DEC, not on this fix-arc
intermediate).
