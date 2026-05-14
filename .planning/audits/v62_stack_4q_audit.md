# V62-A · Stack-Level Four-Question Gate Audit

**Milestone**: M-4Q-AUDIT (Tier 1 closing milestone of `DEC-V62-A-charter`)
**Sub-DEC**: [`DEC-V62-A-sub-M-4Q-AUDIT`](../decisions/2026-05-14_v62_sub_4q_audit.md)
**Charter**: [`DEC-V62-A-charter`](../decisions/2026-05-14_v62_charter_dec.md)
**Modules in scope**: `advisor_stack.py` (composition) · `routes/ai_review.py` (POST `/api/ai-review`) · `routes/ai_diagnose.py` (POST `/api/ai-diagnose`)
**Pairs with**: [`test_4q_gate_stack_acceptance.py`](../../ui/backend/tests/test_4q_gate_stack_acceptance.py) (4 acceptance tests)
**Author**: Claude Code Opus 4.7 (1M ctx) · single-author audit
**Compiled**: 2026-05-14

---

## 1. Four questions (verbatim · V130 advisor-not-driver thesis)

1. **1Q · LLM offline OK?** — Every advisor surface must produce a working
   response when no LLM API key is present and no LLM module is imported.
2. **2Q · Artifacts output?** — Every advisor invocation must emit a
   persistable, machine-readable artifact (audit JSON on disk) plus
   per-finding provenance fields the operator can attach to a commit /
   DEC / retro.
3. **3Q · TrustGate?** — Every advisor finding must carry a
   `source_advisor` + `evidence_v_rows` tuple traceable back to canonical
   V-rows in `docs/openfoam_corpus/industrial_solver_findings_v_series.md`.
4. **4Q · AI advisory only?** — No advisor surface may mutate anything
   under a caller-supplied `case_dir`. The stack reads inputs, writes only
   to `.planning/audits/`, and the engineer remains the sole writer of
   the case state.

These four questions are the **gate**: any feature failing any one of
them is not eligible to land under the V62-A charter.

---

## 2. 3 × 4 cross-feature matrix

Each cell cites the specific test that pins the question for that module.
Acceptance-suite tests (4Q-AUDIT, this milestone) live in
`ui/backend/tests/test_4q_gate_stack_acceptance.py`; per-module inline
tests live in each module's existing test file (kept in place — this
audit aggregates rather than duplicates).

