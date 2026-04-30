"""DEC-V61-102 Phase 1.3 · build_state_preview implementation.

Returns a structured snapshot of the case directory state for the UI
"inspect-before-act" surface. Three sections:

1. ``manifest``: full v2 manifest (typed)
2. ``dict_summary``: per-allowlisted-path {exists, source, etag, line_count}
3. ``next_action_will_overwrite``: paths the named next action would
   re-author. The UI shows this list as "these manual changes would be
   lost — confirm or cancel".

The ``next_action`` parameter is one of:
  - "setup_ldc_bc"     — setup_ldc_bc rewrites system/* + constant/*
  - "setup_channel_bc" — same set, different patch geometry
  - "switch_solver"    — controlDict + fvSchemes + fvSolution

If the action isn't recognized, ``next_action_will_overwrite`` returns
empty (the route layer should still render the rest of the preview).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ui.backend.services.case_dicts.allowlist import ALLOWED_RAW_DICT_PATHS
from ui.backend.services.case_manifest import (
    CaseManifest,
    ManifestNotFoundError,
    compute_etag,
    read_case_manifest,
)


# Per-action authoring footprints. Source: bc_setup.py + the eventual
# solver_profile module in Phase 3. Keep this dict in sync with both.
_ACTION_AUTHORS: dict[str, frozenset[str]] = {
    "setup_ldc_bc": frozenset(
        {
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "constant/momentumTransport",
            "constant/physicalProperties",
        }
    ),
    "setup_channel_bc": frozenset(
        {
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "constant/momentumTransport",
            "constant/physicalProperties",
        }
    ),
    "switch_solver": frozenset(
        {
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
        }
    ),
}


NextAction = Literal[
    "setup_ldc_bc", "setup_channel_bc", "switch_solver", ""
]


@dataclass(frozen=True, slots=True)
class DictSummary:
    """One row in the dict_summary list."""

    path: str
    exists: bool
    source: str  # "ai" | "user"
    etag: str | None
    line_count: int | None
    edited_at: str | None


@dataclass(frozen=True, slots=True)
class StatePreview:
    """The full preview payload."""

    case_id: str
    manifest: CaseManifest | None
    dict_summary: list[DictSummary]
    next_action_will_overwrite: list[str]
    next_action: str = ""

    def to_wire(self) -> dict:
        """Serialize for FastAPI response. Pydantic handles the
        manifest model; everything else is plain dict/list."""
        return {
            "case_id": self.case_id,
            "manifest": (
                self.manifest.model_dump(mode="json", exclude_none=False)
                if self.manifest
                else None
            ),
            "dict_summary": [
                {
                    "path": d.path,
                    "exists": d.exists,
                    "source": d.source,
                    "etag": d.etag,
                    "line_count": d.line_count,
                    "edited_at": d.edited_at,
                }
                for d in self.dict_summary
            ],
            "next_action": self.next_action,
            "next_action_will_overwrite": list(self.next_action_will_overwrite),
        }


def build_state_preview(
    case_dir: Path,
    *,
    next_action: NextAction = "",
) -> StatePreview:
    """Inspect ``case_dir`` and return a preview snapshot.

    ``next_action`` is optional — if omitted, ``next_action_will_overwrite``
    is empty (no overwrite warning). Pass it to surface the confirm
    prompt: e.g. when the user clicks Step 3's [AI 处理], the frontend
    calls ``state-preview?next_action=setup_ldc_bc`` and renders the
    overwrite list before the actual setup-bc POST.
    """
    case_id = case_dir.name

    # Manifest (might not exist on a freshly-staged case).
    manifest: CaseManifest | None = None
    try:
        manifest = read_case_manifest(case_dir)
    except ManifestNotFoundError:
        manifest = None

    override_map = (
        manifest.overrides.raw_dict_files if manifest else {}
    )

    # Per-path summary across the full allowlist.
    summaries: list[DictSummary] = []
    for path in sorted(ALLOWED_RAW_DICT_PATHS):
        abs_path = case_dir / path
        exists = abs_path.is_file()
        etag: str | None = None
        line_count: int | None = None
        if exists:
            content = abs_path.read_bytes()
            etag = compute_etag(content)
            line_count = content.count(b"\n") + (
                0 if content.endswith(b"\n") or not content else 1
            )
        entry = override_map.get(path)
        source = entry.source if entry else "ai"
        edited_at = (
            entry.edited_at.isoformat()
            if entry and entry.edited_at
            else None
        )
        summaries.append(
            DictSummary(
                path=path,
                exists=exists,
                source=source,
                etag=etag,
                line_count=line_count,
                edited_at=edited_at,
            )
        )

    # Overwrite analysis: a path is at risk if (a) the action would
    # author it AND (b) it's currently source=user. AI-authored paths
    # being re-authored is a no-op confirmation — not an overwrite.
    will_overwrite: list[str] = []
    if next_action and next_action in _ACTION_AUTHORS:
        action_paths = _ACTION_AUTHORS[next_action]
        for path in sorted(action_paths):
            entry = override_map.get(path)
            if entry and entry.source == "user":
                will_overwrite.append(path)

    return StatePreview(
        case_id=case_id,
        manifest=manifest,
        dict_summary=summaries,
        next_action=next_action,
        next_action_will_overwrite=will_overwrite,
    )


__all__ = ["build_state_preview", "StatePreview", "DictSummary"]
