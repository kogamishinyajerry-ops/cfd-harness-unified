---
decision_id: DEC-V84-charter
title: V84 charter · 20th V110 advisor-class arc · V5 substrate-depth (mirror V81-after-V80 pattern) · 7th consecutive no-scoring-change arc · close 5 of 9 V83 retro Open Qs · NO new pillar · NO new subscore · NO threshold change · NO new scorer script
status: Accepted
parent_dec: DEC-V83-close
phase: V84
notion_sync_status: pending
predecessor: DEC-V83-close
batch: B267
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V84-charter (bootstrap)
substrate: V83 closed 16/16 × 3 consec under unchanged V78 scoring · V5 blueprint LANDED with 4 contracts (V5.A-V5.D) implemented but behavior-test-only · V83 retro Open Qs #1-#5 list V84 candidates · 20th mandate re-issues "construct next-stage blueprint" 4th time · interpretation: V5 substrate depth, NOT V6 blueprint (V83 close §8 says V6 premature)
---

# DEC-V84-charter · V84 V5-Substrate-Depth Arc · CHARTER

## 1 · Mandate (20th invocation · 4th verbatim re-issue)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程AI CFD demo展示），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

The 20th mandate is the **4th verbatim re-issue** of the V80 wording. Pattern across the 4 re-issues:

| Mandate # | Arc | Interpretation | Why |
|---|---|---|---|
| 16th (V80) | V80 | LAND V4 blueprint | First strategic pivot since V67-C; V3 substrate mature |
| 17th (V81) | V81 | EXTEND V4 substrate depth | V4 just landed, needs proof tests + baselines |
| 19th (V83) | V83 | LAND V5 blueprint | V4 fully substantiated (V82 closed); V83 retro Open Q #5 explicitly green-lit |
| **20th (V84)** | **V84** | **EXTEND V5 substrate depth** | V5 just landed (V83); V83 close §8 said V6 premature; mirror V81-after-V80 pattern |

(The 18th invocation was the terser "完成所有建议" V82 arc, between V81 and V83.)

V83 close §8 stated explicitly:
> "V6 blueprint — V5 just landed; V6 not yet justified · would need V5 to be fully substantiated first (parallel of V80 → V81/V82 → V83 pattern)."

V84 honors that discipline: substrate-depth THIS arc, V6 deferred until V5 is fully substantiated.

## 2 · What V84 is building (concrete sub-DECs · close 5 of 9 V83 retro Open Qs)

| Sub-DEC | V83 retro Open Q # | Headline |
|---|---|---|
| **V84.1** | #1 | V5 visual baselines · 4 new baselines (80 sandbox · 81 failure-mode · 82 cinematic · 83 provenance) close the behavior-vs-visual asymmetry V83 disclosed |
| **V84.2** | #2 | V5 e2e Playwright behavior proof · real-browser specs for sandbox/failure-mode/cinematic-live-timing/provenance · vitest fake-timer tests aren't sufficient for live cinematic timing |
| **V84.3** | #3 | Hooks-order grep sweep · scan `src/` for `useState\|useRef\|useEffect\|useMemo` positioned AFTER conditional returns · fix any found (V83 caught one in DemoBannerV4) |
| **V84.4** | #4 | Router-dependency cleanup sweep · find shared components using `useSearchParams\|useNavigate\|useLocation` directly · lift to props where it improves testability (V83 caught one in AdvisorContent) |
| **V84.5** | #5 | Multi-case sandbox traversal · extend V5.A from `lid_driven_cavity`-only to all 10 Gold-Standard cases (per-case curated outcomes per step) |
| **V84.6** | — | Final verification + close + retro · 7-arc no-scoring-change streak |

V83 retro Open Qs #6-#9 (live solver hookup · firefox/webkit install · YAML migration · V6 blueprint) remain DEFERRED — they are multi-arc efforts OR external-environment carries OR premature. V84 explicitly does NOT pull them in.

## 3 · V79+V80+V81+V82+V83-discipline commitment (carried into V84 · 7th arc)

V78: threshold tightening (framework changed).
V79: feature parity (no framework change).
V80: V4 blueprint LANDED (no framework change).
V81: V4 substrate depth (no framework change).
V82: V4 substrate completion (no framework change).
V83: V5 blueprint LANDED (no framework change).
**V84: V5 substrate depth (7th consecutive no-framework-change arc).**

