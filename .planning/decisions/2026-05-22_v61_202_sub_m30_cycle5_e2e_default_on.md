---
decision_id: DEC-V61-202-SUB-M30-CYCLE5-E2E-DEFAULT-ON
title: M3.0 cycle 5 — Playwright e2e (skipped) + flag flip + V4-integration discovery
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-23
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 5 (discovery + partial landings + integration sub-DEC spawn)
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
---

## Why

Cycles 1-4 closed the dynamic-frame loop via FastAPI TestClient
dogfoods. That covers the route + decide() contract but never proves
the **real frontend renders** the slots correctly when the workbench
loads in a browser. Cycle 5 closes the loop end-to-end with a
Playwright spec that runs the actual vite-served frontend against the
actual uvicorn-served backend (playwright.config.ts already spawns
both via `webServer`).

**MID-CYCLE DISCOVERY (2026-05-22, mid-cycle-5)**: while writing the
Playwright spec, found that `/workbench/case/:caseId` routes to
`WorkbenchShellV4`, NOT `StepPanelShell`. The M3.0 cycles 1-4
dynamic-frame frontend infrastructure (`FacePickUrlSync`,
`DynamicFramePanel`, `DynamicTopbarCta`, `DynamicBottomCards`,
all wired through StepPanelShell.tsx) is technically correct but
**operationally unmounted** — it never reaches a user on the live
workbench. The dogfoods that PASS via FastAPI TestClient work
because the backend endpoint is independent of frontend routing; the
frontend dynamic-frame components have been dead code on the live
route since cycle 1.

This is M3.0-blocking for the milestone litmus (junior engineer
constructs case_007 in ≤30 min via dynamic UI) — the dynamic UI
must be mounted on the route the engineer actually visits.

Cycle 5 pivots its scope accordingly:
1. **Add a dev route** `/workbench/dev/m30/:caseId` that mounts
   StepPanelShell with the full dynamic-frame infrastructure. This
   gets the cycle 5 e2e green and proves the technical plumbing.
2. **Spawn a sibling sub-DEC** `DEC-V61-202-SUB-M30-INTEGRATION` for
   the larger V4-integration work (translate V4 step IDs to backend
   1-5, mount the dynamic slots in V4's TopBar / RightPanel /
   BottomBar zones with proper styling). That work runs in parallel
   with cycle 6 (provenance) and lands before cycle 7 (beginner
   test).
3. **Default-on flag flip** stays in StepPanelShell as originally
   scoped — the file is the M3.0 reference implementation; flipping
   its default-on is a non-op for the live workbench but locks in
   the right behavior for anyone who mounts the shell.

## What

### In scope

**Frontend** (StepPanelShell.tsx):
- Replace `searchParams.get("dynamic_frame") === "1"` flag check with
  `searchParams.get("legacy") !== "1"` (default ON, opt out with
  `?legacy=1`).
- Rename the internal `dynamicFrameEnabled` to `dynamicFrameEnabled`
  (semantics unchanged; just the URL gate inverts).

**MSW handlers** (mocks/handlers.ts):
- Add `GET /api/cases/:caseId/workbench_frame` mock that returns a
  realistic WorkbenchFrame payload (rail_primary, viewport_overlays,
  bottom_cards, topbar_cta, state_sha, manifest_state_sha) so unit
  tests rendering StepPanelShell with the new default-on don't fail
  with network errors.
- Add `PATCH /api/cases/:caseId/manifest` mock for cycle 2 path.

**Dev route** (mid-cycle pivot · App.tsx):
- New route `/workbench/dev/m30/:caseId` → mounts `StepPanelShell`
  directly (bypassing V4 shell) so cycle 5 e2e has a stable target.

