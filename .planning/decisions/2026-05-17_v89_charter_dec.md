---
decision_id: DEC-V89-charter
title: V89 charter · 25th V110 advisor-class arc · 3rd "CFD能力" verbatim re-issue (after V88 V8 LAND) · V8 substantiation arc · V83→V84 pattern · state-injection harness for V8 hard-to-reach UI states + V81.3 baseline #77 flake fix · ZERO new scoring framework changes · 12-arc no-scoring-change streak target
status: Accepted
parent_dec: DEC-V88-close
phase: V89
notion_sync_status: pending
predecessor: DEC-V88-close
batch: B301
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V89-charter (bootstrap)
substrate: V88 closed (V8 SolverConfigEditor LANDED with iter-0/1=100/iter-2=86-flake honestly recorded · 11-arc streak attained · 5 strategic-pivot blueprints landed) · current V8 visual baselines only capture steady-state (clean/readonly/step-3) · dirty/diff-open/error states unreachable in real-flow snap · pre-existing baseline #77 V81.3 ComparatorV4 chromium-flake remains an honest carry · 25th directive is 3rd verbatim "CFD能力" — interpretation: V8 substantiation (V83→V84 pattern: verbatim after LAND in same cohort = substantiate the LAND)
---

# DEC-V89-charter · V89 V8-Substantiation Arc · CHARTER

## 1 · Mandate (25th invocation · 3rd verbatim re-issue of "CFD能力" wording)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程**CFD能力**），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

**Mandate-wording tracking (V80+ cohort):**

| Mandate # | Arc | Wording | Interpretation |
|---|---|---|---|
| 16th (V80) | V80 | "AI CFD demo展示" (1st of 5) | V4 LAND |
| 17th (V81) | V81 | verbatim re-issue | V4 substantiation |
| 18th (V82) | V82 | "完成所有建议" (continuation) | V4 completion |
| 19th (V83) | V83 | verbatim re-issue | V5 LAND (next LAND in cohort) |
| 20th (V84) | V84 | verbatim re-issue | V5 substantiation |
| 21st (V85) | V85 | verbatim re-issue | V6 LAND (next LAND in cohort) |
| 22nd (V86) | V86 | "CFD能力" (1st of new wording) | V7 LAND |
| 23rd (V87) | V87 | "全权授权继续" (continuation) | V7 substantiation |
| 24th (V88) | V88 | "CFD能力" (2nd verbatim) | V8 LAND (next LAND in cohort) |
| **25th (V89)** | **V89** | **"CFD能力" (3rd verbatim)** | **V8 substantiation (V83→V84 pattern: verbatim AFTER a LAND in same cohort = substantiate the LAND · NOT next-LAND)** |

V83→V84 + V88→V89 are the two direct precedents for "verbatim immediately after a LAND in same cohort":
- V83 (V5 LAND) → V84 verbatim → V5 substantiation
- V88 (V8 LAND) → V89 verbatim → V8 substantiation (mirror)

User axis confirmation via AskUserQuestion: selected "V8 state-injection harness + flake fix (Recommended)" · strict V87-pattern substantiation: depth on existing substrate.

## 2 · Pre-implementation surface scan (DEC-V61-088 discipline · 4th round)

**Run BEFORE charter §3 sub-DEC enumeration:**

1. **V88 retro Open Q forecasts**: 12 candidate items. User-selected axis = state-injection harness + flake-fix bundle → maps to Open Q #1 (baseline #77 stability investigation) + Open Q #7 (state-injection harness for V8 dirty/diff-open/error baselines).

2. **Baseline #77 surface scan**: `grep -n "77 · V81" ui/frontend/e2e/visual-baseline.spec.ts` → line 1314 · spec is `comparator-gold-actual-lid_driven_cavity-u_centerline` · 1117×585px snapshot of the ComparatorV4 surface. Last passing in V88 iter-0/1 · V87 close · V85/V86 closes. Flaked in V88 iter-2 (both first run + re-run · same baseline).

3. **State-injection precedent scan**: `grep -rn "_test_state\|stateInject\|VITE_TEST" ui/frontend/src/` → none. V87.2 / V88.6 baselines all used real-flow steady-state. No prior precedent for state-injection in v3.

