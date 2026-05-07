---
decision_id: DEC-V61-N6-CLOSE
title: N6 phase-close summary — AI Advisor Stack delivered; Blueprint v3 N1-N6 arc closed
status: Closed
parent_dec: V61-156
phase: N6
notion_sync_status: pending
---

# N6 Phase Close — AI Advisor Stack (RAG-Backed)

## Status

**Closed 2026-05-07** — all 6 sub-DECs landed; Blueprint v3 N1-N6
critical-path complete. Subsequent work (M3+ in roadmap_v2:
compressibility, multiphase, multi-engine) crosses into BlueprintV4
territory.

## Sub-DECs delivered

| DEC | Sub-phase | Commit | Tests | Codex chain |
|---|---|---|---|---|
| DEC-V61-156 | N6.0 charter | `c6bd5b7` | n/a | n/a |
| DEC-V61-157 | N6.1 RAG corpus loader | `a702c83` | 25 | per Opus confidence (skipped) |
| DEC-V61-158 | N6.2 AI 审查 route | `f692462` → `9c36dde` → `931c326` → `ce427ed` | 39 | R0 (loopback + action-text) → R1 (non-string + Submit gap) → R2 APPROVE |
| DEC-V61-159 | N6.3 AI 诊断 route | `7f5223d` → `c7f043f` → `958ba87` → `d573fba` | 36 | R0 (mem blow-up + non-monotonic) → R1 (TOCTOU + boundary trim) → R2 close-patch (no P1) |
| DEC-V61-160 | N6.4 frontend AIAdvisorPanel | `6ca7748` | 12 | per Opus confidence (skipped — UI integration) |
| DEC-V61-161 | N6.5 offline fallback broaden | `266c312` | 14 | per Opus confidence (skipped — service, not contract) |

**Counter delta**: charter +1, sub-DECs +5 = **+6** added to
`autonomous_governance_counter_v61`.

## Surface delivered

### Backend (read-only, V132 advisory-only contract enforced)

- `ui/backend/schemas/ai_advisor.py` — 7 wire schemas:
  `CitedChunk`, `CorpusStats`, `ReviewFinding`, `ReviewResponse`,
  `DiagnosisHypothesis`, `DiagnoseResponse`, plus 5 literal types
- `ui/backend/services/ai_advisor/` (NEW package):
  - `corpus_loader.py` — local in-memory RAG (keyword +
    section-anchor lookup, anchor weighted 2x, stable
    chunk_id `path:offset:sha16`, corpus fingerprint)
  - `review.py` — `review_case` orchestrator: case state →
    LLM prompt with corpus context → JSON parser with chunk-id
    grounding + action-text strip
  - `diagnose.py` — `diagnose_case` orchestrator: bounded
    seek-tail log read (256 KiB cap, current-EOF tracking,
    boundary-aware trim) + residual-trajectory classifier
    (stalled / diverging requires monotonic) + LLM prompt
  - `safety.py` — shared `has_action_text` sanitizer (covers
    HTTP method+path, /api/ refs, button labels in EN+ZH,
    curl/wget mutating commands, dispatch-tool phrasing)
  - `fallback.py` — N6.5 broaden orchestrator; appends
    `mesh_quality/advisor` outputs to base findings
- `ui/backend/routes/ai_advisor.py` — 2 GET endpoints,
  loopback-guarded, FailureMode whitelist on `?problem=`
- `ui/backend/main.py` — router registered at `/api`
- `ui/backend/tests/test_ai_advisor_contract.py` —
  `_AI_DISPATCH_MODULES` extended with 7 N6 modules
- 5 phase-test files (N6.1 through N6.5): **126 backend tests**

### Frontend (read-only, copy-buttons-only)

- `ui/frontend/src/types/ai_advisor.ts` — wire types mirroring
  backend schemas
- `ui/frontend/src/api/client.ts` — `api.getAIReview` +
  `api.getAIDiagnose` helpers (GET only)
- `ui/frontend/src/pages/workbench/step_panel_shell/AIAdvisorPanel.tsx` —
  panel with two buttons, advisory-only badge, citation chips
  (click-to-expand), copy buttons, degradation banner
