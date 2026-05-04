"""DEC-V61-121 · POST /api/ai-coach/apply-proposal route tests.

Coverage:
  * 200 happy path with audit_id present
  * 400 unknown tool
  * 400 bad case_id
  * 400 arg validation failure
  * 403 non-loopback caller without override
  * 404 case dir doesn't exist
  * 422 underlying-service error mapping
  * 200 + audit_warning when audit write fails AFTER dispatch
  * loopback guard inheritance same as /api/ai-coach/stream
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_coach as ai_coach_route


def _make_app(tmp_path: Path, monkeypatch) -> FastAPI:
    """Build a fresh app with IMPORTED_DIR pointed at tmp_path so each
    test can write to an isolated case directory."""
    monkeypatch.setattr(ai_coach_route, "IMPORTED_DIR", tmp_path)
    app = FastAPI()
    app.include_router(ai_coach_route.router, prefix="/api")
    return app


def _make_case(tmp_path: Path, case_id: str = "lid_driven_cavity") -> Path:
    case_dir = tmp_path / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    return case_dir


# ────────── Happy path ──────────


def test_apply_proposal_200_writes_override_and_returns_audit_id(
    tmp_path, monkeypatch
):
    case_dir = _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
                "model_used": "deepseek-v4-pro",
                "conversation_turn_id": "turn-1",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["applied"] is True
        assert body["tool"] == "set_patch_bc_type"
        assert "walls" in body["summary"]
        assert body["state_after"]["overrides"]["walls"] == "no_slip_wall"
        assert isinstance(body["audit_id"], str) and len(body["audit_id"]) >= 16
        # No audit warning expected on the happy path.
        assert "audit_warning" not in body

    # Underlying V108 file written.
    assert (case_dir / "system" / "patch_classification.yaml").is_file()
    # Audit log written.
    audit_path = case_dir / "system" / "ai_audit" / "applied.yaml"
    assert audit_path.is_file()
    audit_doc = yaml.safe_load(audit_path.read_text())
    assert audit_doc["entries"][0]["model_used"] == "deepseek-v4-pro"
    assert audit_doc["entries"][0]["conversation_turn_id"] == "turn-1"


# ────────── 4xx mappings ──────────


def test_apply_proposal_400_unknown_tool(tmp_path, monkeypatch):
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "drop_database",
                "args": {},
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["failing_check"] == "unknown_tool"
        assert body["detail"]["tool"] == "drop_database"


def test_apply_proposal_400_bad_args(tmp_path, monkeypatch):
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "garbage"},
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["failing_check"] == "arg_validation_failed"
        assert body["detail"]["tool"] == "set_patch_bc_type"
        assert isinstance(body["detail"]["errors"], list)


def test_apply_proposal_400_bad_case_id(tmp_path, monkeypatch):
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        # Path-traversal-shaped case_id is rejected by is_safe_case_id.
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "../etc/passwd",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["failing_check"] == "bad_case_id"


def test_apply_proposal_404_case_not_found(tmp_path, monkeypatch):
    # No case dir created.
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "missing_case",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["failing_check"] == "case_not_found"


def test_apply_proposal_403_non_loopback(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_CHAT_ALLOW_NON_LOOPBACK", raising=False)
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
            headers={"x-forwarded-for": "203.0.113.5, 127.0.0.1"},
        )
        assert resp.status_code == 403


def test_apply_proposal_override_allows_proxy(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
            headers={"x-forwarded-for": "203.0.113.5"},
        )
        assert resp.status_code == 200


# ────────── Audit-write compensation path ──────────


def test_apply_proposal_audit_write_failure_returns_warning(
    tmp_path, monkeypatch
):
    """When the underlying dispatch succeeds but audit write fails,
    the route returns 200 with audit_warning so the UI knows the
    change DID apply but wasn't logged."""
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)

    from ui.backend.services.llm_coach.audit import AuditWriteError as _AWE
    from ui.backend.routes import ai_coach as route_module

    def _failing_audit(case_dir, **kwargs):
        raise _AWE("simulated disk full")

    monkeypatch.setattr(route_module, "write_audit", _failing_audit)

    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is True
        assert body["audit_id"] is None
        assert "audit_warning" in body
        assert "simulated disk full" in body["audit_warning"]


# ────────── 422 underlying-service error ──────────


