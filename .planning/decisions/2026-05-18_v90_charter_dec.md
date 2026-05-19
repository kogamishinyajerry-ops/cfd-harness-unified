---
decision_id: DEC-V90-charter
title: V90 charter · 26th V110 advisor-class arc · 4th "CFD能力" verbatim re-issue (after V89 V8 substantiation) · V9 LAND · cohort next-LAND pattern (V83/V85 mirror) · 6th strategic-pivot blueprint · POST-RUN PATTERN-MATCHING ADVISOR surface (deterministic · LLM-offline by construction · V130 invariant honored by NOT calling LLM at runtime) · ZERO new MUTATING_ROUTES · 13-arc no-scoring-change streak target
status: Accepted
parent_dec: DEC-V89-close
phase: V90
notion_sync_status: pending
predecessor: DEC-V89-close
batch: B305
confidence: high
autonomous_governance: true
verdict: CHARTER_LANDED
v_row_landed: V90-charter (bootstrap)
substrate: V89 closed (V8 substantiation · 12-arc no-scoring-change streak attained · 5-layer V130 defense established) · V7 fully wired (live solver trigger + post-run handoff) · V8 fully wired (USER-edit solver config + 3 state-injection baselines + tolerance-disposed pre-existing baselines) · existing AdvisorContent surface in v3 RightPanel calls /ai-review + /ai-diagnose endpoints (LLM-dependent) · 26th directive is 4th verbatim "CFD能力" — interpretation: V9 LAND (next-LAND in cohort · V83-mirror pattern)
---

# DEC-V90-charter · V90 V9-Post-Run-Advisor Arc · CHARTER

## 1 · Mandate (26th invocation · 4th verbatim re-issue of "CFD能力" wording)

> "批准授权你全权开发，构建下一个阶段的蓝图（致力于顶级的全流程**CFD能力**），瞄准蓝图进行开发，要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有明确的完成度评分机制（要绝对诚实客观，且维度充足，包括CFD仿真全维度能力，包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件，我觉得Claude的UI审美很好），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"

**Mandate-wording tracking (V80+ cohort) · 26-arc table:**

| Mandate # | Arc | Wording | Interpretation |
|---|---|---|---|
| 16th (V80) | V80 | "AI CFD demo展示" (1st of 5) | V4 LAND |
| 17th (V81) | V81 | verbatim | V4 substantiation |
| 18th (V82) | V82 | "完成所有建议" (continuation) | V4 completion |
| 19th (V83) | V83 | verbatim | V5 LAND |
| 20th (V84) | V84 | verbatim | V5 substantiation |
| 21st (V85) | V85 | verbatim | V6 LAND |
| 22nd (V86) | V86 | "CFD能力" (1st of new wording) | V7 LAND |
| 23rd (V87) | V87 | "全权授权继续" (continuation) | V7 substantiation |
| 24th (V88) | V88 | "CFD能力" (2nd verbatim) | V8 LAND |
| 25th (V89) | V89 | "CFD能力" (3rd verbatim) | V8 substantiation |
| **26th (V90)** | **V90** | **"CFD能力" (4th verbatim)** | **V9 LAND (cohort next-LAND · V83/V85 mirror: after a LAND + substantiation, next verbatim = next-LAND)** |

