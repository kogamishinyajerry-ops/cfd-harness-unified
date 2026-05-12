"""Unit + route + contract tests for snappyHexMesh prism layers
(DEC-V61-137 · N2.3).

Covers:
* Schema validators (single-patch v0 cap, layer-count bounds,
  expansion-ratio bounds, patch-name charset, positive
  first_cell_height)
* addlayers_renderer dict format basic shape
* Pipeline error mapping (SnappyAddLayersError → user 422 vs
  SnappyContainerError → 502)
* Boundary patch-name parsing (snappy_runner._read_boundary_patch_names)
* Log parsing (snappy_runner._parse_addlayers_log)
* Route plumbs request through to apply_prism_layers + maps each
  failing_check to its HTTP status
* V132 contract surface: new mutating route + KNOWN_MUTATION_FUNCTIONS
  entries are picked up by test_ai_advisor_contract (verified
  separately in that file's test); we only assert the registry
  contents here.

We do NOT exercise the actual docker container — the snappy_runner is
covered with mocks at the boundary.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ui.backend.main import app
from ui.backend.schemas.mesh_prism_layers import (
    EXPANSION_RATIO_MAX,
    EXPANSION_RATIO_MIN,
    MAX_LAYER_COUNT,
    MeshPrismLayersRequest,
    PatchPrismConfig,
)
from ui.backend.services.ai_actions.mutating_routes import (
    KNOWN_MUTATION_FUNCTIONS,
    MUTATING_ROUTES,
    is_mutating_route,
)
from ui.backend.services.meshing_snappy.addlayers_renderer import (
    render_snappy_dict,
)


client = TestClient(app)


# ---------------------- Schema validator tests ----------------------


def test_patch_config_valid_shape():
    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    assert cfg.patch == "walls"
    assert cfg.num_layers == 5


def test_patch_config_rejects_zero_first_cell_height():
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="walls",
            first_cell_height=0.0,
            expansion_ratio=1.2,
            num_layers=5,
        )


def test_patch_config_rejects_negative_first_cell_height():
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="walls",
            first_cell_height=-1.0e-4,
            expansion_ratio=1.2,
            num_layers=5,
        )


@pytest.mark.parametrize(
    "ratio", [0.0, 0.5, 0.99, EXPANSION_RATIO_MAX + 0.01, 5.0]
)
def test_patch_config_rejects_expansion_ratio_out_of_bounds(ratio: float):
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="walls",
            first_cell_height=1.0e-4,
            expansion_ratio=ratio,
            num_layers=5,
        )


def test_patch_config_accepts_expansion_ratio_at_bounds():
    PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=EXPANSION_RATIO_MIN,
        num_layers=5,
    )
    PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=EXPANSION_RATIO_MAX,
        num_layers=5,
    )


@pytest.mark.parametrize("layers", [0, -1, MAX_LAYER_COUNT + 1, 999])
def test_patch_config_rejects_num_layers_out_of_bounds(layers: int):
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="walls",
            first_cell_height=1.0e-4,
            expansion_ratio=1.2,
            num_layers=layers,
        )


def test_patch_config_rejects_shell_injection_charset():
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="walls; rm -rf /",
            first_cell_height=1.0e-4,
            expansion_ratio=1.2,
            num_layers=5,
        )


def test_patch_config_rejects_empty_patch_name():
    with pytest.raises(ValidationError):
        PatchPrismConfig(
            patch="",
            first_cell_height=1.0e-4,
            expansion_ratio=1.2,
            num_layers=5,
        )


def test_request_v0_rejects_zero_patches():
    with pytest.raises(ValidationError):
        MeshPrismLayersRequest(patches=[])


def test_request_v0_rejects_multiple_patches():
    cfg_a = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    cfg_b = PatchPrismConfig(
        patch="airfoil",
        first_cell_height=5.0e-5,
        expansion_ratio=1.15,
        num_layers=8,
    )
    with pytest.raises(ValidationError) as exc_info:
        MeshPrismLayersRequest(patches=[cfg_a, cfg_b])
    assert "exactly one patch" in str(exc_info.value)


def test_request_v0_accepts_single_patch():
    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    req = MeshPrismLayersRequest(patches=[cfg])
    assert len(req.patches) == 1


# ---------------------- addlayers_renderer tests ----------------------


def test_render_snappy_dict_includes_patch_name_and_params():
    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    text = render_snappy_dict([cfg])
    assert "addLayers       true;" in text
    assert "castellatedMesh false;" in text
    assert "snap            false;" in text
    assert "\"walls\"" in text
    assert "nSurfaceLayers 5;" in text
    assert "expansionRatio 1.2" in text


def test_render_snappy_dict_renders_small_first_layer_height_in_scientific():
    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-6,
        expansion_ratio=1.2,
        num_layers=3,
    )
    text = render_snappy_dict([cfg])
    # 1e-6 is below the fixed-point cutoff in _render_float; expect
    # scientific notation.
    assert "1.000000e-06" in text or "1e-06" in text


def test_render_snappy_dict_min_thickness_is_half_first_layer():
    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=2.0e-4,
        expansion_ratio=1.2,
        num_layers=3,
    )
    text = render_snappy_dict([cfg])
    # min_thickness = 2.0e-4 * 0.5 = 1.0e-4. Scientific format kicks
    # in below 1e-3 (per _render_float), producing "1.000000e-04".
    assert "minThickness 1.000000e-04" in text


# ---------------------- snappy_runner helpers ---------------------


def test_read_boundary_patch_names_typical(tmp_path: Path):
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _read_boundary_patch_names,
    )

    polyMesh = tmp_path / "constant" / "polyMesh"
    polyMesh.mkdir(parents=True)
    (polyMesh / "boundary").write_text(
        """
