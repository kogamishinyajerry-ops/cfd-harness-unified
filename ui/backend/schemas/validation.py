"""Schemas for case-index, case-detail, and validation-report responses.

Kept deliberately small in Phase 0 — extended in Phase 1 when the
Case Editor needs the full whitelist-case schema round-tripped.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ContractStatus = Literal["PASS", "HAZARD", "FAIL", "UNKNOWN"]


# DEC-V61-040: surface DEC-V61-038 attestor verdict + per-check breakdown.
# The attestor is written into the fixture at audit-fixture time but was
# never threaded through the API until now. "ATTEST_NOT_APPLICABLE" covers
# the case where no solver log is available (reference/visual_only tiers).
AttestVerdict = Literal[
    "ATTEST_PASS", "ATTEST_HAZARD", "ATTEST_FAIL", "ATTEST_NOT_APPLICABLE"
]


class AttestorCheck(BaseModel):
    """Single A1..A6 check outcome. concern_type matches the string the
    verdict engine uses for hard-FAIL detection (SOLVER_CRASH_LOG,
    SOLVER_ITERATION_CAP, CONTINUITY_NOT_CONVERGED, RESIDUALS_ABOVE_TARGET,
    BOUNDING_RECURRENT, NO_RESIDUAL_PROGRESS)."""

    check_id: str
    verdict: Literal["PASS", "HAZARD", "FAIL"]
    concern_type: str | None = None
    summary: str = ""


class AttestorVerdict(BaseModel):
    """Aggregate attestor result: overall verdict + per-check breakdown.

    Mirrors src.convergence_attestor.AttestationResult at the API boundary.
    """

    overall: AttestVerdict
    checks: list[AttestorCheck] = Field(default_factory=list)
"""Three-state semantics: PASS (within tolerance, no hazard armed),
HAZARD (within tolerance but a silent-pass hazard is armed), FAIL
(outside tolerance OR contract precondition unmet). UNKNOWN when
no measurement is available yet."""


RunCategory = Literal[
    "reference",
    "real_incident",
    "under_resolved",
    "wrong_model",
    "grid_convergence",
    "audit_real_run",
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
- grid_convergence: a run at a specific mesh density within a convergence
  sweep (run_id convention `mesh_<N>` — e.g. `mesh_20`, `mesh_80`). These
  feed the interactive mesh-density slider; individually they're coarse /
  fine snapshots, collectively they demonstrate asymptotic convergence.
- audit_real_run: a measurement produced by an actual OpenFOAM solver run
  via FoamAgentExecutor — not curated, not synthesized. Audit-grade
  evidence. Distinguished from real_incident: incidents are historical
  artifacts preserved for decision traceability, audit_real_run are the
  current-authoritative solver outputs that back the signed audit
  package. One per case per commit. Phase 5a onward.
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


class RunSummary(BaseModel):
    """Per-case run distribution — rendered as a small pill on catalog cards.

    `total` counts every curated run (reference/real_incident/under_resolved/
    wrong_model). `verdict_counts` breaks those down by expected_verdict,
    letting the UI show "3 runs · 1 PASS · 2 FAIL" without refetching all
    validation-reports."""

    total: int = 0
    verdict_counts: dict[str, int] = Field(default_factory=dict)


class CaseIndexEntry(BaseModel):
    """One row of GET /api/cases."""

    case_id: str = Field(..., description="whitelist.yaml `id` field")
    name: str = Field(..., description="human-readable case name")
    flow_type: str
    geometry_type: str
    turbulence_model: str
    has_gold_standard: bool
    has_measurement: bool
    run_summary: RunSummary = Field(default_factory=RunSummary)
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
    """The extracted quantity from a solver run.

    DEC-V61-036 G1: `value` may be None when the extractor could not locate
    the gold's target quantity in the run's key_quantities (either direct
    name or via result_comparator alias table). `quantity` carries the
    canonical gold-name the extractor attempted to resolve; when
    `extraction_source == "no_numeric_quantity"` the downstream
    _derive_contract_status forces FAIL with MISSING_TARGET_QUANTITY concern.
    """

    value: float | None
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
    quantity: str | None = None
    extraction_source: str | None = None


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
    # DEC-V61-039: surface the profile-level pointwise verdict alongside
    # the scalar contract_status. For gold-overlay cases (currently only
    # LDC) the comparison_report service computes PASS/PARTIAL/FAIL from
    # point-in-tolerance counts — that answer differs from scalar
    # contract_status when the scalar happens to hit a passing profile
    # point but other points fail (LDC: 11/17 points pass → PARTIAL).
    # Including both verdicts lets the UI honestly surface the split-brain
    # instead of picking one and hiding the other.
    profile_verdict: Literal["PASS", "PARTIAL", "FAIL"] | None = Field(
        None,
        description=(
            "Pointwise profile verdict for gold-overlay cases; None when "
            "no profile comparison is available (scalar-only cases or "
            "visual-only runs)."
        ),
    )
    profile_pass_count: int | None = Field(
        None,
        description=(
            "Number of gold reference points within tolerance band. None "
            "when profile_verdict is None."
        ),
    )
    profile_total_count: int | None = None
    # DEC-V61-040: solver-iteration attestor verdict (A1..A6). Null when the
    # fixture lacks an `attestation` block (pre-DEC-038 fixtures or
    # visual_only/reference tiers where no solver log exists). The API
    # preserves the verdict verbatim from the fixture so the UI can render
    # the per-check breakdown without recomputing.
    attestation: AttestorVerdict | None = None


# ---------------------------------------------------------------------------
# Phase 7a — Field Artifacts
# ---------------------------------------------------------------------------

FieldArtifactKind = Literal["vtk", "csv", "residual_log"]
"""Kind of artifact surfaced by GET /api/runs/{run_id}/field-artifacts.

- vtk: OpenFOAM foamToVTK output (binary, ~1 MB/case for 129x129 LDC)
- csv: sampled profile data (e.g. uCenterline_U_p.xy from OpenFOAM `sets`
  function object)
- residual_log: residuals.csv (derived from OpenFOAM `residuals` function
  object .dat output) or raw log.<solver>

Phase 7a captures these per audit_real_run; Phase 7b renders them to PNG/HTML.
"""


class FieldArtifact(BaseModel):
    """A single field artifact captured by Phase 7a.

    Paths are served via GET /api/runs/{run_id}/field-artifacts/{filename}
    (separate download endpoint; this struct carries metadata).
    """

    kind: FieldArtifactKind
    filename: str = Field(..., description="Basename only; no directory segments.")
    url: str = Field(
        ...,
        description="Download URL under /api/runs/{run_id}/field-artifacts/{filename}",
    )
    sha256: str = Field(
        ...,
        pattern=r"^[0-9a-f]{64}$",
        description="Lowercase hex SHA256 of file bytes.",
    )
    size_bytes: int = Field(..., ge=0)


class FieldArtifactsResponse(BaseModel):
    """Response for GET /api/runs/{run_id}/field-artifacts."""

    run_id: str
    case_id: str
    run_label: str
    timestamp: str = Field(
        ...,
        description="YYYYMMDDTHHMMSSZ UTC — resolved via per-run manifest.",
    )
    artifacts: list[FieldArtifact]
