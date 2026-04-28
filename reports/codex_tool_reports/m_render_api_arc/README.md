# M-RENDER-API arc · Codex review audit trail

**DEC**: DEC-V61-095 (Accepted 2026-04-28)
**Trigger**: RETRO-V61-001 risk-tier (multi-file backend + new HTTP surface + frontend dispatch path · ~2329 LOC)
**Implementation arc**: `c4264f7..84fa4cf` (3 feature commits + 4 fix commits)

## Round summary

| Round | Verdict | Findings | Outcome |
|-------|---------|----------|---------|
| 1 | CHANGES_REQUIRED | 6 (2 P1 · 4 P2) | symlink escape · dead-code fallback · TOCTOU · face-OOB · importer leak · eager bundle |
| 2 | CHANGES_REQUIRED | 5 verified · F3 partial · +F7 P3 (chunk-load) | residual TOCTOU window · chunk-load normalization gap |
| 3 | CHANGES_REQUIRED | F7 verified · F3 still partial | concurrent-reader (replace, unlink) window |
| 4 | CHANGES_REQUIRED | F3 closed BUT regression introduced | `source.stat()` raw `FileNotFoundError` + temp leak |
| 5 | **APPROVE** ✓ | All 7 findings closed · parity verified | merge-ready |

## Feature commits

- `d0360bf` · feat(render): M-RENDER-API Step 2+3 — services/render skeleton + /geometry/render glb endpoint + mtime-keyed cache
- `676b8c2` · feat(render): M-RENDER-API Step 4 — /mesh/render polyMesh wireframe glb
- `2fd3baf` · feat(render): M-RENDER-API Steps 5+6 — field-sample binary stream + frontend glb dispatch

## Fix commits

- `a8dd37f` · fix(render): Round-2 Codex fixes (Findings 1-6)
- `a2f263d` · fix(render): Round-3 Codex fixes (Findings 3, 7)
- `c4f893a` · fix(render): Round-4 Codex fix · close concurrent-reader window
- `84fa4cf` · fix(render): Round-5 Codex fix · OSError tolerance in pre/post-replace stat

## Test counts (final)

- Backend: 59/59 pass (M-RENDER-API tests · 17 field_sample + 14 geometry_glb + 28 mesh_wireframe)
- Frontend: 42/42 pass (5 visualization test files · was 29 before M-RENDER-API)

## Bundle delta (spec_v2 §AC#10)

- Before: Viewport chunk 722.81 KB / 201.85 KB gz (GLTFImporter inlined)
- After:  Viewport chunk 689.70 KB / 191.58 KB gz + GLTFImporter chunk 34.10 KB / 11.29 KB gz (lazy-split)
- STL-only consumers save 11.29 KB gz · §AC#10 +50 KB delta budget preserved with margin

## Briefs

Each round's brief lives at `/tmp/codex_review/m_render_api_round{N}_brief.md`. Briefs documented (a) prior-round verdict, (b) the specific fixes shipped, (c) what to verify, and (d) the canonical output format with verdict trailer.