FoamFile
{
    version 2.0;
    class polyBoundaryMesh;
    object boundary;
}
3
(
    walls
    {
        type wall;
        nFaces 100;
    }
    inlet
    {
        type patch;
        nFaces 25;
    }
    outlet
    {
        type patch;
        nFaces 25;
    }
)
""",
        encoding="utf-8",
    )
    names = _read_boundary_patch_names(polyMesh)
    assert names == {"walls", "inlet", "outlet"}


def test_read_boundary_patch_names_returns_empty_when_missing(tmp_path: Path):
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _read_boundary_patch_names,
    )

    assert _read_boundary_patch_names(tmp_path / "polyMesh") == set()


def test_parse_addlayers_log_extracts_layers_and_coverage():
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = """
... lots of text ...
Overall layer coverage: 84.5 %
Layers added: 5
... more text ...
"""
    layers, coverage, definite_zero = _parse_addlayers_log(log)
    assert layers == 5
    assert coverage == pytest.approx(0.845)
    assert definite_zero is False


def test_parse_addlayers_log_falls_back_to_iteration_count():
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = """
Layer addition iteration 1
Layer addition iteration 2
Layer addition iteration 3
"""
    layers, coverage, definite_zero = _parse_addlayers_log(log)
    assert layers == 3
    assert coverage is None
    # Iteration-count fallback is not a strong "no layers" signal.
    assert definite_zero is False


def test_parse_addlayers_log_unparseable_returns_none_none_false():
    """R0 P1 (Codex 86gs): unparseable log no longer maps to layers=0;
    layers is None so the caller can distinguish "log silent" from
    "log says zero".
    """
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    layers, coverage, definite_zero = _parse_addlayers_log(
        "(garbage with no markers)"
    )
    assert layers is None
    assert coverage is None
    assert definite_zero is False


def test_parse_addlayers_log_explicit_zero_marks_definite_zero():
    """R0 P1 (Codex 86gs): the strong "0 layers added" signal is the
    only thing that triggers SnappyAddLayersError now.
    """
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = """
Doing final balancing
Layers added: 0
"""
    layers, coverage, definite_zero = _parse_addlayers_log(log)
    assert layers == 0
    assert definite_zero is True


def test_parse_addlayers_log_per_patch_summary_zeros_definite():
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = """
Per-patch summary:
   walls: 5 layers requested, 0 layers added
