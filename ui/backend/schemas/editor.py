"""Pydantic schemas for the Case Editor (Phase 1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CaseYamlPayload(BaseModel):
    """GET /api/cases/{id}/yaml response and PUT request body."""

    case_id: str
    yaml_text: str = Field(description="Raw YAML source (UTF-8).")
    origin: Literal["draft", "whitelist", "missing"] = Field(
        description=(
            "Where yaml_text came from: 'draft' = user_drafts/{id}.yaml; "
            "'whitelist' = synthesised from knowledge/whitelist.yaml; "
            "'missing' = no source found."
        )
    )
    draft_path: str | None = Field(
        default=None,
        description="Absolute POSIX path to the on-disk draft, or null.",
    )


class CaseYamlLintResult(BaseModel):
    """Output of the server-side lint pass."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CaseYamlSaveResult(BaseModel):
    """PUT /api/cases/{id}/yaml response."""

    case_id: str
    saved: bool
    draft_path: str | None
    lint: CaseYamlLintResult
