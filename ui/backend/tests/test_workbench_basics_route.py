"""Stage 2 · workbench-basics route tests.

Guards route-level behavior: 200 on authored case, 404 on unauthored
case, 404 on traversal attempts. Schema-level validation (patch drift,
shape variants) is covered by service tests.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from ui.backend.main import app

client = TestClient(app)


def test_authored_case_returns_200() -> None:
    r = client.get("/api/cases/lid_driven_cavity/workbench-basics")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert body["geometry"]["shape"] == "rectangle"
    assert len(body["patches"]) >= 4
    assert any(p["role"] == "moving_wall" for p in body["patches"])


def test_unauthored_case_returns_404() -> None:
    # Stage 2 closed at 10/10 — every whitelist case is authored. Test
    # against a case_id that's clearly not in the whitelist.
    r = client.get("/api/cases/totally_made_up_case/workbench-basics")
    assert r.status_code == 404


def test_traversal_attempt_returns_404() -> None:
    # _validate_segment rejects path-traversal-shaped case ids; FastAPI
    # rewrites the path so the response is 404 rather than the 422 from
    # the validator (route never matches).
    r = client.get("/api/cases/..%2F..%2Fetc/workbench-basics")
    assert r.status_code == 404


def test_all_whitelist_cases_authored() -> None:
    """Stage 2 close trigger: 10/10 cases authored. Regression guard."""
    expected = [
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
    for cid in expected:
        r = client.get(f"/api/cases/{cid}/workbench-basics")
        assert r.status_code == 200, f"{cid} returned {r.status_code}"


def test_response_includes_required_top_level_fields() -> None:
    r = client.get("/api/cases/lid_driven_cavity/workbench-basics")
    body = r.json()
    for required in ("case_id", "display_name", "dimension", "geometry", "patches", "boundary_conditions", "materials"):
        assert required in body, f"missing field {required!r}"


def test_shape_variants_covered() -> None:
    """5 shape renderers in CaseFrame map to ≥5 distinct geometry.shape
    values across the 10 authored cases."""
    shapes_seen = set()
    for cid in (
        "lid_driven_cavity",
        "backward_facing_step",
        "circular_cylinder_wake",
        "naca0012_airfoil",
        "impinging_jet",
        "duct_flow",
    ):
        r = client.get(f"/api/cases/{cid}/workbench-basics")
        assert r.status_code == 200
        shapes_seen.add(r.json()["geometry"]["shape"])
    expected_shapes = {"rectangle", "step", "cylinder", "airfoil", "jet_impingement"}
    assert expected_shapes.issubset(shapes_seen)
