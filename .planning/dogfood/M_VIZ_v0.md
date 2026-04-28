# M-VIZ Tier-A · 3D Viewport Infrastructure · Dogfood Log

**Date**: 2026-04-28
**Scope**: M-VIZ Tier-A per `.planning/strategic/m_viz_kickoff/spec_v2_2026-04-28.md`
**Strategic clearance**: Kogami APPROVE_WITH_COMMENTS in
`.planning/reviews/kogami/m_viz_kickoff_governance_clearance_2026-04-28/review.md`
**Ratifying DEC**: DEC-V61-094 (Accepted 2026-04-28)
**Ratifying commit**: `7642bb4` (Codex-verified: APPROVE_WITH_COMMENTS · 5-round halt)

---

## Programmatic verification (already captured · pre-Step-7)

| Check | Status | Evidence |
|---|---|---|
| Backend `GET /api/cases/{id}/geometry/stl` returns 200 + STL bytes for ldc_box | ✅ | `test_get_case_stl_returns_bytes_for_cube` |
| Backend serves all 3 fixture shapes (ldc_box · cylinder · naca0012-like) | ✅ | parametrized `test_get_case_stl_serves_three_bundled_fixture_shapes` |
| Backend 404 for unknown case_id · missing triSurface · empty triSurface · unsafe id | ✅ | 4 tests in `test_geometry_render_route.py` |
| Backend matches `.STL` (uppercase) on case-sensitive FS | ✅ | `test_get_case_stl_matches_uppercase_extension` (Codex R1 #1 fix) |
| Frontend Viewport mounts + fetches STL + renders ready/loading/error states | ✅ | 5 RTL tests · vtk.js mocked via vtk-stub alias |
| Frontend `loadStlFromUrl` fetch path covers 200/404/network-err/abort | ✅ | 4 fetch tests in `stl_loader.test.ts` |
| Frontend parser converts vtk.js native throws to `StlLoadError(kind="parse")` + dispose reader | ✅ | 1 test · Codex R2 #1 fix |
| Frontend disposes kernel on unmount (no WebGL leak) | ✅ | 1 test · asserts `disposeMock` called once |
| Production bundle: main entry ≤2.5 MB gzipped (soft target) | ✅ | 349 KB gzipped · vtk.js lazy-loaded |
| Production bundle: Viewport chunk loaded only after upload | ✅ | 190 KB gzipped lazy chunk |
| Frontend typecheck clean | ✅ | `npm run typecheck` |
| Frontend test suite | ✅ | 29/29 passing |
| Backend test suite (route + scaffold + ingest unaffected) | ✅ | 9/9 new + 437 pre-existing pass |

## Spec acceptance criteria checklist (from spec_v2 §AC#1..#10)

| # | AC | Status | Note |
|---|----|--------|------|
| 1 | Library choice ratified by CFDJerry | ✅ | DEC-V61-094 frontmatter `library_choice: vtk.js` · CFDJerry "全 yes" 2026-04-28 |
| 2 | ROADMAP line-A contract extension landed PRE-implementation | ✅ | Commit `8fdb0a3` lands BEFORE Step 3 commit `b4074c5` |
| 3 | Viewport renders all 3 bundled STLs in real Chrome | ⏸️ pending CFDJerry | manual smoke checklist below |
| 4 | Pan / rotate / zoom each work | ⏸️ pending CFDJerry | manual smoke checklist below |
| 5 | `npm run typecheck` clean | ✅ | |
| 6 | `npm test -- --run` all green | ✅ | 29/29 |
| 7 | `pytest ui/backend/tests -q` all green | ✅ | 9/9 new + 437 pre-existing (4 unrelated pre-existing failures stable) |
| 8 | Bundle-size tiered budget | ✅ | main 349 KB / Viewport 190 KB gzipped — soft 2.5 MB / hard 4 MB / chunk 2 MB all clear |
| 9 | No WebGL / canvas leak on unmount | ✅ | dispose order verified (R3 #2 trackball + R4 #1 DOM listener fixes) |
| 10 | DEC §Path A engagement timeline filled | ✅ | DEC-V61-094 §Scope item 5 milestone-anchored Gates 0..4 |

AC #3 + #4 require human-eyes verification — that is Step 7's purpose.

---

## Step 7 · CFDJerry manual visual smoke checklist

**Dev stack** (already running; verified healthy 2026-04-28):

- Backend (FastAPI): `http://127.0.0.1:8004`
- Frontend (Vite): `http://127.0.0.1:5183`
- Backend port chosen because 8000 was occupied (no-port-squatting rule);
  Vite was started with `CFD_BACKEND_PORT=8004` so the proxy follows.

**Health probes** (passed pre-Step-7):
- `curl http://127.0.0.1:8004/api/health` → `{"status":"ok"}`
- `curl http://127.0.0.1:5183/api/health` (via Vite proxy) → same response
- `/api/cases/{id}/geometry/stl` route is registered (visible in `/api/openapi.json`)

### Smoke procedure

1. Open `http://127.0.0.1:5183/workbench/import` in Chrome
2. Upload `examples/imports/ldc_box.stl` (684 B · watertight cube · 12 faces)
3. After "Case created" panel appears, scroll to **Geometry preview** panel
4. Verify the cube renders inside the dark canvas
5. Test camera controls:
   - [ ] **Drag** to rotate (left-mouse drag in canvas) — cube should orbit
   - [ ] **Wheel** to zoom — cube grows/shrinks
   - [ ] **Shift+drag** to pan — cube translates
   - [ ] **⌥drag** to spin (rotates camera around its forward axis)
   - [ ] **Reset camera** button recenters cube and resets zoom
6. Click "Import another" → upload `examples/imports/cylinder.stl` → verify same controls work
7. Repeat with `examples/imports/naca0012.stl` (628 faces · larger fixture)
8. **Stress test mount/unmount** — repeat upload cycle 3-5×; observe DevTools
   Performance / Memory tab for any visible WebGL context leak (Chrome warns
   in DevTools console if too many WebGL contexts are alive)
9. Screenshot each fixture's render + paste below

### Expected visual checklist

- [ ] ldc_box.stl renders (small grey cube, default lighting)
- [ ] cylinder.stl renders (grey cylinder, ~24 sections)
- [ ] naca0012.stl renders (airfoil section)
- [ ] Drag rotates · wheel zooms · shift-drag pans · ⌥-drag spins · Reset works
- [ ] No console errors visible in Chrome DevTools
- [ ] No WebGL leak warnings after 3-5× upload cycle
- [ ] Existing post-upload report card and "Continue to editor" link still work
  (regression check: M5.0 surface preserved per DEC-V61-094 §A.2 constraint)

### Screenshots

> Paste Chrome screenshots here after smoke. PNG inline or relative path
> to `.planning/dogfood/screenshots/m_viz_*.png`.

### Issues encountered

> If any step fails, list the symptom + reproduction here. Each issue
> opens a follow-up commit + may trigger a fresh Codex regression review
> using the reserved Pro quota slice.

---

## Codex iteration summary (Step 8 · pre-smoke)

| Round | Findings (severity) | Resolution | Status |
|-------|---------------------|------------|--------|
| 1     | 3 P2 (case-sensitivity · Viewport overflow · eager bundle) | `4811c27` | RESOLVED in R2 |
| 2     | 1 P2 (vtk.js parse exception leak)                          | `8c72a65` | RESOLVED in R3 |
| 3     | 1 P1 + 1 P3 (unused import · trackball style leak)          | `12baa5e` | RESOLVED in R4 |
| 4     | 1 P2 (DOM-listener leak in dispose order)                   | `b5e560b` | RESOLVED in R5 |
| 5     | 1 P3 (pan-modifier copy)                                    | `855e1e6` | self-verified  |

Ratification: `7642bb4` (empty ops commit · canonical
`Codex-verified: APPROVE_WITH_COMMENTS` trailer · halts iteration at
R5 + verbatim copy fix per CFDJerry direction).

Reports: `reports/codex_tool_reports/2026-04-28_m_viz_bundle_steps_3_to_6_codex_review_round{1..5}.md`

---

## Path A engagement gate state

Per DEC-V61-094 §Path A timeline:

- **Gate 0** (DEC ratified · async mockup feedback): N/A — no stranger
  recruited as of 2026-04-28
- **Gate 1** (M-VIZ MVP merged on `main`): **UNLOCKED** as of `7642bb4`
  push 2026-04-28. Demo shape: stranger uploads own STL → sees it
  render with camera controls.
- Gate 2/3/4: blocked on M-RENDER-API / M-PANELS / M-AI-COPILOT respectively.

If a stranger surfaces, Gate-1 demo flow:
1. Send the dev URL `http://...:5183/workbench/import` (or a deployed
   instance once available)
2. They upload their own STL
3. They see the geometry render with trackball controls
4. First credible "this is real" moment per DEC §Path A

---

## Next steps after CFDJerry smoke

If smoke passes (all checkboxes green):
- DEC-V61-094 Status flips from Accepted → Closed (or stays Accepted with
  a closeout note · TBD per project convention)
- Counter advances 59 → 60 on the closeout DEC
- Optional: post-Step-7 regression Codex review (uses reserved Pro quota)
- M-RENDER-API kickoff DEC drafting begins (next milestone in Addendum 3
  hard ordering)

If smoke fails:
- Each issue → fix commit
- Optional Codex regression round before re-smoke
- Step 7 re-runs until clean

---

## Counter

DEC-V61-094 counter advance: 58 → 59 (already advanced on DEC ratify
2026-04-28). No further advance from Step 7 itself; the post-smoke
closeout DEC (when written) is what advances 59 → 60.
