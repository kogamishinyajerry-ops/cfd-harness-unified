"""DEC-V61-102 Phase 1.3 · case_inspect state-preview route tests."""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi.testclient import TestClient

from ui.backend.services.case_manifest import (
    CaseManifest,
    mark_ai_authored,
    mark_user_override,
    write_case_manifest,
)


_VALID_CONTROLDICT = """\
FoamFile { class dictionary; }
application icoFoam;
endTime 2;
"""


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_inspect.IMPORTED_DIR", target
    )
    return target


def _stage(imported_dir: Path, case_id: str, files: dict[str, str] | None = None) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    if files:
        for rel, content in files.items():
            abs_path = case_dir / rel
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-04-30T00-00-00Z_{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# Cases: clean, AI-authored, mixed AI+user, missing-files
# ---------------------------------------------------------------------------


def test_preview_clean_case_no_dicts(monkeypatch, tmp_path):
    """Freshly-imported case with no dicts authored yet:
    every allowlisted path shows exists=False, no overwrite warnings."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    resp = _client().get(f"/api/cases/{case_id}/state-preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["next_action_will_overwrite"] == []
    # Every entry in dict_summary shows exists=False.
    assert len(body["dict_summary"]) >= 5
    assert all(entry["exists"] is False for entry in body["dict_summary"])


def test_preview_ai_authored_case_no_overwrite_warning(monkeypatch, tmp_path):
    """An AI-authored case with no manual edits: re-running setup_ldc_bc
    is a no-op confirmation, NOT an overwrite. The will_overwrite list
    is empty even with next_action set."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(
        imported,
        case_id,
        files={
            "system/controlDict": _VALID_CONTROLDICT,
            "system/fvSchemes": "FoamFile {} ",
            "system/fvSolution": "FoamFile {} ",
            "constant/momentumTransport": "FoamFile {} simulationType laminar;",
            "constant/transportProperties": "FoamFile {} nu 0.01;",
        },
    )
    mark_ai_authored(
        case_dir,
        relative_paths=[
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "constant/momentumTransport",
            "constant/transportProperties",
        ],
        action="setup_ldc_bc",
    )

    resp = _client().get(
        f"/api/cases/{case_id}/state-preview?next_action=setup_ldc_bc"
    )
    assert resp.status_code == 200
    body = resp.json()
    # All AI-authored — no warning.
    assert body["next_action_will_overwrite"] == []
    # dict_summary reflects existence + ai source.
    summary = {e["path"]: e for e in body["dict_summary"]}
    assert summary["system/controlDict"]["exists"] is True
    assert summary["system/controlDict"]["source"] == "ai"
    assert summary["system/fvSchemes"]["source"] == "ai"


def test_preview_mixed_ai_user_overwrite_warning(monkeypatch, tmp_path):
    """Case where user manually edited some dicts, AI authored others:
    next_action=setup_ldc_bc lists ONLY the user-overridden paths in
    will_overwrite — those are what would be clobbered."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(
        imported,
        case_id,
        files={
            "system/controlDict": _VALID_CONTROLDICT,
            "system/fvSchemes": "FoamFile {} ",
        },
    )
    mark_ai_authored(
        case_dir,
        relative_paths=["system/controlDict", "system/fvSchemes"],
        action="setup_ldc_bc",
    )
    # User edits controlDict.
    mark_user_override(
        case_dir,
        relative_path="system/controlDict",
        new_content=_VALID_CONTROLDICT.encode("utf-8"),
    )

    resp = _client().get(
        f"/api/cases/{case_id}/state-preview?next_action=setup_ldc_bc"
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["next_action_will_overwrite"] == ["system/controlDict"]
    summary = {e["path"]: e for e in body["dict_summary"]}
    assert summary["system/controlDict"]["source"] == "user"
    assert summary["system/controlDict"]["edited_at"] is not None
    assert summary["system/fvSchemes"]["source"] == "ai"


def test_preview_missing_manifest_returns_null_manifest(monkeypatch, tmp_path):
    """A case_dir without a manifest yet: the preview still works,
    manifest is None, dict_summary lists allowlisted paths with
    exists=False or actual file state if files exist."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = imported / case_id
    case_dir.mkdir()
    # No manifest written.
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(_VALID_CONTROLDICT)

    resp = _client().get(f"/api/cases/{case_id}/state-preview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["manifest"] is None
    summary = {e["path"]: e for e in body["dict_summary"]}
    # File on disk shows exists=True even without manifest.
    assert summary["system/controlDict"]["exists"] is True
    # No manifest → defaults to ai.
    assert summary["system/controlDict"]["source"] == "ai"
    # No next_action → no warnings.
    assert body["next_action_will_overwrite"] == []


def test_preview_unknown_action_silently_no_warning(monkeypatch, tmp_path):
    """Unknown next_action string doesn't crash — just empty warning list."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    resp = _client().get(
        f"/api/cases/{case_id}/state-preview?next_action=hypothetical_future_action"
    )
    assert resp.status_code == 200
    assert resp.json()["next_action_will_overwrite"] == []


def test_preview_unknown_case_404(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get("/api/cases/imported_does_not_exist_xxxx/state-preview")
    assert resp.status_code == 404
