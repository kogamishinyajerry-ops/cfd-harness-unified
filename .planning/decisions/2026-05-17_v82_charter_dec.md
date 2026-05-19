---
decision_id: DEC-V82-charter
title: V82 charter · 18th V110 advisor-class arc · close all 4 V81 retro Open Qs · 5th consecutive no-scoring-change arc · NO new pillar · NO new subscore · NO threshold change · NO new scorer script
status: Accepted
parent_dec: DEC-V81-close
phase: V82
notion_sync_status: pending
predecessor: DEC-V81-close
batch: B253
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V82-charter (bootstrap)
substrate: V81 closed 16/16 × 2 consec under unchanged V78 scoring · 4-arc no-scoring-change streak · V82 closes all 4 V81 retro Open Qs in a single arc per user mandate "完成所有建议"
---

# DEC-V82-charter · V82 V4-Substrate-Completion Arc · CHARTER

## 1 · Mandate (18th invocation · "complete all suggestions")

> "批准你全权开发，继续，完成所有建议"

The 18th mandate is terser than 13-17: not the long "全都要" verbatim, but a direct authorization to complete the V81 retro Open Q list. This is a CONTINUATION mandate, not a NEW-BLUEPRINT mandate. The user explicitly says "complete all suggestions" — referring to the V81 retro §"Open questions for V82+" list.

## 2 · What V82 is building (concrete sub-DECs · 1-to-1 with V81 retro Open Qs)

| Sub-DEC | V81 retro Open Q # | Headline |
|---|---|---|
| **V82.1** | #1 | Commentary breadth completion · curate remaining 7 Gold-Standard cases (circular_cylinder_wake / turbulent_flat_plate / plane_channel_flow / impinging_jet / rayleigh_benard_convection / differential_heated_cavity / duct_flow) |
| **V82.2** | #4 | Visual baselines 78 + 79 · close V4.A behavior-vs-visual asymmetry · banner mid-tour state + first-time hint cold state |
| **V82.3** | #2 | Vitest flake root cause investigation · reproduce + fix the 1-of-N intermittent failure flagged in V81.5 iter-2 |
| **V82.4** | #3 | Backend SSE more-physical residual generator · replace V78.1 simple exp-decay with simpleFoam-like momentum/pressure-coupled pattern (still synthetic · still LLM-offline · static-substrate · NOT a live solver hookup) |
| **V82.5** | — | V78 scorers UNCHANGED · 16-pillar 100/100 × 2 consec |
| **V82.6** | — | Close DEC + retro · 5-arc no-scoring-change streak |

## 3 · V79+V80+V81-discipline commitment (carried into V82 · 5th arc)

V78: threshold tightening (1 arc · framework changed).
V79: feature parity (2nd arc · no framework change).
V80: strategic pivot · V4 blueprint LANDED (3rd arc · no framework change).
V81: V4 substrate depth proven (4th arc · no framework change).
**V82: V4 substrate completion · close all V81 retro Open Qs (5th consecutive no-framework-change arc).**

V82 reverse-stops carry V78+V79+V80+V81:
- ❌ NO new pillar (V78 reverse-stop · 5th arc carry)
- ❌ NO new subscore (V79 reverse-stop · 4th arc carry)
- ❌ NO V78 scorer threshold change (V79 reverse-stop · 4th arc carry)
- ❌ NO new scorer script (V80 reverse-stop · 3rd arc carry · `v82_fleet/` MUST NOT exist)
- ❌ Advisor commentary MUST remain human-curated (V80 reverse-stop · 3rd arc carry)
- ❌ Aggressive demo UX MUST NOT appear (V80 reverse-stop · 3rd arc carry)
- ❌ V81.4 score_all.sh `--arc-label` flag MUST NOT regress backward compat (V81 reverse-stop · 2nd arc carry)

## 4 · What V82 is NOT building (charter §5 disclosures)

- ❌ **V5 blueprint** — V4 substrate still incomplete (V82 fills holes); V5 premature until V4 is fully proven
- ❌ **Live solver hookup for ComparatorV4** — depends on real backend solver execution, beyond V82.4's static-substrate scope (V80+V81+V82 carry on live-hookup specifically · V82.4 instead improves the SYNTHETIC pattern)
- ❌ **Firefox + Webkit actual install** — V79.2 config still env-gated · V79+V80+V81+V82 carry · external lockfile situation unchanged
- ❌ **YAML migration of advisor_commentary** — V80+V81 retro Open Q still defer; with V82.1 the TS module hits 10 cases, may become V83 candidate
- ❌ **Side-by-side variant of ComparatorV4** — V80 retro Open Q · overlay-with-worst-point shipped · variant deferred
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 5-arc streak invariant

## 5 · Reverse-stops (V82)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant)
3. **NO new pillar** (5th arc carry)
4. **NO new subscore** (4th arc carry)
5. **NO V78 scorer threshold change** (4th arc carry)
6. **NO new scorer script** (3rd arc carry · no `v82_fleet/`)
7. **AI advisor commentary text MUST be human-curated** (3rd arc carry)
8. Demo mode aggressive UX (3rd arc carry)
9. V81.4 `--arc-label` flag backward compat (2nd arc carry)
10. **NEW**: V82.4 SSE residual generator MUST stay LLM-offline (no runtime LLM call to generate residuals)
11. **NEW**: V82.4 backend route MUST NOT become MUTATING (still GET-only · still streaming · still cancellable via `request.is_disconnected()`)
12. Any of 77 V81-validated baselines drifts (78+79 if V82.2 lands · then 79-validated)
13. axe-core finds WCAG violations on any of Steps 1-5

## 6 · 4Q gate (every V82 sub-DEC must answer)

1. **LLM offline runnable?** ✓ All V82 work is offline-pure · V82.4 SSE generator uses a deterministic curve-shape generator with no LLM call
2. **Artifacts emitted?** ✓ Same audit-package artifacts as before
3. **TrustGate intact?** ✓ No new MUTATING_ROUTES (V82.4 reuses existing GET /api/cases/{id}/solver/stream)
4. **AI advisory only?** ✓ V82.1 commentary is read-only display · V82.4 is solver telemetry display

## 7 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V81 substrate carried | 100/100 (carry) |
| 1 | V82.1-V82.4 LANDED · 78+79 baselines snap-confirmed | 100/100 (substrate orthogonal) |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 8 · Counter telemetry (estimated)

- V82-charter: B253
- V82.1-V82.6 + close: B254-B259 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 9 · The bigger picture (5-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 (rebalanced) | +4 tightenings | 4 new | tooling debts |
| V79 | 0 | 0 | 0 | 0 | feature parity |
| V80 | 0 | 0 | 0 | 0 | V4 blueprint + demo showcase |
| V81 | 0 | 0 | 0 | 0 (added flag to existing) | V4 substrate depth |
| **V82** | **0** | **0** | **0** | **0** | **V4 substrate completion + SSE physical realism + flake fix** |

V78+V79+V80+V81+V82 = 5-arc "raise depth at constant framework" streak. After V82, the V4 blueprint is fully substantiated and the V77-era scoring framework has absorbed 5 arcs of depth.

— DEC-V82-charter · 2026-05-17 · LANDED
