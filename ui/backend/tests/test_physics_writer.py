"""DEC-V61-142 (N3.3) · physics writer + route tests.

Coverage:
  * render_physical_properties: laminar incompressible (no thermal),
    thermal block enabled, value formatting
  * render_momentum_transport: every RegimeKind branch
  * write_physics_dicts: atomic write (rename), constant/ missing
    raises, dict files exist after call
  * route: 200 happy path, 400 bad case_id, 404 case missing,
    422 case not scaffolded, V132 registry membership
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.schemas.material_contract import (
    FluidProperties,
    MaterialContract,
    ThermalProperties,
)
from ui.backend.schemas.regime_contract import (
    ApplicabilityBounds,
    RegimeContract,
)
from ui.backend.services.physics.writer import (
    render_momentum_transport,
    render_physical_properties,
    write_physics_dicts,
)


def _custom_material(
    *,
    with_thermal: bool = False,
    nu: float = 1.0e-6,
    rho: float = 998.0,
) -> MaterialContract:
    fluid = FluidProperties(
        name="custom",
        density=rho,
        kinematic_viscosity=nu,
        prandtl=7.0 if with_thermal else None,
    )
    thermal = (
        ThermalProperties(specific_heat=4184.0, thermal_conductivity=0.6)
        if with_thermal
        else None
    )
    return MaterialContract(
        kind="custom",
        fluid=fluid,
        thermal=thermal,
        authored_at="2026-05-07T12:00:00Z",
    )


def _regime(kind: str = "laminar") -> RegimeContract:
    return RegimeContract(
        kind="custom",
        regime=kind,  # type: ignore[arg-type]
        applicability=ApplicabilityBounds(),
        authored_at="2026-05-07T12:00:00Z",
    )


# ────────── render_physical_properties ──────────


def test_phys_isothermal_emits_nu_only_no_density_block():
    text = render_physical_properties(_custom_material(with_thermal=False))
    assert "transportModel  Newtonian;" in text
    assert "nu " in text and "[0 2 -1 0 0 0 0]" in text
    assert "rho " not in text  # isothermal path skips rho/cp/k
    assert "Cp " not in text
    assert "kappa " not in text
    assert "Pr " not in text


def test_phys_thermal_emits_full_block():
    text = render_physical_properties(_custom_material(with_thermal=True))
    assert "rho " in text and "[1 -3 0 0 0 0 0]" in text
    assert "Cp " in text and "[0 2 -2 -1 0 0 0]" in text
    assert "kappa " in text and "[1 1 -3 -1 0 0 0]" in text
    assert "Pr " in text


def test_phys_thermal_omits_pr_when_unset():
    """Thermal block + Pr=None → kappa emitted but Pr line omitted."""
    fluid = FluidProperties(name="custom", density=1.0, kinematic_viscosity=1e-6, prandtl=None)
    thermal = ThermalProperties(specific_heat=1000.0, thermal_conductivity=1.0)
    contract = MaterialContract(
        kind="custom",
        fluid=fluid,
        thermal=thermal,
        authored_at="2026-05-07T12:00:00Z",
    )
    text = render_physical_properties(contract)
    assert "kappa " in text
    assert "Pr " not in text


def test_phys_value_formatting_picks_readable_form():
    """ν=2e-4 (LDC default) → fixed-point; ν=1e-8 → scientific.
    Threshold matches _render_float (≥1e-4 fixed; below → scientific)."""
    text_fixed = render_physical_properties(_custom_material(nu=2.0e-4))
    assert "0.0002" in text_fixed
    text_sci = render_physical_properties(_custom_material(nu=1e-8))
    assert "1.000000e-08" in text_sci


# ────────── render_momentum_transport ──────────


def test_momentum_laminar():
    text = render_momentum_transport(_regime("laminar"))
    assert "simulationType laminar;" in text
    assert "RAS" not in text


def test_momentum_rans_ras_emits_kepsilon():
    text = render_momentum_transport(_regime("RANS-RAS"))
    assert "simulationType RAS;" in text
    assert "RASModel        kEpsilon;" in text
    assert "turbulence      on;" in text


def test_momentum_rans_komega_sst_emits_kOmegaSST():
    text = render_momentum_transport(_regime("RANS-kOmegaSST"))
    assert "simulationType RAS;" in text
    assert "RASModel        kOmegaSST;" in text


def test_momentum_les_stub_emits_todo_comment_and_laminar_fallback():
    text = render_momentum_transport(_regime("LES-stub"))
    assert "TODO(N3-extend)" in text
    assert "simulationType laminar;" in text
    # Engineer should see they need to hand-edit for a real LES dict.
    assert "LES" in text or "sub-grid" in text


def test_momentum_unknown_regime_raises():
    """Defensive branch: if RegimeKind grew without writer being
    updated, the writer must raise rather than emit silent garbage."""
    # Construct a regime contract with a literal not in the writer's
    # mapping by bypassing pydantic (simulating future-schema drift).
    class _FakeRegime:
        regime = "future-not-implemented"
    with pytest.raises(ValueError, match="unknown regime"):
        render_momentum_transport(_FakeRegime())  # type: ignore[arg-type]


# ────────── write_physics_dicts ──────────


def test_write_creates_both_dict_files(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    (case_dir / "constant").mkdir(parents=True)
    written = write_physics_dicts(
        case_dir,
        material=_custom_material(),
        regime=_regime("RANS-kOmegaSST"),
    )
    assert (case_dir / "constant" / "physicalProperties").is_file()
    assert (case_dir / "constant" / "momentumTransport").is_file()
    assert "constant/physicalProperties" in written
    assert "constant/momentumTransport" in written
    # Sanity: written text matches what render_* produced.
    on_disk = (case_dir / "constant" / "physicalProperties").read_text()
    assert on_disk == written["constant/physicalProperties"]


def test_write_missing_constant_raises(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    case_dir.mkdir()
    # No constant/ subdir.
    with pytest.raises(FileNotFoundError):
        write_physics_dicts(
            case_dir, material=_custom_material(), regime=_regime("laminar"),
        )


def test_write_overwrites_prior_dict_atomically(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    (case_dir / "constant").mkdir(parents=True)
    # Pre-existing dict.
    (case_dir / "constant" / "physicalProperties").write_text("STALE\n")
    write_physics_dicts(
        case_dir, material=_custom_material(), regime=_regime("laminar"),
    )
    text = (case_dir / "constant" / "physicalProperties").read_text()
    assert "STALE" not in text
    assert "Newtonian" in text


def test_write_no_temp_files_remain(tmp_path: Path):
    case_dir = tmp_path / "imported_test"
    (case_dir / "constant").mkdir(parents=True)
    write_physics_dicts(
        case_dir, material=_custom_material(), regime=_regime("laminar"),
    )
    # Atomic-write tempfiles use prefix='.<name>.' suffix='.tmp'.
    leftovers = list((case_dir / "constant").glob(".*.tmp"))
    assert leftovers == []


# ────────── V132 registry membership ──────────


def test_v132_registry_includes_physics_route():
    """Any AI dispatch path that tries to call POST /api/cases/{id}/physics
    must be caught by the V132 registry. Verify the route is listed."""
    from ui.backend.services.ai_actions.mutating_routes import (
        MUTATING_ROUTES,
        is_mutating_route,
    )

    assert ("POST", "/api/cases/{case_id}/physics") in MUTATING_ROUTES
    # Concrete instance check (case_id segment is normalized).
    assert is_mutating_route(
        "POST", "/api/cases/imported_2026-05-07T12-00-00Z_abc123/physics"
    )


def test_v132_registry_includes_writer_function():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    assert (
        "ui.backend.services.physics.writer",
        "write_physics_dicts",
    ) in KNOWN_MUTATION_FUNCTIONS
    assert (
        "ui.backend.services.physics",
        "write_physics_dicts",
    ) in KNOWN_MUTATION_FUNCTIONS


# ────────── Route ──────────


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """FastAPI TestClient with IMPORTED_DIR redirected to tmp_path."""
    monkeypatch.setattr(
        "ui.backend.routes.physics.IMPORTED_DIR", tmp_path
    )
    from ui.backend.main import app

    return TestClient(app)


def test_route_400_on_unsafe_case_id(client):
    response = client.post(
        "/api/cases/..%2Fevil/physics",
        json={
            "material": _custom_material().model_dump(),
            "regime": _regime("laminar").model_dump(),
        },
    )
    # Path-traversal probe: FastAPI may unescape and route reach;
    # is_safe_case_id catches '..' and slashes before disk touch.
    assert response.status_code in (400, 404, 422)


def test_route_404_on_missing_case(client):
    response = client.post(
        "/api/cases/case_does_not_exist/physics",
        json={
            "material": _custom_material().model_dump(),
            "regime": _regime("laminar").model_dump(),
        },
    )
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["failing_check"] == "case_not_found"


def test_route_422_when_constant_dir_missing(client, tmp_path: Path):
    case_dir = tmp_path / "imported_partial"
    case_dir.mkdir()
    # No constant/ subdir — case wasn't scaffolded.
    response = client.post(
        "/api/cases/imported_partial/physics",
        json={
            "material": _custom_material().model_dump(),
            "regime": _regime("laminar").model_dump(),
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["failing_check"] == "case_not_scaffolded"


def test_route_200_writes_dicts_and_echoes(client, tmp_path: Path):
    case_dir = tmp_path / "imported_ok"
    (case_dir / "constant").mkdir(parents=True)
    response = client.post(
        "/api/cases/imported_ok/physics",
        json={
            "material": _custom_material(with_thermal=True).model_dump(),
            "regime": _regime("RANS-kOmegaSST").model_dump(),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["case_id"] == "imported_ok"
    assert "constant/physicalProperties" in body["written_paths"]
    assert "constant/momentumTransport" in body["written_paths"]
    assert "Newtonian" in body["dict_texts"]["constant/physicalProperties"]
    assert "kOmegaSST" in body["dict_texts"]["constant/momentumTransport"]
    # On-disk verification.
    on_disk = (case_dir / "constant" / "momentumTransport").read_text()
    assert on_disk == body["dict_texts"]["constant/momentumTransport"]


def test_route_200_invalid_material_returns_422(client, tmp_path: Path):
    """Pydantic validation surfaces as FastAPI default 422."""
    case_dir = tmp_path / "imported_ok"
    (case_dir / "constant").mkdir(parents=True)
    response = client.post(
        "/api/cases/imported_ok/physics",
        json={
            "material": {
                "kind": "custom",
                "fluid": {
                    "name": "custom",
                    "density": -1.0,  # invalid: must be > 0
                    "kinematic_viscosity": 1e-6,
                },
                "authored_at": "2026-05-07T12:00:00Z",
            },
            "regime": _regime("laminar").model_dump(),
        },
    )
    assert response.status_code == 422
