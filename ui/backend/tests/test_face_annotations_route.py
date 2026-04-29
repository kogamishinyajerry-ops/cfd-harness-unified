"""Tests for the GET/PUT /api/cases/{case_id}/face-annotations route.

DEC-V61-098 spec_v2 §A4. The route is the persistence channel for
the M-AI-COPILOT collab dialog.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _isolated_imported(monkeypatch, tmp_path: Path) -> Path:
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_annotations.IMPORTED_DIR", target
    )
    return target


def _stage_imported_case(imported_dir: Path, case_id: str) -> Path:
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    return case_dir


def _new_client() -> TestClient:
    from ui.backend.main import app

    return TestClient(app)


def _safe_case_id() -> str:
    return f"imported_2026-04-29T00-00-00Z_{secrets.token_hex(4)}"


# ────────── GET happy paths ──────────


def test_get_returns_empty_doc_when_file_missing(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.get(f"/api/cases/{case_id}/face-annotations")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == case_id
    assert body["revision"] == 0
    assert body["faces"] == []


def test_get_returns_404_for_missing_case(monkeypatch, tmp_path):
    _isolated_imported(monkeypatch, tmp_path)
    client = _new_client()
    r = client.get("/api/cases/imported_2026-04-29T00-00-00Z_zzzz/face-annotations")
    assert r.status_code == 404
    assert r.json()["detail"]["failing_check"] == "case_not_found"


def test_get_rejects_unsafe_case_id(monkeypatch, tmp_path):
    _isolated_imported(monkeypatch, tmp_path)
    client = _new_client()
    # Path-traversal attempt; is_safe_case_id should reject.
    r = client.get("/api/cases/..%2Ftraversal/face-annotations")
    assert r.status_code in {400, 404, 422}  # FastAPI may 422 on URL decoding


# ────────── PUT happy paths ──────────


def test_put_creates_first_revision(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {
                    "face_id": "fid_abcd1234efgh5678",
                    "name": "lid",
                    "patch_type": "wall",
                    "confidence": "user_authoritative",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["revision"] == 1
    assert len(body["faces"]) == 1
    assert body["faces"][0]["name"] == "lid"
    assert body["faces"][0]["annotated_by"] == "human"


def test_put_round_trip_through_get(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{"face_id": "fid_aaaa1111bbbb2222", "name": "inlet"}],
        },
    )
    r = client.get(f"/api/cases/{case_id}/face-annotations")
    assert r.status_code == 200
    body = r.json()
    assert body["revision"] == 1
    assert body["faces"][0]["face_id"] == "fid_aaaa1111bbbb2222"
    assert body["faces"][0]["name"] == "inlet"


# ────────── PUT concurrency ──────────


def test_put_revision_conflict_returns_409(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    # First PUT lands as revision 1.
    client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{"face_id": "fid_a"*4, "name": "x"}],
        },
    )
    # Second PUT with stale if_match_revision=0 → 409.
    r = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{"face_id": "fid_b"*4, "name": "y"}],
        },
    )
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["failing_check"] == "revision_conflict"
    assert body["detail"]["attempted_revision"] == 0
    assert body["detail"]["current_revision"] == 1


# ────────── Sticky invariant ──────────


def test_put_sticky_user_authoritative_against_ai(monkeypatch, tmp_path):
    """AI write of a user_authoritative face is silently dropped at
    the route level (mirrors merge_face).
    """
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    # Human declares face as user_authoritative.
    client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {
                    "face_id": "fid_user1234abcdefab",
                    "name": "inlet",
                    "confidence": "user_authoritative",
                }
            ],
        },
    )
    # AI tries to overwrite the same face_id.
    r = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 1,
            "annotated_by": "ai:rule-based",
            "faces": [
                {
                    "face_id": "fid_user1234abcdefab",
                    "name": "wall",
                    "confidence": "ai_confident",
                }
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    # Sticky: the face should still say "inlet" / human.
    f = body["faces"][0]
    assert f["name"] == "inlet"
    assert f["confidence"] == "user_authoritative"
    assert f["annotated_by"] == "human"


# ────────── Validation ──────────


def test_put_rejects_negative_revision(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": -1,
            "annotated_by": "human",
            "faces": [],
        },
    )
    assert r.status_code == 422  # Pydantic ge=0 violation


def test_put_rejects_short_face_id(monkeypatch, tmp_path):
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [{"face_id": "x"}],  # min_length=4
        },
    )
    assert r.status_code == 422


def test_put_404_for_missing_case(monkeypatch, tmp_path):
    _isolated_imported(monkeypatch, tmp_path)
    client = _new_client()
    r = client.put(
        "/api/cases/imported_2026-04-29T00-00-00Z_nope/face-annotations",
        json={"if_match_revision": 0, "annotated_by": "human", "faces": []},
    )
    assert r.status_code == 404
