---
decision_id: DEC-V81-charter
title: V81 charter · 17th V110 advisor-class arc · continue against V4 blueprint · 4th consecutive no-scoring-change arc · extend substrate where V80 was thin · NO new pillar · NO new subscore · NO threshold change · NO new scorer script
status: Accepted
parent_dec: DEC-V80-close
phase: V81
notion_sync_status: pending
predecessor: DEC-V80-close
batch: B246
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V81-charter (bootstrap)
substrate: V80 closed 16/16 × 2 consec under unchanged V78 scoring · V4 blueprint LANDED with 4 contracts · V81 extends V4 substrate breadth + closes V80 honest-disclosure carries (advisor commentary scope · V4.C baseline 77 · V4.A/V4.D e2e proof · score aggregator hygiene)
---

# DEC-V81-charter · V81 v4-Substrate-Depth Arc · CHARTER

## 1 · Mandate (17th invocation · re-issued V80 wording verbatim)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程AI CFD demo展示），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

V80 closed hours ago. The 17th mandate re-issues V80's wording verbatim. Per V80 close DEC §8 ("V81+ work continues against V4 the way V71-V79 worked against V3"), V81 is interpreted as **continuation, not new-blueprint**. Constructing a V5 blueprint less than 24 hours after V4 landed would be substrate-thinness, not substrate-depth.

V81 therefore picks the **V4 substrate-depth interpretation**: extend the V4 contracts where V80 left them thin, add proof-tests for contracts that only had implementation, and clean up infrastructure debts the V79+V80 retros flagged.

## 2 · What V81 is building (concrete sub-DECs)

| Sub-DEC | Headline | V80 thinness it addresses |
|---|---|---|
| **V81.1** | Extend advisor commentary breadth · curated text for 2-3 more whitelist cases beyond `lid_driven_cavity` | V80 §5: "advisor commentary curation covers only lid_driven_cavity" |
| **V81.2** | Playwright e2e for V4.A + V4.D contracts · prove banner + first-time hint actually behave per blueprint | V80.2 had only vitest contract tests + visual baselines; no e2e behavior proof |
| **V81.3** | Visual baseline 77 for `ComparatorV4` (V4.C contract acceptance test promised this · V80.4 didn't capture) | V4.C acceptance test §4: "Visual baseline added (number 77) for this comparator surface" |
| **V81.4** | Score aggregator filename hygiene · `score_all.sh --arc-label V81` writes `.planning/scores/V81_iter_N.md` directly | V79+V80 retros both flagged manual-copy workaround |
| **V81.5** | V78 scorers UNCHANGED · 16-pillar 100/100 × 2 consec | charter §3 commitment |
| **V81.6** | Close DEC + retro · 4-arc no-scoring-change streak (V78+V79+V80+V81) | streak documentation |

## 3 · V79+V80-discipline commitment (carried into V81 · 4th arc)

V78: "harder work, same nominal score" via threshold tightening (1 arc).
V79: "more work, same nominal score" via zero scoring changes (2nd arc).
V80: "strategic pivot work, same nominal score" via zero scoring changes (3rd arc · added V4 blueprint).
**V81: "substrate-depth work, same nominal score" via zero scoring changes — 4th consecutive arc.**

V81 reverse-stops carry V78+V79+V80's:
- ❌ NO new pillar (V78 reverse-stop · carried)
- ❌ NO new subscore (V79 reverse-stop · carried)
- ❌ NO V78 scorer threshold change (V79 reverse-stop · carried)
- ❌ NO new scorer script (NO `v81_fleet/` directory will be created · V80 reverse-stop · carried)

## 4 · What V81 is NOT building (charter §5 disclosures)

- ❌ **V5 blueprint** — V4 just landed; V5 would be substrate-thinness, not depth. The V80 close DEC §8 explicitly says V81+ continues against V4.
- ❌ **Backend SSE physically-accurate generator** — V78.1 synthetic generator still unchanged · DEFERRED again (V80 carry · this is a multi-arc effort)
- ❌ **Live solver hookup for ComparatorV4** — depends on backend SSE physically-accurate generator landing · DEFERRED with V80's disclosure intact
- ❌ **Firefox + Webkit actual install** — config still env-gated · V79+V80 carry · lockfile situation outside V81 scope
- ❌ **YAML migration of advisor_commentary** — V80 retro Open Q #1 · defer to evidence (need ≥3 non-engineer authors editing) · NOT V81 scope
- ❌ **Side-by-side variant of ComparatorV4** — V80 retro Open Q #2 · V4.C overlay shipped · variant deferred
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — V78+V79+V80+V81 streak invariant

## 5 · Reverse-stops (V81)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant)
3. **NO new pillar** (V78 charter reverse-stop carried · 4th arc)
4. **NO new subscore** (V79 charter reverse-stop carried · 3rd arc)
5. **NO V78 scorer threshold change** (V79 charter reverse-stop carried · 3rd arc)
6. **NO new scorer script** (V80 charter reverse-stop carried · 2nd arc · `v81_fleet/` MUST NOT exist)
7. **AI advisor commentary text MUST be human-curated · NOT runtime LLM-generated** (V80 reverse-stop carried)
8. Demo mode aggressive UX (V80 reverse-stop carried)
9. **NEW: V81.4 score_all.sh changes MUST preserve backward compatibility** (no `--arc-label` flag → behave like V78/V79/V80, write to `V78_iter_N.md`)
10. Any of 76 V79-validated baselines drifts (carried · 77 if V81.3 lands a new baseline · then 77-validated)
11. axe-core finds WCAG violations on any of Steps 1-5 (carried)

## 6 · 4Q gate (every V81 sub-DEC must answer)

1. **LLM offline runnable?** ✓ All V81 work is offline-pure · commentary extension is static text · e2e is browser-only · baseline 77 is canonical-state capture
2. **Artifacts emitted?** ✓ Same audit-package artifacts as before
3. **TrustGate intact?** ✓ No new MUTATING_ROUTES
4. **AI advisory only?** ✓ All V81 work either passive surface (commentary) or test infrastructure

## 7 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V80 substrate carried | 100/100 (carry from V80 close) |
| 1 | V81.1-V81.3 LANDED + V81.4 filename fix | 100/100 (substrate orthogonal · re-snap baseline 77 if needed) |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged). Same as V80.

## 8 · Counter telemetry (estimated)

- V81-charter: B246
- V81.1-V81.6 + close: B247-B252 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 9 · The bigger picture (4-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 (rebalanced) | +4 tightenings | 4 new | tooling debts |
| V79 | 0 | 0 | 0 | 0 | feature parity |
| V80 | 0 | 0 | 0 | 0 | V4 blueprint + demo showcase |
| **V81** | **0** | **0** | **0** | **0** | **V4 substrate depth · advisor breadth · e2e proof · baseline 77 · infra hygiene** |

V78+V79+V80+V81 = 4-arc "raise depth at constant framework" streak. The user mandate's "99分以上" is permanently met; arcs improve the project, not the score.

— DEC-V81-charter · 2026-05-17 · LANDED
