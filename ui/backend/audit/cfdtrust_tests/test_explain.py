"""M10 — Template-based AI advisor (`cfdtrust explain`) tests.

Verifies the advisor:
  - reads trust_report.json + case_manifest.yaml WITHOUT modifying them;
  - renders Markdown with the canonical sections (Header / TL;DR /
    Per-gate / Honesty / Next action);
  - generates rule-based recommendations from gate details (no LLM);
  - honors the AI advisor rules from CLAUDE.md (no silently changing
    FAIL to PASS, no claim to validation when gates FAIL);
  - handles every gate status (PASS / FAIL / BLOCKED / MOCKED).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from cfdtrust.cli_explain import explain, cmd_explain


# ---------- fixture helpers ----------


def _write_case(tmp_path: Path, report: Dict[str, Any], manifest: Dict[str, Any] | None = None) -> Path:
    """Write a minimal case dir with trust_report.json + case_manifest.yaml."""
    case = tmp_path / "case"
    (case / "artifacts").mkdir(parents=True)
    (case / "artifacts" / "trust_report.json").write_text(json.dumps(report, indent=2))
    (case / "case_manifest.yaml").write_text(
        yaml.safe_dump(manifest or {"case_id": report.get("case_id", "test")})
    )
    return case


def _pass_report() -> Dict[str, Any]:
    """A canonical fully-passing trust report."""
    return {
        "case_id": "happy_case",
        "generated_at": "2026-05-21T00:00:00Z",
        "overall_status": "PASS",
        "solver_execution": "real",
        "validation_status": "validated",
        "gates": {
            "geometry_contract": {
                "status": "PASS",
                "summary": "presence PASS (5/5); dimensionality PASS.",
                "details": {"realized_patch_count": 5},
            },
            "mesh_contract": {
                "status": "PASS",
                "summary": "quality PASS; y+ PASS.",
                "details": {},
            },
            "bc_contract": {
                "status": "PASS",
                "summary": "all 4 dims PASS.",
                "details": {
                    "type_match": {"checked_count": 9},
                    "value_match": {"matched_count": 4},
                    "derived_consistency": {"matched_count": 2},
                },
            },
            "solver_execution": {
                "status": "PASS",
                "summary": "converged at iter 159.",
                "details": {"final_iter": 159},
            },
            "qoi_extraction": {"status": "PASS", "summary": "Cf extracted"},
            "reference_comparison": {"status": "PASS", "summary": "max error 3%"},
        },
        "limitations": [],
    }


def _fail_mesh_yplus_report() -> Dict[str, Any]:
    """Canonical BFS-style FAIL: mesh y+ overshoot."""
    r = _pass_report()
    r["case_id"] = "yplus_overshoot_case"
    r["overall_status"] = "FAIL"
    r["validation_status"] = "not_validated"
    r["gates"]["mesh_contract"] = {
        "status": "FAIL",
        "summary": "quality PASS; y+ FAIL (bottomWall avg=20.77 outside [0.5, 5.0]).",
        "details": {
            "quality_dimension": {"dimension_status": "PASS"},
            "y_plus_dimension": {
                "dimension_status": "FAIL",
                "patch_evaluated": "bottomWall",
                "actual_avg": 20.77,
                "target_min": 0.5,
                "target_max": 5.0,
            },
        },
    }
    r["limitations"] = ["mesh_contract FAIL; not validated."]
    return r


# ---------- output structure ----------


def test_explain_renders_canonical_sections(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    md = explain(case)
    for section in (
        "# Trust Report Explanation",
        "## TL;DR",
        "## Per-gate breakdown",
        "## Next best action",
    ):
        assert section in md, f"missing section: {section}"


def test_explain_renders_all_six_gates(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    md = explain(case)
    for gate_name in (
        "geometry_contract", "mesh_contract", "bc_contract",
        "solver_execution", "qoi_extraction", "reference_comparison",
    ):
        assert f"`{gate_name}`" in md, f"gate {gate_name} not rendered"


def test_explain_includes_case_id_in_header(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    md = explain(case)
    assert "happy_case" in md.split("## TL;DR")[0]


def test_explain_writes_to_file_when_out_given(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    out = tmp_path / "expl.md"
    rc = cmd_explain(str(case), out=str(out))
    assert rc == 0
    assert out.exists()
    assert "# Trust Report Explanation" in out.read_text()


def test_explain_fails_when_no_trust_report(tmp_path: Path):
    case = tmp_path / "no_report"
    case.mkdir()
    (case / "case_manifest.yaml").write_text("case_id: x")
    rc = cmd_explain(str(case))
    assert rc == 1   # FileNotFoundError surfaces as exit 1


# ---------- TL;DR tone ----------


def test_tldr_for_pass_claims_validated(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    md = explain(case)
    tldr = md.split("## TL;DR")[1].split("## Per-gate")[0]
    assert "validated" in tldr.lower() or "passed" in tldr.lower()


def test_tldr_for_fail_does_not_claim_validation(tmp_path: Path):
    """HONESTY FENCE: the AI advisor must NOT call a FAIL run 'validated'."""
    case = _write_case(tmp_path, _fail_mesh_yplus_report())
    md = explain(case)
    tldr = md.split("## TL;DR")[1].split("## Per-gate")[0]
    assert "validated" not in tldr.lower() or "not validated" in tldr.lower() or "NOT claim" in tldr or "did NOT" in tldr
    # Specifically: the advisor names the failing gate
    assert "mesh_contract" in md


def test_tldr_for_mocked_explicit(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "MOCKED"
    r["solver_execution"] = "mocked"
    r["validation_status"] = "not_validated"
    case = _write_case(tmp_path, r)
    md = explain(case)
    tldr = md.split("## TL;DR")[1].split("## Per-gate")[0]
    assert "mocked" in tldr.lower()
    assert "not a validation result" in tldr.lower() or "not constitute validation" in tldr.lower() or "no real cfd was executed" in tldr.lower()


# ---------- per-gate recommendations ----------


def test_mesh_yplus_overshoot_recommends_refine_wall_mesh(tmp_path: Path):
    case = _write_case(tmp_path, _fail_mesh_yplus_report())
    md = explain(case)
    mesh_section = md.split("`mesh_contract`")[1].split("`bc_contract`")[0]
    # Rule-based: y+ ratio computed and surfaced (~4.2× target max)
    assert "Refine" in mesh_section or "refine" in mesh_section
    assert "first-cell" in mesh_section.lower() or "wall" in mesh_section.lower()


def test_mesh_yplus_below_target_recommends_coarsen(tmp_path: Path):
    """If realized y+ is BELOW the target minimum (over-resolved wall),
    advisor recommends coarsening, not refining."""
    r = _fail_mesh_yplus_report()
    r["gates"]["mesh_contract"]["details"]["y_plus_dimension"] = {
        "dimension_status": "FAIL",
        "patch_evaluated": "wall",
        "actual_avg": 0.05,    # well below min=0.5
        "target_min": 0.5,
        "target_max": 5.0,
    }
    case = _write_case(tmp_path, r)
    md = explain(case)
    mesh_section = md.split("`mesh_contract`")[1].split("`bc_contract`")[0]
    assert "coarsen" in mesh_section.lower() or "too fine" in mesh_section.lower() or "over-resolved" in mesh_section.lower()


def test_geometry_missing_patch_recommends_blockmesh_edit(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "FAIL"
    r["gates"]["geometry_contract"] = {
        "status": "FAIL",
        "summary": "presence FAIL (missing: ['stepFace'])",
        "details": {
            "presence_dimension": {
                "dimension_status": "FAIL",
                "missing": ["stepFace"],
            },
        },
    }
    case = _write_case(tmp_path, r)
    md = explain(case)
    geom = md.split("`geometry_contract`")[1].split("`mesh_contract`")[0]
    assert "blockMeshDict" in geom or "blockMesh" in geom
    assert "stepFace" in geom


def test_bc_value_mismatch_surfaces_concrete_example(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "FAIL"
    r["gates"]["bc_contract"] = {
        "status": "FAIL",
        "summary": "value_match FAIL (mismatches=1)",
        "details": {
            "file_presence": {"dimension_status": "PASS"},
            "patch_coverage": {"dimension_status": "PASS"},
            "type_match": {"dimension_status": "PASS", "checked_count": 9},
            "value_match": {
                "dimension_status": "FAIL",
                "value_mismatches": [{
                    "manifest_key": "inlet",
                    "field_class": "velocity",
                    "numeric_field": "magnitude_m_s",
                    "field": "U",
                    "resolved_patch": "inlet",
                    "declared": 44.2,
                    "actual": 30.0,
                }],
                "value_missing": [],
            },
            "derived_consistency": {"dimension_status": "PASS"},
        },
    }
    case = _write_case(tmp_path, r)
    md = explain(case)
    bc = md.split("`bc_contract`")[1].split("`solver_execution`")[0]
    assert "44.2" in bc and "30.0" in bc
    assert "manifest" in bc.lower() or "0/<field>" in bc.lower()


def test_solver_residual_stall_explains_failed_field(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "FAIL"
    r["gates"]["solver_execution"] = {
        "status": "FAIL",
        "summary": "simpleFoam ran 2000/2000 iters; 1/5 field(s) did not reach residual target.",
        "details": {
            "reason": "residual_targets_not_met",
            "final_iter": 2000,
            "max_iter": 2000,
            "failed_fields": [{
                "field": "p",
                "final_residual": 3.16e-5,
                "target": 1e-5,
            }],
        },
    }
    case = _write_case(tmp_path, r)
    md = explain(case)
    solver = md.split("`solver_execution`")[1].split("`qoi_extraction`")[0]
    assert "`p`" in solver or "field" in solver.lower()
    assert "max_iterations" in solver or "residual" in solver.lower()


# ---------- honesty fences ----------


def test_explain_does_not_modify_trust_report(tmp_path: Path):
    """AI advisor MUST NOT write to trust_report.json — that's the
    explicit honesty rule in CLAUDE.md."""
    report = _fail_mesh_yplus_report()
    case = _write_case(tmp_path, report)
    report_path = case / "artifacts" / "trust_report.json"
    original_bytes = report_path.read_bytes()
    original_mtime = report_path.stat().st_mtime_ns

    explain(case)

    assert report_path.read_bytes() == original_bytes
    # Permissions / mtime should also be unchanged (no touch)
    assert report_path.stat().st_mtime_ns == original_mtime


def test_explain_does_not_modify_manifest(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    manifest_path = case / "case_manifest.yaml"
    original = manifest_path.read_bytes()
    explain(case)
    assert manifest_path.read_bytes() == original


def test_explain_renders_limitations_verbatim(tmp_path: Path):
    """Honesty disclosures from trust_report MUST appear in the
    explanation. The advisor cannot 'soften' or omit them."""
    r = _fail_mesh_yplus_report()
    r["limitations"] = [
        "No real CFD solver was executed. This run does not constitute validation.",
        "mesh_contract FAILed on y+ overshoot.",
    ]
    case = _write_case(tmp_path, r)
    md = explain(case)
    for lim in r["limitations"]:
        assert lim in md, f"limitation dropped: {lim!r}"


def test_explain_fail_status_never_appears_as_pass(tmp_path: Path):
    """Belt-side fence: scan rendered Markdown to ensure no FAIL gate is
    reframed as PASS anywhere in its block."""
    r = _fail_mesh_yplus_report()
    case = _write_case(tmp_path, r)
    md = explain(case)
    # mesh_contract is FAILed; its section header must not say PASS.
    mesh_section = md.split("`mesh_contract`")[1].split("`bc_contract`")[0]
    header_line = mesh_section.split("\n")[0]
    assert "PASS" not in header_line
    assert "FAIL" in header_line


def test_explain_next_action_for_fail_points_to_blocker(tmp_path: Path):
    r = _fail_mesh_yplus_report()
    case = _write_case(tmp_path, r)
    md = explain(case)
    nba = md.split("## Next best action")[1]
    # The first blocker in render order is mesh_contract (geometry is PASS).
    assert "mesh_contract" in nba


def test_explain_next_action_for_pass_suggests_regression_suite(tmp_path: Path):
    case = _write_case(tmp_path, _pass_report())
    md = explain(case)
    nba = md.split("## Next best action")[1]
    assert "regression" in nba.lower() or "future" in nba.lower()


# ---------- mocked / blocked paths ----------


def test_explain_mocked_solver_says_no_real_cfd(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "MOCKED"
    r["solver_execution"] = "mocked"
    r["gates"]["geometry_contract"]["status"] = "MOCKED"
    r["gates"]["solver_execution"]["status"] = "MOCKED"
    case = _write_case(tmp_path, r)
    md = explain(case)
    # The mocked solver gate must explain itself as a synthetic placeholder.
    solver = md.split("`solver_execution`")[1].split("`qoi_extraction`")[0]
    assert "synthetic" in solver.lower() or "placeholder" in solver.lower() or "no real" in solver.lower()


def test_explain_blocked_gate_recommends_running(tmp_path: Path):
    r = _pass_report()
    r["overall_status"] = "BLOCKED"
    r["gates"]["geometry_contract"] = {
        "status": "BLOCKED",
        "summary": "no geometry evidence",
        "details": {"reason": "geometry_quality_json_missing"},
    }
    case = _write_case(tmp_path, r)
    md = explain(case)
    geom = md.split("`geometry_contract`")[1].split("`mesh_contract`")[0]
    assert "Run" in geom or "cfdtrust run" in geom
