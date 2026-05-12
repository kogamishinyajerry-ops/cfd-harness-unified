"""DEC-V61-154 (N5.3) · audit V2 manifest schema + builder + byte-repro tests.

Coverage:
  * Schema validators (SHA hex format, DEC-V61- prefix, schema_version literal)
  * Builder on empty case (case_state_sha computed even with all
    files missing)
  * Builder on partial case (changing files changes SHA)
  * Solver log SHA computed when log present, None when absent
  * figure_shas walk
  * Byte-reproducibility: same case state at different wall-clock
    times → identical canonical_manifest_bytes
  * V130 advisory-only: builder + canonical_manifest_bytes NOT in
    KNOWN_MUTATION_FUNCTIONS
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ui.backend.schemas.audit_v2_manifest import ProvenanceManifest
from ui.backend.services.audit_v2 import (
    build_provenance_manifest,
    canonical_manifest_bytes,
)


_VALID_SHA = "a" * 64


# ────────── Schema validators ──────────


def test_schema_version_must_be_v2():
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            schema_version="v1",  # type: ignore[arg-type]
            case_id="x",
            case_state_sha=_VALID_SHA,
            authored_at="2026-05-07T12:00:00Z",
        )


def test_case_state_sha_must_be_hex_64():
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha="too short",
            authored_at="2026-05-07T12:00:00Z",
        )
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha="g" * 64,  # invalid hex char
            authored_at="2026-05-07T12:00:00Z",
        )


def test_solver_log_sha_optional_but_validated_when_set():
    ProvenanceManifest(
        case_id="x",
        case_state_sha=_VALID_SHA,
        solver_log_sha=None,
        authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha=_VALID_SHA,
            solver_log_sha="bad",
            authored_at="2026-05-07T12:00:00Z",
        )


def test_figure_shas_each_must_be_valid_hex():
    ProvenanceManifest(
        case_id="x",
        case_state_sha=_VALID_SHA,
        figure_shas={"u_field.png": _VALID_SHA},
        authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha=_VALID_SHA,
            figure_shas={"u_field.png": "bad"},
            authored_at="2026-05-07T12:00:00Z",
        )


def test_dec_trail_must_have_dec_v61_prefix():
    ProvenanceManifest(
        case_id="x",
        case_state_sha=_VALID_SHA,
        dec_trail=["DEC-V61-152", "DEC-V61-154"],
        authored_at="2026-05-07T12:00:00Z",
    )
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha=_VALID_SHA,
            dec_trail=["random_id"],
            authored_at="2026-05-07T12:00:00Z",
        )


def test_extra_keys_forbidden():
    with pytest.raises(ValidationError):
        ProvenanceManifest(
            case_id="x",
            case_state_sha=_VALID_SHA,
            authored_at="2026-05-07T12:00:00Z",
            mystery="oops",
        )


# ────────── Builder ──────────


def test_builder_empty_case_produces_consistent_sha(tmp_path: Path):
    case_dir = tmp_path / "imported_empty"
    case_dir.mkdir()
    m1 = build_provenance_manifest(case_dir)
    m2 = build_provenance_manifest(case_dir)
    assert m1.case_state_sha == m2.case_state_sha
    assert m1.solver_log_sha is None
    assert m1.figure_shas == {}


def test_builder_changes_sha_when_file_added(tmp_path: Path):
    case_dir = tmp_path / "imported_change"
    case_dir.mkdir()
    sha_empty = build_provenance_manifest(case_dir).case_state_sha
    # Add a physics dict.
    (case_dir / "constant").mkdir()
    (case_dir / "constant" / "physicalProperties").write_text(
        "transportModel Newtonian;\n"
    )
    sha_with_phys = build_provenance_manifest(case_dir).case_state_sha
    assert sha_empty != sha_with_phys


def test_builder_solver_log_sha_when_log_present(tmp_path: Path):
    case_dir = tmp_path / "imported_with_log"
    case_dir.mkdir()
    log_content = b"Solving for Ux, Initial residual = 1e-5\n"
    (case_dir / "log.icoFoam").write_bytes(log_content)
    manifest = build_provenance_manifest(case_dir)
    expected = hashlib.sha256(log_content).hexdigest()
    assert manifest.solver_log_sha == expected


def test_builder_figure_shas_walks_postprocessing_dir(tmp_path: Path):
    case_dir = tmp_path / "imported_figs"
    figures = case_dir / "postProcessing" / "figures"
    figures.mkdir(parents=True)
    (figures / "u_centerline.png").write_bytes(b"PNG_BYTES")
    (figures / "p_field.svg").write_bytes(b"<svg></svg>")
    manifest = build_provenance_manifest(case_dir)
    assert "u_centerline.png" in manifest.figure_shas
    assert "p_field.svg" in manifest.figure_shas
    assert (
        manifest.figure_shas["u_centerline.png"]
        == hashlib.sha256(b"PNG_BYTES").hexdigest()
    )


def test_builder_figure_shas_skips_subdirs(tmp_path: Path):
    """Builder walks only top-level files in postProcessing/figures/.
    Subdirectories are ignored."""
    case_dir = tmp_path / "imported_subdir"
    figures = case_dir / "postProcessing" / "figures"
    (figures / "subdir").mkdir(parents=True)
    (figures / "fig.png").write_bytes(b"x")
    manifest = build_provenance_manifest(case_dir)
    assert "fig.png" in manifest.figure_shas
    assert "subdir" not in manifest.figure_shas


# ────────── Byte-reproducibility ──────────


def test_canonical_bytes_excludes_authored_at(tmp_path: Path):
    """Two manifests with different authored_at but same case state
    produce identical canonical_manifest_bytes."""
    case_dir = tmp_path / "imported_repro"
    case_dir.mkdir()
    (case_dir / "constant").mkdir()
    (case_dir / "constant" / "physicalProperties").write_text("test\n")

    m1 = build_provenance_manifest(case_dir)
    m2_same_state = m1.model_copy(
        update={"authored_at": "2099-12-31T23:59:59Z"}
    )
    assert canonical_manifest_bytes(m1) == canonical_manifest_bytes(m2_same_state)


def test_canonical_bytes_changes_when_case_state_changes(tmp_path: Path):
    case_dir = tmp_path / "imported_change"
    case_dir.mkdir()
    m1 = build_provenance_manifest(case_dir)
    (case_dir / "constant").mkdir()
    (case_dir / "constant" / "physicalProperties").write_text("test\n")
    m2 = build_provenance_manifest(case_dir)
    assert canonical_manifest_bytes(m1) != canonical_manifest_bytes(m2)


def test_canonical_bytes_is_sorted_and_compact():
    """Sorted keys + compact separators ensure stable bytes across
    Python dict-iteration order and pretty-printer changes."""
    m = ProvenanceManifest(
        case_id="x",
        case_state_sha=_VALID_SHA,
        figure_shas={"z.png": _VALID_SHA, "a.png": _VALID_SHA},
        authored_at="2026-05-07T12:00:00Z",
    )
    canon = canonical_manifest_bytes(m).decode("utf-8")
    # Sorted-keys: 'a.png' should come before 'z.png' in serialized form.
    a_pos = canon.find('"a.png"')
    z_pos = canon.find('"z.png"')
    assert 0 < a_pos < z_pos
    # Compact (no spaces after separators).
    assert ", " not in canon
    assert ": " not in canon


# ────────── V130 advisory-only contract ──────────


def test_audit_v2_module_not_in_known_mutation_functions():
    """N5.3 ships a manifest BUILDER (read-only walk) — the existing
    audit_package zip writer is the mutator. The new builder module
    must NOT be flagged as a mutator itself."""
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, symbol in KNOWN_MUTATION_FUNCTIONS:
        assert "audit_v2" not in module
        assert symbol != "build_provenance_manifest"
        assert symbol != "canonical_manifest_bytes"
