"""DEC-V61-153 (N5.2) · honest issue list schema.

Pure structured-data schema. The enumerator walks case state and
produces an `IssueList`; the engineer reads the list and decides.
**No AI prose anywhere** — charter §risk-register row 2: "honest
issue list MUST NOT generate AI prose; it lists structured data
only".

Severity ladder:
  * critical — case will not run / will produce garbage results
                (e.g. mesh missing, physics not committed)
  * warning  — case will run but result quality is degraded
                (e.g. checkMesh failed, residuals stalled)
  * info     — non-blocking note (e.g. fast_survey tier picked,
                LES sub-grid model TODO)

Each Issue carries:
  * severity literal
  * source_rule_id — stable enum the UI pattern-matches on
  * scope — which area: geometry / mesh / physics / solver / output
  * message — short factual statement (NO AI prose)
  * details — optional structured key/value bundle

Stable wire schema: external auditors / engineers' scripts can
pattern-match on `source_rule_id` to programmatically check whether
specific issues are present.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


IssueSeverity = Literal["critical", "warning", "info"]

IssueScope = Literal[
    "geometry",
    "mesh",
    "physics",
    "solver",
    "output",
]

# Stable enum the UI + audit scripts pattern-match on. Adding a new
# rule MUST extend this literal — tests assert every rule the
# enumerator can emit is in this set.
SourceRuleId = Literal[
    # Geometry rules
    "geometry_stl_missing",
    "geometry_bbox_missing",
    "geometry_no_named_patches",
    # Mesh rules
    "mesh_polymesh_missing",
    "mesh_zero_cells",
    "mesh_dense_warning",
    "mesh_low_count_warning",
    "mesh_checkmesh_failed",
    "mesh_severe_non_ortho_faces",
    # Physics rules
    "physics_dicts_missing",
    "physics_regime_missing",
    "physics_no_citation",
    # Solver rules
    "solver_no_derivation",
    "solver_tolerance_fast_survey",
    "solver_les_subgrid_todo",
    # Output rules
    "output_residuals_stalled",
    "output_run_log_missing",
]


class Issue(BaseModel):
    """A single rule-emitted issue."""

    model_config = ConfigDict(extra="forbid")

    severity: IssueSeverity
    source_rule_id: SourceRuleId
    scope: IssueScope
    message: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description=(
            "Short factual statement. NO AI prose. Charter §risk-"
            "register row 2 enforced."
        ),
    )
    details: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description=(
            "Optional structured key/value bundle for UI rendering "
            "(e.g. {'cell_count': 50, 'threshold': 100})."
        ),
    )


class IssueList(BaseModel):
    """Top-level container. The enumerator returns this."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    issues: list[Issue] = Field(default_factory=list)
    generated_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp when the list was built.",
    )

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")


__all__ = [
    "Issue",
    "IssueList",
    "IssueScope",
    "IssueSeverity",
    "SourceRuleId",
]
