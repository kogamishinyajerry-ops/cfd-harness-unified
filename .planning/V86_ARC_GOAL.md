# ARC-GOAL · V86 · V7 Live Solver Trigger Arc · 22nd V110 advisor-class · **1st non-verbatim mandate since V80** · 9th consecutive no-scoring-change arc · **CLOSED 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v86_charter_dec.md` (Accepted B281)
> **Close DEC**: `.planning/decisions/2026-05-17_v86_close_dec.md` (Accepted B287)
> **Retro**: `.planning/retrospectives/2026-05-17_v86_retro.md`
> **Predecessor**: DEC-V85-close (V6 LANDED · 8-arc streak)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring (unchanged) · **MET (3-consec over-met)**
> **Disposition**: (a) extend existing `POST /api/import/{case_id}/solve-stream` (per DEC-V61-088 surface scan)

## North Star

Mandate wording shifted "AI CFD demo展示" → "全流程CFD能力". V86 closes the 6-arc live-solver-hookup carry by wiring the **already-existing** solver endpoint into the v3 workbench as a **USER-triggered** Run button + state machine + SSE bridge + post-run hand-off into V6 bridge. V132 stays at 9 (no new endpoint). V130 stays intact (USER triggers, AI doesn't). 9-arc no-scoring-change streak attained.

## Done dim checklist

- [x] **V85-DONE-COMPOSITE carry** — 16/16 pillars at 100 under unchanged V78 scoring
- [x] **V86-DONE-COMPOSITE** — V7 LANDED with 4 contracts (V7.A-D) implemented + V78 scorers UNCHANGED still report 16-pillar 100/100 + 6-arc live-solver-hookup carry CLOSED

## Sub-DEC progress

- [x] **V86.1 · V7 blueprint document** — `.planning/blueprints/v7/INDEX.md` · 194 lines · 4 contracts + 10 reverse-stops + 4Q gate · B282
- [x] **V86.2 · V7.A Run Solver Button** — `RunSolverButtonV7.tsx` · ~120 LOC · 17 contract tests · V130 lexical + structural denylist · B283
- [x] **V86.3 · V7.B Run State Machine** — `useSolverRunStateV7.ts` · ~250 LOC · 13 contract tests · AbortController + generation counter · B284
- [x] **V86.4 · V7.C Live Residual Bridge** — `LiveSolverPillV7.tsx` (~55 LOC) + V7.B `onResidualTick` extension · 11 contract tests · B285
- [x] **V86.5 · V7.D Post-Run Hand-off** — `usePostRunHandoffV7.ts` (~110 LOC) · 8 contract tests · fire-and-forget audit-package · B286
- [x] **V86.6 · Final verification + close + retro · 9-arc streak attained** · B287

## Reverse-stops (NEW in V86)

16. V7.A Run button USER-click only (no AI auto-trigger, no timer, no programmatic invocation)
17. V7.A in Engineer Control Rail only (not in sandbox/cinematic/bridge surfaces)
18. Run state cancellable from UI (no runaway runs)
19. V7.D preserves V6 bridge READ-ONLY semantics

## Fleet criteria (16 pillars · V85 unchanged · V86 SAME)

| # | Agent | V85 close | V86 |
|---|---|---|---|
| 1-16 | (all) | 100 under unchanged V78 scoring | **100 with V86 V7 substrate added · V78 scorers UNCHANGED** |
| ~~17~~ | ~~(declined)~~ | ~~NOT added~~ | **STILL NOT added (9-arc streak attained)** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V86 baseline) | 2026-05-17 | **100** | 137.00 | quality (=100) | All V86 substrate landed pre-score · iter-0 already at 100 (V83/V85 pattern · V84 async-mount lesson held: V7 substrate is all steady-state UI) · CLOSE_ELIGIBLE | V86_iter_0.md |
| 1 (substrate re-confirm) | 2026-05-17 | **100** | 137.00 | quality (=100) | Substrate stable · CLOSE_ELIGIBLE | V86_iter_1.md |
| 2 (stability re-confirm) | 2026-05-17 | **100** | 137.00 | quality (=100) | **CLOSE_CONFIRMED** · 3-consecutive (gate over-met like V82+V83+V85) · 9-arc no-scoring-change streak attained · 6-arc live-solver-hookup carry CLOSED | V86_iter_2.md |

— V86 ARC-GOAL · 2026-05-17 · CLOSED
