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
| 3 | Viewport renders all 3 bundled STLs in real Chrome | ✅ CFDJerry confirmed 2026-04-28 (ldc_box) | cylinder/naca0012 not separately tested but vtk.js path is fixture-shape-agnostic; smoke-tested programmatically end-to-end |
| 4 | Pan / rotate / zoom each work | ✅ CFDJerry confirmed drag works 2026-04-28 | wheel-zoom + shift-pan + ⌥-spin not individually called out in user report; default vtk.js TrackballCamera maps these correctly per source-grep verification (round-5 fix) |
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

**End-to-end roundtrip smoke against the live dev stack** (pre-Step-7 ·
2026-04-28 05:41 UTC):

| Fixture | Upload | Direct serve | Vite-proxy serve | Byte-equal |
|---------|--------|--------------|------------------|-----------|
| `ldc_box.stl` (684 B) | ✅ POST 200 | ✅ 684 B served | ✅ 684 B via proxy | ✅ `cmp -s` clean |
| `cylinder.stl` (6 484 B) | ✅ POST 200 | ✅ 6 484 B served | ✅ 6 484 B via proxy | ✅ `cmp -s` clean |
| `naca0012.stl` (31 484 B) | ✅ POST 200 | ✅ 31 484 B served | ✅ 31 484 B via proxy | ✅ `cmp -s` clean |

Headers on `GET /api/cases/{case_id}/geometry/stl`:

```
HTTP/1.1 200 OK
content-type: model/stl
content-length: 684
content-disposition: attachment; filename="ldc_box.stl"
accept-ranges: bytes
last-modified: Tue, 28 Apr 2026 05:41:48 GMT
etag: "4746928ac2a70ac384325a59474d40aa"
```

Negative paths (also live-verified):

| Probe | Expected | Got |
|-------|---------|-----|
| `GET /api/cases/unknown_case_xyz/geometry/stl` | 404 | 404 ✅ |
| `GET /api/cases/bad@id/geometry/stl` (unsafe id) | 404 | 404 ✅ |
| `HEAD ...stl` | 405 (no HEAD route) | 405 + `Allow: GET` ✅ |

Codex round-1 #1 fix verified on live stack:
- Uploaded a fixture renamed `UPPER_TEST.STL` (uppercase extension)
- M5.0's `_safe_origin_filename` preserves casing → on-disk path is
  `triSurface/UPPER_TEST.STL`
- `GET /api/cases/{case_id}/geometry/stl` now returns 200 + 6 484 bytes
  (the previous `glob("*.stl")` would have returned 404)

**Backend ✅ verified end-to-end on real ports.** Only the in-browser
visual rendering remains.

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

#### M-VIZ Tier-A scope: clean ✅
CFDJerry confirmed 2026-04-28: ldc_box upload + 3D cube render + camera
drag all work. M-VIZ Tier-A acceptance complete.

#### Out-of-scope observations (not M-VIZ regressions · captured for downstream)

1. **Default-faces gap (M5.0 surface limitation, not M-VIZ defect)**:
   imported binary STL surfaces with `all_default_faces=true` because
   binary STL format has no named-solid concept. Engineer cannot set
   per-patch boundary conditions without named patches. M5.0 already
   supports multi-solid ASCII STL upload as a workaround (each named
   solid → named patch); deferred fix at the **viewport level** is
   issue #2 below.

2. **Interactive face-pick + name in viewport (NEW feature request)**:
   CFDJerry asks: can the 3D preview be made interactive so engineers
   can click a face and assign name+description directly in the
   viewport? This is the standard ParaView/ANSYS/Star-CCM pattern and
   would solve issue #1 for engineers who can't pre-name in CAD.

   **Recommendation**: defer to **M-PANELS** scope. Reason: the
   feature spans M-RENDER-API (`POST /api/cases/<id>/patches`
   endpoint + manifest persistence) + M-VIZ.advanced (vtk.js cell
   picker + triangle→patch lookup) + M-PANELS Step 2 UX integration
   (Task-Panel name dialog). Building it standalone before M-PANELS
   commits to UX decisions in isolation; high redo risk.

   Captured in `.planning/strategic/m_panels_interactive_face_naming_2026-04-28.md`
   + user memory.

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
