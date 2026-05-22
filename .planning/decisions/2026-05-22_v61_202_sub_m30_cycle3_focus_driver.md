---
decision_id: DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
title: M3.0 cycle 3 — focus_patch driver fully wired (URL sync + bottom_cards bias + rail.primary bias)
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-22
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 3 (focus driver · 4th SSOT driver fully load-bearing)
notion_sync_status: synced 2026-05-22 (https://www.notion.so/368c68942bed81ff9c4edbac25bf0f08)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE (display)
  - DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR (action loop closed)
codex_review:
  r0_commit: 9fb3d1a
  r0_relay: crs (effort=high)
  r0_verdict: CHANGES_REQUIRED (1 P1 + 2 P2)
  r0_findings:
    - "P1: FacePickProvider must be keyed by caseId (cross-case URL bleed)"
    - "P2-A: focus sort merges audit FAIL with completeness critical; missing_field bubbled above unrelated FAIL"
    - "P2-B: _collect_resolved_patches misses real bc_audit type_mismatches[].resolved_patch shape"
  r1_commit: 6151e7f
  r1_verdict: CHANGES_REQUIRED (1 P2; R0 P1 + P2-A closed)
  r1_findings:
    - "P2: _collect_resolved_patches scanned all sublists incl. successful matched/checked → false-positive focus match"
  r2_commit: db62f8b
  r2_verdict: CHANGES_REQUIRED (1 P2; R0 P2-B fully closed)
  r2_findings:
    - "P2: FAIL sublist whitelist missed value_missing / derived_mismatches / derived_missing"
  r3_commit: 638fed0
  r3_verdict: APPROVED (verbatim Codex P2 fix; cycle 3 review chain closed at round cap=3)
---

## Why

SSOT §3 names 4 UI-content drivers; cycle 1 wired 3 (step / problem /
info gap) and cycle 2 wired the 4th SSOT slot (topbar_cta). **focus**
(driver 4) has been a query-string parameter since cycle 1 but isn't
load-bearing yet:
- Engineer clicking a patch doesn't update the URL
- decide() only adds a corner-badge ViewportOverlay when focus is set;
  bottom_cards + rail.primary ignore focus entirely

Cycle 3 makes focus actually do something. Per SSOT §3:
> Engineer clicks "inlet" patch in viewport → rail auto-switches to
> inlet BC editor; advisor cards filtered to inlet-relevant.

Pre-implementation surface scan (V61-088):
- **Existing infrastructure**: `ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx`
  (DEC-V61-098) already publishes face-pick events from the Viewport
  including a `patchName: string` field. PickedFaceState doesn't yet
  STORE patchName, only the face_id + worldPosition.
- **Disposition: extend** — add patchName to PickedFaceState (1 line),
  subscribe from StepPanelShell, sync to URL.
- **bc_audit.json shape**: `patch_coverage_dimension.gaps_by_field`
  maps `{fieldname: [missing_patch1, ...]}` — the data structure for
  "which patches are involved in which gaps" already exists.

## What

### In scope

**Backend** (~150 LOC + tests):
- `services/workbench_decide.py`:
  - `_focus_matches(state, item)` helper: True iff `item` mentions
    `state.focus_patch`. Checks `field_path`, `body_text`, and the
    field-coverage gap shape (`patch_coverage_dimension.gaps_by_field`).
  - `_pick_bottom_cards()`: when `focus_patch` is set, prepend any
    cards matching the focus before non-matching ones. Cap at 8 still
    applies; focus-matched ones win the top slots.
  - `_pick_rail_primary()`: when a focus-matching FAIL problem exists
    in step-relevant problems, promote it ahead of the non-focused FAIL.
  - `_pick_overlays()`: when `focus_patch` is set + step=4 + bc_audit
    is present, add a focused-patch-context overlay surfacing the
    gap count for that patch.

**Frontend** (~100 LOC + tests):
- `step_panel_shell/FacePickContext.tsx`:
  - Add `patchName: string | null` to `PickedFaceState`
  - Update `useFacePickPublisher` to include patchName when setting picked state
- `pages/workbench/StepPanelShell.tsx`:
  - Subscribe to FacePick state. When `picked.patchName` changes,
    update URL `?focus_patch=<name>` (preserves other params).
  - When picked is cleared (set to null), remove `focus_patch` from URL.
- Tests: PickedFaceState includes patchName + URL sync triggers on pick.

**Dogfood**:
- `scripts/dogfood/case_007_cycle3_focus.py`: stage case with multi-
  patch bc_audit reporting missing-fields gaps per patch. Verify:
  - focus_patch="inlet" → bottom_cards top entries mention inlet
  - focus_patch=null → bottom_cards sorted by severity only (no patch bias)
  - focus_patch="inlet" + Step 4 + FAIL on inlet's field → rail.primary
    is the inlet problem, not a non-inlet FAIL

### Out of scope (defer)

- Full vtk.js 3D patch_highlight ring overlay (existing FacePickContext
  already paints picked face in Viewport; cycle 3 doesn't NEED ring
  paint — engineer gets spatial feedback via existing pick visualization)
- Horizontal multi-physics dogfood (cycle 4)
- Default-on `?dynamic_frame=1` (cycle 5)
- Browser e2e via Playwright (cycle 5)

## Closure criteria

- [x] Backend `_focus_matches` helper + integration into rail/cards/overlays (commit `30827bb`)
- [x] Backend tests 13 passing (9 R0 + 2 R1 regressions + 1 R2 regression covering 3 newly-supported FAIL sublists + 1 R1 false-positive guard)
- [x] Frontend PickedFaceState.patchName + URL sync (commit `9fb3d1a`)
- [x] Frontend tests 6/6 (publisher forwards patchName / URL writes on pick / URL clears on unpick / enabled=false safe / no churn on same patch / empty patchName → URL cleared)
- [x] case_007 dogfood **8/8 PASS** (`scripts/dogfood/case_007_cycle3_focus.py` + `.planning/dogfood/DOGFOOD_CASE_007_CYCLE3.md`)
- [x] Codex R0 CHANGES_REQUIRED (1 P1 + 2 P2) → R1 verbatim fix → R1 CHANGES_REQUIRED 1 P2 → R2 verbatim fix → R2 CHANGES_REQUIRED 1 P2 → R3 verbatim fix → **R3 APPROVED** (closed at round cap=3, verbatim chain)
- [x] DEC Proposed → Accepted (this commit)
- [x] Notion sync (https://www.notion.so/368c68942bed81ff9c4edbac25bf0f08)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| URL update on every patch-pick causes router churn | Debounce: only update URL if patchName actually changed; FacePickContext doesn't re-publish on no-op picks |
| focus_patch could be a synthetic / unrealizable patch name | decide() always falls back to step-default if focus matches nothing; no errors thrown |
| FacePickContext change breaks other consumers | patchName is optional in PickedFaceState (default null); existing consumers reading faceId/faceIds/worldPosition are unaffected |
| Frontend can deep-link with focus_patch in URL but no Viewport pick — focus_patch from URL → FacePickContext.picked = ??? | One-way only: pick → URL (not URL → pick). decide() reads URL directly; viewport just doesn't visually highlight if no pick happened. UX edge case for cycle 4 follow-up. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (Accepted 2026-05-22)
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §3 driver 4
- Predecessors: cycle 1 + 2 (display + action layers)
- Existing surface composed with: `step_panel_shell/FacePickContext.tsx` (DEC-V61-098)
  · `cfdtrust/audit/boundary_conditions.py` (`patch_coverage_dimension.gaps_by_field` shape)
- User authorization 2026-05-22: "按推荐继续...多agent团队持续工作" + "奔着里程碑"

Surface-scan-found: ui/frontend/src/pages/workbench/step_panel_shell/FacePickContext.tsx · disposition: extend (add patchName field, subscribe from StepPanelShell)
