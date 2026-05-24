"""DEC-V61-202-SUB-M31-CYCLE8 · unknown patch_type info-warning tests.

BUG-CYCLE5-4: PATCH `bc.patches.inlet.patch_type = "fixedValue_typo"`
formerly succeeded with no validation warning. OpenFOAM accepts any
string and validates at solver-runtime, so typos surface as cryptic
runtime FATAL IO ERRORs instead of workbench-time gaps. Cycle 8 adds
an info-level gap when a patch_type is outside the common OpenFOAM
vocabulary — non-blocking, but engineer-visible.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

import ui.backend.services.case_completeness.analyzer as cc_analyzer
from ui.backend.services.case_completeness import analyze_case_completeness


@pytest.fixture
def isolated_imported_root(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp(prefix="cycle8_test_"))
    imported_root = tmpdir / "imported"
    imported_root.mkdir()
    monkeypatch.setattr(cc_analyzer, "IMPORTED_DIR", imported_root)
    monkeypatch.setenv("WORKBENCH_PROVENANCE_DISABLED", "1")
    return imported_root


def _write_case(imported_root: Path, case_id: str, manifest: dict) -> None:
    case_dir = imported_root / case_id
    case_dir.mkdir()
    (case_dir / "case_manifest.yaml").write_text(yaml.safe_dump(manifest))


def _base_manifest(case_id: str, patches: dict) -> dict:
    return {
        "case_id": case_id,
        "solver_backend": "openfoam",
        "physics": {"solver": "interFoam", "turbulence_model": "kOmegaSST"},
        "case_family": "ship_vof",
        "bc": {"patches": patches},
    }


# ─── known types: no info gap ───


def test_all_known_patch_types_produce_no_info_gap(isolated_imported_root):
    _write_case(
        isolated_imported_root,
        "case_clean",
        _base_manifest(
            "case_clean",
            {
                "inlet": {"patch_type": "fixedValue"},
                "outlet": {"patch_type": "zeroGradient"},
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    report = analyze_case_completeness("case_clean")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == []


def test_constraint_types_are_known(isolated_imported_root):
    """Common constraint types (symmetry/cyclic/empty/processor) must
    be in the vocabulary."""
    _write_case(
        isolated_imported_root,
        "case_constraints",
        _base_manifest(
            "case_constraints",
            {
                "front": {"patch_type": "symmetry"},
                "back": {"patch_type": "symmetry"},
                "axis": {"patch_type": "wedge"},
                "ghost": {"patch_type": "empty"},
                "proc_boundary": {"patch_type": "processor"},
            },
        ),
    )
    report = analyze_case_completeness("case_constraints")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == []


# ─── unknown / typo: info gap with right shape ───


def test_typo_patch_type_produces_info_gap(isolated_imported_root):
    _write_case(
        isolated_imported_root,
        "case_typo",
        _base_manifest(
            "case_typo",
            {
                "inlet": {"patch_type": "fixedValue_typo"},  # typo
                "outlet": {"patch_type": "zeroGradient"},
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    report = analyze_case_completeness("case_typo")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert len(info_gaps) == 1
    gap = info_gaps[0]
    assert gap.field_path == "bc.patches.inlet.patch_type"
    assert "fixedValue_typo" in gap.why
    assert "inlet" in gap.why


def test_multiple_unknown_patch_types_each_get_a_gap(isolated_imported_root):
    _write_case(
        isolated_imported_root,
        "case_multi_typo",
        _base_manifest(
            "case_multi_typo",
            {
                "inlet": {"patch_type": "fxedValue"},  # typo 1
                "outlet": {"patch_type": "zeroGradiet"},  # typo 2
                "wall": {"patch_type": "noSlip"},  # valid
            },
        ),
    )
    report = analyze_case_completeness("case_multi_typo")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert len(info_gaps) == 2
    paths = sorted(g.field_path for g in info_gaps)
    assert paths == [
        "bc.patches.inlet.patch_type",
        "bc.patches.outlet.patch_type",
    ]


# ─── info gaps don't block readiness ───


def test_info_gap_does_not_block_ready(isolated_imported_root):
    _write_case(
        isolated_imported_root,
        "case_typo_ready",
        _base_manifest(
            "case_typo_ready",
            {
                "inlet": {"patch_type": "fixedValue_typo"},
                "outlet": {"patch_type": "zeroGradient"},
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    report = analyze_case_completeness("case_typo_ready")
    assert report.ready_for_archive is True
    assert report.blocked_by_critical == 0


def test_percentage_stays_balanced_with_unknown_types(isolated_imported_root):
    """expected_info_count = unknown_patch_type_count, so total grows
    by the same amount as missing — `present` count is unchanged.
    """
    _write_case(
        isolated_imported_root,
        "case_balance",
        _base_manifest(
            "case_balance",
            {
                "inlet": {"patch_type": "fixedValue"},
                "outlet": {"patch_type": "totallyMadeUp"},  # unknown
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    report = analyze_case_completeness("case_balance")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert len(info_gaps) == 1
    # Total should be ≥ missing — never under
    assert report.total_count >= len(report.missing)


# ─── non-dict patch entries don't crash ───


def test_non_dict_patch_entry_silently_skipped(isolated_imported_root):
    """A corrupted patch entry (not a dict) is handled by cycle-7's
    schema-validity gap; this scan must not crash on it.
    """
    _write_case(
        isolated_imported_root,
        "case_corrupted_skip",
        _base_manifest(
            "case_corrupted_skip",
            {
                "inlet": "not_a_dict",  # cycle-7 territory; skipped here
                "outlet": {"patch_type": "zeroGradient"},
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    # This will raise via cycle-7's schema check or pass without
    # crashing. Either way, no AttributeError / TypeError from cycle-8.
    report = analyze_case_completeness("case_corrupted_skip")
    # Schema-invalid critical from cycle-7 is fine; cycle-8 just must
    # not contribute its own crash.
    info_gaps_about_inlet = [
        m for m in report.missing
        if m.severity == "info" and "inlet" in m.field_path
    ]
    # 'inlet' is a string so cycle 8 should skip it (not a dict patch entry)
    assert info_gaps_about_inlet == []


def test_groovy_and_coded_bcs_are_known(isolated_imported_root):
    """Cycle-8 R1 P2 regression: groovyBC + swak4Foam are coded BCs
    that the V63-A catalog intentionally excludes (it audits typos,
    not enum closure). The cycle-8 typo-detector includes them so
    cases legitimately using groovyBC don't info-warn.
    """
    _write_case(
        isolated_imported_root,
        "case_coded",
        _base_manifest(
            "case_coded",
            {
                "inlet": {"patch_type": "groovyBC"},
                "outlet": {"patch_type": "swak4Foam"},
                "wall": {"patch_type": "codedFixedValue"},
            },
        ),
    )
    report = analyze_case_completeness("case_coded")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == []


def test_case_completeness_does_not_import_geometry_ingest():
    """Cycle-8 R1 P1 regression: case_completeness must NOT pull
    geometry_ingest (which transitively imports trimesh) into its
    import tree. Base `[ui]` install without `[workbench]` extra
    must boot ui.backend.main successfully.

    Static check: scan the analyzer source for any
    `geometry_ingest` import. The vocabulary is inline-copied with
    a CANONICAL SSOT comment pointing back to the V63-A catalog.
    Drift between the two is caught by the separate
    `test_v63a_catalog_is_subset_of_known_types`.

    Why static (not importlib): `importlib.reload(analyzer)` corrupts
    subsequent test state because other test modules cache analyzer
    references at collection time. A source-level grep is cheap +
    deterministic.
    """
    from pathlib import Path
    import ui.backend.services.case_completeness.analyzer as analyzer

    src = Path(analyzer.__file__).read_text(encoding="utf-8")
    bad_imports = [
        line for line in src.splitlines()
        if "geometry_ingest" in line
        and ("import" in line or "from" in line)
        and not line.lstrip().startswith("#")
    ]
    assert not bad_imports, (
        "case_completeness/analyzer.py imports from geometry_ingest, "
        "which transitively imports trimesh and breaks base `[ui]` "
        "install. Inline-copy the vocabulary instead. Offending lines: "
        f"{bad_imports}"
    )
    # Spot-check: the inlined vocabulary is populated.
    assert "fixedValue" in analyzer._KNOWN_OPENFOAM_PATCH_TYPES
    assert "waveTransmissive" in analyzer._KNOWN_OPENFOAM_PATCH_TYPES
    assert "groovyBC" in analyzer._KNOWN_OPENFOAM_PATCH_TYPES
    assert "patch" in analyzer._KNOWN_OPENFOAM_PATCH_TYPES


def test_v63a_catalog_is_subset_of_known_types():
    """Drift-detection: if V63-A canonical catalog grows, our inlined
    copy must keep up. Failing this test signals the canonical
    `STANDARD_OPENFOAM_BCS` added entries not yet mirrored into
    `_KNOWN_OPENFOAM_PATCH_TYPES`. This import only runs in the
    `[workbench]` test environment (trimesh available).
    """
    try:
        from ui.backend.services.geometry_ingest.bc_type_name_validity_advisor import (
            STANDARD_OPENFOAM_BCS,
        )
    except ImportError:
        pytest.skip("geometry_ingest unavailable in this install (base [ui] only)")
        return

    from ui.backend.services.case_completeness.analyzer import (
        _KNOWN_OPENFOAM_PATCH_TYPES,
    )

    missing_from_local = STANDARD_OPENFOAM_BCS - _KNOWN_OPENFOAM_PATCH_TYPES
    assert not missing_from_local, (
        "V63-A canonical catalog has entries not mirrored in "
        "case_completeness/analyzer.py:_KNOWN_OPENFOAM_PATCH_TYPES: "
        f"{sorted(missing_from_local)}. Mirror them per the SSOT comment."
    )


def test_compressible_les_patch_types_are_known(isolated_imported_root):
    """Cycle-8 R0 P2-B regression: types like waveTransmissive /
    turbulentInlet / mixed / timeVaryingMappedFixedValue are
    legitimate per V63-A catalog. Must NOT info-warn.
    """
    _write_case(
        isolated_imported_root,
        "case_compressible",
        _base_manifest(
            "case_compressible",
            {
                "inlet": {"patch_type": "turbulentInlet"},  # ESI mainline derived
                "outlet": {"patch_type": "waveTransmissive"},  # ESI compressible
                "interface": {"patch_type": "mixed"},  # fvPatchField/basic
                "mapped_inlet": {"patch_type": "timeVaryingMappedFixedValue"},
            },
        ),
    )
    report = analyze_case_completeness("case_compressible")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == [], (
        f"compressible/LES types should not info-warn: "
        f"{[(g.field_path, g.why[:60]) for g in info_gaps]}"
    )


def test_bc_section_non_dict_does_not_crash(isolated_imported_root):
    """Cycle-8 R0 P2-A regression: a schema-invalid manifest where `bc`
    itself is not a mapping (e.g. `bc: 1`, `bc: null`) must NOT crash
    the analyzer. Cycle-7 still surfaces the structural-meta critical
    via _check_imported_manifest; cycle-8 just must not pre-empt that
    with AttributeError.
    """
    manifest = {
        "case_id": "case_bc_corrupted",
        "solver_backend": "openfoam",
        "physics": {"solver": "interFoam", "turbulence_model": "kOmegaSST"},
        "case_family": "ship_vof",
        "bc": 1,  # NOT a dict — schema-invalid in the worst way
    }
    _write_case(isolated_imported_root, "case_bc_corrupted", manifest)
    # Must complete without raising AttributeError
    report = analyze_case_completeness("case_bc_corrupted")
    # Cycle-7 should surface a critical (manifest schema invalid)
    crits = [m for m in report.missing if m.severity == "critical"]
    assert crits, "cycle-7 critical should still fire"


def test_bc_patches_non_dict_does_not_crash(isolated_imported_root):
    """`bc: {patches: "broken"}` — bc.patches not a dict. Cycle 8
    skips silently; doesn't crash.
    """
    manifest = {
        "case_id": "case_patches_corrupted",
        "solver_backend": "openfoam",
        "physics": {"solver": "interFoam", "turbulence_model": "kOmegaSST"},
        "case_family": "ship_vof",
        "bc": {"patches": "broken"},
    }
    _write_case(isolated_imported_root, "case_patches_corrupted", manifest)
    # No crash; info gaps are empty (nothing iterable to scan)
    report = analyze_case_completeness("case_patches_corrupted")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == []


def test_bc_null_does_not_crash(isolated_imported_root):
    """`bc: null` — most common YAML-edit accident."""
    manifest = {
        "case_id": "case_bc_null",
        "solver_backend": "openfoam",
        "physics": {"solver": "interFoam", "turbulence_model": "kOmegaSST"},
        "case_family": "ship_vof",
        "bc": None,
    }
    _write_case(isolated_imported_root, "case_bc_null", manifest)
    report = analyze_case_completeness("case_bc_null")
    info_gaps = [m for m in report.missing if m.severity == "info"]
    assert info_gaps == []


def test_patch_with_no_patch_type_field_skipped(isolated_imported_root):
    """If the patch dict exists but has no patch_type key, cycle 8
    skips it (other rule layers may flag the missing field; cycle 8's
    scope is unknown-value warnings, not missing-field warnings).
    """
    _write_case(
        isolated_imported_root,
        "case_no_type",
        _base_manifest(
            "case_no_type",
            {
                "inlet": {"some_other_field": "x"},  # no patch_type
                "outlet": {"patch_type": "zeroGradient"},
                "wall": {"patch_type": "noSlip"},
            },
        ),
    )
    report = analyze_case_completeness("case_no_type")
    info_gaps_about_inlet = [
        m for m in report.missing
        if m.severity == "info" and "inlet" in m.field_path
    ]
    assert info_gaps_about_inlet == []
