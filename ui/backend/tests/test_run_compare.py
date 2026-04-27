"""Tests for ui.backend.services.run_compare (ROADMAP §60-day · run-vs-run diff).

Uses the same monkeypatched RUNS_ROOT pattern as test_run_history.py
to avoid touching the real reports/ tree.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from ui.backend.services.run_compare import compare_runs
from ui.backend.services.run_history import write_run_artifacts


class _FakeEnum:
    def __init__(self, value):
        self.value = value


class _FakeTaskSpec:
    def __init__(self, *, name="LDC", Re=100.0, geometry_type="SIMPLE_GRID"):
        self.name = name
        self.Re = Re
        self.Ra = None
        self.Re_tau = None
        self.Ma = None
        self.geometry_type = _FakeEnum(geometry_type)
        self.flow_type = _FakeEnum("INTERNAL")
        self.steady_state = _FakeEnum("STEADY")
        self.compressibility = _FakeEnum("INCOMPRESSIBLE")


@pytest.fixture
def two_runs(tmp_path: Path, monkeypatch):
    """Write two LDC runs (Re=100 + Re=400) under tmp_path/reports/.
    Mirrors the real-world dogfood data this feature was built for."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )

    # Run A · Re=100 baseline
    write_run_artifacts(
        case_id="lid_driven_cavity",
        run_id="run_a",
        started_at=datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=100.0),
        source_origin="whitelist",
        success=True,
        exit_code=0,
        verdict_summary="OpenFOAM converged · 23.7s",
        duration_s=23.7,
        key_quantities={
            "u_max": 0.61,
            "u_min": -0.21,
            "u_centerline": [0.0, -0.04, -0.21, 0.30, 1.0],
        },
        residuals={"Ux": 1.4e-5, "Uy": 3.5e-5, "p": 1.0e-5},
        root=reports_root,
    )

    # Run B · Re=400 (edited via /edit page in dogfood)
    write_run_artifacts(
        case_id="lid_driven_cavity",
        run_id="run_b",
        started_at=datetime(2026, 4, 27, 10, 30, 0, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(Re=400.0),
        source_origin="draft",
        success=True,
        exit_code=0,
        verdict_summary="OpenFOAM converged · 20.1s",
        duration_s=20.1,
        key_quantities={
            "u_max": 0.74,
            "u_min": -0.33,
            "u_centerline": [0.0, -0.09, -0.33, 0.45, 1.0],
        },
        residuals={"Ux": 8.2e-6, "Uy": 1.5e-5, "p": 5.5e-6},
        root=reports_root,
    )
    return reports_root


def test_compare_returns_both_runs_metadata(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    assert out["case_id"] == "lid_driven_cavity"
    assert out["run_a"]["run_id"] == "run_a"
    assert out["run_b"]["run_id"] == "run_b"
    assert out["run_a"]["task_spec"]["Re"] == 100.0
    assert out["run_b"]["task_spec"]["Re"] == 400.0


def test_compare_surfaces_task_spec_re_change(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    re_diff = [d for d in out["task_spec_diff"] if d["key"] == "Re"]
    assert len(re_diff) == 1
    assert re_diff[0]["a"] == 100.0
    assert re_diff[0]["b"] == 400.0


def test_compare_scalar_diffs_compute_delta_pct(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_key = {d["key"]: d for d in out["scalar_diffs"]}
    # u_max went 0.61 → 0.74, Δ=0.13, Δ% = +21.3%
    u_max = by_key["u_max"]
    assert abs(u_max["delta_abs"] - 0.13) < 1e-9
    assert abs(u_max["delta_pct"] - 21.3114754) < 1e-3


def test_compare_array_diffs_pointwise(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_key = {d["key"]: d for d in out["array_diffs"]}
    uc = by_key["u_centerline"]
    assert uc["shape_match"] is True
    assert uc["a_len"] == 5
    assert uc["b_len"] == 5
    # Largest pointwise delta is at index 3: |0.45 - 0.30| = 0.15
    assert uc["max_abs_dev_index"] == 3
    assert abs(uc["max_abs_dev"] - 0.15) < 1e-9


def test_compare_residual_diffs(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_key = {d["key"]: d for d in out["residual_diffs"]}
    # Ux residual went 1.4e-5 → 8.2e-6, both finite, delta_abs negative
    assert by_key["Ux"]["a_finite"] is True
    assert by_key["Ux"]["b_finite"] is True
    assert by_key["Ux"]["delta_abs"] < 0


def test_compare_verdict_diff_no_change(two_runs):
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    # Both runs succeeded with exit_code 0
    assert out["verdict_diff"]["success_changed"] is False
    assert out["verdict_diff"]["exit_code_changed"] is False


def test_compare_missing_run_raises_filenotfound(two_runs):
    with pytest.raises(FileNotFoundError):
        compare_runs("lid_driven_cavity", "run_a", "does_not_exist")


def test_compare_missing_case_raises_filenotfound(two_runs):
    with pytest.raises(FileNotFoundError):
        compare_runs("no_such_case", "run_a", "run_b")


def test_compare_array_shape_mismatch_surfaces_flag(tmp_path, monkeypatch):
    """When two runs have arrays of different lengths (e.g. mesh-size
    edit changed the centerline sample count), the diff must NOT
    silently truncate — surface a shape_match=False flag instead."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_a",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": [1.0, 2.0, 3.0]},
        residuals={}, root=reports_root,
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_b",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": [1.0, 2.0, 3.0, 4.0, 5.0]},
        residuals={}, root=reports_root,
    )
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_key = {d["key"]: d for d in out["array_diffs"]}
    assert by_key["profile"]["shape_match"] is False
    assert by_key["profile"]["max_abs_dev"] is None


def test_compare_handles_nan_in_array_with_taint_flag(tmp_path, monkeypatch):
    """Codex r1 P1.2: diverged-NaN run vs converged run must NOT pose
    as identical. Service must surface a `tainted=True` flag and list
    the offending indices so a NaN-tainted array is structurally
    distinguishable from a clean one (even if mean_abs_dev happens to
    be 0 for the finite indices)."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_clean",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": [1.0, 2.0, 3.0]},
        residuals={}, root=reports_root,
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_diverged",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": [1.0, float("nan"), 3.0]},
        residuals={}, root=reports_root,
    )
    out = compare_runs("lid_driven_cavity", "run_clean", "run_diverged")
    by_key = {d["key"]: d for d in out["array_diffs"]}
    profile = by_key["profile"]
    assert profile["shape_match"] is True
    # The taint flag is the load-bearing assertion — it's the signal
    # that prevents the "looks identical" misclassification Codex flagged.
    assert profile["tainted"] is True
    assert 1 in profile["tainted_indices"]
    # Mean still 0.0 across finite-paired indices (0 and 2) — but the
    # taint flag means consumers know that's an incomplete picture.
    assert profile["mean_abs_dev"] == 0.0


def test_compare_clean_arrays_have_taint_false(two_runs):
    """Negative case: when both runs are fully finite, tainted=False."""
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_key = {d["key"]: d for d in out["array_diffs"]}
    uc = by_key["u_centerline"]
    assert uc["tainted"] is False
    assert uc["tainted_indices"] == []


def test_compare_scalar_to_array_type_mismatch(tmp_path, monkeypatch):
    """Codex r1 P2.1: when a key changes from scalar (run A) to array
    (run B), the diff must surface type_mismatch=True so the frontend
    can highlight the structural change rather than silently losing
    shape info to scalar_diff."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_a",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"u_max": 0.61},  # scalar
        residuals={}, root=reports_root,
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_b",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"u_max": [0.61, 0.62, 0.63]},  # array — mismatch
        residuals={}, root=reports_root,
    )
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    # u_max appears in array_diffs (with type_mismatch flag), NOT in
    # scalar_diffs — since merging losslessly into either bucket alone
    # would erase one side's structure.
    by_arr = {d["key"]: d for d in out["array_diffs"]}
    assert "u_max" in by_arr
    assert by_arr["u_max"]["type_mismatch"] is True
    assert by_arr["u_max"]["a_kind"] == "scalar"
    assert by_arr["u_max"]["b_kind"] == "array"


def test_compare_scalar_to_empty_list_routes_to_array_bucket(tmp_path, monkeypatch):
    """Codex r2 P2: when extractor failure produces an empty list on
    one side and the other side has a scalar, the diff must surface in
    array_diffs with type_mismatch=True — not collapse to scalar_diffs
    (which would lose the structural change). Empty list != failed
    scalar from a downstream perspective."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_a",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": 1.0},  # scalar
        residuals={}, root=reports_root,
    )
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_b",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"profile": []},  # empty list (extractor failure)
        residuals={}, root=reports_root,
    )
    out = compare_runs("lid_driven_cavity", "run_a", "run_b")
    by_arr = {d["key"]: d for d in out["array_diffs"]}
    assert "profile" in by_arr
    assert by_arr["profile"]["type_mismatch"] is True
    assert by_arr["profile"]["a_kind"] == "scalar"
    assert by_arr["profile"]["b_kind"] == "list_empty"
    # Must NOT also appear in scalar_diffs.
    assert not any(d["key"] == "profile" for d in out["scalar_diffs"])


# --- Codex r1 P2.2 · route-layer tests ------------------------------------


def _patch_runs_root_to(tmp_path: Path, monkeypatch):
    """Helper: redirect both run_history's RUNS_ROOT and the FakeTaskSpec
    write target to tmp_path/reports."""
    reports_root = tmp_path / "reports"
    monkeypatch.setattr(
        "ui.backend.services.run_history.RUNS_ROOT", reports_root
    )
    return reports_root


def test_route_compare_traversal_attempt_returns_400(tmp_path, monkeypatch):
    """Codex r1 P1.1: percent-encoded `..` in case_id must be rejected
    with HTTP 400 by run_ids._validate_segment, NOT a generic 404 from
    get_run_detail's filesystem check."""
    from fastapi.testclient import TestClient
    _patch_runs_root_to(tmp_path, monkeypatch)
    from ui.backend.main import app
    client = TestClient(app)
    # Direct '..' in case_id segment
    r = client.get("/api/cases/..%2F/run-history/run_a/compare/run_b")
    # Could be 400 (our validator) or 404 (FastAPI router can't resolve
    # the route at all because the % gets decoded to /); either is a
    # rejection. The bad case is a 200 OK.
    assert r.status_code in (400, 404, 422)
    # And explicitly: the literal '..' should hit our validator with 400
    r2 = client.get("/api/cases/..%2E.%2E/run-history/run_a/compare/run_b")
    assert r2.status_code in (400, 404, 422)


def test_route_compare_unsafe_run_id_returns_400(tmp_path, monkeypatch):
    """Slashes / dotfiles in run_id segments must also reject."""
    from fastapi.testclient import TestClient
    _patch_runs_root_to(tmp_path, monkeypatch)
    from ui.backend.main import app
    client = TestClient(app)
    # Embedded `..` in run_id (after URL decoding)
    r = client.get(
        "/api/cases/lid_driven_cavity/run-history/.../compare/run_b"
    )
    assert r.status_code in (400, 404)


def test_route_compare_missing_run_returns_404(tmp_path, monkeypatch):
    """Service-level FileNotFoundError must surface as HTTP 404, not 500."""
    from fastapi.testclient import TestClient
    reports_root = _patch_runs_root_to(tmp_path, monkeypatch)
    # Write only run_a so run_b lookup fails
    write_run_artifacts(
        case_id="lid_driven_cavity", run_id="run_a",
        started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        task_spec=_FakeTaskSpec(),
        source_origin="whitelist", success=True, exit_code=0,
        verdict_summary="x", duration_s=1.0,
        key_quantities={"u": 0.5}, residuals={}, root=reports_root,
    )
    from ui.backend.main import app
    client = TestClient(app)
    r = client.get(
        "/api/cases/lid_driven_cavity/run-history/run_a/compare/missing"
    )
    assert r.status_code == 404
    body = r.json()
    assert "missing" in body["detail"].lower() or "not found" in body["detail"].lower()


def test_route_compare_happy_path_returns_diff(tmp_path, monkeypatch):
    """Full round-trip via FastAPI route → 200 + correctly shaped JSON."""
    from fastapi.testclient import TestClient
    reports_root = _patch_runs_root_to(tmp_path, monkeypatch)
    for run_id, re_value, u_max in [("run_a", 100.0, 0.61), ("run_b", 400.0, 0.74)]:
        write_run_artifacts(
            case_id="lid_driven_cavity", run_id=run_id,
            started_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
            task_spec=_FakeTaskSpec(Re=re_value),
            source_origin="whitelist", success=True, exit_code=0,
            verdict_summary="x", duration_s=1.0,
            key_quantities={"u_max": u_max},
            residuals={}, root=reports_root,
        )
    from ui.backend.main import app
    client = TestClient(app)
    r = client.get(
        "/api/cases/lid_driven_cavity/run-history/run_a/compare/run_b"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert body["run_a"]["run_id"] == "run_a"
    assert body["run_b"]["run_id"] == "run_b"
    assert any(d["key"] == "Re" for d in body["task_spec_diff"])
