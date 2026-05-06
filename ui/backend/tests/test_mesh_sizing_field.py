"""Unit + route tests for MeshSizingField (DEC-V61-135 · N2.1).

Covers:
* Schema validators (ordering, positivity, range).
* MeshRequest accepts ``sizing_field``.
* mesh_imported route plumbs ``sizing_field`` through to
  ``mesh_imported_case`` and labels the result mesh_mode "custom".
* Pipeline-layer ``effective_mode`` selection precedence.
* No envelope drift — V132 advisor contract still green (covered in
  test_ai_advisor_contract.py; we don't re-assert here).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ui.backend.main import app
from ui.backend.schemas.mesh_imported import MeshRequest
from ui.backend.schemas.mesh_sizing import MeshSizingField


client = TestClient(app)


# ---------------------- Schema validator tests ----------------------


def test_sizing_field_default_is_inactive():
    sf = MeshSizingField()
    assert sf.is_active() is False


def test_sizing_field_partial_field_makes_active():
    assert MeshSizingField(curvature_target_size=15).is_active() is True
    assert MeshSizingField(proximity_layers=4).is_active() is True
    assert MeshSizingField(base_lc=0.05).is_active() is True


def test_sizing_field_rejects_min_greater_than_max():
    with pytest.raises(ValidationError):
        MeshSizingField(min_lc=0.5, max_lc=0.1)


def test_sizing_field_rejects_min_greater_than_base():
    with pytest.raises(ValidationError):
        MeshSizingField(min_lc=0.5, base_lc=0.1)


def test_sizing_field_rejects_base_greater_than_max():
    with pytest.raises(ValidationError):
        MeshSizingField(base_lc=0.5, max_lc=0.1)


def test_sizing_field_rejects_zero_or_negative_lc():
    with pytest.raises(ValidationError):
        MeshSizingField(base_lc=0.0)
    with pytest.raises(ValidationError):
        MeshSizingField(min_lc=-0.01)


def test_sizing_field_clamps_proximity_layers_range():
    # Pydantic ge=1, le=10
    with pytest.raises(ValidationError):
        MeshSizingField(proximity_layers=0)
    with pytest.raises(ValidationError):
        MeshSizingField(proximity_layers=11)
    # Boundaries OK
    assert MeshSizingField(proximity_layers=1).proximity_layers == 1
    assert MeshSizingField(proximity_layers=10).proximity_layers == 10


def test_sizing_field_only_validates_supplied_pairs():
    # min_lc set without base_lc/max_lc is a valid call shape
    sf = MeshSizingField(min_lc=0.001)
    assert sf.is_active() is True


def test_mesh_request_default_has_no_sizing_field():
    r = MeshRequest()
    assert r.sizing_field is None


def test_mesh_request_accepts_sizing_field():
    r = MeshRequest(
        mesh_mode="beginner",
        sizing_field=MeshSizingField(base_lc=0.05, min_lc=0.005, max_lc=0.10),
    )
    assert r.sizing_field is not None
    assert r.sizing_field.base_lc == 0.05


# ---------------------- Pipeline effective_mode tests ----------------------


def test_pipeline_effective_mode_selection():
    """Verify the precedence: sizing_field > target/lc-override > preset.

    We don't run gmsh — we monkeypatch the inner function so the test
    exercises only the labeling logic.
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

    cases = [
        # (mesh_mode, target, lc_override, sf, expected_label)
        ("beginner", None, None, None, "beginner"),
        ("power", None, None, None, "power"),
        ("beginner", 100_000, None, None, "target"),
        ("beginner", None, 0.05, None, "target"),
        # sizing_field wins over preset
        ("beginner", None, None, MeshSizingField(base_lc=0.05), "custom"),
        # sizing_field wins even with target_cell_count set
        ("beginner", 100_000, None, MeshSizingField(curvature_target_size=20), "custom"),
        # inactive sizing_field falls through to target
        ("beginner", 100_000, None, MeshSizingField(), "target"),
    ]

    for mesh_mode, target, lc_override, sf, expected in cases:
        with patch.object(
            pipeline_mod, "_resolve_imported_case",
            return_value=(Path("/tmp/case"), Path("/tmp/case/triSurface/x.stl")),
        ), patch.object(
            pipeline_mod, "run_gmsh_on_imported_case", return_value=fake_gmsh_result,
        ), patch.object(
            pipeline_mod, "run_gmsh_to_foam", return_value=fake_foam_result,
        ):
            result = pipeline_mod.mesh_imported_case(
                "imported_TEST_emode",
                mesh_mode=mesh_mode,
                target_cell_count=target,
                characteristic_length_override=lc_override,
                sizing_field=sf,
            )
        assert result.mesh_mode == expected, (
            f"case={mesh_mode}/{target}/{lc_override}/{sf} → "
            f"expected {expected}, got {result.mesh_mode}"
        )


# ---------------------- Route-level test ----------------------


