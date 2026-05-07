"""DEC-V61-140 (N3.1) · MaterialContract schema.

Structured contract for fluid + thermal material properties. Becomes
the source of truth for what gets written into the case's
``constant/physicalProperties`` (and successor `transportProperties`)
file. Replaces the ad-hoc hand-crafted dict authoring in
``bc_setup.py`` (Newtonian + hard-coded ν).

V130 Principle B: schema is engineer-filled (form), not AI-filled.
The frontend Step "Physics" panel (N3.3) renders fields; the engineer
types or selects from the preset library.

Citation discipline: every bundled preset MUST carry a public-source
URL in ``citation`` so the engineer can audit where the value came
from. Engineer-typed materials MAY omit citation (their own
responsibility).

Wire shape (Pydantic):

    MaterialContract
      kind: Literal["preset", "custom"]
      preset_id: str | None        # set when kind=preset
      fluid:
        name: str                  # human-readable, e.g. "water"
        density: float             # kg/m³, > 0
        kinematic_viscosity: float # m²/s, > 0  (this is `nu` in OpenFOAM)
        prandtl: float | None      # dimensionless, > 0 (None when thermal not used)
      thermal:
        specific_heat: float       # J/(kg·K), > 0  (cp)
        thermal_conductivity: float# W/(m·K), > 0  (k)
      | None                       # whole thermal block None for isothermal cases
      citation: HttpUrl | None     # public source URL (NIST, journal DOI, etc.)
      authored_at: str             # ISO 8601 timestamp string

Out of scope for N3.1:
  * Compressibility (ρ depends on p/T) — N3-extend
  * Temperature-dependent ν / cp / k tables — N3-extend
  * Multi-phase mixture properties — M4+ territory
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FluidProperties(BaseModel):
    """Newtonian-fluid properties used by ALL N3 regimes (laminar +
    RANS + LES). Compressibility / temperature dependence is NOT
    captured here — those belong to N3-extend.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Human-readable fluid name (e.g. 'water', 'air @ 20°C'). "
            "Free-form text — the wire schema does NOT enforce a "
            "vocabulary. Audited via citation field."
        ),
    )
    density: float = Field(
        ...,
        gt=0.0,
        description="Mass density ρ in kg/m³. Must be strictly positive.",
    )
    kinematic_viscosity: float = Field(
        ...,
        gt=0.0,
        description=(
            "Kinematic viscosity ν = μ/ρ in m²/s. Written into "
            "OpenFOAM ``physicalProperties`` as `nu [0 2 -1 0 0 0 0] <value>`."
        ),
    )
    prandtl: float | None = Field(
        default=None,
        description=(
            "Prandtl number Pr = ν/α (dimensionless). None for "
            "isothermal cases. When set, must be strictly positive — "
            "Pr<=0 implies α=∞ (instantaneous thermal equilibrium), "
            "which the energy equation solvers cannot represent."
        ),
    )

    @field_validator("prandtl")
    @classmethod
    def _prandtl_positive_when_set(cls, v: float | None) -> float | None:
        if v is not None and v <= 0.0:
            raise ValueError("prandtl must be > 0 when set (None for isothermal cases)")
        return v


class ThermalProperties(BaseModel):
    """Optional thermal block — present when the case includes an
    energy equation. Absent (whole block None on the parent
    MaterialContract) for isothermal cases.
    """

    model_config = ConfigDict(extra="forbid")

    specific_heat: float = Field(
        ...,
        gt=0.0,
        description=(
            "Specific heat at constant pressure cp in J/(kg·K). "
            "Strictly positive (a fluid with cp<=0 violates the second law)."
        ),
    )
    thermal_conductivity: float = Field(
        ...,
        gt=0.0,
        description=(
            "Thermal conductivity k in W/(m·K). Strictly positive — "
            "k<=0 implies heat flows from cold to hot."
        ),
    )


class MaterialContract(BaseModel):
    """N3.1 wire contract — what the engineer commits via the Step
    Physics panel.

    The frontend POSTs this body to (future N3.3 route)
    ``POST /api/cases/{case_id}/physics``; the writer translates
    ``fluid`` and ``thermal`` into the legacy
    ``constant/physicalProperties`` dict.

    ``kind`` discriminates preset selection vs custom typing. Preset
    selections carry the preset_id so the audit trail records which
    library entry was applied; custom selections set kind=custom and
    leave preset_id=None. Either way, the actual numbers used are
    those in ``fluid``/``thermal`` (preset is shorthand, not a binding
    indirection — this matters for reproducibility when the library
    later updates its bundled values).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["preset", "custom"] = Field(
        ...,
        description=(
            "Audit field: 'preset' when populated from the bundled "
            "library, 'custom' when engineer typed values manually. "
            "Numerics in fluid/thermal are authoritative either way."
        ),
    )
    preset_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Preset library identifier (e.g. 'water_20c'). Required "
            "when kind=preset; MUST be None when kind=custom (custom "
            "values have no library home)."
        ),
    )
    fluid: FluidProperties = Field(
        ...,
        description="Required Newtonian-fluid properties.",
    )
    thermal: ThermalProperties | None = Field(
        default=None,
        description=(
            "Optional thermal block. None for isothermal simulations. "
            "When the regime (N3.2) implies energy-equation solving "
            "(e.g. buoyantSimpleFoam), the route layer rejects "
            "MaterialContract with thermal=None at 422."
        ),
    )
    citation: HttpUrl | None = Field(
        default=None,
        description=(
            "Public-source URL for the bundled values (e.g. NIST "
            "webbook entry, journal DOI). Required for kind=preset "
            "(every bundled preset MUST cite); optional for kind=custom "
            "(engineer's own responsibility)."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
        description=(
            "ISO 8601 timestamp string when the engineer committed "
            "this contract. Recorded into the case audit trail."
        ),
    )

    @field_validator("preset_id")
    @classmethod
    def _preset_id_consistency(cls, v: str | None, info) -> str | None:
        # NB: in v2 pydantic, cross-field validation is conventionally a
        # model_validator; we use field_validator here only for the
        # length / charset on the literal value. Cross-field
        # (kind=preset → preset_id required) is enforced in the model
        # validator below.
        if v is not None and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "preset_id must be alphanumeric with optional '_' / '-'"
            )
        return v

    def model_post_init(self, __context) -> None:
        # Cross-field invariants. Pydantic v2 field_validators don't
        # see other fields in the same model cleanly; model_post_init
        # runs after all field validators and is the canonical place
        # for relational checks.
        if self.kind == "preset":
            if self.preset_id is None:
                raise ValueError("kind=preset requires preset_id")
            if self.citation is None:
                raise ValueError(
                    "kind=preset requires citation (every bundled preset must cite)"
                )
        elif self.kind == "custom":
            if self.preset_id is not None:
                raise ValueError(
                    "kind=custom must leave preset_id=None"
                )
