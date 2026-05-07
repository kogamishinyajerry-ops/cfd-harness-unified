"""DEC-V61-140 (N3.1) · MaterialContract schema + preset library tests.

Coverage:
  * Schema field validators (positivity, length, charset)
  * Cross-field invariants (kind=preset → preset_id + citation required)
  * Preset library citation completeness (charter threat-model row 4)
  * Preset library uniqueness + lookup behavior
"""
from __future__ import annotations

import pytest
from pydantic import HttpUrl, ValidationError

from ui.backend.schemas.material_contract import (
    FluidProperties,
    MaterialContract,
    ThermalProperties,
)
from ui.backend.services.physics import (
    MATERIAL_PRESETS,
    get_material_preset,
    list_material_preset_ids,
)


# ────────── FluidProperties ──────────


def test_fluid_density_must_be_positive():
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=0.0, kinematic_viscosity=1e-6)
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=-1.0, kinematic_viscosity=1e-6)


def test_fluid_kinematic_viscosity_must_be_positive():
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=1000.0, kinematic_viscosity=0.0)
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=1000.0, kinematic_viscosity=-1e-6)


def test_fluid_prandtl_optional_but_positive_when_set():
    # None is allowed (isothermal case).
    f = FluidProperties(name="x", density=1.0, kinematic_viscosity=1e-6, prandtl=None)
    assert f.prandtl is None
    # 0.0 / negative rejected.
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=1.0, kinematic_viscosity=1e-6, prandtl=0.0)
    with pytest.raises(ValidationError):
        FluidProperties(name="x", density=1.0, kinematic_viscosity=1e-6, prandtl=-0.1)


def test_fluid_name_length_bounds():
    with pytest.raises(ValidationError):
        FluidProperties(name="", density=1.0, kinematic_viscosity=1e-6)
    long_name = "x" * 65
    with pytest.raises(ValidationError):
        FluidProperties(name=long_name, density=1.0, kinematic_viscosity=1e-6)


def test_fluid_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        FluidProperties(
            name="x", density=1.0, kinematic_viscosity=1e-6, mystery="oops",
        )


# ────────── ThermalProperties ──────────


def test_thermal_specific_heat_positive():
    with pytest.raises(ValidationError):
        ThermalProperties(specific_heat=0.0, thermal_conductivity=1.0)


def test_thermal_conductivity_positive():
    with pytest.raises(ValidationError):
        ThermalProperties(specific_heat=1000.0, thermal_conductivity=0.0)


def test_thermal_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        ThermalProperties(
            specific_heat=1000.0, thermal_conductivity=1.0, mystery="oops",
        )


# ────────── MaterialContract cross-field ──────────


def _custom_fluid() -> FluidProperties:
    return FluidProperties(
        name="custom_fluid", density=1000.0, kinematic_viscosity=1e-6,
    )


