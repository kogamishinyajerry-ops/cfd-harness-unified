"""Pydantic schemas for the M5 STL case-import surface.

Mirrors the dataclass returns from ``ui.backend.services.geometry_ingest`` in
a JSON-serializable form. The route returns these to the frontend so
``ImportPage.tsx`` can render the ingest report card.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


UnitGuess = Literal["m", "mm", "in", "unknown"]


class PatchInfoPayload(BaseModel):
    name: str
    face_count: int


class IngestReportPayload(BaseModel):
    is_watertight: bool
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    bbox_extent: tuple[float, float, float]
    unit_guess: UnitGuess
    solid_count: int
    face_count: int
    is_single_shell: bool
    patches: list[PatchInfoPayload]
    all_default_faces: bool
    warnings: list[str]
    errors: list[str]


class ImportSTLResponse(BaseModel):
    case_id: str
    ingest_report: IngestReportPayload
    edit_url: str


class ImportRejection(BaseModel):
    """Returned as 4xx body when ingest rejects."""

    reason: str
    failing_check: str
    ingest_report: IngestReportPayload | None = None
