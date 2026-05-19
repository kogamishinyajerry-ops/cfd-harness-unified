---
decision_id: DEC-V86-charter
title: V86 charter · 22nd V110 advisor-class arc · 1st non-verbatim mandate since V80 ("AI CFD demo展示" → "全流程CFD能力") · V7 Live Solver Trigger blueprint LAND · disposition (a) extend existing POST /api/import/{id}/solve-stream · V132 MUTATING_ROUTES stays at 9 · NO Codex round required · 9th consecutive no-scoring-change arc target · closes 6-arc live-solver-hookup carry via v3 frontend wiring
status: Accepted
parent_dec: DEC-V85-close
phase: V86
notion_sync_status: pending
predecessor: DEC-V85-close
batch: B281
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V86-charter (bootstrap)
substrate: V85 closed 16/16 × 3 consec under unchanged V78 scoring · V6 LANDED · live-solver-hookup carry was 6-arc dominant debt · pre-implementation surface-scan (DEC-V61-088 discipline) found POST /api/import/{id}/solve-stream + /solve already exist in case_solve.py · v3 workbench has ZERO Run-Solver affordance (gap is purely frontend) · disposition (a) extend confirmed by user · V132=9 stays locked · no security boundary crossed
---

# DEC-V86-charter · V86 V7-Live-Solver-Trigger Arc · CHARTER

## 1 · Mandate (22nd invocation · **1st non-verbatim re-issue since V80**)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程**CFD能力**），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

**Wording shift vs V80-V85 (×5 verbatim):**

| | V80-V85 (×5 verbatim) | V86 (this one) |
|---|---|---|
| Core noun | "**AI CFD demo展示**" (AI CFD demo display) | "**CFD能力**" (CFD capability) |
| 全流程 prefix | kept | kept |

The user deliberately removed "AI" + "demo展示" framing while keeping "全流程" + "顶级的" + the rest. Signal: **pivot from showcase substrate to actual CFD capability**. V85 retro Open Q #1 + V85 close §8 both flagged the live-solver-hookup carry (6 arcs) as the dominant structural debt; the mandate wording change aligns with closing it.

Pattern across the 6 mandate instances:

| Mandate # | Arc | Interpretation | Why |
|---|---|---|---|
| 16th (V80) | V80 | LAND V4 blueprint | First strategic pivot since V67-C |
| 17th (V81) | V81 | EXTEND V4 | V4 just landed |
| 19th (V83) | V83 | LAND V5 blueprint | V4 substantiated |
| 20th (V84) | V84 | EXTEND V5 | V5 just landed |
| 21st (V85) | V85 | LAND V6 blueprint | V5 substantiated (3rd strategic pivot) |
| **22nd (V86)** | **V86** | **LAND V7 Live Solver Trigger** | **Mandate wording shifted → pivot from demo substrate to actual capability · 4th strategic pivot since V67-C** |

## 2 · Pre-implementation surface scan (DEC-V61-088 discipline)

**Run BEFORE charter §3 sub-DEC enumeration:**

1. **ROADMAP scan**: 6-arc live-solver-hookup carry (V80+V81+V82+V83+V84+V85) is the dominant structural debt per V85 close §8 + V85 retro Open Q #1.

2. **Existing-implementation grep**: `grep -rn "^@router.post" ui/backend/routes/` found 25 POST routes. `grep -rn "solve" ui/backend/routes/case_solve.py` found two pre-existing live-solver endpoints:
   - `POST /api/import/{case_id}/solve-stream` (SSE-streaming · `case_solve.py:674-756`)
   - `POST /api/import/{case_id}/solve` (blocking · `case_solve.py:759+`)
   Both already counted in `MUTATING_ROUTES = 9` baseline (per `scripts/governance/v68b_fleet/audit_ai_advisory.sh:14`).

3. **Frontend gap analysis**: `grep -rn "solve-stream\|/solve\b" ui/frontend/src/pages/workbench/v3/` returned ZERO matches. The legacy `ui/frontend/src/pages/workbench/step_panel_shell/SolveStreamContext.tsx` wires both endpoints, but **the v3 workbench (V71-V85 substrate) has no Run-Solver affordance**.

**Disposition decision (per DEC-V61-088 + user-selected option a):**
- (a) **Extend** — reuse existing `/api/import/{id}/solve-stream` from v3 workbench · CONFIRMED
- (b) parallel new — REJECTED (endpoint duplication)
- (c) refactor + consolidate — REJECTED (legacy migration scope too large for one arc)

**Implication**: V86 is a **frontend wiring arc**, NOT a backend pivot. V132 MUTATING_ROUTES count stays at 9. No new auth surface. No v2.2 1-sync-trigger hit. No Codex round required. 8-arc no-scoring-change streak target preserved.

