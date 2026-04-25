"""Stage 3 · mesh-metrics route tests.

Covers route 200/404 surface + QC band threshold semantics + honest
gray-state on oscillating convergence.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.schemas.mesh_metrics import (
    _verdict_gci,
    _verdict_n_levels,
    _verdict_richardson_p,
)

client = TestClient(app)


def test_lid_driven_cavity_returns_full_payload() -> None:
    r = client.get("/api/cases/lid_driven_cavity/mesh-metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert len(body["densities"]) == 4
    assert {d["id"] for d in body["densities"]} == {
        "mesh_20",
        "mesh_40",
        "mesh_80",
        "mesh_160",
    }
    assert "qc_band" in body
    assert set(body["qc_band"].keys()) == {
        "gci_32",
        "asymptotic_range",
        "richardson_p",
        "n_levels",
    }


def test_oscillating_convergence_yields_gray_band() -> None:
    """RBC and impinging_jet have sign-flip between refinements →
    Richardson formula doesn't apply → qc_band entries become gray
    rather than fake-green. Regression guard for the honesty
    requirement (Codex meeting anti-pattern: 假安全感)."""
    for cid in ("rayleigh_benard_convection", "impinging_jet"):
        r = client.get(f"/api/cases/{cid}/mesh-metrics")
        assert r.status_code == 200
        band = r.json()["qc_band"]
        assert band["gci_32"] == "gray"
        assert band["richardson_p"] == "gray"


def test_unknown_case_returns_404() -> None:
    r = client.get("/api/cases/never_existed/mesh-metrics")
    assert r.status_code == 404


def test_no_fixture_graceful_404_not_500() -> None:
    """Opus 4.7 review 2026-04-25 ACCEPT_WITH_COMMENTS edge case #1:
    a case_id with no mesh_*_measurement.yaml fixtures must return 404
    with a descriptive detail, not 500. Guards the graceful-degradation
    contract for newly-added cases that haven't been fixture-populated
    yet."""
    r = client.get("/api/cases/totally_no_fixture_yet/mesh-metrics")
    assert r.status_code == 404
    body = r.json()
    # detail should mention "fixture" or "mesh" so the client can react
    detail = (body.get("detail") or "").lower()
    assert "fixture" in detail or "mesh" in detail


def test_threshold_helper_gci() -> None:
    assert _verdict_gci(None) == "gray"
    assert _verdict_gci(0.0) == "green"
    assert _verdict_gci(5.0) == "green"
    assert _verdict_gci(5.0001) == "yellow"
    assert _verdict_gci(15.0) == "yellow"
    assert _verdict_gci(15.0001) == "red"


def test_threshold_helper_richardson_p() -> None:
    assert _verdict_richardson_p(None) == "gray"
    assert _verdict_richardson_p(2.0) == "green"
    assert _verdict_richardson_p(1.5) == "green"
    assert _verdict_richardson_p(2.5) == "green"
    assert _verdict_richardson_p(1.0) == "yellow"
    assert _verdict_richardson_p(4.0) == "yellow"
    assert _verdict_richardson_p(0.99) == "red"
    assert _verdict_richardson_p(4.01) == "red"


def test_threshold_helper_n_levels() -> None:
    assert _verdict_n_levels(4) == "green"
    assert _verdict_n_levels(3) == "yellow"
    assert _verdict_n_levels(2) == "red"
    assert _verdict_n_levels(0) == "red"


def test_all_whitelist_cases_serve_200() -> None:
    cases = [
        "lid_driven_cavity",
        "backward_facing_step",
        "circular_cylinder_wake",
        "turbulent_flat_plate",
        "plane_channel_flow",
        "differential_heated_cavity",
        "rayleigh_benard_convection",
        "naca0012_airfoil",
        "impinging_jet",
        "duct_flow",
    ]
    for cid in cases:
        r = client.get(f"/api/cases/{cid}/mesh-metrics")
        assert r.status_code == 200, f"{cid} returned {r.status_code}"
