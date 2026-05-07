"""DEC-V61-141 (N3.2) · bundled regime preset library.

V0 ships 4 regime presets matching the RegimeKind literal:
  * laminar (default for low-Re internal flow)
  * RANS-RAS (k-epsilon family)
  * RANS-kOmegaSST (industrial wall-bounded default)
  * LES-stub (forward-compatibility placeholder)

Same citation discipline as materials_library.py — every preset
ships with a public-source URL. Tests assert this invariant.

Same "shallow-copy not auto-bind" discipline: when the engineer picks
a preset, the frontend (N3.3) shallow-copies the preset's
`regime` literal + `applicability` bounds into the contract body and
POSTs that. Library updates do NOT silently change saved cases.
"""
from __future__ import annotations

from dataclasses import dataclass

from ui.backend.schemas.regime_contract import (
    ApplicabilityBounds,
    RegimeKind,
)


@dataclass(frozen=True)
class RegimePreset:
    """A regime library entry. Not a wire contract — the engineer's
    POST body is a :class:`RegimeContract`. This dataclass populates
    UI dropdown options + drives test assertions.
    """

    preset_id: str
    display_name: str
    citation: str  # public-source URL — invariant: must be non-empty
    regime: RegimeKind
    applicability: ApplicabilityBounds
    notes: str = ""


# ────────── Library ──────────


_LAMINAR_INTERNAL = RegimePreset(
    preset_id="laminar_internal_default",
    display_name="laminar · internal flow (Re < 2300)",
    # Schlichting & Gersten "Boundary-Layer Theory" 9th ed., Springer
    # 2017 — pipe-flow transition reference.
    citation="https://link.springer.com/book/10.1007/978-3-662-52919-5",
    regime="laminar",
    applicability=ApplicabilityBounds(
        re_min=0.0,
        re_max=2300.0,
        mach_max=0.3,
        y_plus_target=None,  # laminar regime is wall-agnostic for y+
    ),
    notes=(
        "Pipe-flow laminar/turbulent transition is conventionally Re ≈ 2300 "
        "(Reynolds 1883). For external flows (flat plate) the bound shifts "
        "to Re ≈ 5e5 — consider a custom RegimeContract for those."
    ),
)

_RANS_RAS_GENERIC = RegimePreset(
    preset_id="rans_ras_kepsilon_default",
    display_name="RANS · k-ε (industrial baseline)",
    # Wilcox "Turbulence Modeling for CFD" 3rd ed., DCW Industries 2006.
    citation="https://www.dcwindustries.com/turbulence-modeling-for-cfd",
    regime="RANS-RAS",
    applicability=ApplicabilityBounds(
        re_min=1.0e3,
        re_max=None,  # no documented upper bound
        mach_max=0.3,
        y_plus_target=30.0,  # wall functions
    ),
    notes=(
        "Standard k-ε with wall functions; valid above Re ≈ 1000 for "
        "fully turbulent flows. Avoid for heavily separated / "
        "adverse-pressure-gradient flows — prefer kOmegaSST."
    ),
)

_RANS_KOMEGA_SST_DEFAULT = RegimePreset(
    preset_id="rans_komegasst_default",
    display_name="RANS · k-ω SST (industrial default)",
    # Menter, "Two-equation eddy-viscosity turbulence models for
    # engineering applications" AIAA Journal 1994.
    # https://doi.org/10.2514/3.12149
    citation="https://doi.org/10.2514/3.12149",
    regime="RANS-kOmegaSST",
    applicability=ApplicabilityBounds(
        re_min=1.0e3,
        re_max=None,
        mach_max=0.3,
        y_plus_target=1.0,  # wall-resolving
    ),
    notes=(
        "Menter's SST blends k-ω near walls with k-ε in free-stream; "
        "the most commonly recommended industrial default for wall-"
        "bounded incompressible RANS. Requires wall-resolving y+ ≈ 1."
    ),
)

_LES_STUB = RegimePreset(
    preset_id="les_stub_placeholder",
    display_name="LES · sub-grid model TBD (placeholder)",
    # Sagaut, "Large Eddy Simulation for Incompressible Flows" 3rd ed.,
    # Springer 2006.
    citation="https://link.springer.com/book/10.1007/b137536",
    regime="LES-stub",
    applicability=ApplicabilityBounds(
        re_min=1.0e4,
        re_max=None,
        mach_max=0.3,
        y_plus_target=1.0,
    ),
    notes=(
        "Forward-compatibility placeholder — actual sub-grid model "
        "selection (Smagorinsky / WALE / dynamic) is deferred to "
        "M3-extend. Selecting this regime in v0 lets the engineer "
        "stage an LES case but the writer (N3.3) emits a TODO comment "
        "instead of a full momentumTransport block."
    ),
)


REGIME_PRESETS: dict[str, RegimePreset] = {
    p.preset_id: p
    for p in (
        _LAMINAR_INTERNAL,
        _RANS_RAS_GENERIC,
        _RANS_KOMEGA_SST_DEFAULT,
        _LES_STUB,
    )
}


def list_regime_preset_ids() -> list[str]:
    """Stable-ordered list for UI dropdown — laminar first, then RAS,
    then kOmegaSST, then LES-stub."""
    return list(REGIME_PRESETS.keys())


def get_regime_preset(preset_id: str) -> RegimePreset | None:
    """Lookup; returns None for unknown preset_id."""
    return REGIME_PRESETS.get(preset_id)
