---
decision_id: DEC-V80-charter
title: V80 charter · STRATEGIC PIVOT · construct V4 blueprint for top-tier full-pipeline AI CFD demo showcase · NO new pillar · NO new subscore · NO threshold change · 4 substrate sub-DECs
status: Accepted
parent_dec: DEC-V79-close
phase: V80
notion_sync_status: pending
predecessor: DEC-V79-close
batch: B238
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V80-charter (bootstrap)
substrate: V79 closed 16/16 × 2 consec under unchanged V78 scoring · V79 retro Open Q #4 honored · V80 mandate adds 构建下一个阶段的蓝图 clause · this is the first STRATEGIC PIVOT arc since V67-C
---

# DEC-V80-charter · V80 v3→v4 Strategic Pivot · CHARTER

## 1 · Mandate (16th invocation · NEW CLAUSE)

> "批准授权你全权开发，**构建下一个阶段的蓝图（致力于顶级的全流程AI CFD demo展示）**，瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

**The 16th invocation adds the bolded clause that did NOT appear in V67-C through V79.** The user mandate is no longer "develop against the existing blueprint" — it now demands "construct the next-stage blueprint targeting top-tier full-pipeline AI CFD demo showcase".

This is the first STRATEGIC PIVOT arc since V67-C. V67-C through V79 worked against the V3 blueprint (`.planning/blueprints/v3/INDEX.md`). V80 constructs the V4 blueprint.

## 2 · What "demo showcase" means concretely

**Target user**: a fresh engineer (aerospace/automotive intern · novice but technically literate) lands on the workbench cold. Within 30 seconds they understand:

1. **What this tool does** (AI-assisted CFD · LLM offline runnable · the pipeline runs without an AI in the loop)
2. **What top industrial software looks like** (CATIA / STAR-CCM+ / Ansys Workbench DNA already in the V3 UI)
3. **What "AI advisor not driver" means** (concrete advisor commentary visible in the right panel · no auto-execute affordances)
4. **The full pipeline** (Import → Mesh → Physics → Solver → Postprocess → Trust verdict)

The "demo showcase" is NOT a marketing site. It is the workbench as it already exists, with:
- A **narrative scaffold** that walks a fresh user through the 5-step pipeline in 30s
- **AI advisor depth** — 3 commentary kinds (mesh quality reasoning, convergence diagnostics, result interpretation) keyed to case+step, human-curated text snippets (LLM offline · V130 invariant)
- **Comparator visualizations** that make gold-vs-actual visible beyond delta tables (lid_driven_cavity centerline u-velocity vs Ghia 1982)
- All 76 V77+V78+V79 baselines holding · all 16 pillars at 100 under unchanged V78 scoring

## 3 · The V79-discipline commitment (carried into V80)

V78: "harder work, same nominal score" via threshold tightening.
V79: "more work, same nominal score" via zero scoring changes.
**V80: "strategic pivot work, same nominal score" via zero scoring changes — third consecutive arc.**

V80 charter §6 reverse-stops carry V79's:
- ❌ NO new pillar (V78 reverse-stop · carried)
- ❌ NO new subscore (V79 reverse-stop · carried)
- ❌ NO V78 scorer threshold change (V79 reverse-stop · carried)
- ❌ NO new scorer script (NO `v80_fleet/` directory will be created)

This is a STRATEGIC arc, not a scoring framework arc. The V4 blueprint is a STRATEGIC DOCUMENT, not a new pillar.

## 4 · Sub-DEC roadmap

| Sub-DEC | Headline | Substrate landing |
|---|---|---|
| **V80.1** | V4 blueprint document | `.planning/blueprints/v4/INDEX.md` — extends V3 (does NOT replace) · 4 NEW visual contracts (demo banner / advisor depth panel / comparator viz / first-time landing) · honest 30s narrative timeline |
| **V80.2** | Demo mode + guided narrative | `/workbench/v3?demo=1` query trigger · opt-in (non-aggressive) banner · 5-step guided narrative steps · uses existing case data · NO LLM call at runtime · respects V130 invariant |
| **V80.3** | AI advisor depth panels | Right-panel Advisor tab gains 3 commentary kinds (`advisor-commentary-mesh-quality` / `-convergence` / `-result-interpretation`) · human-curated text snippets keyed by (case_id, step) · ADVISORY only · footer "0 actions taken · V132 locked" preserved |
| **V80.4** | Comparator visualizations | `ResultsCanvas` gold-vs-actual side-by-side SVG · lid_driven_cavity centerline u-velocity overlay (computed vs Ghia 1982 reference) · ±5% tolerance band visible · NOT a replacement for GoldDeltaPanel · complement |
| **V80.5** | Final verification | V78 scorers UNCHANGED · 16-pillar 100/100 under V80 substrate · honest disclosure if any drift |
| **V80.6** | Close DEC + retro | 3-arc no-scoring-change streak documented (V78+V79+V80) |

