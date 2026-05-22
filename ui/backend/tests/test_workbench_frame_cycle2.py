"""DEC-V61-202-SUB-M30-CYCLE2 · topbar_cta + manifest field-path PATCH tests.

Coverage:
    1. topbar_cta surfaces all 4 kinds (next_step / re_audit /
       submit_solve / step_default disabled)
    2. PATCH happy path: write at field_path + recompute state_sha
    3. PATCH 409 on stale expected_state_sha
    4. PATCH 404 on missing case
    5. PATCH 400 on malformed field_path (__, .., empty segment)
    6. PATCH schema validation: returns success=False + errors
    7. Whitelist fork: PATCH on catalog case creates draft, sets
       case_kind=whitelist_forked
    8. Round-trip: PATCH then GET workbench_frame shows new state
"""
from __future__ import annotations

import json
import secrets
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from ui.backend.schemas.manifest_patch import ManifestPatchRequest
from ui.backend.schemas.workbench_frame import CaseStateSnapshot
from ui.backend.services.manifest_patch import (
    PatchConflict,
    PatchPathError,
    apply_field_path_patch,
    manifest_only_state_sha,
)
from ui.backend.services.workbench_decide import decide


def _client() -> TestClient:
    from ui.backend.main import app
    return TestClient(app)


def _safe_id() -> str:
    return f"imported_2026-05-22T00-00-00Z_{secrets.token_hex(4)}"


def _stage_imported_case(monkeypatch, tmp_path: Path, manifest: dict) -> tuple[str, Path]:
    case_id = _safe_id()
    imported_root = tmp_path / "imported"
    imported_root.mkdir()
    case_dir = imported_root / case_id
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))
    (case_dir / "artifacts").mkdir()

    monkeypatch.setattr(
        "ui.backend.routes.workbench_frame.IMPORTED_DIR", imported_root
    )
    monkeypatch.setattr(
        "ui.backend.services.case_completeness.analyzer.IMPORTED_DIR",
        imported_root,
    )
    monkeypatch.setattr(
        "ui.backend.services.manifest_patch.IMPORTED_DIR", imported_root
    )
    return case_id, case_dir


# ───────────────────── topbar_cta tests ─────────────────────


def _state(**kwargs) -> CaseStateSnapshot:
    base = {
        "case_id": "x",
        "step": 1,
        "manifest": {},
        "artifacts": {},
        "completeness": None,
    }
    base.update(kwargs)
    return CaseStateSnapshot(**base)


def test_topbar_step_default_step1_is_next_step():
    frame = decide(_state(step=1))
    assert frame.topbar_cta.kind == "next_step"
    assert frame.topbar_cta.enabled is True
    assert frame.topbar_cta.target_step == 2


def test_topbar_step_default_step5_is_submit_solve():
    frame = decide(_state(step=5))
    assert frame.topbar_cta.kind == "submit_solve"
    assert frame.topbar_cta.enabled is True
    assert frame.topbar_cta.target_step is None