## 3 · What V86 is building (concrete sub-DECs · V7 contracts)

| Sub-DEC | V7 contract | Headline |
|---|---|---|
| **V86.1** | (blueprint document) | V7 blueprint LANDED at `.planning/blueprints/v7/INDEX.md` · 4 contracts (V7.A-D) + reverse-stops + 4Q gate · disposition (a) extend documented |
| **V86.2** | V7.A Run Solver Button | `RunSolverButtonV7` component in v3 Engineer Control Rail · USER-clickable affordance (no auto-trigger · V130 invariant) · disabled when prerequisites unmet (mesh missing / BC not setup) · POSTs to existing `/api/import/{case_id}/solve-stream` · contract tests for V130 |
| **V86.3** | V7.B Run State Machine | `useSolverRunStateV7` hook · idle → starting → running → done/failed/cancelled transitions · cancellable from UI · prerequisite gating · contract tests for all state transitions |
| **V86.4** | V7.C Live Residual Bridge | SSE stream from `/solve-stream` wired into v3 `ResidualsChartV3` + LIVE pill in TopBar · existing `useSseResidualStream` hook reused · contract tests that V82.4 4-layer realism model display gracefully accepts real SSE OR curated stream |
| **V86.5** | V7.D Post-Run Hand-off | Completed real `run_id` feeds into V6 bridge `BridgeArtifact` loader · audit-package auto-build on successful completion · run_id surfaces in TopBar provenance line · contract tests |
| **V86.6** | (close + retro) | V78 fleet score iter-0/1/2 · 100/100 × 2 consec · DEC-V86-close · V86 retro · 9-arc no-scoring-change streak target · 6-arc live-solver-hookup carry CLOSED |

## 4 · V79+...+V85-discipline commitment (carried into V86 · 9th arc target)

V78: threshold tightening (framework changed).
V79: feature parity.
V80: V4 blueprint LANDED.
V81: V4 substrate depth.
V82: V4 substrate completion.
V83: V5 blueprint LANDED.
V84: V5 substrate depth.
V85: V6 blueprint LANDED.
**V86: V7 Live Solver Trigger LAND (9th consecutive no-framework-change arc target).**

