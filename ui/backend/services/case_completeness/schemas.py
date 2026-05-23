"""DEC-V61-116 · response schemas for the case-completeness analyzer."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Severity = Literal["critical", "warning", "info"]
CaseKind = Literal["whitelist", "imported_user", "draft"]


class MissingField(BaseModel):
    """One entry in the 'still-needed' list.

    `severity = critical` blocks `ready_for_archive`. `warning` and `info`
    do not block but are surfaced for engineer awareness.

    `field_path` uses JSON-path notation rooted at the case YAML
    (e.g. ``physics.turbulence_model``, ``boundary_conditions.inlet.patch_type``).
    UI deep-link hooks will route field_path → step + form-field highlight,
    but that wiring is V61-117 scope.
    """

    field_path: str = Field(
        ...,
        description="JSON-path rooted at the case YAML. Period-separated.",
    )
    severity: Severity = Field(
        ...,
        description=(
            "critical = blocks archive · warning = surface but non-blocking · "
            "info = nice-to-have for completeness percentage"
        ),
    )
    why: str = Field(
        ...,
        description=(
            "Human-readable reason in zh/en. Names the rule that flagged "
            "this field (manifest schema, physics contract precondition, "
            "Re-appropriate turbulence check, etc.)"
        ),
    )
    suggested_default: Any | None = Field(
        default=None,
        description=(
            "Optional fallback value the UI may auto-fill when the user "
            "clicks [接受建议]. None means no auto-fill (engineer types "
            "manually). Surfaced in API response but Tier-A UI does not "
            "yet apply it."
        ),
    )
    suggested_skeleton: dict[str, Any] | None = Field(
        default=None,
        description=(
            "DEC-V61-202-SUB-M31-CYCLE1 · domain-aware form helper. "
            "Optional structural dict skeleton for fields that are too "
            "complex for a scalar `suggested_default` (e.g. `bc.patches` "
            "needs a multi-key nested dict). The rail renders a separate "
            "'Apply skeleton' CTA when this is present; the engineer "
            "overrides specific values afterwards. None = no skeleton "
            "offered for this field."
        ),
    )


class CaseCompletenessReport(BaseModel):
    """The right-rail card payload."""

    case_id: str
    case_kind: CaseKind = Field(
        ...,
        description=(
            "Provenance of the case under analysis. Determines which "
            "completeness rules apply: whitelist gets the full gold "
            "contract; imported_user gets a minimal contract; draft "
            "(whitelist-fork) gets the gold contract plus drift checks."
        ),
    )
    ready_for_archive: bool = Field(
        ...,
        description=(
            "True when blocked_by_critical == 0 AND all manifest required "
            "fields are present. Warnings + info do NOT block."
        ),
    )
    blocked_by_critical: int = Field(
        ...,
        ge=0,
        description="Count of MissingField entries with severity == critical.",
    )
    present_count: int = Field(
        ...,
        ge=0,
        description=(
            "Number of fields the analyzer expected AND found. Counted "
            "by the same rule set that produced `total_count`."
        ),
    )
    total_count: int = Field(
        ...,
        ge=0,
        description=(
            "Total fields the analyzer expected for this case_kind. Sum "
            "of (manifest required) + (gold-contract preconditions) where "
            "applicable."
        ),
    )
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="100.0 * present_count / total_count, rounded to 1dp.",
    )
    missing: list[MissingField] = Field(default_factory=list)
    notes: list[str] = Field(
        default_factory=list,
        description=(
            "Contextual explanations the UI can render below the missing "
            "list. Examples: 'this case has no gold standard linked; "
            "using minimal contract', 'imported STL had ingest warnings — "
            "review before archive'."
        ),
    )