**Playwright e2e** (`e2e/m30-dynamic-frame.spec.ts`):
- Test 1: dynamic frame slots render on default navigation
  - `/workbench/dev/m30/<seed_case_id>?step=4` (no `?legacy=`)
  - Assert: `[data-testid="dynamic-frame-panel"]` visible
  - Assert: `[data-testid="dynamic-topbar-cta"]` visible
  - Assert: `[data-testid="dynamic-bottom-cards"]` visible
- Test 2: `?legacy=1` opts out
  - `/workbench/dev/m30/<seed_case_id>?step=4&legacy=1`
  - Assert: dynamic slots NOT visible
- Test 3: focus_patch deep link biases the frame
  - `/workbench/dev/m30/<seed_case_id>?step=4&focus_patch=inlet`
  - Assert: backend receives ?focus_patch=inlet on workbench_frame call

Seed case is filesystem-staged in `beforeAll` via Node `fs` directly
under `ui/backend/user_drafts/imported/m30_cycle5_e2e_seed/` (the
IMPORTED_DIR the dev backend reads from).

**Documentation**:
- Add `data-testid` attributes to DynamicFramePanel, DynamicTopbarCta,
  DynamicBottomCards (if not already present) so the Playwright spec
  has stable selectors.

### Out of scope (cycle 6+)

- Removing legacy code paths for `?legacy=1` (cycle 6 cleanup)
- vtk.js viewport pick → URL deep link via actual mouse click (cycle 4
  deferred this; cycle 5 covers the URL→backend round trip via deep
  link, not the pick→URL leg via real click)
- provenance audit_v2 file (cycle 6)
- M3.0 final beginner test (cycle 7)

## Closure criteria

- [x] StepPanelShell flips default-on (`?legacy=1` opt-out) — landed
- [x] MSW handlers cover workbench_frame + manifest PATCH endpoints — landed
- [x] Playwright spec template authored (covers 3 scenarios) — landed as `.skip`
- [ ] ~~`npx playwright test e2e/m30-dynamic-frame.spec.ts` passes~~ — DEFERRED to integration sub-DEC (no live route until V4 wires the slots; pre-existing stl_loader STLReader `.js` extension also blocks Playwright `--list`)
- [x] Existing test suite still passes (355/355 vitest green)
- [x] Mid-cycle discovery documented: dynamic frame is unmounted on the live `/workbench/case/:caseId` route (routes to `WorkbenchShellV4`, not `StepPanelShell`)
- [x] Sibling sub-DEC spawned: `DEC-V61-202-SUB-M30-INTEGRATION-V4-SHELL` — milestone-critical, between cycles 5 and 6
- [x] DEC Proposed → Accepted (this commit · honest scope reduction)
- [ ] Notion sync (session-end batch)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Flipping default-on breaks unrelated tests that render StepPanelShell without `?legacy=1` and don't have MSW workbench_frame handler | grep search confirms no current unit tests render StepPanelShell directly. New MSW handler covers any future test that mounts it. |
| Playwright spec is flaky due to vite/uvicorn cold-start timing | Use `await page.waitForResponse('**/api/cases/**/workbench_frame*')` to lock the assertion to after the query resolves, not a fixed timeout |
| `channel_flow_rans_sst` IMPORTED_DIR path may not be picked up by the dev backend | Verify locally; if the path doesn't resolve, fall back to a simpler stage via `notion_sync` skip or document the actual IMPORTED_DIR resolution in the test |
| Default-on changes the look of every page that mounts the workbench shell in this commit; user may want a release-train flag | Behavior is identical for completed cycles 1-3 — observers already saw it via `?dynamic_frame=1` on case_007. The flip is a UI gate change, not a new feature. |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §1 litmus
- Predecessors: cycles 1+2+3+4 (route/contract validated)
- Method backing: cycle 4 dogfood proves the API contract; cycle 5
  proves the browser renders it.
- User authorization 2026-05-22: "继续奔着里程碑"

Surface-scan-found: ui/frontend/src/pages/workbench/StepPanelShell.tsx · disposition: extend (flip flag polarity, no structural change)
