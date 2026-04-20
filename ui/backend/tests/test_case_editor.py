"""Tests for Phase 1 Case Editor routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services import case_drafts

client = TestClient(app)

CASE = "differential_heated_cavity"


@pytest.fixture(autouse=True)
def _isolated_drafts_dir(tmp_path: Path, monkeypatch):
    """Redirect drafts dir to a temp path so tests don't write into the repo."""
    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", tmp_path / "user_drafts")
    yield


def test_get_yaml_returns_whitelist_source():
    resp = client.get(f"/api/cases/{CASE}/yaml")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["case_id"] == CASE
    assert body["origin"] == "whitelist"
    assert body["draft_path"] is None
    # The emitted YAML should contain the case id.
    assert f"id: {CASE}" in body["yaml_text"] or CASE in body["yaml_text"]


def test_put_yaml_saves_draft_and_roundtrips():
    # Seed with current source, append a harmless comment, save.
    original = client.get(f"/api/cases/{CASE}/yaml").json()["yaml_text"]
    edited = original + "\n# editor touched by test\n"
    put = client.put(
        f"/api/cases/{CASE}/yaml",
        json={
            "case_id": CASE,
            "yaml_text": edited,
            "origin": "draft",
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["saved"] is True
    assert body["lint"]["ok"] is True
    assert body["draft_path"] is not None

    # Now GET should return the draft.
    resp = client.get(f"/api/cases/{CASE}/yaml")
    assert resp.status_code == 200
    assert resp.json()["origin"] == "draft"
    assert "editor touched by test" in resp.json()["yaml_text"]


def test_put_yaml_rejects_unparseable():
    resp = client.put(
        f"/api/cases/{CASE}/yaml",
        json={"case_id": CASE, "yaml_text": ":::::::\n  bad:\n -", "origin": "draft"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["saved"] is False
    assert body["lint"]["ok"] is False
    assert len(body["lint"]["errors"]) >= 1


def test_lint_only_does_not_persist():
    resp = client.post(
        f"/api/cases/{CASE}/yaml/lint",
        json={"case_id": CASE, "yaml_text": "just: a_value\n", "origin": "draft"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    # Missing recommended fields → warnings present
    assert any("id" in w for w in body["warnings"])


def test_delete_yaml_reverts_to_whitelist():
    # Seed a draft first.
    original = client.get(f"/api/cases/{CASE}/yaml").json()["yaml_text"]
    client.put(
        f"/api/cases/{CASE}/yaml",
        json={"case_id": CASE, "yaml_text": original + "\n# transient\n", "origin": "draft"},
    )
    assert client.get(f"/api/cases/{CASE}/yaml").json()["origin"] == "draft"

    resp = client.delete(f"/api/cases/{CASE}/yaml")
    assert resp.status_code == 200
    assert resp.json()["origin"] == "whitelist"


def test_unknown_case_returns_404():
    resp = client.get("/api/cases/does_not_exist/yaml")
    assert resp.status_code == 404
