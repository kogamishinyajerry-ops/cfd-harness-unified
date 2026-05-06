"""Unit + route tests for refinement zones (DEC-V61-136 · N2.2).

Covers:
* Schema validators on BoxRefinementZone / SphereRefinementZone
* Discriminated-union routing on the ``geometry`` tag
* lc_scale_for_level helper parity
* AABB-overlap helpers (_geometry_aabb / _box_intersects_aabb /
  _sphere_intersects_aabb / _validate_refinement_zones)
* MeshRequest accepts ``refinement_zones``
* Route plumbs zones through to ``mesh_imported_case``
* Route translates ``RefinementZoneError`` from pipeline → 422 with
  ``failing_check=refinement_zone_invalid``
* Empty list / None preserves N2.1 behavior (back-compat)
* No envelope drift — V132 advisor contract still green (covered in
  test_ai_advisor_contract.py; we don't re-assert here).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from ui.backend.main import app
from ui.backend.schemas.mesh_imported import MeshRequest
from ui.backend.schemas.mesh_refinement import (
    BoxRefinementZone,
    LEVEL_MAX,
    LEVEL_MIN,
    MeshRefinementZone,
    SphereRefinementZone,
    lc_scale_for_level,
)


client = TestClient(app)

# Discriminated-union TypeAdapter for the union outside MeshRequest;
# pydantic 2 requires the Annotated[Union, Field(discriminator=...)] to
# be validated through TypeAdapter when used outside a containing model.
_ZoneAdapter: TypeAdapter[MeshRefinementZone] = TypeAdapter(MeshRefinementZone)


# ---------------------- Schema validator tests ----------------------


def test_box_zone_valid_shape():
    z = BoxRefinementZone(
        bbox=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
        level=2,
    )
    assert z.geometry == "box"
    assert z.level == 2
    assert z.bbox == [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]


def test_box_zone_rejects_inverted_extent():
    with pytest.raises(ValidationError):
        BoxRefinementZone(bbox=[1.0, 0.0, 0.0, 0.0, 1.0, 1.0], level=1)


def test_box_zone_rejects_zero_extent():
    with pytest.raises(ValidationError):
        BoxRefinementZone(bbox=[0.0, 0.0, 0.0, 0.0, 1.0, 1.0], level=1)


def test_box_zone_rejects_wrong_bbox_length():
    with pytest.raises(ValidationError):
        BoxRefinementZone(bbox=[0.0, 0.0, 0.0, 1.0, 1.0], level=1)


def test_sphere_zone_valid_shape():
    z = SphereRefinementZone(center=[0.5, 0.5, 0.5], radius=0.1, level=3)
    assert z.geometry == "sphere"
    assert z.radius == 0.1


def test_sphere_zone_rejects_negative_radius():
    with pytest.raises(ValidationError):
        SphereRefinementZone(center=[0.0, 0.0, 0.0], radius=-0.1, level=1)


def test_sphere_zone_rejects_zero_radius():
    with pytest.raises(ValidationError):
        SphereRefinementZone(center=[0.0, 0.0, 0.0], radius=0.0, level=1)


def test_sphere_zone_rejects_wrong_center_length():
    with pytest.raises(ValidationError):
        SphereRefinementZone(center=[0.0, 0.0], radius=0.1, level=1)


@pytest.mark.parametrize("bad_level", [0, -1, LEVEL_MAX + 1, 99])
def test_zone_rejects_level_out_of_range(bad_level: int):
    with pytest.raises(ValidationError):
        BoxRefinementZone(
            bbox=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0], level=bad_level
        )
    with pytest.raises(ValidationError):
        SphereRefinementZone(
            center=[0.0, 0.0, 0.0], radius=0.1, level=bad_level
        )


def test_discriminated_union_routes_box():
    payload = {
        "geometry": "box",
        "bbox": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
        "level": 1,
    }
    z = _ZoneAdapter.validate_python(payload)
    assert isinstance(z, BoxRefinementZone)


def test_discriminated_union_routes_sphere():
    payload = {
        "geometry": "sphere",
        "center": [0.0, 0.0, 0.0],
        "radius": 0.5,
        "level": 2,
    }
    z = _ZoneAdapter.validate_python(payload)
    assert isinstance(z, SphereRefinementZone)


def test_discriminated_union_rejects_unknown_geometry():
    with pytest.raises(ValidationError):
        _ZoneAdapter.validate_python(
            {"geometry": "tetrahedron", "level": 1}
        )


def test_lc_scale_for_level_doubles_per_step():
    assert lc_scale_for_level(1) == pytest.approx(0.5)
    assert lc_scale_for_level(2) == pytest.approx(0.25)
    assert lc_scale_for_level(3) == pytest.approx(0.125)


def test_lc_scale_for_level_rejects_out_of_range():
    with pytest.raises(ValueError):
        lc_scale_for_level(LEVEL_MIN - 1)
    with pytest.raises(ValueError):
        lc_scale_for_level(LEVEL_MAX + 1)


# ---------------------- AABB helper tests ----------------------


def test_geometry_aabb_empty_returns_none():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _geometry_aabb

    assert _geometry_aabb([]) is None


def test_geometry_aabb_typical_points():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _geometry_aabb

    pts = [(0.0, 0.0, 0.0), (1.0, 2.0, 3.0), (-0.5, 0.5, 1.0)]
    assert _geometry_aabb(pts) == (-0.5, 0.0, 0.0, 1.0, 2.0, 3.0)


def test_box_intersects_aabb_full_overlap():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _box_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert _box_intersects_aabb([1.0, 1.0, 1.0, 5.0, 5.0, 5.0], geom_aabb)


def test_box_intersects_aabb_partial_overlap():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _box_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # Box hangs off the +x face but still overlaps
    assert _box_intersects_aabb([5.0, 5.0, 5.0, 15.0, 15.0, 15.0], geom_aabb)


def test_box_intersects_aabb_disjoint_x_axis():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _box_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert not _box_intersects_aabb([20.0, 5.0, 5.0, 30.0, 5.5, 5.5], geom_aabb)


def test_box_intersects_aabb_disjoint_z_axis():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _box_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # Disjoint along z, despite overlap in x and y
    assert not _box_intersects_aabb([1.0, 1.0, 20.0, 5.0, 5.0, 25.0], geom_aabb)


def test_sphere_intersects_aabb_center_inside():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _sphere_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    assert _sphere_intersects_aabb([5.0, 5.0, 5.0], 0.1, geom_aabb)


def test_sphere_intersects_aabb_touching_face():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _sphere_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # Center 11 units beyond +x face, radius 1.0 → reaches face exactly
    assert _sphere_intersects_aabb([11.0, 5.0, 5.0], 1.0, geom_aabb)


def test_sphere_intersects_aabb_disjoint():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _sphere_intersects_aabb

    geom_aabb = (0.0, 0.0, 0.0, 10.0, 10.0, 10.0)
    # Center 20 units beyond, radius 1.0 → far short
    assert not _sphere_intersects_aabb([20.0, 5.0, 5.0], 1.0, geom_aabb)


def test_validate_refinement_zones_accepts_overlap():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _validate_refinement_zones

    aabb = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    zones = [
        {"geometry": "box", "bbox": [0.2, 0.2, 0.2, 0.8, 0.8, 0.8], "level": 2},
        {"geometry": "sphere", "center": [0.5, 0.5, 0.5], "radius": 0.1, "level": 3},
    ]
    # No raise = pass
    _validate_refinement_zones(zones, aabb)


def test_validate_refinement_zones_rejects_box_outside():
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        RefinementZoneError,
        _validate_refinement_zones,
    )

    aabb = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    zones = [
        {"geometry": "box", "bbox": [10.0, 10.0, 10.0, 11.0, 11.0, 11.0], "level": 1},
    ]
    with pytest.raises(RefinementZoneError) as exc_info:
        _validate_refinement_zones(zones, aabb)
    assert "refinement_zones[0]" in str(exc_info.value)
    assert "no overlap" in str(exc_info.value)


def test_validate_refinement_zones_rejects_sphere_outside():
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        RefinementZoneError,
        _validate_refinement_zones,
    )

    aabb = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    zones = [
        {"geometry": "sphere", "center": [10.0, 10.0, 10.0], "radius": 0.1, "level": 1},
    ]
    with pytest.raises(RefinementZoneError) as exc_info:
        _validate_refinement_zones(zones, aabb)
    assert "refinement_zones[0]" in str(exc_info.value)


def test_validate_refinement_zones_empty_list_noop():
    from ui.backend.services.meshing_gmsh.gmsh_runner import _validate_refinement_zones

    aabb = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    # Should not raise on empty list or None aabb
    _validate_refinement_zones([], aabb)
    _validate_refinement_zones(
        [{"geometry": "box", "bbox": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0], "level": 1}],
        None,  # degenerate gmsh state — caller skips validation
    )


def test_validate_refinement_zones_rejects_unknown_geometry():
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        RefinementZoneError,
        _validate_refinement_zones,
    )

    aabb = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    with pytest.raises(RefinementZoneError):
        _validate_refinement_zones(
            [{"geometry": "tetrahedron", "level": 1}],
            aabb,
        )


# ---------------------- MeshRequest integration ----------------------


def test_mesh_request_default_omits_refinement_zones():
    req = MeshRequest()
    assert req.refinement_zones is None


def test_mesh_request_accepts_zones_list():
    req = MeshRequest.model_validate({
        "mesh_mode": "beginner",
        "refinement_zones": [
            {"geometry": "box", "bbox": [0, 0, 0, 1, 1, 1], "level": 2},
            {"geometry": "sphere", "center": [0.5, 0.5, 0.5], "radius": 0.1, "level": 3},
        ],
    })
    assert req.refinement_zones is not None
    assert len(req.refinement_zones) == 2
    assert isinstance(req.refinement_zones[0], BoxRefinementZone)
    assert isinstance(req.refinement_zones[1], SphereRefinementZone)


def test_mesh_request_empty_zones_list_is_permitted():
    req = MeshRequest.model_validate({
        "mesh_mode": "beginner",
        "refinement_zones": [],
    })
    assert req.refinement_zones == []


# ---------------------- Route-level tests ----------------------


def test_mesh_route_plumbs_refinement_zones(tmp_path: Path):
    """POST body with refinement_zones is forwarded to pipeline."""
    from ui.backend.services.meshing_gmsh.pipeline import MeshResult
    from ui.backend.routes import mesh_imported as route_mod

    fake = MeshResult(
        case_id="imported_TEST_zones",
        # Pure refinement_zones (no sizing_field) keeps preset label.
        mesh_mode="beginner",
        cell_count=44_444,
        face_count=20_000,
        point_count=8_000,
        polyMesh_path=tmp_path / "constant" / "polyMesh",
        msh_path=tmp_path / "imported.msh",
        generation_time_s=3.14,
        warning=None,
    )

    captured: dict = {}

    def _spy(case_id: str, **kwargs):
        captured["case_id"] = case_id
        captured["kwargs"] = kwargs
        return fake

    with patch.object(route_mod, "mesh_imported_case", side_effect=_spy):
        response = client.post(
            "/api/import/imported_TEST_zones/mesh",
            json={
                "mesh_mode": "beginner",
                "refinement_zones": [
                    {"geometry": "box", "bbox": [0, 0, 0, 1, 1, 1], "level": 2},
                    {"geometry": "sphere", "center": [0.5, 0.5, 0.5], "radius": 0.1, "level": 3},
                ],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mesh_summary"]["mesh_mode_used"] == "beginner"
    zones = captured["kwargs"]["refinement_zones"]
    assert zones is not None
    assert len(zones) == 2
    assert zones[0].geometry == "box"
    assert zones[1].geometry == "sphere"


def test_mesh_route_default_omits_refinement_zones(tmp_path: Path):
    """Back-compat: callers that don't set refinement_zones see the
    pipeline receive ``None`` and the V135-era response shape unchanged.
    """
    from ui.backend.services.meshing_gmsh.pipeline import MeshResult
    from ui.backend.routes import mesh_imported as route_mod

    fake = MeshResult(
        case_id="imported_TEST_no_zones",
        mesh_mode="beginner",
        cell_count=10_000,
        face_count=5_000,
        point_count=2_000,
        polyMesh_path=tmp_path / "constant" / "polyMesh",
        msh_path=tmp_path / "imported.msh",
        generation_time_s=1.0,
        warning=None,
    )
    captured: dict = {}

    def _spy(case_id: str, **kwargs):
        captured["kwargs"] = kwargs
        return fake

    with patch.object(route_mod, "mesh_imported_case", side_effect=_spy):
        response = client.post(
            "/api/import/imported_TEST_no_zones/mesh",
            json={"mesh_mode": "beginner"},
        )

    assert response.status_code == 200
    assert captured["kwargs"]["refinement_zones"] is None


def test_mesh_route_translates_refinement_zone_invalid_to_422():
    """Pipeline raising ``MeshPipelineError(failing_check=refinement_zone_invalid)``
    surfaces as HTTP 422 with the structured rejection body.
    """
    from ui.backend.services.meshing_gmsh.pipeline import MeshPipelineError
    from ui.backend.routes import mesh_imported as route_mod

    def _raise_zone_error(case_id: str, **kwargs):
        raise MeshPipelineError(
            "refinement_zones[0] (box) bbox=[10,10,10,11,11,11] has no overlap with case AABB=[0,0,0,1,1,1]; the gmsh field would be a no-op.",
            "refinement_zone_invalid",
        )

    with patch.object(route_mod, "mesh_imported_case", side_effect=_raise_zone_error):
        response = client.post(
            "/api/import/imported_TEST_outside/mesh",
            json={
                "mesh_mode": "beginner",
                "refinement_zones": [
                    {"geometry": "box", "bbox": [10, 10, 10, 11, 11, 11], "level": 1},
                ],
            },
        )

    assert response.status_code == 422
    body = response.json()
    detail = body["detail"]
    assert detail["failing_check"] == "refinement_zone_invalid"
    assert "refinement_zones[0]" in detail["reason"]
    assert "no overlap" in detail["reason"]


def test_mesh_route_rejects_bogus_zone_payload():
    """Schema-level rejection (zero-extent bbox) → 422 with FastAPI
    validation error shape (NOT failing_check — pre-pipeline).
    """
    response = client.post(
        "/api/import/imported_TEST_bogus/mesh",
        json={
            "mesh_mode": "beginner",
            "refinement_zones": [
                {"geometry": "box", "bbox": [0, 0, 0, 0, 1, 1], "level": 1},
            ],
        },
    )
    assert response.status_code == 422
    # FastAPI request-validation shape, not the pipeline's failing_check.
    body = response.json()
    assert "detail" in body


# ---------------------- Pipeline plumbing ----------------------


def test_pipeline_passes_zones_to_gmsh_runner():
    """Verify mesh_imported_case forwards refinement_zones to
    run_gmsh_on_imported_case and that pure-zones runs do NOT toggle
    mesh_mode_used="custom" (custom is reserved for sizing_field
    activeness — engineers can mix preset+zones without losing the
    preset label).
    """
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod
    from ui.backend.services.meshing_gmsh.gmsh_runner import GmshRunResult

    fake_gmsh_result = GmshRunResult(
        msh_path=Path("/tmp/fake.msh"),
        cell_count=10_000,
        face_count=5_000,
        point_count=2_000,
        characteristic_length_used=0.05,
        generation_time_s=0.1,
    )
    fake_foam_result = type("F", (), {"polyMesh_dir": Path("/tmp/poly")})()

    captured: dict = {}

    def _spy_runner(**kwargs):
        captured["kwargs"] = kwargs
        return fake_gmsh_result

    zones = [
        BoxRefinementZone(bbox=[0.2, 0.2, 0.2, 0.8, 0.8, 0.8], level=2),
    ]

    with patch.object(
        pipeline_mod, "_resolve_imported_case",
        return_value=(Path("/tmp/case"), Path("/tmp/case/triSurface/x.stl")),
    ), patch.object(
        pipeline_mod, "run_gmsh_on_imported_case", side_effect=_spy_runner,
    ), patch.object(
        pipeline_mod, "run_gmsh_to_foam", return_value=fake_foam_result,
    ):
        result = pipeline_mod.mesh_imported_case(
            "imported_TEST_pipeline_zones",
            mesh_mode="beginner",
            refinement_zones=zones,
        )

    assert captured["kwargs"]["refinement_zones"] is zones
    # Pure-zones run keeps the preset label, NOT "custom".
    assert result.mesh_mode == "beginner"


def test_pipeline_zones_combine_with_sizing_field_label_is_custom():
    """When BOTH sizing_field and refinement_zones are supplied, the
    mesh_mode_used label is "custom" (sizing_field active wins).
    """
    from ui.backend.schemas.mesh_sizing import MeshSizingField
    from ui.backend.services.meshing_gmsh import pipeline as pipeline_mod
    from ui.backend.services.meshing_gmsh.gmsh_runner import GmshRunResult

    fake_gmsh_result = GmshRunResult(
        msh_path=Path("/tmp/fake.msh"),
        cell_count=10_000,
        face_count=5_000,
        point_count=2_000,
        characteristic_length_used=0.05,
        generation_time_s=0.1,
    )
    fake_foam_result = type("F", (), {"polyMesh_dir": Path("/tmp/poly")})()

    with patch.object(
        pipeline_mod, "_resolve_imported_case",
        return_value=(Path("/tmp/case"), Path("/tmp/case/triSurface/x.stl")),
    ), patch.object(
        pipeline_mod, "run_gmsh_on_imported_case", return_value=fake_gmsh_result,
    ), patch.object(
        pipeline_mod, "run_gmsh_to_foam", return_value=fake_foam_result,
    ):
        result = pipeline_mod.mesh_imported_case(
            "imported_TEST_pipeline_combo",
            mesh_mode="beginner",
            sizing_field=MeshSizingField(base_lc=0.05),
            refinement_zones=[
                BoxRefinementZone(bbox=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0], level=1),
            ],
        )

    assert result.mesh_mode == "custom"
