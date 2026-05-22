# Dogfood · M3.0 integration · dynamic frame mounted in V4 shell

> **Cycle**: DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL
> **Date**: 2026-05-23
> **Surface under test**: WorkbenchShellV4 with M3.0 dynamic-frame slots wired in
> **Method**: Playwright e2e `e2e/m30-dynamic-frame.spec.ts` + manual route navigation
> **Verdict**: **PASS** · 3/3 e2e tests + 8/8 step-id translator unit tests

## Context

Cycle 5 mid-cycle discovered the M3.0 cycles 1-4 dynamic-frame frontend
was wired into `StepPanelShell` but the live route
`/workbench/case/:caseId` mounts `WorkbenchShellV4`. The dynamic
frame had been operationally unmounted on the live route since
cycle 1.

This integration sub-DEC mounted the 3 slot components + the
FacePickProvider into `WorkbenchShellV4`, with a step-id translator
bridging V4's 8-step pipeline (`import / geometry / mesh / physics
/ boundary / solver / post / doe`) to the backend's 5-step spine
(1..5).

## What landed

### Backend bridge — step_id_translator.ts (1 file · 8 LOC)

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

### V4 shell wiring — WorkbenchShellV4.tsx (modify)

- Wrap JSX root in `<FacePickProvider key={caseId}>` (per-case remount
  pattern from cycle 3 Codex R0 P1 fix)
- Mount `<FacePickUrlSync enabled={dynamicFrameEnabled} />` inside
  the provider
- Read `?legacy=1` from URL search params for opt-out
- Call `useWorkbenchFrame` with V4 step translated to backend step
- Inject `<DynamicTopbarCta />` next to `<TopBarV4 />` (right side)
- Inject `<DynamicFramePanel />` above `<RightPanelV4 />`
- Inject `<DynamicBottomCards />` above `<BottomBarV4 />`

CTA click handler reverse-maps backend step → V4 step so navigation
goes to the right V4 page.

### STLReader extension fix — stl_loader.ts (1 line)

`import vtkSTLReader from "@kitware/vtk.js/IO/Geometry/STLReader"` →
`import vtkSTLReader from "@kitware/vtk.js/IO/Geometry/STLReader.js"`

Vite handles either form; Node ESM (Playwright's static spec
loader) requires the `.js` suffix. Pre-existing issue not introduced
by M3.0; surfaced when cycle 5 added a dev route that pulled the
chain into Playwright's transformer. The fix is conservative — Vite
build still produces the same chunk shape.

### Playwright spec — e2e/m30-dynamic-frame.spec.ts (3 tests)

1. **Default navigation renders all 3 slots** —
   `/workbench/case/<seed>?step=boundary` shows `[data-testid="dynamic-frame-panel"]`,
   `[data-testid="dynamic-topbar-cta"]`, `[data-testid="dynamic-bottom-cards"]`
2. **?legacy=1 opts out** — `/workbench/case/<seed>?step=boundary&legacy=1`
   shows V4 shell without M3.0 slots
3. **?focus_patch=inlet deep-link** —
   `/workbench/case/<seed>?step=boundary&focus_patch=inlet`
   triggers a `workbench_frame` GET that carries `focus_patch=inlet`
   through to backend decide()

Seed case staged via Node `fs` in `beforeAll`:
`ui/backend/user_drafts/imported/m30_cycle5_e2e_seed/` with v2
imported-user manifest + bc_audit.json carrying a WARN.

## Reproduction

```bash
cd /Users/Zhuanz/Desktop/cfd-audit-merge/ui/frontend
npx playwright test e2e/m30-dynamic-frame.spec.ts
```

Expected output:
```
3 passed (~8s)
```

## Test coverage

- Unit: `v4StepToBackendStep` 8/8 mappings
- Unit: 360/360 step_panel_shell + handlers (no regression from V4 wrap)
- E2E: 3/3 dynamic-frame Playwright scenarios
- Build: `npm run build` clean (vite production build with .js suffix change)
- TypeScript: `npx tsc --noEmit` clean

## Verdict

The M3.0 milestone litmus path is now **reachable** — an engineer
visiting `/workbench/case/<id>` sees the dynamic frame slots
without needing any opt-in URL param. The litmus test (junior
engineer constructs case_007 in ≤30 min via the dynamic UI) can now
be exercised end-to-end. M3.0 cycle 7 (beginner test) can proceed.

confidence: high
