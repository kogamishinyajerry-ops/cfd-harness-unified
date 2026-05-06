---
decision_id: DEC-V61-129a
title: Per-patch severe-non-ortho count from checkMesh nonOrthoFaces faceSet · narrow V129a (V129b heavy per-cell aggregation deferred)
status: Accepted (2026-05-06 · Codex R3 APPROVE clean at 18bc660 · 3-round chain, BOTTOM of 3-4 prediction band. Empirical-capture discipline (faceSet body verified against OpenFOAM 10 container BEFORE writing the parser) prevented format-guess rounds; the two findings caught (R1 P1 bash-rc swallow, R2 P2 test substituting wrong path) were both real bugs caught the first time they were introduced.)
codex_tool_report_path: reports/codex_tool_reports/v61_129a_r1_chain.md
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline per RETRO-V61-001)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-06
authored_under: User 2026-05-06 mandate "按你的顺序和建议，继续推进" (fourth issuance) — V128 closed at R1 APPROVE clean, calibration recovered. V129a is the next narrowest cut from my recommendation list: real per-patch severe-non-ortho count parsed from checkMesh's `nonOrthoFaces` faceSet (constant/polyMesh/sets/nonOrthoFaces) WITHOUT the heavyweight per-cell field aggregation (V129b) that V127's chain report flagged for V129. Cross-contract surface (backend exec flag + parser + schema + frontend consumer); predicted 3-4 rounds.
parent_decisions:
  - DEC-V61-128 (V128 patch chip derived coloring · V129a replaces V128's amber/green fallback with REAL per-patch data when available, and falls through to V128 logic when not)
  - DEC-V61-127 (mesh-quality card · V129a continues Phase E shell-entry visual signal work on the same surface)
  - DEC-V61-126 (V126 schema · V129a extends MeshQualityReportV126 with one new field; preserves base V122 + V126 contract)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · cross-contract triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/mesh_quality/checkmesh_runner.py (extended with -allGeometry -allTopology + faceSet body capture + parser)
  - ui/backend/services/mesh_quality/analyzer.py (new _read_patch_ranges + aggregate_severe_faces_per_patch helpers)
  - ui/backend/services/mesh_quality/schemas.py (MeshQualityReportV126 gains checkmesh_n_severe_non_ortho_faces_per_patch field)
  - ui/frontend/src/pages/workbench/step_panel_shell/types.ts (mirror schema field)
  - ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx (PatchChips uses real per-patch count when present, V128 fallback otherwise)
counter_impact: +1 (autonomous_governance: true · cross-contract change. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter ≥ 20, not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 cross-contract trigger.)
notion_sync_status: synced 2026-05-06 (https://www.notion.so/358c68942bed819f9a91f06f66539858)
self_estimated_pass_rate: 60% (predicted 3-4 rounds · cross-contract per V123 §L1. Backend parser + schema + frontend consumer is exactly the surface that earned cross-contract designation. Empirically captured the real OpenFOAM-10 faceSet body format BEFORE writing the parser to reduce R0→R1 misses on format guesses; this should pull the round count toward 3 rather than 4. The +5% over V128's 75% reflects the empirical-capture discipline; the -15% from V128's actual 100% reflects the genuinely larger surface area.)

---

# DEC-V61-129a · Per-patch severe-non-ortho count

## Why now

V128 ships chip coloring derived from already-fetched data (mesh_ok globally — every chip is amber on global failure). Engineers can't tell WHICH patch is causing the failure; they have to scan the failed_checks list manually. V129a pulls per-patch data from checkMesh's existing `nonOrthoFaces` faceSet output (already written automatically when faces fail the orthogonality check) so chips show genuine localized signal.

V129a is deliberately the NARROW cut of the V129 work scoped in V128's chain report. The HEAVY V129b path (per-cell field aggregation via `-writeAllFields` field-file parsing + cell→patch mapping for skewness/aspect-ratio per patch) defers; it's a 5-7 round arc on its own and depends on infrastructure V129a doesn't need.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: V129a maps to V128's "deferred to V129" line and to the Phase E shell-entry roadmap (engineer can localize mesh quality issues to specific patches without scanning text).

**Existing-implementation grep** + empirical container probe:
- `checkmesh_runner.py` runs `checkMesh 2>&1` (no extra flags); the OpenFOAM 10 default doesn't write the nonOrthoFaces faceSet
- Confirmed empirically (cfd-openfoam container 2026-05-06 sweep): `checkMesh -allGeometry -allTopology` writes `constant/polyMesh/sets/nonOrthoFaces` (and `skewFaces`) when issues are found, in canonical OpenFOAM faceSet dictionary format (FoamFile header + count + paren list of int face IDs)
- Existing `_BOUNDARY_PATCH_RE` in analyzer.py captures (name, nFaces, startFace) — the third group is currently discarded by `_read_patch_face_counts`; V129a needs all three for face-id → patch mapping
- No existing per-patch severe-face aggregation infrastructure

**Disposition: extend** — cross-file edit:
- `checkmesh_runner.py`: add `-allGeometry -allTopology` + `cat constant/polyMesh/sets/nonOrthoFaces` tail with sentinel separator; extract face IDs in parser
- `analyzer.py`: add `_read_patch_ranges` + `aggregate_severe_faces_per_patch` helpers; thread patch_ranges into `_try_run_checkmesh`
- `schemas.py`: add one new optional field
- `types.ts`: mirror the field
- `MeshQualityCard.tsx`: PatchChips tone derivation gets a new precedence level

## V1 scope (V129a deliberately narrow)

V129a R0 ships:

1. **`checkmesh_runner.py` extension** (~30 LOC):
   - Add `-allGeometry -allTopology` flags to checkMesh exec_run command
   - Append `cat constant/polyMesh/sets/nonOrthoFaces 2>/dev/null || true` with a sentinel delimiter so the existing single exec_run captures both stdout and the set body
   - New `_parse_faceset_body` parser (header-tolerant: skips OpenFOAM banner + FoamFile dict; reads count + paren list)
   - Extend `CheckMeshResult` with `severe_non_ortho_face_ids: tuple[int, ...]`
2. **`analyzer.py` extension** (~50 LOC):
   - New `_read_patch_ranges` returns `dict[str, tuple[int, int]]` (startFace, nFaces); existing `_read_patch_face_counts` becomes a thin wrapper
   - New `aggregate_severe_faces_per_patch(face_ids, patch_ranges)` does the linear-scan map → per-patch count dict (always includes every patch with count=0 for clean ones)
   - Thread `patch_ranges` from `analyze_mesh_quality` into `_try_run_checkmesh`
3. **`schemas.py`**: add `checkmesh_n_severe_non_ortho_faces_per_patch: dict[str, int] | None` (default None) to MeshQualityReportV126
4. **Frontend**:
   - `types.ts`: mirror the new field
   - `MeshQualityCard.tsx` PatchChips: new precedence level — when V129a dict present, per-patch severe>0 → rose, severe=0 → green (overrides V128's mesh_ok-derived amber/green). When dict null, V128 logic preserved.
   - Chip text appends "·N severe" suffix when count > 0 (a11y: text signal redundant with rose tone)
5. **Tests**:
   - Backend: 6 new (faceSet parser real fixture + empty + header-only; aggregator maps + zeros + empty patches)
   - Frontend: 5 new (per-patch>0 → rose; all 0 → green; V129a null + V128 fallback; zero-face precedence; missing patch fallthrough)

## Out of scope (deferred to V129b)

- Cell-level field-file parsing (`-writeAllFields` produces `0/cellSkewness`, `0/nonOrthoAngle`, `0/cellAspectRatio` scalar fields)
- Cell→patch mapping via owner+boundary
- Per-patch max(skewness) / max(aspect_ratio) / max(nonOrthoAngle) aggregation
- Continuous-value gauges per patch chip
- 3D viewport per-cell coloring (Phase E v2 separate DEC)

V129a is intentionally a **single-metric, count-based** cut. V129b can build on V129a once the per-patch dict surface proves useful in dogfood.

## Risk register

1. **Container output format drift**: the empirical probe was against OpenFOAM 10. If the cfd-openfoam container is upgraded to 11, the faceSet body format would need re-verification. Parser is tolerant (header-blind, skips non-int lines until `(`) so minor format adjustments are absorbed.
2. **Internal-face severe count loss**: the global `n_severe_non_ortho_faces` count includes both internal AND boundary faces; per-patch dict only counts boundary ones. The global count remains in the schema for the gauge and is the canonical "total severe" — per-patch is a localization aid, not a sum.
3. **Sentinel collision**: the bash-cmd uses `__CFD_HARNESS_SET_BODY_DELIM__` between checkMesh stdout and the cat tail. If checkMesh ever emitted that string verbatim, the partition would break. The string is unique enough that this is virtually impossible, but the parser is defensive (uses `partition` not `rsplit`, so the FIRST occurrence wins, and the parser handles missing-sentinel gracefully).
4. **a11y**: tone is reinforced by "·N severe" text suffix on rose chips; color-blind users see the same signal.

## Acceptance criteria

- Backend regression: 1234+ pass (V129a adds 6 new tests; pre-existing failures in unrelated files unchanged)
- Frontend tests: 29/29 pass (was 24, +5 V129a scenarios)
- tsc: clean
- OpenAPI surface: schema gains one optional field; backward-compat preserved (default None)
- Visual smoke: in dev server with cfd-openfoam container running on a deliberately skewed mesh, confirm rose chip with "N severe" suffix appears for the failing patch
- Codex review APPROVE
