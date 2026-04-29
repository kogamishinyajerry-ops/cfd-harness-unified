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

    Two route modules import IMPORTED_DIR at module load: case_solve
    (for setup-bc) and case_annotations (for face-annotations PUT/GET).
    Both must be patched to keep the full E2E loop self-contained.
    """
    target = tmp_path / "imported"
    target.mkdir()
    monkeypatch.setattr(
        "ui.backend.services.case_scaffold.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_solve.IMPORTED_DIR", target
    )
    monkeypatch.setattr(
        "ui.backend.routes.case_annotations.IMPORTED_DIR", target
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


# ────────── envelope=1 full-loop HTTP E2E (RETRO-V61-053 mandate) ──────────
#
# RETRO-V61-053 addendum (2026-04-24) introduced the
# `executable_smoke_test` flag: a category of post-R3 defects that
# Codex static review structurally cannot catch — they only surface
# when the handshake between classifier, action wrapper, and HTTP
# route is exercised through the actual API. Wrapper-level full-loop
# coverage already exists in test_ai_classifier.test_full_loop_*; this
# closes the route-layer gap.


def test_envelope_full_loop_uncertain_pin_lid_then_confident_via_http(
    monkeypatch, tmp_path
):
    """E2E: POST setup-bc → uncertain · PUT face-annotations · POST
    setup-bc → confident · BC dicts on disk.

    Exercises the contract Codex M9 Step 2 R2 closed (classifier-
    executor parity via _top_plane_face_ids) over the actual HTTP
    surface, so a route-layer breakage between the FastAPI body
    schema, _resolve_case_dir, and ai_actions wrapper would be
    caught here even when wrapper-level tests stay green.
    """
    # Inline cube fixture (mirrors test_ai_classifier._stage_full_cube).
    # We don't import from a sibling test module — that's brittle and
    # makes pytest collection order matter.
    points_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class vectorField;\n    location \"constant/polyMesh\";\n"
        "    object points;\n}\n\n8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 1)\n(1 0 1)\n(1 1 1)\n(0 1 1)\n)\n"
    )
    faces_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class faceList;\n    location \"constant/polyMesh\";\n"
        "    object faces;\n}\n\n6\n(\n"
        "4(0 1 2 3)\n4(4 5 6 7)\n4(0 1 5 4)\n"
        "4(2 3 7 6)\n4(1 2 6 5)\n4(0 3 7 4)\n)\n"
    )
    boundary_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class polyBoundaryMesh;\n"
        "    location \"constant/polyMesh\";\n    object boundary;\n}\n\n"
        "1\n(\n    walls\n    {\n        type wall;\n"
        "        nFaces 6;\n        startFace 0;\n    }\n)\n"
    )
    owner_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class labelList;\n    location \"constant/polyMesh\";\n"
        "    object owner;\n}\n\n6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )

    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points_cube, encoding="utf-8")
    (polymesh / "faces").write_text(faces_cube, encoding="utf-8")
    (polymesh / "boundary").write_text(boundary_cube, encoding="utf-8")
    (polymesh / "owner").write_text(owner_cube, encoding="utf-8")

    client = _new_client()

    # Step 1: first envelope call returns uncertain · lid_orientation.
    r1 = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},  # NOTE: no force flags — exercises the real classifier
    )
    assert r1.status_code == 200, r1.text
    env1 = r1.json()
    assert env1["confidence"] == "uncertain", env1
    assert any(
        q["id"] == "lid_orientation" for q in env1["unresolved_questions"]
    )
    assert env1["annotations_revision_consumed"] == 0
    assert not (case_dir / "0").is_dir()  # executor did NOT run yet

    # Step 2: compute the actual top-plane face_id and PUT the lid pin.
    from ui.backend.services.case_annotations import face_id

    top_face_id = face_id(
        [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0)]
    )
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {
                    "face_id": top_face_id,
                    "name": "lid",
                    "confidence": "user_authoritative",
                }
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    put_payload = r_put.json()
    assert put_payload["revision"] == 1
    pinned = next(f for f in put_payload["faces"] if f["face_id"] == top_face_id)
    assert pinned["name"] == "lid"
    assert pinned["confidence"] == "user_authoritative"

    # Step 3: re-run envelope → classifier verifies pin geometrically →
    # confident · setup_ldc_bc runs → BC dicts on disk.
    r2 = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},
    )
    assert r2.status_code == 200, r2.text
    env2 = r2.json()
    assert env2["confidence"] == "confident", env2
    assert env2["unresolved_questions"] == []
    assert env2["annotations_revision_consumed"] == 1
    assert (case_dir / "0").is_dir()
    assert (case_dir / "system").is_dir()
    assert (case_dir / "constant").is_dir()


def test_envelope_full_loop_lid_pin_off_top_plane_stays_uncertain(
    monkeypatch, tmp_path
):
    """E2E negative path: pinning a non-top face with name='lid' must
    NOT silently flip the classifier to confident — that would let
    setup_ldc_bc override the engineer's intent. Codex M9 Step 2 R2
    HIGH finding.
    """
    points_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class vectorField;\n    location \"constant/polyMesh\";\n"
        "    object points;\n}\n\n8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 1)\n(1 0 1)\n(1 1 1)\n(0 1 1)\n)\n"
    )
    faces_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class faceList;\n    location \"constant/polyMesh\";\n"
        "    object faces;\n}\n\n6\n(\n"
        "4(0 1 2 3)\n4(4 5 6 7)\n4(0 1 5 4)\n"
        "4(2 3 7 6)\n4(1 2 6 5)\n4(0 3 7 4)\n)\n"
    )
    boundary_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class polyBoundaryMesh;\n"
        "    location \"constant/polyMesh\";\n    object boundary;\n}\n\n"
        "1\n(\n    walls\n    {\n        type wall;\n"
        "        nFaces 6;\n        startFace 0;\n    }\n)\n"
    )
    owner_cube = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class labelList;\n    location \"constant/polyMesh\";\n"
        "    object owner;\n}\n\n6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )

    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points_cube, encoding="utf-8")
    (polymesh / "faces").write_text(faces_cube, encoding="utf-8")
    (polymesh / "boundary").write_text(boundary_cube, encoding="utf-8")
    (polymesh / "owner").write_text(owner_cube, encoding="utf-8")

    # Pin a SIDE face (z=0 plane) with name='lid' — wrong geometry.
    from ui.backend.services.case_annotations import face_id

    bottom_face_id = face_id(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    )
    client = _new_client()
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {
                    "face_id": bottom_face_id,
                    "name": "lid",
                    "confidence": "user_authoritative",
                }
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    put_payload = r_put.json()
    # Prove the bad pin was actually written (not silently no-op'd).
    # Without this, the test could pass on a stale/empty doc and the
    # uncertain assertion below would still hold for the wrong reason.
    assert put_payload["revision"] == 1
    assert any(
        f["face_id"] == bottom_face_id and f["name"] == "lid"
        for f in put_payload["faces"]
    )

    # Envelope MUST stay uncertain — classifier honors geometry.
    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},
    )
    assert r.status_code == 200, r.text
    env = r.json()
    assert env["confidence"] == "uncertain", env
    # Prove the classifier actually consumed the bad pin (revision=1)
    # before deciding to stay uncertain — closes the Codex E2E R1 LOW
    # gap where the test could pass on the wrong reason (no annotation
    # consumed at all).
    assert env["annotations_revision_consumed"] == 1
    # And critically: setup_ldc_bc did NOT run — no 0/ dir.
    assert not (case_dir / "0").is_dir()


# ────────── DEC-V61-101 channel executor E2E ──────────


def test_envelope_full_loop_channel_inlet_outlet_pin_then_confident_via_http(
    monkeypatch, tmp_path
):
    """DEC-V61-101: the channel-geometry analog of the LDC full-loop
    HTTP E2E.

    POST setup-bc → uncertain (inlet+outlet face_label questions) ·
    PUT face-annotations (both pins as user_authoritative) ·
    POST setup-bc → confident · channel BC dicts on disk · boundary
    patch split into inlet/outlet/walls.

    Defends the route layer against the same kind of post-R3 defect
    RETRO-V61-053 mandates an executable smoke test for, but on the
    new non-cube path that DEC-V61-101 introduces.
    """
    # 1×1×10 channel polyMesh fixture (mirrors test_ai_classifier
    # _POINTS_CHANNEL + _stage_full_channel).
    points = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class vectorField;\n    location \"constant/polyMesh\";\n"
        "    object points;\n}\n\n8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 10)\n(1 0 10)\n(1 1 10)\n(0 1 10)\n)\n"
    )
    faces = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class faceList;\n    location \"constant/polyMesh\";\n"
        "    object faces;\n}\n\n6\n(\n"
        "4(0 1 2 3)\n4(4 5 6 7)\n4(0 1 5 4)\n"
        "4(2 3 7 6)\n4(1 2 6 5)\n4(0 3 7 4)\n)\n"
    )
    boundary = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class polyBoundaryMesh;\n"
        "    location \"constant/polyMesh\";\n    object boundary;\n}\n\n"
        "1\n(\n    walls\n    {\n        type wall;\n"
        "        nFaces 6;\n        startFace 0;\n    }\n)\n"
    )
    owner = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class labelList;\n    location \"constant/polyMesh\";\n"
        "    object owner;\n}\n\n6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )

    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points, encoding="utf-8")
    (polymesh / "faces").write_text(faces, encoding="utf-8")
    (polymesh / "boundary").write_text(boundary, encoding="utf-8")
    (polymesh / "owner").write_text(owner, encoding="utf-8")

    client = _new_client()

    # Step 1: first envelope call returns uncertain · 2 face questions.
    r1 = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},
    )
    assert r1.status_code == 200, r1.text
    env1 = r1.json()
    assert env1["confidence"] == "uncertain", env1
    qids = {q["id"] for q in env1["unresolved_questions"]}
    assert "inlet_face" in qids
    assert "outlet_face" in qids
    assert not (case_dir / "0").is_dir()

    # Step 2: compute the inlet/outlet face_ids and PUT both pins.
    from ui.backend.services.case_annotations import face_id

    inlet_fid = face_id(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    )
    outlet_fid = face_id(
        [
            (0.0, 0.0, 10.0),
            (1.0, 0.0, 10.0),
            (1.0, 1.0, 10.0),
            (0.0, 1.0, 10.0),
        ]
    )
    r_put = client.put(
        f"/api/cases/{case_id}/face-annotations",
        json={
            "if_match_revision": 0,
            "annotated_by": "human",
            "faces": [
                {
                    "face_id": inlet_fid,
                    "name": "inlet_main",
                    "confidence": "user_authoritative",
                },
                {
                    "face_id": outlet_fid,
                    "name": "outlet_main",
                    "confidence": "user_authoritative",
                },
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    assert r_put.json()["revision"] == 1

    # Step 3: re-run envelope → classifier verifies pins → confident →
    # setup_channel_bc writes dicts + splits boundary into 3 patches.
    r2 = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},
    )
    assert r2.status_code == 200, r2.text
    env2 = r2.json()
    assert env2["confidence"] == "confident", env2
    assert env2["unresolved_questions"] == []
    assert env2["annotations_revision_consumed"] == 1
    assert "inlet=" in env2["summary"] and "outlet=" in env2["summary"]
    # Executor wrote the channel dict tree (NOT the LDC tree — no
    # `lid` patch).
    assert (case_dir / "0" / "U").is_file()
    assert (case_dir / "0" / "p").is_file()
    assert (case_dir / "system" / "controlDict").is_file()
    bnd_text = (case_dir / "constant" / "polyMesh" / "boundary").read_text()
    assert "inlet" in bnd_text
    assert "outlet" in bnd_text
    assert "walls" in bnd_text
    assert "lid" not in bnd_text  # not the LDC executor


def test_envelope_channel_executor_failure_routes_to_422_pin_mismatch(
    monkeypatch, tmp_path
):
    """Codex DEC-V61-101 R1 MED closure: when setup_channel_bc raises
    BCSetupError (e.g., a pin doesn't resolve mid-flight because the
    classifier's _boundary_face_ids snapshot somehow disagrees with
    the executor's), the route layer must surface a 422
    channel_pin_mismatch — NOT generic 422 setup_channel_bc_failed
    or 500 write_failed.

    We exercise this by directly calling setup_channel_bc with a
    bogus inlet_face_id; the wrapper raises AIActionError(failing_check
    = setup_channel_bc_failed), and the route maps it via
    _setup_bc_failure_to_http to 422 channel_pin_mismatch.
    """
    from ui.backend.services.case_annotations import face_id

    # Stage a 1×1×10 channel mesh; pin a REAL outlet but a BOGUS inlet.
    points = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class vectorField;\n    location \"constant/polyMesh\";\n"
        "    object points;\n}\n\n8\n(\n"
        "(0 0 0)\n(1 0 0)\n(1 1 0)\n(0 1 0)\n"
        "(0 0 10)\n(1 0 10)\n(1 1 10)\n(0 1 10)\n)\n"
    )
    faces = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class faceList;\n    location \"constant/polyMesh\";\n"
        "    object faces;\n}\n\n6\n(\n"
        "4(0 1 2 3)\n4(4 5 6 7)\n4(0 1 5 4)\n"
        "4(2 3 7 6)\n4(1 2 6 5)\n4(0 3 7 4)\n)\n"
    )
    boundary = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class polyBoundaryMesh;\n"
        "    location \"constant/polyMesh\";\n    object boundary;\n}\n\n"
        "1\n(\n    walls\n    {\n        type wall;\n"
        "        nFaces 6;\n        startFace 0;\n    }\n)\n"
    )
    owner = (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        "    class labelList;\n    location \"constant/polyMesh\";\n"
        "    object owner;\n}\n\n6\n(\n0\n0\n0\n0\n0\n0\n)\n"
    )

    imported = _isolated_imported(monkeypatch, tmp_path)
    case_id = _safe_case_id()
    case_dir = _stage_imported_case(imported, case_id)
    polymesh = case_dir / "constant" / "polyMesh"
    polymesh.mkdir(parents=True)
    (polymesh / "points").write_text(points, encoding="utf-8")
    (polymesh / "faces").write_text(faces, encoding="utf-8")
    (polymesh / "boundary").write_text(boundary, encoding="utf-8")
    (polymesh / "owner").write_text(owner, encoding="utf-8")

    # Force the wrapper to invoke setup_channel_bc with a deliberately
    # mismatched pin set by patching the classifier to return confident
    # with a bogus inlet face_id (real outlet). This simulates the
    # mid-flight stale-pin race that the R1 HIGH guards against.
    real_outlet = face_id(
        [
            (0.0, 0.0, 10.0),
            (1.0, 0.0, 10.0),
            (1.0, 1.0, 10.0),
            (0.0, 1.0, 10.0),
        ]
    )

    from ui.backend.services.ai_actions import classifier as cls_mod

    fake_result = cls_mod.ClassificationResult(
        geometry_class="non_cube",
        confidence="confident",
        questions=[],
        summary="(test fixture)",
        rationale="test",
        inlet_face_ids=("fid_bogus0000000",),
        outlet_face_ids=(real_outlet,),
    )
    monkeypatch.setattr(
        "ui.backend.services.ai_actions.classify_setup_bc",
        lambda case_dir, annotations: fake_result,
    )

    client = _new_client()
    r = client.post(
        f"/api/import/{case_id}/setup-bc",
        params={"envelope": 1},
    )
    assert r.status_code == 422, r.text
    payload = r.json()
    assert payload["detail"]["failing_check"] == "channel_pin_mismatch"
    # Either "stale pins" (partial match) or "no boundary face matched"
    # (zero match) is valid — both are 422 channel_pin_mismatch with
    # an actionable engineer message.
    detail = payload["detail"]["detail"]
    assert (
        "stale pins" in detail or "no boundary face matched" in detail
    ), detail
