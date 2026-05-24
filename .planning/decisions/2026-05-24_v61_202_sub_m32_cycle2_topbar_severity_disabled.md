---
decision_id: DEC-V61-202-SUB-M32-CYCLE2-TOPBAR-SEVERITY-DISABLED
title: M3.2 cycle 2 — severity-aware TopbarCta disabled state
status: Accepted
proposed_date: 2026-05-24
accepted_date: 2026-05-24
codex_review_arc: R0 (1 P1 V4 live mount missing railSeverity prop) → R1 APPROVE ("correctly threads railSeverity into the V4 mount, regression test covers known production call sites")
final_commit: 7a6737e
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.2 cycle 2 (workbench frontend · CTA severity)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M32-CYCLE1-RAIL-SEVERITY-SURFACING  # adds severity field
---

## Why

M3.2 cycle 1 added `RailPrimary.severity` and made the rail's pill
visually distinct (rose/amber/sky) for each urgency. But the topbar
CTA (the engineer's "Next step" / "Submit" button) keeps a uniform
grey disabled state regardless of WHY it's disabled:
- Disabled because manifest is corrupted (must fix) → grey
- Disabled because case_family is unset (recommended to fill) → grey
- Disabled because a low-priority typo warning fired → grey

This hides the criticality signal the rail just surfaced. Engineer
must look at the rail separately to understand urgency. The disabled
CTA should mirror the rail's severity so visual hierarchy is
coherent: same hue family, muted (grey-shifted) for disabled.

## What

### In scope

1. **New `railSeverity?: FrameSeverity` prop** on `DynamicTopbarCta`.
   Optional with default "info" preserves legacy mounts (any caller
   that doesn't pass it gets the existing sky-grey behavior).

2. **`DISABLED_CLASS_BY_SEVERITY` table** mapping each severity to a
   muted version of the corresponding rail hue:
   - `fail` → rose-grey (`border-rose-800/60 bg-rose-950/40 text-rose-500/70`)
   - `warn` → amber-grey (`border-amber-800/60 bg-amber-950/40 text-amber-500/70`)
   - `info` → sky-grey (preserves existing visual)

3. **`data-rail-severity` attribute** on the rendered button for
   test-driver / DOM-query convenience.

4. **Enabled state unchanged**: when CTA is enabled, kind-driven tone
   still wins (a "submit_solve" button is always emerald-green when
   live, regardless of rail severity — that's the action semantic,
   not the rail severity).

5. **Parent wiring**: `StepPanelShell` passes
   `railSeverity={dynamicFrame.rail_primary.severity}` to the mount.

6. **Tests** in `DynamicTopbarCta.test.tsx`:
   - disabled + railSeverity=fail → rose tone classes present
   - disabled + railSeverity=warn → amber tone classes present
   - disabled + no prop → defaults to "info"/sky (legacy)
   - enabled state ignores railSeverity (kind tone wins)

### Out of scope

- Severity-aware re_audit / submit_solve KIND_TONE.enabled colors
  (those carry their own action semantic). Only disabled state
  inherits rail severity.
- Animated transitions when severity changes.
- Tooltip text changes — the `cta.reason` from backend already
  carries the "why disabled" string.

## Closure criteria

- [x] `railSeverity` prop added with sensible default
- [x] `DISABLED_CLASS_BY_SEVERITY` table populated
- [x] `data-rail-severity` attribute on button
- [x] StepPanelShell passes the prop
- [x] 4 new vitest cases pass (fail / warn / default / enabled-ignores)
- [x] 925/925 full frontend regression pass
- [ ] Codex review ≤ 3 rounds → APPROVE
- [ ] DEC final_commit set
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Other DynamicTopbarCta mounts break because prop is required | Prop is optional with default "info" — backward-compatible. |
| The muted-color choices clash with the existing UI palette | All three colors (rose / amber / sky) are already in use via the `*-900/40` saturated variants for the rail; the muted `*-950/40` versions are within the same Tailwind token family. |
| Engineer interprets "rose-grey CTA" as "active button" rather than "disabled" | Combined signal: `disabled` attribute + `aria-disabled` + `cursor-not-allowed` + reduced text opacity (`text-X-500/70`). The hue conveys urgency, the muting conveys "can't act". |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md`
- Predecessor: cycle 1 added `RailPrimary.severity`
- User mandate 2026-05-24: 持续开发, M3.2 workbench frontend

Surface-scan-found: `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicTopbarCta.tsx`
KIND_TONE only has `enabled` variants; disabled state was hardcoded
single string. Disposition: extend with severity-aware disabled
mapping. No parallel-new component.
