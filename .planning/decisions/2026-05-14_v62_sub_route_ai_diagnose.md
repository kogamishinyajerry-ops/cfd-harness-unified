---
decision_id: DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE
title: M-ROUTE-AI-DIAGNOSE · POST /api/ai-diagnose · V-series similarity matching · advisor_stack cross-reference · audit artifact · 4Q gate inline-verified
status: Accepted
parent_dec: V62-A-charter
phase: V62-A Tier 1 · M-ROUTE-AI-DIAGNOSE (stack-level route #2 of 2; pairs with M-ROUTE-AI-REVIEW)
notion_sync_status: pending session-end batch
codex_review_relay: 86gs gpt-5.4 xhigh · MANDATORY
---

# DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE · POST /ai-diagnose

## Status

**Accepted 2026-05-14** — second route-level sub-DEC under V62-A charter
(pairs with M-ROUTE-AI-REVIEW). Lands one new route module
(`ui/backend/routes/ai_diagnose.py`, 612 LOC) + one new test file
(`ui/backend/tests/test_ai_diagnose_route.py`, 15 tests, 0.55 s green)
that plumb the V-series corpus into a live diagnose endpoint and
cross-reference findings with the LANDED `advisor_stack`.

## Goal

Close Done Definition dimension #1 second slot: `Advisor stack 路由聚合 · 2
routes LANDED · 每条 ≥3 advisor 调用 / V-series hit`. M-ROUTE-AI-REVIEW
delivers the review surface; this sub-DEC delivers the diagnose surface.

Use case (from V61-198 §"AI Diagnose button"): on a solver convergence
failure, the engineer pastes a symptom (e.g. *"janafThermo limit warnings
flood the log"* / *"cellZoneInside inside empty for solid region"*); the
route returns the top-ranked matching V-series rows + an extracted `Fix`
suggestion + (if `case_dir` provided) a cross-reference to the live
advisor_stack output for that case.

## Scope

### What this sub-DEC adds

- New route `ui/backend/routes/ai_diagnose.py` (`POST /api/ai-diagnose`):
  - Pydantic request schema `AIDiagnoseRequest`: `symptom_text` (required),
    `solver_log_excerpt`, `case_dir`, `llm_match`, `top_k`.
  - Pydantic response schema `AIDiagnoseResponse`: `request_id`,
    `v_row_matches[VSeriesMatch]`, `stack_report` (optional summary),
    `audit_artifact_path`, `llm_match_used`, `timing`, `corpus_size`.
  - V-series parser: `### V<N> · <title>` heading-aware split, Fix-field
    extraction from the per-row markdown table.
  - Scoring: title-weighted token overlap (title 3x, body 1x), normalized
    by query length, clamped to `[0, 1]`.
  - Stack cross-reference: when `case_dir` resolves and a
    `parts_manifest.json` is present, `assemble_stack` runs and any
    surfaced V-rows are boosted (+0.10) in the diagnose ranking.
  - Audit persistence: `.planning/audits/ai_diagnose/<request_id>.json`
    with timing, request echo, corpus size, stack summary, matches.
  - Loopback-only via shared `_loopback_guard.require_loopback` (blast
    radius parity with `/ai-review` + `/ai-chat`).
  - Module-level corpus cache keyed by `(path, mtime)` — invalidates on
    file edit or attribute monkeypatch, so test redirects compose with
    the live cache path used in production.

- New tests `ui/backend/tests/test_ai_diagnose_route.py` — 15 cases
  covering V41/V92 top-3 matching, LLM-offline, audit round-trip,
  TrustGate, crash isolation, 4Q gate, ranking order, case_dir →
  stack invocation, error paths, top_k clamping, lexical no-LLM-import
  scan, and stack-crash isolation.

- main.py wiring: `from ui.backend.routes import ai_diagnose` +
  `app.include_router(ai_diagnose.router, prefix="/api", tags=["ai-diagnose"])`.

### Surface-scan disposition (DEC-V61-088)

An existing route `GET /api/cases/{case_id}/ai-diagnose` (N6.3
LLM-driven, case-bound) is in `routes/ai_advisor.py`. Disposition:
**parallel new** — different verb (POST), different path, different
contract (stack-level LLM-offline V-series matching vs case-bound
LLM-driven failure-mode advisor). Both coexist; FastAPI route table
verified (`/api/ai-diagnose` + `/api/cases/{case_id}/ai-diagnose`).
Lineage: N6.3 predates V62-A and remains the case-bound LLM surface;
the new POST route is V62-A stack-level. Future consolidation deferred
to V63 if it surfaces as overlap.

### What this sub-DEC explicitly does NOT add

- No LLM provider import / call. `llm_match=True` is forward-compatible
  but always returns `llm_match_used=False` until a provider is wired in
  a future sub-DEC. Base ranking remains the contractual SSOT (4Q gate
  (1) requires LLM-offline functionality).
- No mutation of any case directory file. Route only **reads**
  `parts_manifest.json` (JSON parse, no write-back) under `case_dir`.
  `test_4q_gate_route_does_not_write_inside_case_dir` enforces this.
- No N6.1 RAG loader import. V-series parser is inlined so the 4Q gate
  (1) lexical scan can pin absence of any LLM-stack import.
- No richer artifact discovery (shm_dict / thermo_dict / interface specs).
  M-ROUTE-AI-REVIEW already plumbs those for the review surface; the
  diagnose surface intentionally narrows to `parts_manifest` so each
  route stays Codex-reviewable in isolation. Richer cross-reference is
  M-4Q-AUDIT scope.

## Four-question gate inline verification

| # | Question | Verification | Result |
|---|---|---|---|
| 1 | LLM offline OK? | `test_4q_gate_no_llm_imports_in_route_module` lexically scans route source for forbidden tokens (`anthropic`, `openai`, `llm_provider`, `ai_advisor`, `corpus_loader`). `test_llm_match_true_returns_llm_match_used_false_offline` exercises the wire flag + verifies base ranking still surfaces matches | PASS |
| 2 | Artifacts output? | `test_audit_artifact_round_trips` reads back the JSON, asserts `request_id` echo, schema_version pin, and presence of timing / matches / corpus / stack fields | PASS |
| 3 | TrustGate? | `test_trust_gate_every_match_carries_v_row_id_and_rationale` enforces each match has v_row_id (regex `^V\d+$`), v_row_title, similarity_rationale, similarity_score in `[0,1]`. Rationale enumerates which title/body tokens matched + flags stack cross-reference | PASS |
| 4 | AI advisory only? | `test_4q_gate_route_does_not_write_inside_case_dir` snapshots case_dir bytes before/after a POST that includes case_dir; asserts equality | PASS |

All 4Q-gate tests are part of the 15-test green suite.

## Test coverage detail

| # | Test | What it pins |
|---|---|---|
| 1 | `test_v41_symptom_top_3_match` | V41 surfaces top-3 on "janafThermo limit warnings" |
| 2 | `test_v92_symptom_top_3_match` | V92 surfaces top-3 on "cellZoneInside inside empty for solid" |
| 3 | `test_llm_match_true_returns_llm_match_used_false_offline` | 4Q gate (1) on wire-flag path |
| 4 | `test_audit_artifact_round_trips` | 4Q gate (2) — artifact deserializable |
| 5 | `test_trust_gate_every_match_carries_v_row_id_and_rationale` | 4Q gate (3) — every match auditable |
| 6 | `test_corpus_load_failure_crash_isolated_with_500` | Missing corpus → structured 500 + audit logged |
| 7 | `test_4q_gate_route_does_not_write_inside_case_dir` | 4Q gate (4) — no case_dir writes |
| 8 | `test_at_least_3_matches_ranking_descending` | ≥3 matches, scores strictly non-increasing |
| 9 | `test_case_dir_provided_invokes_assemble_stack` | case_dir + parts_manifest → stack_report populated |
| 10 | `test_empty_symptom_returns_400_with_actionable_error` | Empty symptom → 400 + actionable detail |
| 11 | `test_missing_case_dir_returns_400` | Missing case_dir → 400 with `case_dir_not_found` |
| 12 | `test_solver_log_excerpt_contributes_to_matching` | Excerpt augments token signal |
| 13 | `test_top_k_clamps_response_length` | top_k=2 → ≤2 matches |
| 14 | `test_4q_gate_no_llm_imports_in_route_module` | 4Q gate (1) lexical scan |
| 15 | `test_stack_crash_isolation_route_still_returns_200` | assemble_stack raises → 200, stack_report=None, audit captures error |

## Codex review

`codex-review-relay --base origin/main` on the commit, **MANDATORY**
per V62-A charter §"Codex review" + RETRO-V61-001 risk-tier (route is
operator-facing security boundary). Round cap = 3 per V133. Findings
classified P1/P2/P3 will be addressed inline or queued to retro per
v2.3 governance.

## v2.3 governance compliance

- **DEC scope**: sub-DEC scope (single route + tests). Parent DEC is the
  V62-A charter (≥3 共享代码路径 already established).
- **Codex review**: MANDATORY (route = operator-facing).
- **Round cap = 3**: per V133.
- **Kogami**: opt-in only per V133; not invoked.
- **Notion sync**: deferred to session-end batch (Status=Accepted).
- **Surface-scan trailer**: commit body carries `Surface-scan-found:
  ui/backend/routes/ai_advisor.py:95 · disposition: parallel new` (per
  DEC-V61-088).
- **Counter**: `autonomous_governance_counter_v61` +1 (pure telemetry).

## Open follow-ups (out of scope for this sub-DEC)

1. **LLM augmentation** — wire `llm_match=True` to a re-ranker (likely
   reusing N6.1 / N6.3 provider infra). Base ranking must remain a
   functional fallback. Candidate sub-DEC under V62-A Tier 2 or V63.
2. **Richer artifact discovery** — diagnose surface currently only reads
   `parts_manifest.json`. M-4Q-AUDIT will define a discovery protocol
   that this route can adopt to mirror M-ROUTE-AI-REVIEW's shm/thermo
   reach. Decision deferred until M-4Q-AUDIT lands.
3. **Persona-aware ranking** — engineer vs first-time-user weights on
   different V-row fields. Out of scope until persona signal lands.
4. **Cross-route consolidation** — at V63, evaluate whether
   `GET /cases/{id}/ai-diagnose` (N6.3) and `POST /ai-diagnose` should be
   unified or whether the parallel split is permanent product surface.

## Confidence

`confidence: med` — pattern is well-established (B23 + M-ROUTE-AI-REVIEW
sibling) and the surface is narrower than B24's. Risk: V-series corpus
parsing is custom (not reusing N6.1 RAG loader by 4Q-gate (1) design);
the parser is minimal but Codex review is the appropriate quality gate
for that custom parser.

## End of sub-DEC
