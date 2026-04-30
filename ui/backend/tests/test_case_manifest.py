"""DEC-V61-102 Phase 1.1 · case_manifest schema/io/overrides tests."""
from __future__ import annotations

import yaml

from ui.backend.services.case_manifest import (
    CaseManifest,
    ManifestNotFoundError,
    ManifestParseError,
    compute_etag,
    is_user_override,
    mark_ai_authored,
    mark_user_override,
    read_case_manifest,
    reset_to_ai_default,
    write_case_manifest,
)


# ---------------------------------------------------------------------------
# Schema migration v1 → v2
# ---------------------------------------------------------------------------


def test_v1_manifest_migrates_to_v2_lossless(tmp_path):
    """A v1 manifest (DEC-V61-093 import-time-only shape, no
    ``schema_version`` key) reads as v2 with all legacy fields preserved.
    """
    v1_payload = {
        "source": "imported",
        "source_origin": "imported_user",
        "case_id": "imported_2026-04-30T08-14-40Z_2c29e9fd",
        "origin_filename": "cylinder.stl",
        "ingest_report_summary": {
            "is_watertight": True,
            "bbox_min": [0, 0, 0],
            "bbox_max": [1, 1, 1],
            "bbox_extent": [1, 1, 1],
            "unit_guess": "m",
            "solid_count": 1,
            "face_count": 128,
            "is_single_shell": True,
            "patches": [{"name": "defaultFaces", "face_count": 128}],
            "all_default_faces": True,
            "warnings": [],
        },
        "created_at": "2026-04-30T08:14:40+00:00",
        "solver_version_compat": "openfoam-v2412",
    }
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump(v1_payload, sort_keys=False), encoding="utf-8"
    )

    manifest = read_case_manifest(tmp_path)

    # All v1 fields preserved verbatim.
    assert manifest.source == "imported"
    assert manifest.source_origin == "imported_user"
    assert manifest.case_id == v1_payload["case_id"]
    assert manifest.origin_filename == "cylinder.stl"
    assert manifest.ingest_report_summary["face_count"] == 128
    assert manifest.solver_version_compat == "openfoam-v2412"
    # New v2 sections initialized empty.
    assert manifest.schema_version == 2
    assert manifest.physics.solver is None
    assert manifest.bc.patches == {}
    assert manifest.numerics.fv_schemes_overrides == {}
    assert manifest.overrides.raw_dict_files == {}
    assert manifest.history == []


def test_v2_manifest_roundtrips_byte_stable(tmp_path):
    """Write v2 → read v2 → produces identical model after round-trip."""
    manifest = CaseManifest(
        case_id="test_case",
        physics={"solver": "pimpleFoam", "turbulence_model": "kOmegaSST",
                 "end_time": 5.0, "delta_t": 0.005,
                 "source": {"solver": "ai", "turbulence_model": "user"}},
    )
    manifest.bc.patches["inlet"] = {"patch_type": "fixedValue",
                                     "fields": {"U": [1, 0, 0]},
                                     "source": {"patch_type": "ai", "fields": "ai"}}

    write_case_manifest(tmp_path, manifest)
    reloaded = read_case_manifest(tmp_path)

    assert reloaded.schema_version == 2
    assert reloaded.physics.solver == "pimpleFoam"
    assert reloaded.physics.turbulence_model == "kOmegaSST"
    assert reloaded.physics.source.get("turbulence_model") == "user"
    assert "inlet" in reloaded.bc.patches
    assert reloaded.bc.patches["inlet"].patch_type == "fixedValue"


def test_explicit_v2_schema_version_loads_clean(tmp_path):
    """A manifest already at schema_version=2 doesn't re-trigger migration
    (i.e. its existing structured sections are preserved as-is)."""
    v2_payload = {
        "schema_version": 2,
        "case_id": "fresh",
        "physics": {"solver": "icoFoam", "turbulence_model": "laminar",
                    "source": {"solver": "ai"}},
        "bc": {"patches": {}},
        "numerics": {},
        "overrides": {"raw_dict_files": {
            "system/controlDict": {"source": "user", "edited_at": "2026-04-30T10:00:00+00:00",
                                    "etag": "abc123"}
        }},
        "history": [],
    }
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump(v2_payload, sort_keys=False), encoding="utf-8"
    )

    manifest = read_case_manifest(tmp_path)
    assert manifest.physics.solver == "icoFoam"
    entry = manifest.overrides.raw_dict_files["system/controlDict"]
    assert entry.source == "user"
    assert entry.etag == "abc123"


def test_unknown_schema_version_rejected(tmp_path):
    """Unknown schema_version (e.g. v3 from a future build) fails loud."""
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump({"schema_version": 3, "case_id": "x"}), encoding="utf-8"
    )
    try:
        read_case_manifest(tmp_path)
    except ManifestParseError as exc:
        assert "schema_version=3" in str(exc)
    else:
        assert False, "expected ManifestParseError"


def test_missing_manifest_raises_not_found(tmp_path):
    try:
        read_case_manifest(tmp_path)
    except ManifestNotFoundError:
        pass
    else:
        assert False, "expected ManifestNotFoundError"


# ---------------------------------------------------------------------------
# Override helpers
# ---------------------------------------------------------------------------