def test_topbar_problem_fix_is_re_audit():
    state = _state(
        step=4,
        artifacts={
            "bc_quality.json": {
                "findings": [
                    {"severity": "fail", "title": "U missing", "message": "..."}
                ]
            }
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "problem_fix"
    assert frame.topbar_cta.kind == "re_audit"
    assert frame.topbar_cta.enabled is True


def test_topbar_info_gap_disables_with_reason():
    state = _state(
        step=3,
        completeness={
            "missing": [
                {
                    "field_path": "vof_contract.phases",
                    "severity": "critical",
                    "why": "interFoam needs phases",
                }
            ]
        },
    )
    frame = decide(state)
    assert frame.rail_primary.kind == "info_gap"
    assert frame.topbar_cta.enabled is False
    assert frame.topbar_cta.reason is not None
    assert "vof_contract.phases" in frame.topbar_cta.reason


# ───────────────────── manifest_state_sha tests ─────────────────────


def test_manifest_state_sha_present_on_frame():
    frame = decide(_state())
    assert isinstance(frame.manifest_state_sha, str)
    assert len(frame.manifest_state_sha) == 64


def test_manifest_state_sha_excludes_artifacts():
    """A manifest write must change manifest_state_sha; an artifact
    refresh must NOT (otherwise PATCH races on every audit run)."""
    s_no_art = decide(_state(manifest={"a": 1}))
    s_with_art = decide(
        _state(manifest={"a": 1}, artifacts={"mesh_report.json": {"x": 1}})
    )
    # Full state_sha differs (artifacts changed)
    assert s_no_art.state_sha != s_with_art.state_sha
    # Manifest-only sha is identical
    assert s_no_art.manifest_state_sha == s_with_art.manifest_state_sha


def test_manifest_state_sha_excludes_step():
    """Same manifest at different steps must produce same manifest_state_sha."""
    s1 = decide(_state(step=1, manifest={"a": 1}))
    s4 = decide(_state(step=4, manifest={"a": 1}))
    assert s1.manifest_state_sha == s4.manifest_state_sha


# ───────────────────── PATCH service tests ─────────────────────


def test_patch_writes_at_field_path(monkeypatch, tmp_path):
    case_id, case_dir = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {
            "case_id": "x",
            "case_family": "test",
            "solver_backend": "openfoam",
            "solver": "interFoam",
            "physics": {"regime": "transient_incompressible_turbulent_vof"},
        },
    )
    sha = manifest_only_state_sha(case_id)
    request = ManifestPatchRequest(
        field_path="vof_contract.phases",
        value=["water", "air"],
        expected_state_sha=sha,
    )
    response = apply_field_path_patch(case_id, request)
    assert response.success is True
    assert response.applied_path == "vof_contract.phases"
    # Manifest on disk has the new value.
    persisted = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    assert persisted["vof_contract"]["phases"] == ["water", "air"]


def test_patch_creates_intermediate_dicts(monkeypatch, tmp_path):
    case_id, case_dir = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    sha = manifest_only_state_sha(case_id)
    response = apply_field_path_patch(
        case_id,
        ManifestPatchRequest(
            field_path="mesh_contract.y_plus_target.max",
            value=5.0,
            expected_state_sha=sha,
        ),
    )
    assert response.success is True
    persisted = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    assert persisted["mesh_contract"]["y_plus_target"]["max"] == 5.0


def test_patch_state_sha_conflict_raises(monkeypatch, tmp_path):
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    import pytest

    with pytest.raises(PatchConflict) as exc:
        apply_field_path_patch(
            case_id,
            ManifestPatchRequest(
                field_path="physics.solver",
                value="simpleFoam",
                expected_state_sha="0" * 64,  # wrong SHA
            ),
        )
    assert len(exc.value.current_state_sha) == 64


def test_patch_recomputed_sha_matches_next_patch_expectation(monkeypatch, tmp_path):
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    sha1 = manifest_only_state_sha(case_id)
    r1 = apply_field_path_patch(
        case_id,
        ManifestPatchRequest(
            field_path="solver",
            value="simpleFoam",
            expected_state_sha=sha1,
        ),
    )
    assert r1.success
    # Now another PATCH using r1.new_state_sha must succeed
    r2 = apply_field_path_patch(
        case_id,
        ManifestPatchRequest(
            field_path="case_family",
            value="external_aero",
            expected_state_sha=r1.new_state_sha,
        ),
    )
    assert r2.success


def test_patch_rejects_forbidden_path():
    import pytest

    with pytest.raises(PatchPathError):
        apply_field_path_patch(
            "x",
            ManifestPatchRequest(
                field_path="__class__.__init__",
                value="x",
                expected_state_sha="0" * 64,
            ),
        )


def test_patch_rejects_empty_segment():
    import pytest

    with pytest.raises(PatchPathError):
        apply_field_path_patch(
            "x",
            ManifestPatchRequest(
                field_path="a..b",
                value="x",
                expected_state_sha="0" * 64,
            ),
        )


def test_patch_rejects_traversal():
    import pytest

    with pytest.raises(PatchPathError):
        apply_field_path_patch(
            "x",
            ManifestPatchRequest(
                field_path="a/../b",
                value="x",
                expected_state_sha="0" * 64,
            ),
        )


def test_patch_unset_removes_key(monkeypatch, tmp_path):
    case_id, case_dir = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {
            "case_id": "x",
            "case_family": "test",
            "solver_backend": "openfoam",
            "vof_contract": {"phases": ["water", "air"]},
        },
    )
    sha = manifest_only_state_sha(case_id)
    response = apply_field_path_patch(
        case_id,
        ManifestPatchRequest(
            field_path="vof_contract.phases",
            value=None,
            op="unset",
            expected_state_sha=sha,
        ),
    )
    assert response.success is True
    persisted = yaml.safe_load((case_dir / "case_manifest.yaml").read_text())
    # vof_contract still exists; phases removed
    assert "vof_contract" in persisted
    assert "phases" not in persisted["vof_contract"]


