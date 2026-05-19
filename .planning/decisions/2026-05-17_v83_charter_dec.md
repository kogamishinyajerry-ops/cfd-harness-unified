---
decision_id: DEC-V83-charter
title: V83 charter · 19th V110 advisor-class arc · 2nd STRATEGIC PIVOT (V5 blueprint construction · V4 fully substantiated by V82) · 6th consecutive no-scoring-change arc · 4 NEW visual contracts (V5.A-V5.D) · NO new pillar · NO new subscore · NO threshold change · NO new scorer script
status: Accepted
parent_dec: DEC-V82-close
phase: V83
notion_sync_status: pending
predecessor: DEC-V82-close
batch: B260
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V83-charter (bootstrap)
substrate: V82 closed 16/16 × 3 consec under unchanged V78 scoring · V4 blueprint FULLY substantiated (10/10 cases · 79 baselines · 4 contracts proven) · V82 retro Open Q #5 explicitly flagged V5 decision point · 19th mandate re-issues "construct next-stage blueprint" verbatim · interpretation: V5 IS the answer this arc (vs V81 + V82 substrate-only interpretations)
---

# DEC-V83-charter · V83 V5-Blueprint-Construction Arc · CHARTER

## 1 · Mandate (19th invocation · re-issued V80 wording verbatim · 3rd time)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程AI CFD demo展示），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

The 19th mandate is the **3rd verbatim re-issue** of the V80 mandate (which added the "construct next-stage blueprint" clause). V81 + V82 interpreted these re-issues as **substrate-depth / substrate-completion** of V4 because V4 was fresh. After V82, V4 is FULLY substantiated (10/10 cases · 79 baselines · 4 contracts × behavior + visual proofs). V82 retro Open Q #5 explicitly raised:

> "V5 blueprint construction — V4 is fully proven now. The case for a V5 blueprint depends on whether the user mandate's 'construct next-stage blueprint' clause should re-activate. V82 interpreted it as substrate completion; V83 could legitimately interpret it as new blueprint."

The 19th mandate re-issuing the blueprint clause SETTLES the question: V83 = **V5 blueprint construction arc**.

## 2 · What V83 is building (concrete sub-DECs)

| Sub-DEC | Headline | V5 contract |
|---|---|---|
| **V83.1** | V5 blueprint document · `.planning/blueprints/v5/INDEX.md` · 4 NEW contracts extending V4 (NOT replacing) | V5.A-V5.D meta-contract |
| **V83.2** | Demo Sandbox Mode · `?demo=2` opt-in click-through Steps 1-5 with curated state · feels interactive · NOT a live solver | V5.A |
| **V83.3** | Failure-Mode Showcase · 3 canonical CFD failure patterns + live AI advisor diagnosis · what AI catches that a beginner misses | V5.B |
| **V83.4** | Cinematic Mode · auto-progressing 60s tour with play/pause/back · still opt-in (`?demo=1&cinema=1`) · respects V80 reverse-stop #8 (no aggressive UX) | V5.C |
| **V83.5** | Demo Run Provenance Card · end-of-tour summary (cases viewed · advisor commentaries shown · comparator deltas · citation count) · gives the demo a tangible "you saw N pieces of CFD knowledge" payoff | V5.D |
| **V83.6** | Final verification + close + retro · 6-arc no-scoring-change streak | — |

## 3 · V79+V80+V81+V82-discipline commitment (carried into V83 · 6th arc)

V78: threshold tightening (1 arc · framework changed).
V79: feature parity (2nd arc · no framework change).
V80: V4 blueprint LANDED (3rd arc · no framework change).
V81: V4 substrate depth (4th arc · no framework change).
V82: V4 substrate completion (5th arc · no framework change).
**V83: V5 blueprint construction (6th consecutive no-framework-change arc).**

