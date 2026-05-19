---
decision_id: DEC-V87-charter
title: V87 charter · 23rd V110 advisor-class arc · "全权授权继续" continuation pattern (mirror V82 post-pivot completion) · V7 substantiation arc (mount + visual baselines + e2e + schema-drift guard) · mirror V81/V84 pattern · 10th consecutive no-scoring-change arc target
status: Accepted
parent_dec: DEC-V86-close
phase: V87
notion_sync_status: pending
predecessor: DEC-V86-close
batch: B288
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V87-charter (bootstrap)
substrate: V86 closed 16/16 × 3 consec under unchanged V78 scoring · V7 LANDED but NOT yet mounted in WorkbenchShellV3 (V86 close §5 + retro Open Q #1 explicit) · 23rd directive is "全权授权继续" continuation (no mandate wording shift · mirror V82 "完成所有建议" pattern post-V81) · interpretation: V7 substantiation (depth · not new blueprint)
---

# DEC-V87-charter · V87 V7-Substantiation Arc · CHARTER

## 1 · Directive (23rd invocation · continuation pattern · mirror V82)

> "全权授权继续"

This is the **2nd continuation-pattern directive** in the V80+ cohort (the 1st was V82's "批准你全权开发，继续，完成所有建议" between V81 substantiation and V83 V5-land). Pattern:

| Directive # | Arc | Form | Interpretation |
|---|---|---|---|
| 16th (V80) | V80 | full mandate | LAND V4 blueprint |
| 17th (V81) | V81 | verbatim re-issue | EXTEND V4 (1st substantiation) |
| **18th (V82)** | **V82** | **"完成所有建议" continuation** | **COMPLETE V4 (post-substantiation polish)** |
| 19th (V83) | V83 | verbatim re-issue | LAND V5 blueprint |
| 20th (V84) | V84 | verbatim re-issue | EXTEND V5 (2nd substantiation) |
| 21st (V85) | V85 | verbatim re-issue | LAND V6 blueprint |
| 22nd (V86) | V86 | **non-verbatim "CFD能力"** | LAND V7 Live Solver Trigger (4th strategic pivot · 1st wording-shift) |
| **23rd (V87)** | **V87** | **"全权授权继续" continuation** | **V7 substantiation (mount + baselines + e2e + schema-drift guard)** |

V86 just LANDED the V7 contracts as **orthogonal pieces** (component + 3 hooks · 4 contract test files · 49 tests). V86 close §5 explicitly disclosed:

> "WorkbenchShellV3 integration of V7.A button — V86 lands the V7 contracts (component + hooks) but does NOT yet mount them in the v3 shell. V87 candidate (small follow-up · estimated ≤2 sub-DECs)"

V86 retro Open Q #1:
> "WorkbenchShellV3 integration of V7.A + V7.C — the substantiation arc · mirror V81/V84 pattern."

V87 honors that forecast. The "继续" continuation directive matches V82's pattern of completing/substantiating the preceding land arc.

## 2 · Pre-implementation surface scan (DEC-V61-088 discipline · re-confirmed)

**Run BEFORE charter §3 sub-DEC enumeration:**

1. **V86 close §8 forecast**: WorkbenchShellV3 mount + visual baselines + e2e + schema-drift guard explicitly listed as V87 candidates.

2. **Mount-status grep**: `grep -n "RunSolverButtonV7\|LiveSolverPillV7\|useSolverRunStateV7\|usePostRunHandoffV7" ui/frontend/src/pages/workbench/v3/ -r --exclude-dir=__tests__` returned ONLY the V7 component/hook self-references — confirming **zero shell integration** to date.

3. **Engineer Control Rail check**: V86 retro disclosed "Engineer Control Rail" is conceptual (no `EngineerControlRailV3.tsx` file). Plausible mount points:
   - `BottomPanelV3.tsx` collapsed bar (Step 4 entry · already shows "streaming" pill at Step ≥4 · natural Run button neighbor)
   - `TopBarV3.tsx` (V7.C LIVE pill belongs here · adjacent to existing run_id provenance)
   Choose BottomPanelV3 for the button (Step 4 spatial · engineer-mode neighbor) and TopBarV3 for the pill (visible across all steps when run active).

4. **V132 baseline re-confirm**: `MUTATING_ROUTES = 9` carry from V86. V87 is mount-and-wire work · zero new endpoints · count stays locked.

**Disposition**: V87 is pure frontend substantiation. No backend changes. No Codex round triggered. 4Q gate intact.

## 3 · What V87 is building (concrete sub-DECs · mirror V81/V84)

| Sub-DEC | Headline |
|---|---|
| **V87.1** | WorkbenchShellV3 V7 integration: mount `RunSolverButtonV7` in `BottomPanelV3` collapsed bar (Step 4 entry) · wire `useSolverRunStateV7` + `usePostRunHandoffV7` in `WorkbenchShellV3` · mount `LiveSolverPillV7` in `TopBarV3` · feed `lastCompletedRunId` into `DemoSandboxV5` bridgeArtifact pipeline via existing `useQuery` to `/api/cases/{id}/run-history/{run_id}` · shell-integration contract tests |
| **V87.2** | V7 visual baselines (3 new): 84 run-solver-button-idle · 85 run-solver-button-disabled-with-hint · 86 live-solver-pill-running · all steady-state (no post-click async-mount per V84.6 lesson) |
| **V87.3** | V7 e2e Playwright specs: `v87-v7-live-solver.spec.ts` · 4-5 specs (prereq-gated disable · click triggers POST · cancel mid-run · post-run handoff into bridge · network-mutation guard) |
| **V87.4** | V7.B SSE schema-drift Zod guard: runtime schema validation at parse boundary in `useSolverRunStateV7` · invalid events degrade gracefully (no crash · no state corruption) · closes V85+V86 retro Open Q (2-arc carry) |
| **V87.5** | Final verification + close + retro · 10-arc no-scoring-change streak target |

V86 retro Open Qs that V87 does NOT pull in:
- #5 Multi-run timeline UI (V8+ candidate)
- #6 Live-vs-curated diff with V7 streaming residuals (V8+ candidate · V6.C currently static-vs-static)
- #7 Legacy step-panel-shell consolidation (disposition (c) rejected at V86 · V88+ candidate)
- #8 V8 blueprint (V7 just landed · premature)
- #9 Firefox + Webkit install (8-arc carry · WONTFIX candidate · V88+)
- #10 YAML migration of advisor_commentary (6-arc carry)

## 4 · V79+...+V86-discipline commitment (carried into V87 · 10th arc target)

V78: threshold tightening (framework changed).
V79-V86: 9-arc no-framework-change streak (see V86 close §6).
**V87: V7 substantiation (10th consecutive no-framework-change arc target).**

V87 reverse-stops carry all prior (full V86 reverse-stop list §6 inherited):
- ❌ NO new pillar / subscore / threshold change / scorer script (10-arc target)
- ❌ V130 Run button USER-click only · denylist enforced at shell integration too (no parent-level useEffect calling `request()`)
- ❌ V132 MUTATING_ROUTES = 9 (no new endpoint · uses existing `/solve-stream` + `/audit-package/build` + `/run-history`)
- ❌ V7.A in Engineer Control Rail conceptual location only · NOT in sandbox/cinematic/bridge surfaces (V86 reverse-stop #17 enforced at mount site)
- ❌ V83.2 sandbox no-mutating-backend · V87.1 must NOT add Run button to sandbox UI surface
- ❌ V85.X V6 bridge READ-ONLY · V87.1 post-run handoff feeds bridge but bridge mode itself stays read-only
- **NEW V87**: WorkbenchShellV3 integration of V7.A MUST keep the button BEHAVIORALLY disabled when sandbox/cinematic/bridge URL mode is active (these modes are read-only; clicking Run while in them would be confusing) · OR alternately, hide the button entirely in those modes — implementation choice
- **NEW V87**: V7 visual baselines MUST be steady-state (no post-click captures) · V84.6 lesson honored
- **NEW V87**: V87.4 schema-drift guard MUST degrade gracefully (invalid event → log + skip · NOT crash / NOT state corruption)

## 5 · What V87 is NOT building (charter §5 disclosures)

- ❌ **New POST endpoint** — V132 stays at 9 · V86 disposition (a) extend carry
- ❌ **AI-triggered solver path** — `foam_agent_adapter.py` unchanged · V130 invariant
- ❌ **Multi-run timeline UI** — V8+ candidate
- ❌ **Legacy step-panel-shell consolidation** — V88+ candidate (disposition (c) deferred)
- ❌ **V8 blueprint** — premature · V87 is substantiation arc
- ❌ **Cross-case parallel runs** — V8+ candidate
- ❌ **Configurable solver flags from UI** — V8+ candidate
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 10-arc streak target

## 6 · Reverse-stops (V87)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9 · 7th arc carry)
2. Any AI-auto-execute of the Run button (V130 invariant · 2nd arc carry)
3. NO new pillar (10th arc target)
4. NO new subscore (9th arc carry)
5. NO V78 scorer threshold change (9th arc carry)
6. NO new scorer script (8th arc carry · no `v87_fleet/`)
7. AI advisor commentary human-curated (8th arc carry)
8. Demo mode aggressive UX (8th arc carry)
9. V81.4 `--arc-label` backward compat (7th arc carry)
10. V82.4 SSE curated generator route discipline (6th arc carry · V87.1 wires REAL SSE alongside curated)
11. V83.4 cinematic auto-advance discipline (5th arc carry)
12. V83.2 sandbox no-mutating-backend (5th arc carry · V87 must NOT add Run button to sandbox surface)
13. V83.5 provenance card analytics-free (5th arc carry)
14. V84.5 multi-case sandbox curated outcomes (4th arc carry)
15. V85.X V6 bridge READ-ONLY (3rd arc carry · V87.1 post-run handoff respects this)
16. V86 V7.A USER-click only (2nd arc carry · MUST hold across shell integration)
17. V86 V7.A in Engineer Control Rail only (2nd arc carry · V87.1 mount site must respect this)
18. V86 V7 run cancellable (2nd arc carry)
19. V86 V7.D V6 bridge READ-ONLY semantics (2nd arc carry)
20. **NEW**: V7.A behavioral disable (or hide) when URL has `?demo=2` OR `?demo=1&cinema=1` OR `?bridge=1` (those are read-only modes · Run click would be confusing)
21. **NEW**: V7 visual baselines MUST be steady-state (V84.6 lesson)
22. **NEW**: V87.4 schema-drift guard MUST degrade gracefully (invalid events skipped · NOT crash)
23. Any of 83 V85-validated baselines drift (86+ if V87.2 lands new baselines)

## 7 · 4Q gate (every V87 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V87.1 is shell mounting (no LLM) · V87.2 baselines are PNG captures · V87.3 e2e uses mock SSE (no LLM) · V87.4 Zod is deterministic schema check
2. **Artifacts emitted?** ✓ When V87.1 mounts and a user runs a real solver, the audit-package auto-build (V7.D · V86 carry) fires · real artifacts land in `reports/{case}/runs/{run_id}/`
3. **TrustGate intact?** ✓ V7.D audit-package on completion · run_id in TopBar provenance · existing `/audit-packages/{bundle}/manifest.json` GET endpoint surfaces manifest
4. **AI advisory only?** ✓ Run button is USER-clicked · V87.1 mount site is BottomPanelV3 collapsed bar (NOT sandbox / cinematic / bridge · V83.2 + V83.4 + V85.X carries) · V130 denylist enforced at shell level too

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V86 substrate carried · V87 substrate landed before scoring | 100/100 (V83/V85/V86 pattern · steady-state baselines) OR 86/9X if V87.2 baselines drift (V84.6 risk class) |
| 1 | Substrate re-confirm (post-fix if iter-0 drifted) | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 9 · Counter telemetry (estimated)

- V87-charter: B288
- V87.1-V87.5: B289-B293
- All `autonomous_governance: true`
- Counter contribution: **+6** · arc within v2.3 cadence floor 30

## 10 · The bigger picture (10-arc commitment target)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 | +4 | 4 new | tooling debts |
| V79-V86 (8 arcs) | 0 | 0 | 0 | 0 | 4 strategic pivots (V4/V5/V6/V7) + 2 substantiations (V81/V84) + V82 completion + V79 parity |
| **V87** | **0** | **0** | **0** | **0** | **V7 substantiation: shell mount + 3 visual baselines + 4-5 e2e specs + SSE schema-drift Zod guard** |

V78+V79+V80+V81+V82+V83+V84+V85+V86+V87 = **10-arc** streak target. Symbolic milestone: 10 consecutive arcs with NO scoring framework changes, across 4 strategic pivots and 1 mandate-wording-shift pivot.

— DEC-V87-charter · 2026-05-17 · LANDED
