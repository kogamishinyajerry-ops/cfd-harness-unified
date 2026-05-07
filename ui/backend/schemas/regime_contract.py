"""DEC-V61-141 (N3.2) · RegimeContract schema.

Structured contract for turbulence-regime selection. Becomes the
source of truth for what gets written into ``constant/momentumTransport``
(or successor `turbulenceProperties`). N3.4 maps the regime literal
to a solver name (read-only mapping table); N3.5 maps the regime to
default tolerance template.

V0 regime set (charter §"Out of scope" caps further regimes to
N3-extend / M3+):
  * laminar
  * RANS-RAS (k-epsilon family — generic baseline)
  * RANS-kOmegaSST (default for industrial wall-bounded flows)
  * LES-stub (placeholder so the wire enum is forward-compatible;
    sub-grid model selection deferred to M3-extend)

Each regime carries APPLICABILITY BOUNDS (Re/Ma/y+) sourced from
public references — Charter threat-model row 2: bounds are advisory
metadata, NOT auto-rejection. Engineer reads citation, decides.

Wire shape (Pydantic):

    RegimeContract
      kind: Literal["preset", "custom"]
      preset_id: str | None        # required when kind=preset
      regime: Literal[              # canonical regime name
          "laminar",
          "RANS-RAS",
          "RANS-kOmegaSST",
          "LES-stub",
      ]
      applicability:
        re_min: float | None       # Reynolds-number lower bound
        re_max: float | None       # upper bound
        mach_max: float | None     # incompressibility cutoff (typ. 0.3)
        y_plus_target: float | None# wall y+ recommendation
      citation: HttpUrl | None     # public source URL (paper / textbook DOI)
      authored_at: str             # ISO 8601 string

Out of scope for N3.2:
  * Sub-grid model selection (Smagorinsky / WALE / dynamic) — M3-extend
  * Transition / SST-LM / γ-Reθ — M3-extend
  * Reynolds-Stress family (RSM) — M3-extend
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


RegimeKind = Literal[
    "laminar",
    "RANS-RAS",
    "RANS-kOmegaSST",
    "LES-stub",
]


class ApplicabilityBounds(BaseModel):
    """Advisory metadata describing the regime's published validity
    envelope. None = "no bound documented" — the engineer reads the
    citation and decides if their case is in-scope.

    Charter §threat-model row 2: bounds NEVER auto-reject. The Step
    Physics panel surfaces them as informational hints next to the
    regime selector.
    """

    model_config = ConfigDict(extra="forbid")

    re_min: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Lower Reynolds bound below which this regime is typically "
            "inapplicable. Example: RANS-kOmegaSST ~ Re > 1e3."
        ),
    )
    re_max: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Upper Reynolds bound. Example: laminar regime breaks "
            "around Re > 2300 (pipe) / 5e5 (flat plate)."
        ),
    )
    mach_max: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Incompressibility cutoff. Default 0.3 — above this, "
            "compressible solvers (rhoSimpleFoam etc.) are required "
            "and the incompressible path of N3 is out of scope."
        ),
    )
    y_plus_target: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Recommended wall y+ for the regime. Wall-resolving k-ω "
            "SST: y+ ~ 1; wall-function k-ε: y+ ~ 30-300. None when "
            "the regime is wall-agnostic (e.g. laminar internal flow)."
        ),
    )

    @field_validator("re_max")
    @classmethod
    def _re_max_above_re_min(cls, v: float | None, info) -> float | None:
        # Pydantic v2: cross-field validation lives in
        # model_post_init. We only do the field-local positivity here.
        return v


class RegimeContract(BaseModel):
    """N3.2 wire contract — what the engineer commits via the Step
    Physics panel for turbulence regime.

    Same `kind` / `preset_id` discipline as MaterialContract:
    selection from the bundled REGIME_PRESETS library is "preset",
    engineer-typed deviations are "custom". Either way, the
    `regime` literal + `applicability` bounds are authoritative
    (preset is shorthand, not a binding indirection).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["preset", "custom"] = Field(
        ...,
        description=(
            "Audit field: 'preset' when populated from the bundled "
            "library, 'custom' when engineer typed values manually."
        ),
    )
    preset_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Preset library identifier (e.g. 'rans_komegasst_default'). "
            "Required when kind=preset; MUST be None when kind=custom."
        ),
    )
    regime: RegimeKind = Field(
        ...,
        description=(
            "Canonical regime literal. Stable enum so N3.4 (solver "
            "derivation) and N3.5 (tolerance binding) can pattern-match "
            "without parsing free-form text."
        ),
    )
    applicability: ApplicabilityBounds = Field(
        default_factory=ApplicabilityBounds,
        description=(
            "Published validity envelope. Advisory metadata only — "
            "Charter §threat-model row 2 prohibits auto-rejection."
        ),
    )
    citation: HttpUrl | None = Field(
        default=None,
        description=(
            "Public-source URL for the applicability bounds (textbook, "
            "paper DOI, OpenFOAM user guide). Required for kind=preset."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
        description="ISO 8601 timestamp string when engineer committed.",
    )

    @field_validator("preset_id")
    @classmethod
    def _preset_id_charset(cls, v: str | None) -> str | None:
        if v is not None and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "preset_id must be alphanumeric with optional '_' / '-'"
            )
        return v

    def model_post_init(self, __context) -> None:
        # Cross-field invariants: same triple as MaterialContract.
        if self.kind == "preset":
            if self.preset_id is None:
                raise ValueError("kind=preset requires preset_id")
            if self.citation is None:
                raise ValueError(
                    "kind=preset requires citation (every bundled preset must cite)"
                )
        elif self.kind == "custom":
            if self.preset_id is not None:
                raise ValueError("kind=custom must leave preset_id=None")
        # ApplicabilityBounds: re_max must be above re_min when both set.
        ap = self.applicability
        if (
            ap.re_min is not None
            and ap.re_max is not None
            and ap.re_max <= ap.re_min
        ):
            raise ValueError(
                f"applicability.re_max ({ap.re_max}) must exceed re_min ({ap.re_min})"
            )
