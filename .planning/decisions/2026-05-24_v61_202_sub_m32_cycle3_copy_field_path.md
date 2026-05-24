---
decision_id: DEC-V61-202-SUB-M32-CYCLE3-COPY-FIELD-PATH
title: M3.2 cycle 3 — clipboard button for rail field_path
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (1 P2 clipboard optional-chaining false-success) → R1 APPROVE ("clipboard availability guard fixes prior false-success path without introducing regression")
final_commit: 28951f1
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.2 cycle 3 (workbench frontend · engineer actionability)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M32-CYCLE1-RAIL-SEVERITY-SURFACING
  - DEC-V61-202-SUB-M32-CYCLE2-TOPBAR-SEVERITY-DISABLED
---

## Why

M3.2 cycles 1+2 made rail/CTA severity visible everywhere (rose/amber/
sky). Engineer can now SEE the urgency. But for critical rails
(e.g. corrupted manifest), the only "action" today is to manually
select the field_path text in the rail header and copy it. There's
no in-workbench button.

Smallest impactful engineer-action affordance: a 📋 button next to
the field_path display. Click → `navigator.clipboard.writeText` →
field_path on clipboard. Engineer pastes into their text editor,
terminal, or grep search.

Pattern intentionally tiny — first cycle of the M3.2 "engineer
actionability" thread. Cycle 4+ may add: "Open raw YAML" modal,
"Reveal in file system", "Reset to skeleton" recovery, etc.

## What

### In scope

1. **`CopyFieldPathButton` component** at the bottom of
   `DynamicFramePanel.tsx`:
   - Renders next to the existing `<code>` element in the rail header
   - 📋 default, ✓ for 1.5s after successful copy
   - `navigator.clipboard.writeText(fieldPath)` with try/catch
   - Graceful silent no-op if API unavailable / denied
   - `data-testid="dynamic-frame-copy-field-path"`,
     `data-copied={copied}` for tests
   - `aria-label` / `title` carry full Chinese/English context

2. **Conditional rendering**: only when `rail.field_path` is set
   (step_default rails don't have one → no button).

3. **Tests** (4 new in `DynamicFramePanel.test.tsx`):
   - Button present when field_path is set
   - Button absent when field_path is null (step_default)
   - Click writes field_path to clipboard + button text flips ✓
   - Permission-denied silently fails (button stays 📋, no crash)

### Out of scope

- **Toast notification** ("已复制 / Copied" floating message) —
  cycle 4+ if the icon-only feedback is insufficient
- **Copy `body_text` (full why message)** — cycle 4+; today's
  affordance is field_path only
- **Copy validation error reason from analyzer** — cycle 4+; same
  copy-action layer, different content
- **Open in IDE / "Reveal in Finder"** — cycle 5+, requires OS
  integration
- **Raw YAML viewer modal** — cycle 5+, requires backend YAML fetch
  route

## Closure criteria

- [x] `CopyFieldPathButton` component lands
- [x] Rendered conditionally on `rail.field_path` presence
- [x] 4 new vitest cases pass (presence / absence / click+copied /
      permission-denied)
- [x] 930/930 full frontend regression pass
- [ ] Codex review ≤ 3 rounds → APPROVE
- [ ] DEC final_commit set
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| `navigator.clipboard` is undefined in older browsers / non-HTTPS contexts | try/catch + silent degrade. Engineer can fall back to manual selection — no regression, just no upgrade. |
| Test mocks `navigator.clipboard` and leaks to other tests | Uses `Object.defineProperty(navigator, "clipboard", { configurable: true, value: ... })` per test. Vitest's per-test isolation handles the cleanup naturally. |
| 📋 emoji renders inconsistently across systems | Acceptable — title attribute carries the text "复制路径 / Copy path" for screen readers + hover. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- M3.2 cycle 1 + 2 made severity visible; cycle 3 opens the
  actionability thread
- User mandate 2026-05-24: 持续开发, M3.2 workbench frontend

Surface-scan-found: rail header at
`DynamicFramePanel.tsx:224` renders `<code>{rail.field_path}</code>`
inline with no copy affordance. Disposition: extend in-place with
sibling button + new helper component at file bottom.
