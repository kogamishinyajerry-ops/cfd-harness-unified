"""Tests for Screen 6 audit-package route (Phase 5 · PR-5d · DEC-V61-018)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app


@pytest.fixture(autouse=True)
def _hmac_secret_env(monkeypatch):
    """Provide a dev-grade HMAC secret for all route tests."""
    monkeypatch.setenv("CFD_HARNESS_HMAC_SECRET", "text:route-test-dev-secret")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestBuildAuditPackage:
    """POST /api/cases/{id}/runs/{rid}/audit-package/build."""

    def test_build_returns_200_with_expected_shape(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        assert resp.status_code == 200
        body = resp.json()
        # Top-level keys
        for key in (
            "bundle_id", "manifest_id", "case_id", "run_id", "generated_at",
            "pdf_available", "downloads", "vv40_checklist", "signature_hex",
        ):
            assert key in body, f"missing key {key}"
        assert body["case_id"] == "duct_flow"
        assert body["run_id"] == "r1"
        assert body["manifest_id"] == "duct_flow-r1"

    def test_bundle_id_is_32_hex(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        bid = resp.json()["bundle_id"]
        assert len(bid) == 32
        assert all(c in "0123456789abcdef" for c in bid)

    def test_signature_is_64_hex(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        sig = resp.json()["signature_hex"]
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_downloads_structure(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        dl = resp.json()["downloads"]
        bid = resp.json()["bundle_id"]
        expected_base = f"/api/audit-packages/{bid}"
        assert dl["manifest_json"] == f"{expected_base}/manifest.json"
        assert dl["bundle_zip"] == f"{expected_base}/bundle.zip"
        assert dl["bundle_html"] == f"{expected_base}/bundle.html"
        assert dl["bundle_sig"] == f"{expected_base}/bundle.sig"
        # PDF may or may not be available on this host
        if resp.json()["pdf_available"]:
            assert dl["bundle_pdf"] == f"{expected_base}/bundle.pdf"
        else:
            assert dl["bundle_pdf"] is None

    def test_vv40_checklist_has_eight_areas(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        checklist = resp.json()["vv40_checklist"]
        assert len(checklist) == 8
        for item in checklist:
            assert "area" in item
            assert "description" in item
            assert "manifest_fields" in item
            assert isinstance(item["manifest_fields"], list)

    def test_unknown_case_id_still_builds_skeleton(self, client):
        """Unknown case → manifest.whitelist_entry=None but build succeeds."""
        resp = client.post("/api/cases/nonexistent_case/runs/r1/audit-package/build")
        assert resp.status_code == 200
        body = resp.json()
        assert body["manifest_id"] == "nonexistent_case-r1"

    def test_missing_hmac_secret_returns_500(self, client, monkeypatch):
        monkeypatch.delenv("CFD_HARNESS_HMAC_SECRET", raising=False)
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        assert resp.status_code == 500
        # Error message includes actionable install/rotation hint
        assert "openssl rand" in resp.json()["detail"]


class TestDownloadAuditPackageArtifacts:
    """GET /api/audit-packages/{bundle_id}/*"""

    def _build_and_get_bundle_id(self, client):
        resp = client.post("/api/cases/duct_flow/runs/r1/audit-package/build")
        return resp.json()["bundle_id"]

    def test_download_manifest_json(self, client):
        bid = self._build_and_get_bundle_id(client)
        resp = client.get(f"/api/audit-packages/{bid}/manifest.json")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        import json
        data = json.loads(resp.content)
        assert data["manifest_id"] == "duct_flow-r1"

    def test_download_zip_is_valid_zipfile(self, client, tmp_path):
        bid = self._build_and_get_bundle_id(client)
        resp = client.get(f"/api/audit-packages/{bid}/bundle.zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        # Write to disk + open with zipfile to verify structure
        zpath = tmp_path / "bundle.zip"
        zpath.write_bytes(resp.content)
        with zipfile.ZipFile(zpath) as zf:
            names = zf.namelist()
            assert "manifest.json" in names

    def test_download_html_is_utf8(self, client):
        bid = self._build_and_get_bundle_id(client)
        resp = client.get(f"/api/audit-packages/{bid}/bundle.html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "duct_flow-r1" in resp.text

    def test_download_sig_is_64_hex(self, client):
        bid = self._build_and_get_bundle_id(client)
        resp = client.get(f"/api/audit-packages/{bid}/bundle.sig")
        assert resp.status_code == 200
        # sidecar content: hex + newline
        sig_text = resp.text.strip()
        assert len(sig_text) == 64
        assert all(c in "0123456789abcdef" for c in sig_text)

    def test_unknown_bundle_id_returns_404(self, client):
        resp = client.get("/api/audit-packages/0000000000000000000000000000dead/bundle.zip")
        assert resp.status_code == 404

    def test_malformed_bundle_id_returns_404(self, client):
        """Non-hex / wrong-length → 404 (regex validated)."""
        for bad in ("short", "not-hex-" * 4, "../escape", ""):
            resp = client.get(f"/api/audit-packages/{bad}/bundle.zip")
            assert resp.status_code == 404, f"bad bundle_id {bad!r} leaked"

    def test_path_traversal_rejected(self, client):
        """Encoded ../ in bundle_id doesn't escape staging dir."""
        # FastAPI path params decode %2F; try a few attempts
        resp = client.get("/api/audit-packages/..%2F..%2Fetc/bundle.zip")
        assert resp.status_code == 404


class TestEndToEndSignAndVerify:
    """Operator-level flow: build → download → independently verify HMAC."""

    def test_downloaded_zip_and_sig_verify(self, client):
        """Build a bundle, download both zip + sig + manifest, run verify()."""
        import base64  # noqa: F401
        import json

        from src.audit_package import verify

        resp = client.post("/api/cases/duct_flow/runs/verify-test/audit-package/build")
        assert resp.status_code == 200
        body = resp.json()
        bid = body["bundle_id"]

        zip_bytes = client.get(f"/api/audit-packages/{bid}/bundle.zip").content
        manifest = json.loads(client.get(f"/api/audit-packages/{bid}/manifest.json").content)
        sig_text = client.get(f"/api/audit-packages/{bid}/bundle.sig").text.strip()

        # Use the same dev key from the fixture
        key = b"route-test-dev-secret"
        assert verify(manifest, zip_bytes, sig_text, key) is True

    def test_tampered_zip_fails_verify(self, client):
        import json
        from src.audit_package import verify

        resp = client.post("/api/cases/duct_flow/runs/tamper-test/audit-package/build")
        bid = resp.json()["bundle_id"]
        zip_bytes = client.get(f"/api/audit-packages/{bid}/bundle.zip").content
        manifest = json.loads(client.get(f"/api/audit-packages/{bid}/manifest.json").content)
        sig_text = client.get(f"/api/audit-packages/{bid}/bundle.sig").text.strip()

        # Flip one byte in zip → verify must fail
        tampered = bytes([zip_bytes[0] ^ 1]) + zip_bytes[1:]
        key = b"route-test-dev-secret"
        assert verify(manifest, tampered, sig_text, key) is False
