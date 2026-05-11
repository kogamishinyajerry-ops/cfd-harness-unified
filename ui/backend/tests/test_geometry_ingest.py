"""Unit tests for ``ui.backend.services.geometry_ingest`` (M5.0)."""

from __future__ import annotations

from ui.backend.services.geometry_ingest import (
    canonical_stl_bytes,
    combine,
    detect_patches,
    ingest_stl,
    load_stl_from_bytes,
    run_health_checks,
    solid_count,
)
from ui.backend.tests.conftest import (
    box_stl,
    multi_solid_ascii_stl,
    open_box_stl,
    seamed_multi_solid_box_stl,
)


def test_cube_ingest_passes_with_default_face_warning():
    report = ingest_stl(box_stl())
    assert report.errors == []
    assert report.is_watertight is True
    assert report.face_count == 12  # 6 sides × 2 triangles
    assert report.is_single_shell is True
    assert report.solid_count == 1
    assert report.unit_guess == "m"
    # Binary-exported STL has no named solids — defaultFaces warning expected.
    assert report.all_default_faces is True
    assert any("defaultFaces" in w for w in report.warnings)
    assert [p.name for p in report.patches] == ["defaultFaces"]


def test_empty_bytes_rejected_with_parse_error():
    report = ingest_stl(b"")
    assert report.errors
    assert "empty" in report.errors[0].lower()
    assert report.face_count == 0


def test_garbage_bytes_rejected_with_parse_error():
    report = ingest_stl(b"this is not an STL file at all, just some garbage\x00\xff")
    assert report.errors  # parse failure
    assert report.face_count == 0


def test_non_watertight_stl_produces_error():
    report = ingest_stl(open_box_stl())
    assert report.is_watertight is False
    assert any("watertight" in e.lower() for e in report.errors)


def test_unit_guess_mm_band_kicks_in_for_large_extent():
    report = ingest_stl(box_stl(size=500.0))
    assert report.unit_guess == "mm"


def test_run_health_checks_body_class_filter_wires_through(monkeypatch):
    """V198 session 4 wiring: body_extents_raw plumbed from route layer
    flips a case_003-like overall-bbox-dominated payload from 'unknown'
    to 'mm' via :func:`detect_unit`.

    Without the filter, overall bbox 2.44e6 (raw) is industrially
    implausible under every common unit → UNKNOWN. With the filter,
    the 3 airframe-class bodies (~2e4 raw, plausible as mm) survive →
    decision = MM.
    """
    import trimesh as _tm

    combined = _tm.creation.box([2438552.0, 1600000.0, 1540000.0])
    combined.merge_vertices()
    report_with_filter = run_health_checks(
        combined=combined,
        solid_count=7,
        patches=[],
        all_default_faces=True,
        body_extents_raw=[
            2438552.0, 1600200.0, 1540764.0, 1600000.0,  # 4 CFD-domain walls
            18290.0, 27430.0, 18290.0,  # 3 airframe-class bodies (18-27 m at mm)
        ],
    )
    assert report_with_filter.unit_guess == "mm"

    report_no_filter = run_health_checks(
        combined=combined,
        solid_count=1,
        patches=[],
        all_default_faces=True,
        body_extents_raw=None,
    )
    # Legacy band: 2.44e6 > 1e5 cap → "unknown". Filter absent and the
    # bbox alone is too large to commit to any unit.
    assert report_no_filter.unit_guess == "unknown"


def test_run_health_checks_legacy_band_fallback_preserved():
    """Single-class loads with ambiguous bbox (multiple plausible units
    under :func:`detect_unit`) still get a deterministic band-based
    answer so naca0012/cylinder/ldc_box UX doesn't regress."""
    import trimesh as _tm

    combined = _tm.creation.box([1.0, 1.0, 1.0])
    combined.merge_vertices()
    report = run_health_checks(
        combined=combined,
        solid_count=1,
        patches=[],
        all_default_faces=True,
        body_extents_raw=None,
    )
    # 1.0 raw is plausible under m, cm, inch → detect_unit returns UNKNOWN.
    # Legacy band: 1e-3 ≤ 1.0 ≤ 10 → "m".
    assert report.unit_guess == "m"


def test_unit_guess_unknown_for_extreme_extent():
    report = ingest_stl(box_stl(size=1.0e7))
    assert report.unit_guess == "unknown"
    assert any("unit could not be guessed" in w.lower() for w in report.warnings)


def test_canonical_bytes_roundtrip_remains_loadable():
    original = box_stl()
    loaded, errs = load_stl_from_bytes(original)
    assert errs == []
    canon = canonical_stl_bytes(combine(loaded))
    loaded2, errs2 = load_stl_from_bytes(canon)
    assert errs2 == []
    patches2, all_default2 = detect_patches(loaded2)
    report2 = run_health_checks(
        combined=combine(loaded2),
        solid_count=solid_count(loaded2),
        patches=patches2,
        all_default_faces=all_default2,
    )
    assert report2.is_watertight is True
    assert report2.face_count == 12


def test_load_stl_from_bytes_returns_errors_on_garbage():
    loaded, errs = load_stl_from_bytes(b"\x00\x01\x02\x03not stl")
    assert loaded is None
    assert errs


def test_canonical_bytes_preserves_named_regions():
    """Multi-solid STL → canonical bytes must round-trip through trimesh
    with the same patch names. Without this, the snappyHexMeshDict.stub
    references regions that don't exist in the written triSurface STL."""
    data = multi_solid_ascii_stl("inlet", "outlet", "wall")
    loaded, errs = load_stl_from_bytes(data)
    assert errs == []
    patches, all_default = detect_patches(loaded)
    assert all_default is False
    assert {p.name for p in patches} == {"inlet", "outlet", "wall"}

    canon = canonical_stl_bytes(loaded, patch_names=[p.name for p in patches])
    loaded2, errs2 = load_stl_from_bytes(canon)
    assert errs2 == []
    patches2, all_default2 = detect_patches(loaded2)
    assert all_default2 is False
    assert {p.name for p in patches2} == {"inlet", "outlet", "wall"}


def test_seamed_multi_solid_box_passes_watertight_check():
    """Adversarial-loop iter01 regression: a single closed cube split
    into inlet/outlet/walls solids — the canonical CAD-export form —
    must report ``is_watertight=True``. Before the ``stl_loader.combine``
    fix this returned False because seam vertices weren't welded across
    solid boundaries."""
    report = ingest_stl(seamed_multi_solid_box_stl())
    assert report.errors == []
    assert report.is_watertight is True
    assert report.solid_count == 3
    assert {p.name for p in report.patches} == {"inlet", "outlet", "walls"}
    assert report.is_single_shell is True


def test_canonical_bytes_sanitizes_invalid_names_round_trip():
    """STL solid names with whitespace + special chars must survive the
    sanitize → canonical-bytes → reload pipeline as OpenFOAM-valid tokens."""
    data = multi_solid_ascii_stl("inlet zone", "wall.left")
    loaded, _ = load_stl_from_bytes(data)
    patches, _ = detect_patches(loaded)
    sanitized = {p.name for p in patches}
    assert sanitized == {"inlet_zone", "wall_left"}

    canon = canonical_stl_bytes(loaded, patch_names=[p.name for p in patches])
    loaded2, _ = load_stl_from_bytes(canon)
    patches2, _ = detect_patches(loaded2)
    assert {p.name for p in patches2} == sanitized