def test_mesh_route_accepts_sizing_field_body(tmp_path: Path):
    """POST body with sizing_field is forwarded to pipeline; response
    reports mesh_mode_used="custom"."""
    from ui.backend.services.meshing_gmsh.pipeline import MeshResult
    from ui.backend.routes import mesh_imported as route_mod

    fake = MeshResult(
        case_id="imported_TEST_sizing",
        mesh_mode="custom",
        cell_count=33_333,
        face_count=12_222,
        point_count=6_111,
        polyMesh_path=tmp_path / "constant" / "polyMesh",
        msh_path=tmp_path / "imported.msh",
        generation_time_s=2.34,
        warning=None,
    )

    captured: dict = {}

    def _spy(case_id: str, **kwargs):
        captured["case_id"] = case_id
        captured["kwargs"] = kwargs
        return fake

    with patch.object(route_mod, "mesh_imported_case", side_effect=_spy):
        response = client.post(
            "/api/import/imported_TEST_sizing/mesh",
            json={
                "mesh_mode": "beginner",
                "sizing_field": {
                    "base_lc": 0.05,
                    "min_lc": 0.005,
                    "max_lc": 0.10,
                    "curvature_target_size": 20,
                    "proximity_layers": 4,
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mesh_summary"]["mesh_mode_used"] == "custom"
    # Pipeline received the sizing_field
    sf = captured["kwargs"]["sizing_field"]
    assert sf is not None
    assert sf.base_lc == 0.05
    assert sf.proximity_layers == 4


def test_mesh_route_rejects_bogus_sizing_field():
    response = client.post(
        "/api/import/anything/mesh",
        json={
            "mesh_mode": "beginner",
            "sizing_field": {"min_lc": 0.5, "max_lc": 0.1},
        },
    )
    assert response.status_code == 422


def _stub_gmsh_module():
    """Install a MagicMock as ``gmsh`` so _gmsh_inline can import +
    drive the sizing-field branch without the [workbench] extra."""
    import sys
    from unittest.mock import MagicMock
    from numpy import array  # gmsh.model.mesh.getNodes shape: (tags, coords, ...)

    fake = MagicMock()
    fake.model.getEntities.return_value = [(2, 1)]
    # Real signature: returns (nodeTags, coords, parametricCoords). The
    # production code reshapes coords to (-1, 3) then iterates as floats;
    # supply 2 distinct points so _bbox_diagonal > 0 and the preset
    # fallback gives lc=diagonal/30 ≈ 0.0577.
    fake.model.mesh.getNodes.return_value = (
        array([1, 2]),
        array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0]),
        [],
    )
    sys.modules["gmsh"] = fake
    return fake


def test_one_sided_max_lc_below_preset_min_is_rejected(tmp_path):
    """Codex R0 P2 #1: when base_lc is omitted and only max_lc is set,
    the missing min_lc gets derived from preset fallback (lc * 0.5).
    If max_lc is below that derived min, gmsh would receive an
    inverted range. The runtime check inside _gmsh_inline must raise
    GmshMeshGenerationError before gmsh.generate(3) is invoked.
    """
    import sys
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        GmshMeshGenerationError,
    )

    stl = tmp_path / "x.stl"
    stl.write_bytes(b"solid\nendsolid\n")
    out = tmp_path / "x.msh"

    _stub_gmsh_module()
    try:
        with pytest.raises(GmshMeshGenerationError, match="inverted"):
            runner_mod._gmsh_inline(
                stl_path=stl,
                output_msh_path=out,
                mesh_mode="beginner",
                characteristic_length_override=None,
                target_cell_count=None,
                sizing_field={
                    "base_lc": None,
                    "min_lc": None,
                    "max_lc": 0.001,  # below derived min ≈ 0.029
                    "curvature_target_size": None,
                    "proximity_layers": None,
                },
            )
    finally:
        sys.modules.pop("gmsh", None)


def test_one_sided_min_lc_above_preset_max_is_rejected(tmp_path):
    """Symmetric to the test above: only min_lc set, derived max_lc =
    preset lc < supplied min_lc → inversion."""
    import sys
    from ui.backend.services.meshing_gmsh import gmsh_runner as runner_mod
    from ui.backend.services.meshing_gmsh.gmsh_runner import (
        GmshMeshGenerationError,
    )

    stl = tmp_path / "x.stl"
    stl.write_bytes(b"solid\nendsolid\n")
    out = tmp_path / "x.msh"

    _stub_gmsh_module()
    try:
        with pytest.raises(GmshMeshGenerationError, match="inverted"):
            runner_mod._gmsh_inline(
                stl_path=stl,
                output_msh_path=out,
                mesh_mode="beginner",
                characteristic_length_override=None,
                target_cell_count=None,
                # min_lc=10.0 forces inversion: derived lc_max ≈ 0.058
                sizing_field={
                    "base_lc": None,
                    "min_lc": 10.0,
                    "max_lc": None,
                    "curvature_target_size": None,
                    "proximity_layers": None,
                },
            )
    finally:
        sys.modules.pop("gmsh", None)


def test_mesh_route_default_omits_sizing_field():
    """Sanity: omitting sizing_field uses None default and reaches
    pipeline as None (back-compat with all V124/V125-era callers)."""
    from ui.backend.services.meshing_gmsh.pipeline import MeshResult
    from ui.backend.routes import mesh_imported as route_mod

    fake = MeshResult(
        case_id="imported_TEST_nosf",
        mesh_mode="beginner",
        cell_count=10_000, face_count=5_000, point_count=2_000,
        polyMesh_path=Path("/tmp/poly"), msh_path=Path("/tmp/x.msh"),
        generation_time_s=0.1, warning=None,
    )
    captured: dict = {}

    def _spy(case_id: str, **kwargs):
        captured["kwargs"] = kwargs
        return fake

    with patch.object(route_mod, "mesh_imported_case", side_effect=_spy):
        response = client.post(
            "/api/import/imported_TEST_nosf/mesh",
            json={"mesh_mode": "beginner"},
        )

    assert response.status_code == 200
    assert captured["kwargs"]["sizing_field"] is None
