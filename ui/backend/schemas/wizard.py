"""Onboarding-wizard schemas · Stage 8a.

Surfaces a guided "newcomer's first case" flow on /workbench/new. The
wizard renders a hand-written CFD case YAML from one of three starter
templates + form-driven parameter overrides, then drops the result into
``ui/backend/user_drafts/`` (same store the existing CaseEditor uses).

Strict additive — no changes to existing schemas, no shared types with
foam_agent_adapter, no fixture-format touching. Runs sit on top of the
existing synthetic-residual stream wrapped with phase-tagged narration.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ParamType = Literal["int", "float"]


class TemplateParam(BaseModel):
    """One form field exposed to the user during wizard config."""

    key: str = Field(..., description="YAML path key, e.g. 'Re' or 'lid_velocity'")
    label_zh: str
    label_en: str
    type: ParamType
    default: float
    min: Optional[float] = None
    max: Optional[float] = None
    unit: Optional[str] = Field(
        None, description="Display unit, e.g. 'm/s', 'Pa·s', 'dimensionless'"
    )
    help_zh: Optional[str] = None


class TemplateSummary(BaseModel):
    """One wizard starter template."""

    template_id: str = Field(..., description="Stable id, e.g. 'square_cavity'")
    name_zh: str
    name_en: str
    description_zh: str
    geometry_type: str = Field(
        ...,
        description=(
            "Same enum as knowledge/whitelist.yaml geometry_type — "
            "SIMPLE_GRID / AXISYMMETRIC / etc."
        ),
    )
    flow_type: str = Field(..., description="INTERNAL / EXTERNAL")
    solver: str = Field(..., description="OpenFOAM solver name, e.g. icoFoam")
    canonical_ref: Optional[str] = Field(
        None,
        description="Real benchmark this template is patterned on, if any",
    )
    params: list[TemplateParam]


class TemplateListResponse(BaseModel):
    templates: list[TemplateSummary]


class DraftCreateRequest(BaseModel):
    template_id: str
    case_id: str = Field(
        ...,
        description=(
            "User-chosen id for the new draft. Must be alphanumeric / "
            "underscore / hyphen — same rule as case_drafts._draft_path "
            "to prevent path traversal."
        ),
    )
    name_display: Optional[str] = Field(
        None,
        description="Human-readable name override; defaults to template name + case_id",
    )
    params: dict[str, float] = Field(
        default_factory=dict,
        description="Param key → numeric value; missing keys fall back to template default",
    )


class DraftCreateResponse(BaseModel):
    case_id: str
    draft_path: str
    yaml_text: str
    lint_ok: bool
    lint_errors: list[str] = Field(default_factory=list)
    lint_warnings: list[str] = Field(default_factory=list)


# --- Run-stream events (Stage 8a-2; surfaced now so frontend types align)
PhaseId = Literal["geometry", "mesh", "boundary", "solver", "compare"]
PhaseStatus = Literal["ok", "fail", "running"]
EventType = Literal["phase_start", "log", "metric", "phase_done", "run_done"]


class RunPhaseEvent(BaseModel):
    """One SSE message on /api/wizard/run/{case_id}/stream.

    Discriminated by `type`. `phase_start` opens a phase; `log` and
    `metric` carry per-phase telemetry; `phase_done` closes a phase
    with a status + 1-line summary; `run_done` closes the whole run.
    """

    type: EventType
    phase: Optional[PhaseId] = None
    t: float = Field(..., description="Unix timestamp seconds")
    line: Optional[str] = None
    message: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[PhaseStatus] = None
    metric_key: Optional[str] = None
    metric_value: Optional[float] = None
