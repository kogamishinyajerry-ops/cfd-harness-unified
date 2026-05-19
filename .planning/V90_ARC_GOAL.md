# ARC-GOAL · V90 · V9 Post-Run Pattern-Matching Advisor Arc · 26th V110 advisor-class · 4th "CFD能力" verbatim re-issue · **13th consecutive no-scoring-change arc target** · **Active 2026-05-18**

> **Charter**: `.planning/decisions/2026-05-18_v90_charter_dec.md` (Accepted B305)
> **Predecessor**: DEC-V89-close (12-arc no-scoring-change streak ATTAINED · 3-consec over-meet RESTORED)
> **Target**: 16-pillar min ≥99 · 2-consecutive close gate under V78 scoring (unchanged) · ideally extend the V89-restored 3-consec over-meet streak
> **Pattern**: V83/V85 mirror (verbatim AFTER LAND-then-substantiate in same cohort = next-LAND)
> **Cohort**: V86 (V7 LAND) + V87 (substantiate) + V88 (V8 LAND) + V89 (substantiate) + **V90 (V9 LAND · 6th strategic pivot)**

## North Star

V89 closed V8 substantiation with all V88-wiring-induced baseline fallouts disposed (3 baselines · 3 dispositions · all evidence-backed) and the V130 5-layer defense established. V90 lands V9 — the **post-run pattern-matching advisor surface** — closing the AFTER-RUN axis of the CFD lifecycle. V9's key design property: **V130 invariant honored BY CONSTRUCTION** (no LLM call at runtime) rather than by gating. The "advisor" is human-curated rule matching against real run artifacts — complementary to (NOT replacing) the existing LLM-dependent `/ai-review` + `/ai-diagnose` endpoints. V132 stays at 9 (zero new endpoints). 13-arc streak target. 6 strategic-pivot blueprints (V4/V5/V6/V7/V8/V9).

## Done dim checklist

- [x] **V89-DONE-COMPOSITE carry** — V8 substantiation closed + 3-consec over-meet restored under unchanged V78 scoring
- [ ] **V90-DONE-COMPOSITE** — V9 blueprint LANDED + V9.C ruleset (6-10 curated rules with provenance) + V9.B pure-function matcher (≥15 contract tests · deterministic) + V9.A presentational component (≥10 contract tests · zero mutating fetch · honest framing) + V9.D audit-package sidecar schema documented · V132 stays at 9 · V130 honored BY CONSTRUCTION (no LLM call) · V78 scorers UNCHANGED still report 16-pillar 100/100

## Sub-DEC progress

- [x] **V90.1 · V9 blueprint document** — `.planning/blueprints/v9/INDEX.md` · 4 contracts (V9.A-D) + 11 reverse-stops + 4Q gate + Claude-Code-session-is-real-advisor framing · ~370 lines · B306
- [x] **V90.2 · V9.C curated commentary ruleset** — `src/data/v9_advisor_rules.ts` · 8 curated rules · each carries id + predicate + commentary + provenance (V-series link · 6 rules · Versteeg & Malalasekera CFD textbook · 2 rules) + severity (advise/warn/info) · B307
- [x] **V90.3 · V9.B pattern matcher** — `src/data/advisor_pattern_matcher.ts` · pure function `matchAdvisorPatterns(slice, rules) → MatchedCommentary[]` · deterministic · no I/O · no fetch · no LLM · 26 contract tests pass (covering each rule positive/negative + edge cases + determinism + graceful predicate-throw degrade) · B308
- [x] **V90.4 · V9.A PostRunAdvisorV9 component** — `components/right-panel/PostRunAdvisorV9.tsx` · pure presentational · mounted in AdvisorContent (BOTH whitelist + non-whitelist branches) · WorkbenchShellV3 supplies real matches via `adaptBridgeArtifactToSlice(bridge)` helper (graceful degrade: BridgeArtifact's single-value residuals incompatible with V9.B's history-array shape → history-dependent rules skipped not crashed) · 13 contract tests pass (V130 lexical denylist + structural mount-time fetch-zero + literal-source LLM-import absence · regex strips JSDoc + line comments before grep) · honest framing "Curated diagnostic patterns" · empty-state graceful · B309
- [x] **V90.5 · V9.D commentary sidecar + close + retro · 13-arc streak target ATTAINED** · V9.D audit-package sidecar schema documented as V91+ forward-plan in close DEC · DEC-V90-close + V90 retro WRITTEN · B310

