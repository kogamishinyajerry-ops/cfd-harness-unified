---
decision_id: DEC-V61-202-SUB-M31-CYCLE2-UI-LABELER-SCALAR-INPUT
title: M3.1 cycle 2 — inline scalar input for case_family + future scalar gaps
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (2 findings) → R1 (2 findings) → R2 (1 finding) → R3 APPROVE
final_commit: aaade23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.1 cycle 2 (UI labeler form)
notion_sync_status: synced 2026-05-24 (https://www.notion.so/36ac68942bed812e8561fff43161124f)
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE1-FORM-HELPER-SHIPVOF  # cycle-1 R4 P1 deferred this work
---

## Why

Cycle 1 surfaces `case_family` as a Step-1 rail gap on interFoam imports
(per the demand-driven advisory), but the workbench has no UI affordance
to set it. The `DynamicFramePanel` renders only a disabled `编辑 / Edit`
button because the gap carries no `suggested_default` and no
`suggested_skeleton`. Engineers see the prompt and have no way to act
on it from the workbench UI — they must PATCH via the API directly.

Cycle 2 closes this gap with a **generic inline scalar input
affordance**: any rail that surfaces a `field_path` with no auto-apply
payload renders an `<input>` + Apply button so the engineer can type
the value and PATCH in one click. `case_family` is the first
user-visible surface; the affordance also applies to any future scalar
gap (e.g. an engineer-named override).

This pattern explicitly does NOT replace existing structural
affordances:
- `suggested_default` (scalar) → existing primary "Apply" button (unchanged)
- `suggested_skeleton` (dict) → existing secondary "Apply skeleton" button (unchanged)
- No payload → **NEW** inline input + "Apply" button (cycle 2)

## What

### In scope

1. **Frontend — DynamicFramePanel.tsx**: add inline-edit affordance.
   Render conditions (all required):
   - `rail.field_path` is set
   - `rail.suggested_default` is null/undefined
   - `rail.suggested_skeleton` is null/undefined
   - `caseId` + `manifestStateSha` are available (PATCH context)
   When all conditions hold, render `<input type="text">` +
   `应用 / Apply` button inside the panel. The original `编辑 / Edit`
   primary button (currently disabled) is suppressed when the inline
   affordance is rendered (no duplicate dead button — same shape as
   cycle 1's cta_label=null suppression for skeleton-only gaps).

2. **Frontend — apply flow**: reuses the existing `useManifestPatch`
   mutation with `value = inputState.trim()`. Same error handling as
   the scalar + skeleton flows (errorMsg state, validation_errors
   surfacing).

3. **Frontend — empty-input handling**: disable Apply button when
   trimmed input is empty (no PATCH with empty string). Whitespace-only
   values reject without a network call.

4. **Frontend — tests** (DynamicFramePanel.test.tsx):
   - renders inline input + Apply button when conditions met
   - omits original primary CTA button when inline affordance shows
   - input is disabled / Apply is hidden when caseId or sha missing
   - typing updates input value; Apply triggers PATCH with field_path + value
   - empty/whitespace-only input keeps Apply disabled

5. **TypeScript**: no schema change required — all conditions read
   from existing RailPrimary fields.

### Out of scope (later cycles)

- **Enum / dropdown picker** for case_family with known families.
  Cycle 2 ships free-text input; cycle 3 (or later) can add a select
  with `[ship_vof, rans_steady_incompressible, les_compressible, ...]`
  populated from `_SOLVER_TO_CASE_FAMILY_CANDIDATES` once that grows
  past 1-2 entries.
- **Type-aware input shapes** (numeric / boolean / array / dict). Cycle
  2 handles only string-typed scalar gaps. Numeric gaps remain on the
  existing `suggested_default` path (which already handles them via
  patch.mutate({ value: number })).
- **Multi-step undo / preview**. Engineer applies → manifest written.
  Cycle 3+ may add a "preview diff before commit" affordance.
- **Solver-source authority** — see cycle-1 DEC out-of-scope; punted
  to a separate cycle-2-or-3 design DEC.

## Closure criteria

- [ ] DynamicFramePanel.tsx implements inline input affordance
- [ ] 5 frontend tests added (per matrix above), all pass
- [ ] Existing 11/11 DynamicFramePanel tests still pass (no regressions)
- [ ] Full frontend regression PASS (905+ tests)
- [ ] Codex review ≤ 3 rounds (v2.3 cap)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end, Accepted DECs only)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Free-text input lets engineers type invalid values (e.g. "shipVof" typo) | Backend PATCH validation is the source of truth; invalid values produce 200+success=false+validation_errors, surfaced as errorMsg |
| Two CTAs (primary + inline-input Apply) visible at the same time confusing UX | Render conditions are mutually exclusive: inline-input fires ONLY when neither suggested_default nor suggested_skeleton exists |
| Engineer types case_family but the rail doesn't refresh post-PATCH | Existing manifest_state_sha invalidation already triggers refetch; mutation onSuccess clears errorMsg |
| Generic affordance fires for unintended fields (e.g. internal-only paths) | Cycle 2 limit: only top-level scalar gaps get this treatment by default. If a field shouldn't be editable, the analyzer shouldn't surface it on the rail with field_path set |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Cycle-1 DEC out-of-scope section explicitly named this work
- User authorization 2026-05-24 AskUserQuestion: "case_family UI labeler form"
- User standing mandate: "我批准你的多agent团队持续工作，奔着里程碑继续"

Surface-scan-found: `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx` ·
disposition: extend (add inline-edit affordance alongside existing
primary + skeleton CTAs); no parallel-new component, no rename, no break.
