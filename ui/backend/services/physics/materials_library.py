"""DEC-V61-140 (N3.1) · bundled material preset library.

V0 ships water / air / oil + isothermal-air-only variant per N3
charter §"Out of scope" (custom materials defer to N3-extend).

Citation discipline (Charter threat model row 4): every preset MUST
carry a public-source URL. The route layer + tests both assert this
invariant — a preset without citation cannot ship.

Library entries are not auto-bound to MaterialContract: when the
engineer picks a preset, the frontend (N3.3) shallow-copies the
preset's fluid/thermal numbers into the contract body and POSTs that.
This means library updates do NOT silently change saved cases —
reproducibility wins over freshness.
"""
from __future__ import annotations

from dataclasses import dataclass

from ui.backend.schemas.material_contract import (
    FluidProperties,
    ThermalProperties,
)


@dataclass(frozen=True)
class MaterialPreset:
    """A library entry. Not a wire contract — the engineer's POST body
    is a :class:`MaterialContract`. This dataclass is the in-process
    representation used by the route layer to populate dropdown
    options + by tests to assert citation completeness.
    """

    preset_id: str
    display_name: str
    citation: str  # public-source URL — invariant: must be non-empty
    fluid: FluidProperties
    thermal: ThermalProperties | None
    notes: str = ""


# ────────── Library ──────────

# Convention: preset_id is `<material>_<reference_state>`. Numbers
# come from the cited source at the listed reference state. Absent a
# perfect-match reference, we pick the nearest commonly-cited value
# and document the choice in `notes`.

_WATER_20C = MaterialPreset(
    preset_id="water_20c",
    display_name="water · 20°C, 1 atm",
    # NIST WebBook for water at 293.15 K, 0.101325 MPa.
    # https://webbook.nist.gov/cgi/fluid.cgi?ID=C7732185&Action=Page
    citation="https://webbook.nist.gov/cgi/fluid.cgi?ID=C7732185&Action=Page",
    fluid=FluidProperties(
        name="water",
        density=998.21,            # kg/m³
        kinematic_viscosity=1.0034e-6,  # m²/s (μ=1.002e-3 Pa·s, ρ=998.21)
        prandtl=7.01,
    ),
    thermal=ThermalProperties(
        specific_heat=4184.0,      # J/(kg·K)
        thermal_conductivity=0.598,# W/(m·K)
    ),
    notes="Saturated liquid water at 20°C; NIST WebBook reference state.",
)

_AIR_20C = MaterialPreset(
    preset_id="air_20c",
    display_name="air · 20°C, 1 atm",
    # NIST WebBook for dry air at 293.15 K, 0.101325 MPa.
    # https://webbook.nist.gov/cgi/fluid.cgi?ID=C132259100&Action=Page
    citation="https://webbook.nist.gov/cgi/fluid.cgi?ID=C132259100&Action=Page",
    fluid=FluidProperties(
        name="air",
        density=1.2041,            # kg/m³
        kinematic_viscosity=1.516e-5,  # m²/s
        prandtl=0.7296,
    ),
    thermal=ThermalProperties(
        specific_heat=1005.0,      # J/(kg·K)
        thermal_conductivity=0.0257,# W/(m·K)
    ),
    notes="Dry air at sea-level reference state; NIST WebBook.",
)

_AIR_20C_ISOTHERMAL = MaterialPreset(
    preset_id="air_20c_isothermal",
    display_name="air · 20°C · isothermal (no thermal block)",
    citation="https://webbook.nist.gov/cgi/fluid.cgi?ID=C132259100&Action=Page",
    fluid=FluidProperties(
        name="air",
        density=1.2041,
        kinematic_viscosity=1.516e-5,
        prandtl=None,
    ),
    thermal=None,
    notes=(
        "Same air @ 20°C with thermal block stripped — for isothermal "
        "simpleFoam / pisoFoam runs where the energy equation is not "
        "solved. Engineer chooses this when the regime is "
        "incompressible-isothermal."
    ),
)

_OIL_GENERIC_40C = MaterialPreset(
    preset_id="oil_iso_vg_46_40c",
    display_name="oil · ISO VG 46 lubricant @ 40°C",
    # ISO 3448 viscosity grade reference; ν=46 cSt at 40°C is the
    # defining property of VG 46. Density and Pr from a published
    # technical data sheet (Mobil DTE 25 / equivalent class).
    # https://www.machinerylubrication.com/Read/2/Lubricant-Viscosity
    citation="https://www.machinerylubrication.com/Read/2/Lubricant-Viscosity",
    fluid=FluidProperties(
        name="oil_vg46",
        density=860.0,             # kg/m³
        kinematic_viscosity=4.6e-5,# m²/s (= 46 cSt)
        prandtl=350.0,             # typical for mineral lubricant @ 40°C
    ),
    thermal=ThermalProperties(
        specific_heat=1900.0,
        thermal_conductivity=0.13,
    ),
    notes=(
        "ISO Viscosity Grade 46 — a representative mineral hydraulic / "
        "lubricant oil. Engineer should override with their own "
        "material data when the simulation depends on precise "
        "rheology."
    ),
)


MATERIAL_PRESETS: dict[str, MaterialPreset] = {
    p.preset_id: p
    for p in (_WATER_20C, _AIR_20C, _AIR_20C_ISOTHERMAL, _OIL_GENERIC_40C)
}


def list_material_preset_ids() -> list[str]:
    """Stable-ordered list of preset IDs for UI dropdown. Sorted by
    insertion order in the library above (NOT alpha) so the most
    common defaults (water → air → isothermal-air → oil) appear
    first."""
    return list(MATERIAL_PRESETS.keys())


def get_material_preset(preset_id: str) -> MaterialPreset | None:
    """Lookup; returns None when the id is unknown so the caller can
    return a structured 404 with `failing_check: preset_not_found`."""
    return MATERIAL_PRESETS.get(preset_id)
