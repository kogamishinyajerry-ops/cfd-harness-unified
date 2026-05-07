"""DEC-V61-146 (N4.1) · structured per-patch BC contract.

Replaces the path of "engineer hand-edits `0.orig/{U, p}` boundary
blocks via raw-dict route" with a typed contract the engineer fills
via form (future Step 3 BC palette panel — wired in N4.2).

V0 BC type set (9 types, per N4 charter §sub-DEC table N4.1):

  Inlet family:
    * velocity_inlet         — fixedValue U + zeroGradient p
    * volumetric_flow_inlet  — flowRateInletVelocity (volumetric m³/s)
    * mass_flow_inlet        — flowRateInletVelocity (mass kg/s)
  Outlet family:
    * pressure_outlet        — zeroGradient U + fixedValue p
    * inlet_outlet           — pressureInletOutletVelocity + fixedValue p
                               (handles backflow gracefully)
  Wall family:
    * no_slip_wall           — fixedValue U=0 + zeroGradient p
    * moving_wall            — fixedValue U=<vector> + zeroGradient p
  Other:
    * symmetry               — symmetry both U + p
    * cyclic                 — cyclic both U + p (paired patches)
    * empty                  — empty both (used for 2D/wedge meshes)

Tagged-union pattern: each BC type is a separate Pydantic model with
the fields it needs; the union is keyed on `bc_type`. Pydantic v2
discriminator emits OpenAPI `discriminator: {propertyName: "bc_type"}`
for clean schema-driven tooling.

Out of scope for N4.1:
  * Thermal BCs (T field) — N3 thermal block lands the contract;
    N4.1 ships only U + p. Thermal-BC sub-DEC is N4.1-extend or
    rolled into N4.5 (controlDict timing also touches thermal cases).
  * Turbulence BCs (k, ω, ε) — N4.2 territory once solver dict
    editor lands and we know which fields are present
  * Custom-coded BCs (groovyBC, swak4Foam, codedFixedValue) — out
    forever from the structured contract; engineer uses the raw
    escape hatch (N4.4).
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ────────── Per-BC-type configs (tagged union) ──────────


class _BCBase(BaseModel):
    """Common fields. Each BC type subclasses to add its own knobs."""

    model_config = ConfigDict(extra="forbid")


class VelocityInletBC(_BCBase):
    """Fixed-value inlet velocity vector. The most common inlet BC.

    OpenFOAM emits:
      U: type fixedValue; value uniform (vx vy vz);
      p: type zeroGradient;
    """

    bc_type: Literal["velocity_inlet"] = "velocity_inlet"
    velocity: tuple[float, float, float] = Field(
        ...,
        description=(
            "Cartesian velocity vector (vx, vy, vz) in m/s. Direction "
            "matters — engineer's responsibility to set sign convention "
            "consistent with the mesh axis."
        ),
    )


class VolumetricFlowInletBC(_BCBase):
    """Volumetric flow rate inlet — useful when engineer knows m³/s
    target but not direction-resolved velocity.

    OpenFOAM emits:
      U: type flowRateInletVelocity; volumetricFlowRate <Q>;
         extrapolateProfile yes;
      p: type zeroGradient;
    """

    bc_type: Literal["volumetric_flow_inlet"] = "volumetric_flow_inlet"
    volumetric_flow_rate: float = Field(
        ...,
        gt=0.0,
        description="Volumetric flow rate Q in m³/s. Strictly positive.",
    )


class MassFlowInletBC(_BCBase):
    """Mass flow rate inlet — for compressible regimes (out of scope
    in v0 per N4 charter §"compressible regime path") OR
    incompressible cases where engineer prefers kg/s framing.

    OpenFOAM emits:
      U: type flowRateInletVelocity; massFlowRate <m_dot>;
         rho rho; rhoInlet <rho_value>;
         extrapolateProfile yes;
      p: type zeroGradient;
    """

    bc_type: Literal["mass_flow_inlet"] = "mass_flow_inlet"
    mass_flow_rate: float = Field(
        ...,
        gt=0.0,
        description="Mass flow rate ṁ in kg/s. Strictly positive.",
    )


class PressureOutletBC(_BCBase):
    """Fixed-pressure outlet — the most common outlet BC.

    OpenFOAM emits:
      U: type zeroGradient;
      p: type fixedValue; value uniform <p_value>;
    """

    bc_type: Literal["pressure_outlet"] = "pressure_outlet"
    gauge_pressure: float = Field(
        default=0.0,
        description=(
            "Gauge pressure (Pa) at the outlet. Default 0 — most "
            "incompressible cases use atmospheric / reference 0."
        ),
    )


class InletOutletBC(_BCBase):
    """Outlet that handles backflow gracefully — switches to inlet
    behavior when the local velocity reverses (e.g., recirculation
    near outlet).

    OpenFOAM emits:
      U: type pressureInletOutletVelocity; value uniform (0 0 0);
      p: type fixedValue; value uniform <p_value>;
    """

    bc_type: Literal["inlet_outlet"] = "inlet_outlet"
    gauge_pressure: float = Field(
        default=0.0,
        description="Gauge pressure (Pa) when flow exits.",
    )


class NoSlipWallBC(_BCBase):
    """No-slip stationary wall — the most common wall BC.

    OpenFOAM emits:
      U: type fixedValue; value uniform (0 0 0);
      p: type zeroGradient;
    """

    bc_type: Literal["no_slip_wall"] = "no_slip_wall"


class MovingWallBC(_BCBase):
    """Wall with prescribed translational velocity (e.g., LDC top
    lid). Rotational walls / sliding interfaces are M4-extend.

    OpenFOAM emits:
      U: type fixedValue; value uniform (vx vy vz);
      p: type zeroGradient;
    """

    bc_type: Literal["moving_wall"] = "moving_wall"
    velocity: tuple[float, float, float] = Field(
        ...,
        description="Wall translational velocity (m/s).",
    )


class SymmetryBC(_BCBase):
    """Mirror-plane symmetry. Common for half-domain reductions.

    OpenFOAM emits:
      U: type symmetry;
      p: type symmetry;
    """

    bc_type: Literal["symmetry"] = "symmetry"


class CyclicBC(_BCBase):
    """Periodic boundary — patches must be paired in
    constant/polyMesh/boundary. v0 emits the cyclic flag; engineer
    must ensure mesh has the matching paired patch.

    OpenFOAM emits:
      U: type cyclic;
      p: type cyclic;
    """

    bc_type: Literal["cyclic"] = "cyclic"
    paired_patch: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description=(
            "Name of the paired patch (already declared as a cyclic "
            "neighbor in constant/polyMesh/boundary). Engineer's "
            "responsibility to ensure the pairing exists in the mesh."
        ),
    )


class EmptyBC(_BCBase):
    """For 2D / wedge / axisymmetric meshes — directions OpenFOAM
    should ignore.

    OpenFOAM emits:
      U: type empty;
      p: type empty;
    """

    bc_type: Literal["empty"] = "empty"


# Discriminated union — schema-driven tooling cleanly selects the
# correct branch on the wire `bc_type` literal.
PerPatchBC = Annotated[
    Union[
        VelocityInletBC,
        VolumetricFlowInletBC,
        MassFlowInletBC,
        PressureOutletBC,
        InletOutletBC,
        NoSlipWallBC,
        MovingWallBC,
        SymmetryBC,
        CyclicBC,
        EmptyBC,
    ],
    Field(discriminator="bc_type"),
]


# ────────── Top-level contract ──────────


class BCContract(BaseModel):
    """N4.1 wire contract — engineer commits a per-patch BC mapping
    via the Step Physics workbench (BC palette panel · wired in N4.2).

    `patches` is a dict from patch_name (matching what's in
    constant/polyMesh/boundary) to the BC config. Patches not present
    in the dict default to no_slip_wall via the writer (with a
    warning surfaced in CaseProfile / TrustGate).

    `cyclic` BC types reference each other via `paired_patch`; the
    contract validator asserts the pairing is bidirectional and that
    every cyclic patch's pair is also in the dict.
    """

    model_config = ConfigDict(extra="forbid")

    patches: dict[str, PerPatchBC] = Field(
        ...,
        min_length=1,
        description=(
            "Map from patch name (matching constant/polyMesh/boundary) "
            "to per-patch BC config. Must contain at least one entry."
        ),
    )
    authored_at: str = Field(
        ...,
        min_length=10,
        max_length=40,
        description="ISO 8601 timestamp string when committed.",
    )

    @field_validator("patches")
    @classmethod
    def _patch_names_charset(
        cls, v: dict[str, PerPatchBC]
    ) -> dict[str, PerPatchBC]:
        # OpenFOAM patch names tolerate alnum + underscore. We also
        # allow hyphen + dot to match what gmsh + the case_solve
        # subsystem already accept. Anything else is a typo or
        # injection probe.
        for name in v:
            cleaned = name.replace("_", "").replace("-", "").replace(".", "")
            if not cleaned.isalnum():
                raise ValueError(
                    f"patch name {name!r} contains illegal characters "
                    "(only alnum + '_' + '-' + '.' permitted)"
                )
            if not name:
                raise ValueError("patch name must be non-empty")
        return v

    @model_validator(mode="after")
    def _validate_cyclic_pairings(self) -> "BCContract":
        """Cyclic BCs must reference patches that also exist in the
        dict, and the pairing must be bidirectional (A pairs with B
        AND B pairs with A) and both endpoints must be cyclic."""
        cyclic_pairs: dict[str, str] = {}
        for name, bc in self.patches.items():
            if isinstance(bc, CyclicBC):
                cyclic_pairs[name] = bc.paired_patch
        for name, paired in cyclic_pairs.items():
            if paired not in self.patches:
                raise ValueError(
                    f"cyclic patch {name!r} pairs with {paired!r}, "
                    "but {paired!r} is not in patches dict"
                )
            paired_bc = self.patches[paired]
            if not isinstance(paired_bc, CyclicBC):
                raise ValueError(
                    f"cyclic patch {name!r} pairs with {paired!r}, "
                    f"but {paired!r} has bc_type={paired_bc.bc_type!r} "
                    "(must also be cyclic)"
                )
            if paired_bc.paired_patch != name:
                raise ValueError(
                    f"cyclic pairing not bidirectional: {name!r} → "
                    f"{paired!r}, but {paired!r} → {paired_bc.paired_patch!r}"
                )
        return self


__all__ = [
    "BCContract",
    "CyclicBC",
    "EmptyBC",
    "InletOutletBC",
    "MassFlowInletBC",
    "MovingWallBC",
    "NoSlipWallBC",
    "PerPatchBC",
    "PressureOutletBC",
    "SymmetryBC",
    "VelocityInletBC",
    "VolumetricFlowInletBC",
]
