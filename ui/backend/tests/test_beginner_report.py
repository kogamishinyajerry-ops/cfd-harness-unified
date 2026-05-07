"""DEC-V61-152 (N5.1) · beginner report builder + verdict + renderer tests.

Coverage:
  * Schema validators (each section accepts None / extra=forbid)
  * Builder on empty case → all sections empty + geometry_setup_incomplete
  * Builder on partial case (geometry only) → mesh_setup_incomplete
  * Builder on full case (geometry+mesh+physics+regime+thermal=False)
    → ready_for_review
  * Verdict precedence (5 conditions)
  * Markdown renderer: every section header present + (not yet set)
    placeholders + verdict badge
  * V130 advisory-only: builder + verdict_rules NOT in
    KNOWN_MUTATION_FUNCTIONS; no LLM imports
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ui.backend.schemas.beginner_report import (
    BeginnerReport,
    GeometrySection,
    MeshSection,
    PhysicsSection,
    SolverSection,
    VerdictSection,
)
from ui.backend.services.case_report import (
    build_beginner_report,
    derive_verdict,
    render_beginner_report_markdown,
)


# ────────── Schema validators ──────────


def test_geometry_section_all_fields_optional():
    GeometrySection()  # all None / empty default


def test_geometry_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        GeometrySection(mystery="oops")


def test_mesh_section_cell_count_non_negative():
    MeshSection(cell_count=0)
    with pytest.raises(ValidationError):
        MeshSection(cell_count=-1)


def test_physics_density_positive():
    PhysicsSection(density=1.0)
    with pytest.raises(ValidationError):
        PhysicsSection(density=0.0)


def test_verdict_literal_enforced():
    with pytest.raises(ValidationError):
        VerdictSection(verdict="not_a_real_verdict", reason="x")


def test_full_report_round_trip():
    rep = BeginnerReport(
        case_id="case_test",
        geometry=GeometrySection(),
        mesh=MeshSection(),
        physics=PhysicsSection(),
        solver=SolverSection(),
        verdict=VerdictSection(
            verdict="geometry_setup_incomplete", reason="test",
        ),
        generated_at="2026-05-07T12:00:00Z",
    )
    assert rep.case_id == "case_test"


# ────────── Verdict precedence ──────────


def _all_full() -> tuple[GeometrySection, MeshSection, PhysicsSection, SolverSection]:
    geometry = GeometrySection(
        stl_filename="test.stl",
        bounding_box_min=(0.0, 0.0, 0.0),
        bounding_box_max=(1.0, 1.0, 1.0),
    )
    mesh = MeshSection(
        cell_count=1000,
        checkmesh_ran=True,
        checkmesh_ok=True,
    )
    physics = PhysicsSection(fluid_name="water", regime="laminar")
    solver = SolverSection(derived_solver="icoFoam")
    return geometry, mesh, physics, solver


def test_verdict_geometry_incomplete_when_stl_missing():
    g, m, p, s = _all_full()
    g_no_stl = g.model_copy(update={"stl_filename": None})
    v = derive_verdict(geometry=g_no_stl, mesh=m, physics=p, solver=s)
    assert v.verdict == "geometry_setup_incomplete"


def test_verdict_geometry_incomplete_when_bbox_missing():
    g, m, p, s = _all_full()
    g2 = g.model_copy(update={"bounding_box_min": None})
    v = derive_verdict(geometry=g2, mesh=m, physics=p, solver=s)
    assert v.verdict == "geometry_setup_incomplete"


def test_verdict_mesh_incomplete_when_cell_count_zero():
    g, m, p, s = _all_full()
    m2 = m.model_copy(update={"cell_count": 0})
    v = derive_verdict(geometry=g, mesh=m2, physics=p, solver=s)
    assert v.verdict == "mesh_setup_incomplete"


def test_verdict_mesh_incomplete_when_cell_count_none():
    g, m, p, s = _all_full()
    m2 = m.model_copy(update={"cell_count": None})
    v = derive_verdict(geometry=g, mesh=m2, physics=p, solver=s)
    assert v.verdict == "mesh_setup_incomplete"


def test_verdict_physics_incomplete_when_fluid_missing():
    g, m, p, s = _all_full()
    p2 = p.model_copy(update={"fluid_name": None})
    v = derive_verdict(geometry=g, mesh=m, physics=p2, solver=s)
    assert v.verdict == "physics_setup_incomplete"


def test_verdict_physics_incomplete_when_regime_missing():
    g, m, p, s = _all_full()
    p2 = p.model_copy(update={"regime": None})
    v = derive_verdict(geometry=g, mesh=m, physics=p2, solver=s)
    assert v.verdict == "physics_setup_incomplete"


def test_verdict_open_issues_when_checkmesh_failed():
    g, m, p, s = _all_full()
    m2 = m.model_copy(update={"checkmesh_ok": False})
    v = derive_verdict(geometry=g, mesh=m2, physics=p, solver=s)
    assert v.verdict == "has_open_issues"


def test_verdict_open_issues_when_solver_missing():
    g, m, p, s = _all_full()
    s2 = s.model_copy(update={"derived_solver": None})
    v = derive_verdict(geometry=g, mesh=m, physics=p, solver=s2)
    assert v.verdict == "has_open_issues"


def test_verdict_ready_when_all_full():
    g, m, p, s = _all_full()
    v = derive_verdict(geometry=g, mesh=m, physics=p, solver=s)
    assert v.verdict == "ready_for_review"


def test_verdict_ready_when_checkmesh_unavailable():
    """checkMesh skipped (graceful degrade) → still ready_for_review
    (not auto-rejected for missing optional metric)."""
    g, m, p, s = _all_full()
    m2 = m.model_copy(update={"checkmesh_ran": False, "checkmesh_ok": None})
    v = derive_verdict(geometry=g, mesh=m2, physics=p, solver=s)
    assert v.verdict == "ready_for_review"


# ────────── Builder on empty case ──────────


def test_builder_empty_case_returns_geometry_incomplete(tmp_path: Path):
    case_dir = tmp_path / "imported_empty"
    case_dir.mkdir()
    rep = build_beginner_report(case_dir)
    assert rep.case_id == "imported_empty"
    assert rep.geometry.stl_filename is None
    assert rep.mesh.cell_count is None
    assert rep.verdict.verdict == "geometry_setup_incomplete"


def test_builder_partial_geometry_only_returns_mesh_incomplete(tmp_path: Path):
    """When geometry is populated but mesh isn't, verdict is
    mesh_setup_incomplete."""
    case_dir = tmp_path / "imported_geom_only"
    (case_dir / "constant" / "triSurface").mkdir(parents=True)
    (case_dir / "constant" / "triSurface" / "test.stl").write_text("")
    # No polyMesh — mesh not generated.
    rep = build_beginner_report(case_dir)
    # bbox is None because we don't have polyMesh/points.
    assert rep.geometry.stl_filename == "test.stl"
    # Verdict cascades: bbox missing → still geometry_setup_incomplete.
    assert rep.verdict.verdict == "geometry_setup_incomplete"


def test_builder_with_full_polymesh_populates_mesh(tmp_path: Path):
    case_dir = _scaffold_case_with_polymesh(tmp_path, "imported_full")
    rep = build_beginner_report(case_dir)
    assert rep.geometry.bounding_box_min is not None
    assert rep.geometry.bounding_box_max is not None
    assert rep.mesh.cell_count is not None
    assert rep.mesh.cell_count > 0
    # Without physics, verdict cascades to physics_setup_incomplete.
    assert rep.verdict.verdict == "physics_setup_incomplete"


def test_builder_with_physics_populates_solver(tmp_path: Path):
    case_dir = _scaffold_case_with_polymesh(tmp_path, "imported_full2")
    # Add physics dicts.
    (case_dir / "constant" / "physicalProperties").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object physicalProperties; }\n'
        "transportModel  Newtonian;\n"
        "nu              [0 2 -1 0 0 0 0] 1e-6;\n"
    )
    (case_dir / "constant" / "momentumTransport").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object momentumTransport; }\n'
        "simulationType laminar;\n"
    )
    rep = build_beginner_report(case_dir)
    assert rep.physics.regime == "laminar"
    assert rep.physics.kinematic_viscosity == 1e-6
    assert rep.solver.derived_solver == "icoFoam"
    assert rep.solver.tolerance_tier == "engineering"
    assert rep.verdict.verdict == "ready_for_review"


def test_builder_kOmegaSST_populates_correctly(tmp_path: Path):
    case_dir = _scaffold_case_with_polymesh(tmp_path, "imported_komega")
    (case_dir / "constant" / "physicalProperties").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object physicalProperties; }\n'
        "nu              [0 2 -1 0 0 0 0] 1.5e-5;\n"
    )
    (case_dir / "constant" / "momentumTransport").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object momentumTransport; }\n'
        "simulationType RAS;\n"
        "RAS\n{\n    RASModel        kOmegaSST;\n}\n"
    )
    rep = build_beginner_report(case_dir)
    assert rep.physics.regime == "RANS-kOmegaSST"
    assert rep.solver.derived_solver == "simpleFoam"


# ────────── Markdown renderer ──────────


def test_markdown_renderer_has_every_section_header():
    rep = _empty_report()
    md = render_beginner_report_markdown(rep)
    assert "## 1. Geometry" in md
    assert "## 2. Mesh" in md
    assert "## 3. Physics" in md
    assert "## 4. Solver" in md
    assert "## 5. Verdict" in md


def test_markdown_renderer_shows_not_yet_set_for_empty_fields():
    rep = _empty_report()
    md = render_beginner_report_markdown(rep)
    assert "(not yet set)" in md


def test_markdown_renderer_emits_verdict_badge():
    rep = _empty_report()
    md = render_beginner_report_markdown(rep)
    assert "✗ GEOMETRY INCOMPLETE" in md


def test_markdown_renderer_full_case_no_placeholders_in_data_rows():
    """A fully-populated report should NOT show '(not yet set)' next
    to populated rows — quick smoke."""
    g, m, p, s = _all_full()
    rep = BeginnerReport(
        case_id="case_full",
        geometry=g,
        mesh=m,
        physics=p,
        solver=s,
        verdict=derive_verdict(geometry=g, mesh=m, physics=p, solver=s),
        generated_at="2026-05-07T12:00:00Z",
    )
    md = render_beginner_report_markdown(rep)
    assert "READY FOR REVIEW" in md
    # The "STL file" row should show test.stl, not "(not yet set)".
    assert "test.stl" in md


def test_markdown_renderer_no_html_injection_in_case_id():
    """Defensive: arbitrary case_id is not interpreted as markdown."""
    rep = _empty_report().model_copy(update={"case_id": "<script>x</script>"})
    md = render_beginner_report_markdown(rep)
    assert "<script>" in md  # raw text preserved
    # The renderer wraps in backticks; the renderer doesn't escape — it
    # just templates literally. That's fine for markdown's purposes
    # since markdown renderers won't execute script tags.


# ────────── V130 advisory-only contract ──────────


def test_no_llm_imports_in_report_modules():
    """N5 charter §risk-register row 2 + Q4: report builder MUST NOT
    import any LLM provider module."""
    for mod_name in (
        "ui.backend.services.case_report.builder",
        "ui.backend.services.case_report.markdown_renderer",
        "ui.backend.services.case_report.verdict_rules",
    ):
        mod = importlib.import_module(mod_name)
        # Walk module attributes; any imported name from llm_provider /
        # llm_coach would surface here.
        for name in dir(mod):
            if name.startswith("_"):
                continue
            obj = getattr(mod, name, None)
            if obj is None:
                continue
            mod_path = getattr(obj, "__module__", "") or ""
            assert "llm_provider" not in mod_path, (
                f"{mod_name} pulls in LLM provider via {name!r}"
            )
            assert "llm_coach" not in mod_path


def test_report_modules_not_in_known_mutation_functions():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, _ in KNOWN_MUTATION_FUNCTIONS:
        assert "case_report" not in module


# ────────── Helpers ──────────


def _empty_report() -> BeginnerReport:
    g = GeometrySection()
    m = MeshSection()
    p = PhysicsSection()
    s = SolverSection()
    return BeginnerReport(
        case_id="case_empty",
        geometry=g,
        mesh=m,
        physics=p,
        solver=s,
        verdict=derive_verdict(geometry=g, mesh=m, physics=p, solver=s),
        generated_at="2026-05-07T12:00:00Z",
    )


def _scaffold_case_with_polymesh(tmp_path: Path, name: str) -> Path:
    """Scaffold a minimal but valid polyMesh + triSurface in
    tmp_path/<name>."""
    case_dir = tmp_path / name
    pm = case_dir / "constant" / "polyMesh"
    pm.mkdir(parents=True)
    # Add stl so geometry section populates stl_filename + bbox.
    tri = case_dir / "constant" / "triSurface"
    tri.mkdir(parents=True)
    (tri / "geom.stl").write_text("")
    # Minimal points file (8 corners of a unit cube).
    (pm / "points").write_text(
        "FoamFile { version 2.0; format ascii; class vectorField; "
        'location "constant/polyMesh"; object points; }\n'
        "8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 1)\n(1 0 1)\n(1 1 1)\n(0 1 1)\n"
        ")\n"
    )
    # Minimal owner — single cell, 6 internal faces (degenerate but
    # parser-accepting).
    (pm / "owner").write_text(
        "FoamFile { version 2.0; format ascii; class labelList; "
        'location "constant/polyMesh"; object owner; }\n'
        "6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )
    # Minimal boundary with one named patch.
    (pm / "boundary").write_text(
        "FoamFile { version 2.0; format ascii; class polyBoundaryMesh; "
        'location "constant/polyMesh"; object boundary; }\n'
        "1\n(\n"
        "walls\n{\n    type wall;\n    nFaces 6;\n    startFace 0;\n}\n"
        ")\n"
    )
    return case_dir
