"""DEC-V61-168 / B.5.2 · /state alias route tests.

Surfaced by DOGFOOD_REPORT_LIVE F1: engineers expect /state, not
/state-preview. Verify the alias delegates to the same service and
returns identical payload.
"""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi.testclient import TestClient

from ui.backend.services.case_manifest import (
    CaseManifest,
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


def _stage(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    (case_dir / "system").mkdir()
    (case_dir / "system" / "controlDict").write_text(
        _VALID_CONTROLDICT, encoding="utf-8"
    )
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-05-07T00-00-00Z_{secrets.token_hex(4)}"


def test_state_alias_returns_same_payload_as_state_preview(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    client = _client()
    alias = client.get(f"/api/cases/{case_id}/state")
    canonical = client.get(f"/api/cases/{case_id}/state-preview")

    assert alias.status_code == 200
    assert canonical.status_code == 200
    assert alias.json() == canonical.json()


def test_state_alias_passes_next_action_query(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    client = _client()
    alias = client.get(
        f"/api/cases/{case_id}/state?next_action=switch_solver"
    )
    canonical = client.get(
        f"/api/cases/{case_id}/state-preview?next_action=switch_solver"
    )
    assert alias.status_code == 200
    assert canonical.status_code == 200
    assert alias.json() == canonical.json()


def test_state_alias_404_for_missing_case(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    client = _client()
    resp = client.get(f"/api/cases/{_safe_id()}/state")
    assert resp.status_code == 404


def test_state_alias_400_for_unsafe_case_id(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    client = _client()
    resp = client.get("/api/cases/..%2Fevil/state")
    assert resp.status_code in (400, 404)
