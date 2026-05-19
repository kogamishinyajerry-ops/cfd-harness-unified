---
decision_id: DEC-V78-charter
title: V78 charter · tooling-debt arc · NO new pillar · backend SSE impl + SSIM tooling + audit-package E2E + UX 100% specs threshold · 16-pillar fleet w/ tightened thresholds
status: Accepted
parent_dec: DEC-V77-close
phase: V78
notion_sync_status: pending
predecessor: DEC-V77-close
batch: B222
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V78-charter (bootstrap)
substrate: V77 closed 16/16 × 2 consec · 4 tooling debts oldest 5 retros aged (SSIM) · Pillar 17 explicitly DECLINED per V77 retro Open Question #6
---

# DEC-V78-charter · V78 v3 Tooling-Debt Arc · NO NEW PILLAR · CHARTER

## 1 · Mandate (14th verbatim)

> "批准授权你全权开发，瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

14th V110 advisor-class single-day arc. Identical wording across V67-C..V77.

## 2 · Why V78 is NOT adding Pillar 17

V67-C → V77 added 9 pillars (7 → 16). **Each was forced by a missing substrate axis the user mandate would not otherwise score.** V77 retro Open Question #6 was explicit:

> "What's the ceiling on Pillar count? V67-C started at 7, V77 has 16. **V78 should NOT add Pillar 17 reflexively** · should consider tooling-debt arc instead."

V78 honors that. The honest scoring imperative ("绝对诚实客观") demands that "迭代发开下去" can NOT always mean "add a new axis". After 9 consecutive additions, the marginal pillar would be score gaming — measuring a synthetic axis to satisfy mandate verbatim.

**V78 reframes "99分以上 (above 99 across sufficient dimensions)" as TIGHTENING existing dimension thresholds while closing real tooling debts.** The same score (16-pillar 100/100) must now be achieved against HARDER subscores, not added subscores.

## 3 · The 4 longest-aged tooling debts

| Debt | First mentioned | Retros aged | V78 sub-DEC |
|---|---|---|---|
| **SSIM visual baseline tooling** | V73 retro | 5 (V73/V74/V75/V76/V77) | V78.2 |
| **Backend audit-package E2E smoke** | V74 close §5 | 4 (V74/V75/V76/V77) | V78.3 |
| **Backend SSE endpoint** | V77 close §5 | 1 (V77) — but enables full V71.L bookmark closure (8 arcs from V71.L itself) | V78.1 |
| **UX 100% specs threshold** | V75 retro | 3 (V75/V76/V77) | V78.4 |

V78.1 is the youngest debt but the highest impact — closes the V71.L SSE bookmark END-to-end (front + back) after 8 arcs.

## 4 · Sub-DEC roadmap

| Sub-DEC | Headline | Quality dimension tightened |
|---|---|---|
| **V78.1** | Backend `/api/cases/{id}/solver/stream` FastAPI route · synthetic residual generator · 200 OK text/event-stream · pyt unit + integration tests | Pillar 16 quality: "offline graceful" → "live end-to-end" |
| **V78.2** | SSIM visual baseline tool · script computes Structural Similarity Index Measure for each baseline vs current capture · threshold ≥0.99 · keeps playwright spec format · adds `scripts/visual/ssim_compare.py` | Pillar 4 quality: pixel-ratio (shallow) → SSIM (structural) |
| **V78.3** | pytest smoke `tests/integration/test_audit_package_e2e.py` exercises buildAuditPackage → download → verify manifest schema + signature_hex · runs against live backend | Pillar 13 quality: "static buildAuditPackage call" → "roundtrip verified" |
| **V78.4** | Pillar 3 UX scorer · flow_completion subscore requires **100% playwright specs PASS** (was ≥17 of 122) · forces full suite green | Pillar 3 quality: "≥17 specs threshold" → "all specs PASS" |
| **V78.5** | v78_fleet scorers · Pillar 4 SSIM-aware · Pillar 3 100% specs · Pillar 13 + audit_package_e2e subscore · Pillar 16 + backend_e2e subscore · NO new pillar | Threshold-only changes |
| **V78.6** | Close DEC + retro + verification · 16-pillar 100/100 × 2-consec w/ TIGHTENED scoring | — |

## 5 · Scoring framework discipline

