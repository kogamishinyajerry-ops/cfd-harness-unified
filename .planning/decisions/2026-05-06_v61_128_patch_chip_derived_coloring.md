---
decision_id: DEC-V61-128
title: Patch chip derived coloring · narrow V128 R0 (frontend-only · cell-level data deferred to V129)
status: Accepted (2026-05-06 · Codex R1 APPROVE clean at 02d447f · 1-round chain, BOTTOM of 1-2 prediction band. Calibration recovered after V127's 8-round miss; the deliberately narrow scope worked as intended.)
codex_tool_report_path: reports/codex_tool_reports/v61_128_r1_chain.md
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline per RETRO-V61-001)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-06
authored_under: User 2026-05-06 mandate "按你的顺序和建议，继续推进" (third issuance) — V127 closed at R8 APPROVE, scope continues per recommended order. Original V127 §V1 deferred per-patch coloring to "V128+"; this DEC narrows V128 R0 to frontend-derived coloring (no backend, no schema change) and pushes the heavyweight per-cell aggregation to V129. Rationale: V127 just took 8 rounds on cache-design surface; deliberately holding V128 narrow per V123 §L1 to recover calibration headroom before re-attempting cross-contract work.
parent_decisions:
  - DEC-V61-127 (mesh-quality card · V128 colors the chips that V127 ships in neutral grey)
  - DEC-V61-126 (V126 schema · V128 reads existing checkmesh_mesh_ok + patch_face_counts; no schema change)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · UI polish triggers Codex pre-merge)
parent_artifacts:
  - ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx (existing PatchChips component — V128 extends its props + tone derivation)
  - ui/frontend/src/pages/workbench/step_panel_shell/__tests__/MeshQualityCard.test.tsx (existing tests — V128 adds 4 chip-coloring scenarios)
counter_impact: +1 (autonomous_governance: true · single-file frontend extension. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro, not governance-rule change — single-file ≤50 LOC routine commit clause applies. Codex pre-merge per RETRO-V61-001 (UI interaction polish triggers it; even though single-file, V127's calibration miss argues for being conservative).)
notion_sync_status: synced 2026-05-05 (https://www.notion.so/357c68942bed81d18fe3d996c0c4d95c)
self_estimated_pass_rate: 75% (predicted 1-2 rounds · narrow no-cross. Single-file frontend, deriving from already-fetched data, no new contract surface. V127's calibration miss was rooted in cross-component cache contracts; V128 has none of that — it's pure render-derive logic. The +5% over V127's prediction reflects the deliberately tighter scope.)

---

# DEC-V61-128 · Patch chip derived coloring · narrow V128 R0

## Why now

V127 ships gauges and a verdict pill but the per-patch chip row is rendered uniformly neutral grey. The engineer can see "Mesh OK" or "Failed N checks" globally but can't visually triage WHICH patches are most likely problematic. V128 closes that gap with a derived signal — no new backend metric, just smarter rendering of data already fetched.

V127 §V1 originally queued per-patch coloring for "V128 (needs cell-level checkMesh data — `-allTopology -allGeometry -writeAllFields` flag)". V128 R0 explicitly does NOT pursue that path; the cell-level / per-cell aggregation work moves to V129. Rationale: V127 took 8 rounds on cache-design cross-contract surface (predicted 3); calibration headroom is constrained. V128 stays narrow to recover prediction confidence before re-attempting cross-contract work.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: V128 maps to V127 §"deferred to V128+" and to the user-stated UX endgame ("可视化的悬浮进度条，直观的感受到工作正在推进，也能知道哪些内容被AI检查过、智能优化过") — making each patch visually tagged with a quality state is part of "you can feel the work happening".

**Existing-implementation grep**: `grep -rn "PatchChips\|patch_face_counts\|writeAllFields\|allTopology" ui/frontend/src/ ui/backend/services/`:
- `MeshQualityCard.tsx:279` `PatchChips` component — currently consumes only `patch_face_counts`, renders neutral grey
- `schemas.py:106` V122 base has `patch_face_counts: dict[str, int]`
- No prior `-writeAllFields` / `-allTopology` invocation, no per-cell aggregation infrastructure

**Disposition: extend** — single-file edit on `MeshQualityCard.tsx` PatchChips component. Pass through `MeshQualityReport` (or relevant fields) + derive tone per chip. NO modification to api/client.ts, no schema change, no backend touch.

## V1 scope (deliberately narrow per V123 §L1)

V128 R0 ships:

1. **`PatchChips` props extended** (~30 LOC delta): pass either the full report or the relevant signals (mesh_ok, report_kind) alongside the existing patch_face_counts
2. **Per-chip tone derivation** based on already-fetched data:
   - `patch_face_counts[name] === 0` → tone="rose" (degenerate patch — zero faces is always wrong)
   - V126 `checkmesh_mesh_ok === false` AND face_count > 0 → tone="amber" (mesh fails globally; this patch may or may not be implicated, but it's worth the engineer's attention)
   - V126 `checkmesh_mesh_ok === true` → tone="green" (mesh passes globally; per-patch quality unknown but no signal of trouble)
   - V126 `checkmesh_mesh_ok === null` (graceful degrade) OR V122 fallback → tone="neutral" (existing grey behavior preserved)
3. **a11y reinforcement**: chips with non-neutral tone carry an explicit text label (e.g. " · empty" for zero-face) so color-blind users get the same signal
4. **Tests** (~4 new scenarios in `MeshQualityCard.test.tsx`):
   - V126 mesh_ok=true → all chips green
   - V126 mesh_ok=false + nonzero faces → all chips amber
   - V126 mesh_ok=true + a zero-face patch → that chip rose, others green
   - V122 fallback → all chips neutral (regression guard for existing behavior)

## Out of scope (deferred to V129)

- Cell-level per-patch metrics from `-writeAllFields` field files (cellSkewness / nonOrthoAngle / cellAspectRatio per cell, mapped to patches via owner+boundary, aggregated per patch)
- Per-patch severe-non-ortho face count from `-allGeometry` face-id list
- Backend schema extension with per-patch quality fields
- 3D viewport per-cell coloring (Phase E v2 separate DEC)

V128 R0 is intentionally a **derive-from-existing-data** cut. V129 will pursue the heavy backend path once V128's signal proves useful enough in dogfood to warrant the extra Docker round-trip cost.

## Risk register

1. **a11y**: tone-only signal must be paired with text differentiator on each non-neutral chip (rose has explicit "empty" suffix; amber and green can rely on the text bg+border + tooltip combo since they don't change the WORD content, only the color, and contrast is sufficient — but I'll lean toward explicit text labels to be safe)
2. **stale-data tooltip**: chip tone reflects the LAST fetched checkmesh_mesh_ok; if a mesh mutation happens but the cache hasn't busted yet, color could be stale. R0 leans on V127 R4-R7's hardened `mesh:mutated` plumbing — every polyMesh-mutation path now busts the cache, so this risk is contained to the gap between mutation and re-fetch (~100-300ms typical).
3. **regression on V122-only path**: must not break the grey-chip behavior for cases without checkMesh; explicit test scenario covers this

## Acceptance criteria

- Vitest unit tests pass (existing 19 + 4 new = 23)
- Backend regression: untouched (no backend change)
- OpenAPI surface: untouched
- Visual smoke: in dev server, navigate to a meshed case → Step 2 → confirm chips colored per the rules above
- Codex review APPROVE