def test_mark_ai_authored_creates_entries(tmp_path):
    """First setup_*_bc call records the dicts as AI-authored."""
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump({"case_id": "x", "schema_version": 2}), encoding="utf-8"
    )

    updated = mark_ai_authored(
        tmp_path,
        relative_paths=["system/controlDict", "system/fvSchemes"],
        action="setup_ldc_bc",
    )

    assert updated.overrides.raw_dict_files["system/controlDict"].source == "ai"
    assert updated.overrides.raw_dict_files["system/fvSchemes"].source == "ai"
    assert len(updated.history) == 1
    assert updated.history[0].action == "setup_ldc_bc"
    assert updated.history[0].source == "ai"


def test_mark_ai_authored_preserves_user_override(tmp_path):
    """Critical invariant: AI re-author MUST NOT overwrite a user override.
    The bc_setup caller is responsible for skipping the actual file write
    when the manifest already records source=user; this helper only
    guarantees the manifest itself isn't clobbered.
    """
    initial = CaseManifest(case_id="x")
    initial.overrides.raw_dict_files["system/controlDict"] = {
        "source": "user", "edited_at": "2026-04-30T09:00:00+00:00", "etag": "deadbeef"
    }
    write_case_manifest(tmp_path, initial)

    updated = mark_ai_authored(
        tmp_path,
        relative_paths=["system/controlDict", "system/fvSchemes"],
        action="setup_ldc_bc",
    )

    # controlDict stays user-owned.
    assert updated.overrides.raw_dict_files["system/controlDict"].source == "user"
    assert updated.overrides.raw_dict_files["system/controlDict"].etag == "deadbeef"
    # fvSchemes (no prior entry) becomes ai-owned.
    assert updated.overrides.raw_dict_files["system/fvSchemes"].source == "ai"


def test_mark_user_override_records_etag(tmp_path):
    """User-edit path records the new etag for race protection."""
    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump({"case_id": "x", "schema_version": 2}), encoding="utf-8"
    )

    new_content = b"FoamFile { class dictionary; }\nendTime 10;\n"
    updated = mark_user_override(
        tmp_path,
        relative_path="system/controlDict",
        new_content=new_content,
    )

    entry = updated.overrides.raw_dict_files["system/controlDict"]
    assert entry.source == "user"
    assert entry.etag == compute_etag(new_content)
    assert entry.edited_at is not None
    assert updated.history[-1].action == "edit_dict"
    assert updated.history[-1].source == "user"


def test_reset_to_ai_default_flips_source(tmp_path):
    """Reset converts user-owned back to ai-owned (the actual file
    regeneration is the caller's job)."""
    initial = CaseManifest(case_id="x")
    initial.overrides.raw_dict_files["system/controlDict"] = {
        "source": "user", "edited_at": "2026-04-30T09:00:00+00:00", "etag": "deadbeef"
    }
    write_case_manifest(tmp_path, initial)

    updated = reset_to_ai_default(tmp_path, relative_path="system/controlDict")
    entry = updated.overrides.raw_dict_files["system/controlDict"]
    assert entry.source == "ai"
    assert entry.edited_at is None


def test_is_user_override_predicate(tmp_path):
    """Predicate returns False for missing manifest, False for ai-owned,
    True for user-owned."""
    # Missing manifest: graceful False.
    assert is_user_override(tmp_path, relative_path="system/controlDict") is False

    (tmp_path / "case_manifest.yaml").write_text(
        yaml.safe_dump({"case_id": "x", "schema_version": 2}), encoding="utf-8"
    )
    mark_ai_authored(tmp_path, relative_paths=["system/controlDict"], action="setup")
    assert is_user_override(tmp_path, relative_path="system/controlDict") is False

    mark_user_override(
        tmp_path,
        relative_path="system/controlDict",
        new_content=b"x",
    )
    assert is_user_override(tmp_path, relative_path="system/controlDict") is True


def test_compute_etag_deterministic_and_truncated():
    """Etag is SHA-256 truncated to 16 chars — stable across calls."""
    a = compute_etag(b"hello")
    b = compute_etag(b"hello")
    c = compute_etag(b"world")
    assert a == b
    assert a != c
    assert len(a) == 16


def test_write_case_manifest_cleans_up_partial_tmp_write(tmp_path, monkeypatch):
    """Codex round-6 LOW closure: write_case_manifest's tmp_path.write_text
    can fail partway (creates+truncates the .tmp before raising). The
    cleanup must unlink the orphan so case_manifest.yaml.tmp doesn't
    leak in the case dir."""
    from pathlib import Path

    from ui.backend.services.case_manifest import io as io_mod

    case_dir = tmp_path / "case-partial-manifest"
    case_dir.mkdir()
    manifest = CaseManifest(case_id="case-partial-manifest")

    real_write_text = Path.write_text

    def partial_manifest_write(self, data, *args, **kwargs):
        if self.name == "case_manifest.yaml.tmp":
            real_write_text(self, data[: len(data) // 2], *args, **kwargs)
            raise OSError("simulated partial-manifest-write (round-6)")
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", partial_manifest_write)

    raised = False
    try:
        io_mod.write_case_manifest(case_dir, manifest)
    except OSError:
        raised = True
    assert raised

    leftover = list(case_dir.glob("*.tmp"))
    assert leftover == [], (
        f"partial manifest tmp write leaked: {leftover} — "
        f"cleanup must cover the write_text failure path, not just os.replace"
    )
