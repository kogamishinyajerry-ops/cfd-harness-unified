---
decision_id: DEC-V61-138
title: N2.4 · checkMesh advisor (rule-based fix suggestions, read-only metadata)
status: Accepted
parent_dec: V61-134
phase: N2
notion_sync_status: pending
---

# DEC-V61-138 · N2.4 checkMesh Advisor

## Status

**Accepted 2026-05-07** — V133 sub-DEC schema (slim 6-field
frontmatter). Low-risk read-only addition; no Codex pre-merge mandate
per N2 charter §3 row "N2.4 · checkMesh advisor (read-only suggestions)
| low | no [Pre-merge Codex]". Opus confidence high — pure additive
function over already-populated V126 fields, no mutation surface, no
new route, no new HTTP method.

## Decision

Add a rule-based advisor that maps populated checkMesh metrics on
`MeshQualityReportV126` to human-readable fix suggestions. Engineer
reads + decides; UI renders `recommended_change` as displayed text
only. **NO auto-apply, NO Apply button, NO POST anywhere in the
advisor surface** (V130 Principle B + V132 contract).

## Wire contract

`MeshFixSuggestion` (read-only metadata):
```python
class MeshFixSuggestion(BaseModel):
    metric: Literal[
        "max_non_orthogonality", "max_skewness", "max_aspect_ratio",
        "n_severe_non_ortho_faces", "mesh_ok",
    ]
    severity: Literal["critical", "warning", "info"]
    suggestion_text: str
    recommended_change: dict | None = None
```

`MeshQualityReportV126` gains `suggestions: list[MeshFixSuggestion] =
Field(default_factory=list)`. Returned populated when
`run_checkmesh=true` AND checkMesh produced metrics; empty when
checkMesh skipped (graceful degrade) OR mesh is clean.

## Rule thresholds (matches MeshQualityCard band ladders)

| Metric | Severity ladder | Recommended_change route hint |
|---|---|---|
| `n_severe_non_ortho_faces > 0` | warning (top-3 patches localized) | Step 2 → sizing OR region refinement |
| `max_non_orthogonality > 75°` | critical | Step 2 → sizing (halve characteristic length) |
| `max_non_orthogonality > 65°` | warning (no change) | informational only |
| `max_skewness > 0.95` | critical | Step 2 → sizing OR region refinement (curvature) |
| `max_skewness > 0.7` | warning (no change) | informational only |
| `max_aspect_ratio > 1000` | warning | Step 2 → prism layers (N2.3) |
| `max_aspect_ratio > 100` | info (no change) | informational only |
| `mesh_ok=False` (no metric breach) + `failed_checks` non-empty | warning | review failed_checks list |

## V132 contract enforcement

`recommended_change` MUST contain `step` and/or `hint` keys (human-
readable text). Forbidden keys: `url`, `method`, `endpoint`, `route`,
HTTP verb names — anything that could be mistaken for an apply-button
payload. Test `test_recommended_change_never_contains_route_or_endpoint`
encodes this.

Frontend `SuggestionsList`:
- renders `recommended_change` entries as plain key/value text (font-
  mono, `<div>` not `<button>`)
- only one `<button>` permitted in the panel: the disclosure toggle
  (test asserts panel `querySelectorAll("button").length === 1`)
- no event handler ever calls `api.*` mutating endpoints

## Files touched

Backend:
- `ui/backend/services/mesh_quality/schemas.py` — `FixSeverity`,
  `MeshFixSuggestion`, `suggestions` field on `MeshQualityReportV126`
- `ui/backend/services/mesh_quality/advisor.py` — `derive_suggestions()`
  rule engine
- `ui/backend/services/mesh_quality/__init__.py` — re-exports
- `ui/backend/services/mesh_quality/analyzer.py` — wire suggestions via
  `model_copy(update=...)` on the V126 path

Frontend:
- `ui/frontend/src/pages/workbench/step_panel_shell/types.ts` —
  `FixSeverity` + `MeshFixSuggestion` + `suggestions` on V126
- `ui/frontend/src/pages/workbench/step_panel_shell/MeshQualityCard.tsx`
  — `SuggestionsList` collapsible panel

Tests:
- `ui/backend/tests/test_mesh_quality_advisor.py` (22 cases)
- `ui/backend/tests/test_checkmesh_runner.py` (+2 integration cases)
- `ui/frontend/src/pages/workbench/step_panel_shell/__tests__/MeshQualityCard.test.tsx`
  (+2 cases — empty-state + advisor render with V132 button-count
  invariant)

## Verification

- 22 advisor unit tests pass (rule engine, severity, V132 contract)
- 24 checkmesh runner tests pass (integration: clean → empty,
  failure → suggestions populated)
- 188 mesh-related backend tests green (no regression)
- 27 MeshQualityCard frontend tests pass (empty state + render +
  button-count invariant)
- 224 step_panel_shell frontend tests green (no regression)

## Out of scope (future work)

- AI coach integration that surfaces suggestions in chat (M6 territory)
- Per-suggestion "Open Step 2 → sizing" navigation deep-links (UI
  could add later as pure routing; still no apply path)
- Density / coverage metric suggestions (would require V128+ data)
