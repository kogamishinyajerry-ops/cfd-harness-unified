---
decision_id: DEC-V61-152
title: N5.1 · Beginner report (5-section structured + markdown renderer + verdict rule engine)
status: Accepted
parent_dec: V61-151
phase: N5
notion_sync_status: pending
---

# DEC-V61-152 · N5.1 Beginner Report

## Status

**Accepted 2026-05-07** — V133 sub-DEC slim 6-field. Medium-risk per
N5 charter; Opus confidence high — pure read-only walk + markdown
templating + rule-based verdict, no mutation surface, no V132 entry.

## Decision

Land the 5-section structured beginner report end-to-end:

- `BeginnerReport` Pydantic schema with 5 typed sections
  (geometry / mesh / physics / solver / verdict)
- `build_beginner_report(case_dir)` walker that populates each
  section best-effort from disk
- `derive_verdict()` pure rule function emitting one of 5 verdict
  literals with short reason
- `render_beginner_report_markdown()` templating with
  `(not yet set)` placeholders for missing fields

## Wire shape

```python
VerdictLiteral = Literal[
    "ready_for_review",
    "has_open_issues",
    "physics_setup_incomplete",
    "mesh_setup_incomplete",
    "geometry_setup_incomplete",
]

class BeginnerReport(BaseModel):  # extra=forbid
    case_id: str
    geometry: GeometrySection
    mesh: MeshSection
    physics: PhysicsSection
    solver: SolverSection
    verdict: VerdictSection
    generated_at: str  # ISO 8601 UTC
```

Every section's data fields are Optional — builder fills what it
can, leaves None when state is absent.

## Verdict precedence (most-blocking first)

1. `geometry_setup_incomplete` — STL filename or bounding box missing
2. `mesh_setup_incomplete` — cell_count missing OR 0
3. `physics_setup_incomplete` — fluid name OR regime missing
4. `has_open_issues` — checkMesh failed OR derived solver missing
5. `ready_for_review` — all sections populated, no blocking issues

The "ready_for_review" verdict explicitly tolerates checkMesh
unavailability (graceful degrade path); only an explicit
`checkmesh_ok=False` triggers `has_open_issues`.

## V130 / V132 enforcement

- Builder reads disk; no AI generation
- Verdict rule function returns dataclass; no LLM call
- Markdown renderer is pure string templating; no AI
- Test asserts no `llm_provider` / `llm_coach` imports in any of the
  3 modules (`builder`, `verdict_rules`, `markdown_renderer`)
- Test asserts none of the modules appear in
  `KNOWN_MUTATION_FUNCTIONS`

## Builder data sources

| Section | Source | Fallback |
|---|---|---|
| geometry.stl_filename | `constant/triSurface/*.stl` first match | None |
| geometry.bounding_box_* | parse `constant/polyMesh/points` | None |
| geometry.named_patches | parse `constant/polyMesh/boundary` | [] |
| mesh.* | reuse N2.4 `analyze_mesh_quality(run_checkmesh=False)` | None on parse error |
| physics.kinematic_viscosity | regex parse `constant/physicalProperties` | None |
| physics.regime | map `simulationType` + `RASModel` to RegimeKind | None |
| solver.derived_solver | call N3.4 `derive_solver()` with synthetic contracts | None on KeyError |
| solver.tolerance_tier | call N3.5 `derive_tolerance_for_regime()` | None |
| verdict | rule engine on populated sections | always populated |

## Markdown renderer

Fixed 5-section template:

```
# Case Report — `<case_id>`
_Generated <iso_ts>_

---

## 1. Geometry
- **STL file:** ...
- **Bounding box (min):** ...
- ...

## 2. Mesh
- **Cells:** ...
- **checkMesh:** ✓/✗/skipped

## 3. Physics
- **Fluid:** ...
- **Energy equation:** yes/no

## 4. Solver
- **Derived solver:** `simpleFoam`
- **Tolerance tier:** `engineering`

## 5. Verdict
**✓ READY FOR REVIEW** — Geometry, mesh, physics, and solver setup
all populated; no blocking issues detected by rule engine.
```

Verdict badges:
- `ready_for_review` → `✓ READY FOR REVIEW`
- `has_open_issues` → `⚠ OPEN ISSUES`
- `physics_setup_incomplete` → `✗ PHYSICS INCOMPLETE`
- `mesh_setup_incomplete` → `✗ MESH INCOMPLETE`
- `geometry_setup_incomplete` → `✗ GEOMETRY INCOMPLETE`

## Files touched

Backend (NEW):
- `ui/backend/schemas/beginner_report.py` — schemas
- `ui/backend/services/case_report/__init__.py`
- `ui/backend/services/case_report/builder.py` — disk walker
- `ui/backend/services/case_report/verdict_rules.py` — rule function
- `ui/backend/services/case_report/markdown_renderer.py` — templating

Tests (NEW):
- `ui/backend/tests/test_beginner_report.py` (28 cases — schema
  validators, verdict precedence 5 conditions including ready-when-
  checkmesh-unavailable, builder on empty/partial/full case fixtures,
  RANS-kOmegaSST physics → simpleFoam derivation, markdown renderer
  emits all 5 section headers + verdict badges + (not yet set)
  placeholders, V130 advisory-only contract enforced via 2 test
  invariants — no LLM imports + not in KNOWN_MUTATION_FUNCTIONS)

## Verification

- 28 N5.1 tests green
- 14 V132 contract tests still green (no regression)
- Builder is robust: missing case dir → all-None sections + verdict
- Builder accepts partial case state without crashing
- Verdict precedence pinned by 11 dedicated tests

## Out of scope (future sub-DECs)

- PDF rendering (markdown-first per charter §risk-register row 1) —
  N5-extend or downstream
- Honest issue list (N5.2) consumes the same case-state walker but
  emits a complementary view (red flags vs verdict)
- Audit package V2 manifest provenance — N5.3
- Frontend Step 5 report viewer panel — UI integration post-N5
- Report localization (zh / en) — defer
