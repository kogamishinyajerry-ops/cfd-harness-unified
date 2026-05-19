---
decision_id: DEC-V79-charter
title: V79 charter · feature-parity arc · NO new pillar · NO new subscore · vtk.js camera presets + cross-browser playwright + SSIM active gate + a11y keyboard nav
status: Accepted
parent_dec: DEC-V78-close
phase: V79
notion_sync_status: pending
predecessor: DEC-V78-close
batch: B230
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V79-charter (bootstrap)
substrate: V78 closed 16/16 × 2 consec under TIGHTENED scoring · V78 retro Open Q #4 "continue the discipline of NOT adding pillars" honored · V79 also adds NO new subscores
---

# DEC-V79-charter · V79 v3 Feature-Parity Arc · CHARTER

## 1 · Mandate (15th verbatim)

> "批准授权你全权开发，瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

15th V110 advisor-class single-day arc. Identical wording across V67-C..V78.

## 2 · Why V79 doubles down on V78's discipline

V67-C → V77 added 9 pillars across 9 arcs. V78 added 0 (first arc with stable framework). V78 retro Open Q #4: "Pillar count: stay at 16 or 17? V79 should continue that discipline."

V79 honors that AND goes further: **V79 also adds NO new subscores.** Every V78 close-listed carry (vtk.js camera presets, cross-browser, SSIM active gate, a11y keyboard nav) is implemented as **work that EXISTING scorers absorb automatically** — not as new scoring axes.

The user mandate's "维度充足 (sufficient dimensions)" was satisfied by V77's 16-pillar framework. V78 proved harder work fits into the same nominal score by tightening thresholds. **V79 proves harder work fits into the same nominal score WITHOUT any scoring changes at all** — pure substrate improvement automatically detected by the V78 scorers.

## 3 · Sub-DEC roadmap (4 V78-listed carries + verification + close)

| Sub-DEC | Headline | How EXISTING V78 scorers absorb it |
|---|---|---|
| **V79.1** | vtk.js camera presets · 3 buttons (front/top/iso) with literal `data-testid="vtk-camera-preset-{front,top,iso}"` | Pillar 15 `camera_widget_count` already counts vtk-camera-* prefix; presets increment but cap is FULL=20 — no score change; substrate IS the value |
| **V79.2** | Cross-browser playwright (firefox + webkit projects) · same 130 specs run on 3 browsers | Pillar 3 UX `flow_completion` requires 100% specs PASS · cross-browser triples spec count and 100% threshold automatically becomes harder |
| **V79.3** | SSIM as active screenshot gate · custom `expect.extend` wraps playwright `toHaveScreenshot` to also enforce SSIM ≥0.99 | Pillar 4 `ssim_tool_present` already PASS · V79 makes SSIM ACTIVELY GATE not just present; same subscore, stricter substrate |
| **V79.4** | a11y full-keyboard nav specs · new playwright spec Tab-walks Steps 1-5 ensuring every interactive element keyboard-reachable + has visible focus ring | Pillar 3 UX absorbs new specs · existing a11y axe scorer (Pillar 11 interaction_polish wcag_runtime) unchanged but new tests run alongside |
| **V79.5** | Run V78 scorers as-is against new substrate · NO v79_fleet/ scripts | NO scorer changes |
| **V79.6** | Close DEC + retro | — |

## 4 · Scoring framework discipline (V79 commitment)

**Pillar count stays at 16. NO subscore added. NO threshold change. NO new scorer scripts.**

What V79 changes:
- ❌ NOT a new scorer script (`scripts/governance/v79_fleet/` will NOT exist)
- ❌ NOT new subscores in existing scorers
- ❌ NOT new thresholds in existing scorers
- ✅ V79 ONLY adds substrate (code + tests + playwright specs)
- ✅ V78 scorers (run unchanged) must still report 16-pillar 100/100

If V79 cannot hit 16-pillar 100/100 under V78 scoring with V79 substrate added, the honest answer is: **the arc closes at lower-than-100 and discloses it** — not relax scoring.

## 5 · Why this is the right discipline

V78 demonstrated "harder work, same score" via threshold tightening. V79 demonstrates "more work, same score" via NO scoring changes at all. Together V78+V79 establish a pattern:

**The user mandate's "99分以上 (above 99)" is permanently met. Further arcs improve the project's REAL quality without inflating the scoring framework.**

This is the path to NOT score-game when the user repeats the verbatim mandate indefinitely. Future readers comparing V79 close → V78 close should see ZERO scoring framework changes — work happened in code, tests, browser matrix, a11y depth, not in scoring.

## 6 · Reverse-stops (V79)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface
3. **NO new pillar** (V78 charter-level reverse-stop carried)
4. **NO new subscore** (V79 charter-level reverse-stop · NEW)
5. **NO new V78-scorer threshold change** (V79 charter-level reverse-stop · NEW)
6. Cross-browser playwright reveals serious WCAG violations → must fix, not skip
7. SSIM active gate false-passes (must verify expect.extend rejects shape-mismatched images)
8. Any of 76 V78-validated baselines drifts under SSIM ≥0.99
9. axe-core finds violations on any of Steps 1-5 (carried)

## 7 · Honest disclosures (V79 explicitly NOT doing)

- ❌ **Pillar 17** — V78 reverse-stop carried · still NOT adding
- ❌ **New subscore in existing pillar** — V79 reverse-stop · NEW
- ❌ **Backend SSE convergence model upgrade** — V78.1 synthetic generator unchanged · DEFERRED to V80
- ❌ **Pillar count audit / re-balance** — V78 already audited · skip
- ❌ **Performance benchmarking** — V79 is feature parity, not perf

## 8 · 4Q gate (every sub-DEC must answer)

1. **LLM offline runnable?** ✓ All V79 work is offline-pure
2. **Artifacts emitted?** No new artifact types
3. **TrustGate intact?** No new MUTATING_ROUTES
4. **AI advisory only?** No AI affordances added

## 9 · Iteration target

| Iter | Goal | Expected min(16) |
|---|---|---|
| 0 | Baseline under V78 scorers · V78 substrate carried | 100/100 (same as V78 close) |
| 1 | V79.1 LANDED (camera presets) · V79.2 LANDED (firefox+webkit) | likely drop from 100 — cross-browser will surface real fails |
| 2 | V79.3 LANDED (SSIM active gate) · V79.4 LANDED (a11y nav specs) · cross-browser fails investigated/fixed | should approach 100 |
| 3 | All V79 work + cross-browser green · NO scorer changes | 100 (CLOSE_ELIGIBLE) |
| 4 | Stability re-confirm | 100 (CLOSE_CONFIRMED 2-consec) |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged). If unachievable due to cross-browser failures, close at lower score with honest disclosure.

## 10 · Counter telemetry (estimated)

- V79-charter: B230
- V79.1-V79.6 + close: B231-B237 estimated
- All `autonomous_governance: true`
- Counter contribution: **+8** · arc within v2.3 cadence floor 30

## 11 · The bigger commitment (continued from V78)

V78: "harder work, same nominal score" via threshold tightening.
V79: "more work, same nominal score" via NO scoring change.

If V80 arrives with another verbatim mandate, the pattern should hold: **work is real, scoring framework is stable**. Reaching 99分 is a permanent state once achieved through honest scoring; further work raises the project, not the score.

— DEC-V79-charter · 2026-05-17 · LANDED
