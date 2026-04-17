from pathlib import Path

import yaml

from auto_verifier import AutoVerifier


def test_report_yaml_schema(tmp_path: Path, copy_case_fixture):
    case_dir = copy_case_fixture("lid_driven_cavity_benchmark")
    output_path = tmp_path / "report.yaml"
    report = AutoVerifier().verify_from_files(
        case_id="lid_driven_cavity_benchmark",
        log_file=case_dir / "log.icoFoam",
        gold_standard_file=Path("knowledge/gold_standards/lid_driven_cavity_benchmark.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_path,
    )

    raw = yaml.safe_load(output_path.read_text())
    assert raw["case_id"] == report.case_id
    assert raw["convergence"]["status"] in {"CONVERGED", "OSCILLATING", "DIVERGED", "UNKNOWN"}
    assert raw["gold_standard_comparison"]["overall"] in {"PASS", "PASS_WITH_DEVIATIONS", "FAIL", "SKIPPED"}
    assert raw["physics_check"]["status"] in {"PASS", "WARN", "FAIL"}
    assert raw["verdict"] in {"PASS", "PASS_WITH_DEVIATIONS", "FAIL"}


def test_determinism_replay(tmp_path: Path, copy_case_fixture):
    case_dir = copy_case_fixture("backward_facing_step_steady")
    verifier = AutoVerifier()
    output_a = tmp_path / "a.yaml"
    output_b = tmp_path / "b.yaml"

    verifier.verify_from_files(
        case_id="backward_facing_step_steady",
        log_file=case_dir / "log.simpleFoam",
        gold_standard_file=Path("knowledge/gold_standards/backward_facing_step_steady.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_a,
    )
    verifier.verify_from_files(
        case_id="backward_facing_step_steady",
        log_file=case_dir / "log.simpleFoam",
        gold_standard_file=Path("knowledge/gold_standards/backward_facing_step_steady.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_b,
    )

    assert output_a.read_text() == output_b.read_text()


def test_disabled_hook_is_noop(tmp_path: Path):
    hook = AutoVerifier().build_post_execute_hook(enabled=False, output_root=tmp_path)
    result = hook(task_spec=None, exec_result=None)
    assert result["status"] == "disabled"


def test_out_of_scope_case_returns_noop(tmp_path: Path):
    report = AutoVerifier().verify(
        case_id="of-99-future-case",
        log_file=tmp_path / "missing.log",
        gold_standard={"observables": []},
        sim_results={},
        output_path=tmp_path / "report.yaml",
    )
    assert report.out_of_scope_reason is not None
    assert report.gold_standard_comparison.overall == "SKIPPED"
