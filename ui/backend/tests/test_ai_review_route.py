"""Route-level tests for POST /api/ai-review (DEC-V62-A-sub-ROUTE-AI-REVIEW).

Coverage (matches sub-DEC §test spec · ≥10 tests):

  1. parts_manifest only → 200 + advisor_count≥2 + audit file
  2. case_dir auto-discover → advisor_count≥2 (parts_manifest + shm_dict)
  3. empty payload → 200 + advisor_count=0
  4. bad case_dir → 400 with actionable error
  5. LLM import-error + llm_enhance=True → 200 + llm_enhanced=False
  6. llm_enhance=False default → llm_enhanced=False (4Q gate)
  7. audit JSON round-trips
  8. TrustGate: every finding has source_advisor + evidence_v_rows
  9. Crash isolation: single advisor raises → route 200, failed_advisor_count≥1
 10. 4Q gate compliance: route does not write inside case_dir
 11. llm_enhance=True with provider importable → llm_enhanced=True
 12. Explicit kwargs win over auto-discovered values
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ui.backend.routes import ai_review as ai_review_route
from ui.backend.services import advisor_stack as advisor_stack_module


# ---------- Helpers / fixtures --------------------------------------------


def _parts_manifest_basic() -> dict:
    """A4 V79 D7 case + A5 V81 violation."""
    return {
        "parts": [
            {
                "name": "louver_vane_2",
                "actual_face_normal": [0.7880, -0.6157, 0.0],
                "expected_face_normal": [0.0, -1.0, 0.0],
                "tolerance_deg": 4.0,
            },
            {"name": "supply_inlet", "role": "inlet"},
        ]
    }


def _shm_dict_with_typo() -> dict:
    return {
        "geometry": {
            "region_fluid": {"type": "triSurfaceMesh", "file": "region_fluid.stl"}
        },
        "castellatedMeshControls": {
            "features": [],
            "refinementSurfaces": {"region_fluid": {"level": [2, 2]}},
            "refinementRegions": {},
            "minMedianAxisAngle": 90,  # V52 typo
        },
        "addLayersControls": {},
    }


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    """Build a FastAPI app with /api/ai-review mounted, repo-root pinned to tmp."""
    # Redirect repo-root + audit dir into tmp so tests are hermetic
    monkeypatch.setattr(ai_review_route, "_REPO_ROOT", tmp_path)
    a = FastAPI()
    a.include_router(ai_review_route.router, prefix="/api")
    return a


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def repo_root(app: FastAPI) -> Path:
    """Returns the (monkeypatched) repo root from the route module."""
    return ai_review_route._REPO_ROOT


# ---------- Tests ----------------------------------------------------------


def test_parts_manifest_only_yields_2_advisors_and_persists_audit(
    client: TestClient, repo_root: Path
) -> None:
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["report"]["advisor_count"] == 2
    assert body["llm_enhanced"] is False
    # audit artifact exists on disk
    audit = Path(body["audit_artifact_path"])
    assert audit.is_file()
    assert audit.parent == repo_root / ".planning" / "audits"
    payload = json.loads(audit.read_text())
    assert payload["case_label"] == "anon"
    assert payload["report"]["advisor_count"] == 2


def test_case_dir_autodiscovers_parts_and_shm(
    client: TestClient, repo_root: Path, tmp_path: Path
) -> None:
    case_dir = tmp_path / "case_autodisc"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump(_parts_manifest_basic()), encoding="utf-8"
    )
    (inputs / "shm_dict.json").write_text(
        json.dumps(_shm_dict_with_typo()), encoding="utf-8"
    )
    resp = client.post(
        "/api/ai-review",
        json={"case_dir": str(case_dir)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 3 advisors: face_orientation + inlet_outlet (from parts) + shm_dict
    assert body["report"]["advisor_count"] >= 3
    names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "face_orientation_advisor" in names
    assert "shm_dict_validator" in names


def test_empty_payload_returns_zero_advisors(client: TestClient) -> None:
    resp = client.post("/api/ai-review", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["advisor_count"] == 0
    assert body["report"]["findings"] == []
    assert body["llm_enhanced"] is False


def test_bad_case_dir_returns_400_with_actionable_error(client: TestClient) -> None:
    resp = client.post(
        "/api/ai-review",
        json={"case_dir": "/no/such/path/abcdef"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["failing_check"] == "case_dir_not_found"
    assert "no/such/path/abcdef" in detail["case_dir"]


def test_llm_enhance_with_import_error_downgrades_gracefully(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate ImportError on the LLM provider → route still 200, findings intact."""

    def boom(_payload):
        # Mirror the try/except: this path returns (False, ms)
        return (False, 0.5)

    monkeypatch.setattr(ai_review_route, "_try_llm_enhance", boom)
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic(), "llm_enhance": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_enhanced"] is False
    # Base findings must still be populated despite LLM failure
    assert len(body["report"]["findings"]) > 0