- `ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx` —
  panel wired into right rail after `CompletenessCard`
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/AIAdvisorPanel.test.tsx` —
  **12 frontend tests**

### Corpus content

- `docs/openfoam_corpus/` — 5 hand-curated topic markdown files +
  README:
  - `mesh_quality_checkmesh.md` — checkMesh metric thresholds
  - `solver_selection.md` — simpleFoam / icoFoam / pimpleFoam guide
  - `boundary_conditions_basics.md` — common BC types
  - `under_relaxation_factors.md` — URF guidance for SIMPLE / PISO
  - `residual_diagnostics.md` — residual interpretation patterns

## Test totals

| Suite | Pass count |
|---|---|
| N6.1 corpus loader | 25/25 |
| N6.2 AI 审查 (3-round Codex chain regression set) | 39/39 |
| N6.3 AI 诊断 (3-round Codex chain regression set) | 36/36 |
| N6.4 AIAdvisorPanel (frontend, vitest) | 12/12 |
| N6.5 fallback broadening | 14/14 |
| V132 contract (Layer-A/B/C with 7 N6 modules) | 21/21 |
| **N6 backend total** | **135/135** |
| **N6 frontend total** | **12/12** |
| Full backend suite (excl. 4 pre-existing failures) | 1724/1724 |

## Four-question gate (phase-level)

| # | Question | Answer |
|---|---|---|
| Q1 | LLM offline → engineer can complete the workbench? | ✅ Both advisor routes return 200 + non-empty findings/hypotheses with `MockLLMProvider`; rule-based fallback consumes N5.2 IssueList + mesh-quality advisor + residual-trajectory classifier; corpus is local on-disk (no network); 5-step workbench workflow remains 100% functional offline |
| Q2 | Artifacts output? | ✅ ReviewResponse + DiagnoseResponse are pipeable JSON with structured findings, citations, evidence dicts, corpus_sha fingerprint, generated_at timestamps |
| Q3 | TrustGate / completeness / audit explainable? | ✅ Every finding/hypothesis carries `citation.chunk_id` resolving to a real corpus chunk; missing chunk → finding dropped (no fake citations); `corpus_sha` fingerprint exposes corpus state; `llm_available` boolean exposes degradation; UI renders citation chip with click-to-expand |
| Q4 | AI advisory only (no mutating call)? | ✅ Routes are GET (idempotent); 7 N6 modules in `_AI_DISPATCH_MODULES` (Layer-C AST scan); Layer-A sentinel patches across LLM + offline branches assert zero mutation invocations; loopback guard on both routes; server-side action-text strip rejects route descriptors / button labels / curl mutations / dispatch phrasing in LLM output; FailureMode whitelist on `?problem=`; UI renders ZERO apply/submit/execute buttons (12 frontend tests assert this) |

## Codex review economy

| Metric | Value |
|---|---|
| Mandatory pre-merge rounds (charter §"Codex pre-merge mandatory") | 2 sub-DECs (N6.2, N6.3) |
| Total rounds fired | 6 (N6.2: R0+R1+R2; N6.3: R0+R1+R2) |
| Round cap reached (V133 cap = 3) | N6.2 (R2 APPROVE); N6.3 (R2 close-patch on P2/P3, no P1) |
| Findings closed | N6.2: P1 loopback, P2 action-text, P1 non-string crash, P2 [Submit] gap; N6.3: P1 unbounded read, P2 non-monotonic divergence, P2 TOCTOU, P3 line-boundary trim, P2 stale-EOF, P3 test fixture bug |
| Pre-emptive Codex-aware design (N6.3 baseline carrying N6.2 lessons) | Caught: loopback, action-text, type-safety, path containment, whitelist. Missed: file-I/O edge cases (TOCTOU, boundary trim, monotonic check) — these required independent review pressure |

**Lesson for retro queue**: pre-emptive design carries general
contract lessons cleanly but does not predict file-I/O / classifier
correctness edge cases. Future high-risk PRs should still expect
≥1 Codex round even with strong upfront discipline.

## Artifacts in retro queue

Per V133 round-cap rules (round 3 with no P1 → P2/P3 to retro):

- N6.3 R2 P2 (live-EOF stale window) — **resolved in close-patch**
  `d573fba` (not retro queue; user / Opus discretion exercised
  V133's "close-patch" alternative since the fix was 5 LOC and the
  bug had real correctness impact)
- N6.3 R2 P3 (frozen-size invariant in regression test) —
  **resolved in close-patch** `d573fba`

No outstanding retro-queue items from N6.

## Counter / governance bookkeeping

- `autonomous_governance_counter_v61` delta: **+6**
- All 6 sub-DECs marked `autonomous_governance: true` (charter
  inheritance)
- No external gates (no `autonomous_governance: false` DECs)
- Kogami: opt-in per V133; not invoked. User may invoke
  retroactively for strategic-layer review of the closed phase.

## V1 deferrals (not blockers)

These were explicitly scoped out per charter §"Out of scope for N6":

- Multi-turn dialog state (N6.1 corpus is single-shot only)
- Embedding-based RAG retrieval (V1 ships keyword + anchor; upgrade
  trigger = recall regression in retro)
- URF advisor + timing advisor wiring into offline fallback (N6.5
  V1 ships mesh-quality advisor only; URF + timing wait on a
  case-state reader)
- Multi-case batch advisor
- Streaming advisor responses
- Cross-language corpus (V1 = en + project zh DEC trail)

## Blueprint v3 closure

With N6 closed, all 28 DECs across N2-N6 are landed:

- **N2** (mesh control parity): charter + N2.1-N2.4 (5 DECs)
- **N3** (physics + materials): charter + N3.1-N3.5 (6 DECs)
- **N4** (BC + solver unification): charter + N4.1-N4.5 (6 DECs)
- **N5** (post-processing report): charter + N5.1-N5.4 (5 DECs)
- **N6** (AI advisor stack): charter + N6.1-N6.5 (6 DECs)

**Cumulative scope realized**:

- Engineer drives 5-step workflow end-to-end with no LLM dependency ✅
- AI advisor surfaces (review + diagnose) operational with corpus + citations + LLM-offline fallback ✅
- Audit package V2 with HMAC + provenance manifest (N5.3) ✅
- Mesh control parity ~60% Fluent baseline (N2) ✅
- Physics regime + materials + BC + solver dict + URF all engineer-controlled (N3 + N4) ✅
- Beginner report + honest issue list + audit export (N5) ✅

This closes Blueprint v3. Subsequent work crosses into BlueprintV4
territory (compressibility, multiphase, radiation, FSI, multi-engine).

## References

- DEC-V61-130 · Strategic pivot to AI-as-advisor (root)
- DEC-V61-156 · N6 charter
- DEC-V61-157..161 · N6.1-N6.5 sub-DECs
- DEC-V61-132 · MUTATING_ROUTES + KNOWN_MUTATION_FUNCTIONS (V130 contract spine)
- DEC-V61-133 · B+ governance simplification (round cap = 3 applied here)
- `.planning/strategic/blueprint_v3_2026-05-07.md`
- `.planning/strategic/n3_n6_outline_2026-05-07.md` §4