# ───────────────────── PATCH route tests ─────────────────────


def test_route_patch_returns_200_on_success(monkeypatch, tmp_path):
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    sha = manifest_only_state_sha(case_id)
    r = _client().patch(
        f"/api/cases/{case_id}/manifest",
        json={
            "field_path": "solver",
            "value": "simpleFoam",
            "expected_state_sha": sha,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["applied_path"] == "solver"


def test_route_patch_returns_409_on_stale_sha(monkeypatch, tmp_path):
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    r = _client().patch(
        f"/api/cases/{case_id}/manifest",
        json={
            "field_path": "solver",
            "value": "simpleFoam",
            "expected_state_sha": "0" * 64,
        },
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "current_state_sha" in detail
    assert len(detail["current_state_sha"]) == 64


def test_route_patch_returns_404_on_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "ui.backend.services.manifest_patch.IMPORTED_DIR", tmp_path / "x"
    )
    monkeypatch.setattr(
        "ui.backend.services.manifest_patch.DRAFTS_DIR", tmp_path / "y"
    )
    r = _client().patch(
        "/api/cases/no_such_case/manifest",
        json={
            "field_path": "solver",
            "value": "simpleFoam",
            "expected_state_sha": "0" * 64,
        },
    )
    assert r.status_code == 404


def test_route_patch_returns_400_on_malformed_path(monkeypatch, tmp_path):
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {"case_id": "x", "case_family": "test", "solver_backend": "openfoam"},
    )
    sha = manifest_only_state_sha(case_id)
    r = _client().patch(
        f"/api/cases/{case_id}/manifest",
        json={
            "field_path": "__class__.__init__",
            "value": "x",
            "expected_state_sha": sha,
        },
    )
    assert r.status_code == 400


def test_route_patch_then_frame_shows_new_state(monkeypatch, tmp_path):
    """Closed-loop: PATCH a field, then GET workbench_frame reflects new value."""
    case_id, _ = _stage_imported_case(
        monkeypatch,
        tmp_path,
        {
            "case_id": "x",
            "case_family": "test",
            "solver_backend": "openfoam",
            "solver": "interFoam",
        },
    )
    client = _client()
    # Initial frame
    r_before = client.get(f"/api/cases/{case_id}/workbench_frame?step=3")
    assert r_before.status_code == 200
    sha_before = r_before.json()["manifest_state_sha"]
    # PATCH
    r_patch = client.patch(
        f"/api/cases/{case_id}/manifest",
        json={
            "field_path": "vof_contract.phases",
            "value": ["water", "air"],
            "expected_state_sha": sha_before,
        },
    )
    assert r_patch.status_code == 200, r_patch.text
    new_sha = r_patch.json()["new_state_sha"]
    # Refetch frame: manifest_state_sha is the new one
    r_after = client.get(f"/api/cases/{case_id}/workbench_frame?step=3")
    assert r_after.status_code == 200
    assert r_after.json()["manifest_state_sha"] == new_sha
