"""Workbench-basics schema · Stage 2 MVP per Codex industrial-workbench
meeting 2026-04-25 (transcript:
reports/codex_tool_reports/industrial_workbench_meeting_2026-04-25.md).

Backs the `<CaseFrame>` SVG primitive: structured first-screen view of
geometry / patches / boundary conditions / materials / solver for a
single CFD case. Source data lives in
`knowledge/workbench_basics/<case_id>.yaml`; this module just types it
for the FastAPI route.

Schema is informally v1; ratified once Stage 2 close trigger fires
(8-of-10 cases populated). See `.planning/roadmaps/workbench_rollout_roadmap.md`.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class BBox(BaseModel):
    """Geometry bounding box in physical units."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float = 0.0
    z_max: float = 0.0


class CharacteristicLength(BaseModel):
    name: str
    value: float
    unit: str
    description_zh: Optional[str] = None


class Geometry(BaseModel):
    """Domain shape for SVG topology rendering."""

    shape: str = Field(
        ...,
        description=(
            "Domain shape category for SVG renderer. "
            "Known values: rectangle, airfoil, cylinder, step, "
            "annulus, channel, jet_impingement. The frontend "
            "<CaseFrame> selects the SVG drawing strategy from this."
        ),
    )
    bbox: BBox
    characteristic_length: CharacteristicLength


class Patch(BaseModel):
    """One boundary surface (e.g. lid, leftWall, inlet, airfoil_upper)."""

    id: str
    role: str = Field(
        ...,
        description=(
            "Semantic role for color coding. Known values: "
            "wall, moving_wall, inlet, outlet, symmetry, "
            "cyclic, empty, airfoil, periodic."
        ),
    )
    location: str = Field(
        ...,
        description=(
            "Where on the SVG outline this patch lives. Known: "
            "top, bottom, left, right, front_back (2D empty), "
            "inlet, outlet, airfoil_upper, airfoil_lower, "
            "cylinder_surface, step_face."
        ),
    )
    label_zh: str
    label_en: str
    description_zh: Optional[str] = None


class BoundaryConditionPatch(BaseModel):
    """One patch's BC for one field. `value` shape depends on field
    (scalar p, 3-vector U, etc.) — kept loose as Union/Any.
    """

    type: str = Field(
        ...,
        description=(
            "OpenFOAM BC type token. Known: fixedValue, "
            "noSlip, zeroGradient, inletOutlet, slip, "
            "empty, cyclic, calculated."
        ),
    )
    value: Optional[Union[float, list[float], str]] = None
    display_zh: Optional[str] = None


class BoundaryCondition(BaseModel):
    field: str
    quantity: str
    units: str
    description_zh: Optional[str] = None
    per_patch: dict[str, BoundaryConditionPatch]


class MaterialProperty(BaseModel):
    symbol: str
    name: str
    value: float
    unit: str
    note_zh: Optional[str] = None


class Material(BaseModel):
    id: str
    label_zh: str
    label_en: str
    properties: list[MaterialProperty]


class DerivedQuantity(BaseModel):
    symbol: str
    name: str
    value: float
    formula: str
    note_zh: Optional[str] = None


class Solver(BaseModel):
    name: str
    family: str
    steady_state: bool
    laminar: bool
    display_zh: str
    reasoning_zh: str


class WorkbenchBasicsHints(BaseModel):
    """Optional terse pedagogical hints rendered as tooltip captions
    in <CaseFrame>. Long-form prose lives in StoryTab — anti-pattern
    is to mirror Story content here (per Codex meeting "把报告页伪装
    成工作台" warning)."""

    geometry_zh: Optional[str] = None
    driver_zh: Optional[str] = None
    physical_intuition_zh: Optional[str] = None


class WorkbenchBasics(BaseModel):
    """Top-level response shape for `/api/cases/{case_id}/workbench-basics`.

    All fields except `hints` are required for the SVG to render
    completely. A case with partial coverage (e.g. solver section
    missing) returns the populated subset and the frontend falls
    back to per-section skeletons.
    """

    case_id: str
    display_name: str
    display_name_zh: Optional[str] = None
    canonical_ref: Optional[str] = None
    dimension: int = Field(..., ge=2, le=3)
    geometry: Geometry
    patches: list[Patch]
    boundary_conditions: list[BoundaryCondition]
    materials: list[Material]
    derived: list[DerivedQuantity] = Field(default_factory=list)
    solver: Optional[Solver] = None
    hints: Optional[WorkbenchBasicsHints] = None

    # When schema-drift catches mismatched per_patch keys vs patch ids,
    # the loader stuffs the diagnostic into this field rather than
    # raising — UI surfaces it as an amber banner so the dev sees the
    # discrepancy without 500ing the page.
    schema_drift_warning: Optional[str] = None


def validate_patch_consistency(payload: dict[str, Any]) -> Optional[str]:
    """Return a human-readable warning if BC.per_patch keys don't
    match patches[*].id, else None. Loose check — intentionally
    forgiving (warn, don't error) per Stage 2 risk note."""
    patch_ids = {p.get("id") for p in payload.get("patches", []) if isinstance(p, dict)}
    drift: list[str] = []
    for bc in payload.get("boundary_conditions", []):
        if not isinstance(bc, dict):
            continue
        per_patch = bc.get("per_patch") or {}
        for pid in per_patch:
            if pid not in patch_ids:
                drift.append(
                    f"BC field {bc.get('field')!r} references patch "
                    f"{pid!r} not declared in `patches:` block"
                )
    if not drift:
        return None
    return "; ".join(drift)
