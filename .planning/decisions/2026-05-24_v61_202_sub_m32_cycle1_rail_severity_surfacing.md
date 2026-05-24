---
decision_id: DEC-V61-202-SUB-M32-CYCLE1-RAIL-SEVERITY-SURFACING
title: M3.2 cycle 1 — surface rail severity to frontend (critical vs warning vs info visual treatment)
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (1 P2 audit_v2 provenance log scrapes severity string instead of new field) → R1 APPROVE ("I did not identify an actionable correctness issue")
final_commit: c91ae09
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.2 cycle 1 (workbench frontend · severity surfacing)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
user_ratification: 2026-05-24 AskUserQuestion — "M3.2 workbench frontend"
predecessors:
  - DEC-V61-202-SUB-M31-CYCLE7-CORRUPTED-MANIFEST-RAIL  # produces critical info_gap
  - DEC-V61-202-SUB-M31-CYCLE8-PATCH-TYPE-ENUM-WARNING  # produces info info_gap
---

## Why

M3.1 added two new severity classes to info_gap rails:
- **Critical info_gap** (cycle 7): corrupted-manifest detector surfaces
  `kind=info_gap` with `gap.severity=critical` + `cta.enabled=false`.
- **Info info_gap** (cycle 8): unknown-`patch_type` warnings surface
  `kind=info_gap` with `gap.severity=info` + `cta.enabled=true`.

Frontend probe (post-M3.1):
- `DynamicFramePanel.KIND_TONE` maps by `rail.kind` only — all
  `info_gap` rails get the same amber "待补充" pill.
- `RailPrimary` schema has NO `severity` field — gap severity is
  encoded only in the `provenance` string (`"...severity=critical"`),
  which the frontend doesn't parse.
- Engineer cannot visually distinguish a critical corruption warning
  from a soft typo warning. Both look like "待补充 / fill in this
  field" — same urgency, same recommended action.

UX consequence: the visual hierarchy doesn't match the decision-
priority hierarchy. A corruption-class rail (block proceed, fix
required) shouldn't look like a typo-class rail (advisory, can
ignore).

## What

### In scope

1. **Backend schema**: add `severity: Severity = "info"` to
   `RailPrimary` in `ui/backend/schemas/workbench_frame.py`. Default
   "info" preserves existing test fixtures (step_default rails stay
   "info"; problem_fix rails will get explicit severity).

2. **Backend population**: extend `_rail_from_problem` and
   `_rail_from_gap` in `ui/backend/services/workbench_decide.py` to
   pass through `_normalize_severity(severity)` (existing helper
   maps `"critical"→"fail"`, `"warning"→"warn"`, etc). `_rail_default`
   keeps the default "info" (no blockers = no severity signal).

3. **Frontend rendering**: extend `DynamicFramePanel`'s `KIND_TONE`
   into a 2D map `[kind][severity]`. For `kind=info_gap`:
   - `severity=fail` → rose tone + "需立即修复 / Fix now" label
   - `severity=warn` → amber tone + "待补充 / Fill in" label (current)
   - `severity=info` → sky/blue tone + "建议 / Suggestion" label
   For other kinds, severity-collapse to existing tone (problem_fix
   always rose, step_default always emerald). Backward-compatible.

4. **Backend tests** in
   `ui/backend/tests/test_workbench_decide_rail_severity.py`:
   - `_rail_from_gap` with critical gap → rail.severity = "fail"
   - `_rail_from_gap` with warning gap → rail.severity = "warn"
   - `_rail_from_gap` with info gap → rail.severity = "info"
   - `_rail_from_problem` with fail-class audit problem → rail.severity = "fail"
   - `_rail_default` → rail.severity = "info"
   - Integration: M3.1-cycle-7 corrupted-manifest case → rail.severity = "fail"
   - Integration: M3.1-cycle-8 typo case → rail.severity = "info"

5. **Frontend tests** in
   `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/__tests__/DynamicFramePanel.test.tsx`:
   - New test cases asserting severity-distinct tone classes for
     each (kind × severity) combo. Builds on existing fixture pattern.

### Out of scope

- **Inline action affordance for critical rails** (e.g. "click here to
  view raw YAML") — cycle 2+ frontend
- **Animated transitions on severity change** — cosmetic, cycle N+
- **Severity-driven sort within bottom_cards** — already exists; not
  touched here. RailPrimary is the focus.
- **Backend audit log new field** (severity is already in provenance) —
  cycle 8 retro queue item, not this cycle.

## Closure criteria

- [ ] `RailPrimary.severity` field added
- [ ] `_rail_from_gap` + `_rail_from_problem` populate it
- [ ] Backend unit tests pass (7 new + 0 regressions)
- [ ] Frontend tests pass (3 new + 0 regressions for tone variants)
- [ ] M3.1 cycle 7 + cycle 8 dogfood still PASS (no behavioral
      change to corruption / typo detection — only visual)
- [ ] Codex review ≤ 3 rounds → APPROVE (or user-ratified close)
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Adding a new optional field breaks frontend type-checking | Field has default "info" — backward-compatible. Frontend `RailPrimary` type re-generates via tsx codegen / matches the optional default. |
| Engineer confusion if all 3 info_gap colors fire on different cases at the same time | Decision tree picks ONE rail (priority order); multiple gaps' visual mix only appears in bottom_cards, which already has severity colors. Rail at any moment = 1 color. |
| Sky/blue tone clashes with existing UI palette | Inherit from project color tokens; if clash, swap to a neutral surface tone. |
| Severity mapping `critical → fail` confuses readers vs source vocabulary | Maintain the existing `_normalize_severity` helper. Frontend reads only the `Severity = "fail" / "warn" / "info"` vocabulary. Backend / analyzer continue to use `"critical" / "warning" / "info"`. Only the rail surface is normalized. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Surfaced by: M3.1 phase-close retro + post-cycle-7/8 frontend probe
  (DynamicFramePanel rendering audit)
- User ratification 2026-05-24: "M3.2 workbench frontend"
- User mandate 2026-05-24: 持续开发, 瞄准里程碑

Surface-scan-found:
- `ui/backend/schemas/workbench_frame.py:class RailPrimary` (line 37):
  no severity field. disposition: extend in-place.
- `ui/backend/services/workbench_decide.py:_rail_from_gap` (line 405):
  severity computed but not passed to RailPrimary. disposition:
  pass through.
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx`
  KIND_TONE (line 40): kind-only map. disposition: extend to 2D.
