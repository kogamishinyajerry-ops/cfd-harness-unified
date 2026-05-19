# V9 Blueprint · Post-Run Pattern-Matching Advisor · ACTIVE 2026-05-18

> **Predecessor**: V8 blueprint (`.planning/blueprints/v8/INDEX.md`) · landed V88 · substantiated V89 (state-injection harness + flake fixes)
> **Charter**: `.planning/decisions/2026-05-18_v90_charter_dec.md` (B305)
> **Streak**: 13th consecutive arc target with NO scoring framework changes (V78+...+V89 = 12 arcs)
> **Mandate**: 26th invocation · 4th verbatim re-issue of "CFD能力" wording (V86 1st · V87 continuation · V88 2nd · V89 substantiate · V90 4th) · interpretation = next-LAND in cohort (V83/V85 mirror)

## 0 · What V9 is + isn't

**V9 IS**:
- A **post-run pattern-matching advisor surface** that mounts inside the existing v3 RightPanel Advisor tab
- A **deterministic, LLM-offline-by-construction** layer that complements (NOT replaces) the existing LLM-dependent `/ai-review` and `/ai-diagnose` endpoints
- A **honest framing** of curated diagnostic commentary keyed to real run artifacts via human-authored rules
- A **client-side computation** — pattern matcher reads `runDetail` (audit-package or run-history GET response) and runs deterministic predicates against the curated ruleset, then renders matched commentary
- A **V130 invariant honored BY CONSTRUCTION** — there is no LLM call to gate · the "advisor" is rule-matching against human-curated text · the existing AI endpoints continue to work alongside but V9 does not depend on them

**V9 IS NOT**:
- A new LLM endpoint · NO new `/ai-*` route · NO change to existing LLM call sites
- An AI auto-write or AI auto-rerun affordance · V130 invariant intact at 5 layers + the inherent "no LLM call" of V9
- A replacement for the existing AdvisorContent /ai-review or /ai-diagnose paths · those continue alongside · V9 mounts as an additive section
- A backend persistence change · V9 matched-commentary is computed client-side · the audit-package sidecar schema (charter §6) is FORWARD-PLAN documentation · V91+ candidate to wire backend
- A pillar / subscore / threshold / scorer-script (V90 charter §6 reverse-stops · 13-arc no-scoring-change target)
- A V132 increment · existing GETs (`/run-history/{id}` · `/audit-packages/{bundle}/manifest`) reused · V132 = 9 preserved

## 1 · The narrative (V9 closes the after-run advisor axis)

V4 = static knowledge. V5 = interactive curated demo. V6 = real-data bridge (READ). V7 = USER triggers live solver. V8 = USER edits config pre-run. **V9 = AFTER a run completes, surface curated diagnostic commentary keyed to the real artifact's patterns.**

| Mode | Surface | What user sees | Source of truth |
|---|---|---|---|
| Default (curated) | Advisor tab | Curated commentary cards (V4 base) | sandbox_step_states.ts |
| Cinematic | + `?demo=1&cinema=1` | 12s auto-tour | V4 + V5.C |
| Sandbox | + `?demo=2` | Click-through curated state | V5.A |
| Bridge | + `?bridge=1` | READ-only real artifact view | V6.A |
| Live (V7) | engineer-rail Run button | REAL solver streams · TopBar LIVE pill | V7.A → V7.D |
| Config-edit (V8) | BottomPanel Config tab | USER edits controlDict · diff preview · commit | V8.A → V8.D |
| **Post-run advisor (NEW · V9)** | **Advisor tab (extension within AdvisorContent)** | **Curated diagnostic commentary cards matched against the completed run_id's artifact (residuals · forces · convergence stats) · LLM-offline by construction · provenance-cited** | **V9.A reads runDetail → V9.B pattern matcher → V9.C ruleset → matched commentary IDs → V9.A renders cards** |

## 2 · The 4 V9 contracts

### V9.A · PostRunAdvisorV9 (component)

`src/pages/workbench/v3/components/right-panel/PostRunAdvisorV9.tsx`:

```tsx
interface PostRunAdvisorV9Props {
  /** When null/undefined, render the empty-state ("no completed run yet"). */
  caseId: string | null;
  runId: string | null;
  /** Inject the matched commentary slice from caller (allows test override). */
  matches: MatchedCommentary[];
  /** Source attribution surfaced in each card. */
  rulesetVersion: string;
}

interface MatchedCommentary {
  rule_id: string;
  matched_at: string;  // e.g., "iter_132" or "convergence_stats"
  commentary_excerpt: string;  // human-curated paragraph (full text in V9.C)
  provenance: string;  // V-series link or CFD textbook citation
  severity: "info" | "warn" | "advise";  // visual treatment only · NEVER blocks anything
}
```

