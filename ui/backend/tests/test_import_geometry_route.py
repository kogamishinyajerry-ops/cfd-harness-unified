"""Tests for ``POST /api/import/stl`` (M5.0 routine route)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.routes import import_geometry as import_route
from ui.backend.services import case_drafts
from ui.backend.services.case_scaffold import template_clone
from ui.backend.tests.conftest import (
    box_stl,
    farfield_6_plate_stl,
    multi_solid_ascii_stl,
    open_box_stl,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_drafts(tmp_path: Path, monkeypatch):
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", drafts)
    return drafts, imported


def test_happy_path_returns_case_id_and_edit_url():
    resp = client.post(
        "/api/import/stl",
        files={"file": ("cube.stl", box_stl(), "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["case_id"].startswith("imported_")
    assert body["edit_url"] == f"/workbench/case/{body['case_id']}/edit"
    report = body["ingest_report"]
    assert report["is_watertight"] is True
    assert report["face_count"] == 12
    assert report["errors"] == []
    # all_default_faces is a warning, not an error → request still succeeds.
    assert report["all_default_faces"] is True


def test_non_watertight_returns_400_with_watertight_failing_check():
    resp = client.post(
        "/api/import/stl",
        files={"file": ("open_box.stl", open_box_stl(), "application/octet-stream")},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    detail = body["detail"]
    assert detail["failing_check"] == "watertight"
    assert "watertight" in detail["reason"].lower()
    # Ingest report attached so UI can still render the diagnostic card.
    assert detail["ingest_report"]["is_watertight"] is False


def test_garbage_bytes_returns_400_with_stl_parse_failing_check():
    resp = client.post(
        "/api/import/stl",
        files={"file": ("garbage.stl", b"absolutely not an STL", "application/octet-stream")},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "stl_parse"


@pytest.mark.parametrize("fixture_name", ["ldc_box.stl", "cylinder.stl", "naca0012.stl"])
def test_bundled_fixtures_roundtrip(fixture_name: str):
    """Each fixture in examples/imports/ must upload cleanly + scaffold."""
    from ui.backend.services.validation_report import REPO_ROOT

    fixture_path = REPO_ROOT / "examples" / "imports" / fixture_name
    assert fixture_path.exists(), f"fixture missing: {fixture_path}"

    resp = client.post(
        "/api/import/stl",
        files={"file": (fixture_name, fixture_path.read_bytes(), "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ingest_report"]["is_watertight"] is True
    assert body["ingest_report"]["unit_guess"] == "m"
    assert body["edit_url"].startswith("/workbench/case/")


def test_f_new_26_6_plate_returns_400_with_body_overlap_failing_check():
    """F-NEW-26 systematic CAD bug: 6 thick farfield plates whose AABBs
    overlap at 12 cube edges. Session 11 added the import-time defensive
    layer; session 13 verifies it surfaces through the route as a
    structured 4xx with a cross-repo ticket reference.

    Pre-session-13 gap: the route called ``run_health_checks`` without
    ``body_aabbs``, so the defensive layer was dead code at the HTTP
    layer (only the :func:`ingest_stl` wrapper fired it). This test
    pins the wiring.
    """
    resp = client.post(
        "/api/import/stl",
        files={"file": ("6_plate_farfield.stl", farfield_6_plate_stl(), "application/octet-stream")},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "body_overlap", detail
    reason = detail["reason"]
    assert "edge AABB" in reason, reason
    assert "F-NEW-26" in reason, reason
    assert "2026-05-12_case_003_build_cad_farfield_overlap.md" in reason, reason
    # Ingest report attached so UI can render the per-body AABB diagnostic.
    assert detail["ingest_report"]["is_watertight"] is True
    assert detail["ingest_report"]["solid_count"] == 6


def test_disjoint_multi_solid_returns_200_no_overlap_diagnostic():
    """Two named solids with non-intersecting AABBs must NOT fire the
    F-NEW-26 defensive layer. Pins that the wiring doesn't misfire on
    clean multi-body STLs (regression guard for false positives)."""
    resp = client.post(
        "/api/import/stl",
        files={"file": ("two_bodies.stl", multi_solid_ascii_stl("body_a", "body_b"), "application/octet-stream")},
    )
    assert resp.status_code == 200, resp.text
    report = resp.json()["ingest_report"]
    assert report["errors"] == []
    overlap_msgs = [
        m for m in report["warnings"] + report["errors"]
        if "AABB" in m or "F-NEW-26" in m
    ]
    assert overlap_msgs == [], f"unexpected overlap diagnostic on disjoint bodies: {overlap_msgs}"


def test_oversize_upload_returns_413(monkeypatch):
    """Force the limit to a tiny value and overshoot it deterministically."""
    monkeypatch.setattr(import_route, "MAX_STL_BYTES", 1024)  # 1 KB cap
    big_blob = b"\x00" * 4096  # 4 KB, content shape irrelevant
    resp = client.post(
        "/api/import/stl",
        files={"file": ("huge.stl", big_blob, "application/octet-stream")},
    )
    assert resp.status_code == 413, resp.text
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "size_limit"
