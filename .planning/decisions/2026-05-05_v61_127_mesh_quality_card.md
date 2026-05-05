---
decision_id: DEC-V61-127
title: Mesh-quality card · Fluent-style gauges + per-patch chips · Phase E shell entry
status: Proposed (2026-05-05 · pre-implementation surface scan complete; Codex pre-merge MANDATORY per RETRO-V61-001 multi-file frontend + UI interaction mode change + first user-visible Fluent-style polish)
codex_tool_report_path: reports/codex_tool_reports/v61_127_r1_chain.md (to be created)
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline per RETRO-V61-001)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-05
authored_under: User 2026-05-05 mandate "按你的顺序和建议，继续推进" — Phase A closed at V126 with checkMesh metrics flowing to the AI but NOT yet to the engineer's eyes. V127 is the first deliberately-Fluent-styled UI element; doubles as Phase E (Fluent shell UX) shell entry. Per V123 §L1 lesson, this DEC is **no-cross**: pure frontend extension of existing Step2Mesh + new sibling component, no backend, no new contract. Predicted 3 rounds.
parent_decisions:
  - DEC-V61-126 (Docker checkMesh integration · V127 surfaces V126's checkmesh_* fields visually; relies on existing GET /api/cases/{id}/mesh-quality?run_checkmesh=true contract)
  - DEC-V61-122 (mesh-quality adviser foundation · V127 also surfaces V122 fields when checkMesh unavailable for graceful degradation)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file frontend + UI interaction mode + first user-visible polish triggers Codex pre-merge)
parent_artifacts:
  - ui/frontend/src/pages/workbench/step_panel_shell/steps/Step2Mesh.tsx (existing post-mesh success card; V127 mounts MeshQualityCard sibling under it)
  - ui/backend/services/mesh_quality/schemas.py (V126 MeshQualityReportV126 carries the fields V127 reads; no schema change)
  - ui/frontend/src/api/client.ts (existing api.getMeshQuality call; V127 adds run_checkmesh=true variant)
  - ui/frontend/src/visualization/Viewport.tsx (existing 3D viewport · V127 R0 does NOT touch this; Phase E v2 will add per-cell coloring on the polyMesh boundary surface in a separate DEC)
