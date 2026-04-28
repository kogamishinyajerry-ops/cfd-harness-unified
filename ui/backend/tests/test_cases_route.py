"""Tests for the /api/cases/{case_id} route (M-PANELS Step 10 follow-up).

Covers the imported-draft fall-through added so M-PANELS Step 1's
`api.getCase(caseId)` resolves for engineer-driven imports — without it
the entire imported-case happy path 404s and Step 1 surfaces a red
error panel for every imported case (Pivot Charter Addendum 3 §3 path).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ui.backend.main import app
from ui.backend.services import case_drafts
from ui.backend.services import validation_report
from ui.backend.services.case_scaffold import scaffold_imported_case, template_clone
from ui.backend.services.geometry_ingest import (
    combine,
    detect_patches,
    load_stl_from_bytes,
    run_health_checks,
    solid_count,
)
from ui.backend.tests.conftest import box_stl


client = TestClient(app)


@pytest.fixture
def isolated_drafts(tmp_path: Path, monkeypatch):
    """Redirect DRAFTS_DIR + IMPORTED_DIR + REPO_ROOT-derived draft path to tmp."""
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    drafts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", drafts)
    # validation_report._load_imported_draft reads via REPO_ROOT, so
    # redirect REPO_ROOT to tmp_path's grandparent of the synthetic
    # ui/backend/user_drafts tree we'll set up.
    fake_repo = tmp_path / "repo_root"
    fake_drafts = fake_repo / "ui" / "backend" / "user_drafts"
    fake_drafts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(validation_report, "REPO_ROOT", fake_repo)
    return drafts, imported, fake_drafts


def test_get_case_returns_gold_case_unchanged() -> None:
    """Regression: whitelist cases keep their full CaseDetail (with gold_standard)."""
    r = client.get("/api/cases/lid_driven_cavity")
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == "lid_driven_cavity"
    assert body["name"] == "Lid-Driven Cavity"
    assert body["gold_standard"] is not None
    assert body["geometry_type"] == "SIMPLE_GRID"


def _seed_imported_draft(fake_drafts: Path, case_id: str) -> None:
    """Drop a minimal imported-draft YAML at the redirected REPO_ROOT location."""
    yaml_text = (
        f"id: {case_id}\n"
        "name: Imported · cylinder.stl\n"
        "flow_type: INTERNAL\n"
        "geometry_type: CUSTOM\n"
        "turbulence_model: laminar\n"
        "solver:\n"
        "  name: simpleFoam\n"
        "  family: incompressible\n"
    )
    (fake_drafts / f"{case_id}.yaml").write_text(yaml_text, encoding="utf-8")


def test_get_case_falls_through_to_imported_draft_via_http(isolated_drafts) -> None:
    """M-PANELS Step 1 fix · WIRE PATH: imported case_ids resolve through the route.

    Codex Round 3 WARNING: the original test reached load_case_detail()
    directly, which left the actual /api/cases/{id} HTTP path uncovered for
    imported cases. This test goes through the FastAPI TestClient.
    """
    _, _, fake_drafts = isolated_drafts
    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
    _seed_imported_draft(fake_drafts, case_id)

    r = client.get(f"/api/cases/{case_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == case_id
    assert body["name"] == "Imported · cylinder.stl"
    assert body["geometry_type"] == "CUSTOM"
    assert body["flow_type"] == "INTERNAL"
    assert body["turbulence_model"] == "laminar"
    assert body["solver"] == "simpleFoam"  # solver dict → solver.name
    assert body["gold_standard"] is None
    assert body["preconditions"] == []


def test_get_case_returns_404_for_unknown_id_via_http(isolated_drafts) -> None:
    """Cases in neither whitelist nor user_drafts still 404 through the route."""
    r = client.get("/api/cases/unknown_case_xyz")
    assert r.status_code == 404


def test_get_case_rejects_path_traversal(isolated_drafts) -> None:
    """Path-traversal attempts are rejected by the alphanum/underscore/hyphen guard."""
    # The starlette router strips dot-segments from URL paths so the route
    # never sees the raw traversal chars; reach load_case_detail directly to
    # verify the *guard* (the second line of defense) rejects unsafe ids.
    detail = validation_report.load_case_detail("../../../etc/passwd")
    assert detail is None
    # Also probe the HTTP layer for a syntactically-invalid id that survives
    # path normalization (a colon is route-safe but fails the allowlist).
    r = client.get("/api/cases/has:colons:and:slashes")
    assert r.status_code == 404


def test_audit_package_refuses_imported_case_ids(isolated_drafts, monkeypatch) -> None:
    """Codex Round 3 P1 regression guard: audit-package signing must NOT
    silently widen to imported cases now that load_case_detail() also
    resolves them. The route uses is_whitelisted() explicitly to keep its
    whitelist-only contract intact.
    """
    _, _, fake_drafts = isolated_drafts
    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
    _seed_imported_draft(fake_drafts, case_id)
    monkeypatch.setenv("CFD_HARNESS_HMAC_SECRET", "text:test-secret")

    # Imported case → 404 (whitelist gate, even though /api/cases/<id> serves it).
    r = client.post(f"/api/cases/{case_id}/runs/no_run/audit-package/build")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert "not in knowledge/whitelist.yaml" in detail


def test_is_whitelisted_predicate(isolated_drafts) -> None:
    """is_whitelisted() is True for whitelist cases, False for imported drafts."""
    _, _, fake_drafts = isolated_drafts
    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
    _seed_imported_draft(fake_drafts, case_id)

    assert validation_report.is_whitelisted("lid_driven_cavity") is True
    # Imported draft exists (load_case_detail resolves it) but it's NOT
    # whitelisted — this is the predicate audit_package.py needs.
    assert validation_report.load_case_detail(case_id) is not None
    assert validation_report.is_whitelisted(case_id) is False
    assert validation_report.is_whitelisted("totally_unknown") is False


def test_get_case_e2e_imported_via_scaffold(isolated_drafts) -> None:
    """End-to-end: scaffold a real imported case + verify the route resolves it."""
    _, _, fake_drafts = isolated_drafts
    loaded, errs = load_stl_from_bytes(box_stl())
    assert errs == []
    combined = combine(loaded)
    assert combined is not None
    patches, all_default = detect_patches(loaded)
    report = run_health_checks(
        combined=combined,
        solid_count=solid_count(loaded),
        patches=patches,
        all_default_faces=all_default,
    )
    result = scaffold_imported_case(
        report=report,
        combined=combined,
        loaded=loaded,
        origin_filename="cube.stl",
    )

    # The scaffold writes to template_clone.DRAFTS_DIR (redirected via
    # isolated_drafts), but validation_report._load_imported_draft reads
    # from validation_report.REPO_ROOT. Bridge by copying the draft into
    # the REPO_ROOT-relative drafts dir.
    src_yaml = isolated_drafts[0] / f"{result.case_id}.yaml"
    assert src_yaml.exists()
    (fake_drafts / f"{result.case_id}.yaml").write_text(
        src_yaml.read_text(encoding="utf-8"), encoding="utf-8"
    )

    r = client.get(f"/api/cases/{result.case_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["case_id"] == result.case_id
    assert body["name"].startswith("Imported")
    assert body["gold_standard"] is None
