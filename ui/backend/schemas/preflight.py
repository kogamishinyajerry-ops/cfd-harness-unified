"""Preflight schema · Stage 4 GuardedRun MVP per Codex industrial-workbench
meeting 2026-04-25.

Backs `<RunRail>`: a checkpoint visualization shown above the Run button.
Each check has a category (physics / schema / mesh / gold_standard /
adapter) and a tri-state verdict (pass / fail / partial / skip). Failures
expose evidence_ref so the user can see *why* the gate is red, not just
that it is red.

Stage 4 close trigger: ≥5 distinct preflight categories surfaced. We
ship 5 here; new categories slot in additively.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# Status tri-state — matches existing harness conventions ("partial" used
# by physics_precondition rows that have caveats).
PreflightStatus = str  # Literal["pass", "fail", "partial", "skip"]

# Category — small closed set for now; new entries land additively.
PreflightCategory = str  # Literal["physics", "schema", "mesh", "gold_standard", "adapter"]


class PreflightCheck(BaseModel):
    """One checkpoint shown as a row in <RunRail>."""

    category: PreflightCategory
    id: str = Field(..., description="Stable id within case (used as React key)")
    label_zh: str = Field(..., description="Short Chinese label for the row title")
    label_en: Optional[str] = None
    status: PreflightStatus
    evidence: Optional[str] = Field(
        None,
        description=(
            "Free-form rationale: why pass, or what failed and where. "
            "Surfaced verbatim under the row when the user expands."
        ),
    )
    consequence: Optional[str] = Field(
        None,
        description=(
            "What downstream pipeline step breaks if this gate fails. "
            "Empty for pass-state rows."
        ),
    )


class PreflightCounts(BaseModel):
    """Roll-up counters for the header strip in <RunRail>."""

    pass_: int = Field(0, alias="pass")
    fail: int = 0
    partial: int = 0
    skip: int = 0
    total: int = 0

    model_config = {"populate_by_name": True}


class PreflightSummary(BaseModel):
    """Top-level response for `/api/cases/{case_id}/preflight`."""

    case_id: str
    checks: list[PreflightCheck]
    counts: PreflightCounts
    n_categories: int = Field(
        ...,
        description=(
            "Number of distinct categories surfaced. Stage 4 close trigger "
            "requires ≥5; this field makes the trigger machine-checkable."
        ),
    )
    overall: PreflightStatus = Field(
        ...,
        description=(
            "Aggregate verdict: 'fail' if any hard check fails, 'partial' "
            "if any partial without hard fail, else 'pass'. 'skip' only if "
            "literally no checks ran."
        ),
    )
    diagnostic_note: Optional[str] = None
