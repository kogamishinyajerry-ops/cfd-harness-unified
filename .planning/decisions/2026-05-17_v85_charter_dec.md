---
decision_id: DEC-V85-charter
title: V85 charter · 21st V110 advisor-class arc · V6 blueprint LAND · Real-Artifact Bridge interpretation (mirror V83-after-V81 pattern · 5th re-issue = blueprint land) · 8th consecutive no-scoring-change arc target · closes 5-arc live-solver-hookup carry READ-ONLY · NO new MUTATING_ROUTES · NO new pillar · NO new subscore · NO threshold change · NO new scorer script
status: Accepted
parent_dec: DEC-V84-close
phase: V85
notion_sync_status: pending
predecessor: DEC-V84-close
batch: B274
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V85-charter (bootstrap)
substrate: V84 closed 16/16 × 2 consec under unchanged V78 scoring · V5 fully substantiated (V83 land + V84 depth) · V84 close §8 + V84 retro Open Q #6 explicitly green-lit V6 IF mandate re-issues · 21st mandate IS that 5th verbatim re-issue · interpretation: V6 = Real-Artifact Bridge (V4/V5 demo layer reads existing run artifacts via existing GET endpoints · NO AI-triggered solver execution · NO new MUTATING_ROUTES)
---

# DEC-V85-charter · V85 V6-Blueprint-Construction Arc · CHARTER

## 1 · Mandate (21st invocation · 5th verbatim re-issue)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程AI CFD demo展示），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

The 21st mandate is the **5th verbatim re-issue** of the V80 wording. Pattern across the 5 re-issues:

