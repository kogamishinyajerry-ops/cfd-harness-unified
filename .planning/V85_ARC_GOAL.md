# ARC-GOAL · V85 · V6 Blueprint Construction Arc · 21st V110 advisor-class · 8th consecutive no-scoring-change arc · **CLOSED 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v85_charter_dec.md` (Accepted B274)
> **Close DEC**: `.planning/decisions/2026-05-17_v85_close_dec.md` (Accepted B280)
> **Retro**: `.planning/retrospectives/2026-05-17_v85_retro.md`
> **Predecessor**: DEC-V84-close (V5 substantiated · 7-arc streak)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring (unchanged) · **MET (3-consec over-met)**

## North Star

V5 fully substantiated (V83 land + V84 depth). V85 lands **V6 = Real-Artifact Bridge** — V4/V5 demo surfaces can now display REAL OpenFOAM run artifacts (residuals · gold-delta · provenance hashes · run_id · audit-package URL) from existing `reports/{case_id}/runs/*/` via existing GET endpoints. READ-ONLY · zero new MUTATING_ROUTES · zero AI-triggered solver execution · V130/V132 invariants automatic.

## Done dim checklist

- [x] **V84-DONE-COMPOSITE carry** — 16/16 pillars at 100 under unchanged V78 scoring
- [x] **V85-DONE-COMPOSITE** — V6 blueprint LANDED with 4 contracts (V6.A-D) implemented + V78 scorers UNCHANGED still report 16-pillar 100/100

## Sub-DEC progress

- [x] **V85.1 · V6 blueprint document** — `.planning/blueprints/v6/INDEX.md` · 4 contracts + reverse-stops + 4Q gate · 179 lines · B275
- [x] **V85.2 · V6.A Bridge Reader** — `src/data/run_artifact_reader.ts` · pure data module · 180 LOC · 17 contract tests · B276
- [x] **V85.3 · V6.B Bridge-Mode Sandbox** — DemoSandboxV5 + `?bridge=1` + LIVE badge + 7 contract tests · B277
- [x] **V85.4 · V6.C Live-vs-Curated Diff Panel** — `LiveVsCuratedDiffV6` · 150 LOC · 12 contract tests · 3 divergence kinds · B278
- [x] **V85.5 · V6.D Bridge Truth-Gate Disclosure** — `BridgeModeShowcase` · 120 LOC · 11 contract tests · top-LEFT LIVE DATA pill · B279
- [x] **V85.6 · Final verification + close + retro · 8-arc streak** · B280

## Fleet criteria (16 pillars · V84 unchanged · V85 SAME)

| # | Agent | V84 close | V85 |
|---|---|---|---|
| 1-16 | (all) | 100 under unchanged V78 scoring | **100 with V85 V6 bridge substrate added · V78 scorers UNCHANGED** |
| ~~17~~ | ~~(declined)~~ | ~~NOT added~~ | **STILL NOT added (8-arc streak target)** |

## Reverse-stops (NEW in V85)

15. Bridge mode READ-ONLY (no new MUTATING_ROUTES · count locked at 9)
16. Bridge AI passive-observe (no auto-execute · no advisory side effects)
17. Bridge UI visual distinction from curated (LIVE DATA pill + badge mandatory)

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V85 baseline) | 2026-05-17 | **100** | 137.00 | quality (=100) | All V85 substrate landed pre-score · iter-0 already at 100 (V83 pattern · V84 async-mount lesson held: zero post-click async-mounts in V85 substrate) · CLOSE_ELIGIBLE | V85_iter_0.md |
| 1 (substrate re-confirm) | 2026-05-17 | **100** | 137.00 | quality (=100) | Substrate stable · CLOSE_ELIGIBLE | V85_iter_1.md |
| 2 (stability re-confirm) | 2026-05-17 | **100** | 137.00 | quality (=100) | **CLOSE_CONFIRMED** · 3-consecutive (gate over-met like V82+V83) · 8-arc no-scoring-change streak attained | V85_iter_2.md |

— V85 ARC-GOAL · 2026-05-17 · CLOSED
