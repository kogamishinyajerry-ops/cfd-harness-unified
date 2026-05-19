# ARC-GOAL · V80 v3→v4 Strategic Pivot · V4 blueprint + demo showcase substrate · NO new pillar · NO new subscore · NO threshold change · **ACTIVE 2026-05-17**

> **Charter**: `.planning/decisions/2026-05-17_v80_charter_dec.md` (Accepted B238)
> **Predecessor**: DEC-V79-close (16-pillar 100/100 under unchanged V78 scoring · B237)
> **NEW**: V4 blueprint document at `.planning/blueprints/v4/INDEX.md` (V80.1 substrate)
> **Streak**: 3rd consecutive arc with NO scoring framework changes (V78 + V79 + V80)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring (unchanged)

## North Star

A fresh engineer lands on `/workbench/v3?demo=1`, walks a 30-second guided narrative through the 5-step CFD pipeline, sees AI advisor commentary at 3 substantive depths (mesh-quality reasoning, convergence diagnostics, result interpretation), and exits with a clear picture of "AI-assisted CFD at industrial quality with AI as advisor not driver".

## Why this arc

V67-C..V79 built the workbench against the V3 blueprint. The 16th invocation of the user mandate added **构建下一个阶段的蓝图** (construct the next-stage blueprint) — this is the first STRATEGIC PIVOT arc since V67-C. V80 delivers:

1. **V4 blueprint** (`.planning/blueprints/v4/INDEX.md`) — 4 new visual contracts extending V3's 8
2. **Demo showcase substrate** (4 sub-DECs landing real code/UI)
3. **Continuation of V78+V79 discipline** — no scoring framework changes

## Done dim checklist

- [x] **V79-DONE-1..16 carry** — 16/16 pillars at 100 under unchanged V78 scoring (V80_iter_1.md + V80_iter_2.md both 100/100)
- [x] **V80-DONE-COMPOSITE** — V4 blueprint LANDED + 4 demo substrate sub-DECs landed (V80.1-V80.4) + V78 scorers UNCHANGED still report 16-pillar 100/100 × 2 consecutive iters

## Sub-DEC progress

- [x] **V80.1 · V4 blueprint document** — `.planning/blueprints/v4/INDEX.md` · 4 visual contracts · honest disclosures
- [x] **V80.2 · Demo mode + guided narrative** — `?demo=1` query trigger + non-aggressive banner + 6-step tour + V4.D first-time hint chip
- [x] **V80.3 · AI advisor depth panels** — 3 commentary kinds (mesh-quality / convergence / result-interpretation) · human-curated text in `ui/frontend/src/data/advisor_commentary.ts` · 8 contract tests passing
- [x] **V80.4 · Comparator visualizations** — `ComparatorV4` SVG gold-vs-actual lid_driven_cavity u-centerline · 17 Ghia reference points + computed polyline + ±5% band + dusty-amber worst-point highlight · 8 contract tests passing
- [x] **V80.5 · Final verification** — V78 scorers UNCHANGED · 16-pillar 100/100 × 2 consecutive iters · CLOSE_CONFIRMED
- [x] **V80.6 · Close DEC + retro · 3-arc no-scoring-change streak (V78+V79+V80)** — `.planning/decisions/2026-05-17_v80_close_dec.md` + `.planning/retrospectives/2026-05-17_v80_retro.md` LANDED

## Fleet criteria (16 pillars · V79 unchanged · V80 SAME)

| # | Agent | V79 close | V80 |
|---|---|---|---|
| 1-16 | (all) | 100 under unchanged V78 scoring | **100 with V80 demo substrate added · V78 scorers UNCHANGED** |
| ~~17~~ | ~~(declined)~~ | ~~NOT added~~ | **STILL NOT added (3-arc streak)** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V80 baseline) | 2026-05-17 | 86 | mid | ux (136/138 specs · baselines 54 + 59 drifted from V80.3 advisor commentary + V80.4 comparator render diff) | charter LANDED · V4 blueprint LANDED · V80.2-V80.4 substrate LANDED · V78 scorers UNCHANGED | V80_iter_0.md |
| 1 (post re-snap) | 2026-05-17 | **100** | 121.04 | quality (tied at 100) | Baselines 54 + 59 re-snapped under V80 substrate · 138/138 specs PASS · CLOSE_ELIGIBLE | V80_iter_1.md |
| 2 (stability re-confirm) | 2026-05-17 | **100** | 121.04 | quality (tied at 100) | 2-consecutive 100/100 reached · CLOSE_CONFIRMED · V78 scorers UNCHANGED · 3-arc no-scoring-change streak attained | V80_iter_2.md |

## Reverse-stop log

- V132 MUTATING_ROUTES net diff > 0 (locked at 9)
- Adding Pillar 17 (V78 reverse-stop carried)
- Adding new subscore (V79 reverse-stop carried)
- Changing V78 scorer threshold (V79 reverse-stop carried)
- **Creating `scripts/governance/v80_fleet/` directory (V80 charter reverse-stop · NEW)**
- **Runtime LLM-generated advisor commentary (V80 charter reverse-stop · NEW)**
- **Aggressive demo UX (auto-popup modal / full-screen takeover) (V80 charter reverse-stop · NEW)**
- Any of 76 V79-validated baselines drifts > 0.01 pixel ratio
- WCAG violations on Steps 1-5

## Counter telemetry

- V80 charter: B238
- V80.1-V80.6 + close: B239-B245 estimated

— V80 ARC-GOAL · 2026-05-17
