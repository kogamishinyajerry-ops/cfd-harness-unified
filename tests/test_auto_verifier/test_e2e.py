from pathlib import Path

import yaml

from auto_verifier import AutoVerifier
from src.models import Compressibility, ExecutionResult, FlowType, GeometryType, SteadyState, TaskSpec


def test_e2e_lid_driven_cavity(tmp_path: Path, copy_case_fixture):
    case_dir = copy_case_fixture("lid_driven_cavity_benchmark")
    output_path = tmp_path / "reports" / "lid_driven_cavity_benchmark" / "auto_verify_report.yaml"
    report = AutoVerifier().verify_from_files(
        case_id="lid_driven_cavity_benchmark",
        log_file=case_dir / "log.icoFoam",
        gold_standard_file=Path("knowledge/gold_standards/lid_driven_cavity_benchmark.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_path,
    )
    assert output_path.is_file()
    assert report.verdict == "PASS"


def test_e2e_backward_facing_step(tmp_path: Path, copy_case_fixture):
    case_dir = copy_case_fixture("backward_facing_step_steady")
    output_path = tmp_path / "reports" / "backward_facing_step_steady" / "auto_verify_report.yaml"
    report = AutoVerifier().verify_from_files(
        case_id="backward_facing_step_steady",
        log_file=case_dir / "log.simpleFoam",
        gold_standard_file=Path("knowledge/gold_standards/backward_facing_step_steady.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_path,
    )
    assert output_path.is_file()
    assert report.verdict == "PASS"


def test_e2e_cylinder_crossflow(tmp_path: Path, copy_case_fixture):
    case_dir = copy_case_fixture("cylinder_crossflow")
    output_path = tmp_path / "reports" / "cylinder_crossflow" / "auto_verify_report.yaml"
    report = AutoVerifier().verify_from_files(
        case_id="cylinder_crossflow",
        log_file=case_dir / "log.pimpleFoam",
        gold_standard_file=Path("knowledge/gold_standards/cylinder_crossflow.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=output_path,
    )
    assert output_path.is_file()
    assert report.verdict == "PASS"


def test_no_mutation_on_execution_plane(tmp_path: Path, copy_case_fixture, directory_hash):
    case_dir = copy_case_fixture("lid_driven_cavity_benchmark")
    corrections_dir = tmp_path / "corrections"
    corrections_dir.mkdir()
    before_case_hash = directory_hash(case_dir)
    before_corrections_hash = directory_hash(corrections_dir)

    AutoVerifier().verify_from_files(
        case_id="lid_driven_cavity_benchmark",
        log_file=case_dir / "log.icoFoam",
        gold_standard_file=Path("knowledge/gold_standards/lid_driven_cavity_benchmark.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=tmp_path / "report.yaml",
    )

    assert directory_hash(case_dir) == before_case_hash
    assert directory_hash(corrections_dir) == before_corrections_hash


def test_enabled_hook_reads_artifacts_without_mutation(tmp_path: Path, copy_case_fixture, directory_hash):
    case_dir = copy_case_fixture("cylinder_crossflow")
    before_hash = directory_hash(case_dir)
    sim_results = yaml.safe_load((case_dir / "sim_results.yaml").read_text())
    task = TaskSpec(
        name="Circular Cylinder Wake",
        geometry_type=GeometryType.BODY_IN_CHANNEL,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.TRANSIENT,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=100,
    )
    exec_result = ExecutionResult(
        success=True,
        is_mock=False,
        key_quantities=sim_results,
        raw_output_path=str(case_dir),
    )

    hook = AutoVerifier().build_post_execute_hook(enabled=True, output_root=tmp_path / "reports")
    report = hook(task_spec=task, exec_result=exec_result)
    assert report.verdict == "PASS"
    assert directory_hash(case_dir) == before_hash


def test_forbidden_anchor_paths_unchanged_during_verification(tmp_path: Path, copy_case_fixture, directory_hash):
    case_dir = copy_case_fixture("backward_facing_step_steady")
    guarded_paths = [
        Path("src/error_attributor.py"),
        Path("src/foam_agent_adapter.py"),
        Path("src/result_comparator.py"),
        Path("tests/test_error_attributor.py"),
        Path("tests/test_foam_agent_adapter.py"),
        Path("tests/test_result_comparator.py"),
    ]
    before_hashes = {str(path): directory_hash(path.parent) for path in guarded_paths}

    AutoVerifier().verify_from_files(
        case_id="backward_facing_step_steady",
        log_file=case_dir / "log.simpleFoam",
        gold_standard_file=Path("knowledge/gold_standards/backward_facing_step_steady.yaml"),
        sim_results_file=case_dir / "sim_results.yaml",
        output_path=tmp_path / "report.yaml",
    )

    after_hashes = {str(path): directory_hash(path.parent) for path in guarded_paths}
    assert before_hashes == after_hashes