| Mandate # | Arc | Interpretation | Why |
|---|---|---|---|
| 16th (V80) | V80 | LAND V4 blueprint | First strategic pivot since V67-C |
| 17th (V81) | V81 | EXTEND V4 substrate depth | V4 just landed |
| 19th (V83) | V83 | LAND V5 blueprint | V4 fully substantiated |
| 20th (V84) | V84 | EXTEND V5 substrate depth | V5 just landed |
| **21st (V85)** | **V85** | **LAND V6 blueprint** | V5 fully substantiated (V84 close §8 + V84 retro Open Q #6 explicit green-light) |

(The 18th invocation was the terser "完成所有建议" V82 arc.)

V84 close §8 stated:
> "V6 blueprint — V5 is now substantiated (V83 + V84). V85 IF user re-issues 'construct next-stage blueprint' mandate AND no other priority surfaces, V6 candidate."

V84 retro Open Q #6:
> "V6 blueprint — V5 substantiated this arc. IF the user re-issues 'construct next-stage blueprint' verbatim a 5th time, V6 candidate. Otherwise V85 could pivot strategically (e.g., live solver bridge as V4/V5 substantiation → real-data layer)."

The mandate re-issued verbatim 5th time. V6 lands.

**V6 interpretation**: Real-Artifact Bridge. Not "another visual demo blueprint" (V4 + V5 already cover demo layer · adding V6 in same vein = substrate inflation). Instead, V6 closes the **5-arc structural carry of "live solver hookup"** — but READ-ONLY. The bridge mode reads existing run artifacts (already in `reports/{case_id}/runs/*/`) via existing GET endpoints (already in `ui/backend/routes/`); zero new MUTATING_ROUTES; zero AI-triggered solver execution. V130 (AI advisor not driver) + V132 (MUTATING_ROUTES locked at 9) automatic.

## 2 · What V85 is building (concrete sub-DECs · V6 contracts)

| Sub-DEC | V6 contract | Headline |
|---|---|---|
| **V85.1** | (blueprint document) | V6 blueprint LANDED at `.planning/blueprints/v6/INDEX.md` · 4 contracts (V6.A-D) + reverse-stops + 4Q gate · ~300 lines |
| **V85.2** | V6.A Bridge Reader | Frontend data hook `src/data/run_artifact_reader.ts` · consumes `/api/cases/{id}` + `/api/audit-packages` + `reports/{case}/runs/*/` · returns `BridgeStepState` or null (graceful degrade to curated) · contract tests |
| **V85.3** | V6.B Bridge-Mode Sandbox | DemoSandboxV5 extended with `bridgeActive` prop · `?bridge=1` activates · `getBridgeStepState(caseId, step)` takes precedence over `getSandboxStepState()` · LIVE DATA badge per step · contract tests for both modes |
| **V85.4** | V6.C Live-vs-Curated Diff Panel | New component `LiveVsCuratedDiffV6` · side-by-side curated vs real for current step · highlights significant divergences as AI advisor observations (passive · no auto-execute) · contract tests |
| **V85.5** | V6.D Bridge Truth-Gate Disclosure | `BridgeModeShowcase` component · global "LIVE DATA · advisor passive · no AI mutation" pill · real run_id + commit SHA + checksum from artifact · explicit "exit to curated" CTA · contract tests |
| **V85.6** | (close + retro) | V78 fleet score iter-0/1/2 · 100/100 × 2 consec · DEC-V85-close · V85 retro · 8-arc no-scoring-change streak target |

V84 retro Open Qs that V85 does NOT pull in:
- #3 Live solver hookup (multi-arc commitment beyond V85's READ-ONLY scope) — V85 partially addresses by bridging to existing artifacts but does NOT add live-trigger
- #4 Firefox + Webkit install (environmental carry · defer or close WONTFIX in V86)
- #5 YAML migration of advisor_commentary (defer to V86+)
- #7 Sub-pixel font variance root cause (deeper investigation · defer)

V84 retro Open Qs that V85 partially closes:
- #1 Async-mount baseline audit — V85.6 visual baselines will use settle+threshold-loosen by default (V84.6 lesson applied)
- #2 `resnap_failed_baselines.sh` helper — V85.6 will write this ≤30 LOC helper inline

## 3 · V79+...+V84-discipline commitment (carried into V85 · 8th arc)

V78: threshold tightening (framework changed).
V79: feature parity (no framework change).
V80: V4 blueprint LANDED (no framework change).
V81: V4 substrate depth (no framework change).
V82: V4 substrate completion (no framework change).
V83: V5 blueprint LANDED (no framework change).
V84: V5 substrate depth (no framework change).
**V85: V6 blueprint LAND (8th consecutive no-framework-change arc target).**

V85 reverse-stops carry all prior:
- ❌ NO new pillar (V78 carry · 8th arc)
- ❌ NO new subscore (V79 carry · 7th arc)
- ❌ NO V78 scorer threshold change (V79 carry · 7th arc)
- ❌ NO new scorer script (V80 carry · 6th arc · no `v85_fleet/`)
- ❌ Advisor commentary MUST remain human-curated (V80 carry · 6th arc)
- ❌ Aggressive demo UX MUST NOT appear (V80 carry · 6th arc · cinematic auto-advance stays opt-in + pausable)
- ❌ V81.4 `--arc-label` flag backward compat (V81 carry · 5th arc)
- ❌ V82.4 SSE generator MUST stay LLM-offline + GET-only (V82 carry · 4th arc)
- ❌ V83.4 cinematic auto-advance MUST stay cancellable + respect `prefers-reduced-motion` (V83 carry · 3rd arc)
- ❌ V83.2 sandbox MUST NOT call mutating backend endpoints (V83 carry · 3rd arc)
- ❌ V83.5 provenance card MUST stay analytics-free (V83 carry · 3rd arc)
- ❌ V84.5 multi-case sandbox per-case data MUST stay human-curated (V84 carry · 2nd arc)
- **NEW V6**: Bridge mode MUST be READ-ONLY (zero new MUTATING_ROUTES · V132 count locked at 9)
- **NEW V6**: Bridge data MUST come from existing run artifacts (NO AI-triggered solver execution · V130 invariant)
- **NEW V6**: Bridge UI MUST visually distinguish LIVE vs CURATED (LIVE DATA pill + badge per surface · no ambiguity)
- **NEW V6**: Bridge MUST degrade gracefully (missing artifacts → fall back to curated mode · no crash · no AI auto-trigger)
- **NEW V6**: AI advisor in bridge mode MUST stay passive-observe (observation only · no advisory side effects · no auto-execute · diff panel surfaces divergences as notes, not actions)

## 4 · What V85 is NOT building (charter §5 disclosures)

- ❌ **AI-triggered solver execution** — bridge mode is READ-ONLY · user pre-runs case offline (existing `dogfood_loop.py` or manual) · bridge reads resulting artifacts
- ❌ **New MUTATING_ROUTES** — count locked at 9 · V132 invariant
- ❌ **New auth surface** — bridge consumes existing unauthenticated GET endpoints
- ❌ **V7 blueprint** — V6 just landing · multiple blueprints per arc is substrate inflation
- ❌ **Live OpenFOAM trigger from UI** — V80+V81+V82+V83+V84+V85 carry continues (becoming structural debt · V86 candidate for separate dedicated arc)
- ❌ **Firefox + Webkit actual install** — 7-arc carry continues
- ❌ **YAML migration of advisor_commentary** — 5-arc carry · defer
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 8-arc streak invariant

## 5 · Reverse-stops (V85)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant · including bridge mode)
3. NO new pillar (8th arc carry)
4. NO new subscore (7th arc carry)
5. NO V78 scorer threshold change (7th arc carry)
6. NO new scorer script (6th arc carry · no `v85_fleet/`)
7. AI advisor commentary text MUST be human-curated (6th arc carry)
8. Demo mode aggressive UX (6th arc carry · cinematic stays opt-in)
9. V81.4 `--arc-label` backward compat (5th arc carry)
10. V82.4 SSE generator + route discipline (4th arc carry)
11. V83.4 cinematic auto-advance discipline (3rd arc carry)
12. V83.2 sandbox no-mutating-backend discipline (3rd arc carry)
13. V83.5 provenance card analytics-free (3rd arc carry)
14. V84.5 multi-case sandbox per-case curated outcomes (2nd arc carry)
15. **NEW**: Bridge mode READ-ONLY (no new MUTATING_ROUTES · 1st arc)
16. **NEW**: Bridge mode AI passive-observe (no auto-execute · no advisory side effects · 1st arc)
17. **NEW**: Bridge UI visual distinction from curated (LIVE DATA pill + badge mandatory · 1st arc)
18. Any of 83 V84-validated baselines drift (87+ if V85.6 lands new baselines)
19. axe-core finds WCAG violations on any of Steps 1-5 (in either curated or bridge mode)

## 6 · 4Q gate (every V85 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V85.2 Bridge Reader reads static artifacts · V85.3-V85.5 are UI components · V85.6 visual baselines are PNG captures
2. **Artifacts emitted?** ✓ Bridge mode SURFACES real artifacts (run_id · commit SHA · checksum · audit-package URL · gold-delta) · this is the entire point of V6
3. **TrustGate intact?** ✓ Zero new MUTATING_ROUTES · V85.4 diff panel marks divergences as advisor observations not actions · V85.5 truth-gate makes mode explicit at every surface
4. **AI advisory only?** ✓ Bridge mode AI is passive-observe · diff panel surfaces but does not act · no auto-execute · no remediation buttons

## 7 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V84 substrate carried · V85 substrate landed before scoring | 100/100 (V82+V83 pattern OR 86/9X-then-fix per V84 if async-mount drift recurs) |
| 1 | Substrate re-confirm (post-fix if iter-0 drifted) | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 8 · Counter telemetry (estimated)

- V85-charter: B274
- V85.1-V85.6 + close: B275-B280 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 9 · The bigger picture (8-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 | +4 | 4 new | tooling debts |
| V79 | 0 | 0 | 0 | 0 | feature parity |
| V80 | 0 | 0 | 0 | 0 | V4 blueprint + demo showcase |
| V81 | 0 | 0 | 0 | 0 (added flag) | V4 substrate depth |
| V82 | 0 | 0 | 0 | 0 | V4 substrate completion |
| V83 | 0 | 0 | 0 | 0 | V5 blueprint + 4 interactive contracts |
| V84 | 0 | 0 | 0 | 0 | V5 substrate depth |
| **V85** | **0** | **0** | **0** | **0** | **V6 blueprint LAND: Real-Artifact Bridge (V4/V5 → real run artifacts · READ-ONLY · 5-arc live-solver-hookup carry partially closed)** |

V78+V79+V80+V81+V82+V83+V84+V85 = **8-arc** streak target. The framework continues to absorb depth without growing — including a strategic pivot from "demo-layer-only" (V4 + V5) to "demo-layer + real-data bridge" (V6).

— DEC-V85-charter · 2026-05-17 · LANDED
