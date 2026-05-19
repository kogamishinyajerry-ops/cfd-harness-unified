---
decision_id: DEC-V88-charter
title: V88 charter · 24th V110 advisor-class arc · 2nd "CFD能力" verbatim re-issue (after V86 LAND + V87 substantiation) · V8 Solver Configuration Editor blueprint LAND · disposition (a) extend existing POST /api/cases/{id}/dicts/{relative_path:path} · V132 stays at 9 · 11th consecutive no-scoring-change arc target
status: Accepted
parent_dec: DEC-V87-close
phase: V88
notion_sync_status: pending
predecessor: DEC-V87-close
batch: B294
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V88-charter (bootstrap)
substrate: V87 closed 16/16 × 3 consec under unchanged V78 scoring · 10-arc streak attained · V7 fully integrated (button + state machine + live SSE + post-run handoff + schema-drift guard) · current Run flow uses solver DEFAULTS only · 24th directive is 2nd verbatim of "CFD能力" wording · interpretation: V8 Solver Configuration Editor LAND (5th strategic pivot · extends V7 capability axis)
---

# DEC-V88-charter · V88 V8-Solver-Config-Editor Arc · CHARTER

## 1 · Mandate (24th invocation · 2nd verbatim re-issue of "CFD能力" wording)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程**CFD能力**），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

**Mandate-wording tracking (V80+ cohort):**

| Mandate # | Arc | Wording | Interpretation |
|---|---|---|---|
| 16th (V80) | V80 | "AI CFD demo展示" (1st of 5) | V4 LAND |
| 17th (V81) | V81 | verbatim re-issue | V4 substantiation |
| 18th (V82) | V82 | "完成所有建议" (continuation) | V4 completion |
| 19th (V83) | V83 | verbatim re-issue | V5 LAND |
| 20th (V84) | V84 | verbatim re-issue | V5 substantiation |
| 21st (V85) | V85 | verbatim re-issue | V6 LAND |
| 22nd (V86) | V86 | **non-verbatim "CFD能力" (1st)** | V7 LAND (4th strategic pivot · wording shift) |
| 23rd (V87) | V87 | "全权授权继续" (continuation) | V7 substantiation |
| **24th (V88)** | **V88** | **verbatim "CFD能力" (2nd)** | **V8 LAND (5th strategic pivot · wording-cohort 2nd verbatim parallels V80→V83 jump)** |

V86-V87-V88 mirrors V80-V81+V82-V83 pattern:
- V86 (CFD能力 1st) ≈ V80 (demo展示 1st) — first wording cohort LAND
- V87 (continuation) ≈ V81+V82 collapsed (substantiate + complete the LAND)
- **V88 (CFD能力 2nd verbatim) ≈ V83 (demo展示 3rd verbatim) — NEXT LAND in the cohort**

The verbatim re-issue of "CFD能力" after a substantiation/continuation arc signals a NEW blueprint LAND within the capability axis. Per V87 retro Open Q #8 + AskUserQuestion sequence, the user selected **V8 Solver Configuration Editor** (extend V7 USER-triggered execution with USER-controlled solver settings).

## 2 · Pre-implementation surface scan (DEC-V61-088 discipline · 2nd round of the V86 lesson)

**Run BEFORE charter §3 sub-DEC enumeration:**

1. **V87 retro Open Q forecasts**: 3 candidate V8 axes surfaced (solver-config-editor / BC-editor / V6 backfill). User-selected via AskUserQuestion: solver-config-editor.

2. **Backend endpoint scan**: `grep -n "^@router.post" ui/backend/routes/case_dicts.py` found `POST /api/cases/{case_id}/dicts/{relative_path:path}` (case_dicts.py:202) with `RawDictPostBody` schema. Already counted in `MUTATING_ROUTES = 9` baseline (per V86 surface scan).

3. **Companion GET**: `GET /api/cases/{case_id}/dicts/{relative_path:path}` returns `{content, source, etag, edited_at}` (case_dicts.py:144). ETag-based optimistic concurrency · 409 on mismatch · structured 422 on validation failure.

