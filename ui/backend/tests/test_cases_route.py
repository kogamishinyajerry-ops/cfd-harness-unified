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


def test_get_case_falls_through_to_imported_draft(isolated_drafts) -> None:
    """M-PANELS Step 1 fix: imported case_ids resolve via user_drafts/<id>.yaml."""
    _, _, fake_drafts = isolated_drafts
    case_id = "imported_2026-04-28T11-39-46Z_a4d3db45"
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

    detail = validation_report.load_case_detail(case_id)
    assert detail is not None
    assert detail.case_id == case_id
    assert detail.name == "Imported · cylinder.stl"
    assert detail.geometry_type == "CUSTOM"
    assert detail.flow_type == "INTERNAL"
    assert detail.turbulence_model == "laminar"
    # solver dict in YAML → str via solver.name
    assert detail.solver == "simpleFoam"
    # imported cases never carry gold standard / preconditions
    assert detail.gold_standard is None
    assert detail.preconditions == []
    assert detail.contract_status_narrative is None


def test_get_case_returns_404_for_unknown_id(isolated_drafts) -> None:
    """Cases that exist in neither whitelist nor user_drafts still 404."""
    detail = validation_report.load_case_detail("unknown_case_xyz")
    assert detail is None


def test_get_case_rejects_path_traversal(isolated_drafts) -> None:
    """Path-traversal attempts are rejected by the alphanum/underscore/hyphen guard."""
    # Whitelist won't match; draft-fall-through guard rejects unsafe chars.
    detail = validation_report.load_case_detail("../../../etc/passwd")
    assert detail is None


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

    detail = validation_report.load_case_detail(result.case_id)
    assert detail is not None
    assert detail.case_id == result.case_id
    assert detail.name.startswith("Imported")
    assert detail.gold_standard is None