"""
    layers, coverage, definite_zero = _parse_addlayers_log(log)
    assert layers == 0
    assert definite_zero is True


def test_parse_addlayers_log_small_percent_coverage_normalizes():
    """R0 P2 (Codex 86gs): "0.8 %" is 0.008, not 0.8."""
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = "Overall layer coverage: 0.8 %\nLayers added: 1\n"
    _, coverage, _ = _parse_addlayers_log(log)
    assert coverage == pytest.approx(0.008)


def test_parse_addlayers_log_fraction_coverage_no_percent():
    """When the log already reports a [0, 1] fraction (no % suffix),
    do NOT divide.
    """
    from ui.backend.services.meshing_snappy.snappy_runner import (
        _parse_addlayers_log,
    )

    log = "Overall layer coverage: 0.92\nLayers added: 5\n"
    _, coverage, _ = _parse_addlayers_log(log)
    assert coverage == pytest.approx(0.92)


# ---------------------- Pipeline tests ----------------------


def test_pipeline_polymesh_not_ready_maps_to_check(tmp_path: Path):
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod
    from ui.backend.services.meshing_snappy.snappy_runner import (
        SnappyAddLayersError,
    )

    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )

    case_dir = tmp_path / "imported_TEST_no_polymesh"
    case_dir.mkdir(parents=True)

    with patch.object(
        pipeline_mod, "_resolve_imported_case", return_value=case_dir
    ), patch.object(
        pipeline_mod,
        "run_snappy_addlayers",
        side_effect=SnappyAddLayersError(
            "polyMesh not ready under .../polyMesh — run the gmsh stage first."
        ),
    ):
        with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
            pipeline_mod.apply_prism_layers(
                "imported_TEST_no_polymesh", patches=[cfg]
            )
    assert exc_info.value.failing_check == "polyMesh_not_ready"


def test_pipeline_patch_not_found_maps_to_check(tmp_path: Path):
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod
    from ui.backend.services.meshing_snappy.snappy_runner import (
        SnappyAddLayersError,
    )

    cfg = PatchPrismConfig(
        patch="airfoil",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    case_dir = tmp_path / "imported_TEST_patch_missing"
    case_dir.mkdir(parents=True)

    with patch.object(
        pipeline_mod, "_resolve_imported_case", return_value=case_dir
    ), patch.object(
        pipeline_mod,
        "run_snappy_addlayers",
        side_effect=SnappyAddLayersError(
            "patch(es) ['airfoil'] not present in .../boundary — declared patches are ['walls']."
        ),
    ):
        with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
            pipeline_mod.apply_prism_layers(
                "imported_TEST_patch_missing", patches=[cfg]
            )
    assert exc_info.value.failing_check == "patch_not_found"


def test_pipeline_addlayers_did_not_converge_maps_to_check(tmp_path: Path):
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod
    from ui.backend.services.meshing_snappy.snappy_runner import (
        SnappyAddLayersError,
    )

    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    case_dir = tmp_path / "imported_TEST_no_converge"
    case_dir.mkdir(parents=True)

    with patch.object(
        pipeline_mod, "_resolve_imported_case", return_value=case_dir
    ), patch.object(
        pipeline_mod,
        "run_snappy_addlayers",
        side_effect=SnappyAddLayersError(
            "snappyHexMesh exit_code=0 but no layers were actually added (parsed addLayers log shows 0)."
        ),
    ):
        with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
            pipeline_mod.apply_prism_layers(
                "imported_TEST_no_converge", patches=[cfg]
            )
    assert exc_info.value.failing_check == "snappy_addlayers_did_not_converge"


def test_pipeline_container_error_maps_to_502_check(tmp_path: Path):
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod
    from ui.backend.services.meshing_snappy.snappy_runner import (
        SnappyContainerError,
    )

    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    case_dir = tmp_path / "imported_TEST_container"
    case_dir.mkdir(parents=True)

    with patch.object(
        pipeline_mod, "_resolve_imported_case", return_value=case_dir
    ), patch.object(
        pipeline_mod,
        "run_snappy_addlayers",
        side_effect=SnappyContainerError("docker is not running"),
    ):
        with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
            pipeline_mod.apply_prism_layers(
                "imported_TEST_container", patches=[cfg]
            )
    assert exc_info.value.failing_check == "snappy_container_failed"


def test_pipeline_unknown_addlayers_msg_falls_back_to_snappy_diverged(tmp_path: Path):
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod
    from ui.backend.services.meshing_snappy.snappy_runner import (
        SnappyAddLayersError,
    )

    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    case_dir = tmp_path / "imported_TEST_generic"
    case_dir.mkdir(parents=True)

    with patch.object(
        pipeline_mod, "_resolve_imported_case", return_value=case_dir
    ), patch.object(
        pipeline_mod,
        "run_snappy_addlayers",
        side_effect=SnappyAddLayersError("snappyHexMesh exit_code=1; (some other failure)"),
    ):
        with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
            pipeline_mod.apply_prism_layers(
                "imported_TEST_generic", patches=[cfg]
            )
    assert exc_info.value.failing_check == "snappy_diverged"


def test_pipeline_unsafe_case_id_rejects():
    from ui.backend.services.meshing_snappy import pipeline as pipeline_mod

    cfg = PatchPrismConfig(
        patch="walls",
        first_cell_height=1.0e-4,
        expansion_ratio=1.2,
        num_layers=5,
    )
    with pytest.raises(pipeline_mod.PrismLayersPipelineError) as exc_info:
        pipeline_mod.apply_prism_layers("../etc/passwd", patches=[cfg])
    assert exc_info.value.failing_check == "case_not_found"


# ---------------------- Route tests ----------------------


def test_mesh_prism_route_happy_path_returns_summary(tmp_path: Path):
    from ui.backend.routes import mesh_prism_layers as route_mod
    from ui.backend.services.meshing_snappy.pipeline import PrismLayersResult

    fake = PrismLayersResult(
        case_id="imported_TEST_prism_ok",
        polyMesh_path=tmp_path / "constant" / "polyMesh",
        log_path=tmp_path / "log.snappyHexMesh",
        layers_added=5,
        coverage_fraction=0.92,
        generation_time_s=12.34,
    )

    captured: dict = {}

    def _spy(case_id: str, **kwargs):
        captured["case_id"] = case_id
        captured["kwargs"] = kwargs
        return fake

    with patch.object(route_mod, "apply_prism_layers", side_effect=_spy):
        response = client.post(
            "/api/import/imported_TEST_prism_ok/mesh/prism-layers",
            json={
                "patches": [
                    {
                        "patch": "walls",
                        "first_cell_height": 1.0e-4,
                        "expansion_ratio": 1.2,
                        "num_layers": 5,
                    }
                ]
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    summary = body["prism_summary"]
    assert summary["layers_added"] == 5
    assert summary["coverage_fraction"] == 0.92
    # Pipeline received the parsed PatchPrismConfig.
    assert len(captured["kwargs"]["patches"]) == 1
    assert captured["kwargs"]["patches"][0].patch == "walls"


@pytest.mark.parametrize(
    "failing_check, expected_status",
    [
        ("polyMesh_not_ready", 422),
        ("patch_not_found", 422),
        ("snappy_diverged", 422),
        ("snappy_addlayers_did_not_converge", 422),
        ("snappy_container_failed", 502),
    ],
)
def test_mesh_prism_route_translates_each_failing_check(
    failing_check: str, expected_status: int
):
    from ui.backend.routes import mesh_prism_layers as route_mod
    from ui.backend.services.meshing_snappy.pipeline import (
        PrismLayersPipelineError,
    )

    def _raise(case_id: str, **kwargs):
        raise PrismLayersPipelineError(
            f"synthetic message for {failing_check}", failing_check  # type: ignore[arg-type]
        )

    with patch.object(route_mod, "apply_prism_layers", side_effect=_raise):
        response = client.post(
            "/api/import/imported_TEST_fail/mesh/prism-layers",
            json={
                "patches": [
                    {
                        "patch": "walls",
                        "first_cell_height": 1.0e-4,
                        "expansion_ratio": 1.2,
                        "num_layers": 5,
                    }
                ]
            },
        )
    assert response.status_code == expected_status, response.text
    detail = response.json()["detail"]
    assert detail["failing_check"] == failing_check


def test_mesh_prism_route_rejects_zero_patches_at_schema():
    response = client.post(
        "/api/import/imported_TEST_empty/mesh/prism-layers",
        json={"patches": []},
    )
    assert response.status_code == 422


def test_mesh_prism_route_rejects_bogus_expansion_ratio():
    response = client.post(
        "/api/import/imported_TEST_bogus/mesh/prism-layers",
        json={
            "patches": [
                {
                    "patch": "walls",
                    "first_cell_height": 1.0e-4,
                    "expansion_ratio": 5.0,  # > 2.0
                    "num_layers": 5,
                }
            ]
        },
    )
    assert response.status_code == 422


def test_mesh_prism_route_rejects_shell_injection_patch_name():
    response = client.post(
        "/api/import/imported_TEST_shell/mesh/prism-layers",
        json={
            "patches": [
                {
                    "patch": "walls; rm -rf /",
                    "first_cell_height": 1.0e-4,
                    "expansion_ratio": 1.2,
                    "num_layers": 5,
                }
            ]
        },
    )
    assert response.status_code == 422


# ---------------------- V132 contract surface tests ----------------------


def test_prism_route_is_in_mutating_routes_registry():
    """V132 contract surface: the new POST endpoint must be registered
    so AI dispatch paths cannot call it.
    """
    target = ("POST", "/api/import/{case_id}/mesh/prism-layers")
    assert target in MUTATING_ROUTES


def test_apply_prism_layers_is_in_known_mutation_functions():
    """V132 contract surface: the pipeline function must be registered
    in BOTH module paths (the test_ai_advisor_contract Layer-A
    sentinel patches both forms).
    """
    expected = {
        ("ui.backend.services.meshing_snappy.pipeline", "apply_prism_layers"),
        ("ui.backend.services.meshing_snappy", "apply_prism_layers"),
    }
    assert expected.issubset(KNOWN_MUTATION_FUNCTIONS)


def test_is_mutating_route_recognizes_prism_endpoint():
    """is_mutating_route must classify a real-world prism-layers
    request as mutating, regardless of which case_id segment shape
    the engineer used (handles imported_*, hex, uuid, etc).
    """
    assert is_mutating_route(
        "POST", "/api/import/imported_2026-04-30T00-00-00Z_abc123/mesh/prism-layers"
    )
    assert is_mutating_route(
        "POST", "/api/import/some_other_case/mesh/prism-layers"
    )
    # Wrong method → not mutating
    assert not is_mutating_route(
        "GET", "/api/import/imported_x/mesh/prism-layers"
    )
    # Too-short path → not mutating
    assert not is_mutating_route(
        "POST", "/api/import/some_case/mesh"
    ) is False  # NB: /mesh IS mutating; this asserts the prism path is distinct
