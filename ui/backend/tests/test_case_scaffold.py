"""Unit tests for ``ui.backend.services.case_scaffold`` (M5.0)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from ui.backend.services import case_drafts
from ui.backend.services.case_scaffold import (
    allocate_imported_case_id,
    create_imported_case_dir,
    scaffold_imported_case,
    template_clone,
)
from ui.backend.services.case_scaffold.template_clone import _safe_origin_filename
from ui.backend.services.geometry_ingest import (
    IngestReport,
    combine,
    detect_patches,
    load_stl_from_bytes,
    run_health_checks,
    solid_count,
)
from ui.backend.tests.conftest import box_stl


@pytest.fixture
def isolated_drafts(tmp_path: Path, monkeypatch):
    """Redirect DRAFTS_DIR + IMPORTED_DIR to tmp_path so tests don't pollute repo."""
    drafts = tmp_path / "user_drafts"
    imported = drafts / "imported"
    monkeypatch.setattr(template_clone, "DRAFTS_DIR", drafts)
    monkeypatch.setattr(template_clone, "IMPORTED_DIR", imported)
    monkeypatch.setattr(case_drafts, "DRAFTS_DIR", drafts)
    return drafts, imported


@pytest.fixture
def clean_report():
    """A passing-ingest IngestReport + the combined Trimesh, from a small cube STL."""
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
    assert report.errors == []
    return report, combined


# ───────── allocator + filename safety ─────────

def test_allocator_with_injection_is_deterministic():
    fixed = datetime(2026, 4, 27, 15, 30, 45, tzinfo=timezone.utc)
    cid = allocate_imported_case_id(now=fixed, rand_hex="abcd1234")
    assert cid == "imported_2026-04-27T15-30-45Z_abcd1234"


def test_allocator_default_produces_safe_string():
    cid = allocate_imported_case_id()
    assert cid.startswith("imported_")
    # safe charset matches case_drafts._draft_path traversal guard
    assert all(c.isalnum() or c in "_-" for c in cid)


def test_safe_origin_filename_strips_path_components():
    assert _safe_origin_filename("/etc/passwd") == "passwd.stl"
    assert _safe_origin_filename("../../../evil.stl") == "evil.stl"
    assert _safe_origin_filename("model.STL") == "model.STL"


def test_safe_origin_filename_appends_stl_when_missing():
    assert _safe_origin_filename("model").endswith(".stl")


def test_safe_origin_filename_replaces_unsafe_chars():
    assert _safe_origin_filename("my model with spaces.stl") == "my_model_with_spaces.stl"


# ───────── directory creation ─────────

def test_create_imported_case_dir_creates_subdirs(isolated_drafts):
    _, imported = isolated_drafts
    cid = "imported_2026-04-27T00-00-00Z_aaaaaaaa"
    root = create_imported_case_dir(cid)
    assert root == imported / cid
    assert (root / "triSurface").is_dir()
    assert (root / "system").is_dir()


def test_create_imported_case_dir_is_idempotent(isolated_drafts):
    cid = "imported_2026-04-27T00-00-00Z_bbbbbbbb"
    create_imported_case_dir(cid)
    create_imported_case_dir(cid)  # second call must not raise


def test_create_imported_case_dir_rejects_unsafe_id(isolated_drafts):
    with pytest.raises(ValueError, match="unsafe case_id"):
        create_imported_case_dir("../traversal_attempt")


# ───────── full scaffold ─────────

def test_scaffold_writes_all_expected_files(isolated_drafts, clean_report):
    drafts, imported = isolated_drafts
    report, combined = clean_report
    fixed = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)

    result = scaffold_imported_case(
        report=report,
        combined=combined,
        origin_filename="my_geometry.stl",
        now=fixed,
        case_id="imported_2026-04-27T12-00-00Z_deadbeef",
    )

    assert result.case_id == "imported_2026-04-27T12-00-00Z_deadbeef"
    assert result.imported_case_dir == imported / result.case_id
    assert result.triSurface_path.exists()
    assert result.triSurface_path.name == "my_geometry.stl"
    assert result.shm_stub_path.exists()
    assert result.shm_stub_path.name == "snappyHexMeshDict.stub"
    assert result.manifest_path.exists()
    assert result.manifest_path.name == "case_manifest.yaml"
    assert result.case_yaml_path.exists()
    assert result.case_yaml_path.parent == drafts


def test_scaffold_manifest_schema_complete(isolated_drafts, clean_report):
    drafts, imported = isolated_drafts
    report, combined = clean_report
    result = scaffold_imported_case(
        report=report,
        combined=combined,
        origin_filename="cube.stl",
    )
    manifest = yaml.safe_load(result.manifest_path.read_text())

    # All M5.0 manifest fields must be present.
    for key in (
        "source",
        "source_origin",
        "case_id",
        "origin_filename",
        "ingest_report_summary",
        "created_at",
        "solver_version_compat",
    ):
        assert key in manifest, f"manifest missing required field: {key}"

    assert manifest["source"] == "imported"
    assert manifest["source_origin"] == "imported_user"
    assert manifest["origin_filename"] == "cube.stl"
    summary = manifest["ingest_report_summary"]
    for sub in ("is_watertight", "bbox_min", "bbox_max", "unit_guess", "patches"):
        assert sub in summary


def test_scaffold_editor_yaml_lints_clean(isolated_drafts, clean_report):
    drafts, imported = isolated_drafts
    report, combined = clean_report
    result = scaffold_imported_case(
        report=report,
        combined=combined,
        origin_filename="ldc_box.stl",
    )
    yaml_text = result.case_yaml_path.read_text()

    # 1. Must lint without parse errors (warnings are OK per case_drafts contract).
    lint = case_drafts.lint_case_yaml(yaml_text)
    assert lint.ok, f"editor case YAML failed to lint: {lint.errors}"

    # 2. The M5.0 schema-additive fields must be present at top level.
    parsed = yaml.safe_load(yaml_text)
    assert parsed["source_origin"] == "imported_user"
    assert parsed["source"] == "imported"
    assert parsed["origin_filename"] == "ldc_box.stl"
    assert "imported_case_dir" in parsed

    # 3. Recommended workbench fields are populated so lint warnings are minimal.
    for key in ("id", "name", "flow_type", "geometry_type", "turbulence_model"):
        assert key in parsed


def test_scaffold_rejects_report_with_errors(isolated_drafts):
    bad = IngestReport.from_parse_failure(["something broke"])
    with pytest.raises(ValueError, match="non-empty report.errors"):
        scaffold_imported_case(
            report=bad,
            combined=None,  # type: ignore[arg-type]
            origin_filename="x.stl",
        )
