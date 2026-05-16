# V67-C Visual Baseline Directory

Playwright screenshot baselines + visual diff anchors for the
workbench shell. Populated by `e2e/*.spec.ts` runs using
`expect(page).toHaveScreenshot()` (Playwright's pixel-diff API).

Files live under:
- `chromium/*-snapshots/` — per-browser baseline PNGs (auto-generated)

To regenerate baselines after intentional UI change:
```bash
cd ui/frontend
npx playwright test --update-snapshots
```

Score_visualization fleet agent verifies the directory exists +
spec files are runnable. Diff threshold is per-test via
`expect(page).toHaveScreenshot({ maxDiffPixels: N })`.

— V67-C.4 (B123)
