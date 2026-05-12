# Calibration Retro · V-series → N6 corpus spike

**Date**: 2026-05-11
**Spike**: inject V198 V-series + solver_convergence_playbook into N6 RAG corpus
**Outcome**: PASS — 26 corpus tests + 115 N6 advisor tests green, zero regression
**Process budget**: ~25 min wall (1 cp x 2, 1 README edit, 1 test file 50 LOC, 2 pytest runs)
**Trigger**: user meta-question — "is the project bloated because model + agent architecture upgraded? are old rules now redundant binders?"

## Spike scope (re-stated)

- ≤30 LOC + ≤2 corpus topic files + 1 integration test
- No sub-DEC frontmatter
- No Codex relay call
- No Kogami invocation
- Commit with `confidence: med`

Actual scope: 2 cp commands (no code) + 7-line README edit + 56-line test file + 0 corpus_loader code change. Strictly under budget.

## What governance rule was load-bearing during this spike

| Rule | Where it helped | Verdict |
|---|---|---|
| **Four-question gate** | Forced check that V-series injection is offline-safe (no LLM dependency for retrieval — keyword + anchor is local) before touching files | **Keep** — 4-line invariant, principled product contract |
| **N6.1 `corpus_sha` + `chunk_id:sha16` contract** | Confirmed by 25 unchanged N6.1 tests that adding 2 corpus files doesn't break any consumer; the contract acted as exactly the safety harness it was designed to be | **Keep** — load-bearing technical contract |
| **`MUTATING_ROUTES` registry + `KNOWN_MUTATION_FUNCTIONS`** | The N6.1 test `test_corpus_loader_module_not_in_mutation_registry` automatically verified my spike didn't accidentally promote corpus_loader into actor territory | **Keep** — V130 advisor philosophy enforced mechanically |
| **`docs/openfoam_corpus/` allowlist scope** | Prevented me from being tempted to add `.planning/methodology/` directly as third corpus root (which would have leaked governance meta-files like `kogami_triggers.md` into the advisor corpus) | **Keep** — narrow surface saves work |
| **APU bay V-series existing in shape that already fits `## `-split convention** | Zero adaptation needed; `cp` was the entire content action | **Keep** — past discipline paid current dividend (V198 §S3 paid off here) |

## What governance rule was *not* load-bearing for this spike

