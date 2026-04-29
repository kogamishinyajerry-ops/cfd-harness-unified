"""Tests for the M-AI-COPILOT envelope mode on POST /api/import/{id}/setup-bc.

DEC-V61-098 spec_v2 §B.4: existing route preserved for backward-compat
(envelope=0); new ``?envelope=1`` opts into ``AIActionEnvelope``.

These tests exercise the route layer + envelope short-circuit paths
(``force_uncertain``, ``force_blocked``) which dogfood the dialog flow
without requiring a real polyMesh. The legacy envelope=0 happy path
requires a full LDC mesh fixture and is covered by the existing
``setup_ldc_bc`` unit tests in `case_solve` (not duplicated here).
"""
from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ui.backend.services.case_scaffold import IMPORTED_DIR


# ────────── helpers ──────────


def _isolated_imported(monkeypatch, tmp_path: Path) -> Path:
    """Repoint IMPORTED_DIR at a tmp dir so tests don't pollute the
    real user_drafts/imported tree.
    """
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_solve.IMPORTED_DIR", target
    )
    return target


def _stage_imported_case(imported_dir: Path, case_id: str) -> Path:
    """Create a minimal imported case dir. Just enough for
    ``_resolve_case_dir`` to find it; force_blocked short-circuits
    before any mesh parsing so polyMesh isn't needed.
    """
    case_dir = imported_dir / case_id
    case_dir.mkdir()
    return case_dir


def _new_client() -> TestClient:
    """Construct a fresh TestClient on the FastAPI app. Each test
    builds its own to avoid shared state between tests.
    """
    from ui.backend.main import app

    return TestClient(app)


def _safe_case_id() -> str:
    return f"imported_2026-04-29T00-00-00Z_{secrets.token_hex(4)}"


# ────────── envelope=0 (legacy) backward-compat ──────────


def test_legacy_envelope_zero_route_unmodified_for_invalid_case(
    monkeypatch, tmp_path
):
    """envelope=0 default branch must not invoke the new
    ai_actions code path. Verified by 404 on a non-existent case
    (the legacy contract).
    """
    _isolated_imported(monkeypatch, tmp_path)
    client = _new_client()

    r = client.post("/api/import/imported_2026-04-29T00-00-00Z_nope/setup-bc")
    assert r.status_code == 404
    assert r.json()["detail"]["failing_check"] == "case_not_found"


# ────────── envelope=1 + force_blocked (dogfood path) ──────────


def test_envelope_force_blocked_returns_blocked_envelope(
    monkeypatch, tmp_path
):
    """Per spec_v2 §D Tier-A demo: force_blocked=1 short-circuits
    BEFORE setup_ldc_bc runs, so the dialog flow can be dogfooded
    on the LDC fixture without the AI actually being uncertain.
    """
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1, "force_blocked": 1},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["confidence"] == "blocked"
    assert len(payload["unresolved_questions"]) == 1
    q = payload["unresolved_questions"][0]
    assert q["kind"] == "face_label"
    assert q["needs_face_selection"] is True
    # Revisions: file does not exist yet, both should be 0.
    assert payload["annotations_revision_consumed"] == 0
    assert payload["annotations_revision_after"] == 0


def test_envelope_force_blocked_does_not_call_setup_ldc_bc(
    monkeypatch, tmp_path
):
    """Critical contract: force_blocked is the dogfood path that does
    NOT actually set up BCs. The case dir has no polyMesh (mesh hasn't
    run); the legacy path would 409 on it. force_blocked must succeed
    anyway because it short-circuits before mesh parsing.
    """
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)  # NO polyMesh
    client = _new_client()

    # Without force_blocked, the legacy path would fail (no polyMesh).
    # With force_blocked, the route returns 200 + blocked envelope.
    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1, "force_blocked": 1},
    )
    assert r.status_code == 200
    assert r.json()["confidence"] == "blocked"


# ────────── envelope=1 + force_uncertain (still calls setup_ldc_bc) ──────────


def test_envelope_force_uncertain_propagates_setup_failure(
    monkeypatch, tmp_path
):
    """force_uncertain DOES still run setup_ldc_bc (so the engineer
    sees real BC numbers in the summary, just with one mock question
    appended). If setup_ldc_bc fails, the route surfaces the failure
    via AIActionError → HTTPException, NOT via a degenerate envelope.
    """
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)  # NO polyMesh → setup will fail
    client = _new_client()

    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1, "force_uncertain": 1},
    )
    # setup_ldc_bc raises BCSetupError → AIActionError →
    # _setup_bc_failure_to_http → 409 (mesh_missing) or 500 (write_failed).
    assert r.status_code in {409, 500}
    body = r.json()
    assert "failing_check" in body["detail"]


# ────────── envelope=1 + invalid query param combos ──────────


def test_envelope_query_param_validation(monkeypatch, tmp_path):
    """Pydantic Query params reject out-of-range values cleanly."""
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    # envelope=2 violates Query(le=1).
    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 2},
    )
    assert r.status_code == 422


def test_envelope_force_blocked_wins_when_both_force_flags_set(
    monkeypatch, tmp_path
):
    """spec_v2 §A3: 'mutually exclusive ... if both, force_blocked
    wins'. force_blocked short-circuits → blocked envelope.
    """
    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    _stage_imported_case(imported, case_id)
    client = _new_client()

    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1, "force_uncertain": 1, "force_blocked": 1},
    )
    assert r.status_code == 200
    assert r.json()["confidence"] == "blocked"


# ────────── envelope=1 reads pre-existing annotations ──────────


def test_envelope_reads_existing_annotations_revision(
    monkeypatch, tmp_path
):
    """When face_annotations.yaml already exists at revision N, the
    envelope reports revision_consumed=N (not 0) — proving the
    AI action read the file before deciding.
    """
    from ui.backend.services.case_annotations import (
        empty_annotations,
        save_annotations,
    )

    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    # Materialize annotations at revision 1.
    save_annotations(case_dir, empty_annotations(case_id), if_match_revision=0)
    # Materialize again to revision 2.
    save_annotations(case_dir, empty_annotations(case_id), if_match_revision=1)

    client = _new_client()
    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1, "force_blocked": 1},
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["annotations_revision_consumed"] == 2
    assert payload["annotations_revision_after"] == 2  # blocked → no write
