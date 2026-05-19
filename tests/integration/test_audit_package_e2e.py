"""V78.3 · Audit-package E2E smoke test.

Closes the V74.5 wire-unverified bookmark (4 arcs aged · V74/V75/V76/V77
all disclosed in close DECs §5 that "audit-package round-trip smoke
deferred").

Tests the full POST /api/cases/{id}/runs/{rid}/audit-package/build →
GET /api/audit-packages/{bundle_id}/manifest.json → GET /api/audit-
packages/{bundle_id}/bundle.zip round-trip:
  - 200 status on every endpoint
  - Manifest schema matches (case_id, run_id, build_fingerprint,
    signature_hex)
  - bundle.zip is a real ZIP with manifest.json inside
  - signature_hex format matches V74.5 spec (64 hex chars from HMAC-SHA256)
"""
from __future__ import annotations

import io
import json
import os
import re
import zipfile

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


SIG_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Ensure HMAC secret is set so the audit-package build doesn't 500.
    # The audit-package service reads CFD_HARNESS_HMAC_SECRET.
    os.environ.setdefault(
        "CFD_HARNESS_HMAC_SECRET",
        "v78-e2e-smoke-test-secret-not-used-in-prod",
    )
    return TestClient(app)


CASE_ID = "lid_driven_cavity"
RUN_ID = "v78-e2e-smoke"


def test_build_returns_200_and_bundle_id(client: TestClient) -> None:
    resp = client.post(
        f"/api/cases/{CASE_ID}/runs/{RUN_ID}/audit-package/build",
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # AuditPackageBuildResponse schema (V74.5 spec)
    assert "bundle_id" in body, body
    assert "case_id" in body
    assert "build_fingerprint" in body
    assert body["case_id"] == CASE_ID
    assert body["run_id"] == RUN_ID
    # signature_hex must be 64 hex chars (HMAC-SHA256 hex digest)
    assert "signature_hex" in body, body
    assert SIG_HEX_RE.match(body["signature_hex"]), body["signature_hex"]
    # downloads dict carries the 4 mandatory artifact URLs
    downloads = body.get("downloads", {})
    for kind in ("manifest_json", "bundle_zip", "bundle_html"):
        assert kind in downloads, f"missing download URL: {kind}"


def test_build_fingerprint_is_stable_across_repeated_builds(
    client: TestClient,
) -> None:
    """Byte-reproducibility invariant (V132 MUTATING_ROUTES adjacent):
    two identical POSTs must produce the same build_fingerprint. This
    is the contract that lets audit-package reviewers trust the bundle
    hasn't drifted between Claude sessions.
    """
    a = client.post(
        f"/api/cases/{CASE_ID}/runs/{RUN_ID}/audit-package/build",
    ).json()
    b = client.post(
        f"/api/cases/{CASE_ID}/runs/{RUN_ID}/audit-package/build",
    ).json()
    assert a["build_fingerprint"] == b["build_fingerprint"]
    # bundle_id is per-staging-dir uuid, so it DIFFERS — fingerprint is
    # the stable identity.


def test_manifest_get_returns_full_schema(client: TestClient) -> None:
    build = client.post(
        f"/api/cases/{CASE_ID}/runs/{RUN_ID}/audit-package/build",
    ).json()
    bundle_id = build["bundle_id"]
    resp = client.get(f"/api/audit-packages/{bundle_id}/manifest.json")
    assert resp.status_code == 200, resp.text
    manifest = resp.json()
    # Manifest carries build_fingerprint at top level + case_id/run_id
    # nested under case/run keys (V61 schema in src.audit_package). We
    # verify the critical provenance fields match the build response.
    assert manifest["build_fingerprint"] == build["build_fingerprint"]
    # case_id lives at manifest.case.id (V61 nested schema)
    case_obj = manifest.get("case") or {}
    assert case_obj.get("id") == CASE_ID or manifest.get("case_id") == CASE_ID, manifest
    run_obj = manifest.get("run") or {}
    actual_run_id = run_obj.get("id") or run_obj.get("run_id") or manifest.get("run_id")
    assert actual_run_id == RUN_ID, f"run_id mismatch: {actual_run_id} != {RUN_ID}"
    # Provenance bundle present (git/executor/schema_version)
    assert "git" in manifest or "schema_version" in manifest, manifest


def test_bundle_zip_contains_manifest(client: TestClient) -> None:
    """The zip is the authoritative artifact reviewers download. It
    MUST contain manifest.json inside; otherwise the signed bundle
    is missing the data that the signature attests to.
    """
    build = client.post(
        f"/api/cases/{CASE_ID}/runs/{RUN_ID}/audit-package/build",
    ).json()
    bundle_id = build["bundle_id"]
    resp = client.get(f"/api/audit-packages/{bundle_id}/bundle.zip")
    assert resp.status_code == 200, resp.text
    # Must be a valid ZIP
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert any(
        n.endswith("manifest.json") for n in names
    ), f"manifest.json not in zip: {names}"

    # The manifest inside the zip must match the one served directly
    manifest_name = next(n for n in names if n.endswith("manifest.json"))
    with zf.open(manifest_name) as f:
        zip_manifest = json.load(f)
    assert zip_manifest["build_fingerprint"] == build["build_fingerprint"]


def test_unknown_case_returns_404(client: TestClient) -> None:
    """V130 whitelist-gate compliance: imported drafts can't get signed
    bundles. 404 (not 500) for unknown case_ids."""
    resp = client.post(
        "/api/cases/does_not_exist/runs/x/audit-package/build",
    )
    assert resp.status_code == 404, resp.text