| Rule | Why it was overhead in this case | Recommendation |
|---|---|---|
| **Kogami pre-charter review** | 36 sources, 629KB prompt, 9 findings, ~3 min wall + token spend — to review a brief that we then deliberately did *not* turn into a charter. The brief itself was an artifact created to feed Kogami, which Kogami then advised us not to land. Process pure. | **For data-injection spikes: skip Kogami entirely.** Kogami value is in genuine strategic uncertainty (V130-pivot-class), not in pre-blessing data adds. v2.3 "Kogami opt-in" already says this; the spike confirmed it operationally. |
| **Charter DEC ceremony for ≥3-module scope** | Brief named 4 pillars (P1-P4) → ostensibly triggered "≥3 modules → write full charter" rule. But P1 alone (this spike's actual scope) is 1 module + 0 code change. Charter would have been process-for-process. | **Charter rule should fire on actual code module count, not aspirational pillar count.** When pillars don't share code paths, treat as N independent sub-arcs not as 1 charter. |
| **Codex relay for risk-tier triggers** | Considered briefly: does V-series injection touch auth / signing / byte-repro? No — pure docs add + 1 read-only retrieval test. Codex would have rubber-stamped. | **v2.3 already correct here** (1-sync-trigger = auth/operator endpoint only); spike re-confirmed. |
| **Sub-DEC frontmatter (6 fields min)** | Drafting 6-field frontmatter + Why + Decision for a `cp x 2` would have taken longer than the work itself. | **Spike-class work (≤30 LOC, no schema change, zero regression risk) should skip sub-DEC entirely.** Commit message + this retro file is sufficient durable record. v2.3 "DEC scope-driven" already permits this; spike confirms it operationally. |
| **`v2.3 ROADMAP main-line / N1-N6 phase tagging`** | I considered which N-phase this spike "belonged to" before realizing the question is meaningless for a corpus-data injection that doesn't change any contract. | **Phase tagging is for code milestones, not data extensions.** Future spike-class work skip phase assignment. |

## What rules became actively *harmful* (false alarm or overhead-no-value)

| Rule | Harm observed | Recommendation |
|---|---|---|
| **"Cross ≥3 modules → must charter"** mis-fires on pillar planning | User-facing strategic brief named 4 pillars → rule wanted full charter DEC → Kogami invoked → 9 findings → most findings were code-architecture (P2-2: FAISS not Kogami's layer) → process generated noise not signal | **Replace "module count" with "code-path count".** A 4-pillar plan that touches 0 shared code paths until each pillar starts is not a ≥3-module change yet. Rule should fire at first sub-DEC, not at strategic-brief authoring. |
| **Implicit "all DECs go to Notion"** | Brief 工件 + Kogami review will land 3 Notion entries (DEC + brief + Kogami review) for a spike that the user said "incremental + don't break it". Notion was designed to be a decision archive, not a process log. | **Skip Notion sync for spike retros that decide *not* to land a DEC.** Notion archives decisions, not non-decisions. |
| **Auto-generated `_v61_NNN` DEC numbering pressure** | I caught myself proposing `DEC-V61-199` as charter ID before user pivoted. Numbering convention nudges toward landing DECs even when retro/no-DEC is the right answer. | **DEC numbering should be reserved at landing, not at proposal.** Today's convention pressures toward escalation. Mild rephrasing in v2.3 ("draft" suffix until Accepted) would help. |

## What I would have done differently without the rules I now consider overhead

Counterfactual: same spike (V-series → corpus + 1 test), no Kogami, no charter brief, no DEC-V61-199 reservation.

- **Time**: ~25 min (actual was ~25 min spike + ~30 min Kogami round-trip + ~20 min charter-vs-spike pivot ≈ 75 min)
- **Output**: same test result, same commit
- **Loss**: no Kogami findings (those were genuinely useful for the *eventual* charter, but the charter is no longer next on the path — value deferred to maybe-never)
- **Process artifacts avoided**: 1 brief file (5KB) + 1 Kogami review dir (briefing 629KB + review.md/json + canary report)
- **Quality gain**: zero (test result identical)

**Lesson**: for spike-class work (≤30 LOC, no schema change, no contract break), the v2.3 process overhead is **~3x the actual work**. This is exactly the bloat the user diagnosed in the meta-question.

## What "Opus 4.7 + GPT-5.5 capability boundary" was probed

- **Code reasoning**: Opus 4.7 1M context handled 36-source Kogami briefing manifest + 197-DEC project state + 5 memory topic files in single session without compression. **Confirmed**: 1M ctx eliminates need for sub-DEC scaffolding to "preserve context" — context preservation is free now.
- **Schema understanding**: read `corpus_loader.py` (5 sites) + 1 test file + 1 schema spec → correctly inferred zero-code-change path. **Confirmed**: complex multi-file inference is Opus's strong suit; old rules requiring "study + plan + implement" 3-stage GSD are over-cautious.
- **Failure mode unprobed**: I did not stress the model on a *genuinely* ambiguous task (this one had clear ground truth: query for known-good failure, assert match). True boundary probing would require a task where the answer is uncertain.

## Recommendations (for retro queue, not as DECs)

1. **Carve "spike" as a first-class scope class in v2.4** distinct from sub-DEC: ≤30 LOC + no schema change + zero contract break + 1 test + commit + 1-file retro = full process. Skip Kogami, skip Codex, skip Notion sync, skip DEC frontmatter.
2. **Replace "≥3 modules → charter" with "≥3 shared code paths → charter"**. Charter trigger fires on first sub-DEC, not on strategic-brief authoring.
3. **Kogami invocation policy**: explicitly OK to invoke for strategic uncertainty, explicitly *not* OK for "we'll probably do something with 3 dependencies"-class plans. v2.3 says opt-in; v2.4 should say *opt-in with falsifiable trigger*.
4. **Notion: archive accepted DECs only.** Retros that decide "no DEC" stay local. Reduce Notion noise.
5. **DEC ID reservation**: only at Accepted, not at Proposed. `draft/` directory for in-flight proposals.

These are observations from one spike, not generalizations. Pattern-test against next 2-3 spikes before landing as v2.4 governance change.

## What this spike did NOT validate

- Whether V-series corpus injection improves *actual AI advisor output quality* on a real engineer query (test only validates retrieval surfaces V3/S1; whether N6.2 review.py uses those chunks well to compose a useful answer is untested)
- Whether `chunk_id:sha16` collision risk increases meaningfully when corpus jumps from 5 files to 7 files (test trusted existing contract; didn't measure)
- Whether the Foam-Agent FAISS upgrade hypothesis (Kogami P2-2 deferred to data) has empirical support — would need to measure retrieval recall on a held-out engineer-query set, which this spike did not build
- Whether the user's meta-question generalizes beyond corpus-data injection class of work — single data point

## Next decision

Three options for the user, not for me to pick:

1. **Land this spike + retro as commits, stop**. The four-pillar mission brief is shelved; future RAG-quality work happens as additional spikes.
2. **Land spike, then write the calibration-driven sub-DEC** (now reframed as "RAG corpus expansion to V-series" rather than P1-of-4-pillar) — small enough for sub-DEC frontmatter to be honest, not over-engineered.
3. **Land spike, then probe a real engineer query through N6.2 `/api/ai/review`** to validate the retrieval-→-review chain actually delivers value. If yes, then write sub-DEC. If no, the V-series injection helps retrieval recall but doesn't help advisor — different problem.

confidence: high on the retro content; med on the recommendations (1 spike's worth of data point).

## Artifacts of this spike

- `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (new · synced from `.planning/methodology/`)
- `docs/openfoam_corpus/solver_convergence_playbook.md` (new · synced from `.planning/methodology/`)
- `docs/openfoam_corpus/README.md` (+7 lines)
- `ui/backend/tests/test_n6_corpus_v_series_spike.py` (new · 56 LOC · 1 test PASS)
- `.planning/strategic/oss_substitution_4pillar_brief_2026-05-11.md` (Kogami brief, retained as historical artifact)
- `.planning/reviews/kogami/oss_substitution_4pillar_charter_scope_2026-05-11/` (Kogami APPROVE_WITH_COMMENTS verdict, retained)
- this retro file
