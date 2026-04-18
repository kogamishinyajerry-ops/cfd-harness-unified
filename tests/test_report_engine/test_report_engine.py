from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from report_engine import ReportDataCollector, ReportGenerator
from report_engine.data_collector import REPORTS_ROOT


def _template_env(repo_root: Path) -> Environment:
    return Environment(loader=FileSystemLoader(str(repo_root / "templates")))


def test_case_summary_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/case_summary.md.j2")
    rendered = template.render(
        case_id="lid_driven_cavity_benchmark",
        case_meta={
            "name": "Lid-Driven Cavity",
            "description": "Ghia et al. 1982",
            "solver": "icoFoam",
            "turbulence_model": "laminar",
            "mesh_strategy": "[DATA MISSING]",
            "key_parameters": {"Re": 100},
            "meta_source": "[DATA MISSING]",
        },
    )
    assert "## Case Summary" in rendered
    assert "icoFoam" in rendered
    assert "Re" in rendered


def test_gold_standard_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/gold_standard_ref.md.j2")
    rendered = template.render(
        gold_standard={
            "source": "Ghia et al. 1982",
            "literature_doi": "10.0/example",
            "observables": [{"name": "u_centerline", "ref_value": 1.0, "tolerance": {"mode": "relative", "value": 0.05}}],
        },
        format_value=lambda value: value,
    )
    assert "Gold Standard Reference" in rendered
    assert "10.0/example" in rendered
    assert "u_centerline" in rendered


def test_results_comparison_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/results_comparison.md.j2")
    rendered = template.render(
        match_rate=1.0,
        auto_verify_report={
            "gold_standard_comparison": {
                "overall": "PASS",
                "observables": [
                    {"name": "drag", "ref_value": 1.0, "sim_value": 1.05, "within_tolerance": True},
                ],
            }
        },
        deviation_direction=lambda ref, sim: "Over",
        format_value=lambda value: value,
    )
    assert "Results vs Reference" in rendered
    assert "drag" in rendered
    assert "Over" in rendered


