# M-RENDER-API Tier-A · Backend render endpoints + frontend glb dispatch · Dogfood log

**Date**: 2026-04-28
**Scope**: M-RENDER-API Tier-A per `.planning/strategic/m_render_api_kickoff/spec_v2_2026-04-28.md`
**Strategic clearance**: Kogami NOT triggered (per DEC-V61-094 P2 #1 bounding clause · 4-condition self-check passed)
**Ratifying DEC**: DEC-V61-095 (Accepted 2026-04-28 · arc closed 2026-04-28)
**Arc commit range**: `c4264f7..84fa4cf` (3 feature + 4 fix)
**Codex**: 5-round APPROVE at R5 · audit trail at `reports/codex_tool_reports/m_render_api_arc/`

---

## Programmatic verification

| Check | Status | Evidence |
|---|---|---|
| `GET /api/cases/{id}/geometry/render` returns 200 + valid glb (magic `b'glTF'`) for box / cylinder / naca0012 | ✅ | `test_get_case_geometry_render_returns_glb_for_cube` + parametrized fixture sweep |
| Cache hit on repeat call returns byte-equal payload | ✅ | `test_cache_hit_returns_byte_equal_payload` |
| Cache invalidates on source mtime change | ✅ | `test_cache_invalidates_on_source_mtime_change` |
| Symlink under `triSurface/` pointing outside case dir is rejected (no_source_stl) | ✅ R2 F1 | `test_build_geometry_glb_rejects_stl_symlink_escape` |
| `GET /api/cases/{id}/mesh/render` returns 200 + valid glb for cube polyMesh fixture | ✅ | `test_get_case_mesh_render_returns_glb_for_cube` |
| polyMesh face with vertex ID >= n_points fails as 422 (polymesh_parse_error) | ✅ R2 F4 | `test_build_mesh_wireframe_422_on_face_index_out_of_range` |
| polyMesh symlink escape → 422 | ✅ R2 F1 | `test_build_mesh_wireframe_rejects_polymesh_symlink_escape` |
| `GET /api/cases/{id}/results/{run_id}/field/{name}` returns 200 + binary float32 stream + `X-Field-Point-Count` | ✅ | `test_get_case_field_returns_binary_float32_stream` |
| Field cache hit byte-equal | ✅ | `test_get_case_field_byte_equal_on_cache_hit` |
| Field-sample cache invalidates on source mtime | ✅ | `test_build_field_payload_invalidates_on_mtime` |
| Pre-replace mtime mutation aborts atomic write (no stale cache visible to concurrent readers) | ✅ R4 F3 | `test_build_field_payload_aborts_on_pre_replace_source_mutation` |
| Source vanish during atomic write surfaces as failing_check + cleans temp (no leak) | ✅ R5 F3 | `test_build_field_payload_aborts_on_source_vanish` |
| Field-name traversal in URL rejected (404 field_not_found) | ✅ | `test_build_field_payload_rejects_traversal_in_field_name` + symlink-escape variant |
| Field-sample uniform internalField → 422 (field_unsupported) | ✅ | `test_build_field_payload_422_on_uniform_field_unsupported` |
| Frontend `glb_loader.ts` mirrors stl_loader contract (fetch 200/4xx/network-err/abort + parse success/dispose) | ✅ | 6 tests in `glb_loader.test.ts` |
| Frontend Viewport dispatches on `format='stl'\|'glb'` and surfaces `kind='config'` for missing URL | ✅ | 4 new tests + 5 existing in `Viewport.test.tsx` |
| Frontend kernel `attachGltf` exception-safe (importer disposed on importActors throw) | ✅ R2 F5 | "renders an error banner when kernel.attachGltf throws" + glb-unmount disposal test |
| Lazy-chunk-load failure normalized to `GlbLoadError(kind='parse')` | ✅ R3 F7 | "normalizes lazy-chunk-load failures to GlbLoadError(kind=parse)" |
| `vtkGLTFImporter` lazy-imported (not in Viewport main chunk) | ✅ R2 F6 | bundle output: separate `GLTFImporter-*.js` 34.10 KB / 11.29 KB gz |
| Frontend typecheck clean | ✅ | `npm run typecheck` |
| Frontend test suite | ✅ | 42/42 (was 29 before M-VIZ; 39 after M-VIZ; +3 in this arc — 6 glb_loader tests, 4 viewport-dispatch tests, partially overlapping with existing renumbering) |
| Backend M-RENDER-API tests | ✅ | 59/59 (17 field_sample + 14 geometry_glb + 28 mesh_wireframe) |

## Spec acceptance criteria checklist (from spec_v2 §AC#1..#10)

| # | AC | Status | Note |
|---|----|--------|------|
| 1 | DEC-V61-095 ratified before any implementation commit | ✅ | DEC `Accepted` 2026-04-28 (commits `c4264f7..e15c153`) precedes feature commit `d0360bf` |
| 2 | All 3 endpoints land behind `/api/cases/...` namespace per Pivot Charter Addendum 3 §4.a | ✅ | routes/geometry_render.py — geometry/render, mesh/render, results/{run}/field/{name} |
| 3 | Tier-A scope: glb (geometry+mesh) + binary float32 stream (field); glTF-accessor-with-COLOR_0 deferred to M-VIZ.results | ✅ | Field endpoint returns `application/octet-stream`; spec note threaded through field_sample.py docstring |
| 4 | mtime-keyed cache + atomic-rename writes per service | ✅ | 3 services share the temp+stat+replace+stat pattern; race coverage R3+R4+R5 closed all known windows |
| 5 | Source-path containment guards prevent symlink escape (R2 F1) | ✅ | resolve(strict=True) + relative_to(case_root) on every chosen source file in all 3 services |
| 6 | polyMesh face-index bounds validation (R2 F4) | ✅ | `polymesh_parser.validate_face_indices` + 3 unit tests + 1 e2e |
| 7 | Frontend `format='stl'\|'glb'` dispatch with backward-compatible default | ✅ | M-VIZ-era `<Viewport stlUrl=... />` callers unchanged; new `format='glb'` opt-in |
| 8 | GLB importer ownership exception-safe (R2 F5) | ✅ | `viewport_kernel.attachGltf` wraps setRenderer + importActors in try/catch + delete on throw |
| 9 | Frontend bundle delta ≤ +50 KB gzipped vs M-VIZ baseline | ✅ | Viewport chunk shrunk from 201 KB gz to 191 KB gz (-10 KB); separate GLTFImporter chunk 11 KB gz (lazy on `format='glb'`); STL-only flow saves 10 KB gz |
| 10 | Codex review per RETRO-V61-001 risk-tier triggers | ✅ | 5-round arc converged at R5 APPROVE; full audit at `reports/codex_tool_reports/m_render_api_arc/` |

---

## Codex 5-round summary

| Round | Verdict | Key findings | Resolution |
|-------|---------|--------------|------------|
| 1 | CHANGES_REQUIRED | F1 P1 (symlink escape) · F2 P1 (dead-code phase5_fields fallback) · F3 P2 (TOCTOU) · F4 P2 (face-OOB) · F5 P2 (importer ownership on attachGltf throw) · F6 P2 (eager GLTFImporter bundle) | Round 2: 5 verified · 1 partial · 1 new |
| 2 | CHANGES_REQUIRED | F3 PARTIAL (post-stat residual race) · F7 P3 NEW (chunk-load normalization) | Round 3: F7 verified · F3 still partial |
| 3 | CHANGES_REQUIRED | F3 PARTIAL (concurrent-reader window between replace and unlink) | Round 4: F3 closed BUT regression introduced |
| 4 | CHANGES_REQUIRED (REGRESSION) | F3 closure introduced raw `FileNotFoundError` propagation + temp leak when source vanished mid-build | Round 5: closed via OSError tolerance in pre/post-replace stat |
| 5 | **APPROVE** ✓ | All 7 findings closed; parity verified across 3 services | merge-ready |

## §11.1 BREAK_FREEZE accounting

**No ImportPage / Workbench-frontend feature edits in this arc.** §11.1 BREAK_FREEZE counter stays at the M-VIZ value (1/3) — M-RENDER-API ships pure backend endpoints + a Viewport prop addition with backward-compatible default; no user-visible workbench surface changes until M-PANELS wires these endpoints into the UI.

## What's wired vs what isn't

**Wired (consumable now)**:
- `GET /api/cases/<id>/geometry/render` — STL → glb transcode (replaces M-VIZ's STL-passthrough as the canonical 3D-preview source)
- `GET /api/cases/<id>/mesh/render` — polyMesh → wireframe glb
- `GET /api/cases/<id>/results/<run_id>/field/<name>` — scalar field → float32 binary stream
- `<Viewport format='glb' glbUrl=... />` — drop-in replacement for the STL path

**NOT wired (M-PANELS scope)**:
- ImportPage still consumes `format='stl'` (M-VIZ default). Switching to `format='glb'` for the import preview is a one-line ImportPage edit but lives in M-PANELS so it can be paired with the panel-naming workflow.
- No mesh-wireframe or field-sample consumers exist in the frontend yet — those land in M-PANELS / M-VIZ.results.
- Face-pick / face-naming feature (CFDJerry's M-VIZ Step-7 ask) remains in M-PANELS scope per the captured project doc.

## Tier-A vs Tier-B / future scope

- Tier-A glb endpoints: trimesh for STL→glb (existing dep · zero new pip), hand-built minimal glTF for polyMesh LINES (trimesh has no LINES primitive). vtkGLTFImporter on the frontend handles both paths.
- Field-sample Tier-A returns raw float32 stream; the colormap mapping is a frontend concern that M-PANELS / M-VIZ.results will own. Spec_v2 §B.3 explicitly defers glTF-accessor-with-COLOR_0 packing to M-VIZ.results.
- Post-replace mtime guard chosen over fcntl.flock for cross-platform simplicity. Tier-A scope is single-user dev tool; multi-tenant production would warrant flock.

## Recruitment / customer-anchor implications

- M-RENDER-API delivers the backend surface that M-PANELS depends on (panel naming, field overlay, mesh inspector). Path A "first customer" recruitment in `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md` does NOT need to wait for M-PANELS to begin — once an interested user lands on the import flow they get the M-VIZ STL preview today; the glb / field surface comes online when they open a runs page.
