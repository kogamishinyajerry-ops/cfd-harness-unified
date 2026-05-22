"""DEC-V61-202-SUB-M30-CYCLE1 · `GET /api/cases/{case_id}/workbench_frame`.

The route handler is a thin wrapper around `decide()` — its job is
loading inputs from disk (manifest + audit artifacts +
CaseCompletenessReport) and packaging them as `CaseStateSnapshot`.
The actual decision logic lives in `services/workbench_decide.py`
where it can be unit-tested without the FastAPI machinery.

Per V130: no LLM call. `decide()` is a pure function of state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query

from ui.backend.schemas.manifest_patch import (
    ManifestPatchRequest,
    ManifestPatchResponse,
)
from ui.backend.schemas.workbench_frame import (
    CaseStateSnapshot,
    WorkbenchFrame,
)
from ui.backend.services.case_completeness import (
    CaseNotFoundError,
    analyze_case_completeness,
)
from ui.backend.services.case_scaffold.template_clone import IMPORTED_DIR
from ui.backend.services.case_drafts import DRAFTS_DIR
from ui.backend.services.manifest_patch import (
    PatchConflict,
    PatchPathError,
    apply_field_path_patch,
)
from ui.backend.services.validation_report import _load_whitelist
from ui.backend.services.workbench_decide import decide

router = APIRouter()


_ARTIFACT_FILES = (
    "geometry_report.json",
    "mesh_report.json",
    "bc_quality.json",
    "bc_audit.json",
    "trust_report.json",
)


@router.get(
    "/cases/{case_id}/workbench_frame",
    response_model=WorkbenchFrame,
    summary="Workbench dynamic frame (DEC-V61-202 cycle 1)",
)
def get_workbench_frame(
    case_id: str,
    step: int = Query(..., ge=1, le=5, description="Current step (1..5)"),
    focus_patch: str | None = Query(default=None),
    focus_region: str | None = Query(default=None),
    focus_panel: str | None = Query(default=None),
) -> WorkbenchFrame:
    """Return the dynamic workbench frame for (case_id, step, focus).

    The frame is what the guided UX renders additively above the
    existing per-step React components in `StepPanelShell.tsx`.
    """

    manifest, case_dir = _load_manifest(case_id)
    if manifest is None and case_dir is None:
        raise HTTPException(
            status_code=404, detail=f"case_id not found: {case_id}"
        )

    artifacts = _load_artifacts(case_dir) if case_dir else {}
    completeness = _safe_completeness(case_id)

    state = CaseStateSnapshot(
        case_id=case_id,
        step=step,
        manifest=manifest or {},
        artifacts=artifacts,
        completeness=completeness,
        focus_patch=focus_patch,
        focus_region=focus_region,
        focus_panel=focus_panel,
    )
    return decide(state)


# ────────────────────────── loaders ──────────────────────────


def _load_manifest(case_id: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Locate the case + return (manifest_dict, case_dir).

    Resolution priority mirrors `case_completeness._resolve_*` + adds a
    whitelist branch (Codex R0 P1 fix · 2026-05-22): benchmark cases
    that ship in `knowledge/whitelist.yaml` must be openable in the
    workbench. Resolution order:
        1. imported_user case (full case_dir with manifest + artifacts)
        2. flat draft YAML (whitelist-fork) — no case_dir
        3. whitelist entry — no case_dir; manifest is the catalog entry
        4. neither → (None, None)
    """
    imported = IMPORTED_DIR / case_id / "case_manifest.yaml"
    if imported.is_file():
        return _read_yaml(imported), imported.parent

    draft = DRAFTS_DIR / f"{case_id}.yaml"
    if draft.is_file():
        return _read_yaml(draft), None

    # Codex R0 P1: whitelist resolver. The whitelist entry is the
    # abstract case definition (solver, turbulence_model, parameters,
    # gold_standard, etc.) — there's no on-disk case_dir, so no audit
    # artifacts. completeness analysis still works (whitelist path
    # in case_completeness.analyzer); decide() falls through to gap-
    # driven rail content.
    whitelist = _load_whitelist()
    if case_id in whitelist:
        return whitelist[case_id], None

    return None, None


def _load_artifacts(case_dir: Path) -> dict[str, dict]:
    """Load known audit artifacts from `<case_dir>/artifacts/*.json`.

    Silently skips missing / malformed files — `decide()` is robust to
    artifacts not being present yet (especially Step 1-3 where they're
    not produced).
    """
    out: dict[str, dict] = {}
    artifacts_dir = case_dir / "artifacts"
    if not artifacts_dir.is_dir():
        return out
    for name in _ARTIFACT_FILES:
        p = artifacts_dir / name
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out[name] = data
        except (OSError, json.JSONDecodeError):
            # decide() degrades gracefully if an artifact won't parse
            continue
    return out


def _safe_completeness(case_id: str) -> dict | None:
    """Run CaseCompletenessReport (DEC-V61-116); return None on failure.

    `decide()` already handles a None completeness payload (it just
    returns no info_gap-driven content). Wrapping the call protects
    the frame endpoint from completeness analyzer bugs.
    """
    try:
        report = analyze_case_completeness(case_id)
    except CaseNotFoundError:
        return None
    except Exception:
        # Defensive: the completeness analyzer composes many rule
        # layers and we don't want any of them to take down the frame.
        return None
    if report is None:
        return None
    return report.model_dump()


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


# ────────────────────────── PATCH /api/cases/{id}/manifest ──────────────────────────


@router.patch(
    "/cases/{case_id}/manifest",
    response_model=ManifestPatchResponse,
    summary="Apply a field-path PATCH to a case's manifest (DEC-V61-202 cycle 2)",
)
def patch_manifest_field(
    case_id: str, request: ManifestPatchRequest
) -> ManifestPatchResponse:
    """Apply one field-path write to the manifest.

    Workflow:
        1. Engineer reads WorkbenchFrame → captures `manifest_state_sha`
        2. Engineer clicks a rail CTA → frontend PATCHes here
        3. Backend validates state_sha, applies write, re-validates schema
        4. On success: returns new state_sha; frontend refetches frame
        5. On 409: case changed since frame was issued; frontend refetches
        6. On schema invalid: returns 200 + success=False + errors;
           engineer can re-edit

    Whitelist cases auto-fork to a draft on first PATCH — the engineer's
    edit doesn't mutate the immutable catalog.
    """
    try:
        response = apply_field_path_patch(case_id, request)
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PatchPathError as e:
        raise HTTPException(status_code=400, detail=f"invalid field_path: {e}")
    except PatchConflict as e:
        # 409 + headers expose the current state_sha so the frontend
        # can update its expected_state_sha without a separate fetch.
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(e),
                "current_state_sha": e.current_state_sha,
            },
        )
    return response
