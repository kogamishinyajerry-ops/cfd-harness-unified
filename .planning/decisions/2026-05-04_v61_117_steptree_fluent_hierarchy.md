---
decision_id: DEC-V61-117
title: StepTree → Fluent-style hierarchical tree · expandable parent rows + indented sub-node labels
status: Proposed (awaiting Codex pre-merge review per RETRO-V61-001 multi-file-frontend trigger)
codex_tool_report_path: reports/codex_tool_reports/v61_117_r1_chain.md
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 design discussion — "对标Fluent、StarCCM，但是不需要过多的子菜单，因为这个项目是要给CFD工程师用的，作为一个新产品，不能傲慢的要求他们直接适应这个项目，而是这个项目应该先迎合他们的习惯、需求". Five-DEC arc plan A→C→B→D→E confirmed by user "全都按你的建议来"; this is item B — visual hierarchy refactor of the existing flat StepTree to match the canonical Fluent / Star-CCM+ tree-of-actions mental model CFD engineers carry across tools.
parent_decisions:
  - DEC-V61-096 (M-PANELS three-pane shell · this DEC refactors the StepTree component spec_v2 §A.5 introduced; left rail visual hierarchy is the change scope)
  - DEC-V61-115 (workbench-first default landing · this DEC adds visual sophistication to the rail that V61-115 raised the visibility of)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan-found trailer per §)
  - RETRO-V61-001 (risk-tier · multi-file frontend change + UI interaction-mode change = mandatory Codex pre-merge)
parent_artifacts:
  - .planning/strategic/m_panels_kickoff/brief_2026-04-28.md:39-65 (canonical Fluent/Star-CCM+ three-pane reference layout · "left rail: 5-step tree" was the Tier-A spec; this DEC adds hierarchy WITHIN that rail)
  - ui/frontend/src/pages/workbench/step_panel_shell/StepTree.tsx (refactor target · 89 LOC flat list → ~150 LOC hierarchical tree)
  - ui/frontend/src/pages/workbench/step_panel_shell/types.ts:218-243 (StepDef contract · adds optional subNodes[] field; existing fields unchanged)
  - ui/frontend/src/pages/workbench/StepPanelShell.tsx:111-230 (STEPS config · per-step subNodes[] declaration lands here)
  - ui/frontend/src/pages/workbench/step_panel_shell/__tests__/StepTree.test.tsx (existing 6-test contract MUST stay green; new tests added for expand/collapse + sub-node rendering)
counter_impact: +1 (autonomous_governance: true · UI hierarchy refactor on existing component, NOT a governance-rule change. Kogami-trigger check: not a phase-close, not a RETRO draft, not a high-risk PR (no irreversible state, no API contract change, no operator endpoint), not arc-size retro, not a governance rule-change DEC · Kogami SKIP per DEC-V61-087 §4.2. Codex pre-merge MANDATORY per RETRO-V61-001 multi-file frontend + UI interaction-mode change triggers.)
notion_sync_status: pending (queued for Codex APPROVE)

---

# DEC-V61-117 · StepTree Fluent-style hierarchy

## Why now

User feedback 2026-05-04 design-discussion turn (verbatim above). The current StepTree (`ui/frontend/src/pages/workbench/step_panel_shell/StepTree.tsx`) is a flat 5-row list — visually correct for skeleton (M-PANELS Tier-A), but **does not match the hierarchical-tree mental model** every CFD engineer carries from Fluent / Star-CCM+ / OpenFOAM-GUI / SU2-GUI. In those tools the left rail is a tree-of-actions: top-level node "Boundary Conditions" expands to per-patch nodes; "Solution Methods" expands to per-equation nodes; etc.

The refactor is the visual half of "迎合他们的习惯、需求" (accommodate their habits) — the engineer should recognize the layout convention before they read a single label. Without it, the workbench looks like a wizard from a different paradigm even though the underlying behavior matches Fluent (engineer-driven, no auto-advance, per-step `[AI 处理]`).

