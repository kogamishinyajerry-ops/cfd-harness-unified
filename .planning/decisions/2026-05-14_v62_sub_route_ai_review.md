---
decision_id: DEC-V62-A-sub-ROUTE-AI-REVIEW
title: M-ROUTE-AI-REVIEW · POST /ai-review · advisor stack route · 4Q gate inline-verified
status: Accepted
parent_dec: V62-A-charter
phase: V62-A Tier 1 · M-ROUTE-AI-REVIEW (first of 2 stack-level routes · partially unblocks M-4Q-AUDIT)
notion_sync_status: pending
---

# DEC-V62-A-sub-ROUTE-AI-REVIEW · POST /ai-review

## Status

**Accepted 2026-05-14** — second sub-DEC of V62-A charter. Lands one new
route module (`ui/backend/routes/ai_review.py`, 315 LOC) + one new test
file (`ui/backend/tests/test_ai_review_route.py`, 329 LOC, 12 tests
green) that exposes `advisor_stack.assemble_stack()` as a FastAPI
endpoint with audit-artifact persistence and a four-question-gate-
compliant LLM augment surface.

## Goal

Close stack-level route #1 of 2 (`POST /ai-review`), advancing Done dim
\#1 from 0/2 → 1/2 and partially instantiating Done dim \#2 (4Q audit
framework). Together with M-ROUTE-AI-DIAGNOSE (next sub-DEC), this
unblocks M-4Q-AUDIT cross-feature audit.

## Scope

### What this sub-DEC adds

- New route module `ui/backend/routes/ai_review.py`:
  - `AIReviewRequest` / `AIReviewResponse` Pydantic v2 wire schemas
  - `POST /ai-review` route — pure dispatch of `assemble_stack(...)`
  - Auto-discovery of `parts_manifest` / `shm_dict` / `thermo_dict` /
    `thin_wall_inputs` under `<case_dir>/inputs/{*.yaml,*.yml,*.json}`
  - Audit-artifact persistence to `<repo>/.planning/audits/<label>_ai_review_<ts>.json`
  - Optional `llm_enhance` flag that imports `llm_provider` in a
    try/except — sets `llm_enhanced=True` if importable, never invokes
    the provider (zero LLM call to keep 4Q gate honest)
- Registered in `ui/backend/main.py` (1 import + 1 `include_router`)
- New test file `ui/backend/tests/test_ai_review_route.py` (12 tests):
  - parts_manifest only · case_dir auto-discover · empty payload
  - bad case_dir → 400 actionable
  - LLM import-error downgrade · default llm_enhance=False · llm_enhance=True
    with importable provider
  - audit JSON round-trip · TrustGate per-finding provenance
  - crash isolation (advisor exception → 200) · explicit-wins-over-autodiscover
  - 4Q gate compliance: route writes no files inside `case_dir`

### What this sub-DEC does NOT change

- `ui/backend/services/advisor_stack.py` (frozen — only imported)
- Other advisor leaf modules (frozen by V132 architecture lock)
- Other routes in `ui/backend/routes/*.py` (no edits)
- `.planning/ARC-GOAL.md` (main session reconciles)

## Non-goals

- The optional `llm_enhance` surface does **not** invoke any provider.
  Real LLM-grounded review continues to live on the loopback-gated
  `GET /api/cases/{case_id}/ai-review` (N6.2 / `ai_advisor.py`); this
  POST route is the **dispatch** surface, not the LLM-grounded one.
- Auto-discovery is intentionally minimal: YAML/JSON only, names fixed.
  OpenFOAM-native `system/snappyHexMeshDict` parsing is out of scope
  (callers wanting that compose the discovery upstream).

## Surface-scan disposition

Pre-implementation surface scan found existing `ui/backend/routes/ai_advisor.py`
with `GET /cases/{case_id}/ai-review` (N6.2 corpus-LLM-grounded review).

**Disposition: parallel-new** — justification:

- Different semantics: corpus-LLM citation-grounded review vs advisor
  stack dispatch report
- Different shapes: GET with `case_id` path param vs POST with arbitrary
  artifact payload + optional auto-discover
- Different blast radius / gating: loopback-only LLM gate vs zero-LLM
  4Q-gate-compliant dispatch
- Co-existence is intentional — UI fans out to both for layered review

Commit trailer: `Surface-scan-found: ui/backend/routes/ai_advisor.py
(GET /cases/{case_id}/ai-review N6.2) · disposition: parallel-new`

## 4-question gate inline verification (V130 thesis)

| # | Question | Verdict | Evidence |
|---|----------|---------|----------|
| 1 | LLM offline OK? | **PASS** | Base path imports zero LLM modules. `_try_llm_enhance` wraps the import in `try/except` and returns `(False, ms)` on failure. Test `test_llm_enhance_with_import_error_downgrades_gracefully` exercises the failure branch and asserts `llm_enhanced=False` + findings remain populated. |
| 2 | Artifacts output? | **PASS** | Every 200 response persists `<repo>/.planning/audits/<label>_ai_review_<UTC-ts>.json` and returns `audit_artifact_path` in the response. Test `test_parts_manifest_only_yields_2_advisors_and_persists_audit` asserts the file exists and `test_audit_artifact_round_trips` asserts deserialization. |
| 3 | TrustGate? | **PASS** | The route does not strip provenance: every `Finding` retains `source_advisor` + `evidence_v_rows` from the stack contract. Test `test_trustgate_every_finding_has_provenance` asserts both fields are populated on every finding in a multi-advisor dispatch. |
| 4 | AI advisory only? | **PASS** | Route reads `case_dir` (auto-discover) but writes only to `.planning/audits/`. Test `test_4q_gate_route_does_not_write_inside_case_dir` snapshots the case_dir tree before/after the call and asserts no mutations. |

## Codex review

- Mandatory per CLAUDE.md "Codex 必须调用场景" (security boundary — new
  public route, FastAPI surface, dispatches to LANDED advisor stack
  whose blast radius depends on caller-controlled inputs).
- Backend: 86gs `gpt-5.4` (xhigh) — governance baseline
- Round cap: 3 per v2.3 (DEC-V61-133)
- Commit trailer: `Codex-verified: <verdict>` after relay returns

## Tests

```
.venv/bin/python -m pytest ui/backend/tests/test_ai_review_route.py -q
# 12 passed in 0.40s

.venv/bin/python -m pytest \
  ui/backend/tests/test_advisor_stack.py \
  ui/backend/tests/test_ai_chat_route.py \
  ui/backend/tests/test_ai_advisor_contract.py \
  ui/backend/tests/test_ai_coach_route.py \
  ui/backend/tests/test_ai_review_route.py -q
# 94 passed in 1.24s
```

## ARC-GOAL fields the main session should reconcile

- `[x] M-ROUTE-AI-REVIEW` (this sub-DEC)
- Stack-level routes LANDED: **0/2 → 1/2**
- `M-4Q-AUDIT` cross-feature audit: **still blocked** (needs M-ROUTE-AI-DIAGNOSE)
- Done dim \#2 (4Q audit framework concrete instantiation): **partial**
  — `/ai-review` provides one concrete 4Q-gate-verified surface

## Risks / follow-ups

- `llm_enhance` semantics are deliberately weak (import-success only).
  If a future iteration wants real LLM-grounded augmentation it should
  go through a separate sub-DEC that handles loopback gating + provider
  selection.
- Auto-discovery filename convention is hard-coded; case-template
  authors must align. A future sub-DEC could promote this to a
  configurable manifest in `case_dir/inputs/.discovery.yaml`.
