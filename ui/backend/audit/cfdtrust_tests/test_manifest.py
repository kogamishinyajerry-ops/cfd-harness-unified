"""Tests for case_manifest loading + validation."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from cfdtrust.manifest import (
    ManifestError,
    load_manifest,
    load_schema,
    validate_manifest,
)


def test_sample_manifest_loads(sample_case_dir: Path):
    data = load_manifest(sample_case_dir)
    assert isinstance(data, dict)
    assert data["case_id"] == "flat_plate_rans_sst"


def test_sample_manifest_validates(sample_case_dir: Path):
    data = validate_manifest(sample_case_dir)
    assert data["solver_backend"] in ("openfoam", "mocked")


def test_schema_loads():
    schema = load_schema()
    assert schema["title"] == "case_manifest"
    assert "case_id" in schema["required"]


def test_missing_case_dir_raises(tmp_path: Path):
    bogus = tmp_path / "no-such-case"
    with pytest.raises(ManifestError):
        load_manifest(bogus)


def test_missing_required_field_fails(sample_case_dir: Path, tmp_path: Path):
    # take the sample manifest, remove `bc_contract`, write into tmp, validate.
    manifest = load_manifest(sample_case_dir)
    broken = copy.deepcopy(manifest)
    broken.pop("bc_contract")
    bad_case = tmp_path / "broken_case"
    bad_case.mkdir()
    (bad_case / "case_manifest.yaml").write_text(yaml.safe_dump(broken))
    with pytest.raises(ManifestError) as exc:
        validate_manifest(bad_case)
    assert "bc_contract" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_invalid_solver_backend_fails(sample_case_dir: Path, tmp_path: Path):
    manifest = load_manifest(sample_case_dir)
    broken = copy.deepcopy(manifest)
    broken["solver_backend"] = "ansys_fluent"  # not in enum
    bad_case = tmp_path / "wrong_backend"
    bad_case.mkdir()
    (bad_case / "case_manifest.yaml").write_text(yaml.safe_dump(broken))
    with pytest.raises(ManifestError):
        validate_manifest(bad_case)
