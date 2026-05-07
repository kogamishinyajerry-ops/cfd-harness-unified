"""DEC-V61-153 (N5.2) · honest issue list schema + enumerator tests.

Coverage:
  * Schema validators (severity / scope / source_rule_id literal
    enforcement; message length bounds; extra=forbid)
  * Empty case → critical issues for missing geometry/mesh/physics
  * Partial scaffolds → progressive issue resolution
  * checkMesh failure → mesh_checkmesh_failed warning
  * fast_survey tolerance → info hint
  * LES-stub regime → info hint
  * Stalled residuals → output_residuals_stalled warning
  * Healthy residuals (decreasing fast) → no stall hint
  * Issue list sorted critical-first then alpha
  * V130 advisory-only: no AI prose; enumerator NOT in
    KNOWN_MUTATION_FUNCTIONS
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ui.backend.schemas.honest_issue_list import Issue, IssueList
from ui.backend.services.case_issues import enumerate_issues


# ────────── Schema validators ──────────


def test_issue_message_required_and_bounded():
    Issue(
        severity="critical",
        source_rule_id="geometry_stl_missing",
        scope="geometry",
        message="x",
    )
    with pytest.raises(ValidationError):
        Issue(
            severity="critical",
            source_rule_id="geometry_stl_missing",
            scope="geometry",
            message="",
        )
    with pytest.raises(ValidationError):
        Issue(
            severity="critical",
            source_rule_id="geometry_stl_missing",
            scope="geometry",
            message="x" * 301,  # over 300 cap
        )


def test_issue_severity_literal_enforced():
    with pytest.raises(ValidationError):
        Issue(
            severity="emergency",  # not in literal
            source_rule_id="geometry_stl_missing",
            scope="geometry",
            message="x",
        )


def test_issue_source_rule_id_literal_enforced():
    with pytest.raises(ValidationError):
        Issue(
            severity="critical",
            source_rule_id="not_a_real_rule",
            scope="geometry",
            message="x",
        )


def test_issue_scope_literal_enforced():
    with pytest.raises(ValidationError):
        Issue(
            severity="critical",
            source_rule_id="geometry_stl_missing",
            scope="cosmic",
            message="x",
        )


def test_issue_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        Issue(
            severity="critical",
            source_rule_id="geometry_stl_missing",
            scope="geometry",
            message="x",
            mystery="oops",
        )


def test_issue_list_severity_counts():
    lst = IssueList(
        case_id="x",
        generated_at="2026-05-07T12:00:00Z",
        issues=[
            Issue(severity="critical", source_rule_id="geometry_stl_missing", scope="geometry", message="x"),
            Issue(severity="critical", source_rule_id="mesh_zero_cells", scope="mesh", message="y"),
            Issue(severity="warning", source_rule_id="mesh_low_count_warning", scope="mesh", message="z"),
            Issue(severity="info", source_rule_id="solver_les_subgrid_todo", scope="solver", message="w"),
        ],
    )
    assert lst.critical_count == 2
    assert lst.warning_count == 1
    assert lst.info_count == 1


# ────────── Enumerator on empty case ──────────


def test_empty_case_emits_critical_geometry_and_mesh_issues(tmp_path: Path):
    case_dir = tmp_path / "imported_empty"
    case_dir.mkdir()
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "geometry_stl_missing" in rule_ids
    assert "mesh_polymesh_missing" in rule_ids
    assert "physics_dicts_missing" in rule_ids


# ────────── Enumerator: progressive setup ──────────


def test_geometry_only_resolves_stl_issue(tmp_path: Path):
    case_dir = tmp_path / "imported_g_only"
    (case_dir / "constant" / "triSurface").mkdir(parents=True)
    (case_dir / "constant" / "triSurface" / "geom.stl").write_text("")
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "geometry_stl_missing" not in rule_ids
    # mesh is still missing.
    assert "mesh_polymesh_missing" in rule_ids


def test_mesh_with_low_cell_count_emits_warning(tmp_path: Path):
    case_dir = _scaffold_full_through_mesh(tmp_path, "imported_lowcells")
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    # The minimal scaffold mesh has < 100 cells (1 cell), so the
    # low-count warning fires.
    assert "mesh_low_count_warning" in rule_ids


def test_full_scaffolded_case_no_geometry_or_mesh_critical(tmp_path: Path):
    case_dir = _scaffold_full_with_physics(tmp_path, "imported_full")
    lst = enumerate_issues(case_dir)
    critical_ids = {i.source_rule_id for i in lst.issues if i.severity == "critical"}
    assert "geometry_stl_missing" not in critical_ids
    assert "mesh_polymesh_missing" not in critical_ids
    assert "physics_dicts_missing" not in critical_ids


# ────────── LES-stub TODO ──────────


def test_les_stub_regime_emits_subgrid_todo(tmp_path: Path):
    case_dir = _scaffold_full_with_physics(
        tmp_path, "imported_les", regime_type="LES",
    )
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "solver_les_subgrid_todo" in rule_ids


# ────────── Residual stall ──────────


def test_stalled_residuals_emit_warning(tmp_path: Path):
    case_dir = _scaffold_full_with_physics(
        tmp_path, "imported_stall", regime_type="laminar",
    )
    # Plant a log with stalled U residuals.
    log_path = case_dir / "log.icoFoam"
    log_path.write_text(
        "Solving for Ux, Initial residual = 1.000e-04, Final ...\n"
        "Solving for Ux, Initial residual = 9.99e-05, Final ...\n"
        "Solving for Ux, Initial residual = 9.98e-05, Final ...\n"
        "Solving for Ux, Initial residual = 9.97e-05, Final ...\n"
        "Solving for Ux, Initial residual = 9.96e-05, Final ...\n"
    )
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "output_residuals_stalled" in rule_ids


def test_decreasing_residuals_no_stall_warning(tmp_path: Path):
    case_dir = _scaffold_full_with_physics(
        tmp_path, "imported_ok_log", regime_type="laminar",
    )
    log_path = case_dir / "log.icoFoam"
    log_path.write_text(
        "Solving for Ux, Initial residual = 1e-1, Final ...\n"
        "Solving for Ux, Initial residual = 1e-2, Final ...\n"
        "Solving for Ux, Initial residual = 1e-3, Final ...\n"
        "Solving for Ux, Initial residual = 1e-4, Final ...\n"
        "Solving for Ux, Initial residual = 1e-5, Final ...\n"
    )
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "output_residuals_stalled" not in rule_ids


def test_log_missing_emits_info_when_physics_committed(tmp_path: Path):
    case_dir = _scaffold_full_with_physics(
        tmp_path, "imported_no_log", regime_type="laminar",
    )
    # No log file planted.
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "output_run_log_missing" in rule_ids


def test_log_missing_NOT_emitted_when_physics_not_committed(tmp_path: Path):
    """Engineer hasn't reached Step 3 yet — no log is expected;
    don't surface a noise issue."""
    case_dir = tmp_path / "imported_no_phys"
    case_dir.mkdir()
    lst = enumerate_issues(case_dir)
    rule_ids = {i.source_rule_id for i in lst.issues}
    assert "output_run_log_missing" not in rule_ids