def test_contract_kind_preset_requires_preset_id():
    with pytest.raises(ValidationError) as exc_info:
        MaterialContract(
            kind="preset",
            preset_id=None,
            fluid=_custom_fluid(),
            citation="https://example.com/cite",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "preset_id" in str(exc_info.value)


def test_contract_kind_preset_requires_citation():
    with pytest.raises(ValidationError) as exc_info:
        MaterialContract(
            kind="preset",
            preset_id="water_20c",
            fluid=_custom_fluid(),
            citation=None,
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "citation" in str(exc_info.value)


def test_contract_kind_custom_must_leave_preset_id_none():
    with pytest.raises(ValidationError) as exc_info:
        MaterialContract(
            kind="custom",
            preset_id="water_20c",
            fluid=_custom_fluid(),
            authored_at="2026-05-07T12:00:00Z",
        )
    assert "preset_id" in str(exc_info.value)


def test_contract_custom_does_not_require_citation():
    # Engineer types own values; citation is their responsibility.
    contract = MaterialContract(
        kind="custom",
        preset_id=None,
        fluid=_custom_fluid(),
        citation=None,
        authored_at="2026-05-07T12:00:00Z",
    )
    assert contract.citation is None


def test_contract_preset_id_charset():
    with pytest.raises(ValidationError):
        MaterialContract(
            kind="preset",
            preset_id="water 20c",  # space disallowed
            fluid=_custom_fluid(),
            citation="https://example.com/cite",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        MaterialContract(
            kind="preset",
            preset_id="water/20c",  # slash disallowed
            fluid=_custom_fluid(),
            citation="https://example.com/cite",  # type: ignore[arg-type]
            authored_at="2026-05-07T12:00:00Z",
        )
    # Underscore + hyphen allowed.
    contract = MaterialContract(
        kind="preset",
        preset_id="water_20c-final",
        fluid=_custom_fluid(),
        citation="https://example.com/cite",  # type: ignore[arg-type]
        authored_at="2026-05-07T12:00:00Z",
    )
    assert contract.preset_id == "water_20c-final"


def test_contract_thermal_optional():
    # Isothermal case — thermal block None is valid.
    contract = MaterialContract(
        kind="custom",
        fluid=_custom_fluid(),
        thermal=None,
        authored_at="2026-05-07T12:00:00Z",
    )
    assert contract.thermal is None


def test_contract_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        MaterialContract(
            kind="custom",
            fluid=_custom_fluid(),
            authored_at="2026-05-07T12:00:00Z",
            mystery="oops",
        )


def test_contract_authored_at_length_bounds():
    with pytest.raises(ValidationError):
        MaterialContract(
            kind="custom",
            fluid=_custom_fluid(),
            authored_at="short",  # under 10 chars
        )


# ────────── Material library ──────────


def test_library_not_empty():
    assert len(MATERIAL_PRESETS) > 0
    assert "water_20c" in MATERIAL_PRESETS
    assert "air_20c" in MATERIAL_PRESETS


def test_library_preset_ids_are_unique_and_match_keys():
    """The library is keyed by preset_id; every entry's preset_id
    field must equal its dict key (otherwise lookups via
    preset.preset_id would mismatch)."""
    for key, preset in MATERIAL_PRESETS.items():
        assert preset.preset_id == key, (
            f"library key {key!r} != preset.preset_id {preset.preset_id!r}"
        )


def test_library_every_preset_carries_citation():
    """Charter threat-model row 4: every bundled preset MUST cite a
    public source. Empty / None citation = ship-blocker."""
    for preset_id, preset in MATERIAL_PRESETS.items():
        assert preset.citation, (
            f"preset {preset_id!r} ships without a citation URL"
        )
        # Must be parseable as an HTTP(S) URL.
        assert preset.citation.startswith(("http://", "https://")), (
            f"preset {preset_id!r} citation is not an HTTP URL"
        )


def test_library_fluid_values_are_physically_plausible():
    """Smoke check — water density should be near 1000 kg/m³, air near
    1.2 kg/m³, oils between. Catches gross typos in the library."""
    water = MATERIAL_PRESETS["water_20c"]
    assert 995.0 < water.fluid.density < 1005.0
    air = MATERIAL_PRESETS["air_20c"]
    assert 1.0 < air.fluid.density < 1.5
    oil = MATERIAL_PRESETS["oil_iso_vg_46_40c"]
    # Mineral oil density typically 850-880.
    assert 800.0 < oil.fluid.density < 900.0


def test_library_isothermal_variant_strips_thermal():
    iso = MATERIAL_PRESETS["air_20c_isothermal"]
    assert iso.thermal is None
    assert iso.fluid.prandtl is None


def test_get_material_preset_returns_none_on_unknown_id():
    assert get_material_preset("unobtanium_500k") is None


def test_get_material_preset_returns_match_on_known_id():
    p = get_material_preset("water_20c")
    assert p is not None
    assert p.preset_id == "water_20c"


def test_list_material_preset_ids_returns_all_keys():
    ids = list_material_preset_ids()
    assert set(ids) == set(MATERIAL_PRESETS.keys())


def test_library_preset_can_populate_a_valid_contract():
    """End-to-end: pick a preset, copy its values into a MaterialContract
    body, and verify it validates. This is the wire-level behavior the
    frontend (N3.3) will perform."""
    preset = MATERIAL_PRESETS["water_20c"]
    contract = MaterialContract(
        kind="preset",
        preset_id=preset.preset_id,
        fluid=preset.fluid,
        thermal=preset.thermal,
        citation=preset.citation,  # type: ignore[arg-type]
        authored_at="2026-05-07T12:00:00Z",
    )
    assert contract.fluid.density == preset.fluid.density
    assert contract.fluid.kinematic_viscosity == preset.fluid.kinematic_viscosity
    assert contract.preset_id == "water_20c"
