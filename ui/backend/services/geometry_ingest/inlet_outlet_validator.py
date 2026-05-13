"""Inlet/outlet boundary emission validator (A5 advisor).

Implements the V81 protocol amendment (DEC-V61-198-sub-protocol-inlet-outlet,
2026-05-12) as an automated parts_manifest audit. case_012 v1 silently
collapsed to natural-convection-only because Codex emitted ``supply_inlet`` /
``return_outlet`` as 3D solid bodies and snappyHexMesh meshed them as walls.
The protocol amendment defined three approved emission patterns; this
module checks a parts_manifest dict against those patterns so the
failure mode is caught pre-mesh, not at v1 sediment time.

Approved patterns (see ``.planning/methodology/codex_case_design_protocol.md``
§"Inlet/outlet boundary geometry emission"):

1. ``thin_extrusion``  — body bbox max dim ≤ 1.5 mm (1 mm canonical + tolerance)
2. ``createPatch_carve`` — body carries ``carve_metadata`` describing the
   parent patch + bbox; pipeline carves the patch post-sHM
3. ``sealed_room_natural_convection`` — explicit annotation that the
   brief was knowingly relaxed to sealed-room physics (no through-flow);
   prevents silent fallback to sealed-room (the V81 failure mode)

Bodies whose ``role`` is not one of {supply, return, inlet, outlet}
are ignored. A through-flow body that omits ``boundary_emission`` and
is not referenced by a ``boundary_zones`` entry is a critical fail.

References:
- V81 in ``industrial_solver_findings_v_series.md`` (case_012 backfill)
- Parent sub-DEC: V61-198-sub-A5 (2026-05-13)
- Sibling validator pattern: ``step_canonicalizer.py`` (A7)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_BOUNDARY_EMISSIONS: frozenset[str] = frozenset(
    {"thin_extrusion", "createPatch_carve", "sealed_room_natural_convection"}
)
THROUGH_FLOW_ROLES: frozenset[str] = frozenset({"supply", "return", "inlet", "outlet"})

# Thin-extrusion ceiling: Pattern 1 canonical extrusion is 1 mm thick;
# 1.5 mm allows a small tolerance for hand-tuned cases without admitting
# the 3D-solid emission that V81 root-caused (case_012 boxes were
# hundreds of mm thick).
THIN_EXTRUSION_MAX_MM: float = 1.5


@dataclass(frozen=True)
class BoundaryFinding:
    """One audit result for one through-flow body."""

    body_name: str
    role: str
    severity: str  # "pass" | "warning" | "fail"
    reason: str
    emission_pattern: str | None


@dataclass(frozen=True)
class InletOutletValidationReport:
    """Outcome of :func:`validate_inlet_outlet_emission`."""

    findings: tuple[BoundaryFinding, ...]
    fail_count: int
    warning_count: int
    pass_count: int

    @property
    def is_valid(self) -> bool:
        """True iff no body produced a ``fail`` finding."""
        return self.fail_count == 0


def _bbox_max_dim_mm(bbox: list[float] | tuple[float, ...]) -> float:
    xmin, ymin, zmin, xmax, ymax, zmax = bbox
    return max(xmax - xmin, ymax - ymin, zmax - zmin)


def validate_inlet_outlet_emission(
    parts_manifest: dict[str, Any],
) -> InletOutletValidationReport:
    """Audit a parts_manifest dict against the V81 emission protocol.

    Expected schema (subset; only the fields read here are documented):

    .. code-block:: yaml

       parts:
         - name: supply_inlet
           role: inlet              # one of supply|return|inlet|outlet to be audited
           boundary_emission: thin_extrusion
           bbox: [xmin, ymin, zmin, xmax, ymax, zmax]   # mm
           # OR boundary_emission: createPatch_carve + carve_metadata: {...}
           # OR boundary_emission: sealed_room_natural_convection
       boundary_zones:                # optional Pattern 2 metadata-only emission
         - name: supply_inlet
           ...

    Bodies whose role is outside the through-flow set are silently
    skipped (the validator's scope is inlet/outlet emission only).
    """
    findings: list[BoundaryFinding] = []
    parts = parts_manifest.get("parts") or []
    boundary_zones = parts_manifest.get("boundary_zones") or []
    carve_target_names = {bz.get("name") for bz in boundary_zones if isinstance(bz, dict)}

    for part in parts:
        if not isinstance(part, dict):
            continue
        role = part.get("role")
        if role not in THROUGH_FLOW_ROLES:
            continue
        name = part.get("name", "<unnamed>")
        emission = part.get("boundary_emission")

        if emission is None:
            if name in carve_target_names:
                findings.append(
                    BoundaryFinding(
                        body_name=name,
                        role=role,
                        severity="pass",
                        reason="Pattern 2 createPatch carve via boundary_zones entry",
                        emission_pattern="createPatch_carve",
                    )
                )
                continue
            findings.append(
                BoundaryFinding(
                    body_name=name,
                    role=role,
                    severity="fail",
                    reason=(
                        "through-flow body missing 'boundary_emission'; "
                        "V81 protocol requires one of "
                        f"{sorted(ALLOWED_BOUNDARY_EMISSIONS)} OR a "
                        "boundary_zones entry matching this body's name"
                    ),
                    emission_pattern=None,
                )
            )
            continue

        if emission not in ALLOWED_BOUNDARY_EMISSIONS:
            findings.append(
                BoundaryFinding(
                    body_name=name,
                    role=role,
                    severity="fail",
                    reason=(
                        f"unknown boundary_emission '{emission}'; "
                        f"allowed: {sorted(ALLOWED_BOUNDARY_EMISSIONS)}"
                    ),
                    emission_pattern=emission,
                )
            )
            continue

        if emission == "thin_extrusion":
            bbox = part.get("bbox")
            if bbox is None or len(bbox) != 6:
                findings.append(
                    BoundaryFinding(
                        body_name=name,
                        role=role,
                        severity="fail",
                        reason=(
                            "thin_extrusion requires bbox "
                            "[xmin,ymin,zmin,xmax,ymax,zmax] in mm"
                        ),
                        emission_pattern=emission,
                    )
                )
                continue
            max_dim = _bbox_max_dim_mm(bbox)
            if max_dim > THIN_EXTRUSION_MAX_MM:
                findings.append(
                    BoundaryFinding(
                        body_name=name,
                        role=role,
                        severity="fail",
                        reason=(
                            f"thin_extrusion bbox max dim {max_dim:.3f} mm "
                            f"exceeds {THIN_EXTRUSION_MAX_MM} mm ceiling — "
                            "sHM will likely treat this body as a wall "
                            "solid (V81 failure mode)"
                        ),
                        emission_pattern=emission,
                    )
                )
                continue
            findings.append(
                BoundaryFinding(
                    body_name=name,
                    role=role,
                    severity="pass",
                    reason=(
                        f"thin_extrusion bbox max dim {max_dim:.3f} mm "
                        f"≤ {THIN_EXTRUSION_MAX_MM} mm"
                    ),
                    emission_pattern=emission,
                )
            )
        elif emission == "createPatch_carve":
            carve_meta = part.get("carve_metadata")
            if not carve_meta:
                findings.append(
                    BoundaryFinding(
                        body_name=name,
                        role=role,
                        severity="fail",
                        reason=(
                            "createPatch_carve requires 'carve_metadata' "
                            "sub-field (parent_patch + bbox) per V81 Pattern 2"
                        ),
                        emission_pattern=emission,
                    )
                )
                continue
            findings.append(
                BoundaryFinding(
                    body_name=name,
                    role=role,
                    severity="pass",
                    reason="createPatch_carve declared with carve_metadata",
                    emission_pattern=emission,
                )
            )
        else:  # sealed_room_natural_convection
            findings.append(
                BoundaryFinding(
                    body_name=name,
                    role=role,
                    severity="warning",
                    reason=(
                        "sealed_room_natural_convection annotation accepted; "
                        "case explicitly relaxed to no-through-flow physics — "
                        "verify the engineering brief truly is sealed-room"
                    ),
                    emission_pattern=emission,
                )
            )

    fail = sum(1 for f in findings if f.severity == "fail")
    warn = sum(1 for f in findings if f.severity == "warning")
    passed = sum(1 for f in findings if f.severity == "pass")
    return InletOutletValidationReport(
        findings=tuple(findings),
        fail_count=fail,
        warning_count=warn,
        pass_count=passed,
    )
