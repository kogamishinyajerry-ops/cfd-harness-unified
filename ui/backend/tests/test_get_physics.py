"""DEC-V61-168 / B.5.2 · GET /api/cases/{id}/physics tests.

Surfaced by DOGFOOD_REPORT_LIVE F3: engineers query state before mutating;
GET /physics paired with the existing POST closes the gap. Both fields
nullable: pre-commit case (Step 1 only) returns null/null, post-commit
returns full dict text.
"""
from __future__ import annotations

import secrets
from pathlib import Path

from fastapi.testclient import TestClient


_PHYS_TEXT = """\
FoamFile { class dictionary; location "constant"; object physicalProperties; }
nu 1e-5;
rho 1.0;
"""

_REGIME_TEXT = """\
FoamFile { class dictionary; location "constant"; object momentumTransport; }
simulationType laminar;
"""


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.physics.IMPORTED_DIR", target
    )
    return target


def _stage(imported_dir: Path, case_id: str, *, with_dicts: bool = False) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    constant = case_dir / "constant"
    constant.mkdir()
    if with_dicts:
        (constant / "physicalProperties").write_text(_PHYS_TEXT, encoding="utf-8")
        (constant / "momentumTransport").write_text(_REGIME_TEXT, encoding="utf-8")
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-05-07T00-00-00Z_{secrets.token_hex(4)}"


def test_get_physics_pre_commit_returns_null_pair(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, with_dicts=False)

    resp = _client().get(f"/api/cases/{case_id}/physics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["material_dict_text"] is None
    assert body["regime_dict_text"] is None


def test_get_physics_post_commit_returns_dict_texts(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, with_dicts=True)

    resp = _client().get(f"/api/cases/{case_id}/physics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert _PHYS_TEXT == body["material_dict_text"]
    assert _REGIME_TEXT == body["regime_dict_text"]


def test_get_physics_404_for_missing_case(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get(f"/api/cases/{_safe_id()}/physics")
    assert resp.status_code == 404


def test_get_physics_400_for_unsafe_case_id(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get("/api/cases/..%2Fevil/physics")
    assert resp.status_code in (400, 404)


def test_get_physics_only_one_dict_present(monkeypatch, tmp_path):
    """Reads each dict independently; one missing should not 500."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    case_dir = _stage(imported, case_id, with_dicts=False)
    (case_dir / "constant" / "physicalProperties").write_text(
        _PHYS_TEXT, encoding="utf-8"
    )
    # momentumTransport intentionally absent
    resp = _client().get(f"/api/cases/{case_id}/physics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["material_dict_text"] == _PHYS_TEXT
    assert body["regime_dict_text"] is None
