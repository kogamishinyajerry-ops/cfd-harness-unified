---
decision_id: DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL
title: M3.0 integration — wire dynamic-frame slots into the live V4 workbench shell
status: Proposed
proposed_date: 2026-05-23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 integration (between cycles 5 and 6, milestone-critical)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
  - DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
  - DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
  - DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
  - DEC-V61-202-SUB-M30-CYCLE5-E2E-DEFAULT-ON
---

## Why

Cycle 5 disclosed mid-cycle that `/workbench/case/:caseId` routes to
`WorkbenchShellV4`, not `StepPanelShell`. The M3.0 cycles 1-5
dynamic-frame infrastructure (decide() backend + the 3 frontend
slots + FacePickUrlSync + manifest PATCH + topbar CTA) has been
operationally unmounted on the live workbench since cycle 1.

The M3.0 milestone litmus — **"junior engineer constructs case_007
KCS ship VOF in ≤30 minutes via the dynamic UI"** — is unreachable
until the dynamic-frame slots appear on the live V4 route. This
sub-DEC tracks the integration work as a milestone-critical sibling
of cycle 6 (provenance), to be completed before cycle 7 (beginner
test).

## What

### In scope

**Step ID translator** (`ui/frontend/src/pages/workbench/v4/step_id_translator.ts`):

V4 declares an 8-step pipeline (`import / geometry / mesh / physics /
boundary / solver / post / doe`); the backend `decide()` speaks the
5-step spine (1..5: Geometry, Mesh, Physics, BCs, Solve+Postp). Add
a pure mapping function:

```ts
export function v4StepToBackendStep(v4: V4PipelineStepId): 1 | 2 | 3 | 4 | 5 {
  switch (v4) {
    case "import":
    case "geometry": return 1;
    case "mesh":     return 2;
    case "physics":  return 3;
    case "boundary": return 4;
    case "solver":
    case "post":
    case "doe":      return 5;
  }
}
```

**WorkbenchShellV4 wrapper** (modify `WorkbenchShellV4.tsx`):

- Wrap the shell's JSX in `<FacePickProvider key={caseId}>`
- Inside the provider, mount `<FacePickUrlSync enabled={true} />`
- Add a `useWorkbenchFrame` call (passing `caseId` + the translated
  v4-step) inside the shell — the result drives the 3 slot components
- The 3 slot components mount inline within existing V4 zones:
  - `DynamicTopbarCta` injected into `TopBarV4` (or as a sibling
    just below TopBarV4)
  - `DynamicFramePanel` injected into `RightPanelV4` (top section
    above existing content)
  - `DynamicBottomCards` injected as a sibling above `BottomBarV4`

**STLReader extension fix** (`ui/frontend/src/visualization/stl_loader.ts`):

Pre-existing issue surfaced by cycle 5: `@kitware/vtk.js/IO/Geometry/STLReader`
lacks the `.js` suffix that Playwright's ESM resolver requires for
non-bundled walks. Vite handles it; Playwright's static spec loader
doesn't. Add `.js`. (Validate no Vite regression.)

This unblocks the Playwright spec template `m30-dynamic-frame.spec.ts`
that cycle 5 left in `.skip` state.

**Playwright spec resurrection** (`e2e/m30-dynamic-frame.spec.ts`):

Remove the `.skip` modifier. Update URLs to use the live route
`/workbench/case/<seed_case_id>?step=4`. Update selectors if any
zone wrapping changes the testid hierarchy.

**Dogfood report**:
`.planning/dogfood/DOGFOOD_M30_INTEGRATION_V4.md` — record before/after
screenshots (or DOM snapshots) showing the slots are now visible on
the live route.

### Out of scope (M3.1+)

- Visual polish of the integrated slots (M3.1 design pass)
- Removing `?legacy=1` (M3.1 cleanup)
- vtk.js viewport pick → focus_patch via real mouse click (cycle 6 / 7)
- StepPanelShell deletion (M3.1 — keep as reference impl until V4 is fully battle-tested)

## Closure criteria

- [ ] `v4StepToBackendStep` helper + unit tests
- [ ] `WorkbenchShellV4` wraps with `FacePickProvider` + `FacePickUrlSync`
- [ ] All 3 dynamic-frame slot components mount inside V4 zones
- [ ] Live route `/workbench/case/<id>` shows the slots when a real case is staged
- [ ] STLReader.js extension fix verified non-regressive in Vite
- [ ] Playwright spec un-skipped + passing
- [ ] Codex R0 APPROVED or CHANGES_REQUIRED closed ≤ 3 rounds
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| V4 layout is opinionated; M3.0 slots may clash visually | Inline-mount approach trades polish for reachability. M3.1 takes a design pass. |
| STLReader `.js` suffix breaks Vite production build | Test with `npm run build` before committing. Vite typically handles both; the fix is conservative. |
| V4 already has competing "rail" / "panel" concepts | Mount as siblings, not replacements. Engineers see both V4 chrome and M3.0 dynamic content side-by-side. |
| Step ID translator drops information (e.g., `post` → backend step 5 same as `solver`) | Acceptable: backend step 5 is "Solve + Postp" by design. `doe` mapping is best-effort; M3.0 litmus doesn't exercise DOE. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §1 litmus
- Triggered by: DEC-V61-202-SUB-M30-CYCLE5 mid-cycle discovery (2026-05-22)
- Method backing: cycle 4 dogfood proved backend contract; cycle 5
  proved the StepPanelShell-side frontend works; integration proves
  the V4-side frontend works.
- User authorization 2026-05-23: "继续奔着里程碑继续" (continuous milestone work)

Surface-scan-found: ui/frontend/src/pages/workbench/v4/WorkbenchShellV4.tsx · disposition: extend (wrap with provider + inject 3 slot components without restructuring V4)
