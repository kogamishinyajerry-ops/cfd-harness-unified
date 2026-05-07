"""B-ext-4.2 F11 fix (DEC-V61-188) regression: /solve must populate
the run-history registry so /api/cases/{id}/run-history doesn't return
empty after a successful solve.

R7 + curl direct E2E showed /solve returning SolveSummary 200 but
/run-history still showed `runs: []`. Root cause: /solve route called
run_icofoam directly without ever invoking write_run_artifacts; only
RealSolverDriver (M3 closed-loop) was wired.

These tests use the run-history service layer directly + a mock-friendly
solver-result shape, so they don't need Docker.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", tmp_path
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_solve.IMPORTED_DIR", tmp_path
    )
    # Redirect run-history writes into tmp_path/reports so the test
    # doesn't pollute the real reports/ tree.
    reports = tmp_path / "reports"
    reports.mkdir(exist_ok=True)
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports
    )
    from ui.backend.main import app

    return TestClient(app)


def _seed_consistent_case(case_dir: Path) -> None:
    """Mesh + 0/ matching — pre-flight passes; run_icofoam will be
    mocked to return success."""
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(
        "FoamFile { object controlDict; }\napplication icoFoam;\n"
    )
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "boundary").write_text(
        "FoamFile { object boundary; }\n"
        "1\n(\n    patch0 { type patch; nFaces 100; startFace 0; }\n)\n"
    )
    zero = case_dir / "0"
    zero.mkdir()
    (zero / "p").write_text(
        "boundaryField { patch0 { type zeroGradient; } }"
    )


def test_solve_writes_run_artifacts_so_run_history_lists_run(
    client: TestClient, tmp_path: Path
) -> None:
    """The contract: after POST /solve returns SolveSummary 200, GET
    /run-history must include the new run_id."""
    from ui.backend.services.case_solve.solver_runner import SolverRunResult

    case_dir = tmp_path / "imported_2026-test_F11"
    _seed_consistent_case(case_dir)

    fake_result = SolverRunResult(
        case_id=case_dir.name,
        end_time_reached=2.0,
        last_initial_residual_p=1e-4,
        last_initial_residual_U=(1e-5, 1e-5, 1e-5),
        last_continuity_error=1e-7,
        n_time_steps_written=5,
        time_directories=("0", "0.5", "1", "1.5", "2"),
        log_path=case_dir / "log.icoFoam",
        wall_time_s=66.5,
        converged=True,
    )

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=fake_result,
    ):
        solve_resp = client.post(f"/api/import/{case_dir.name}/solve")
        assert solve_resp.status_code == 200, solve_resp.text
        body = solve_resp.json()
        assert body["converged"] is True
        run_id = body.get("run_id")
        assert run_id is not None and run_id != ""

        # Run-history must now include this run_id.
        rh_resp = client.get(f"/api/cases/{case_dir.name}/run-history")
        assert rh_resp.status_code == 200, rh_resp.text
        rh_body = rh_resp.json()
        assert rh_body["case_id"] == case_dir.name
        run_ids = [r["run_id"] for r in rh_body["runs"]]
        assert run_id in run_ids, f"run_id {run_id} not in {run_ids}"


def test_solve_records_residuals_and_key_quantities(
    client: TestClient, tmp_path: Path
) -> None:
    """The persisted measurement.yaml must carry the SolveSummary's
    residuals + n_time_steps_written so persona's verdict reasoning
    has data to cite."""
    from ui.backend.services.case_solve.solver_runner import SolverRunResult

    case_dir = tmp_path / "imported_2026-test_F11_quants"
    _seed_consistent_case(case_dir)

    fake_result = SolverRunResult(
        case_id=case_dir.name,
        end_time_reached=2.0,
        last_initial_residual_p=7.76e-4,
        last_initial_residual_U=(0.124, 0.086, 0.170),
        last_continuity_error=8.5e-8,
        n_time_steps_written=5,
        time_directories=("0", "0.5", "1", "1.5", "2"),
        log_path=case_dir / "log.icoFoam",
        wall_time_s=66.45,
        converged=True,
    )

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        return_value=fake_result,
    ):
        solve_resp = client.post(f"/api/import/{case_dir.name}/solve")
        run_id = solve_resp.json()["run_id"]

        detail = client.get(
            f"/api/cases/{case_dir.name}/run-history/{run_id}"
        )
        assert detail.status_code == 200, detail.text
        d = detail.json()
        # measurement.yaml round-trip
        kq = d.get("key_quantities") or {}
        assert kq.get("end_time_reached") == 2.0
        assert kq.get("n_time_steps_written") == 5
        residuals = d.get("residuals") or {}
        assert residuals.get("p") == 7.76e-4
        assert residuals.get("Ux") == 0.124


def test_solve_failure_does_not_write_run_artifacts(
    client: TestClient, tmp_path: Path
) -> None:
    """Symmetric: when run_icofoam raises, no run-history entry is
    persisted. The case keeps a clean run-history (no orphan partials)."""
    from ui.backend.services.case_solve.solver_runner import SolverRunError

    case_dir = tmp_path / "imported_2026-test_F11_fail"
    _seed_consistent_case(case_dir)

    with patch(
        "ui.backend.routes.case_solve.run_icofoam",
        side_effect=SolverRunError("simpleFoam exited with code 1"),
    ):
        solve_resp = client.post(f"/api/import/{case_dir.name}/solve")
        assert solve_resp.status_code == 502, solve_resp.text

        rh_resp = client.get(f"/api/cases/{case_dir.name}/run-history")
        assert rh_resp.status_code == 200, rh_resp.text
        assert rh_resp.json()["runs"] == []