4. **Frontend client scan**: `grep -n "case-dicts\|dicts" ui/frontend/src/api/client.ts` found:
   - `api.listRawDicts(caseId)` (line 885)
   - `api.getRawDict(caseId, relativePath)` (line 894) — ETag + source + content
   - `api.postRawDict(caseId, relativePath, body, options)` (line 927) — ETag-aware POST
   All 3 already plumbed. V8 frontend is pure consumer wiring.

5. **v3 mount-status grep**: `grep -rn "case-dicts\|getRawDict\|postRawDict" ui/frontend/src/pages/workbench/v3/` returned zero non-test references — confirming **zero v3 wiring** for solver config editing.

**Disposition decision**: (a) **Extend** — V8 reuses existing GET/POST `/dicts/{path}` endpoints + existing client methods. V132 stays at 9. No Codex round triggered (no new security boundary). 4Q gate intact.

## 3 · What V88 is building (concrete sub-DECs · V8 contracts)

| Sub-DEC | V8 contract | Headline |
|---|---|---|
| **V88.1** | (blueprint document) | V8 blueprint LANDED at `.planning/blueprints/v8/INDEX.md` · 4 contracts (V8.A-D) + reverse-stops + 4Q gate · ~200 lines · disposition (a) extend documented |
| **V88.2** | V8.A SolverConfigEditor | `SolverConfigEditorV8.tsx` component · controlDict fields (application · endTime · deltaT · writeInterval · writeFormat) · USER-edit form · NO auto-write affordance · explicit "Review changes" gate before commit · V130 lexical denylist tests · structural mount-time fetch-zero-call assertions |
| **V88.3** | V8.B Validation Surface | `solver_config_validator.ts` pure validation logic · rejects malformed values (negative endTime · invalid solver name · deltaT > endTime · etc.) · returns structured `{ field: string, kind: "negative"\|"too_large"\|"invalid_solver"\|"missing", message: string }[]` errors · contract tests cover all edge cases |
| **V88.4** | V8.C Diff Preview | `SolverConfigDiffV8.tsx` component · two-column display: current-vs-pending controlDict · highlights changed fields · "review then commit" flow (no auto-commit · V130 invariant) · contract tests · V130 denylist for "auto-commit" / "automatic" verbiage |
| **V88.5** | V8.D Run-Readiness Signal | `useSolverConfigStateV8.ts` hook · tracks `state ∈ {clean, dirty, saving, saved, error}` · exposes `configReady` boolean for V7.A Run button gate · feeds completed save into V7.A `bcSetup` (or equivalent prereq slot) · contract tests cover V8→V7 handoff |
| **V88.6** | (close + retro) | V78 fleet score iter-0/1/2 · 100/100 × 2 consec · DEC-V88-close · V88 retro · 11-arc no-scoring-change streak target |

V87 retro Open Qs that V88 does NOT pull in:
- #1 State-injection harness for V7.C running-state baseline (V89+ candidate)
- #2 WorkbenchShellV3 shell-level contract test (V89+ candidate)
- #3 Run button in expanded BottomPanel state (V89+ candidate)
- #4 Legacy step-panel-shell consolidation (3-arc carry now)
- #5 Multi-run timeline UI (V9+ candidate)
- #6 Live-vs-curated diff with V7 streaming residuals (V9+ candidate)
- #9 Firefox + Webkit install (10-arc carry)
- #10 YAML migration of advisor_commentary (8-arc carry)

## 4 · V79+...+V87-discipline commitment (carried into V88 · 11th arc target)

V78-V87 = 10-arc no-framework-change streak.
**V88: V8 Solver Configuration Editor LAND (11th consecutive no-framework-change arc target).**

