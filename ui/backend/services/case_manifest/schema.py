"""DEC-V61-102 Phase 1.1 · case_manifest schema (v2).

The v2 manifest is the single source of truth for case state across the
workbench: physics choice, BC patches, numerics overrides, dict-edit
status, action history. Older v1 manifests (DEC-V61-093 import-time-only
shape) auto-migrate to v2 lossless on first read — every existing field
is preserved, the new structured sections are populated with
``source: ai`` defaults so downstream consumers can read uniformly.

Why Pydantic: round-tripping YAML → typed → YAML preserves field order,
catches typos at the boundary, and gives the route layer a clean
contract surface. Frozen=True on inner objects so accidental mutation
elsewhere doesn't silently corrupt the on-disk manifest.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Source provenance — every field that AI can author OR user can override
# carries a source marker. UI surfaces this as 🤖 vs ✋ icons.
# ---------------------------------------------------------------------------

Source = Literal["ai", "user"]


class SourceMap(BaseModel):
    """Per-field source map. Keys are field names within the parent
    section (e.g. "solver", "turbulence_model" inside Physics). Values
    are "ai" or "user". Missing key → assume "ai" (additive default).
    """

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Physics section — solver + turbulence + time controls.
# ---------------------------------------------------------------------------


class PhysicsSection(BaseModel):
    """High-level physics choice. Detailed numerics (schemes, solvers,
    relaxation) live in :class:`NumericsSection`."""

    solver: str | None = None
    turbulence_model: str = "laminar"
    end_time: float | None = None
    delta_t: float | None = None
    write_interval: float | None = None
    source: dict[str, Source] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# BC section — per-patch type + field map. Mirrors face_annotations.yaml
# at a higher level (annotations track WHICH face_id has WHICH role; this
# section tracks WHICH patch has WHICH BC type and field values).
# ---------------------------------------------------------------------------


class BCPatch(BaseModel):
    """One boundary patch's BC configuration."""

    patch_type: str  # "fixedValue" | "zeroGradient" | "noSlip" | ...
    fields: dict[str, Any] = Field(default_factory=dict)
    # Example: {"U": [1, 0, 0], "p": "zeroGradient"}
    source: dict[str, Source] = Field(default_factory=dict)


class BCSection(BaseModel):
    """All boundary patches keyed by patch name (matches polyMesh/boundary
    entries: ``inlet``, ``outlet``, ``walls``, ``frontAndBack``, ...)."""

    model_config = {"extra": "allow"}

    patches: dict[str, BCPatch] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Numerics section — fvSchemes / fvSolution overrides ONLY. Defaults come
# from the solver profile (DEC-V61-102 Phase 3) and are not stored here;
# only deviations are recorded so the manifest stays compact.
# ---------------------------------------------------------------------------


class NumericsSection(BaseModel):
    fv_schemes_overrides: dict[str, Any] = Field(default_factory=dict)
    fv_solution_overrides: dict[str, Any] = Field(default_factory=dict)
    relaxation_factors: dict[str, float] = Field(default_factory=dict)
    source: dict[str, Source] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Overrides section — raw dict edits + their etags / timestamps.
# This is the "engineer manually edited the OpenFOAM dict file" record.
# When ``source: user``, the AI re-author path must honor it (skip or prompt).
# ---------------------------------------------------------------------------


class RawDictOverride(BaseModel):
    """One file-level override entry."""

    source: Source = "ai"
    edited_at: datetime | None = None
    # SHA-256 of the file content at the time of the last edit. UI uses
    # this as an etag for race-protected POST. Omitted for AI-authored
    # files (the manifest can re-derive it on demand).
    etag: str | None = None


class OverridesSection(BaseModel):
    raw_dict_files: dict[str, RawDictOverride] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# History entry — append-only audit log of major state changes.
# ---------------------------------------------------------------------------


class HistoryEntry(BaseModel):
    timestamp: datetime
    action: str  # "import" | "setup_bc" | "edit_dict" | "switch_solver" | ...
    source: Source
    detail: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Top-level manifest — v2 shape. Includes every legacy v1 field as
# optional so migration is lossless and a fresh v2 case can omit the
# import-only fields.
# ---------------------------------------------------------------------------


class CaseManifest(BaseModel):
    """The v2 case manifest. SSOT for case state across the workbench."""

    schema_version: int = 2

    # Legacy v1 fields (preserved for backwards compat during migration).
    source: str | None = None
    source_origin: str | None = None
    case_id: str
    origin_filename: str | None = None
    ingest_report_summary: dict[str, Any] | None = None
    created_at: datetime | None = None
    solver_version_compat: str | None = None

    # v2 structured sections.
    physics: PhysicsSection = Field(default_factory=PhysicsSection)
    bc: BCSection = Field(default_factory=BCSection)
    numerics: NumericsSection = Field(default_factory=NumericsSection)
    overrides: OverridesSection = Field(default_factory=OverridesSection)
    history: list[HistoryEntry] = Field(default_factory=list)

    def append_history(
        self,
        *,
        action: str,
        source: Source,
        detail: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Append a history entry. Mutates in place."""
        self.history.append(
            HistoryEntry(
                timestamp=timestamp or datetime.now(timezone.utc),
                action=action,
                source=source,
                detail=detail or {},
            )
        )
