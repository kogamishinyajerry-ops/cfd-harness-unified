"""Pydantic schemas for the Workflow Monitor (DEC-V61-226).

Server-side mirror of the frontend ``types/workflow.ts`` contract. Serialized
to **camelCase** (alias generator) so the React page consumes it without a
mapping layer.

HONESTY INVARIANT (the project's defining principle): ``WorkflowRun.is_mock``
is explicit. The assembler in ``services/workflow_monitor.py`` sets it False —
every stage state is DERIVED FROM REAL on-disk artifacts (run_record.json /
verdict.json / solver logs), never fabricated. ``StageState`` includes
``blocked`` as a first-class honest outcome (evidence insufficient / gate not
met), distinct from ``failed`` (hard error) — mirroring the backend's
"evidence-insufficient → BLOCK, never a silent pass".
"""
from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

StageKey = Literal[
    "geometry_intake",
    "geometry_validation",
    "mesh_generation",
    "mesh_quality_check",
    "solver_run",
    "result_report",
]

StageState = Literal["pending", "running", "passed", "blocked", "failed"]
MetricVerdict = Literal["pass", "hazard", "fail", "info"]
ArtifactKind = Literal["geometry", "mesh", "field", "log", "report", "table"]
AdvisorLevel = Literal["info", "warn", "block"]

STAGE_ORDER: List[StageKey] = [
    "geometry_intake",
    "geometry_validation",
    "mesh_generation",
    "mesh_quality_check",
    "solver_run",
    "result_report",
]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StageMetric(_CamelModel):
    label: str
    value: Union[str, float, int]
    unit: Optional[str] = None
    verdict: Optional[MetricVerdict] = None


class StageArtifact(_CamelModel):
    name: str
    kind: ArtifactKind
    href: Optional[str] = None


class WorkflowStage(_CamelModel):
    key: StageKey
    title: str
    state: StageState
    progress: int = 0
    current_object: Optional[str] = None
    metrics: List[StageMetric] = []
    warnings: List[str] = []
    errors: List[str] = []
    artifacts: List[StageArtifact] = []
    next_action: Optional[str] = None
    advisor: Optional[str] = None
    started_at: Optional[str] = None
    duration_label: Optional[str] = None


class WorkflowEdge(_CamelModel):
    # `from` is a reserved word — store as from_, serialize as the literal
    # "from" (explicit Field alias wins over the camel alias generator).
    from_: StageKey = Field(alias="from")
    to: StageKey


class AdvisorLogEntry(_CamelModel):
    ts: str
    stage: StageKey
    level: AdvisorLevel
    message: str


class TimelineEntry(_CamelModel):
    stage: StageKey
    label: str
    state: StageState
    at: str


class WorkflowRun(_CamelModel):
    run_id: str
    case_name: str
    is_mock: bool
    current_stage: StageKey
    stages: List[WorkflowStage] = []
    edges: List[WorkflowEdge] = []
    advisor_log: List[AdvisorLogEntry] = []
    timeline: List[TimelineEntry] = []


class WorkflowRunSummary(_CamelModel):
    """Lightweight listing entry for GET /api/workflow-runs."""

    run_key: str
    run_id: str
    case_name: str
    is_mock: bool
    current_stage: StageKey
