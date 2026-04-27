"""Case-YAML editor backing service.

Phase 1 Case Editor persists edits to ``ui/backend/user_drafts/{case_id}.yaml``.
This is *never* allowed to overwrite ``knowledge/whitelist.yaml`` or
``knowledge/gold_standards/**`` — those are hard-floor-1 / hard-floor-2
territory per DEC-V61-002. The editor is a preview/lint surface with a
promote-to-main flow gated by an external Gate review (out of Phase 1
scope).

Source-of-truth (for the "revert to source" button):
    1. ``ui/backend/user_drafts/{case_id}.yaml`` — last saved draft
    2. synthesised from ``knowledge/whitelist.yaml`` for the case_id
       (dumped with yaml.safe_dump)

Public:
    get_case_yaml(case_id)           → (source, is_draft)
    put_case_yaml(case_id, yaml_text) → (saved_path, lint_result)
    revert_case_yaml(case_id)        → (source, deleted)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from ui.backend.services.validation_report import (
    REPO_ROOT,
    _load_whitelist,
)


DRAFTS_DIR = REPO_ROOT / "ui" / "backend" / "user_drafts"


@dataclass(slots=True)
class DraftSource:
    yaml_text: str
    origin: Literal["draft", "whitelist", "missing"]
    draft_path: str | None  # absolute POSIX for UI display


@dataclass(slots=True)
class LintResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def _ensure_drafts_dir() -> None:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


def is_safe_case_id(case_id: str) -> bool:
    """Path-traversal guard: case_id must be alphanum + ``_`` + ``-`` only."""
    return all(c.isalnum() or c in ("_", "-") for c in case_id) and bool(case_id)


def _draft_path(case_id: str) -> Path:
    if not is_safe_case_id(case_id):
        raise ValueError(f"unsafe case_id: {case_id!r}")
    return DRAFTS_DIR / f"{case_id}.yaml"


def get_case_yaml(case_id: str) -> DraftSource:
    """Return the current editor source for a case.

    Order: (1) user_drafts/{case_id}.yaml if it exists, else
    (2) knowledge/whitelist.yaml entry dumped as standalone YAML doc.
    """
    draft = _draft_path(case_id)
    if draft.exists():
        return DraftSource(
            yaml_text=draft.read_text(encoding="utf-8"),
            origin="draft",
            draft_path=str(draft),
        )
    whitelist = _load_whitelist()
    case = whitelist.get(case_id)
    if case is None:
        return DraftSource(yaml_text="", origin="missing", draft_path=None)
    dumped = yaml.safe_dump(
        case, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return DraftSource(yaml_text=dumped, origin="whitelist", draft_path=None)


def lint_case_yaml(yaml_text: str) -> LintResult:
    """Parse + structural-shape check. Returns ok=False only on parse error;
    structural gaps emit warnings (still savable)."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        errors.append(str(exc))
        return LintResult(ok=False, errors=errors, warnings=warnings)

    if not isinstance(parsed, dict):
        errors.append("Top-level must be a mapping (dict). Got: %s" % type(parsed).__name__)
        return LintResult(ok=False, errors=errors, warnings=warnings)

    # Structural warnings (non-blocking).
    required = ("id", "name", "flow_type", "geometry_type", "turbulence_model")
    for key in required:
        if key not in parsed:
            warnings.append(f"Missing recommended field: {key!r}")
    gs = parsed.get("gold_standard")
    if gs is not None and not isinstance(gs, dict):
        warnings.append("gold_standard should be a mapping if present")

    return LintResult(ok=True, errors=errors, warnings=warnings)


def put_case_yaml(case_id: str, yaml_text: str) -> tuple[str, LintResult]:
    """Write draft. Returns (draft_path, lint_result).

    Parse failure short-circuits: no write, errors returned.
    Structural warnings do NOT block write.
    """
    lint = lint_case_yaml(yaml_text)
    if not lint.ok:
        return ("", lint)
    _ensure_drafts_dir()
    path = _draft_path(case_id)
    path.write_text(yaml_text, encoding="utf-8")
    return (str(path), lint)


def revert_case_yaml(case_id: str) -> DraftSource:
    """Delete the draft (if any) and return the whitelist-sourced text."""
    path = _draft_path(case_id)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            # Fuse sandboxes occasionally block unlink; fall back to rename.
            import time as _t
            path.rename(path.with_suffix(f".yaml.deleted.{int(_t.time())}"))
    return get_case_yaml(case_id)