counter_impact: +1 (autonomous_governance: true · new top-level frontend component + UI interaction polish + first Fluent-style visualization. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter ≥ 20 (deferred per ongoing user mandate), not governance-rule change. Codex pre-merge MANDATORY per RETRO-V61-001 (multi-file frontend + UI interaction mode change + first user-visible polish).)
notion_sync_status: synced 2026-05-05 (https://www.notion.so/DEC-V61-127-Mesh-quality-card-Fluent-style-gauges-per-patch-chips-Phase-E-shell-entry-357c68942bed8191a660e8deaf6e43a0)
self_estimated_pass_rate: 70% (predicted 3 rounds · §L1 no-cross-contract baseline. V126 R6 APPROVE clean datapoint shows base review surfaces frontend issues fast — base-review-2 P2 + base-review-3 P1 + base-review-4 P2 + base-review-5 P2 #1 all caught frontend stale-state / streaming gap issues. V127 is bounded surface, but Codex tends to find color-blindness / a11y / hover-state edge cases on novel UI components. Honest 70% — V125 §L1 calibration baseline doubly held (V124+V125 = 3 rounds each), V127 should land in the same band.)

---

# DEC-V61-127 · Mesh-quality card · Fluent-style gauges + per-patch chips

## Why now

Phase A (Meshing 三明治 · V120-V126) is technically closed: AI sees real OpenFOAM checkMesh data, can propose mesh changes, the engineer can Accept proposals. But there's still a critical gap — **the engineer doesn't see the checkMesh data**. Step 2 only shows cell/face/point counts and a generation-time stat. There's no "is my mesh good enough" visual signal of the kind Fluent and StarCCM put front-and-center.

V127 closes that gap with the first deliberately-Fluent-styled UI element in the workbench: a `MeshQualityCard` panel that shows max skewness, max non-orthogonality, max aspect ratio, mesh_ok verdict, and per-patch face counts as colored gauges + chips, with thresholds matching the Fluent reject/warning bands (0.95 / 70°/ 1000) and the typical k-ω SST convergence sensitivity bands (0.7 / 65° / 100).

This is Phase E (Fluent shell UX) shell entry. V127 R0 ships flat panel gauges only; the 3D-viewport-with-per-cell-coloring variant lands as Phase E v2 in a separate DEC after polyMesh surface extraction is wired (out of scope V127).

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: V127 maps directly to the user-stated endgame UX ("AI 智能化的简约智能风格的 Fluent/StarCCM ... 可视化的悬浮进度条，直观的感受到工作正在推进，也能知道哪些内容被AI检查过、智能优化过"). It's the first deliverable that puts **a visual signal on quality**, not just numbers.

**Existing-implementation grep**: `grep -rn "MeshQuality\|quality.*gauge\|skewness" ui/frontend/src/`:
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts` has `MeshQualityReport` types (V122 base) — V127 extends usage to the V126 extended type
- `ui/frontend/src/api/client.ts` has `getMeshQuality(case_id)` — V127 adds the `?run_checkmesh=true` query param variant
- No existing quality gauge / threshold-coloring component
- `Viewport.tsx` has highlight overlays (red/yellow) but no per-cell quality coloring

**Disposition: extend** — new sibling component (`MeshQualityCard.tsx`) mounted in `Step2Mesh.tsx` after the existing mesh-summary card. NO modification to the existing card or to Viewport. This preserves V126 R6's APPROVE'd surface and lets V127 land/iterate independently.

## V1 scope (deliberately narrow per V123 §L1)

V127 R0 ships:

1. **New `MeshQualityCard.tsx`** component (~250 LOC) under
   `ui/frontend/src/pages/workbench/step_panel_shell/`:
   - Fetches `GET /api/cases/{case_id}/mesh-quality?run_checkmesh=true` on mount and on parent `meshGenSeq` bump (when Step2Mesh re-runs the mesh)
   - Renders a colored summary card:
     - Top row: overall verdict pill — green "Mesh OK" / yellow "Mesh has warnings" (V122 only) / red "Failed N checks" (V126 mesh_ok=false) / gray "checkMesh skipped" (graceful degradation)
     - 4 quality gauges (horizontal bar, threshold-colored zones, current-value needle):
       * Skewness: green <0.5, yellow 0.5-0.7, orange 0.7-0.95, red >0.95 (Fluent reject)
       * Non-orthogonality (deg): green <45, yellow 45-65, orange 65-75, red >75
       * Aspect ratio: green <10, yellow 10-100, orange 100-1000, red >1000
       * Cell count: dense_mesh band > 5M shown in amber
     - Per-patch chip row: each patch_name with face count, colored neutral (V127 R0 all neutral; per-patch coloring lands in V128)
     - Failed-check list when mesh_ok=false: bullet list of the failed_checks strings from V126
2. **`Step2Mesh.tsx` mount**: append `<MeshQualityCard caseId={caseId} meshGenSeq={...} />` immediately after the existing `step2-mesh-success` card
3. **`api/client.ts` extension**: `getMeshQuality(case_id, { runCheckmesh })` — single function with optional kwarg; `runCheckmesh=false` is the V122 behavior, `runCheckmesh=true` invokes V126 path
4. **Tests**: Vitest unit tests for MeshQualityCard covering:
   - V122 fallback path (only V122 fields, "checkMesh skipped" badge)
   - V126 happy path (Mesh OK + green gauges)
   - V126 failure path (Mesh failed + red gauges + failed_checks list rendered)
   - Loading state
   - Error state (API 502/500)

## Out of scope (deferred to V128+)

- Per-patch quality coloring (needs cell-level checkMesh data — `-allTopology -allGeometry -writeAllFields` flag); V127 R0 colors gauges only, not patches
- 3D viewport per-cell coloring on the polyMesh boundary surface (Phase E v2)
- Hover-to-inspect on viewport with per-cell quality numbers (Phase E v2)
- Real-time quality re-fetch during a mesh-regenerate operation (V128)
- Animated gauges / transitions (visual polish post-functional)

## Risk register

1. **a11y**: gauge color must not be the only signal — need text labels for color-blind users (red gauge → also "FAIL" word badge)
2. **graceful degradation**: when V126 returns base shape (run_checkmesh=false or container down), gauges for checkmesh_* show "skipped" not zero
3. **mesh-stale**: card must re-fetch when Step 2 mesh regenerates (use existing meshGenSeq or similar trigger)
4. **loading flicker**: skeleton during fetch so the card doesn't pop in jarringly
5. **Fluent threshold copyright**: thresholds (0.95, 70°, 1000) are widely-published industry conventions, not Fluent IP — safe to reference

## Acceptance criteria

- Vitest unit tests pass (5 scenarios above)
- Backend regression: 1239 pass (no new failures; V127 doesn't touch backend)
- OpenAPI surface unchanged (V127 only consumes V126 contract)
- Visual smoke: in dev server, navigate to a meshed case → Step 2 → confirm card renders gauges, verdict pill, patch chips
- Codex review APPROVE