V88 reverse-stops carry all prior (full V87 reverse-stop list §6 inherited):
- ❌ NO new pillar / subscore / threshold change / scorer script (11-arc target)
- ❌ V130 USER-click only · denylist enforced at SolverConfigEditor (no useEffect auto-write of dicts · no AI-triggered commit) · structural mount-time fetch-zero-call assertion
- ❌ V132 MUTATING_ROUTES = 9 (no new endpoint · uses existing `/dicts/{path}` POST)
- ❌ V7.A in Engineer Control Rail only · V8.A also Engineer-mode (mounts adjacent to V7.A or in Right Panel Inspector tab · NOT sandbox/cinematic/bridge)
- ❌ V83.2 sandbox no-mutating-backend · V88 must NOT add solver-config write affordance to sandbox surface
- ❌ V85.X V6 bridge READ-ONLY · V88 solver-config-editor writes case dicts but bridge mode itself stays read-only (NOT mounting V8.A inside bridge surface)
- ❌ V87.4 schema-drift discipline · V8.B validator should integrate with the existing 422-error response shape from POST /dicts/{path}
- **NEW V88**: V8.A solver-config edit MUST go through explicit USER review (V8.C diff preview) BEFORE commit · no one-click "save and commit" shortcut · matches V7.A's user-click discipline
- **NEW V88**: V8.A commits MUST surface the ETag in the manifest audit trail (existing case-dicts endpoint already does this · V8.A just doesn't bypass it)
- **NEW V88**: Validation errors MUST surface to the user pre-commit · NEVER silently accepted (V130: AI must not auto-fix · user must see + decide)
- **NEW V88**: V8.D configReady signal MUST be inspectable by V7.A Run button (decouple via shared state in WorkbenchShellV3 · NOT V7.A directly importing V8.D)

## 5 · What V88 is NOT building (charter §5 disclosures)

- ❌ **New endpoint** — V132 stays at 9 · disposition (a) extend
- ❌ **AI-suggested config presets** — V130 invariant · V8 is USER editor only · AI suggestions = V9+ candidate (would need separate denylist guardrails)
- ❌ **Multi-file dict batch editor** — V8.A edits one dict at a time (controlDict initially) · multi-file commit = V9+ candidate
- ❌ **fvSchemes / fvSolution editors** — V8 starts with controlDict only (most user-impactful · time controls + solver name) · other dicts = V9+ extension
- ❌ **History / undo stack** — V8.A relies on existing case-dicts manifest audit trail (every commit records source=user) · in-UI undo = V9+ candidate
- ❌ **BC editor in UI** — V88 user-selected against this in axis-pick · BC editor = V89+ candidate
- ❌ **V9 blueprint** — V8 just landing · multiple blueprints per arc is substrate inflation
- ❌ **Firefox + Webkit install** — 10-arc carry · WONTFIX candidate
- ❌ **YAML migration of advisor_commentary** — 8-arc carry
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 11-arc streak target

## 6 · Reverse-stops (V88)

1. V132 MUTATING_ROUTES net diff > 0 (locked at 9 · 8th arc carry)
2. Any AI-auto-execute of solver-config commit (V130 invariant · NEW for V8 · enforced at V8.A + V8.D)
3. NO new pillar (11th arc target)
4. NO new subscore (10th arc carry)
5. NO V78 scorer threshold change (10th arc carry)
6. NO new scorer script (9th arc carry · no `v88_fleet/`)
7. AI advisor commentary human-curated (9th arc carry)
8. Demo mode aggressive UX (9th arc carry)
9. V81.4 `--arc-label` backward compat (8th arc carry)
10. V82.4 SSE curated generator route discipline (7th arc carry)
11. V83.4 cinematic auto-advance discipline (6th arc carry)
12. V83.2 sandbox no-mutating-backend (6th arc carry · V88 solver-config NOT in sandbox surface)
13. V83.5 provenance card analytics-free (6th arc carry)
14. V84.5 multi-case sandbox curated outcomes (5th arc carry)
15. V85.X V6 bridge READ-ONLY (4th arc carry · V8.A must NOT mount inside bridge surface)
16. V86 V7.A USER-click only (3rd arc carry)
17. V86 V7.A in Engineer-mode only (3rd arc carry · V8.A also Engineer-mode)
18. V86 V7 run cancellable (3rd arc carry)
19. V86 V7.D V6 bridge READ-ONLY semantics (3rd arc carry)
20. V87 V7.A behavioral disable in read-only modes (2nd arc carry · V8.A SAME · disable in `?demo=2` / `?bridge=1`)
21. V87 V7 visual baselines steady-state (2nd arc carry · V88 baselines also steady-state)
22. V87 V7.B schema-drift guard graceful degrade (2nd arc carry · V8.B validator integrates 422 errors gracefully)
23. **NEW**: V8.A edits MUST go through explicit V8.C diff preview before commit (no one-click save+commit)
24. **NEW**: V8.A validation errors MUST surface pre-commit (NEVER silently accepted · user MUST see + decide)
25. **NEW**: V8.D configReady signal decoupled via shell-level shared state (NOT V7.A importing V8.D directly)
26. **NEW**: V8 visual baselines MUST be steady-state (V84.6 lesson · 4th arc carry for baseline discipline)
27. Any of 86 V87-validated baselines drift (90+ if V88 lands new baselines)

## 7 · 4Q gate (every V88 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V8.A is form UI · V8.B is deterministic validation · V8.C is pure diff · V8.D is local state machine · no LLM call anywhere
2. **Artifacts emitted?** ✓ V8.A commits write case-dicts (existing endpoint records source=user in manifest) · changes flow into subsequent V7-triggered solver runs · audit-package captures committed config
3. **TrustGate intact?** ✓ Every V8 commit records to manifest with source=user + new ETag · existing `/audit-packages/{bundle}/manifest.json` surface continues to expose this
4. **AI advisory only?** ✓ V8.A is USER form · V130 denylist enforced on edit + commit affordances · structural mount-time fetch-zero-call assertions in tests · existing case-dicts endpoint already enforces "source=user" override on every successful POST

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline under V78 scorers · V87 substrate carried · V88 substrate landed before scoring | 100/100 (V83/V85/V86/V87 pattern · steady-state baselines · V84.6 lesson held for 5th arc) |
| 1 | Substrate re-confirm | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 9 · Counter telemetry (estimated)

- V88-charter: B294
- V88.1-V88.6: B295-B300
- All `autonomous_governance: true`
- Counter contribution: **+7** · arc within v2.3 cadence floor 30

## 10 · The bigger picture (11-arc commitment target · 5th strategic pivot)

| Arc | Pillars added | Subscores added | Thresholds changed | Scorer scripts created | Substrate landed |
|---|---|---|---|---|---|
| V67-C..V77 (9 arcs) | +9 (7→16) | many | many | many | proportional |
| V78 | 0 | +3 | +4 | 4 new | tooling debts |
| V79-V87 (9 arcs) | 0 | 0 | 0 | 0 | 4 strategic pivots (V4/V5/V6/V7) + 3 substantiations (V81/V84/V87) + V82 completion + V79 parity + 1 wording-shift (V86) + 2 continuations (V82 V87) |
| **V88** | **0** | **0** | **0** | **0** | **V8 Solver Configuration Editor: 4 contracts (V8.A form + V8.B validator + V8.C diff + V8.D readiness) · disposition (a) extend · 5th strategic pivot since V67-C · capability axis extension** |

V78+V79+...+V87+V88 = **11-arc** streak target. The 10-arc symbolic milestone (V87) extends one further. Framework now absorbing:
- **5 strategic-pivot blueprints** (V4 / V5 / V6 / V7 · **V8**)
- **3 substantiation arcs** (V81 / V84 / V87)
- **V82 completion** + **V79 feature parity** + **V78 threshold anchor**
- 1 mandate-wording-shift (V86 introduced "CFD能力")
- 2 continuation directives (V82 V87)
- 2 same-cohort verbatim re-issues (V86 + V88 both "CFD能力")
- All on the SAME 16-pillar scoring axis · zero pillar/subscore/threshold/script change

— DEC-V88-charter · 2026-05-17 · LANDED
