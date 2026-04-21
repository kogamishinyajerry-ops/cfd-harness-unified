"""Phase 7a — field artifacts route tests.

Runs OFFLINE against the committed fixture at
ui/backend/tests/fixtures/phase7a_sample_fields/ via
set_fields_root_for_testing. Must NOT call the solver.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services.field_artifacts import set_fields_root_for_testing

_FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "phase7a_sample_fields"
_RUN_ID = "lid_driven_cavity__audit_real_run"


@pytest.fixture(autouse=True)
def _point_fields_root_at_fixture():
    set_fields_root_for_testing(_FIXTURE_ROOT)
    yield
    set_fields_root_for_testing(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------- Manifest endpoint ----------

def test_get_manifest_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run_id"] == _RUN_ID
    assert body["case_id"] == "lid_driven_cavity"
    assert body["run_label"] == "audit_real_run"
    assert body["timestamp"] == "20260421T000000Z"


def test_manifest_three_artifacts(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    assert len(artifacts) >= 3, artifacts
    kinds = {a["kind"] for a in artifacts}
    assert {"vtk", "csv", "residual_log"}.issubset(kinds), kinds


def test_manifest_ordering(client: TestClient) -> None:
    """User ratification #6: sort by (kind_order, filename), vtk < csv < residual_log."""
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    assert r.status_code == 200
    artifacts = r.json()["artifacts"]
    order = {"vtk": 0, "csv": 1, "residual_log": 2}
    keys = [(order[a["kind"]], a["filename"]) for a in artifacts]
    assert keys == sorted(keys), keys


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_sha256_format(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert _HEX64.match(a["sha256"]), a


def test_manifest_sizes_positive(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    artifacts = r.json()["artifacts"]
    for a in artifacts:
        assert a["size_bytes"] > 0, a


def test_manifest_404_missing_run(client: TestClient) -> None:
    r = client.get("/api/runs/nonexistent_case__no_run/field-artifacts")
    assert r.status_code == 404, r.text


def test_manifest_400_or_404_malformed_run_id(client: TestClient) -> None:
    r = client.get("/api/runs/no_separator_here/field-artifacts")
    # parse_run_id raises 400; some FastAPI versions wrap as 422. Accept 400 or 404.
    assert r.status_code in (400, 404, 422), r.text


# ---------- Download endpoint ----------

def test_download_residuals_csv_200(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/residuals.csv")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    fixture = _FIXTURE_ROOT / "lid_driven_cavity" / "20260421T000000Z" / "residuals.csv"
    assert int(r.headers.get("content-length", "-1")) == fixture.stat().st_size


def test_download_vtk_200(client: TestClient) -> None:
    """VTK file lives at VTK/lid_driven_cavity_2000.vtk — subpath URL (Codex round 1 HIGH #1)."""
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/VTK/lid_driven_cavity_2000.vtk")
    assert r.status_code == 200, r.text


def test_download_404_traversal_filename(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 404, r.text


def test_download_404_traversal_runid_literal(client: TestClient) -> None:
    """Codex round 1 HIGH #2: traversal via run_id literal '..' must be rejected."""
    r = client.get("/api/runs/..__pwn/field-artifacts/residuals.csv")
    assert r.status_code in (400, 404), r.text


def test_download_404_traversal_runid_urlencoded(client: TestClient) -> None:
    """Codex round 1 HIGH #2: url-encoded '%2e%2e' traversal must also be rejected."""
    r = client.get("/api/runs/%2e%2e__pwn/field-artifacts/residuals.csv")
    assert r.status_code in (400, 404), r.text


def test_manifest_400_traversal_runid(client: TestClient) -> None:
    """Codex round 1 HIGH #2: manifest endpoint also guards run_id segments."""
    r = client.get("/api/runs/..__pwn/field-artifacts")
    assert r.status_code in (400, 404), r.text


def test_manifest_uses_subpath_when_collision(client: TestClient) -> None:
    """Codex round 1 HIGH #1: filename field uses POSIX relative path so
    subdir-nested files don't collide on basename. The fixture VTK lives in
    a VTK/ subdir; its filename in the manifest must include that subpath."""
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts")
    body = r.json()
    vtk_names = {a["filename"] for a in body["artifacts"] if a["kind"] == "vtk"}
    assert "VTK/lid_driven_cavity_2000.vtk" in vtk_names, vtk_names


def test_list_rejects_non_object_manifest(tmp_path: Path) -> None:
    """Codex round 3 non-blocking #1: manifest that is valid JSON but not an
    object (list/string/number) must fail closed to 404, not 500."""
    import json
    fields_root = tmp_path / "fields"
    case_dir = fields_root / "lid_driven_cavity"
    (case_dir / "runs").mkdir(parents=True)
    (case_dir / "20260421T000000Z").mkdir(parents=True)
    # Write a JSON array instead of an object.
    (case_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps(["not", "an", "object"]), encoding="utf-8",
    )
    set_fields_root_for_testing(fields_root)
    try:
        c = TestClient(app)
        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
        assert r.status_code == 404, r.text
    finally:
        set_fields_root_for_testing(_FIXTURE_ROOT)


def test_list_skips_out_of_dir_symlinks(tmp_path: Path) -> None:
    """Codex round 3 non-blocking #2: symlink inside artifact dir pointing
    OUTSIDE must be silently skipped, not 500. Fail closed."""
    import json, os
    fields_root = tmp_path / "fields"
    case_dir = fields_root / "lid_driven_cavity" / "20260421T000000Z"
    (fields_root / "lid_driven_cavity" / "runs").mkdir(parents=True)
    case_dir.mkdir(parents=True)
    # Legit file inside.
    (case_dir / "residuals.csv").write_text("Time,Ux\n1,0.5\n", encoding="utf-8")
    # Malicious symlink pointing outside the artifact dir.
    outside = tmp_path / "secret.csv"
    outside.write_text("secret\n", encoding="utf-8")
    os.symlink(outside, case_dir / "leaked.csv")
    (fields_root / "lid_driven_cavity" / "runs" / "audit_real_run.json").write_text(
        json.dumps({"timestamp": "20260421T000000Z",
                    "case_id": "lid_driven_cavity",
                    "run_label": "audit_real_run"}), encoding="utf-8",
    )
    set_fields_root_for_testing(fields_root)
    try:
        c = TestClient(app)
        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
        assert r.status_code == 200, r.text
        names = {a["filename"] for a in r.json()["artifacts"]}
        # legit file must appear; symlink to outside must be skipped.
        assert "residuals.csv" in names, names
        assert "leaked.csv" not in names, names
    finally:
        set_fields_root_for_testing(_FIXTURE_ROOT)


def test_list_rejects_malicious_manifest_timestamp(tmp_path: Path) -> None:
    """Codex round 2 HIGH: an adversary-written manifest with
    timestamp='../../outside' must NOT cause the LIST endpoint to enumerate
    files outside reports/phase5_fields/. Previously download path was
    guarded but list was not. Both now go through _resolve_artifact_dir."""
    import json
    # Build an isolated fields root with a malicious manifest.
    fields_root = tmp_path / "fields"
    case_dir = fields_root / "lid_driven_cavity"
    (case_dir / "runs").mkdir(parents=True)
    (case_dir / "20260421T000000Z").mkdir(parents=True)  # legit sibling
    # Also plant a file outside the case to prove containment matters.
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leaked.csv").write_text("secret\n", encoding="utf-8")
    (case_dir / "runs" / "audit_real_run.json").write_text(
        json.dumps({"timestamp": "../../outside", "case_id": "lid_driven_cavity",
                    "run_label": "audit_real_run"}),
        encoding="utf-8",
    )
    set_fields_root_for_testing(fields_root)
    try:
        c = TestClient(app)
        r = c.get(f"/api/runs/{_RUN_ID}/field-artifacts")
        # Must NOT return 200 with the leaked artifact — timestamp shape gate.
        assert r.status_code == 404, r.text
        # Download side also blocked.
        r2 = c.get(f"/api/runs/{_RUN_ID}/field-artifacts/leaked.csv")
        assert r2.status_code == 404, r2.text
    finally:
        set_fields_root_for_testing(_FIXTURE_ROOT)


def test_download_404_missing(client: TestClient) -> None:
    r = client.get(f"/api/runs/{_RUN_ID}/field-artifacts/does_not_exist.csv")
    assert r.status_code == 404, r.text