V83 reverse-stops carry all prior:
- ❌ NO new pillar (V78 carry · 6th arc)
- ❌ NO new subscore (V79 carry · 5th arc)
- ❌ NO V78 scorer threshold change (V79 carry · 5th arc)
- ❌ NO new scorer script (V80 carry · 4th arc · no `v83_fleet/`)
- ❌ Advisor commentary MUST remain human-curated (V80 carry · 4th arc)
- ❌ Aggressive demo UX MUST NOT appear (V80 carry · 4th arc)
- ❌ V81.4 `--arc-label` flag backward compat (V81 carry · 3rd arc)
- ❌ V82.4 SSE generator MUST stay LLM-offline (V82 carry · 2nd arc)
- ❌ V82.4 backend route MUST stay GET-only (V82 carry · 2nd arc)
- **NEW**: V83.4 cinematic mode auto-progression MUST be cancellable + pausable + must NOT trigger if `prefers-reduced-motion`
- **NEW**: V83.2 sandbox mode click-through MUST NOT call any real backend endpoint that mutates state
- **NEW**: V83.5 provenance card counts MUST come from observable URL/localStorage state · no telemetry leakage

## 4 · What V83 is NOT building (charter §5 disclosures)

- ❌ **V6 blueprint** — V5 just landing; multiple blueprints per arc is substrate inflation
- ❌ **Live OpenFOAM solver behind the sandbox** — V5.A is curated-state click-through, NOT a real solver. This is the multi-arc carry from V80-V82.
- ❌ **Firefox + Webkit actual install** — V79+V80+V81+V82 carry continues
- ❌ **YAML migration of advisor_commentary** — V82 retro flagged; V83 chose V5 blueprint over migration · defer to V84+
- ❌ **Side-by-side variant of ComparatorV4** — V80 retro Open Q · still deferred
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 6-arc streak invariant
- ❌ **Replacing V3 blueprint** — V3+V4+V5 coexist · V3 retire is V90+ concern
- ❌ **Voice-over audio for cinematic mode** — text-only · accessibility default · audio would force opt-in flow complications

## 5 · Reverse-stops (V83)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant)
3. NO new pillar (6th arc carry)
4. NO new subscore (5th arc carry)
5. NO V78 scorer threshold change (5th arc carry)
6. NO new scorer script (4th arc carry · no `v83_fleet/`)
7. AI advisor commentary text MUST be human-curated (4th arc carry)
8. Demo mode aggressive UX (4th arc carry · cinematic mode MUST respect this · auto-advance is opt-in only · scroll-lock prohibited)
9. V81.4 `--arc-label` backward compat (3rd arc carry)
10. V82.4 SSE generator + route discipline (2nd arc carry)
11. **NEW**: V83.4 cinematic auto-advance MUST be cancellable + respect `prefers-reduced-motion`
12. **NEW**: V83.2 sandbox MUST NOT call mutating backend endpoints
13. **NEW**: V83.5 provenance counts MUST be observable-state-only (no analytics beacons)
14. Any of 79 V82-validated baselines drift (80+ if V83 lands new baselines)
15. axe-core finds WCAG violations on any of Steps 1-5

## 6 · 4Q gate (every V83 sub-DEC must answer)

1. **LLM offline runnable?** ✓ All V83 work is offline-pure · sandbox uses curated lookup · failure-mode showcase uses curated narrative · cinematic mode is URL+timer state · provenance card is observable-state count
2. **Artifacts emitted?** ✓ No new artifact types
3. **TrustGate intact?** ✓ No new MUTATING_ROUTES · sandbox is read-only
4. **AI advisory only?** ✓ V83.3 failure-mode showcase IS V130 invariant rendered as substrate (AI catches the failure · engineer applies the fix)

## 7 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V82 substrate carried | 100/100 (carry) |
| 1 | V83.1-V83.5 LANDED · new baselines snapped under canonical state | 100/100 (substrate orthogonal · with discipline from V82) |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 8 · Counter telemetry (estimated)

- V83-charter: B260
- V83.1-V83.6 + close: B261-B266 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 9 · The bigger picture (6-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 (rebalanced) | +4 tightenings | 4 new | tooling debts |
| V79 | 0 | 0 | 0 | 0 | feature parity |
| V80 | 0 | 0 | 0 | 0 | V4 blueprint + demo showcase |
| V81 | 0 | 0 | 0 | 0 (added flag) | V4 substrate depth |
| V82 | 0 | 0 | 0 | 0 | V4 substrate completion |
| **V83** | **0** | **0** | **0** | **0** | **V5 blueprint construction · 4 NEW contracts extending V4** |

V78+V79+V80+V81+V82+V83 = **6-arc** "raise depth at constant framework" streak. The V77-era framework has now absorbed 2 strategic-pivot blueprints (V4 + V5) and 3 substrate-extension arcs without adding a scoring axis.

— DEC-V83-charter · 2026-05-17 · LANDED
