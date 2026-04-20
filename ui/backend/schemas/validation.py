"""Schemas for case-index, case-detail, and validation-report responses.

Kept deliberately small in Phase 0 — extended in Phase 1 when the
Case Editor needs the full whitelist-case schema round-tripped.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ContractStatus = Literal["PASS", "HAZARD", "FAIL", "UNKNOWN"]
"""Three-state semantics: PASS (within tolerance, no hazard armed),
HAZARD (within tolerance but a silent-pass hazard is armed), FAIL
(outside tolerance OR contract precondition unmet). UNKNOWN when
no measurement is available yet."""


RunCategory = Literal[
    "reference",
    "real_incident",
    "under_resolved",
    "wrong_model",
]
"""Run category for multi-run validation demos:
- reference: a run that SHOULD pass — curated from literature exact solutions
  or published tables. Lets students see what "done right" looks like.
- real_incident: the actual measurement our adapter produced in a specific
  production incident. Preserved for auditability / decision traceability.
- under_resolved: a run deliberately using insufficient mesh / short settle
  time / low y+ — a teaching run that demonstrates why resolution matters.
- wrong_model: a run using a physically-inappropriate turbulence / physics
  model — demonstrates why model selection matters.
"""


class RunDescriptor(BaseModel):
    """One row of GET /api/cases/{id}/runs — lightweight list entry."""

    run_id: str = Field(..., description="stable id within the case")
    label_zh: str = Field(..., description="human label, Chinese primary")
    label_en: str = Field("", description="optional English label")
    description_zh: str = Field(
        "",
        description="what this run represents (what was curated/broken/observed)",
    )
    category: RunCategory
    expected_verdict: ContractStatus = Field(
        "UNKNOWN",
        description="hint only — actual verdict is computed from the measurement",
    )


class CaseIndexEntry(BaseModel):
    """One row of GET /api/cases."""

    case_id: str = Field(..., description="whitelist.yaml `id` field")
    name: str = Field(..., description="human-readable case name")
    flow_type: str
    geometry_type: str
    turbulence_model: str
    has_gold_standard: bool
    has_measurement: bool
    contract_status: ContractStatus


class GoldStandardReference(BaseModel):
    """The anchor numeric + citation for a case."""

    quantity: str
    ref_value: float
    unit: str = ""
    tolerance_pct: float = Field(
        ..., description="Fractional tolerance (0.15 = ±15%)"
    )
    citation: str
    doi: str | None = None


class Precondition(BaseModel):
    """One physics_contract precondition row."""

    condition: str
    satisfied: bool
    evidence_ref: str | None = None
    consequence_if_unsatisfied: str | None = None


class AuditConcern(BaseModel):
    """An audit concern emitted by `error_attributor` or encoded in
    the gold-standard `contract_status` narrative."""

    concern_type: str = Field(
        ...,
        description=(
            "Canonical type: COMPATIBLE_WITH_SILENT_PASS_HAZARD, "
            "DEVIATION, PRECONDITION_UNMET, etc."
        ),
    )
    summary: str = Field(..., description="One-line human-readable summary.")
    detail: str | None = None
    decision_refs: list[str] = Field(
        default_factory=list,
        description="IDs of related DEC-ADWM-* / DEC-V61-* records.",
    )


class DecisionLink(BaseModel):
    """A chronological entry in the case's decision trail."""

    decision_id: str
    date: str
    title: str
    autonomous: bool


class MeasuredValue(BaseModel):
    """The extracted quantity from a solver run."""

    value: float
    unit: str = ""
    source: str = Field(
        ...,
        description=(
            "Where the measurement came from: 'slice_metrics.yaml' or "
            "'fixture' or 'decision_record'."
        ),
    )
    run_id: str | None = None
    commit_sha: str | None = None
    measured_at: str | None = None


class CaseDetail(BaseModel):
    """GET /api/cases/{case_id} payload."""

    case_id: str
    name: str
    reference: str | None = None
    doi: str | None = None
    flow_type: str
    geometry_type: str
    compressibility: str | None = None
    steady_state: str | None = None
    solver: str | None = None
    turbulence_model: str
    parameters: dict[str, float | int | str] = Field(default_factory=dict)
    gold_standard: GoldStandardReference | None = None
    preconditions: list[Precondition] = Field(default_factory=list)
    contract_status_narrative: str | None = None


class ValidationReport(BaseModel):
    """GET /api/validation-report/{case_id} payload — Screen 4 data."""

    case: CaseDetail
    gold_standard: GoldStandardReference
    measurement: MeasuredValue | None = None
    contract_status: ContractStatus
    deviation_pct: float | None = Field(
        None,
        description=(
            "(measured − ref) / ref × 100. None when no measurement is "
            "available."
        ),
    )
    within_tolerance: bool | None = None
    tolerance_lower: float | None = None
    tolerance_upper: float | None = None
    audit_concerns: list[AuditConcern] = Field(default_factory=list)
    preconditions: list[Precondition] = Field(default_factory=list)
    decisions_trail: list[DecisionLink] = Field(default_factory=list)