V84 reverse-stops carry all prior:
- ❌ NO new pillar (V78 carry · 7th arc)
- ❌ NO new subscore (V79 carry · 6th arc)
- ❌ NO V78 scorer threshold change (V79 carry · 6th arc)
- ❌ NO new scorer script (V80 carry · 5th arc · no `v84_fleet/`)
- ❌ Advisor commentary MUST remain human-curated (V80 carry · 5th arc)
- ❌ Aggressive demo UX MUST NOT appear (V80 carry · 5th arc · cinematic auto-advance MUST stay opt-in + pausable)
- ❌ V81.4 `--arc-label` flag backward compat (V81 carry · 4th arc)
- ❌ V82.4 SSE generator MUST stay LLM-offline + GET-only (V82 carry · 3rd arc)
- ❌ V83.4 cinematic auto-advance MUST stay cancellable + respect `prefers-reduced-motion` (V83 carry · 2nd arc)
- ❌ V83.2 sandbox MUST NOT call mutating backend endpoints (V83 carry · 2nd arc · V84.5 multi-case extension MUST preserve this)
- ❌ V83.5 provenance card MUST stay analytics-free (V83 carry · 2nd arc)
- **NEW**: V84.5 multi-case sandbox per-case data MUST be human-curated (parallels V80 reverse-stop #7 for advisor commentary)

## 4 · What V84 is NOT building (charter §5 disclosures)

- ❌ **V6 blueprint** — V83 close §8 explicit · V5 not yet fully substantiated · V84 substantiates · V85 candidate for V6
- ❌ **Live OpenFOAM solver behind sandbox** — V5.A is still curated click-through after V84.5 multi-case extension · V80+V81+V82+V83+V84 carry
- ❌ **Firefox + Webkit actual install** — V79+V80+V81+V82+V83+V84 carry continues
- ❌ **YAML migration of advisor_commentary** — V80+V81+V82+V83+V84 retro Open Q · still defer
- ❌ **Side-by-side variant of ComparatorV4** — V80 retro Open Q · still deferred
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 7-arc streak invariant

## 5 · Reverse-stops (V84)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant)
3. NO new pillar (7th arc carry)
4. NO new subscore (6th arc carry)
5. NO V78 scorer threshold change (6th arc carry)
6. NO new scorer script (5th arc carry · no `v84_fleet/`)
7. AI advisor commentary text MUST be human-curated (5th arc carry)
8. Demo mode aggressive UX (5th arc carry · cinematic stays opt-in)
9. V81.4 `--arc-label` backward compat (4th arc carry)
10. V82.4 SSE generator + route discipline (3rd arc carry)
11. V83.4 cinematic auto-advance discipline (2nd arc carry)
12. V83.2 sandbox no-mutating-backend discipline (2nd arc carry · V84.5 MUST preserve)
13. V83.5 provenance card analytics-free (2nd arc carry)
14. **NEW**: V84.5 multi-case sandbox per-case curated outcomes (human-curated, not LLM-generated)
15. Any of 79 V83-validated baselines drift (83+ if V84.1 lands new baselines)
16. axe-core finds WCAG violations on any of Steps 1-5

## 6 · 4Q gate (every V84 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V84.1 baselines are PNG captures · V84.2 e2e is browser-only · V84.3 + V84.4 are code-hygiene · V84.5 per-case sandbox data is static curated lookup
2. **Artifacts emitted?** ✓ Same audit-package artifacts as before
3. **TrustGate intact?** ✓ No new MUTATING_ROUTES · V84.5 sandbox extension stays GET-equivalent
4. **AI advisory only?** ✓ All V84 work either passive substrate or test infrastructure

## 7 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V83 substrate carried · V84 substrate landed before scoring | 100/100 (V82+V83 pattern continues) |
| 1 | Substrate re-confirm | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 8 · Counter telemetry (estimated)

- V84-charter: B267
- V84.1-V84.6 + close: B268-B273 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 9 · The bigger picture (7-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 | +4 | 4 new | tooling debts |
| V79 | 0 | 0 | 0 | 0 | feature parity |
| V80 | 0 | 0 | 0 | 0 | V4 blueprint + demo showcase |
| V81 | 0 | 0 | 0 | 0 (added flag) | V4 substrate depth |
| V82 | 0 | 0 | 0 | 0 | V4 substrate completion |
| V83 | 0 | 0 | 0 | 0 | V5 blueprint + 4 interactive contracts |
| **V84** | **0** | **0** | **0** | **0** | **V5 substrate depth: visual baselines + e2e proof + hooks-order/Router sweeps + multi-case sandbox** |

V78+V79+V80+V81+V82+V83+V84 = **7-arc** streak. The framework continues to absorb depth without growing.

— DEC-V84-charter · 2026-05-17 · LANDED
