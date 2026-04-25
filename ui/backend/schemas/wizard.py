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


class WizardPreviewResponse(BaseModel):
    """Server-rendered byte-exact preview (Opus round-2 Q11 fix).

    Identical body to the `yaml_text` that `POST /api/wizard/draft` will
    eventually write — uses the same `services.wizard.render_yaml` call.
    The wizard UI must render this text verbatim; client-side YAML
    string-concat was the trust-killer that round-2 review flagged
    (preview said `lid_velocity:`, server emitted `top_wall_u:`).
    """

    yaml_text: str


# --- Run-stream events (Stage 8a-2; surfaced now so frontend types align)
PhaseId = Literal["geometry", "mesh", "boundary", "solver", "compare"]
PhaseStatus = Literal["ok", "fail", "running"]
EventType = Literal["phase_start", "log", "metric", "phase_done", "run_done"]
# Stage 8b prep (round-3 Q13 schema audit, 2026-04-26): real solver
# subprocess will surface log severity. Adding here as an optional
# discriminant so the schema is forward-compatible without a breaking
# wire format change in the Stage 8b PR.
LogLevel = Literal["debug", "info", "warning", "error"]
LogStream = Literal["stdout", "stderr"]


class RunPhaseEvent(BaseModel):
    """One SSE message on /api/wizard/run/{case_id}/stream.

    Discriminated by `type`. `phase_start` opens a phase; `log` and
    `metric` carry per-phase telemetry; `phase_done` closes a phase
    with a status + 1-line summary; `run_done` closes the whole run.

    Round-3 Q13 schema audit (2026-04-26): all originally-defined fields
    were verified to be facts about a run (type/phase/t/line/message/
    summary/status/metric_key/metric_value), not properties of the mock
    pacing. The `routes/wizard.py:_PHASE_SCRIPT` carries mock-shape
    fields (`delay_per_log`, `summary_template`, `patch_count`) but
    those never go on the wire. So the round-2 prediction "Stage 8b is
    a single-file swap" holds for the schema; the Stage 8b PR replaces
    the script generator without changing this contract.

    The `level` / `stream` / `exit_code` fields below are **additive
    forward-compat** — a real OpenFOAM subprocess yields warning lines
    on stderr and a process exit code that the mock script does not
    need to populate. Existing frontend code reads these as undefined
    and renders unchanged; Stage 8b can populate them without a schema
    migration.
    """

    type: EventType
    phase: Optional[PhaseId] = None
    t: float = Field(..., description="Wall-clock timestamp (unix seconds)")
    line: Optional[str] = None
    message: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[PhaseStatus] = None
    metric_key: Optional[str] = None
    metric_value: Optional[float] = None
    # --- Stage 8b forward-compat (round-3 Q13 audit additions) ---
    level: Optional[LogLevel] = Field(
        None,
        description=(
            "Log severity for `log` events. None for legacy/mock streams "
            "(frontend treats as 'info'). Real solver runs populate from "
            "OpenFOAM's '--> FOAM Warning :' / '--> FOAM FATAL ERROR :' "
            "prefixes."
        ),
    )
    stream: Optional[LogStream] = Field(
        None,
        description=(
            "Source stream for `log` events. None when stream is implicit "
            "(mock / single-stream)."
        ),
    )
    exit_code: Optional[int] = Field(
        None,
        description=(
            "Subprocess exit code for `phase_done` / `run_done` events. "
            "None for events emitted before subprocess wait()."
        ),
    )
