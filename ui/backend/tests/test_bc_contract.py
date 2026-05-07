"""DEC-V61-146 (N4.1) · BCContract schema + writer + route tests.

Coverage:
  * Per-BC-type config validators (charset, positivity, vector arity)
  * Discriminated-union dispatch on bc_type literal
  * BCContract patch-name charset, cyclic pairing invariants
  * Writer renders correct U + p block for every BC type
  * Atomic write behavior (overwrite + no temp leftovers)
  * V132 registry membership (HTTP surface + Python symbol)
  * Route 200 / 400 / 404 / 422 paths
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ui.backend.schemas.bc_contract import (
    BCContract,
    CyclicBC,
    EmptyBC,
    InletOutletBC,
    MassFlowInletBC,
    MovingWallBC,
    NoSlipWallBC,
    PressureOutletBC,
    SymmetryBC,
    VelocityInletBC,
    VolumetricFlowInletBC,
)
from ui.backend.services.case_bc.writer import (
    render_p_field,
    render_u_field,
    write_bc_dicts,
)


def _trivial_contract(**overrides) -> BCContract:
    patches = {
        "inlet": VelocityInletBC(velocity=(1.0, 0.0, 0.0)),
        "outlet": PressureOutletBC(),
        "walls": NoSlipWallBC(),
    }
    patches.update(overrides.pop("patches", {}))
    return BCContract(
        patches=patches,
        authored_at="2026-05-07T12:00:00Z",
        **overrides,
    )


# ────────── Per-BC-type validators ──────────


def test_velocity_inlet_requires_velocity_vector():
    VelocityInletBC(velocity=(1.0, 0.0, 0.0))
    with pytest.raises(ValidationError):
        VelocityInletBC()  # missing velocity


def test_volumetric_flow_inlet_must_be_positive():
    VolumetricFlowInletBC(volumetric_flow_rate=0.001)
    with pytest.raises(ValidationError):
        VolumetricFlowInletBC(volumetric_flow_rate=0.0)
    with pytest.raises(ValidationError):
        VolumetricFlowInletBC(volumetric_flow_rate=-0.001)


def test_mass_flow_inlet_must_be_positive():
    MassFlowInletBC(mass_flow_rate=0.5)
    with pytest.raises(ValidationError):
        MassFlowInletBC(mass_flow_rate=0.0)


def test_pressure_outlet_default_zero_gauge():
    bc = PressureOutletBC()
    assert bc.gauge_pressure == 0.0
    bc2 = PressureOutletBC(gauge_pressure=101325.0)
    assert bc2.gauge_pressure == 101325.0


def test_inlet_outlet_default_zero_gauge():
    bc = InletOutletBC()
    assert bc.gauge_pressure == 0.0


def test_moving_wall_requires_velocity():
    MovingWallBC(velocity=(1.0, 0.0, 0.0))
    with pytest.raises(ValidationError):
        MovingWallBC()


def test_cyclic_requires_paired_patch_name():
    CyclicBC(paired_patch="periodic_back")
    with pytest.raises(ValidationError):
        CyclicBC(paired_patch="")  # empty
    with pytest.raises(ValidationError):
        CyclicBC()  # missing


def test_no_slip_and_symmetry_and_empty_have_no_extra_fields():
    NoSlipWallBC()
    SymmetryBC()
    EmptyBC()


def test_extra_keys_forbidden_on_every_bc_type():
    for cls, kwargs in [
        (VelocityInletBC, {"velocity": (1.0, 0.0, 0.0)}),
        (NoSlipWallBC, {}),
        (PressureOutletBC, {}),
    ]:
        with pytest.raises(ValidationError):
            cls(mystery="oops", **kwargs)


# ────────── BCContract validators ──────────


def test_contract_requires_at_least_one_patch():
    with pytest.raises(ValidationError):
        BCContract(patches={}, authored_at="2026-05-07T12:00:00Z")


def test_contract_patch_name_charset():
    for name in ["my patch", "my/patch", "my%patch", "my!patch"]:
        with pytest.raises(ValidationError):
            BCContract(
                patches={name: NoSlipWallBC()},
                authored_at="2026-05-07T12:00:00Z",
            )


def test_contract_patch_name_allows_alnum_underscore_hyphen_dot():
    for name in ["inlet", "wall_1", "patch-A", "domain.0", "abc_def-1.0"]:
        BCContract(
            patches={name: NoSlipWallBC()},
            authored_at="2026-05-07T12:00:00Z",
        )


def test_contract_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        BCContract(
            patches={"x": NoSlipWallBC()},
            authored_at="2026-05-07T12:00:00Z",
            mystery="oops",
        )


def test_contract_cyclic_must_pair_with_existing_patch():
    with pytest.raises(ValidationError) as exc_info:
        BCContract(
            patches={"front": CyclicBC(paired_patch="back")},
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "not in patches dict" in str(exc_info.value)


def test_contract_cyclic_pair_must_also_be_cyclic():
    with pytest.raises(ValidationError) as exc_info:
        BCContract(
            patches={
                "front": CyclicBC(paired_patch="back"),
                "back": NoSlipWallBC(),  # wrong type
            },
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "must also be cyclic" in str(exc_info.value)


def test_contract_cyclic_must_be_bidirectional():
    with pytest.raises(ValidationError) as exc_info:
        BCContract(
            patches={
                "front": CyclicBC(paired_patch="back"),
                "back": CyclicBC(paired_patch="other"),
                "other": CyclicBC(paired_patch="back"),
            },
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "not bidirectional" in str(exc_info.value)


def test_contract_cyclic_valid_bidirectional_pair():
    BCContract(
        patches={
            "front": CyclicBC(paired_patch="back"),
            "back": CyclicBC(paired_patch="front"),
            "walls": NoSlipWallBC(),
        },
        authored_at="2026-05-07T12:00:00Z",
    )


# ────────── Writer ──────────


def test_render_u_field_has_header_and_boundary_block():
    text = render_u_field(_trivial_contract())
    assert "volVectorField" in text
    assert "[0 1 -1 0 0 0 0]" in text
    assert "boundaryField" in text
    # Each patch appears.
    assert "    inlet" in text
    assert "    outlet" in text
    assert "    walls" in text


def test_render_p_field_has_header_and_boundary_block():
    text = render_p_field(_trivial_contract())
    assert "volScalarField" in text
    assert "[0 2 -2 0 0 0 0]" in text
    assert "boundaryField" in text


def test_render_velocity_inlet_emits_fixedValue():
    text = render_u_field(
        BCContract(
            patches={"inlet": VelocityInletBC(velocity=(2.5, 0.0, 0.0))},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "fixedValue" in text
    assert "(2.5 0 0)" in text


def test_render_volumetric_flow_inlet_emits_flowRateInletVelocity():
    text = render_u_field(
        BCContract(
            patches={"inlet": VolumetricFlowInletBC(volumetric_flow_rate=0.005)},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "flowRateInletVelocity" in text
    assert "volumetricFlowRate" in text
    assert "0.005" in text
    assert "extrapolateProfile yes" in text


def test_render_mass_flow_inlet_emits_massFlowRate_and_rho():
    text = render_u_field(
        BCContract(
            patches={"inlet": MassFlowInletBC(mass_flow_rate=2.0)},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "massFlowRate" in text
    assert "rho             rho" in text


def test_render_pressure_outlet_p_emits_fixedValue():
    text = render_p_field(
        BCContract(
            patches={"outlet": PressureOutletBC(gauge_pressure=101325.0)},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "fixedValue" in text
    assert "101325" in text


def test_render_inlet_outlet_emits_pressureInletOutletVelocity():
    text = render_u_field(
        BCContract(
            patches={"outlet": InletOutletBC()},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "pressureInletOutletVelocity" in text


def test_render_no_slip_wall_emits_zero_velocity():
    text = render_u_field(
        BCContract(
            patches={"walls": NoSlipWallBC()},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "fixedValue" in text
    assert "(0 0 0)" in text


def test_render_moving_wall_emits_lid_velocity():
    text = render_u_field(
        BCContract(
            patches={"lid": MovingWallBC(velocity=(1.0, 0.0, 0.0))},
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "(1.0 0 0)" in text


def test_render_symmetry_cyclic_empty_branches():
    text_u = render_u_field(
        BCContract(
            patches={
                "sym": SymmetryBC(),
                "f": CyclicBC(paired_patch="b"),
                "b": CyclicBC(paired_patch="f"),
                "front": EmptyBC(),
            },
            authored_at="2026-05-07T12:00:00Z",
        )
    )
    assert "type            symmetry;" in text_u
    assert "type            cyclic;" in text_u
    assert "type            empty;" in text_u


# ────────── write_bc_dicts ──────────


def test_write_creates_zero_orig_and_files(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    case_dir.mkdir()
    written = write_bc_dicts(case_dir, contract=_trivial_contract())
    assert (case_dir / "0.orig" / "U").is_file()
    assert (case_dir / "0.orig" / "p").is_file()
    assert "0.orig/U" in written
    assert "0.orig/p" in written


def test_write_overwrites_atomically(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    (case_dir / "0.orig").mkdir(parents=True)
    (case_dir / "0.orig" / "U").write_text("STALE\n")
    write_bc_dicts(case_dir, contract=_trivial_contract())
    text = (case_dir / "0.orig" / "U").read_text()
    assert "STALE" not in text
    assert "boundaryField" in text


def test_write_no_temp_files_remain(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    case_dir.mkdir()
    write_bc_dicts(case_dir, contract=_trivial_contract())
    leftovers = list((case_dir / "0.orig").glob(".*.tmp"))
    assert leftovers == []


def test_write_missing_case_dir_raises(tmp_path: Path):
    case_dir = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        write_bc_dicts(case_dir, contract=_trivial_contract())


# ────────── V132 registry ──────────


def test_v132_registry_includes_bc_route():
    from ui.backend.services.ai_actions.mutating_routes import (
        MUTATING_ROUTES,
        is_mutating_route,
    )

    assert ("POST", "/api/cases/{case_id}/bc-contract") in MUTATING_ROUTES
    assert is_mutating_route(
        "POST", "/api/cases/imported_2026-05-07T12-00-00Z_abc/bc-contract"
    )


def test_v132_registry_includes_writer_function():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    assert (
        "ui.backend.services.case_bc.writer",
        "write_bc_dicts",
    ) in KNOWN_MUTATION_FUNCTIONS
    assert (
        "ui.backend.services.case_bc",
        "write_bc_dicts",
    ) in KNOWN_MUTATION_FUNCTIONS


# ────────── Route ──────────


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "ui.backend.routes.case_bc.IMPORTED_DIR", tmp_path
    )
    from ui.backend.main import app

    return TestClient(app)


def test_route_200_writes_dicts(client, tmp_path: Path):
    case_dir = tmp_path / "imported_ok"
    case_dir.mkdir()
    response = client.post(
        "/api/cases/imported_ok/bc-contract",
        json=_trivial_contract().model_dump(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["case_id"] == "imported_ok"
    assert body["patch_count"] == 3
    assert "0.orig/U" in body["written_paths"]
    assert "0.orig/p" in body["written_paths"]
    on_disk_u = (case_dir / "0.orig" / "U").read_text()
    assert on_disk_u == body["dict_texts"]["0.orig/U"]


def test_route_404_on_missing_case(client):
    response = client.post(
        "/api/cases/case_does_not_exist/bc-contract",
        json=_trivial_contract().model_dump(),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["failing_check"] == "case_not_found"


def test_route_400_on_unsafe_case_id(client):
    response = client.post(
        "/api/cases/..%2Fevil/bc-contract",
        json=_trivial_contract().model_dump(),
    )
    assert response.status_code in (400, 404, 422)


def test_route_422_on_invalid_contract(client, tmp_path: Path):
    case_dir = tmp_path / "imported_ok"
    case_dir.mkdir()
    response = client.post(
        "/api/cases/imported_ok/bc-contract",
        json={
            "patches": {
                "inlet": {
                    "bc_type": "volumetric_flow_inlet",
                    "volumetric_flow_rate": -1.0,  # invalid
                },
            },
            "authored_at": "2026-05-07T12:00:00Z",
        },
    )
    assert response.status_code == 422


def test_route_422_on_cyclic_pair_mismatch(client, tmp_path: Path):
    case_dir = tmp_path / "imported_ok"
    case_dir.mkdir()
    response = client.post(
        "/api/cases/imported_ok/bc-contract",
        json={
            "patches": {
                "front": {"bc_type": "cyclic", "paired_patch": "back"},
                "back": {"bc_type": "no_slip_wall"},  # not cyclic — invariant fails
            },
            "authored_at": "2026-05-07T12:00:00Z",
        },
    )
    assert response.status_code == 422
