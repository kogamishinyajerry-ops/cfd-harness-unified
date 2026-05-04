---
decision_id: DEC-V61-122
title: Mesh-quality adviser foundation · polyMesh-derived metrics + AI prompt integration · GET /api/cases/{id}/mesh-quality
status: Proposed (2026-05-04 · pre-implementation surface scan complete; Codex pre-merge MANDATORY per RETRO-V61-001 multi-file backend + new operator-facing endpoint + AI-system-prompt extension triggers)
codex_tool_report_path: reports/codex_tool_reports/v61_122_r1_chain.md (to be created)
codex_review_relay: CRS gpt-5.4 high (default per V61-119 §L2 sustained-86gs-instability protocol)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 mandate "按你的顺序和建议，继续推进" — start of #2 (mesh-quality 三明治) on the differentiation list. V120+V121 closed the AI-coach-with-hands surface; V122 widens what the coach actually KNOWS by giving it mesh metrics that today's UI buries in the Step-2 substeps. V122 is deliberately the lightweight adviser-only half of a 2-DEC arc H→I (V123/V124 will add Docker checkMesh + mesh remediation tool).
parent_decisions:
  - DEC-V61-121 (AI coach action proposals · this DEC's prompt-integration host — when V123 lands the mesh-regenerate tool, the proposal protocol consumes it unchanged)
  - DEC-V61-119 (LLM coach SSE backend · this DEC extends `build_coach_system_prompt` with an optional mesh-quality section)
  - DEC-V61-116 (case completeness analyzer · sibling pattern · V122's MeshQualityReport mirrors CaseCompletenessReport's design)
  - DEC-V61-108 (per-patch BC classification · same polyMesh/boundary parser pattern; V122 extracts the parsing into its own service to avoid coupling V108's BC concerns to V122's quality concerns)
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · multi-file backend + new operator endpoint + AI-prompt extension triggers Codex pre-merge)
parent_artifacts:
  - ui/backend/services/case_solve/bc_setup.py (existing polyMesh parser pattern · V122 reuses ``_split_foam_block`` + ``_parse_points`` shape; service-extracted to avoid the coupling)
  - ui/backend/services/case_solve/bc_setup_from_stl_patches.py:175-194 (existing ``_read_patch_ranges`` for boundary file · V122's MeshQualityAnalyzer uses the same regex)
  - ui/backend/services/llm_coach/prompts.py (V119/V121 system-prompt composer · V122 extends with optional mesh_quality argument)
  - ui/backend/routes/ai_coach.py:124-138 (V119 stream route · V122 adds an inner mesh-quality fetch, gracefully tolerates 404 / no polyMesh yet)
counter_impact: +1 (autonomous_governance: true · new backend service + new operator endpoint + system-prompt extension. Kogami-trigger check: not phase-close, not RETRO draft, not arc-size retro at counter 80 (counter ≥ 20 trigger continues to be deferred per ongoing user mandate "按你的顺序和建议，继续推进" which extends the prior deferral), not governance-rule change. Codex pre-merge MANDATORY.)
notion_sync_status: pending — Notion MCP server still disconnected; sync when reconnected
self_estimated_pass_rate: 65% (predicted 2-3 rounds · V1 scope-down pattern proven 3 consecutive arcs · backend-only, pure Python, no Docker, no new UI · cascade-dimension count is single-axis: polyMesh format edge cases · proposal-parser pattern from V121 already validated)

---

# DEC-V61-122 · Mesh-quality adviser foundation

## Why now

V120+V121 gave the AI coach hands but its KNOWLEDGE is still bounded by V61-116's case-completeness report (manifest schema + gold-standard preconditions). When an engineer asks "is my mesh too coarse?" the coach can only say "I don't have mesh data". V122 closes that gap with a lightweight pure-Python mesh-quality analyzer: cell count, bounding box, patch face stats, simple warnings. The coach can now answer mesh-state questions grounded in the actual polyMesh data the case wrote during gmshToFoam.

This is item **H** of the 2-DEC arc H→I (mesh-quality 三明治 · #2 on the differentiation list). V123 (item I) will add the Docker checkMesh integration for skewness / orthogonality and a mesh-regenerate tool that participates in V121's proposal protocol. V122 ships the foundation FAST — adviser-only, no new UI, no Docker, no remediation — so the AI's mesh awareness is online while V123's heavier surfaces author cleanly.

## Surface scan (per DEC-V61-088)

**ROADMAP scan**: post-W5 + workbench-rollout return zero hits for `mesh_quality`, `mesh-quality`, `MeshQualityReport`, `checkMesh`. The existing `mesh-metrics` route (V61-040ish) is GCI-focused — grid-convergence statistics from fixtures, not actual cell-quality. V122 is structurally distinct.

**Existing-implementation grep** (`grep -rn "mesh_quality\|MeshQualityReport\|checkMesh" ui/backend/`):
- Zero matches for `mesh_quality` / `MeshQualityReport`
- Zero matches for `checkMesh` (no Docker integration today)
- Existing polyMesh parsers in `case_solve/bc_setup.py` (`_split_foam_block`, `_parse_points`) and `case_solve/bc_setup_from_stl_patches.py` (`_read_patch_ranges`) — V122 EXTRACTS the parsing patterns into a new service to avoid cross-domain coupling

**Disposition**: **parallel-new** (`services/mesh_quality/` + `routes/mesh_quality.py` are net-new) AND **extend** (`services/llm_coach/prompts.py` extended with optional mesh-quality argument · `routes/ai_coach.py` stream pipeline extended to fetch mesh-quality alongside completeness · existing polyMesh parsers in `case_solve/` are NOT modified — V122 reads its own parsing).

**Surface-scan trailer**: commits will carry `Surface-scan-found: case_solve/bc_setup.py + case_solve/bc_setup_from_stl_patches.py (existing polyMesh parsers · V122 mirrors patterns), llm_coach/prompts.py + ai_coach.py (V119/V121 prompt host · V122 extends), mesh_metrics.py (V61-040 GCI route · structurally distinct) · disposition: parallel-new (mesh_quality service + route) + extend (llm_coach prompts + ai_coach stream)`.

## Decision

Add a pure-Python `services/mesh_quality/` package that parses `<case_dir>/constant/polyMesh/{points, owner, boundary}` into a structured `MeshQualityReport`. New `GET /api/cases/{id}/mesh-quality` route returns it. The V61-119 `build_coach_system_prompt` accepts an optional `mesh_quality_report` argument and renders a "Current mesh snapshot" section after the case-state line. V61-119's `/api/ai-coach/stream` route fetches the report alongside the completeness snapshot and passes it through; missing polyMesh tolerated gracefully (the prompt simply skips the mesh section).

### Architecture (V1 scope)

```
ui/backend/services/mesh_quality/        — NEW PACKAGE
  __init__.py                            — public API exports
  schemas.py                             — MeshQualityReport, MeshWarning, Severity
  analyzer.py                            — analyze_mesh_quality(case_dir) -> MeshQualityReport
                                            Read polyMesh/{points, owner, boundary}.
                                            Compute cell_count, point_count, internal_face_count,
                                            boundary_face_count, bounding_box (min/max corners),
                                            volume, surface_area_estimate, mesh_density, per-patch
                                            face counts, and a list of MeshWarning entries:
                                            - critical: missing polyMesh, parse failure
                                            - warning: cell_count < 100, BB collapsed dimension,
                                                       patch with 0 faces
                                            - info: very_high_aspect_ratio_estimate, dense mesh
                                                    (cells > 5M for V1 dev hardware)

ui/backend/routes/mesh_quality.py        — NEW: GET /api/cases/{id}/mesh-quality
                                            404 when polyMesh dir missing or unreadable.
                                            500 when parse crashes (stable contract = report
                                            something, never opaque-500). 200 with report.

ui/backend/services/llm_coach/prompts.py — EXTEND: build_coach_system_prompt accepts
                                            optional mesh_quality_report argument; renders
                                            "=== Current mesh snapshot ===" after case state.
                                            Backwards-compatible: no arg → no mesh section
                                            (V120/V121 tests pass unchanged).

ui/backend/routes/ai_coach.py            — EXTEND: in /api/ai-coach/stream, after completeness
                                            pre-fetch, ALSO fetch mesh-quality (best-effort;
                                            log on failure, no abort). Pass to
                                            build_coach_system_prompt.

ui/backend/main.py                       — EXTEND: register mesh_quality router.

ui/backend/tests/test_mesh_quality.py    — NEW: analyzer unit tests with synthetic
                                            polyMesh fixtures.
ui/backend/tests/test_mesh_quality_route.py  — NEW: route-level tests.
ui/backend/tests/test_llm_coach.py       — EXTEND: prompt composition with mesh_quality argument.
ui/backend/tests/test_ai_coach_route.py  — EXTEND: stream route fetches mesh_quality.
```

### V1 explicit scope-down (per V61-119 §L1 anti-cascade discipline · 4th consecutive arc)

| Excluded V1 | Why | Where it goes |
|---|---|---|
| **Docker checkMesh integration** | Container exec + log parsing + cross-OpenFOAM-version compat is its own surface; V122 ships pure-Python first | V61-123 |
| **Skewness / orthogonality / non-orthogonality cell metrics** | Need checkMesh output | V61-123 |
| **Mesh-regenerate as a V121 tool** | New tool surface = new audit + new dispatch contract; ship after V123's checkMesh data | V61-124 |
| **Frontend mesh-quality card** | Let the AI surface mesh quality through chat in V122 (engineer asks "how's my mesh?" — coach answers); add a dedicated card after V123 has richer data | V61-123 frontend |
| **Per-cell volume histogram** | Computed via per-cell aggregation — sizable; V1 ships max/min/avg only | V61-123 |
| **Quality scoring (0-100 single number)** | Premature abstraction — engineer-facing meaning depends on case type | Out of scope until evidence justifies |
| **Caching** | V122 reads files cold each request; ~50-200ms typical; cache lifecycle is its own scope | V61-123 if dogfood shows latency pain |

### Public API contract

#### `MeshQualityReport` (in `services/mesh_quality/schemas.py`)

```python
class MeshWarning(BaseModel):
    severity: Literal["critical", "warning", "info"]
    code: str  # e.g. "cell_count_low", "bb_collapsed_dim", "patch_zero_faces"
    message: str  # zh/en human-readable

class MeshQualityReport(BaseModel):
    case_id: str
    polymesh_present: bool
    cell_count: int
    point_count: int
    internal_face_count: int
    boundary_face_count: int
    bounding_box_min: tuple[float, float, float]
    bounding_box_max: tuple[float, float, float]
    bounding_box_volume: float
    cells_per_unit_volume: float | None  # None if BB volume == 0
    patch_face_counts: dict[str, int]    # {patch_name: nFaces}
    warnings: list[MeshWarning]
```

#### `GET /api/cases/{case_id}/mesh-quality`

```
200 → MeshQualityReport JSON
404 → polyMesh missing (case_dir/constant/polyMesh/ doesn't exist)
500 → parse failure (corrupt polyMesh files); body carries failing_check
```

#### `build_coach_system_prompt` extension

```python
def build_coach_system_prompt(
    report: CaseCompletenessReport,
    project_rules: str = DEFAULT_PROJECT_RULES,
    *,
    max_missing_to_inline: int = 8,
    mesh_quality_report: MeshQualityReport | None = None,  # NEW
) -> str:
```

When `mesh_quality_report is not None`, append after the case state line:

```
=== Current mesh snapshot ===
cells=12450 · points=4321 · internal_faces=18234 · boundary_faces=2345 ·
bounding_box=[(-1.0,-1.0,0.0),(1.0,1.0,1.0)] · volume=8.0 · density=1556.25 cells/unit_vol

Mesh warnings:
- [WARNING] cell_count_low: only 80 cells in this mesh; under-refined for production
- [INFO] dense_mesh: 5.2M cells; large simulation cost expected

Patch face counts:
- walls: 1840
- inlet: 240
- outlet: 240
```

If absent, the section is omitted entirely.

## Risk register

| # | Risk | Likelihood | Mitigation | Status |
|---|---|---|---|---|
| 1 | polyMesh parser fails on edge-case format (e.g. binary `owner`/`points` files) | Medium | V1 supports ASCII format only (gmshToFoam emits ASCII by default); binary case raises ParseError → route 500 with structured detail; defer binary support to V123 | Mitigated V1 |
| 2 | Cell count miscount when reading owner file (e.g. trailing whitespace, comments) | Medium | Use the same regex/parsing pattern as V108's `_read_patch_ranges`; max(owner) + 1 = cell count is the canonical OpenFOAM definition; tested with synthetic fixtures | Mitigated |
| 3 | Bounding-box volume is 0 for 2D meshes (one BB axis collapsed) | Medium | Detect dim collapse explicitly; emit `bb_collapsed_dim` warning; report `cells_per_unit_volume = None` so consumers don't divide by zero | Mitigated by schema |
| 4 | Mesh-quality fetch latency adds to /api/ai-coach/stream pre-stream window | Low | Pure-Python file I/O; ~50-200ms on dev hardware; acceptable; documented; cache deferred to V123 | Accepted V1 |
| 5 | system prompt grows large for cases with many patches | Low | Patch face counts inline as a flat list; existing patches per case are small (typically <20); V123 may add cap if it grows | Accepted V1 |
| 6 | Stream route mesh-quality fetch raises → no graceful fallback → user-visible 500 | Medium | Best-effort fetch in route: try/except logs warning, mesh_quality=None, prompt still composes without mesh section | Mitigated |

## Self-pass-rate calibration

65% / 2-3 rounds. Fourth consecutive arc applying V1-scope-down anti-cascade. The risk surface is:
- polyMesh parser edge cases (1 round)
- Schema/API contract details (1 round)
- AI-prompt composition with optional argument (already-paved by V119/V121 patterns)

Mesh-quality has no cascade-prone mechanism (no cleanup, no concurrent state, no stream mid-flight). The honest risk is parser robustness against malformed polyMesh files — a single-axis surface.

## Successor pointers

- **V61-123 (next)**: Docker checkMesh integration · skewness/orthogonality/non-orthogonality + per-cell volume distribution · richer warnings · frontend mesh-quality card.
- **V61-124 (after V123)**: mesh-regenerate tool added to V121 registry · AI proposes adjusted gmsh params · engineer Accept → re-mesh under audit.

## Files comprising V61-122

```
.planning/decisions/2026-05-04_v61_122_mesh_quality_adviser.md
ui/backend/services/mesh_quality/__init__.py
ui/backend/services/mesh_quality/schemas.py
ui/backend/services/mesh_quality/analyzer.py
ui/backend/routes/mesh_quality.py
ui/backend/main.py                                 (extend: register router)
ui/backend/services/llm_coach/prompts.py           (extend: optional mesh_quality)
ui/backend/routes/ai_coach.py                      (extend: stream fetches mesh)
ui/backend/tests/test_mesh_quality.py              (new)
ui/backend/tests/test_mesh_quality_route.py        (new)
ui/backend/tests/test_llm_coach.py                 (extend)
ui/backend/tests/test_ai_coach_route.py            (extend)
reports/codex_tool_reports/v61_122_r1_chain.md     (new)
```

Estimated LOC: ~700-900 (smaller than V120/V121 because no new frontend, no new dispatch route)