def test_attribution_partial_with_data(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/attribution.md.j2")
    rendered = template.render(
        attribution_report={"primary_cause": "mesh_resolution", "confidence": "MEDIUM", "suggested_correction": "Refine"},
        auto_verify_report={"verdict": "FAIL"},
    )
    assert "mesh_resolution" in rendered
    assert "Refine" in rendered


def test_attribution_partial_missing(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/attribution.md.j2")
    rendered = template.render(attribution_report=None, auto_verify_report={"verdict": "FAIL"})
    assert "Attribution report not yet generated" in rendered


def test_correction_spec_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/correction_spec.md.j2")
    rendered = template.render(
        auto_verify_report={"correction_spec_needed": True},
        correction_spec={"primary_cause": "mesh_resolution", "confidence": "LOW", "suggested_correction": "Refine"},
    )
    assert "suggest-only" in rendered
    assert "mesh_resolution" in rendered


def test_correction_spec_not_needed(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/correction_spec.md.j2")
    rendered = template.render(auto_verify_report={"correction_spec_needed": False}, correction_spec=None)
    assert "No deviation; CorrectionSpec not triggered." in rendered


def test_project_progress_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/project_progress.md.j2")
    rendered = template.render(project_progress={"done_cases": 3, "total_cases": 15, "progress_ratio": 0.2, "auto_verify_reports": 3})
    assert "3/15" in rendered
    assert "20.00%" in rendered


def test_verdict_partial(repo_root: Path):
    env = _template_env(repo_root)
    template = env.get_template("partials/verdict.md.j2")
    rendered = template.render(auto_verify_report={"verdict": "PASS", "convergence": {"status": "CONVERGED"}, "physics_check": {"status": "PASS"}})
    assert "## Verdict" in rendered
    assert "PASS" in rendered


def test_full_report_7_sections():
    result = ReportGenerator().render("lid_driven_cavity_benchmark")
    assert result.section_count == 7


def test_full_report_data_consistency():
    result = ReportGenerator().render("lid_driven_cavity_benchmark")
    report = (REPORTS_ROOT / "lid_driven_cavity_benchmark" / "auto_verify_report.yaml").read_text()
    assert "u_centerline" in result.markdown
    assert "PASS" in result.markdown
    assert "lid_driven_cavity_benchmark" in result.markdown
    assert report


def test_missing_auto_verify_raises(tmp_path: Path):
    from report_engine.data_collector import ReportDataCollector

    collector = ReportDataCollector()
    missing_case = "missing_case"
    with pytest.raises(ValueError):
        collector._load_auto_verify(missing_case)


def test_missing_case_meta_placeholder():
    context = ReportDataCollector().collect("lid_driven_cavity_benchmark")
    assert context.case_meta["meta_source"] == "[DATA MISSING]"
    assert context.case_meta["mesh_strategy"] == "[DATA MISSING]"


def test_e2e_lid_driven_cavity_report(tmp_path: Path):
    output = tmp_path / "lid.md"
    result = ReportGenerator().generate("lid_driven_cavity_benchmark", output_path=output)
    assert output.is_file()
    assert result.section_count == 7


def test_e2e_backward_facing_step_report(tmp_path: Path):
    output = tmp_path / "bfs.md"
    result = ReportGenerator().generate("backward_facing_step_steady", output_path=output)
    assert output.is_file()
    assert "Backward-Facing Step" in result.markdown


def test_e2e_cylinder_crossflow_report(tmp_path: Path):
    output = tmp_path / "cyl.md"
    result = ReportGenerator().generate("cylinder_crossflow", output_path=output)
    assert output.is_file()
    assert "Circular Cylinder Wake" in result.markdown


def test_idempotency(tmp_path: Path):
    generator = ReportGenerator()
    output_a = tmp_path / "a.md"
    output_b = tmp_path / "b.md"
    generator.generate("cylinder_crossflow", output_path=output_a)
    generator.generate("cylinder_crossflow", output_path=output_b)
    assert output_a.read_text() == output_b.read_text()


def test_bare_import_auto_verifier(run_subprocess):
    result = run_subprocess(["python3", "-c", "from auto_verifier import AutoVerifier; print(AutoVerifier.__name__)"])
    assert result.returncode == 0, result.stderr


def test_bare_import_report_engine(run_subprocess):
    result = run_subprocess(["python3", "-c", "from report_engine import ReportGenerator; print(ReportGenerator.__name__)"])
    assert result.returncode == 0, result.stderr


def test_report_contains_suggest_only_banner():
    result = ReportGenerator().render("lid_driven_cavity_benchmark")
    assert "suggest-only, not auto-applied" in result.markdown


def test_report_determinism_replay():
    generator = ReportGenerator()
    left = generator.render("backward_facing_step_steady").markdown
    right = generator.render("backward_facing_step_steady").markdown
    assert left == right


def test_out_of_scope_case_returns_noop(tmp_path: Path):
    output = tmp_path / "out.md"
    result = ReportGenerator().generate("of-99-future-case", output_path=output)
    assert result.status == "noop"
    assert result.reason is not None
    assert "out_of_scope" in result.reason
    assert result.section_count == 0
    assert result.markdown == ""
    assert result.output_path is None
    assert not output.exists()


def test_normalize_auto_verify_fills_defaults():
    collector = ReportDataCollector()
    report = collector._normalize_auto_verify({})
    assert report["gold_standard_comparison"]["overall"] == "SKIPPED"
    assert report["gold_standard_comparison"]["observables"] == []
    assert report["gold_standard_comparison"]["warnings"] == []
    assert report["convergence"]["status"] == "UNKNOWN"
    assert report["convergence"]["target_residual"] == 1e-5
    assert report["physics_check"]["status"] == "UNKNOWN"
    assert report["physics_check"]["warnings"] == []
    assert report["verdict"] == "UNKNOWN"
    assert report["correction_spec_needed"] is False


def test_normalize_auto_verify_preserves_existing():
    collector = ReportDataCollector()
    original = {
        "gold_standard_comparison": {"overall": "PASS", "observables": [{"name": "u"}]},
        "convergence": {"status": "CONVERGED", "final_residual": 1e-7},
        "verdict": "PASS",
    }
    report = collector._normalize_auto_verify(original)
    assert report["gold_standard_comparison"]["overall"] == "PASS"
    assert report["gold_standard_comparison"]["observables"] == [{"name": "u"}]
    assert report["convergence"]["final_residual"] == 1e-7
    assert report["verdict"] == "PASS"


def test_normalize_correction_spec_none():
    assert ReportDataCollector._normalize_correction_spec(None) is None


def test_normalize_correction_spec_resolution_fallback():
    spec = ReportDataCollector._normalize_correction_spec(
        {"resolution": "increase mesh density"}
    )
    assert spec["primary_cause"] == "unknown"
    assert spec["confidence"] == "LOW"
    assert spec["suggested_correction"] == "increase mesh density"


def test_normalize_correction_spec_note_fallback():
    spec = ReportDataCollector._normalize_correction_spec({"note": "see §4"})
    assert spec["suggested_correction"] == "see §4"


def test_normalize_correction_spec_preserves_explicit():
    spec = ReportDataCollector._normalize_correction_spec(
        {"primary_cause": "mesh", "confidence": "HIGH", "suggested_correction": "refine"}
    )
    assert spec["primary_cause"] == "mesh"
    assert spec["confidence"] == "HIGH"
    assert spec["suggested_correction"] == "refine"


def test_forbidden_anchor_paths_unchanged(repo_root: Path):
    protected = [
        repo_root / "src" / "auto_verifier" / "verifier.py",
        repo_root / "src" / "orchestrator" / "__init__.py",
        repo_root / "src" / "notion_client.py",
    ]
    for path in protected:
        assert path.exists()
