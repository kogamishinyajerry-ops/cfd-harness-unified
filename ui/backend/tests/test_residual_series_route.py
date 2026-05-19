"""Route-level tests for ``GET /api/cases/{case_id}/residual-series``.

Closes Codex R7 polish-item #3 (route-level serialization test).
The service layer is already exhaustively covered by
``test_residual_series.py``; this file pins the **HTTP boundary**:

  * JSON envelope shape matches the frontend ``ResidualSeriesPayload``
    contract in ``ui/frontend/src/types/residual_series.ts``
  * ``is_safe_case_id`` traversal guard → 400 on unsafe input
  * All three source labels (``log`` / ``runs`` / ``empty``) flow
    through the serializer without dropping fields
  * Series points serialize as ``{x, y}`` dicts (not the dataclass
    ``ResidualSeriesPoint`` repr)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.services.run_history import write_run_artifacts


# ──────────────────────── fixtures ────────────────────────


class _FakeEnum:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeTaskSpec:
    def __init__(self, *, Re: float = 100.0) -> None:
        self.name = "LDC"
        self.Re = Re
        self.Ra = None
        self.Re_tau = None
        self.Ma = None
        self.geometry_type = _FakeEnum("SIMPLE_GRID")
        self.flow_type = _FakeEnum("INTERNAL")
        self.steady_state = _FakeEnum("STEADY")
        self.compressibility = _FakeEnum("INCOMPRESSIBLE")


def _new_client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


@pytest.fixture
def isolated_roots(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    """Redirect every disk path the route's no-kwarg
    ``build_residual_series(case_id)`` may touch:

      * ``residual_series.IMPORTED_DIR`` — used by ``_try_log`` for the
        per-case persistent solver log.
      * ``residual_series.RUNS_ROOT`` — used by ``_try_log`` for the
        future per-run log fallback (Codex R8 P4 hardening: this
        binding is the module-local name resolved at import time;
        patching ``run_history.RUNS_ROOT`` alone does NOT cover it).
      * ``run_history.RUNS_ROOT`` — used by ``list_runs`` /
        ``get_run_detail`` via ``_from_runs``.

    With all three patched the route is fully isolated from the real
    ``reports/`` tree even if a future archive lands logs there."""
    imported = tmp_path / "imported"
    reports = tmp_path / "reports"
    imported.mkdir()
    reports.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_visualize.residual_series.IMPORTED_DIR",
        imported,
    )
    monkeypatch.setattr(
        "ui.backend.services.case_visualize.residual_series.RUNS_ROOT",
        reports,
    )
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT",
        reports,
    )
    return imported, reports


# ──────────────────────── safety + 4xx ────────────────────────


def test_residual_series_rejects_unsafe_case_id():
    """``is_safe_case_id`` traversal guard: ``../etc`` → 400."""
    client = _new_client()
    # FastAPI/Starlette resolves "../foo" against the route before our
    # handler runs; use a stem that *parses* as a valid path segment
    # but trips the alnum+[_-] guard (e.g. embeds a ``.``).
    resp = client.get("/api/cases/bad.case.id/residual-series")
    assert resp.status_code == 400
    assert "unsafe" in resp.json()["detail"].lower()


# ──────────────────────── source = empty ────────────────────────


def test_residual_series_empty_source(isolated_roots):
    """No log and no runs → 200 with source='empty', empty series dict,
    sample_count=0, achieved=False, human-readable note."""
    client = _new_client()
    resp = client.get("/api/cases/nonexistent_case/residual-series")
    assert resp.status_code == 200
    body = resp.json()

    # Full envelope contract.
    assert body["case_id"] == "nonexistent_case"
    assert body["source"] == "empty"
    assert body["series"] == {}
    assert body["sample_count"] == 0
    assert body["latest_run_id"] is None
    assert body["target_floor"] == pytest.approx(1.0e-6)
    assert body["achieved"] is False
    assert isinstance(body["note"], str) and body["note"]


# ──────────────────────── source = log ────────────────────────


def test_residual_series_log_source(isolated_roots):
    """Valid log on disk → source='log', series points serialize as
    {x, y} dicts (not dataclass repr), achieved reflects target_floor."""
    imported, _ = isolated_roots
    case_id = "ldc_case"
    case_dir = imported / case_id
    case_dir.mkdir()
    (case_dir / "log.icoFoam").write_text(
        "Time = 1\n"
        "smoothSolver:  Solving for Ux, Initial residual = 1.0e-7, Final residual = 1e-8,\n"
        "smoothSolver:  Solving for Uy, Initial residual = 2.0e-7, Final residual = 1e-8,\n"
        "DICPCG:  Solving for p, Initial residual = 3.0e-7, Final residual = 1e-8,\n"
    )

    resp = _new_client().get(f"/api/cases/{case_id}/residual-series")
    assert resp.status_code == 200
    body = resp.json()

    assert body["source"] == "log"
    assert body["latest_run_id"] is None  # log path is run-agnostic
    assert body["sample_count"] == 1
    assert set(body["series"].keys()) == {"Ux", "Uy", "p"}

    # Points must be plain {x, y} dicts — Codex R6 contract.
    ux_pts = body["series"]["Ux"]
    assert isinstance(ux_pts, list) and len(ux_pts) == 1
    assert set(ux_pts[0].keys()) == {"x", "y"}
    assert ux_pts[0]["x"] == pytest.approx(1.0)
    assert ux_pts[0]["y"] == pytest.approx(1.0e-7)

    # All values below 1e-6 → achieved True.
    assert body["achieved"] is True


# ──────────────────────── source = runs ────────────────────────


def test_residual_series_runs_source(isolated_roots):
    """No log + valid runs → source='runs', latest_run_id surfaces,
    series x axis = run ordinal (1-based oldest→newest)."""
    imported, reports = isolated_roots
    case_id = "lid_driven_cavity"

    # Two ordered runs, oldest first.
    write_run_artifacts(
        case_id=case_id,
        run_id="run_a",
        started_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=100.0),
        source_origin="whitelist",
        success=True,
        exit_code=0,
        verdict_summary="converged",
        duration_s=20.0,
        key_quantities={"u_max": 0.61},
        residuals={"Ux": 1.4e-5, "p": 1.0e-5},
        root=reports,
    )
    write_run_artifacts(
        case_id=case_id,
        run_id="run_b",
        started_at=datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=400.0),
        source_origin="draft",
        success=True,
        exit_code=0,
        verdict_summary="converged",
        duration_s=22.0,
        key_quantities={"u_max": 0.74},
        residuals={"Ux": 9.0e-6, "p": 8.0e-6},
        root=reports,
    )

    resp = _new_client().get(f"/api/cases/{case_id}/residual-series")
    assert resp.status_code == 200
    body = resp.json()

    assert body["source"] == "runs"
    assert body["latest_run_id"] == "run_b"
    assert body["sample_count"] == 2

    # Newest (run_b) is the last sample of each series.
    ux_pts = body["series"]["Ux"]
    assert ux_pts[-1] == {"x": 2.0, "y": pytest.approx(9.0e-6)}
    assert ux_pts[0] == {"x": 1.0, "y": pytest.approx(1.4e-5)}

    # 9e-6 > 1e-6 target_floor → not achieved.
    assert body["achieved"] is False


# ──────────────────────── content-type + headers ────────────────────────


def test_residual_series_returns_json_content_type(isolated_roots):
    """Sanity: response is application/json, not the PNG content-type
    of the neighbouring /residual-history.png route. Guards against a
    refactor accidentally routing /residual-series through _png_response."""
    resp = _new_client().get("/api/cases/anything/residual-series")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "application/json" in ct
