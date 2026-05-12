"""DEC-V61-149 (N4.4) · raw-dict escape hatch contract verification.

N4.4 ships ZERO new backend code — the existing case_dicts route
already implements every clause of the charter §sub-DEC table N4.4
contract:

  * "per-dict copy-to-clipboard"   → frontend RawDictEditor uses the
                                     existing GET response's `content`
                                     field; copy-to-clipboard is a
                                     pure-frontend UX concern.
  * "read-back from disk"          → existing GET /api/cases/{id}/
                                     dicts/{path} returns the on-disk
                                     content with a fresh etag.
  * "engineer can edit in their    → roundtrip is GET → external edit
     editor and re-import"            → POST with `expected_etag` from
                                       the original GET. 409 on
                                       intervening overwrite.

This test module documents that contract by exercising each clause
end-to-end against the existing route surface. If a future change
breaks one of these behaviors, this file fails — providing a stable
N4.4 contract guard.

The sub-DEC itself records the design decision (use existing
machinery vs add a new endpoint surface). See
`.planning/decisions/2026-05-07_v61_149_n4_4_escape_hatch.md`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """TestClient with case_dicts IMPORTED_DIR redirected to tmp_path."""
    monkeypatch.setattr(
        "ui.backend.routes.case_dicts.IMPORTED_DIR", tmp_path
    )
    from ui.backend.main import app

    return TestClient(app)


def _scaffold_case_with_dict(
    tmp_path: Path,
    case_id: str,
    rel_path: str,
    content: str,
) -> Path:
    """Create a case directory with a single dict file populated."""
    case_dir = tmp_path / case_id
    (case_dir / Path(rel_path).parent).mkdir(parents=True, exist_ok=True)
    (case_dir / rel_path).write_text(content)
    return case_dir


# ────────── N4.4 contract clause 1: read-back from disk ──────────


def test_n4_4_read_back_returns_disk_content_and_fresh_etag(client, tmp_path):
    case_id = "imported_n4_4_read"
    contents = (
        "FoamFile { version 2.0; format ascii; class dictionary; "
        'location "constant"; object physicalProperties; }\n'
        "transportModel  Newtonian;\n"
        "nu              [0 2 -1 0 0 0 0] 1.5e-5;\n"
    )
    _scaffold_case_with_dict(
        tmp_path, case_id, "constant/physicalProperties", contents
    )
    response = client.get(
        f"/api/cases/{case_id}/dicts/constant/physicalProperties"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["path"] == "constant/physicalProperties"
    assert "Newtonian" in body["content"]
    assert "nu" in body["content"]
    assert body["etag"], "etag must be non-empty for race protection"


# ────────── N4.4 contract clause 2: SHA-aware race protection ──────────


def test_n4_4_post_with_stale_etag_returns_409(client, tmp_path):
    """Engineer GETs a dict, edits externally, in the meantime someone
    else (AI dispatch path or concurrent engineer) writes a new
    version. The engineer's POST with the stale etag must NOT
    silently overwrite — must surface 409 so they can re-fetch."""
    case_id = "imported_n4_4_race"
    case_dir = _scaffold_case_with_dict(
        tmp_path, case_id, "constant/physicalProperties",
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\nnu [0 2 -1 0 0 0 0] 1e-5;\n',
    )
    # Engineer GETs current content + etag.
    get_response = client.get(
        f"/api/cases/{case_id}/dicts/constant/physicalProperties"
    )
    stale_etag = get_response.json()["etag"]

    # Concurrent overwrite happens on disk (simulating another writer).
    (case_dir / "constant" / "physicalProperties").write_text(
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\nnu [0 2 -1 0 0 0 0] 2e-5;\n'
    )

    # Engineer POSTs with the now-stale etag.
    post_response = client.post(
        f"/api/cases/{case_id}/dicts/constant/physicalProperties",
        json={
            "content": (
                'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\nnu [0 2 -1 0 0 0 0] 3e-5;\n'
            ),
            "expected_etag": stale_etag,
        },
    )
    assert post_response.status_code == 409
    detail = post_response.json()["detail"]
    assert "failing_check" in detail


def test_n4_4_post_with_fresh_etag_succeeds(client, tmp_path):
    """Happy path: engineer GETs, edits, immediately POSTs with the
    fresh etag — write succeeds."""
    case_id = "imported_n4_4_ok"
    _scaffold_case_with_dict(
        tmp_path, case_id, "constant/physicalProperties",
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\nnu [0 2 -1 0 0 0 0] 1e-5;\n',
    )
    get_response = client.get(
        f"/api/cases/{case_id}/dicts/constant/physicalProperties"
    )
    fresh_etag = get_response.json()["etag"]

    new_content = (
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\nnu [0 2 -1 0 0 0 0] 5e-6;\n'
    )
    post_response = client.post(
        f"/api/cases/{case_id}/dicts/constant/physicalProperties",
        json={"content": new_content, "expected_etag": fresh_etag},
    )
    assert post_response.status_code == 200, post_response.text
    body = post_response.json()
    assert body["new_etag"] != fresh_etag, (
        "new_etag must advance after successful write so subsequent "
        "POSTs use the latest"
    )


# ────────── N4.4 contract clause 3: list endpoint surfaces every editable path ──────────


def test_n4_4_list_endpoint_includes_every_allowlisted_path(client, tmp_path):
    """The unified Step 3 Physics setup workbench (future panel)
    needs to render every editable dict in one place. The list
    endpoint must return EVERY allowlisted path — even when the file
    doesn't exist on disk yet (with `exists=False`)."""
    case_id = "imported_n4_4_list"
    case_dir = tmp_path / case_id
    case_dir.mkdir()
    response = client.get(f"/api/cases/{case_id}/dicts")
    assert response.status_code == 200, response.text
    paths = {entry["path"] for entry in response.json()}
    from ui.backend.services.case_dicts.allowlist import (
        ALLOWED_RAW_DICT_PATHS,
    )
    assert paths == set(ALLOWED_RAW_DICT_PATHS), (
        "list endpoint must surface every allowlisted path so the UI "
        "panel can render the full set of editable dicts"
    )


def test_n4_4_list_endpoint_marks_existing_vs_missing(client, tmp_path):
    case_id = "imported_n4_4_existence"
    case_dir = _scaffold_case_with_dict(
        tmp_path, case_id, "constant/physicalProperties",
        'FoamFile { version 2.0; format ascii; class dictionary; location "constant"; object physicalProperties; }\ntransportModel  Newtonian;\n',
    )
    response = client.get(f"/api/cases/{case_id}/dicts")
    body = response.json()
    by_path = {entry["path"]: entry for entry in body}
    assert by_path["constant/physicalProperties"]["exists"] is True
    assert by_path["constant/physicalProperties"]["etag"] is not None
    # A path that wasn't scaffolded must be flagged exists=False with
    # null etag — UI renders as "(empty)" placeholder.
    missing = by_path["system/controlDict"]
    assert missing["exists"] is False
    assert missing["etag"] is None


# ────────── N4.4 V132 surface invariant ──────────


def test_n4_4_existing_post_route_is_v132_registered():
    """The raw-dict POST route is the legacy V132 mutator. Confirm
    it's still registered after N4.4 changes — no accidental removal."""
    from ui.backend.services.ai_actions.mutating_routes import MUTATING_ROUTES

    assert ("POST", "/api/cases/{case_id}/dicts/{rest}") in MUTATING_ROUTES
