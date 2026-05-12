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


# ----- F-NEW-26 defensive layer (session 11 · body-pair AABB overlap detection) -----
#
# These tests cover the AABB-overlap detection added to health_check.py.
# Predicate tests are pure (no STL bytes); integration tests drive
# run_health_checks directly with synthesized body_aabbs.

from ui.backend.services.geometry_ingest import (
    BodyAABB,
    BodyPairOverlap,
    detect_body_pair_overlaps,
)
from ui.backend.services.geometry_ingest.health_check import run_health_checks


def _aabb(name: str, mins: tuple[float, float, float], maxs: tuple[float, float, float]) -> BodyAABB:
    return BodyAABB(name=name, min_xyz=mins, max_xyz=maxs)


def test_detect_body_pair_overlaps_disjoint_returns_empty():
    """Two clearly disjoint AABBs → no overlap pair."""
    a = _aabb("a", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    b = _aabb("b", (5.0, 5.0, 5.0), (6.0, 6.0, 6.0))
    assert detect_body_pair_overlaps([a, b]) == []


def test_detect_body_pair_overlaps_containment_classified_as_containment():
    """Outer AABB strictly contains inner — cavity / interior-obstacle pattern."""
    outer = _aabb("outer", (0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    inner = _aabb("inner", (4.0, 4.0, 4.0), (6.0, 6.0, 6.0))
    pairs = detect_body_pair_overlaps([outer, inner])
    assert len(pairs) == 1
    assert pairs[0].classification == "containment"


def test_detect_body_pair_overlaps_significant_classified_as_significant():
    """≥25% volume overlap relative to smaller body."""
    a = _aabb("a", (0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    b = _aabb("b", (5.0, 5.0, 5.0), (15.0, 15.0, 15.0))
    # intersection = 5*5*5 = 125; b's volume = 1000; ratio = 12.5%. Need closer overlap.
    c = _aabb("c", (0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    d = _aabb("d", (2.0, 2.0, 2.0), (12.0, 12.0, 12.0))
    # intersection = 8*8*8 = 512; d's volume = 1000; ratio = 51.2% ≥ 25%
    pairs = detect_body_pair_overlaps([c, d])
    assert len(pairs) == 1
    assert pairs[0].classification == "significant"


def test_detect_body_pair_overlaps_edge_slice_classified_as_edge_overlap():
    """Thin slice overlap at AABB extents (F-NEW-26 thick-plate signature):
    two `lx × ly × t` plates at adjacent faces of a domain cuboid produce
    an `lx × t × t` edge overlap = tiny fraction of either plate's volume.
    """
    # farfield_top: lx=10, ly=10, thickness 0.1 at z=10
    top = _aabb("farfield_top", (0.0, 0.0, 9.95), (10.0, 10.0, 10.05))
    # farfield_outer: lx=10, thickness 0.1 at y=10, lz=10
    outer = _aabb("farfield_outer", (0.0, 9.95, 0.0), (10.0, 10.05, 10.0))
    # overlap region: x∈[0,10], y∈[9.95,10.05], z∈[9.95,10.05] = 10*0.1*0.1 = 0.1
    # smaller volume: 10*10*0.1 = 10; ratio = 1% << 25%
    pairs = detect_body_pair_overlaps([top, outer])
    assert len(pairs) == 1
    assert pairs[0].classification == "edge_overlap"


def test_detect_body_pair_overlaps_case_003_6_plate_signature():
    """case_003 F-NEW-26 reproduction: 6 thick plates at the 6 faces of a
    CFD domain cuboid produce 12 edge-overlap pairs (12 edges of cube).
    """
    t = 0.1  # plate thickness
    L = 10.0  # domain extent
    plates = [
        _aabb("inlet",          (-t/2, -L/2, -L/2), (t/2,  L/2, L/2)),    # x=0 face
        _aabb("outlet",         (L-t/2, -L/2, -L/2), (L+t/2, L/2, L/2)),  # x=L face
        _aabb("symmetry_plane", (-L/2-t, -t/2, -L/2), (L+L/2, t/2, L/2)),
        _aabb("farfield_outer", (-L/2-t, L-t/2, -L/2), (L+L/2, L+t/2, L/2)),
        _aabb("farfield_bottom",(-L/2-t, -L/2, -t/2), (L+L/2, L+L/2, t/2)),
        _aabb("farfield_top",   (-L/2-t, -L/2, L-t/2), (L+L/2, L+L/2, L+t/2)),
    ]
    pairs = detect_body_pair_overlaps(plates)
    edge_overlaps = [p for p in pairs if p.classification == "edge_overlap"]
    # 6 plates at the 6 faces of a cube share 12 edges of the cube — but
    # many pairs share more than one edge. Lower bound: ≥ 3 to trip
    # the systematic-CAD-bug error path.
    assert len(edge_overlaps) >= 3, (
        f"6-plate fixture must produce ≥3 edge overlaps (F-NEW-26 signature); got {len(edge_overlaps)}"
    )


def test_run_health_checks_emits_error_on_case_003_pattern():
    """Integration: feed run_health_checks the 6-plate AABB list and verify
    it emits an error pointing at the cross-repo ticket.
    """
    import trimesh
    from ui.backend.services.geometry_ingest.health_check import (
        PatchInfo,
        run_health_checks,
    )

    t = 0.1
    L = 10.0
    plates = [
        _aabb("inlet",          (-t/2, -L/2, -L/2), (t/2,  L/2, L/2)),
        _aabb("outlet",         (L-t/2, -L/2, -L/2), (L+t/2, L/2, L/2)),
        _aabb("symmetry_plane", (-L/2-t, -t/2, -L/2), (L+L/2, t/2, L/2)),
        _aabb("farfield_outer", (-L/2-t, L-t/2, -L/2), (L+L/2, L+t/2, L/2)),
        _aabb("farfield_bottom",(-L/2-t, -L/2, -t/2), (L+L/2, L+L/2, t/2)),
        _aabb("farfield_top",   (-L/2-t, -L/2, L-t/2), (L+L/2, L+L/2, L+t/2)),
    ]
    # Caller still needs a combined trimesh for the watertight/bbox checks;
    # use a simple box so those pass cleanly.
    combined = trimesh.creation.box([1.0, 1.0, 1.0])
    report = run_health_checks(
        combined=combined,
        solid_count=6,
        patches=[],
        all_default_faces=False,
        body_aabbs=plates,
    )
    assert any("F-NEW-26" in e or "edge AABB" in e for e in report.errors), (
        f"expected F-NEW-26 error, got errors={report.errors}"
    )


def test_run_health_checks_silent_on_cavity_pattern():
    """Outer + inner containment is the valid cavity / interior-obstacle
    pattern. Must NOT emit any AABB-overlap warning or error.
    """
    import trimesh

    outer = _aabb("outer", (0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    inner = _aabb("inner", (4.0, 4.0, 4.0), (6.0, 6.0, 6.0))
    combined = trimesh.creation.box([10.0, 10.0, 10.0])
    report = run_health_checks(
        combined=combined,
        solid_count=2,
        patches=[],
        all_default_faces=False,
        body_aabbs=[outer, inner],
    )
    aabb_msgs = [
        m for m in report.warnings + report.errors
        if "AABB" in m or "F-NEW-26" in m
    ]
    assert aabb_msgs == [], (
        f"cavity pattern (containment) should not emit AABB overlap diagnostic, got {aabb_msgs}"
    )


def test_run_health_checks_silent_on_clean_disjoint_bodies():
    """N bodies with no AABB intersection: no overlap diagnostic emitted."""
    import trimesh

    bodies = [
        _aabb("body_a", (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        _aabb("body_b", (5.0, 5.0, 5.0), (6.0, 6.0, 6.0)),
        _aabb("body_c", (10.0, 10.0, 10.0), (11.0, 11.0, 11.0)),
    ]
    combined = trimesh.creation.box([1.0, 1.0, 1.0])
    report = run_health_checks(
        combined=combined,
        solid_count=3,
        patches=[],
        all_default_faces=False,
        body_aabbs=bodies,
    )
    aabb_msgs = [
        m for m in report.warnings + report.errors
        if "AABB" in m or "F-NEW-26" in m
    ]
    assert aabb_msgs == []


def test_run_health_checks_single_edge_overlap_warns_not_errors():
    """One or two edge_overlap pairs is a warning, not an error
    (could be a legitimate shared-corner assembly). Three or more
    triggers the systematic-bug error path."""
    import trimesh

    t = 0.1
    a = _aabb("a", (0.0, 0.0, 0.0), (10.0, 10.0, t))     # thin plate at z=0
    b = _aabb("b", (9.95, 0.0, 0.0), (10.05, 10.0, 10.0))  # thin plate at x=10
    # Overlap region: x∈[9.95, 10], y∈[0,10], z∈[0, 0.1] = 0.05 * 10 * 0.1 = 0.05
    # a's vol = 10*10*0.1 = 10; b's vol = 0.1*10*10 = 10. Ratio = 0.5%.
    combined = trimesh.creation.box([1.0, 1.0, 1.0])
    report = run_health_checks(
        combined=combined,
        solid_count=2,
        patches=[],
        all_default_faces=False,
        body_aabbs=[a, b],
    )
    aabb_warnings = [w for w in report.warnings if "edge AABB" in w]
    aabb_errors = [e for e in report.errors if "edge AABB" in e]
    assert len(aabb_warnings) == 1, f"expected 1 edge-overlap warning, got warnings={report.warnings}"
    assert aabb_errors == [], f"single edge overlap should not error, got {aabb_errors}"