User also explicitly constrained scope: "**不需要过多的子菜单**" (don't need too many submenus). This DEC honors that — we add ONE level of sub-node hierarchy with 1-2 sub-labels per step where they're meaningful, not a full Fluent-depth tree.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: M-PANELS milestone is closed (DEC-V61-096 spec_v2 §E Step 3 landed the StepTree skeleton). No subsequent milestone re-spec'd the StepTree before this DEC. The five-DEC arc A→C→B→D→E (V61-115 → V61-116 → V61-117 → V61-118 → V61-119) is the post-M-PANELS workbench-UX refinement track per user 2026-05-04 mandate.

**Existing-implementation grep** (`grep -rin "StepTree" ui/frontend/src`):
- `ui/frontend/src/pages/workbench/step_panel_shell/StepTree.tsx` — refactor target
- `ui/frontend/src/pages/workbench/StepPanelShell.tsx` — sole consumer (lines 34, 472-478)
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/StepTree.test.tsx` — existing 6-test contract
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/StepPanelShell.test.tsx` — integration smoke
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts` — `StepDef.shortLabel/longLabel` consumers

**No competing pre-existing implementation found.** Refactor is in-place on the existing StepTree.tsx. Disposition: **extend existing** (no parallel-new file; the existing component absorbs the hierarchy via internal restructure).

## Decision

Refactor `StepTree.tsx` from a flat `<button>×5` list to a hierarchical tree where each parent step row optionally has a `subNodes[]` array of sub-labels rendered as indented children when the parent is expanded.

### Visual contract

```
▼ 1 · Import          ← active (expanded shows nothing — Step 1 has no sub-nodes)
▶ 2 · Mesh
▶ 3 · Setup
▶ 4 · Solve
▶ 5 · Results

(after clicking ▶ on step 3:)

▶ 1 · Import
▶ 2 · Mesh
▼ 3 · Setup
   • Annotations
   • BC patches
▶ 4 · Solve
▶ 5 · Results
```

- **Chevron** (`▶` collapsed / `▼` expanded) replaces the existing status dot's leading position. Status dot stays — it moves to align with the label, not the chevron.
- **Steps with no subNodes** (Step 1 in the M-PANELS spec) render WITHOUT a chevron (just a leading spacer to keep alignment).
- **Auto-expand**: the currently active step's row is expanded by default. User can also manually toggle other steps via chevron click (multi-expand allowed; matches Fluent).
- **Sub-nodes are visual labels only** in this V1 — they show "what's inside this step" as a roadmap. Click-to-anchor navigation is **explicitly out of scope** (deferred to a future DEC if the user signals it's needed; matches "不需要过多的子菜单" restraint).

### Sub-node config (one `subNodes[]` per step in `STEPS` config)

| Step | Sub-nodes | Source-of-truth |
|---|---|---|
| 1 · Import | (none) | Just an upload action; no decomposition needed |
| 2 · Mesh | `Mode`, `Quality` | Mesh-mode picker section + post-mesh stats block |
| 3 · Setup | `Annotations`, `BC patches` | AnnotationPanel + PatchClassificationPanel are pre-existing right-rail sections |
| 4 · Solve | `Run`, `Residuals` | Solve-streaming SSE block + LiveResidualChart in center pane |
| 5 · Results | `Fields`, `Report` | Step5ResultsGrid + report-bundle UI |

These names mirror the Fluent / Star-CCM+ canonical action vocabulary; they don't introduce new concepts the engineer hasn't seen.

### API contract changes

`types.ts::StepDef` gains one **optional** field:

```ts
export interface StepDef {
  /* ...existing fields unchanged... */
  subNodes?: readonly StepSubNode[];
}

export interface StepSubNode {
  id: string;          // stable id for data-testid; unique within parent step
  label: string;       // visible Fluent-style action label (e.g. "BC patches")
}
```

Existing `StepDef` fields and the existing `StepTree` props (`steps`, `currentStepId`, `stepStates`, `onStepClick`, `disabled`) are **unchanged**. The component's existing `data-testid="step-tree-row-${id}"` and `data-step-status` contracts on parent rows are **preserved** — every existing test in `StepTree.test.tsx` continues to pass.

New testable surface:
- `data-testid="step-tree-subnode-${parentId}-${subId}"` on each rendered sub-row
- `data-testid="step-tree-chevron-${parentId}"` on each chevron button
- `data-step-expanded="true|false"` on parent rows
- `data-step-has-subnodes="true|false"` on parent rows

### Out of scope (explicitly deferred)

- **Sub-node click navigation / scroll-to-anchor**: a future DEC can wire `?step=N&sub=X` URL state + `scrollIntoView` on `[data-subnode]` markers in TaskPanels. Not in V1 because (a) user said "don't need too many submenus", (b) the right-rail TaskPanels are mostly linear single-section bodies — anchors would add complexity without proportional UX gain, (c) keeps the diff small for the predicted 70%/2-3-round Codex window.
- **Engineer-customizable sub-nodes**: same deferral as engineer-customizable steps (DEC-V61-096 Tier-C / charter-future).
- **Sub-node status dots**: V1 sub-nodes are display-only text. If a future DEC introduces sub-node status (e.g. "BC patches: 3/5 classified"), it can be additive on the existing markup.

### Why this minimal-scope shape

Three guardrails:
1. **User constraint** — "不需要过多的子菜单" → don't over-engineer.
2. **Codex window** — predicted 70%/2-3-round (per arc retro RETRO-V61-V088-V116 anchor #6). Wider scope (URL routing, scroll-anchors, status sub-states) likely pushes into 4-6 rounds and risks cascading findings on routing semantics.
3. **Test contract preservation** — existing 6-test StepTree contract + StepPanelShell integration smoke must stay green. A pure visual-additive refactor minimizes regression surface.

The Fluent-mental-model 80% delivery is the visual hierarchy itself; the remaining 20% (clickable navigation) can land additively if the user requests it.

## Acceptance criteria

1. `StepTree.tsx` renders parent rows with chevrons for steps that have `subNodes[]`; clicking chevron toggles expansion (no step navigation triggered).
2. Currently active step is auto-expanded on first render and stays expanded as long as it remains active.
3. Sub-rows render with indentation, a leading bullet (`•`) marker, smaller font, and the existing surface-tone color hierarchy.
4. Existing `StepTree.test.tsx` 6 tests stay green without modification.
5. New tests cover: chevron click toggles expansion · sub-rows render only when parent expanded · auto-expand of active step · steps without subNodes render no chevron · sub-row data-testid format.
6. `StepPanelShell.test.tsx` integration smoke stays green.
7. `tsc --noEmit` clean. `pnpm vitest run` clean.
8. Codex pre-merge review APPROVE on 86gs `gpt-5.4` xhigh.
9. Surface-scan-found trailer applied per DEC-V61-088.

## Self-estimated pass rate

**70%** (per RETRO-V61-V088-V116 anchor #6: "UI hierarchy refactor on existing tested component, no API/state contract change, additive markup"). Expected 2-3 round chain. Most-likely Codex finding categories:

- (a) sub-node `id` uniqueness/stability — Codex may want explicit guarantee
- (b) chevron keyboard accessibility (Enter/Space toggle) — likely flagged as P2
- (c) auto-expand vs user-toggle precedence — Codex may probe the state machine: what if user collapses the active step manually?
- (d) ARIA tree role correctness — Codex may want `role="tree"` + `role="treeitem"` + `aria-expanded`
- (e) edge case: step changes while another step is manually expanded — should it stay expanded?

Anchor #6 sample (V61-115 · default landing flip) hit 70% prediction with 3-round actual, 2 of the 3 rounds catching exactly this kind of "did you think about regression in adjacent surfaces" cascade. Same expected here.

## Plan

1. Write DEC (this file). ✓
2. Update `types.ts`: add `StepSubNode` type, optional `subNodes` field on `StepDef`.
3. Update `STEPS` config in `StepPanelShell.tsx`: per-step `subNodes` arrays per the table above.
4. Refactor `StepTree.tsx`:
   - Track local `expanded: Set<StepId>` state, initialize from `currentStepId`
   - Auto-sync `expanded` to include `currentStepId` whenever it changes (additively — don't collapse manually-expanded others)
   - Render chevron + parent row + (when expanded) sub-rows
   - Preserve existing data-testid + data-step-status contracts
5. Update `StepTree.test.tsx`: add 5 new tests covering the criteria above; existing 6 stay unchanged.
6. Run `pnpm vitest run` + `pnpm tsc --noEmit` from `ui/frontend/`.
7. Codex round-1 via `codex-review-relay --uncommitted`.
8. Apply findings (round-2 / round-3 if needed).
9. Commit with `Codex-verified` trailer.
10. Sync to Notion.

## Risk register

- **R1 · State machine subtlety** — Auto-expand on step-change must NOT clobber the user's manual expand-state for other steps. Mitigation: Set-merge, not Set-replace, when stepId changes.
- **R2 · Test contract drift** — Adding new data-attrs to parent rows could collide with selector specificity in StepPanelShell.test.tsx. Mitigation: keep the existing `data-step-status="active|completed|..."` attribute exactly as-is; only add new attrs.
- **R3 · Visual regression on narrow viewports** — Sub-rows with extra indent could overflow the 11-rem rail. Mitigation: truncate sub-row labels with `text-overflow: ellipsis`, same pattern as parent rows.
- **R4 · ARIA tree semantics** — Switching from `<nav>` + `<button>` to a true ARIA tree (`role="tree"`) is a bigger lift; V1 keeps the existing `<nav>` semantic and uses `aria-expanded` on chevron buttons. Codex may push for full tree role — accept if asked, otherwise hold.

## Successor pointers

- DEC-V61-118 (item D · LLM provider integration) does NOT depend on this DEC's structural changes.
- DEC-V61-119 (item E · LLM-wrapped completeness coaching) MAY consume the sub-node anchors if the LLM's completeness suggestions need to deep-link into a specific TaskPanel section (e.g. "you still need to set BC patches" → click-through to Step 3 → BC patches sub-node). That deep-linking is the V1.1 follow-up if needed.