- Surfaces inside `AdvisorContent` as an additive section · NOT a new tab
- Mounts ONLY when `runId != null` (after V7.D handoff supplies a completed run)
- Renders matched cards in a vertical list · each card shows: `rule_id` label · `commentary_excerpt` paragraph · `provenance` link · `severity` chip
- Empty state when `matches.length === 0`: shows "no matched patterns yet · run a case to see structured diagnostic commentary"
- Honest framing: section header says "**Curated diagnostic patterns**" — NOT "AI suggestions"
- `data-testid="post-run-advisor-v9"` + `data-match-count="N"` + `data-ruleset-version="X.Y"` for inspection
- Contract tests assert:
  - V130 lexical denylist: NO "AI generates" / "AI suggests" / "AI diagnoses" verbiage in rendered text
  - V130 structural: NO useEffect that fires any fetch · component is pure presentational
  - NO LLM endpoint imported · `grep "/ai-review|/ai-diagnose|streamAICoach" PostRunAdvisorV9.tsx` returns zero (literal-source test)
  - Empty-state renders gracefully when no matches
  - Each card carries non-empty `provenance` (V9 reverse-stop #32)

### V9.B · Pattern Matcher (pure function)

`src/data/advisor_pattern_matcher.ts`:

```ts
export interface RunArtifactSlice {
  run_id: string;
  case_id: string;
  success: boolean;
  exit_code: number;
  residuals?: Record<string, number[]>;   // per-quantity history (e.g., {p: [1e-1, 5e-2, 3e-2, ...]})
  forces?: { iteration: number; Cd: number; Cl: number; Cm: number }[];
  convergence_stats?: {
    final_iter: number;
    max_iters_reached: boolean;
    converged: boolean;
    elapsed_seconds: number;
  };
  gold_delta?: { max_abs_pct: number };  // V81-vintage gold-vs-actual comparison
}

export interface AdvisorRule {
  id: string;
  predicate: (slice: RunArtifactSlice) => MatchSite | null;
  commentary: string;       // human-curated paragraph
  provenance: string;       // V-series link or CFD textbook citation
  severity: "info" | "warn" | "advise";
}

export interface MatchSite {
  matched_at: string;       // e.g., "iter_132" / "convergence_stats" / "gold_delta"
}

export interface MatchedCommentary {
  rule_id: string;
  matched_at: string;
  commentary_excerpt: string;
  provenance: string;
  severity: "info" | "warn" | "advise";
}

export function matchAdvisorPatterns(
  slice: RunArtifactSlice,
  rules: readonly AdvisorRule[],
): MatchedCommentary[];
```

- Pure function · no I/O · no fetch · no LLM · runs in <5ms for typical artifact sizes
- Iterates rules, calls each `predicate(slice)`, collects non-null matches
- Returns sorted by severity (advise > warn > info) for stable rendering
- Contract tests cover:
  - Each rule's predicate matches its intended pattern (positive case)
  - Each rule's predicate returns null for the negative case
  - Empty artifact (`{}`) → empty matches
  - Malformed artifact (residuals undefined) → no crash · returns empty matches
  - Same artifact + same rules → same output always (determinism · ≥3 runs assert identical)
  - All curated rules carry non-empty commentary + provenance (V90 reverse-stop #32)

### V9.C · Curated Ruleset (pure data)

`src/data/v9_advisor_rules.ts`:

```ts
export const V9_ADVISOR_RULES: readonly AdvisorRule[] = [
  {
    id: "RESIDUAL_OSCILLATION_V9_R1",
    predicate: (slice) => { /* detect p residual oscillation > 30% iter-to-iter */ },
    commentary: "Residual oscillation in pressure observed. Consider reducing the relaxation factor (fvSolution → relaxationFactors → p) ...",
    provenance: ".planning/intel/v_series/V32_residual_oscillation.md",
    severity: "warn",
  },
  {
    id: "MAX_ITERS_REACHED_V9_R2",
    predicate: (slice) => slice.convergence_stats?.max_iters_reached ? { matched_at: "convergence_stats" } : null,
    commentary: "Solver hit maxIters without converging. The case is not finished. Common causes ...",
    provenance: ".planning/intel/v_series/V18_max_iters.md",
    severity: "advise",
  },
  // 4-8 more rules covering: forces non-converged · CFL hint · BC consistency
  // · gold-delta exceeds 5% · solution did not write · etc.
];

export const V9_RULESET_VERSION = "v9.0.0";
```

- Pure data file · no logic · no I/O
- Every rule has: id · predicate · commentary · provenance · severity
- Each `provenance` MUST point to a V-series intel file OR a recognised CFD textbook (Versteeg & Malalasekera · Ferziger & Perić · etc · cited by full reference)
- 6-10 initial rules · V90+ can extend
- `V9_RULESET_VERSION` semver-bumps when ruleset content changes (audit-trail for matched-commentary history)

### V9.D · Audit-Package Sidecar (forward-plan documentation)

V90 client-side computation only. The audit-package manifest schema is documented for V91+ backend persistence:

```jsonc
{
  // existing fields ...
  "advisor_commentary_matches": [
    {
      "rule_id": "MAX_ITERS_REACHED_V9_R2",
      "matched_at": "convergence_stats",
      "commentary_excerpt": "Solver hit maxIters without converging ...",
      "provenance": ".planning/intel/v_series/V18_max_iters.md",
      "severity": "advise",
      "ruleset_version": "v9.0.0"
    }
  ]
}
```

- Additive field · backward-compat (old audit packages render with empty matches via client-side default)
- V91+ backend can persist by reading the same `V9_ADVISOR_RULES` (via shared TS-to-Python contract or HTTP GET of ruleset) and writing matches at run-complete time
- Audit-trail: every commit of `advisor_commentary_matches` records `ruleset_version` so historical analyses know which rules were active

## 3 · Reverse-stops (V9 contracts MUST honor)

1. **NO LLM call**: V9.A + V9.B + V9.C MUST NOT import any LLM endpoint · `grep "/ai-review|/ai-diagnose|streamAICoach|ai_advisor"` in V9 files must return zero matches (contract test enforces literal-source absence)
2. **Honest framing**: V9.A section header is "Curated diagnostic patterns" · NEVER "AI suggestions" · denylist test enforces (V90 reverse-stop #33)
3. **Provenance required**: Every rule in V9.C carries non-empty `provenance` (V90 reverse-stop #32 · V80 reverse-stop carry on human-curated commentary)
4. **Deterministic**: V9.B matcher is pure · same input → same output always · contract test runs the matcher 3× on the same artifact + asserts identical output
5. **Graceful empty state**: V9.A renders gracefully when `matches.length === 0` (NOT crash · NOT error) · contract test enforces
6. **No structural fetch**: V9.A has NO useEffect that fires any fetch · its data comes from props · NOT a component that owns network state · contract test asserts mount-time fetch-zero-call
7. **Engineer-mode only**: V9.A surfaces in AdvisorContent which itself respects `failmodeActive` + read-only modes per existing V83/V85/V87 carries
8. **V132 = 9**: NO new MUTATING_ROUTE · no new endpoint · existing GETs only
9. **Empty graceful**: When no `runId` is available (no completed run yet), the V9 section renders the empty-state · does NOT show error
10. **LLM-offline integration**: V9 continues to work even when `/ai-review` is offline · its rendering is unaffected by LLM availability
11. **V9.C extensible**: New rules can be added in V91+ without changing V9.B matcher signature · only data changes · contract test enforces matcher signature stability

## 4 · 4Q gate (every V9 sub-DEC must answer)

1. **LLM offline runnable?** ✓ V9 IS the LLM-offline answer · all 4 contracts are pure-data/pure-function/pure-presentational
2. **Artifacts emitted?** ✓ V9 matched-commentary IDs are deterministic from artifact + rules · reproducible · audit-package sidecar schema documented for V91+ backend persistence · `ruleset_version` audit-trail
3. **TrustGate intact?** ✓ Every commentary card carries `rule_id` + `provenance` (V-series link or CFD textbook citation) · user can trace every claim back to a human-authored source · NO "AI says X" claims · only "rule X matched against this artifact"
4. **AI advisory only?** ✓ V9 has NO AI at runtime · the "advisory" is human-curated rule matching · V130 invariant honored BY CONSTRUCTION (no LLM call to gate)

## 5 · Honest disclosures (what V9 does NOT do)

- ❌ **Live LLM diagnostic call** — that's `/ai-review` + `/ai-diagnose` (existing AdvisorContent path) · V9 is the COMPLEMENTARY deterministic layer
- ❌ **AI-suggested action buttons** — V9 cards are READ-ONLY commentary · user reads + decides + acts manually (V130 invariant)
- ❌ **Backend persistence of matched commentary** — V91+ candidate · V90 is client-side computation only · audit-package schema is forward-plan documentation
- ❌ **Cross-run trend analysis** — V9 matches one run at a time · multi-run trend is V91+ candidate
- ❌ **Rule editor in UI** — V9.C ruleset is code-as-data · NOT editable from the UI · matches "Claude Code session is real advisor" memory: live ruleset edits go through PR review like any code change
- ❌ **Real-time match-during-run** — V9 matches when run COMPLETES (V7.D handoff) · not during streaming · streaming-time pattern detection is V91+ candidate

## 6 · Substrate expansion (V4 + V5 + V6 + V7 + V8 + V9 coverage map)

| Layer | V4 | V5 | V6 | V7 | V8 | V9 |
|---|---|---|---|---|---|---|
| Static commentary | ✓ | (carry) | (carry) | (carry) | (carry) | (carry) |
| Cinematic auto-tour | ✓ | (carry) | (carry) | (carry) | (carry) | (carry) |
| Provenance card | ✓ | + V5.D | replaced by V6.D | extended by V7.D | (carry) | (carry · V9 matched-commentary also carries provenance) |
| Failure-mode showcase | — | ✓ | (carry) | (carry) | (carry) | (carry) |
| Sandbox click-through | — | ✓ | (carry) | (carry) | (carry) | (carry) |
| Real-artifact bridge (READ) | — | — | ✓ | (carry) | (carry) | (carry · V9 reads same artifacts) |
| Live-vs-curated diff | — | — | ✓ | (carry) | (carry) | (carry) |
| USER-triggered live solver run | — | — | — | ✓ | (carry) | (carry · V9 consumes V7.D handoff) |
| Cancellable run state machine | — | — | — | ✓ | (carry) | (carry) |
| Audit-package auto-build on done | — | — | — | ✓ | (carry) | (carry · V9 reads audit-package artifact) |
| USER-edit solver config form | — | — | — | — | ✓ | (carry) |
| Deterministic config validation | — | — | — | — | ✓ | (carry · V9 borrows pure-function pattern) |
| Diff preview before commit | — | — | — | — | ✓ | (carry) |
| Run-readiness signal (configReady) | — | — | — | — | ✓ | (carry) |
| **Curated diagnostic patterns** | — | — | — | — | — | ✓ NEW V9.A |
| **Pure-function pattern matcher** | — | — | — | — | — | ✓ NEW V9.B |
| **Human-curated CFD ruleset (6-10 rules)** | — | — | — | — | — | ✓ NEW V9.C |
| **Audit-package sidecar schema (V91+ forward-plan)** | — | — | — | — | — | ✓ NEW V9.D doc |

After V9 lands: the workbench covers the FULL CFD lifecycle:
1. **Static-knowledge layer** (V4)
2. **Interactive-demonstration layer** (V5)
3. **Real-data bridge (READ)** (V6)
4. **Live execution layer** (V7) — USER triggers a real run
5. **Pre-run configuration layer** (V8) — USER edits config
6. **Post-run pattern-matched advisor layer** (V9) — Curated diagnostic commentary keyed to real artifacts

All six layers under the same 4Q gate, all V130/V132-compliant, all on the same 16-pillar V78 scoring framework. **V9 is the FIRST layer to introduce an "advisor" SURFACE while honoring V130 BY CONSTRUCTION (no LLM call) rather than by RUNTIME GATING.**

## 7 · Test substrate target (V90.5 close gate)

- Contract (vitest) tests: at least 25 new (V9.B matcher 15 covering each rule + edge cases · V9.A component 10 covering empty state + render + V130 lexical denylist + structural mount-time-fetch-zero)
- e2e Playwright specs: at least 1 new (V9.A renders within AdvisorContent · zero mutating fetch fired · LLM endpoints continue to work alongside)
- Visual baselines: 0 new (V9 mounts inside existing AdvisorContent · existing baseline #28 already covers the Advisor tab · V91+ may add dedicated baselines for matched-state)
- Network-mutation guard: V9 emits ZERO POSTs · zero PUTs · zero DELETEs · zero PATCH (V130 contract · V9 by construction)

— V9 Blueprint · 2026-05-18 · LANDED at V90.1