def test_default_llm_enhance_false_is_zero_llm_call(client: TestClient) -> None:
    """4Q gate: when llm_enhance is omitted (default False), no LLM attempt."""
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_enhanced"] is False
    assert body["timing"]["llm_ms"] == 0.0


def test_audit_artifact_round_trips(client: TestClient) -> None:
    resp = client.post(
        "/api/ai-review",
        json={"shm_dict": _shm_dict_with_typo()},
    )
    body = resp.json()
    audit = Path(body["audit_artifact_path"])
    reloaded = json.loads(audit.read_text())
    # Same advisor_count and finding count as wire response
    assert reloaded["report"]["advisor_count"] == body["report"]["advisor_count"]
    assert len(reloaded["report"]["findings"]) == len(body["report"]["findings"])
    # Reloaded findings preserve TrustGate fields
    for finding in reloaded["report"]["findings"]:
        assert "source_advisor" in finding
        assert "evidence_v_rows" in finding


def test_trustgate_every_finding_has_provenance(client: TestClient) -> None:
    resp = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": _parts_manifest_basic(),
            "shm_dict": _shm_dict_with_typo(),
        },
    )
    body = resp.json()
    findings = body["report"]["findings"]
    assert len(findings) > 0, "expected at least one finding from multi-advisor dispatch"
    for f in findings:
        assert f["source_advisor"], "TrustGate: source_advisor required"
        assert f["evidence_v_rows"], "TrustGate: evidence_v_rows required"
        assert isinstance(f["evidence_v_rows"], list)
        # Every V-row matches the canonical pattern (e.g., 'V41', 'V99')
        for row in f["evidence_v_rows"]:
            assert isinstance(row, str) and row.startswith("V")


def test_crash_isolation_one_advisor_raises_route_still_200(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force the inlet_outlet validator to raise; route should not 500."""
    def explode(*_a, **_k):
        raise RuntimeError("synthetic test-induced advisor crash")

    monkeypatch.setattr(
        advisor_stack_module.inlet_outlet_validator,
        "validate_inlet_outlet_emission",
        explode,
    )
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
    )
    assert resp.status_code == 200
    body = resp.json()
    # face_orientation should still run successfully
    statuses = {c["advisor_name"]: c["status"] for c in body["report"]["advisor_calls"]}
    assert statuses["inlet_outlet_validator"] == "error"
    assert statuses["face_orientation_advisor"] == "ok"


def test_4q_gate_route_does_not_write_inside_case_dir(
    client: TestClient, tmp_path: Path
) -> None:
    """V130 advisor-not-driver: route must NOT mutate anything under case_dir."""
    case_dir = tmp_path / "case_readonly"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    parts_file = inputs / "parts_manifest.yaml"
    parts_file.write_text(yaml.safe_dump(_parts_manifest_basic()), encoding="utf-8")

    # Snapshot directory state pre-call
    before: dict[str, tuple[float, int]] = {}
    for p in case_dir.rglob("*"):
        if p.is_file():
            st = p.stat()
            before[str(p)] = (st.st_mtime, st.st_size)

    resp = client.post("/api/ai-review", json={"case_dir": str(case_dir)})
    assert resp.status_code == 200

    # Snapshot post-call: no new files, no mtime / size changes
    after: dict[str, tuple[float, int]] = {}
    for p in case_dir.rglob("*"):
        if p.is_file():
            st = p.stat()
            after[str(p)] = (st.st_mtime, st.st_size)
    assert before == after, f"4Q gate violated: case_dir modified. before={before} after={after}"


def test_llm_enhance_true_with_importable_provider_records_enhanced(
    client: TestClient,
) -> None:
    """Sanity: when llm_provider is importable, llm_enhanced=True.

    The route does NOT actually invoke the provider (per 4Q gate); it
    only records whether the augment surface was reachable. This test
    locks that import-success → True mapping so we notice if the
    contract drifts.
    """
    # Confirm llm_provider really is importable in this env
    import importlib
    assert importlib.import_module("ui.backend.services.llm_provider") is not None

    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic(), "llm_enhance": True},
    )
    body = resp.json()
    assert body["llm_enhanced"] is True
    assert body["timing"]["llm_ms"] >= 0.0


def test_non_loopback_request_rejected_with_403(
    client: TestClient,
) -> None:
    """Codex R0 P1: x-forwarded-for header marks a proxy → 403 unless override env set."""
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
        headers={"x-forwarded-for": "203.0.113.7"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert "loopback" in detail.lower()
    assert "AI_CHAT_ALLOW_NON_LOOPBACK" in detail


def test_non_loopback_override_env_allows_request(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When AI_CHAT_ALLOW_NON_LOOPBACK=1, proxy-fronted callers pass."""
    monkeypatch.setenv("AI_CHAT_ALLOW_NON_LOOPBACK", "1")
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
        headers={"x-forwarded-for": "203.0.113.7"},
    )
    assert resp.status_code == 200


