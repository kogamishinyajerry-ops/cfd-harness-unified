"""DEC-V61-156/157 (N6.1) · AI advisor wire schemas.

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