**Pillar count stays at 16. No subscore renaming. No new agent. No reflexive pillar add.**

What changes:
- Existing subscore THRESHOLDS tighten (Pillar 3, Pillar 4)
- Existing subscore COMPUTATION method upgrades (Pillar 4 SSIM)
- Existing pillars (13, 16) gain ADDITIONAL substantive subscores (audit_package_e2e, backend_e2e) only because the work is genuinely landing new measurement surfaces

If V78 cannot hit 16-pillar 100/100 with these tightened thresholds, the honest answer is **the arc closes at lower-than-100 and discloses it** — NOT add another pillar to mask.

## 6 · Reverse-stops (V78)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9; backend SSE is GET text/event-stream not mutating)
2. Any auto-execute button in any v3 surface
3. Any of 76 V77 baselines drifts > 0.01 pixel ratio OR SSIM < 0.99 (whichever V78.2 substrate adopts)
4. Backend SSE handler leaks goroutines / async tasks (must cleanly close on client disconnect)
5. audit-package E2E smoke false-passes (must verify signature_hex format matches V74.5 spec)
6. UX 100% specs threshold tightening hides regressions (must surface ALL failing specs, not just count)
7. Adding Pillar 17 (charter-level reverse-stop · V78 commitment)

## 7 · Honest disclosures (V78 explicitly NOT doing)

- ❌ **vtk.js camera presets** (front/top/iso) — DEFERRED to V79; V78 is tooling-debt focused not feature
- ❌ **Pillar 17** — explicitly NOT adding (charter §2)
- ❌ **SSE backend with WebSocket / long-poll fallback** — V78.1 is pure SSE; client-side EventSource is sufficient
- ❌ **Cross-browser playwright matrix** — chromium only; firefox/webkit deferred
- ❌ **V77.5 backend wire upgrade** — V77 scored frontend wire @100 already; V78.1 adds backend WITHOUT bumping Pillar 16 from 100 to higher (it's already saturated)

## 8 · 4Q gate (every sub-DEC must answer)

1. **LLM offline runnable?** Backend SSE is synthetic residual generator, no LLM ✓
2. **Artifacts emitted?** V78.3 verifies audit-package artifacts roundtrip
3. **TrustGate intact?** No new MUTATING_ROUTES; SSE is GET-only
4. **AI advisory only?** No AI affordances added

## 9 · Iteration target

| Iter | Goal | Expected min(16) under TIGHTENED scoring |
|---|---|---|
| 0 | Baseline w/ V78 scorer (tightened) · V77 substrate carried | Expected drop from V77's 100/100 due to: (a) Pillar 3 100% specs threshold not yet met, (b) Pillar 4 SSIM not yet computed, (c) Pillar 13 audit-pkg-e2e new subscore at 0, (d) Pillar 16 backend-e2e new subscore at 0 |
| 1 | V78.1 LANDED · backend SSE returns 200 | Pillar 16 gains backend_e2e ≥25 |
| 2 | V78.2 LANDED · SSIM script + scorer integration | Pillar 4 SSIM-aware |
| 3 | V78.3 LANDED · audit-pkg E2E smoke green | Pillar 13 gains audit_package_e2e ≥25 |
| 4 | V78.4 LANDED · UX 100% specs · all baselines + journey green | Pillar 3 → 100 under new threshold |
| 5 | Close gate eligible · all 16 at 100 under TIGHTENED scoring | CLOSE_ELIGIBLE |
| 6 | Stability re-confirm · CLOSE_CONFIRMED | CLOSE_CONFIRMED (2-consecutive) |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters UNDER tightened scoring. If unachievable, close with honest disclosure of the stuck dim.

## 10 · Counter telemetry (estimated)

- V78-charter: B222
- V78.1-V78.6 + close: B223-B229 estimated
- All `autonomous_governance: true`
- Counter contribution: **+8** · arc within v2.3 cadence floor 30

## 11 · The bigger commitment

V78 is the first arc that **commits to harder work for same nominal score**. If the user reads "16-pillar 100/100" the same way at V78 close as at V77 close, the integrity bar will look identical — but the actual work landed will be substantially harder (SSIM, real backend SSE, real E2E roundtrip, real 100% specs). Honest scoring rewards depth, not breadth.

— DEC-V78-charter · 2026-05-17 · LANDED
