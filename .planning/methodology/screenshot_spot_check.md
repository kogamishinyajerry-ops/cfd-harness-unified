# Workbench visual spot-check methodology · 2026-05-25

> Established: 2026-05-25 (M3.3 cycle 1 → cycle 2 transition)
> Triggered by: M3.2 cycles 4-5 shipped without visual verification (icons too small, toast edge-clipped, body button position weird) — surfaced by user UX review at M3.3 cycle 1.
> Status: active rule for all M-track cycles touching frontend.

## The rule

For every M-track cycle (M3.X cycle N) that touches workbench UI (any file under ui/frontend/src/pages/workbench/), the cycle's CLOSING commit body MUST reference at least one screenshot taken during the cycle's review phase. The screenshot does not need to be committed — referencing the absolute path of a PNG under /tmp or another non-tracked location is sufficient.

## What "touches workbench UI" means

Touched if the cycle modifies, adds, or deletes any of:
- `ui/frontend/src/pages/workbench/**/*.tsx`
- `ui/frontend/src/types/workbench_*.ts`
- backend route/schema that changes the shape of any rail, frame, or topbar CTA the workbench renders

NOT touched if the cycle is:
- pure test changes (Vitest, Playwright spec authoring)
- backend-only with no frontend-visible delta
- pure documentation

## How to run the spot-check

```
# from repo root
cd ui/frontend
node ../../scripts/dogfood/workbench_visual_spot_check.mjs --case-id m33_ux_demo_seed --step geometry
```

The tool writes 4 PNGs to `/tmp/cfd_workbench_screenshots/`. Open them in Preview/Quick Look. Look for:
1. Layout proportions (does the rail look right against the rest of the screen?)
2. Icon/button discoverability (can you find the cycle's new affordance without zooming in?)
3. Toast / popover positioning (is the feedback visible? clipped?)
4. Contrast (does text against backgrounds meet ~AA-ish? eyeball is fine)
5. Unintended visual changes elsewhere in the panel

If any of (1)-(5) feels off, FILE an entry in `.planning/backlog/` referencing the screenshot.

## When to extend the tool

If you need to spot-check a route other than `/workbench/case/:id?step=geometry`, extend the tool's CLI flags. Do NOT inline new URLs in the cycle's commit body.

## How this complements existing testing

| Layer | What it asserts | Used when |
|---|---|---|
| Vitest unit tests | testid presence, click semantics, state machine | every cycle's TDD loop |
| Playwright E2E | testid presence in real backend integration, toast appearance, clipboard interaction | dogfood cycles |
| **Visual spot-check** | layout, proportions, contrast, discoverability | every UI cycle's close |
| Manual UX session | engineer's holistic feel — does the affordance fit the workflow | milestone-close or major release |

Visual spot-check is the cheapest defense against the failure mode that surfaced M3.2 → M3.3: "tests pass but UI looks broken".

## Future enhancement candidates (not currently in scope)

- Snapshot diff testing against a baseline PNG (would require committing baselines)
- Lighthouse / axe-core accessibility audit
- Multi-viewport screenshots (mobile, narrow desktop)
- Automated contrast-ratio check via headless chromium DevTools API