def test_apply_proposal_422_on_underlying_service_error(tmp_path, monkeypatch):
    """When the V108 service raises a typed PatchClassificationIOError,
    the route translates it to 422 with structured detail."""
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)

    # The tool_registry module imports `upsert_override` into its own
    # namespace at module load. Patching the source module does NOT
    # rebind the already-imported reference — patch where the
    # lookup happens (the tool_registry module).
    from ui.backend.services.llm_coach import tool_registry as registry_module
    from ui.backend.services.case_solve.patch_classification_store import (
        PatchClassificationIOError,
    )

    def _failing_upsert(case_dir, **kwargs):
        raise PatchClassificationIOError(
            "lock acquire failed", failing_check="lock_acquire_failed"
        )

    monkeypatch.setattr(
        registry_module, "upsert_override", _failing_upsert
    )

    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["failing_check"] == "underlying_service_error"
        # V123 R2 P2-2: the underlying typed code must be plumbed
        # through to the response body so the frontend ProposalCard
        # can branch on it for actionable remediation.
        assert body["detail"]["inner_failing_check"] == "lock_acquire_failed"


def test_apply_proposal_planted_regular_file_routes_to_symlink_escape(
    tmp_path, monkeypatch
):
    """V123 R3 P2: a tampered case_dir (regular file planted at the
    case-id path) must NOT be rejected at the route as 404
    case_not_found. The route's pre-check uses os.path.lexists so
    tampered paths fall through to dispatch + case_lock, which surface
    them as 422 with inner_failing_check='symlink_escape', matching
    V108/V109's tamper-path contract."""
    # Plant a regular file at the case-id path BEFORE _make_app so
    # the route's pre-check sees the planted file.
    planted = tmp_path / "ldc_planted"
    planted.write_text("not a directory")
    app = _make_app(tmp_path, monkeypatch)

    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "ldc_planted",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        # Tampered path → fell through to dispatch → case_lock raised
        # symlink_escape → 422 with inner_failing_check.
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["detail"]["failing_check"] == "underlying_service_error"
        assert body["detail"]["inner_failing_check"] == "symlink_escape"


def test_apply_proposal_tampered_case_dir_with_unknown_tool_still_returns_symlink_escape(
    tmp_path, monkeypatch
):
    """V123 R4 P2: tamper-path contract must hold end-to-end —
    a planted file at the case_dir path with an UNKNOWN TOOL must
    return 422 symlink_escape, NOT 400 unknown_tool. The route's
    explicit tamper-check preempts tool dispatch."""
    planted = tmp_path / "ldc_planted_unknowntool"
    planted.write_text("not a directory")
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "ldc_planted_unknowntool",
                "tool": "no_such_tool",
                "args": {"x": 1},
            },
        )
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["detail"]["failing_check"] == "underlying_service_error"
        assert body["detail"]["inner_failing_check"] == "symlink_escape"


def test_apply_proposal_tampered_case_dir_with_invalid_args_still_returns_symlink_escape(
    tmp_path, monkeypatch
):
    """V123 R4 P2: same contract for ARG-VALIDATION-FAILED — tamper
    check preempts arg validation."""
    planted = tmp_path / "ldc_planted_badargs"
    planted.write_text("not a directory")
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "ldc_planted_badargs",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "garbage"},
            },
        )
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["detail"]["failing_check"] == "underlying_service_error"
        assert body["detail"]["inner_failing_check"] == "symlink_escape"


def test_apply_proposal_truly_absent_case_dir_still_returns_404(
    tmp_path, monkeypatch
):
    """V123 R3 P2 negative: a TRULY absent case_id (lexists()=False) must
    still return the existing 404 case_not_found contract — the lexists
    switch must not erode the absent-vs-tampered distinction."""
    app = _make_app(tmp_path, monkeypatch)
    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "totally_absent",
                "tool": "set_patch_bc_type",
                "args": {"patch_name": "walls", "bc_class": "no_slip_wall"},
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["failing_check"] == "case_not_found"


def test_apply_proposal_422_regenerate_mesh_inner_failing_check_plumbed(
    tmp_path, monkeypatch
):
    """V123 R2 P2-2: when the regenerate_mesh path fails with a
    structured MeshPipelineError, the response body must include
    detail.inner_failing_check so the frontend ProposalCard surfaces
    the actionable remediation hint (cell_cap_exceeded etc) instead
    of a generic 'underlying_service_error'."""
    _make_case(tmp_path)
    app = _make_app(tmp_path, monkeypatch)

    from ui.backend.services.llm_coach import tool_registry as registry_module
    from ui.backend.services.meshing_gmsh import MeshPipelineError

    def fake_mesh(case_id, *, mesh_mode):
        raise MeshPipelineError("hard cap exceeded", "cell_cap_exceeded")

    monkeypatch.setattr(registry_module, "mesh_imported_case", fake_mesh)

    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-coach/apply-proposal",
            json={
                "case_id": "lid_driven_cavity",
                "tool": "regenerate_mesh",
                "args": {"mesh_mode": "power"},
            },
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"]["failing_check"] == "underlying_service_error"
        assert body["detail"]["inner_failing_check"] == "cell_cap_exceeded"
        assert "cell_cap_exceeded" in body["detail"]["message"]
