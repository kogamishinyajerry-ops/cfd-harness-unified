"""Negative tests — schema must reject broken manifests."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from cfdtrust.manifest import ManifestError, load_manifest, validate_manifest


@pytest.fixture
def broken_case_dir(sample_case_dir: Path, tmp_path: Path):
    def _make(mutator):
        manifest = load_manifest(sample_case_dir)
        broken = copy.deepcopy(manifest)
        mutator(broken)
        case = tmp_path / "broken"
        case.mkdir()
        (case / "case_manifest.yaml").write_text(yaml.safe_dump(broken))
        return case
    return _make


def test_missing_geometry_contract_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m.pop("geometry_contract"))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_missing_mesh_contract_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m.pop("mesh_contract"))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_missing_bc_contract_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m.pop("bc_contract"))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_missing_qoi_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m.pop("qoi"))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_empty_required_patches_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m["geometry_contract"].__setitem__("required_patches", []))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_empty_turbulence_fields_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m["bc_contract"].__setitem__("turbulence_fields", []))
    with pytest.raises(ManifestError):
        validate_manifest(case)


def test_invalid_reference_status_fails(broken_case_dir):
    case = broken_case_dir(lambda m: m["reference_comparison"].__setitem__("status", "definitely_valid"))
    with pytest.raises(ManifestError):
        validate_manifest(case)
