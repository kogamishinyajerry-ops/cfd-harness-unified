"""DEC-V61-156/157/158 (N6.1/N6.2) · AI advisor wire schemas.

V130 advisory-only contract: every advisor finding/diagnosis MUST
carry a citation that resolves to a real corpus chunk. No citation
→ no finding. The schemas live here (not under services/) because
they are part of the public route contract surface (N6.2 / N6.3
will reuse them).

Schema stability: external auditors / engineers' scripts pattern-match
on ``citation.chunk_id`` and ``citation.sha`` to verify the rendered
chunk text actually matches the corpus the system loaded. SHA in the
response is the integrity anchor.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CorpusSource = Literal["openfoam_corpus", "project_decisions"]


class CitedChunk(BaseModel):
    """One retrieved corpus chunk with full provenance.

    ``chunk_id`` is stable across process restarts as long as the
    underlying file content does not change (it is derived from
    ``path`` + ``byte_offset``). ``sha`` is the SHA-256 of the
    chunk text bytes; engineers can paste the SHA into ``shasum``
    to verify the rendered text on the UI matches the system's
    loaded copy.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1, max_length=256)
    source: CorpusSource
    path: str = Field(
        min_length=1,
        max_length=512,
        description="Repo-relative path of the source file",
    )
    sha: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the chunk text",
    )
    section_anchor: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Markdown section header path (e.g. '##/Mesh quality')",
    )
    byte_offset: int = Field(ge=0, description="Byte offset in source file")
    text: str = Field(
        min_length=1,
        max_length=4096,
        description="Chunk text content (truncated for wire transfer)",
    )


class CorpusStats(BaseModel):
    """Loader-level summary surfaced for audit + telemetry purposes.

    The ``llm_available`` flag is NOT here — that lives on per-route
    responses. ``CorpusStats`` describes what the loader ingested,
    independent of LLM provider state.
    """

    model_config = ConfigDict(extra="forbid")

    total_chunks: int = Field(ge=0)
    total_files: int = Field(ge=0)
    sources: dict[CorpusSource, int] = Field(
        default_factory=dict,
        description="Chunk count per CorpusSource",
    )
    corpus_sha: str = Field(
        min_length=64,
        max_length=64,
        description=(
            "SHA-256 of the sorted chunk_id||sha pairs — stable "
            "fingerprint of the loaded corpus across process restarts"
        ),
    )


# ────────── N6.2 · AI 审查 (case review) wire schema ──────────


FindingArea = Literal["geometry", "mesh", "physics", "solver", "output"]
FindingSeverity = Literal["critical", "warning", "info"]
FindingSource = Literal["llm", "rule_based"]


class ReviewFinding(BaseModel):
    """One advisor finding. Engineer reads it and decides.

    Hard rules (charter §"Why citation grounding is mandatory"):
      * ``citation`` is REQUIRED (Optional only at parse time during
        LLM-output validation; the service drops findings whose
        citation does not resolve to a loaded corpus chunk).
      * ``recommended_change`` is metadata-only: a string description
        the engineer reads. It is NEVER a callable, route, or
        action descriptor. The V132 contract test enforces no
        mutation function is invoked on this code path.
    """

    model_config = ConfigDict(extra="forbid")

    severity: FindingSeverity
    area: FindingArea
    message: str = Field(min_length=1, max_length=500)
    citation: CitedChunk = Field(
        ...,
        description=(
            "Corpus chunk grounding the finding. Server-side verified "
            "to resolve to a loaded chunk; missing → finding dropped."
        ),
    )
    recommended_change: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Metadata-only suggestion for the engineer to read. Never "
            "a callable or route. UI renders as text + copy button."
        ),
    )
    source: FindingSource = Field(
        description=(
            "'llm' = composed by LLM with citation grounding. "
            "'rule_based' = derived from existing rule-based emitters "
            "(N5.2 honest issue list / N2.4 / N4.3 / N4.5)."
        ),
    )


class ReviewResponse(BaseModel):
    """Top-level wire response for ``GET /api/cases/{id}/ai-review``.

    ``llm_available`` exposes the degradation mode transparently — UI
    surfaces a "rule-based, LLM unavailable" banner when False.
    ``corpus_sha`` lets engineers verify the rendered citations were
    sourced from a known corpus state.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=256)
    findings: list[ReviewFinding] = Field(default_factory=list)
    llm_available: bool
    corpus_sha: str = Field(min_length=64, max_length=64)
    degradation_note: Optional[str] = Field(
        default=None,
        max_length=500,
        description=(
            "Set when llm_available=False to explain the degraded path "
            "(e.g. 'DEEPSEEK_API_KEY unset; rule-based subset only')."
        ),
    )
    generated_at: str = Field(
        description="ISO 8601 UTC timestamp when the review was built.",
    )


__all__ = [
    "CitedChunk",
    "CorpusSource",
    "CorpusStats",
    "FindingArea",
    "FindingSeverity",
    "FindingSource",
    "ReviewFinding",
    "ReviewResponse",
]
