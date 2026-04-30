"""DEC-V61-102 Phase 1.2 · case_dicts route GET/POST tests."""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.services.case_manifest import (
    mark_ai_authored,
    read_case_manifest,
    write_case_manifest,
)
from ui.backend.services.case_manifest.schema import CaseManifest
from ui.backend.services.case_scaffold import IMPORTED_DIR


_VALID_CONTROLDICT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}
application     icoFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2;
deltaT          0.005;
"""


def _isolate(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_dicts.IMPORTED_DIR", target
    )
    return target


def _stage(imported_dir: Path, case_id: str, controldict: str | None = None) -> Path:
    case_dir = imported_dir / case_id
    (case_dir / "system").mkdir(parents=True)
    if controldict is not None:
        (case_dir / "system" / "controlDict").write_text(controldict, encoding="utf-8")
    # Minimal v2 manifest so override marking can read/write it.
    write_case_manifest(case_dir, CaseManifest(case_id=case_id))
    return case_dir


def _client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-04-30T00-00-00Z_{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# GET happy path
# ---------------------------------------------------------------------------


def test_get_returns_content_and_etag_for_existing_dict(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)
    # Mark it AI-authored so the GET response source field is populated.
    mark_ai_authored(
        imported / case_id,
        relative_paths=["system/controlDict"],
        action="setup_ldc_bc",
    )

    resp = _client().get(f"/api/cases/{case_id}/dicts/system/controlDict")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["path"] == "system/controlDict"
    assert "icoFoam" in body["content"]
    assert body["source"] == "ai"
    assert len(body["etag"]) == 16


def test_get_disallowed_path_404(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    # 0/U is intentionally not in the allowlist.
    resp = _client().get(f"/api/cases/{case_id}/dicts/0/U")
    assert resp.status_code == 404
    assert resp.json()["detail"]["failing_check"] == "path_not_allowed"


def test_get_missing_file_returns_404_with_hint(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    # Stage WITHOUT writing controlDict.
    _stage(imported, case_id, controldict=None)

    resp = _client().get(f"/api/cases/{case_id}/dicts/system/controlDict")
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "dict_file_missing"
    assert "AI" in detail["hint"]


def test_get_unknown_case_404(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().get("/api/cases/imported_does_not_exist_xxxx/dicts/system/controlDict")
    assert resp.status_code == 404


def test_get_bad_case_id_400(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    # Bad shape — case_id without imported_ prefix gets rejected by safety check.
    resp = _client().get("/api/cases/..%2Fevil/dicts/system/controlDict")
    assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# POST happy path + override marking
# ---------------------------------------------------------------------------


def test_post_writes_content_and_marks_user_override(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)
    mark_ai_authored(
        imported / case_id,
        relative_paths=["system/controlDict"],
        action="setup_ldc_bc",
    )

    new_content = _VALID_CONTROLDICT.replace("endTime         2;", "endTime         10;")
    resp = _client().post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": new_content},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "user"
    assert len(body["new_etag"]) == 16

    # File on disk reflects new content.
    on_disk = (imported / case_id / "system" / "controlDict").read_text()
    assert "endTime         10;" in on_disk

    # Manifest reflects user override.
    manifest = read_case_manifest(imported / case_id)
    entry = manifest.overrides.raw_dict_files["system/controlDict"]
    assert entry.source == "user"
    assert entry.etag == body["new_etag"]
    # History captured the edit.
    actions = [h.action for h in manifest.history]
    assert "edit_dict" in actions


def test_post_etag_mismatch_returns_409(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)

    resp = _client().post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": _VALID_CONTROLDICT, "expected_etag": "0000000000000000"},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "etag_mismatch"
    assert detail["expected_etag"] == "0000000000000000"
    assert "current_etag" in detail


def test_post_validation_error_blocks_save(monkeypatch, tmp_path):
    """controlDict missing FoamFile header AND missing application line
    triggers two error issues — without ?force=1 the route blocks."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)

    bad_content = "this is not a valid foam dict\n"
    resp = _client().post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": bad_content},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "validation_failed"
    msgs = [i["message"] for i in detail["issues"]]
    assert any("FoamFile" in m for m in msgs)
    assert any("application" in m for m in msgs)


def test_post_force_bypasses_validation(monkeypatch, tmp_path):
    """?force=1 lets the engineer save even invalid content (the
    'I know what I'm doing' path)."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)

    bad_content = "totally nonstandard content\n"
    resp = _client().post(
        f"/api/cases/{case_id}/dicts/system/controlDict?force=1",
        json={"content": bad_content},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "user"
    # Warnings list still surfaces the would-have-blocked issues.
    assert len(body["warnings"]) > 0


def test_post_disallowed_path_404(monkeypatch, tmp_path):
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id)

    resp = _client().post(
        f"/api/cases/{case_id}/dicts/0/U",
        json={"content": "x"},
    )
    assert resp.status_code == 404


def test_post_unknown_case_404(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    resp = _client().post(
        "/api/cases/imported_does_not_exist_xxxx/dicts/system/controlDict",
        json={"content": _VALID_CONTROLDICT},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Round-trip: GET → POST → GET
# ---------------------------------------------------------------------------


def test_e2e_get_edit_post_get_round_trip(monkeypatch, tmp_path):
    """Full round-trip: AI-authored file → engineer GETs it → edits →
    POSTs with the etag → re-GETs → sees the new content + source=user."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)
    mark_ai_authored(
        imported / case_id,
        relative_paths=["system/controlDict"],
        action="setup_ldc_bc",
    )
    client = _client()

    # 1. GET — capture etag.
    resp1 = client.get(f"/api/cases/{case_id}/dicts/system/controlDict")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["source"] == "ai"
    etag1 = body1["etag"]

    # 2. POST with the etag.
    new_content = body1["content"].replace("deltaT          0.005;", "deltaT          0.001;")
    resp2 = client.post(
        f"/api/cases/{case_id}/dicts/system/controlDict",
        json={"content": new_content, "expected_etag": etag1},
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["source"] == "user"
    etag2 = body2["new_etag"]
    assert etag2 != etag1

    # 3. GET again — see updated content + source=user.
    resp3 = client.get(f"/api/cases/{case_id}/dicts/system/controlDict")
    assert resp3.status_code == 200
    body3 = resp3.json()
    assert "deltaT          0.001;" in body3["content"]
    assert body3["source"] == "user"
    assert body3["etag"] == etag2
    assert body3["edited_at"] is not None


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


def test_list_returns_all_allowlisted_paths_with_state(monkeypatch, tmp_path):
    """The list endpoint enumerates every allowlisted path with
    existence + source state. Paths that don't have files yet show
    exists=False. Paths that have user overrides show source=user."""
    imported = _isolate(monkeypatch, tmp_path)
    case_id = _safe_id()
    _stage(imported, case_id, controldict=_VALID_CONTROLDICT)
    mark_ai_authored(
        imported / case_id,
        relative_paths=["system/controlDict"],
        action="setup_ldc_bc",
    )

    resp = _client().get(f"/api/cases/{case_id}/dicts")
    assert resp.status_code == 200
    entries = resp.json()
    by_path = {e["path"]: e for e in entries}

    # controlDict exists + ai-authored
    assert by_path["system/controlDict"]["exists"] is True
    assert by_path["system/controlDict"]["source"] == "ai"
    # fvSchemes not staged → doesn't exist yet
    assert by_path["system/fvSchemes"]["exists"] is False
    assert by_path["system/fvSchemes"]["source"] == "ai"
    # 0/U etc. are NOT in the response (allowlist boundary)
    assert "0/U" not in by_path
