"""DEC-V61-075 P2-T2.3 · has_docker_openfoam_reference_run tests.

Covers the §6.3 reference-run resolver per the brief's acceptance:
  (a) no reference run → False
  (b) reference run present → True
  (c) malformed manifest → no exception (silent skip)

Plus boundary tests for legacy-id aliasing, mode filtering, verdict
filtering, missing executor section (pre-P2 zip forward-compat), and
the scan cap.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from src.audit_package.reference_lookup import has_docker_openfoam_reference_run


def _write_zip_with_manifest(
    target_dir: Path,
    name: str,
    manifest: dict,
) -> Path:
    """Write a signed-zip-shaped bundle containing manifest.json."""
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / f"{name}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def _docker_openfoam_manifest(
    case_id: str = "lid_driven_cavity",
    legacy_ids: tuple[str, ...] = (),
    verdict: str = "PASS",
) -> dict:
    """Minimal manifest matching the build_manifest schema slice the
    resolver consumes."""
    return {
        "schema_version": 1,
        "manifest_id": f"{case_id}-run-001",
        "case": {
            "id": case_id,
            "legacy_ids": list(legacy_ids),
        },
        "executor": {
            "mode": "docker_openfoam",
            "version": "0.2",
            "contract_hash": "deadbeef" * 8,
        },
        "measurement": {
            "comparator_verdict": verdict,
        },
    }


# ---------------------------------------------------------------------------
# Acceptance: (a) (b) (c) per brief
# ---------------------------------------------------------------------------

def test_no_reference_run_returns_false_for_empty_root(tmp_path):
    """(a) Empty audit_package_root → False (no matching manifests)."""
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


def test_no_reference_run_returns_false_when_root_does_not_exist(tmp_path):
    """audit_package_root that doesn't exist on disk → False, no raise.
    Defensive: callers may pass a path that hasn't been created yet."""
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity",
        audit_package_root=tmp_path / "nonexistent",
    ) is False


def test_matching_manifest_returns_true(tmp_path):
    """(b) docker_openfoam manifest for the case → True."""
    _write_zip_with_manifest(
        tmp_path,
        "ldc_run_001",
        _docker_openfoam_manifest(case_id="lid_driven_cavity"),
    )
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is True


def test_malformed_manifest_does_not_raise(tmp_path):
    """(c) Corrupt zip / non-JSON manifest → silent skip, returns False."""
    # Truncated zip
    (tmp_path / "broken.zip").write_bytes(b"\x50\x4b\x03\x04 truncated")
    # Valid zip with non-JSON manifest body
    bad_payload = io.BytesIO()
    with zipfile.ZipFile(bad_payload, "w") as zf:
        zf.writestr("manifest.json", "this is not json {[")
    (tmp_path / "bad_json.zip").write_bytes(bad_payload.getvalue())
    # Plain manifest.json with non-UTF-8 garbage
    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe\x00garbage")

    # Must not raise + return False (no successful match)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


# ---------------------------------------------------------------------------
# Mode filtering
# ---------------------------------------------------------------------------

def test_mock_mode_manifest_returns_false(tmp_path):
    """A mock-mode manifest must NOT count as a docker_openfoam reference."""
    manifest = _docker_openfoam_manifest()
    manifest["executor"]["mode"] = "mock"
    _write_zip_with_manifest(tmp_path, "mock_run", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


def test_hybrid_init_mode_manifest_returns_false(tmp_path):
    """A hybrid_init manifest cannot anchor itself as its own reference."""
    manifest = _docker_openfoam_manifest()
    manifest["executor"]["mode"] = "hybrid_init"
    _write_zip_with_manifest(tmp_path, "hybrid_run", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


def test_missing_executor_section_treated_as_docker_openfoam(tmp_path):
    """Pre-P2 manifests had no executor section. Per
    EXECUTOR_ABSTRACTION §3 forward-compat, treat as docker_openfoam."""
    manifest = _docker_openfoam_manifest()
    del manifest["executor"]
    _write_zip_with_manifest(tmp_path, "pre_p2_run", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is True


# ---------------------------------------------------------------------------
# Case-id matching
# ---------------------------------------------------------------------------

def test_legacy_id_alias_matches(tmp_path):
    """A manifest with the case_id in legacy_ids resolves (rename history)."""
    manifest = _docker_openfoam_manifest(
        case_id="duct_flow",
        legacy_ids=("fully_developed_pipe",),
    )
    _write_zip_with_manifest(tmp_path, "renamed", manifest)
    assert has_docker_openfoam_reference_run(
        "fully_developed_pipe", audit_package_root=tmp_path
    ) is True


def test_different_case_id_does_not_match(tmp_path):
    """A docker_openfoam manifest for a different case must NOT resolve."""
    _write_zip_with_manifest(
        tmp_path,
        "other_case",
        _docker_openfoam_manifest(case_id="other_case_id"),
    )
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


# ---------------------------------------------------------------------------
# Verdict filtering
# ---------------------------------------------------------------------------

def test_failed_verdict_excludes_manifest(tmp_path):
    """A FAIL verdict cannot anchor §5.1 byte-equality invariant."""
    manifest = _docker_openfoam_manifest(verdict="FAIL")
    _write_zip_with_manifest(tmp_path, "failed_run", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


def test_hazard_verdict_excludes_manifest(tmp_path):
    """A HAZARD verdict (attestor concerns) excludes the reference."""
    manifest = _docker_openfoam_manifest(verdict="HAZARD")
    _write_zip_with_manifest(tmp_path, "hazard_run", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is False


def test_pre_verdict_manifest_is_permissive(tmp_path):
    """A manifest without comparator_verdict (attestation-only bundle)
    still anchors §5.1 — the byte-equality contract is on
    canonical_artifacts, not on a downstream verdict."""
    manifest = _docker_openfoam_manifest()
    del manifest["measurement"]["comparator_verdict"]
    _write_zip_with_manifest(tmp_path, "pre_verdict", manifest)
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is True


# ---------------------------------------------------------------------------
# Plain manifest.json (unzipped) support
# ---------------------------------------------------------------------------

def test_plain_manifest_json_also_resolves(tmp_path):
    """When operators export a manifest.json without zipping (dev
    inspection workflow), the resolver still finds it."""
    case_dir = tmp_path / "lid_driven_cavity_run_002"
    case_dir.mkdir()
    (case_dir / "manifest.json").write_text(
        json.dumps(_docker_openfoam_manifest())
    )
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is True


# ---------------------------------------------------------------------------
# Mixed-corpus scenario: True wins as soon as any match found
# ---------------------------------------------------------------------------

def test_mixed_corpus_first_success_wins(tmp_path):
    """In a corpus with mock + failed + successful docker_openfoam,
    the resolver returns True (any successful match suffices)."""
    _write_zip_with_manifest(
        tmp_path / "subdir_a",
        "mock_run",
        {**_docker_openfoam_manifest(), "executor": {
            "mode": "mock", "version": "0.2", "contract_hash": "x" * 64,
        }},
    )
    _write_zip_with_manifest(
        tmp_path / "subdir_b",
        "failed_run",
        _docker_openfoam_manifest(verdict="FAIL"),
    )
    _write_zip_with_manifest(
        tmp_path / "subdir_c",
        "good_run",
        _docker_openfoam_manifest(verdict="PASS"),
    )
    assert has_docker_openfoam_reference_run(
        "lid_driven_cavity", audit_package_root=tmp_path
    ) is True