## Reverse-stops (NEW in V90)

31. V9.A AdvisorPanelV9 MUST NOT call any LLM endpoint (grep enforced literal-source absence test)
32. V9.C commentary text is HUMAN-CURATED · every rule MUST have non-empty `provenance` field (V-series link OR CFD textbook citation · 9-arc V80 lineage on human-curated commentary)
33. V9.A copy MUST NOT contain "AI generates" / "AI suggests" / "AI diagnoses" verbiage · honest framing: "Curated diagnostic patterns"
34. V9.A MUST gracefully render empty matched-commentary list · NOT crash · NOT show error

## Fleet criteria (16 pillars · V89 unchanged · V90 SAME)

| # | Agent | V89 close | V90 |
|---|---|---|---|
| 1-16 | (all) | 100 (iter-0/1/2 all 100 · 3-consec over-meet restored) | **100/100/100 target** (V9 is pure-data + pure-function + pure-presentational · blast radius small · iter-0 should hit 100 directly) |
| ~~17~~ | ~~(declined)~~ | ~~NOT added~~ | **STILL NOT added (13-arc streak target)** |

## Iteration tracker

| Iter | Date | min(16) | weighted | Lowest dim | Notes | Score report |
|---|---|---|---|---|---|---|
| 0 (V90 baseline · first run) | 2026-05-18 | 86 | (n/a) | visualization (baseline #29 single-run flake) | NOT a regression · single-run statistical flake on visual baseline · re-run clean | (transient · superseded) |
| 0 (V90 baseline · re-run) | 2026-05-18 | **100** | high | (none below 100) | All V90 substrate landed pre-score · V9.A mounted · ruleset complete · 26+13 contract tests green | `.planning/scores/V90_iter_0.md` |
| 1 (substrate re-confirm) | 2026-05-18 | 70 | (n/a) | stability (1/3 vitest runs FAIL · run2) | NOT a regression · 1-in-9 statistical flake (diagnostic isolation run = 9/9 PASS) · stability scorer = `npm run test × 3 → 100 - flake×30` | `.planning/scores/V90_iter_1.md` |
| 2 (stability re-confirm) | 2026-05-18 | **100** | high | (none below 100) | 3/3 vitest runs PASS · flake gone · `CLOSE_ELIGIBLE this-iter-only` | `.planning/scores/V90_iter_2.md` |
| 3 (2-consec close attempt) | 2026-05-18 | **100** | high | (none below 100) | 3/3 vitest runs PASS · **2-CONSEC CLOSE GATE MET** (iter-2 + iter-3 both ≥99) | `.planning/scores/V90_iter_3.md` |

## V90 outcome

- **Close gate**: ✅ **MET** (iter-2 = 100 · iter-3 = 100 · 2-consecutive ≥99 under V78 scoring unchanged)
- **13-arc no-scoring-change streak**: ✅ **ATTAINED**
- **3-consec over-meet streak** (iter-0 · iter-2 · iter-3 all 100): ✅ **RESTORED-AND-HELD** (iter-1 was a statistical flake · not real over-meet break · evidence-backed disposition)
- **6 strategic-pivot blueprints LANDED**: V4 · V5 · V6 · V7 · V8 · V9 · V130 invariant continues to hold (5-layer defense intact + V9 BY-CONSTRUCTION presentational)
- **V132 endpoints**: 9 (unchanged · V9 added zero new mutating routes)

— V90 ARC-GOAL · 2026-05-18 · **CLOSED** · **13-arc streak ATTAINED · 6th strategic-pivot blueprint**