## 5 · What V80 is NOT building (charter §7 disclosures)

- ❌ **Marketing landing page** — V80 is workbench-as-demo, not marketing-site-as-demo
- ❌ **LLM-driven advisor text generation** — V80.3 uses human-curated snippets · runtime LLM call would violate V130 + 4Q gate
- ❌ **Auto-execute "Run demo" affordance** — opt-in only · user-initiated narrative · V132 invariant
- ❌ **Backend SSE physically-accurate model** — V78.1 synthetic generator unchanged · DEFERRED to V81
- ❌ **Firefox/Webkit actual runs** — V79.2 config-ready, V80 doesn't address browser install
- ❌ **Pillar 17 / new subscore / scorer change** — V78+V79+V80 streak invariant
- ❌ **SSIM at per-screenshot replacement** — V79.3 proved standalone gate · V80 doesn't address

## 6 · Reverse-stops (V80)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9)
2. Any auto-execute button in any v3 surface (V130 invariant)
3. **NO new pillar** (V78 charter reverse-stop carried)
4. **NO new subscore** (V79 charter reverse-stop carried)
5. **NO V78 scorer threshold change** (V79 charter reverse-stop carried)
6. **NO new scorer script (`v80_fleet/` MUST NOT exist)** (V80 charter reverse-stop · NEW)
7. **AI advisor commentary text MUST be human-curated · NOT runtime LLM-generated** (V80 charter reverse-stop · NEW)
8. Demo mode aggressive UX (auto-popup modal, full-screen takeover) (V80 charter reverse-stop · NEW)
9. Any of 76 V79-validated baselines drifts (carried)
10. axe-core finds WCAG violations on any of Steps 1-5 (carried)

## 7 · 4Q gate (every V80 sub-DEC must answer)

1. **LLM offline runnable?** ✓ All V80 work is offline-pure · demo narrative is static SVG/HTML · advisor commentary is curated snippets
2. **Artifacts emitted?** No new artifact types
3. **TrustGate intact?** No new MUTATING_ROUTES
4. **AI advisory only?** V80.3 advisor depth IS the V130 invariant rendered as substrate

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V79 substrate carried | 100/100 (no regression) |
| 1 | V80.1 blueprint LANDED · V80.2 demo mode LANDED | 100/100 (substrate orthogonal to existing tests) |
| 2 | V80.3 advisor depth LANDED · V80.4 comparator viz LANDED | possible baseline drift (new visual surfaces) · re-snap as needed |
| 3 | All V80 substrate verified · CLOSE_ELIGIBLE | 100 |
| 4 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged). If V80 substrate triggers any pillar regression, close at lower score with honest disclosure.

## 9 · Counter telemetry (estimated)

- V80-charter: B238
- V80.1-V80.6 + close: B239-B245 estimated
- All `autonomous_governance: true`
- Counter contribution: **+8** · arc within v2.3 cadence floor 30

## 10 · The bigger picture (3-arc commitment)

| Arc | Pillars added | Subscores added | Thresholds changed | Substrate landed |
|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | proportional |
| V78 | 0 | +3 (rebalanced) | +4 tightenings | tooling debts |
| V79 | 0 | 0 | 0 | feature parity |
| **V80** | **0** | **0** | **0** | **V4 blueprint + demo showcase substrate** |

V67-C through V77 was the "build the framework" era. V78+V79+V80 is the "raise project depth at constant framework" era. The user mandate's "99分以上" is permanently met; arcs improve the project, not the score.

**The V80 charter's most important commitment is that the V4 blueprint exists as a STRATEGIC DOCUMENT, not a scoring axis.** Future arcs (V81+) work against V4 the way V71-V79 worked against V3.

— DEC-V80-charter · 2026-05-17 · LANDED