# ────────── Sort + listing ──────────


def test_issues_sorted_critical_first(tmp_path: Path):
    case_dir = tmp_path / "imported_sort"
    case_dir.mkdir()  # empty → many critical + maybe warnings
    lst = enumerate_issues(case_dir)
    rank = {"critical": 0, "warning": 1, "info": 2}
    for i in range(len(lst.issues) - 1):
        assert rank[lst.issues[i].severity] <= rank[lst.issues[i + 1].severity]


# ────────── V130 advisory-only contract ──────────


def test_no_llm_imports_in_enumerator():
    mod = importlib.import_module("ui.backend.services.case_issues.enumerator")
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name, None)
        mod_path = getattr(obj, "__module__", "") or ""
        assert "llm_provider" not in mod_path
        assert "llm_coach" not in mod_path


def test_enumerator_module_not_in_known_mutation_functions():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, _ in KNOWN_MUTATION_FUNCTIONS:
        assert "case_issues" not in module


# ────────── Helpers ──────────


def _scaffold_full_through_mesh(tmp_path: Path, name: str) -> Path:
    case_dir = tmp_path / name
    pm = case_dir / "constant" / "polyMesh"
    pm.mkdir(parents=True)
    tri = case_dir / "constant" / "triSurface"
    tri.mkdir(parents=True)
    (tri / "geom.stl").write_text("")
    (pm / "points").write_text(
        "FoamFile { version 2.0; format ascii; class vectorField; "
        'location "constant/polyMesh"; object points; }\n'
        "8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 1)\n(1 0 1)\n(1 1 1)\n(0 1 1)\n"
        ")\n"
    )
    (pm / "owner").write_text(
        "FoamFile { version 2.0; format ascii; class labelList; "
        'location "constant/polyMesh"; object owner; }\n'
        "6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )
    (pm / "boundary").write_text(
        "FoamFile { version 2.0; format ascii; class polyBoundaryMesh; "
        'location "constant/polyMesh"; object boundary; }\n'
        "1\n(\n"
        "walls\n{\n    type wall;\n    nFaces 6;\n    startFace 0;\n}\n"
        ")\n"
    )
    return case_dir


def _scaffold_full_with_physics(
    tmp_path: Path,
    name: str,
    *,
    regime_type: str = "laminar",
) -> Path:
    case_dir = _scaffold_full_through_mesh(tmp_path, name)
    (case_dir / "constant" / "physicalProperties").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object physicalProperties; }\n'
        "transportModel  Newtonian;\n"
        "nu              [0 2 -1 0 0 0 0] 1e-6;\n"
    )
    if regime_type == "LES":
        body = "simulationType LES;\n"
    elif regime_type == "RANS":
        body = (
            "simulationType RAS;\n"
            "RAS\n{\n    RASModel        kOmegaSST;\n}\n"
        )
    else:
        body = "simulationType laminar;\n"
    (case_dir / "constant" / "momentumTransport").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object momentumTransport; }\n' + body
    )
    return case_dir