4. **V8 component scan**: V8.A `SolverConfigEditorV8` accepts state via props (state · validationErrors · errorMessage etc). V8.D `useSolverConfigStateV8` drives those props. State-injection options: (a) override V8.D hook output via URL param read at WorkbenchShellV3 level · (b) bypass V8.D entirely and feed mock state slice via test-only mount route. Option (a) preserves the component contracts intact + is simplest.

5. **V132 invariance check**: V89 adds NO new endpoints · zero mutating-route surface change · V132 = 9 preserved.

**Disposition decision**: substantiation = (a) **fix baseline #77 honestly** + (b) **state-injection via URL param read at shell level** · no new MUTATING_ROUTE · no new endpoint · no scoring framework changes.

## 3 · What V89 is building (concrete sub-DECs · V8 substantiation contracts)

| Sub-DEC | Headline | Closes V88 carry |
|---|---|---|
| **V89.1** | Baseline #77 V81.3 ComparatorV4 flake fix · re-run spec in isolation to characterize · disposition: (i) regenerate baseline PNG if real drift · OR (ii) widen `maxDiffPixelRatio` from 0.01 to a justified-noise-floor value · OR (iii) `mask` the jittering subregion. Document the chosen disposition with evidence. | V88 retro Open Q #1 · V88 honest-disclosure carry |
| **V89.2** | V8 state-injection harness · URL param `?_v89_inject=dirty\|diff_open\|error` read at WorkbenchShellV3 level · ONLY active when `import.meta.env.DEV` or `import.meta.env.MODE === 'test'` (production builds ignore the param · V130 invariant preserved · injection cannot enable AI auto-write or trigger commits) · 3 new visual baselines (90 V8 dirty · 91 V8 diff-open · 92 V8 commit-error) | V88 retro Open Q #7 · V87 retro Open Q #1 (state-injection harness pattern) |
| **V89.3** | Final verification + close + retro · V78 fleet 16-pillar 100/100 × 2-consec close gate · 12-arc no-scoring-change streak documented | (this DEC) |

V88 retro Open Qs that V89 does NOT pull in (V90+ candidates):
- #2 Snapshot-the-score-after-shell-edit playbook entry (methodology · best done as retro-time addendum once enough data accrues)
- #3 V8.A second mount in RightPanelV3 Inspector tab (surface depth · NOT substantiation depth)
- #4 fvSchemes / fvSolution editors (V9+ LAND candidate · would extend dict scope · violates V88 reverse-stop #11)
- #5 AI-suggested config presets (V9+ candidate · V130 invariant risk surface · needs separate guardrails)
- #6 Multi-file dict batch editor (V9+)
- #8 BC editor in UI (V90+)
- #9 Live-vs-curated diff with V7 streaming residuals
- #10 Legacy step-panel-shell consolidation (5-arc carry now)

## 4 · V79+...+V88-discipline commitment (carried into V89 · 12th arc target)

V78-V88 = 11-arc no-framework-change streak.
**V89: V8 substantiation (12th consecutive no-framework-change arc target).**

