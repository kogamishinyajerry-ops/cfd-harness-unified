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


def test_thin_wall_overflow_bbox_returns_400_not_500(client: TestClient) -> None:
    """Codex R1 P2: oversized int in bbox raises OverflowError → must be 400, not 500."""
    huge = 10**400  # well past float overflow
    resp = client.post(
        "/api/ai-review",
        json={
            "thin_wall_inputs": {
                "patches": [{"name": "p", "bbox_dimensions": [huge, 1.0, 1.0]}],
                "background_cell_size": 1.0,
            }
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["failing_check"] == "thin_wall_patch_fields"


@pytest.mark.parametrize("bad_patches", ["", 0, {}, 42, "patches_str"])
def test_thin_wall_non_iterable_patches_returns_400(
    client: TestClient, bad_patches
) -> None:
    """Codex R1 P3: falsey/scalar/non-list ``patches`` must surface as 400,
    not be silently normalized to an empty tuple."""
    resp = client.post(
        "/api/ai-review",
        json={
            "thin_wall_inputs": {
                "patches": bad_patches,
                "background_cell_size": 1.0,
            }
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["failing_check"] == "thin_wall_patches_type"


def test_thin_wall_absent_patches_key_is_not_400(client: TestClient) -> None:
    """Absent key is still OK — only invalid-non-iterable is 400. Keeps the
    discrimination Codex R1 P3 asked for: 'absent' vs 'malformed' are different."""
    resp = client.post(
        "/api/ai-review",
        json={
            "thin_wall_inputs": {"background_cell_size": 1.0},
        },
    )
    assert resp.status_code == 200
    # No patches → advisor runs with empty input, may produce no findings
    statuses = {c["advisor_name"]: c["status"] for c in resp.json()["report"]["advisor_calls"]}
    assert statuses.get("thin_wall_advisor") == "ok"


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


# ---------- DEC-V62-A-sub-REQ-SCHEMA-EXPAND (2026-05-14) -------------------
# Five new tests verify the wire schema expansion unblocks unit_detector
# (gated on step_path) and A2-v2 virtual_interface_detector (gated on
# interface_bodies + interface_specs) in the HTTP path, closes the
# M-STACK-TRACK-1 §8 / TRACK-2 divergence (Python path 5 advisors vs
# HTTP path 4 advisors). 25 prior tests remain untouched.


def _ifc_body(name: str, *, cx: float, cy: float = 0.0, cz: float = 0.0) -> dict:
    """Construct a minimal BodyGeometry wire-form dict with one face.

    A single +x-facing endcap face at the centroid is enough to exercise
    InterfaceSpec(mode='endcap', axis='+x') routing without depending on
    specific gap thresholds.
    """
    return {
        "name": name,
        "centroid": [cx, cy, cz],
        "faces": [
            {
                "area": 1.0,
                "bbox_min": [cx, cy - 0.5, cz - 0.5],
                "bbox_max": [cx, cy + 0.5, cz + 0.5],
                "normal": [1.0, 0.0, 0.0],
                "centroid": [cx, cy, cz],
            }
        ],
    }


def test_step_path_routes_to_unit_detector(
    client: TestClient, tmp_path: Path
) -> None:
    """step_path field → unit_detector appears in audit trail."""
    fake_step = tmp_path / "phantom.step"
    fake_step.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    resp = client.post(
        "/api/ai-review",
        json={
            "step_path": str(fake_step),
            "step_bbox": [0.0, 0.0, 0.0, 0.180, 0.150, 0.090],
            "step_extents": [0.180, 0.150, 0.090],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "unit_detector" in names, (
        f"unit_detector missing from advisors {names} — schema expansion "
        "did not plumb step_path through to assemble_stack"
    )


def test_interface_bodies_routes_to_a2v2_virtual_interface_detector(
    client: TestClient,
) -> None:
    """interface_bodies + interface_specs → virtual_interface_detector dispatches."""
    bodies = [_ifc_body("body_a", cx=0.0), _ifc_body("body_b", cx=1.0)]
    specs = [
        {
            "patch_name": "if_ab",
            "mode": "endcap",
            "body": "body_a",
            "axis": "+x",
        }
    ]
    resp = client.post(
        "/api/ai-review",
        json={"interface_bodies": bodies, "interface_specs": specs},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "virtual_interface_detector" in names, (
        f"A2-v2 missing from advisors {names} — schema expansion did not "
        "plumb interface_bodies/specs through to assemble_stack"
    )
    statuses = {c["advisor_name"]: c["status"] for c in body["report"]["advisor_calls"]}
    assert statuses["virtual_interface_detector"] == "ok"


def test_auto_discover_step_path_from_case_dir(
    client: TestClient, tmp_path: Path
) -> None:
    """case_dir/*.step picked up when explicit step_path is absent."""
    case_dir = tmp_path / "case_auto_step"
    case_dir.mkdir()
    (case_dir / "cad").mkdir()
    step_in_cad = case_dir / "cad" / "geometry.step"
    step_in_cad.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")

    resp = client.post(
        "/api/ai-review",
        json={"case_dir": str(case_dir)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "unit_detector" in names
    # Confirm the auto-discovered path actually flows into the input_summary
    unit_call = next(
        c for c in body["report"]["advisor_calls"]
        if c["advisor_name"] == "unit_detector"
    )
    assert "geometry.step" in unit_call["input_summary"]


def test_auto_discover_interface_bodies_from_manifest(
    client: TestClient, tmp_path: Path
) -> None:
    """case_dir/manifest.json carrying interface_bodies/specs lights up A2-v2."""
    case_dir = tmp_path / "case_auto_ifc"
    case_dir.mkdir()
    manifest = {
        "interface_bodies": [_ifc_body("b1", cx=0.0), _ifc_body("b2", cx=1.0)],
        "interface_specs": [
            {"patch_name": "if_12", "mode": "endcap", "body": "b1", "axis": "+x"}
        ],
    }
    (case_dir / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    resp = client.post(
        "/api/ai-review",
        json={"case_dir": str(case_dir)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "virtual_interface_detector" in names


def test_explicit_step_and_interface_override_auto_discover(
    client: TestClient, tmp_path: Path
) -> None:
    """Explicit step_path / interface_bodies override case_dir auto-discovery."""
    case_dir = tmp_path / "case_override_v2"
    case_dir.mkdir()
    (case_dir / "cad").mkdir()
    # Disk file is at one path
    (case_dir / "cad" / "discovered.step").write_text(
        "ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8"
    )
    # Disk manifest has one body pair
    (case_dir / "manifest.json").write_text(
        json.dumps({"interface_bodies": [_ifc_body("disk_body", cx=0.0)]}),
        encoding="utf-8",
    )
    # Explicit payload uses a different STEP path + DIFFERENT body set
    explicit_step = tmp_path / "explicit.step"
    explicit_step.write_text(
        "ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8"
    )
    resp = client.post(
        "/api/ai-review",
        json={
            "case_dir": str(case_dir),
            "step_path": str(explicit_step),
            "interface_bodies": [
                _ifc_body("explicit_a", cx=0.0),
                _ifc_body("explicit_b", cx=1.0),
            ],
            "interface_specs": [
                {
                    "patch_name": "if_x",
                    "mode": "endcap",
                    "body": "explicit_a",
                    "axis": "+x",
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # input_summary should reference the EXPLICIT path, not the auto-discovered one
    unit_call = next(
        c for c in body["report"]["advisor_calls"]
        if c["advisor_name"] == "unit_detector"
    )
    assert "explicit.step" in unit_call["input_summary"]
    assert "discovered.step" not in unit_call["input_summary"]
    # A2-v2 sees 2 bodies (explicit), not 1 (disk)
    a2 = next(
        c for c in body["report"]["advisor_calls"]
        if c["advisor_name"] == "virtual_interface_detector"
    )
    assert "2 bodies" in a2["input_summary"]


def test_malformed_step_bbox_returns_400(client: TestClient) -> None:
    """Wrong-arity step_bbox surfaces a 400 instead of 500-ing the route."""
    resp = client.post(
        "/api/ai-review",
        json={"step_path": "/tmp/nope.step", "step_bbox": [0.0, 0.0, 1.0]},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["failing_check"] == "step_bbox_arity"


def test_malformed_interface_body_returns_400(client: TestClient) -> None:
    """Wire-form body missing required keys surfaces 400, not 500."""
    resp = client.post(
        "/api/ai-review",
        json={
            "interface_bodies": [{"name": "incomplete"}],  # missing centroid + faces
            "interface_specs": [
                {"patch_name": "x", "mode": "endcap", "body": "incomplete"}
            ],
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["failing_check"] in {
        "interface_body_fields",
        "interface_body_centroid_arity",
    }


# ---------- DEC-V62-A-sub-D10 (2026-05-14) ---------------------------------
# Two tests verify the wire-form bc_specs field dispatches the D10
# bc_type_name_validity_advisor, closing M-STACK-TRACK-3 §gap2 (case_006
# V29 evidence row: foam-extend-only BC names passing the stack silently).


def test_bc_specs_explicit_dispatches_d10_with_v29_evidence(
    client: TestClient,
) -> None:
    """DEC-V62-A-sub-D10: explicit bc_specs over the wire → D10 fires.

    Replays the case_006 V29 ground truth — the farfield_inlet bc block
    declares two foam-extend-only BC names; D10 must flag both as
    critical findings carrying ``V29`` in their evidence_v_rows.
    """
    resp = client.post(
        "/api/ai-review",
        json={
            "bc_specs": [
                {
                    "part_name": "farfield_inlet",
                    "fields": {
                        "U": "characteristicVelocityInletOutletVelocity",
                        "p": "characteristicPressureInletOutletPressure",
                        "T": "freestream",
                    },
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "bc_type_name_validity_advisor" in advisor_names
    d10 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "bc_type_name_validity_advisor"
    ]
    assert len(d10) == 2, d10  # U + p; T=freestream is valid
    for f in d10:
        assert f["severity"] == "critical"
        assert "V29" in f["evidence_v_rows"]


def test_parts_manifest_bc_blocks_auto_extract_to_d10(client: TestClient) -> None:
    """When parts_manifest carries bc: blocks, the stack auto-extracts
    bc_specs via extract_bc_specs_from_parts_manifest and D10 fires
    alongside A4 + A5 (the canonical case_006 path with no explicit
    bc_specs on the wire)."""
    resp = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": {
                "parts": [
                    {
                        "name": "farfield_inlet",
                        "role": "farfield",
                        "bc": {
                            "U": "characteristicVelocityInletOutletVelocity",
                            "p": "fixedValue",
                        },
                    }
                ]
            }
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "bc_type_name_validity_advisor" in advisor_names
    d10 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "bc_type_name_validity_advisor"
    ]
    assert len(d10) == 1
    assert d10[0]["severity"] == "critical"
    assert "V29" in d10[0]["evidence_v_rows"]


def test_bc_fork_foam_extend_tolerates_characteristic_family(
    client: TestClient,
) -> None:
    """bc_fork='foam-extend' must reclassify the characteristic* family
    as info (suppressed from findings), preserving the advisor's fork-
    aware contract over the wire."""
    resp = client.post(
        "/api/ai-review",
        json={
            "bc_specs": [
                {
                    "part_name": "farfield_inlet",
                    "fields": {
                        "U": "characteristicVelocityInletOutletVelocity",
                        "p": "characteristicPressureInletOutletPressure",
                    },
                }
            ],
            "bc_fork": "foam-extend",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    d10 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "bc_type_name_validity_advisor"
    ]
    assert d10 == []  # no findings on foam-extend fork


# ---------- DEC-V63-A-sub-D11 — stl_face_label_validator wire ----------
# Two tests covering: explicit stl_face_normals → D11 fires with V94 evidence;
# case_dir auto-discovery from <case_dir>/cad/face_normals.json.


def test_stl_face_normals_explicit_dispatches_d11_with_v94_evidence(
    client: TestClient,
) -> None:
    """DEC-V63-A-sub-D11: explicit stl_face_normals + manifest face_labels
    over the wire → D11 fires.

    Replays the case_011 V94 canonical evidence — manifest claims face
    labels hot_inlet / hot_outlet but the STL inventory only contains
    the parent body label (cq.exporters single-shell behaviour).
    """
    resp = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": {
                "parts": [
                    {
                        "name": "region_hot_fluid",
                        "role": "region_fluid",
                        "face_labels": ["hot_inlet", "hot_outlet"],
                    }
                ]
            },
            "stl_face_normals": {
                "region_hot_fluid": [[0.0, 1.0, 0.0]],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "stl_face_label_validator" in advisor_names
    d11 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "stl_face_label_validator"
    ]
    # Both declared labels orphan-fire (neither in stl_face_normals keys)
    assert len(d11) == 2
    orphan_labels = {f["raw"]["face_label"] for f in d11}
    assert orphan_labels == {"hot_inlet", "hot_outlet"}
    for f in d11:
        assert f["severity"] == "warning"
        assert "V94" in f["evidence_v_rows"]


def test_stl_face_normals_autodiscovered_from_case_dir(
    client: TestClient, tmp_path: Path
) -> None:
    """case_dir auto-discovery: when stl_face_normals is absent on the
    wire but ``<case_dir>/cad/face_normals.json`` exists, the route
    loads it and plumbs to D11."""
    case_dir = tmp_path / "case_d11_autodisc"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    cad = case_dir / "cad"
    cad.mkdir()
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "parts": [
                    {
                        "name": "region_cold_fluid",
                        "role": "region_fluid",
                        "face_labels": ["cold_inlet"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    # face_normals.json contains only the parent body label — cold_inlet
    # is absent so D11 will orphan-fire on it.
    (cad / "face_normals.json").write_text(
        json.dumps({"region_cold_fluid": [[0.0, -1.0, 0.0]]}),
        encoding="utf-8",
    )
    resp = client.post(
        "/api/ai-review",
        json={"case_dir": str(case_dir)},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "stl_face_label_validator" in advisor_names
    d11 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "stl_face_label_validator"
    ]
    assert len(d11) == 1
    assert d11[0]["raw"]["face_label"] == "cold_inlet"
    assert "V94" in d11[0]["evidence_v_rows"]


# ---------- DEC-V63-A-sub-M-D6-HTTP-WIRE — extra_body_advisor wire ----------
# Five tests covering: explicit stl_bbox_set → D6 fires with V55 evidence,
# auto-discover from <case_dir>/cad/stl_bbox_set.json, auto-discover from
# <case_dir>/manifest.json stl_bbox_set field, explicit overrides auto-
# discover, and backward-compat (interface_bodies-only payload does NOT
# accidentally dispatch D6 — the new field must be the sole D6 trigger).


def test_stl_bbox_set_routes_to_d6(client: TestClient) -> None:
    """DEC-V63-A-sub-M-D6-HTTP-WIRE: explicit stl_bbox_set + manifest →
    D6 fires with V55 evidence and the case_016 debris-cube finding.
    """
    resp = client.post(
        "/api/ai-review",
        json={
            "parts_manifest": {
                "parts": [
                    {
                        "name": "region_air",
                        "role": "region_air",
                        "bbox": [0.0, -200.0, -200.0, 600.0, 200.0, 200.0],
                    },
                ]
            },
            "stl_bbox_set": {
                "region_air": [0.0, -200.0, -200.0, 600.0, 200.0, 200.0],
                "debris_cube_10mm": [
                    315.0, 13.0, -84.0, 325.0, 23.0, -74.0,
                ],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "extra_body_advisor" in advisor_names
    d6 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "extra_body_advisor"
    ]
    debris = [f for f in d6 if f["location"] == "debris_cube_10mm"]
    assert len(debris) == 1
    assert debris[0]["code"] == "d6_unregistered_body"
    assert debris[0]["severity"] == "critical"
    assert "V55" in debris[0]["evidence_v_rows"]


def test_auto_discover_stl_bbox_set_from_case_dir(
    client: TestClient, tmp_path: Path
) -> None:
    """case_dir auto-discovery (path 1): when stl_bbox_set is absent on
    the wire but ``<case_dir>/cad/stl_bbox_set.json`` exists, the route
    loads it and plumbs to D6."""
    case_dir = tmp_path / "case_d6_autodisc_cad"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    cad = case_dir / "cad"
    cad.mkdir()
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "parts": [
                    {
                        "name": "region_air",
                        "role": "region_air",
                        "bbox": [0.0, 0.0, 0.0, 600.0, 200.0, 200.0],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (cad / "stl_bbox_set.json").write_text(
        json.dumps(
            {
                "region_air": [0.0, 0.0, 0.0, 600.0, 200.0, 200.0],
                "rogue_debris": [10.0, 10.0, 10.0, 20.0, 20.0, 20.0],
            }
        ),
        encoding="utf-8",
    )
    resp = client.post("/api/ai-review", json={"case_dir": str(case_dir)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "extra_body_advisor" in advisor_names
    d6 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "extra_body_advisor"
    ]
    assert any(
        f["code"] == "d6_unregistered_body" and f["location"] == "rogue_debris"
        for f in d6
    )


def test_auto_discover_stl_bbox_set_from_manifest_field(
    client: TestClient, tmp_path: Path
) -> None:
    """case_dir auto-discovery (path 2): manifest.json ``stl_bbox_set``
    field is consulted when the dedicated cad/stl_bbox_set.json is absent.
    """
    case_dir = tmp_path / "case_d6_autodisc_manifest"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump({"parts": [{"name": "shell", "role": "wall"}]}),
        encoding="utf-8",
    )
    (case_dir / "manifest.json").write_text(
        json.dumps(
            {
                "stl_bbox_set": {
                    "stowaway_inclusion": [
                        1.0, 1.0, 1.0, 2.0, 2.0, 2.0,
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    resp = client.post("/api/ai-review", json={"case_dir": str(case_dir)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    assert "extra_body_advisor" in advisor_names
    d6 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "extra_body_advisor"
    ]
    assert any(
        f["code"] == "d6_unregistered_body"
        and f["location"] == "stowaway_inclusion"
        for f in d6
    )


def test_explicit_stl_bbox_set_overrides_auto_discover(
    client: TestClient, tmp_path: Path
) -> None:
    """Auto-discover only fills *missing* slots — when both an explicit
    wire field and an on-disk file are present, the wire value wins."""
    case_dir = tmp_path / "case_d6_explicit_wins"
    inputs = case_dir / "inputs"
    inputs.mkdir(parents=True)
    cad = case_dir / "cad"
    cad.mkdir()
    (inputs / "parts_manifest.yaml").write_text(
        yaml.safe_dump({"parts": [{"name": "shell", "role": "wall"}]}),
        encoding="utf-8",
    )
    # On-disk file claims a body named "disk_only" — the explicit wire
    # payload omits it entirely and claims "wire_only" instead. After
    # dispatch, only "wire_only" should surface as unregistered.
    (cad / "stl_bbox_set.json").write_text(
        json.dumps({"disk_only": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]}),
        encoding="utf-8",
    )
    resp = client.post(
        "/api/ai-review",
        json={
            "case_dir": str(case_dir),
            "stl_bbox_set": {
                "wire_only": [5.0, 5.0, 5.0, 6.0, 6.0, 6.0],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    d6 = [
        f for f in body["report"]["findings"]
        if f["source_advisor"] == "extra_body_advisor"
    ]
    locations = {f["location"] for f in d6}
    assert "wire_only" in locations
    assert "disk_only" not in locations


def test_stl_bbox_set_none_falls_back_to_interface_bodies_routing(
    client: TestClient,
) -> None:
    """Backward-compat: an interface_bodies-only payload (no
    stl_bbox_set) must NOT accidentally dispatch D6. The wire field is
    the sole D6 trigger; A2-v2 keeps owning interface_bodies."""
    body_a = _ifc_body("body_a", cx=0.0)
    body_b = _ifc_body("body_b", cx=20.0)
    resp = client.post(
        "/api/ai-review",
        json={
            "interface_bodies": [body_a, body_b],
            "interface_specs": [
                {
                    "patch_name": "iface_ab",
                    "mode": "shared",
                    "body_a": "body_a",
                    "body_b": "body_b",
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    advisor_names = {c["advisor_name"] for c in body["report"]["advisor_calls"]}
    # A2-v2 fires (the legacy path) but D6 does not (no STL inventory).
    assert "virtual_interface_detector" in advisor_names
    assert "extra_body_advisor" not in advisor_names