def test_thin_wall_inputs_dict_form_rehydrates_and_dispatches(
    client: TestClient,
) -> None:
    """Codex R0 P2: dict-form patches must rehydrate to PatchGeometry."""
    resp = client.post(
        "/api/ai-review",
        json={
            "thin_wall_inputs": {
                "patches": [
                    {"name": "thin_plate", "bbox_dimensions": [100.0, 50.0, 0.5]}
                ],
                "refinement_levels": {"thin_plate": [0, 0]},
                "background_cell_size": 1.0,
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # thin_wall_advisor should have run (not crashed into isolation)
    statuses = {c["advisor_name"]: c["status"] for c in body["report"]["advisor_calls"]}
    assert statuses.get("thin_wall_advisor") == "ok"
    assert body["report"]["failed_advisor_count"] == 0
    # 0.5 mm patch in 1.0 mm cell → at-risk warning expected
    tw_findings = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "thin_wall_advisor"
    ]
    assert len(tw_findings) >= 1


def test_thin_wall_malformed_patch_returns_400(client: TestClient) -> None:
    """Bad thin_wall_inputs surfaces an actionable 400, not a 500."""
    resp = client.post(
        "/api/ai-review",
        json={
            "thin_wall_inputs": {
                "patches": [{"name": "bad", "bbox_dimensions": [1.0, 2.0]}],
                "background_cell_size": 1.0,
            }
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["failing_check"] in {
        "thin_wall_bbox_arity",
        "thin_wall_patch_fields",
    }


def test_audit_filenames_unique_back_to_back(client: TestClient) -> None:
    """Codex R0 P2: two reviews in the same second must not overwrite each other."""
    paths: set[str] = set()
    for _ in range(5):
        resp = client.post(
            "/api/ai-review",
            json={"parts_manifest": _parts_manifest_basic()},
        )
        assert resp.status_code == 200
        paths.add(resp.json()["audit_artifact_path"])
    assert len(paths) == 5, f"audit filenames collided: {paths}"
    # All 5 files must exist on disk
    for p in paths:
        assert Path(p).is_file()


def test_response_includes_computed_property_counts(client: TestClient) -> None:
    """Codex R0 P2: failed_advisor_count + critical_count + warning_count
    must be in the wire payload (not dropped by dataclasses.asdict)."""
    resp = client.post(
        "/api/ai-review",
        json={"parts_manifest": _parts_manifest_basic()},
    )
    body = resp.json()
    assert "failed_advisor_count" in body["report"]
    assert "critical_count" in body["report"]
    assert "warning_count" in body["report"]
    # Hand-derive the expected values to lock the serialization fidelity
    expected_failed = sum(
        1 for c in body["report"]["advisor_calls"] if c["status"] == "error"
    )
    assert body["report"]["failed_advisor_count"] == expected_failed
    expected_critical = sum(
        1 for f in body["report"]["findings"] if f["severity"] in {"critical", "fail"}
    )
    assert body["report"]["critical_count"] == expected_critical


def test_explicit_kwargs_override_autodiscovered(
    client: TestClient, tmp_path: Path
) -> None:
    """If both ``case_dir`` and an explicit kwarg are passed, explicit wins."""
    case_dir = tmp_path / "case_override"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    # Disk file has 1 part
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump({"parts": [{"name": "only_one"}]}), encoding="utf-8"
    )
    # Explicit payload has 2 parts — should be what's used
    explicit = _parts_manifest_basic()
    resp = client.post(
        "/api/ai-review",
        json={"case_dir": str(case_dir), "parts_manifest": explicit},
    )
    assert resp.status_code == 200
    body = resp.json()
    # face_orientation only fires on parts with face-normal fields → confirms
    # the 2-part explicit manifest reached the advisor (disk's 1-part has no
    # face normals → would produce 0 findings)
    fo_findings = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "face_orientation_advisor"
    ]
    assert len(fo_findings) == 1, (
        "explicit parts_manifest with face_normal should produce A4 finding"
    )