V89 reverse-stops carry all prior (full V88 reverse-stop list §6 inherited):
- ❌ NO new pillar / subscore / threshold change / scorer script (12-arc target)
- ❌ V130 USER-click only · state-injection MUST NOT enable AI auto-write or auto-commit · production builds MUST NOT honor the injection param
- ❌ V132 MUTATING_ROUTES = 9 (no new endpoint)
- ❌ V8.A still in BottomPanel Config-tab only · V89 does NOT add a second mount (Open Q #3 deferred to V90+)
- ❌ V8 still single-dict (controlDict) · V89 does NOT extend to fvSchemes/fvSolution (Open Q #4 deferred to V9+)
- **NEW V89 #28**: State-injection URL param MUST be gated behind `import.meta.env.DEV || import.meta.env.MODE === 'test'` · production builds discard the param silently (contract test)
- **NEW V89 #29**: State-injection MUST NOT fire ANY mutating fetch · injected `error` state shows the banner WITHOUT having attempted a POST (contract test asserts zero POST calls in injection mode)
- **NEW V89 #30**: Baseline #77 disposition MUST be evidence-backed · regenerate path requires "before/after PNG sampled · drift class characterized" note in the close DEC

## 5 · What V89 is NOT building (charter §5 disclosures)

- ❌ **New endpoint** — V132 stays at 9
- ❌ **V8.A in RightPanelV3 Inspector tab** — surface-depth, not substantiation-depth · V90+ candidate
- ❌ **fvSchemes / fvSolution editors** — V9+ LAND candidate · would violate single-dict reverse-stop
- ❌ **AI-suggested presets** — V130 invariant risk · V9+ candidate
- ❌ **Multi-file batch editor** — V9+ candidate
- ❌ **BC editor in UI** — V90+ candidate
- ❌ **V9 blueprint** — V8 just substantiating · multiple blueprints per arc is substrate inflation
- ❌ **Firefox + Webkit install** — 12-arc carry · WONTFIX candidate
- ❌ **YAML migration of advisor_commentary** — 10-arc carry
- ❌ **Pillar 17 / new subscore / threshold change / scorer script** — 12-arc streak target

## 6 · Reverse-stops (V89)

(carries V88's 27 reverse-stops + adds 3 new)

1-22. (carried from V88 charter · ETag concurrency · sandbox no-mutating · V7.A in Engineer-mode · etc.)
23. V8.A edits MUST go through explicit V8.C diff preview before commit (V88 carry)
24. V8.A validation errors MUST surface pre-commit (V88 carry)
25. V8.D configReady decoupled via shell-level shared state (V88 carry)
26. V8 visual baselines steady-state (V88 carry · V89's new injection-driven baselines are DETERMINISTIC steady-state-of-injected-state)
27. V8.A behavioral disable in read-only modes (V88 carry)
28. **NEW**: State-injection URL param ONLY active in dev/test builds · production discards (contract test enforced)
29. **NEW**: State-injection MUST NOT enable AI auto-write · NOT fire any mutating fetch · injected `error` state surfaces the banner WITHOUT having issued a POST
30. **NEW**: Baseline #77 disposition MUST be evidence-backed (regenerate + before/after sample · OR widen tolerance with characterized noise floor · OR mask justified subregion)

## 7 · 4Q gate (every V89 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V89.1 is a baseline disposition (no LLM) · V89.2 is shell-level URL-param routing (no LLM) · all paths LLM-offline runnable
2. **Artifacts emitted?** ✓ V89.1 produces a regenerated PNG (or tolerance-config diff) · V89.2 produces 3 new baseline PNGs · V8 commits continue to flow through existing case-dicts manifest path
3. **TrustGate intact?** ✓ State-injection does NOT bypass any audit affordance · injected `saved` state is just visual · no new manifest entries from injection mode
4. **AI advisory only?** ✓ State-injection cannot enable AI auto-write (gated by env check · injected `error` state shows banner without prior POST) · V130 invariant preserved at all 4 layers (lexical denylist + structural mount-time fetch-zero-call + architectural pure-presentational + live-browser network-mutation guard)

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | Baseline #77 fix MUST land before scoring · V8 state-injection harness + 3 new baselines also pre-score | 100/100 (target · matches V83/V85/V86/V87 pattern) |
| 1 | Substrate re-confirm | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100/100 (target · ideally restoring the 3-consec over-meet streak that V88 broke) |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 9 · Counter telemetry (estimated)

- V89-charter: B301
- V89.1: B302 (baseline fix)
- V89.2: B303 (state-injection harness + 3 baselines)
- V89.3: B304 (close + retro)
- All `autonomous_governance: true`
- Counter contribution: **+4 · arc within v2.3 cadence floor 30**

## 10 · The bigger picture (12-arc commitment target · 4th substantiation arc)

| Arc | Type | Pillars added | Subscores added | Thresholds changed | Scorer scripts created |
|---|---|---|---|---|---|
| V78 (anchor) | threshold tighten | 0 | +3 | +4 | 4 new |
| V79-V88 (10 arcs) | substantiate/LAND mix | 0 | 0 | 0 | 0 |
| **V89** | **V8 substantiation (4th substantiation arc)** | **0** | **0** | **0** | **0** |

V78+V79+...+V88+V89 = **12-arc** streak target. Framework now absorbing:
- **5 strategic-pivot blueprints** (V4 / V5 / V6 / V7 / V8)
- **4 substantiation arcs** (V81 / V84 / V87 · **V89**)
- **V82 completion** + **V79 feature parity** + **V78 threshold anchor**
- 1 mandate-wording-shift (V86 introduced "CFD能力")
- 2 continuation directives (V82 V87)
- **3 same-cohort verbatim re-issues** (V86+V88+V89 all "CFD能力")
- All on the SAME 16-pillar scoring axis · zero pillar/subscore/threshold/script change

— DEC-V89-charter · 2026-05-17 · LANDED
