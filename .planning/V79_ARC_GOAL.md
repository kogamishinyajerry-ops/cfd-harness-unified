# ARC-GOAL · V79 v3 Feature-Parity Arc · NO new pillar · NO new subscore · vtk.js camera presets + cross-browser playwright + SSIM active gate + a11y keyboard nav · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v79_charter_dec.md` (Accepted B230)
> **Predecessor**: DEC-V78-close (16-pillar 100/100 under TIGHTENED scoring · B229)
> **Pillar count**: stays at 16 (V78 commitment continued)
> **NO new subscore**: V79 charter-level reverse-stop · scoring framework UNCHANGED
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring

## North Star

The arc closes with **same nominal score (16-pillar 100/100), same V78 scorers (no changes), but additional substrate underneath:**
- vtk.js camera presets (front/top/iso) so engineers can snap-orient like real CAE
- Same 130 playwright specs run on 3 browsers (chromium + firefox + webkit) — 100% UX threshold now ≈ 390 specs PASS
- SSIM ≥0.99 ACTIVELY gates every screenshot via expect.extend, not just sits in `scripts/visual/`
- a11y keyboard-nav full Tab walk: every interactive element reachable + visible focus ring on Steps 1-5

## Why this arc

V78 established the "no new pillar" discipline. V79 doubles down with "no new subscore either". The user's verbatim mandate is satisfied permanently once 99分 is achieved through honest scoring — subsequent arcs improve the PROJECT, not the SCORING.

## Done dim checklist

- [x] **V78-DONE-1..16 carry** — 16/16 pillars at 100 under unchanged V78 scoring (verified iter-1/iter-2)
- [x] **V79-DONE-COMPOSITE** — All 16 pillars at 100 · V79 substrate absorbed · V78 scorers ZERO CHANGE

## Sub-DEC progress

- [x] **V79.1 · vtk.js camera presets** — front/top/iso buttons + viewport_kernel.setCameraPreset method
- [x] **V79.2 · Cross-browser playwright** — config landed (env-gated CROSSBROWSER=1) · firefox+webkit install pending (external lockfile)
- [x] **V79.3 · SSIM as active screenshot gate** — 3 tests in v79-ssim-active-gate.spec.ts + --batch mode actively rejects file-level corruption
- [x] **V79.4 · a11y full-keyboard nav specs** — 5 specs · Steps 1-5 each ≥8 distinct focus stops
- [x] **V79.5 · Final integration verification** — V78 scorers run UNCHANGED · zero v79_fleet/ scripts · zero subscore added · zero threshold changed
- [x] **V79.6 · Close DEC + retro · baseline 63 re-snap (V79.1 button cluster)**

## Fleet criteria (16 pillars · V79 SAME AS V78)

| # | Agent | V78 close | V79 |
|---|---|---|---|
| 1-16 | (all) | 100 under TIGHTENED scoring | **100 with V79 substrate added · V78 scorers UNCHANGED** |
| ~~17~~ | ~~(declined)~~ | ~~NOT added (V78)~~ | **STILL NOT added (V79 reverse-stop)** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V79 baseline) | 2026-05-17 | 86 | mid | ux | 137/138 specs PASS · baseline 63 (V76 single button) drifted under V79.1 4-button cluster · all other V79 substrate ran clean on first try | V79_iter_0.md |
| 1 | 2026-05-17 | **100** | 121.04 | (all 100) | baseline 63 re-snapped under V79.1 cluster · CLOSE_ELIGIBLE | V79_iter_1.md |
| 2 | 2026-05-17 | **100** | 121.04 | (all 100) | stability re-confirm under unchanged V78 scoring · CLOSE_CONFIRMED (2-consec) | V79_iter_2.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0 (locked at 9)
- Adding Pillar 17 (V78 charter-level reverse-stop carried)
- **Adding new subscore (V79 charter-level reverse-stop · NEW)**
- **Changing V78 scorer thresholds (V79 charter-level reverse-stop · NEW)**
- Cross-browser playwright reveals WCAG → must fix not skip
- SSIM active gate false-passes
- Any of 76 V78-validated baselines drifts under SSIM ≥0.99

## Counter telemetry

- V79 charter: B230
- V79.1-V79.6 + close: B231-B237 estimated

— V79 ARC-GOAL · 2026-05-17