V83/V85 (in "demo展示" cohort) are the direct precedents:
- V83 (3rd verbatim · 1st LAND→substantiation→next-verbatim) = V5 LAND (NEW blueprint)
- V85 (5th verbatim · 2nd LAND→substantiation→next-verbatim) = V6 LAND (NEW blueprint)
- **V90 (4th verbatim · CFD能力 cohort's 1st LAND→substantiation→next-verbatim) = V9 LAND (NEW blueprint · 6th strategic pivot)**

User axis confirmation via AskUserQuestion: selected "V9 AI Diagnose / Post-Run Review surface (highest impact · highest V130 risk)" — the missing piece of "顶级的全流程CFD能力" since V4-V8 covered static knowledge / curated demo / read-only bridge / live execute / pre-run config. V9 closes the AFTER-RUN advisor axis.

## 2 · V130 design discipline (the key constraint)

Per project memory `feedback_claude_code_is_the_advisor.md`: "M6 charter 的 advisor UI 按钮是过度工程化 · Claude Code session 直接读 V-series corpus + 驱动 workflow + 给死法模式判断 = 真实'advisor'". The in-UI "advisor" surface MUST NOT pretend to BE the advisor — it must be a HONEST presentation of pre-curated patterns matched against real artifacts.

**The V9 design contract that honors both the user's axis-pick AND the "AI 顾问不是接管者" memory:**

V9 is a **pattern-matching advisor surface** — NOT a live-LLM advisor.
- Commentary cards are HUMAN-CURATED text (V80 reverse-stop carry: AI advisor commentary MUST be human-curated).
- Pattern matcher is a PURE FUNCTION (artifact, rules) → matched_commentary_ids[]. Deterministic. No LLM call at runtime.
- The matcher runs entirely client-side · no new backend endpoint · LLM-offline by construction.
- The existing /ai-review and /ai-diagnose LLM endpoints CONTINUE TO WORK alongside · V9 adds a complementary deterministic layer.
- Honest framing in the UI: section header says "Curated diagnostic patterns" (NOT "AI suggestions") · each card carries `source: human_curated_rule` provenance.

This is the V130 invariant honored BY CONSTRUCTION — not by gating an LLM call, but by NOT MAKING ONE in the first place.

## 3 · Pre-implementation surface scan (DEC-V61-088 discipline · 5th round)

**Run BEFORE charter §4 sub-DEC enumeration:**

1. **V89 retro Open Q forecasts**: 4 V9 LAND candidates surfaced (fvSchemes / AI advisor / BC editor / multi-run timeline). User-selected via AskUserQuestion: AI advisor surface.

2. **Existing AdvisorContent scan**: `grep -rn "AdvisorContent" ui/frontend/src/pages/workbench/v3/` shows the existing surface at `components/right-panel/AdvisorContent.tsx` already calls `/api/ai/review` + `/api/ai/diagnose` (LLM-dependent). It has llm_available=false fallback already. V9 EXTENDS this with a complementary LLM-offline pattern-matching layer · does NOT replace.

3. **API client scan**: `api.diagnoseRun` + `api.reviewCase` already exist. V9 uses NEITHER (no new LLM call). V9 reads run artifacts via existing `api.getRunDetail` + `api.getRunHistory` (already wired in V87).

4. **V132 invariance check**: V90 adds NO new endpoints · V132 = 9 preserved.

5. **Curated rules location scan**: `grep -rn "advisor_rules\|curated_rule\|pattern_match" ui/frontend/src/data/` returned zero. V9 introduces `ui/frontend/src/data/v9_advisor_rules.ts` as a NEW data module · pure TypeScript · no schema migration needed.

6. **artifacts emission scan**: V9 commentary match IDs need a persistent home. Existing audit-package manifest is the natural sidecar. V90 charter §6 specifies the JSON schema for `advisor_commentary_matches` field (additive · backward-compat · old audit packages without this field render with empty matches).

**Disposition decision**: V9 is an ADDITIVE LAND · extends AdvisorContent · reuses existing GETs · adds 1 pure-function module + 1 data module + 1 sub-component · NO new endpoint · V132 = 9.

## 4 · What V90 is building (concrete sub-DECs · V9 contracts)

| Sub-DEC | V9 contract | Headline |
|---|---|---|
| **V90.1** | (blueprint document) | V9 blueprint LANDED at `.planning/blueprints/v9/INDEX.md` · 4 contracts (V9.A-D) + reverse-stops + 4Q gate + "Claude Code session is real advisor" framing · ~370 lines · disposition (a) extend AdvisorContent documented |
| **V90.2** | V9.C curated commentary ruleset | `ui/frontend/src/data/v9_advisor_rules.ts` · pure data file · 6-10 initial rules covering: residual oscillation · forces non-converged · iter-count-maxed-out · convergence stalled · CFL hint · BC consistency hint · gold-delta exceeds 5% · etc. Each rule has `id` · `pattern` (structural predicate) · `commentary` (human-curated paragraph) · `provenance` (V-series link or CFD textbook citation) |
| **V90.3** | V9.B pattern matcher | `ui/frontend/src/data/advisor_pattern_matcher.ts` · pure function · `matchAdvisorPatterns(artifact, rules) → MatchedCommentary[]` · deterministic · no I/O · no fetch · no LLM · ≥15 contract tests covering each rule + edge cases |
| **V90.4** | V9.A PostRunAdvisorV9 component | `ui/frontend/src/pages/workbench/v3/components/right-panel/PostRunAdvisorV9.tsx` · pure presentational · mounts inside AdvisorContent when a completed run_id is available (V7.D handoff) · renders MatchedCommentary cards · NO LLM call · NO useEffect that fetches · honest framing ("Curated diagnostic patterns") · ≥10 contract tests + 1 e2e spec proving zero mutating fetch |
| **V90.5** | (close + retro · V9.D doc) | V9.D commentary sidecar pattern documented (existing audit-package manifest is the home) · V78 fleet score iter-0/1/2 · 100/100 × 2-consec close gate · DEC-V90-close · V90 retro · 13-arc no-scoring-change streak · 6 strategic-pivot blueprints |

## 5 · Reverse-stops (V90 · carries 30 from V89 + adds 4 new)

(carries V89's 30 reverse-stops + adds 4 new)

1-30. (V89 carry · V130 5-layer defense · V132 = 9 · sandbox no-mutating · steady-state baselines · etc.)
31. **NEW V90 #31**: V9.A AdvisorPanelV9 MUST NOT call any LLM endpoint · `grep "ai-review\|ai-diagnose\|streamAICoach"` in the V9.A component file must return zero (contract test)
32. **NEW V90 #32**: V9.C commentary text is HUMAN-CURATED · every rule MUST have `provenance` field with V-series link OR CFD textbook citation · contract test asserts no rule has empty provenance (V80 reverse-stop carry · 9-arc lineage now)
33. **NEW V90 #33**: V9.A copy MUST NOT contain "AI generates" / "AI suggests" / "AI diagnoses" verbiage · denylist test enforced · honest framing: "Curated diagnostic patterns" / "Pattern-matched commentary" / "Human-authored advisor notes"
34. **NEW V90 #34**: V9.A MUST gracefully render with empty matched-commentary list (zero matches) · NOT crash · NOT show error · shows "no matched patterns yet · run a case to see structured diagnostic commentary"

## 6 · Audit-package sidecar schema (V9.D · additive · backward-compat)

The audit-package manifest grows ONE optional field. Old audit packages without this field render with `matched_commentary: []`.

```jsonc
{
  // ... existing fields ...
  "advisor_commentary_matches": [
    {
      "rule_id": "RESIDUAL_OSCILLATION_V9_R1",
      "matched_at": "iter_132",
      "commentary_excerpt": "residual oscillation observed in p — see V32...",
      "provenance": "V-series/V32_residual_oscillation.md"
    }
  ]
}
```

V9.D doc-comment in code clarifies this is FORWARD-PLAN — backend persistence is V91+ candidate. For V90, the matches are computed CLIENT-SIDE from the artifact + ruleset · only persisted if the audit-package endpoint is updated to accept this field. **Within V90 scope: just the client-side computation + render · backend persistence stays a documented future arc**.

## 7 · 4Q gate (every V90 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V9 IS the LLM-offline answer · V9.B pattern matcher is pure · V9.C rules are static · V9.A renders matched cards without any fetch · the existing /ai-review and /ai-diagnose continue to work alongside but V9 doesn't depend on them
2. **Artifacts emitted?** ✓ V9 matched-commentary IDs are deterministic from artifact + rules · same artifact + same rules → same matches always · reproducible · audit-package manifest schema documented for future backend persistence
3. **TrustGate intact?** ✓ Each commentary card carries `rule_id` + `provenance` (V-series link or CFD textbook citation) · user can trace every claim back to a human-authored source · NO "AI says X" claims · only "rule X matched against this artifact"
4. **AI advisory only?** ✓ V9 has NO AI at runtime · the "advisory" is human-curated rule matching · V130 invariant honored BY CONSTRUCTION (no LLM call to gate) · 5-layer V130 defense unchanged · existing AdvisorContent's LLM endpoints still get their own gating

## 8 · Iteration target

| Iter | Goal | Expected min(16) under V78 scoring |
|---|---|---|
| 0 | All V90 substrate to land pre-score · V9 mounted in AdvisorContent · 6-10 rules in ruleset · pattern matcher tests green | 100/100 (target · matches V83/V85/V86/V87 pattern · V89 lesson: snapshot iter-0 IMMEDIATELY after shell-level edits — but V90 only adds presentational + pure data, no shell hook, so blast radius is small) |
| 1 | Substrate re-confirm | 100/100 |
| 2 | Stability re-confirm · CLOSE_CONFIRMED 2-consec | 100/100 |

**Close gate**: 16-pillar min ≥99 × 2-consecutive iters under V78 scoring (unchanged).

## 9 · Counter telemetry (estimated)

- V90-charter: B305
- V90.1-V90.5: B306-B310
- All `autonomous_governance: true`
- **Counter contribution: +7 · arc within v2.3 cadence floor 30**

## 10 · The bigger picture (13-arc commitment target · 6 strategic pivots)

| Arc | Type | Substrate landed |
|---|---|---|
| V78 (anchor) | threshold tighten | 4 subscores · 4 threshold tightenings · 4 scorer scripts |
| V79-V89 (11 arcs) | substantiate/LAND mix | 5 pivots + 4 substantiations + completion + parity |
| **V90** | **V9 LAND (6th strategic pivot)** | **Pattern-matching advisor surface · human-curated rules · LLM-offline-by-construction · V130 invariant honored by NOT calling LLM** |

V78 → V90 = **13-arc** streak target. Framework now absorbing:
- **6 strategic-pivot blueprints** (V4 / V5 / V6 / V7 / V8 / **V9**)
- **4 substantiation arcs** (V81 / V84 / V87 / V89)
- **V82 completion** + **V79 feature parity** + **V78 threshold anchor**
- 1 mandate-wording-shift (V86 introduced "CFD能力")
- 2 continuation directives (V82 V87)
- **4 same-cohort verbatim re-issues** (V86 V88 V89 V90 all "CFD能力")
- All on the SAME 16-pillar scoring axis · zero pillar/subscore/threshold/script change

Workbench now covers the FULL CFD lifecycle:
1. **Static-knowledge layer** (V4) — curated commentary cards
2. **Interactive-demonstration layer** (V5) — click through curated narratives
3. **Real-data bridge (READ)** (V6) — view real run artifacts
4. **Live execution layer** (V7) — USER triggers a real run, watches it stream
5. **Pre-run configuration layer** (V8) — USER edits solver config, validates, commits
6. **Post-run pattern-matched advisor layer** (V9) — curated diagnostic commentary keyed to real run artifacts · LLM-offline by construction · V130 honored

— DEC-V90-charter · 2026-05-18 · LANDED