V86 reverse-stops carry all prior:
- ❌ NO new pillar (V78 carry · 9th arc)
- ❌ NO new subscore (V79 carry · 8th arc)
- ❌ NO V78 scorer threshold change (V79 carry · 8th arc)
- ❌ NO new scorer script (V80 carry · 7th arc · no `v86_fleet/`)
- ❌ Advisor commentary MUST remain human-curated (V80 carry · 7th arc)
- ❌ Aggressive demo UX MUST NOT appear (V80 carry · 7th arc)
- ❌ V81.4 `--arc-label` flag backward compat (V81 carry · 6th arc)
- ❌ V82.4 SSE generator MUST stay LLM-offline + GET-only WHEN curated path active (V82 carry · 5th arc · CLARIFIED: V7.C wires REAL SSE from `/solve-stream` but curated path remains intact for `?bridge` and demo flows)
- ❌ V83.4 cinematic auto-advance MUST stay cancellable + respect `prefers-reduced-motion` (V83 carry · 4th arc)
- ❌ V83.2 sandbox MUST NOT call mutating backend endpoints (V83 carry · 4th arc · V7.A Run button is engineer-control-rail surface, NOT sandbox surface)
- ❌ V83.5 provenance card analytics-free (V83 carry · 4th arc)
- ❌ V84.5 multi-case sandbox per-case data human-curated (V84 carry · 3rd arc)
- ❌ V85.X V6 bridge MUST stay READ-ONLY for `?bridge=1` flow (V85 carry · 2nd arc · V7.D post-run hand-off SURFACES the real run_id but bridge mode itself reads the resulting artifact, doesn't trigger another run)
- **NEW V7**: Run Solver button MUST be a USER-clickable affordance · NO auto-trigger from AI · NO timer-based auto-execute · NO programmatic invocation outside of user click event (V130 invariant explicit)
- **NEW V7**: Run Solver button MUST be in Engineer Control Rail, NOT in sandbox/cinematic/bridge surfaces (those stay read-only · V7 is engineer-mode capability)
- **NEW V7**: Run state transitions MUST be cancellable from UI (no runaway runs · user retains stop control)
- **NEW V7**: V132 MUTATING_ROUTES count MUST stay at 9 (no new endpoint added · reuses existing `/solve-stream`)
- **NEW V7**: V82.4 curated 4-layer SSE generator path stays operational alongside real-SSE wiring (curated mode default · real mode opt-in via user click)

## 5 · What V86 is NOT building (charter §5 disclosures)

- ❌ **New POST endpoint** — surface scan found existing `/api/import/{case_id}/solve-stream` · disposition (a) extend confirmed · V132 stays at 9
- ❌ **New auth surface** — no Codex round triggered · v2.2 1-sync-trigger not hit
- ❌ **Solver execution from AI agent path** — V7.A button is USER-only · `foam_agent_adapter.py` AI-trigger path remains unchanged (V130 invariant intact)
- ❌ **V8 blueprint** — V7 just landing · multiple blueprints per arc is substrate inflation
- ❌ **Real-data bridge for all 10 cases** — V6 bridge known-cases stays at lid_driven_cavity only (per V85.2 conservative list) · post-run hand-off (V7.D) ADDS new run_ids to the list dynamically when triggered, but the static `BRIDGE_KNOWN_CASES` list doesn't grow
- ❌ **Cross-case run comparison** — V7+ candidate · not in scope
- ❌ **Legacy step-panel-shell consolidation** — disposition (c) was rejected · legacy paths continue parallel · V86+ candidate
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 9-arc streak target invariant

## 6 · Reverse-stops (V86)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9 · V7 reuses existing endpoint)
2. Any AI-auto-execute of the Run button (V130 invariant · button MUST be USER-click only)
3. NO new pillar (9th arc target)
4. NO new subscore (8th arc carry)
5. NO V78 scorer threshold change (8th arc carry)
6. NO new scorer script (7th arc carry)
7. AI advisor commentary text MUST be human-curated (7th arc carry)
8. Demo mode aggressive UX (7th arc carry)
9. V81.4 `--arc-label` backward compat (6th arc carry)
10. V82.4 SSE curated generator + route discipline (5th arc carry · V7.C wires REAL SSE without breaking curated path)
11. V83.4 cinematic auto-advance discipline (4th arc carry)
12. V83.2 sandbox no-mutating-backend discipline (4th arc carry · V7.A is engineer-rail, NOT sandbox)
13. V83.5 provenance card analytics-free (4th arc carry)
14. V84.5 multi-case sandbox curated outcomes (3rd arc carry)
15. V85.X V6 bridge READ-ONLY (2nd arc carry)
16. **NEW**: V7.A Run button = USER-click only · no AI auto-trigger · no timer auto-execute · no programmatic invocation
17. **NEW**: V7.A surfaces in Engineer Control Rail only · NOT in sandbox / cinematic / bridge surfaces
18. **NEW**: V7 run state cancellable from UI · no runaway runs
19. **NEW**: V7.D post-run hand-off preserves V6 bridge READ-ONLY semantics (post-run artifacts are read, never re-triggered automatically)
20. Any of 83 V85-validated baselines drift
21. axe-core finds WCAG violations on any of Steps 1-5

## 7 · 4Q gate (every V86 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V7.A button is user-click · V7.B state machine is deterministic · V7.C SSE wiring works without LLM · V7.D hand-off reads artifacts (no LLM call)
2. **Artifacts emitted?** ✓ Real solver run emits canonical `reports/{case_id}/runs/{run_id}/` artifacts · V7.D wires them into V6 bridge
3. **TrustGate intact?** ✓ Audit-package auto-build on successful completion (V7.D) · run_id surfaces in TopBar provenance · existing `/audit-packages/{bundle}/manifest.json` GET endpoint reused
4. **AI advisory only?** ✓ Run button is USER-clicked · AI does NOT trigger solver · V130 invariant intact · denylist test for "auto-trigger" / "AI runs" patterns in V7.A contract

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V85 substrate carried · V86 substrate landed before scoring | 100/100 (V83/V85 pattern · clean steady-state baselines) |
| 1 | Substrate re-confirm | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 9 · Counter telemetry (estimated)

- V86-charter: B281
- V86.1-V86.6: B282-B287 estimated
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 10 · The bigger picture (9-arc commitment target)

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
| V85 | 0 | 0 | 0 | 0 | V6 blueprint + Real-Artifact Bridge |
| **V86** | **0** | **0** | **0** | **0** | **V7 Live Solver Trigger: 4 contracts (V7.A button + V7.B state · V7.C live SSE · V7.D post-run handoff) · disposition (a) extend · 6-arc live-solver-hookup carry CLOSED** |

V78+V79+V80+V81+V82+V83+V84+V85+V86 = **9-arc** streak target. The framework continues to absorb depth without growing — including a strategic pivot from "demo-layer-only" (V4 + V5) to "demo-layer + real-data bridge" (V6) to **"demo-layer + bridge + USER-triggered real solver capability"** (V7).

— DEC-V86-charter · 2026-05-17 · LANDED
