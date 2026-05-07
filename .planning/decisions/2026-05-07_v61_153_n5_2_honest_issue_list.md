---
decision_id: DEC-V61-153
title: N5.2 · Honest issue list (rule-based enumerator · no AI prose)
status: Accepted
parent_dec: V61-151
phase: N5
notion_sync_status: pending
---

# DEC-V61-153 · N5.2 Honest Issue List

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Medium-risk per
N5 charter; Opus confidence high — pure rule-based enumerator, no
mutation surface, no V132 entry. Charter §risk-register row 2
explicit "MUST NOT generate AI prose" is structurally enforced
(no LLM imports, every Issue.message is a literal short factual
statement).

## Decision

Land the structured issue enumerator end-to-end:

- `Issue` + `IssueList` Pydantic schemas with stable `SourceRuleId`
  literal (17 rule IDs covering geometry / mesh / physics / solver /
  output)
- `enumerate_issues(case_dir)` walker that reuses the N5.1 case-state
  builder, then layers checkMesh metrics + residual-log scanning
- Stable sort: critical → warning → info; alpha by source_rule_id
  within each severity

## Wire shape

```python
SourceRuleId = Literal[
    "geometry_stl_missing",
    "geometry_bbox_missing",
    "geometry_no_named_patches",
    "mesh_polymesh_missing",
    "mesh_zero_cells",
    "mesh_dense_warning",
    "mesh_low_count_warning",
    "mesh_checkmesh_failed",
    "mesh_severe_non_ortho_faces",
    "physics_dicts_missing",
    "physics_regime_missing",
    "physics_no_citation",
    "solver_no_derivation",
    "solver_tolerance_fast_survey",
    "solver_les_subgrid_todo",
    "output_residuals_stalled",
    "output_run_log_missing",
]

class Issue(BaseModel):  # extra=forbid
    severity: Literal["critical", "warning", "info"]
    source_rule_id: SourceRuleId
    scope: Literal["geometry", "mesh", "physics", "solver", "output"]
    message: str  # 1..300 chars, NO AI prose
    details: dict[str, str | int | float | bool | None]

class IssueList(BaseModel):  # extra=forbid
    case_id: str
    issues: list[Issue]
    generated_at: str
    # convenience properties: critical_count / warning_count / info_count
```

## Rule outputs (17 stable IDs)

Geometry (3):
- `geometry_stl_missing` (critical) — no STL imported
- `geometry_bbox_missing` (critical) — polyMesh/points absent
- `geometry_no_named_patches` (warning) — boundary file empty

Mesh (5):
- `mesh_polymesh_missing` (critical) — polyMesh dir absent
- `mesh_zero_cells` (critical) — polyMesh present but cell_count=0
- `mesh_low_count_warning` (warning) — < 100 cells
- `mesh_dense_warning` (info) — > 5M cells
- `mesh_checkmesh_failed` (warning) — checkMesh mesh_ok=False

Physics (3):
- `physics_dicts_missing` (critical) — no dicts at all
- `physics_regime_missing` (critical) — momentumTransport missing
- `physics_no_citation` (placeholder for N5.3 manifest integration)

Solver (3):
- `solver_no_derivation` (warning) — regime declared, no solver
- `solver_tolerance_fast_survey` (info) — fast_survey tier hint
- `solver_les_subgrid_todo` (info) — LES-stub regime reminder

Output (2):
- `output_residuals_stalled` (warning) — last 5 U residuals stable < 1%
- `output_run_log_missing` (info) — emitted ONLY when physics is
  committed (else "engineer hasn't reached Step 4 yet" — silent)

## Residual-stall heuristic

Conservative — last 5 `Solving for U[xyz]` initial residuals must
ALL show < 1% relative change consecutively. Avoids false-positives
on legitimately converging residuals (which drop fast, e.g. 1e-1 →
1e-2 → 1e-3 → 1e-4 → 1e-5 has ~10× drops, not 1%).

## V130 / V132 enforcement

- Enumerator reuses N5.1 builder (read-only)
- All `Issue.message` strings are literal factual statements; no
  LLM call anywhere
- Test asserts no `llm_provider` / `llm_coach` imports in enumerator
- Test asserts `case_issues` not in `KNOWN_MUTATION_FUNCTIONS`

## Files touched

Backend (NEW):
- `ui/backend/schemas/honest_issue_list.py` — schemas
- `ui/backend/services/case_issues/__init__.py`
- `ui/backend/services/case_issues/enumerator.py` — rule engine

Tests (NEW):
- `ui/backend/tests/test_honest_issue_list.py` (18 cases — schema
  validators including all 4 literal enforcements + message bounds +
  extra=forbid; severity_count properties; empty case → 3 critical
  rule IDs surfaced; progressive resolution as scaffold grows; 1-cell
  mesh → low_count_warning; LES-stub → subgrid_todo; stalled vs
  decreasing residuals; log_missing emission gated on physics
  committed; sort order critical-first; V130 contract — no LLM
  imports + not in KNOWN_MUTATION_FUNCTIONS)

## Verification

- 18 N5.2 tests green
- 14 V132 contract tests still green
- Sort invariant tested across multi-severity cases
- Stable rule IDs allow programmatic audit-script integration

## Out of scope (future sub-DECs)

- Audit V2 manifest provenance — N5.3 (will source `physics_no_citation`
  rule data)
- Frontend issue-list panel (rendering by severity + scope filter) —
  UI integration post-N5
- More residual-stall heuristics (per-equation, regime-aware) —
  N5-extend
- Aggregating issues across multiple cases (batch report) — defer