| Module | 1Q · LLM offline | 2Q · Artifacts | 3Q · TrustGate | 4Q · Advisory-only |
|---|---|---|---|---|
| **`advisor_stack.py`** (services · ~534 LOC) | inline: `test_4q_gate_no_llm_imports` (`test_advisor_stack.py:493`) lexically pins absence of `anthropic` / `openai` / `corpus_loader` / `llm_provider` / `ai_advisor` from module source + `sys.modules` snapshot | inline: `test_audit_call_fields_populated` (`test_advisor_stack.py:473`) asserts every `AdvisorCall` carries name + status + duration + version + non-empty input_summary | inline: `test_evidence_refs_only_include_dispatched_advisors` (`test_advisor_stack.py:484`) — V-rows surfaced are exactly the union of dispatched advisors' canonical tuples (`_V_ROWS_PER_ADVISOR`) | inline: `test_4q_gate_no_case_dir_writes` (`test_advisor_stack.py:510`) — `Path.write_text` / `write_bytes` monkeypatched to count → 0 writes during full-stack dispatch |
| **`routes/ai_review.py`** (POST `/api/ai-review` · ~432 LOC) | inline: default `llm_enhance=False` path → `llm_enhanced=False` (`test_ai_review_route.py:177`, `:184`) · acceptance: `test_q1_llm_offline_both_routes_return_200_with_payload` (`test_4q_gate_stack_acceptance.py`) with `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `AZURE_OPENAI_API_KEY` removed from env via `monkeypatch.delenv` | inline: `test_audit_artifact_round_trips` (`test_ai_review_route.py:188`) — JSON re-deserialization + field round-trip · acceptance: `test_q2_findings_carry_source_advisor_evidence_v_rows_and_audit_artifact` re-asserts audit file presence + finding provenance over the live HTTP surface | inline: `test_trustgate_every_finding_has_provenance` (`test_ai_review_route.py:205`) — every finding has source_advisor + non-empty evidence_v_rows · acceptance: `test_q3_trustgate_every_evidence_v_row_is_canonical` enforces V-row ∈ `_V_ROWS_PER_ADVISOR[advisor]` over the wire payload | inline: `test_4q_gate_route_does_not_write_inside_case_dir` (`test_ai_review_route.py:249`) — pre/post `(mtime, size)` snapshot · acceptance: `test_q4_case_dir_sha256_unchanged_across_both_routes` strengthens to byte-level `sha256` equality |
| **`routes/ai_diagnose.py`** (POST `/api/ai-diagnose` · ~765 LOC) | inline: `test_4q_gate_no_llm_imports_in_route_module` (`test_ai_diagnose_route.py:370`) + `test_llm_match_true_returns_llm_match_used_false_offline` (`test_ai_diagnose_route.py:122`) · acceptance: `test_q1_llm_offline_both_routes_return_200_with_payload` exercises diagnose surface with API keys removed | inline: `test_audit_artifact_round_trips` (`test_ai_diagnose_route.py:141`) — `schema_version: v62-a-ai-diagnose-v1` pinned · acceptance: same Q2 test asserts audit JSON file on disk re-readable by `json.loads` | inline: `test_trust_gate_every_match_carries_v_row_id_and_rationale` (`test_ai_diagnose_route.py:162`) — every `VSeriesMatch` regex-matches `^V\d+$` + non-empty rationale + score in `[0,1]` · acceptance: Q3 test also walks `stack_report.findings` from the diagnose route to enforce canonical V-row membership | inline: `test_4q_gate_route_does_not_write_inside_case_dir` (`test_ai_diagnose_route.py:206`) — pre/post `read_bytes` equality · acceptance: Q4 test extends to sha256 dict comparison covering both routes back-to-back over the same `case_dir` |

---

## 3. Acceptance suite (this milestone)

File: `ui/backend/tests/test_4q_gate_stack_acceptance.py` (4 tests · 0.44 s · 4/4 PASS in
isolation · 72/72 PASS when bundled with the per-module suites
above).

| Test | Pinned question | Strategy |
|---|---|---|
| `test_q1_llm_offline_both_routes_return_200_with_payload` | 1Q | `monkeypatch.delenv("ANTHROPIC_API_KEY")` + `OPENAI_API_KEY` + `AZURE_OPENAI_API_KEY` → POST `/api/ai-review` (multi-advisor payload) **and** `/api/ai-diagnose` (case_dir provided) → both 200 + `advisor_count ≥ 2` (review) / `v_row_matches` non-empty (diagnose) + `llm_enhanced=False` / `llm_match_used=False`. |
| `test_q2_findings_carry_source_advisor_evidence_v_rows_and_audit_artifact` | 2Q | Inspect each response Finding for `source_advisor` + non-empty `evidence_v_rows`. Open `audit_artifact_path` on disk; re-load JSON; assert `report.advisor_count` round-trips. |
| `test_q3_trustgate_every_evidence_v_row_is_canonical` | 3Q | Build canonical set = `⋃ _V_ROWS_PER_ADVISOR.values()`. For every finding (both routes), assert `evidence_v_row ∈ canonical` AND `evidence_v_row ∈ _V_ROWS_PER_ADVISOR[source_advisor]` (per-advisor narrow check). Also walks the diagnose `stack_report.findings` payload. |
| `test_q4_case_dir_sha256_unchanged_across_both_routes` | 4Q | sha256 every file under `case_dir`, POST `/api/ai-review`, recompute, assert equality. POST `/api/ai-diagnose`, recompute, assert equality against the initial snapshot (covers sequencing across routes). |

---

## 4. What this audit does NOT claim

- It does **not** prove there is no LLM call at runtime under load — it
  proves there is no LLM import surface in the module sources and no LLM
  env key is consulted by the test path. Production probes that fan out
  to siblings such as `/api/cases/{id}/ai-review` (N6.2, LLM-driven) are
  out of scope: those routes are stack-external and carry their own
  per-route 4Q stance.
- It does **not** prove all 8 LANDED + 1 D-class advisors are reachable
  through every route. `routes/ai_diagnose.py` deliberately narrows to
  `parts_manifest` (per its sub-DEC §"What this sub-DEC does NOT add");
  the audit asserts the surfaces that ARE wired, not coverage of every
  advisor by every route.
- It does **not** replace Codex review. Codex APPROVE-on-merge for the
  three upstream sub-DECs (`b27c99f → 4850683` for STACK-ASSEMBLY; chain
  closure at `943e2cd` for ROUTE-AI-REVIEW; `f8b73b3` for
  ROUTE-AI-DIAGNOSE) remains the security-boundary review record. M-4Q-AUDIT
  is a stack-level cross-feature audit, not a security review.

---

## 5. Sign-off

**Verdict**: PASS · 4Q gate cleared at stack level for V62-A Tier 1.

**Evidence commits** (parent_dec: `V62-A-charter`):

| Module | Final LANDED commit | Sub-DEC frontmatter |
|---|---|---|
| `services/advisor_stack.py` | `4850683` (R3 V133 round cap final) | `DEC-V62-A-sub-STACK-ASSEMBLY` (Accepted 2026-05-14) |
| `routes/ai_review.py` | `943e2cd` (R2 APPROVE) | `DEC-V62-A-sub-ROUTE-AI-REVIEW` (Accepted 2026-05-14) |
| `routes/ai_diagnose.py` | `f8b73b3` (R2-verbatim chain close) | `DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE` (Accepted 2026-05-14) |

**Audit commit**: this file + `test_4q_gate_stack_acceptance.py` + sub-DEC
`DEC-V62-A-sub-M-4Q-AUDIT` (Accepted 2026-05-14) — see ARC-GOAL Tier 1
status line for the exact commit SHA.

**Signed**: Claude Code Opus 4.7 (1M ctx) main session · 2026-05-14
· `confidence: med`.

**Effect on Done Definition**: dimension #2 (four-question gate
cross-feature audit) moves from `partial (per-advisor LLM-offline OK ·
stack 未审)` to `MET ✓` — see `.planning/ARC-GOAL.md` Tier 1 + counter
block.

---

## 6. Follow-ups (out of scope for M-4Q-AUDIT)

- **Stack-level Track C dogfood** (M-STACK-TRACK-1/2/3, Tier 2) will
  exercise the same 4Q surface end-to-end on real industrial cases.
  Should any session uncover a 4Q violation, that is a Tier 2 finding
  and ratchets the audit (this file gets a `## 7. Findings & corrections`
  appendix per V61-198 audit-amendment precedent).
- **Drift hook v2** (M-DRIFT-V2, Tier 2) will enforce the V-series
  ↔ runtime corpus invariant at the `/ai-review` boundary; that is the
  natural follow-up to Q3 (TrustGate) once the corpus grows past the
  current ~100 rows.
- **Diagnose surface widening** — adding shm_dict / thermo_dict / thin_wall
  discovery to `/ai-diagnose` is parked behind a future sub-DEC (see
  `DEC-V62-A-sub-M-ROUTE-AI-DIAGNOSE` §"What this sub-DEC does NOT add").
  When that surfaces, M-4Q-AUDIT§3 expands by one acceptance test and
  this audit is re-signed.
