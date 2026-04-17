from pathlib import Path

from auto_verifier import ConvergenceChecker


def test_l1_converged(tmp_path: Path):
    log_file = tmp_path / "log.icoFoam"
    log_file.write_text(
        "\n".join(
            [
                "Solving for Ux, Initial residual = 1.0e-02, Final residual = 5.0e-04",
                "Solving for Ux, Initial residual = 5.0e-04, Final residual = 1.0e-05",
                "Solving for p, Initial residual = 2.0e-03, Final residual = 9.0e-06",
            ]
        )
    )

    report = ConvergenceChecker().check(log_file)
    assert report.status == "CONVERGED"
    assert report.final_residual == 1.0e-05


def test_l1_oscillating(tmp_path: Path):
    log_file = tmp_path / "log.simpleFoam"
    log_file.write_text(
        "\n".join(
            [
                f"Solving for Ux, Initial residual = 1.0e-03, Final residual = {value:.1e}"
                for value in [1.0e-4, 2.0e-4, 1.1e-4, 2.2e-4, 1.2e-4, 2.3e-4]
            ]
        )
    )

    report = ConvergenceChecker().check(log_file)
    assert report.status == "OSCILLATING"


def test_l1_diverged(tmp_path: Path):
    log_file = tmp_path / "log.pimpleFoam"
    log_file.write_text(
        "\n".join(
            [
                "Solving for Ux, Initial residual = 1.0e-06, Final residual = 2.0e-05",
                "Solving for Ux, Initial residual = 2.0e-05, Final residual = 2.0e-04",
            ]
        )
    )

    report = ConvergenceChecker().check(log_file)
    assert report.status == "DIVERGED"


def test_l1_missing_log(tmp_path: Path):
    report = ConvergenceChecker().check(tmp_path / "missing.log")
    assert report.status == "UNKNOWN"
    assert "missing_or_empty_log" in report.warnings

