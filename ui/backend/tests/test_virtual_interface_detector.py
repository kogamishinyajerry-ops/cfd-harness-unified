"""Tests for ``geometry_ingest.virtual_interface_detector`` (A2 advisor).

Coverage targets the 5 cases enumerated in
``.planning/patches/draft_a2_extraction_2026-05-08.md``:

  1. shared mode with known interface → matched
  2. shared mode with non-overlapping bodies → not matched
  3. BREP equality fails but geometric matches → matched (V2 case)
  4. endcap mode: parallel-aligned normals → matched
  5. threshold sensitivity at 79% bbox overlap → not matched (boundary)

Plus a coverage-validation smoke test (mostly to lock the API).
"""
from __future__ import annotations

from ui.backend.services.geometry_ingest.virtual_interface_detector import (
    BodyGeometry,
    DEFAULT_BBOX_OVERLAP_MIN,
    DetectedInterface,
    FaceGeometry,
    InterfaceSpec,
    area_diff_fraction,
    bbox_overlap_fraction,
    detect_virtual_interfaces,
    faces_match_shared,
    find_endcap_face,
    find_face_facing_target,
    normal_dot,
    validate_interface_coverage,
)


def _face(*, area, bbox_min, bbox_max, normal, centroid):
    return FaceGeometry(
        area=area, bbox_min=bbox_min, bbox_max=bbox_max, normal=normal, centroid=centroid,
    )


# ---------------------------------------------------------------- algorithm


def test_bbox_overlap_full_when_identical():
    f = _face(area=1.0, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 0.01),
              normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.005))
    assert bbox_overlap_fraction(f, f) == 1.0


def test_bbox_overlap_zero_when_disjoint():
    a = _face(area=1.0, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 0.01),
              normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.005))
    b = _face(area=1.0, bbox_min=(5.0, 5.0, 0.0), bbox_max=(6.0, 6.0, 0.01),
              normal=(0.0, 0.0, 1.0), centroid=(5.5, 5.5, 0.005))
    assert bbox_overlap_fraction(a, b) == 0.0


def test_area_diff_zero_when_equal():
    f = _face(area=2.5, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 0.01),
              normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.005))
    assert area_diff_fraction(f, f) == 0.0


def test_normal_dot_opposing_returns_neg_one():
    a = _face(area=1.0, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 0.01),
              normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.005))
    b = _face(area=1.0, bbox_min=(0.0, 0.0, -0.01), bbox_max=(1.0, 1.0, 0.0),
              normal=(0.0, 0.0, -1.0), centroid=(0.5, 0.5, -0.005))
    assert normal_dot(a, b) == -1.0


# ---------------------------------------------------------------- spec/driver


def _shared_pair_bodies():
    """Two boxes touching at z=0 plane; each carries the interface face."""
    face_a = _face(
        area=1.0, bbox_min=(0.0, 0.0, -0.005), bbox_max=(1.0, 1.0, 0.005),
        normal=(0.0, 0.0, -1.0), centroid=(0.5, 0.5, 0.0),
    )
    face_b = _face(
        area=1.0, bbox_min=(0.0, 0.0, -0.005), bbox_max=(1.0, 1.0, 0.005),
        normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.0),
    )
    body_a = BodyGeometry(name="A", faces=(face_a,), centroid=(0.5, 0.5, 0.5))
    body_b = BodyGeometry(name="B", faces=(face_b,), centroid=(0.5, 0.5, -0.5))
    return body_a, body_b, face_a, face_b


def test_case1_shared_mode_known_interface_matched():
    """Two boxes at z=0; spec mode='shared' → matched."""
    body_a, body_b, _, _ = _shared_pair_bodies()
    spec = InterfaceSpec(patch_name="ab_iface", mode="shared", body_a="A", body_b="B")
    [result] = detect_virtual_interfaces({"A": body_a, "B": body_b}, [spec])
    assert result.matched
    assert result.body_owner in {"A", "B"}
    assert result.face is not None


def test_case2_shared_mode_no_overlap_not_matched():
    """Two boxes far apart, no facing planes → not matched."""
    face_a = _face(
        area=1.0, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 0.01),
        normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.005),
    )
    face_b = _face(
        area=1.0, bbox_min=(10.0, 10.0, 0.0), bbox_max=(11.0, 11.0, 0.01),
        normal=(0.0, 0.0, 1.0), centroid=(10.5, 10.5, 0.005),
    )
    body_a = BodyGeometry(name="A", faces=(face_a,), centroid=(0.5, 0.5, 0.5))
    body_b = BodyGeometry(name="B", faces=(face_b,), centroid=(10.5, 10.5, 0.5))
    spec = InterfaceSpec(patch_name="iface", mode="shared", body_a="A", body_b="B")
    [result] = detect_virtual_interfaces({"A": body_a, "B": body_b}, [spec])
    assert not result.matched
    assert "no planar face" in result.diagnostic


def test_case3_brep_inequality_geometric_match():
    """Two distinct BREP faces share a plane geometrically (V2 case).

    Different parametric directions / vertex orderings → an isSame()
    fast-path would miss this. Geometric heuristic finds the match.
    """
    # Same physical plane, same area, opposite-pointing normals; APU
    # bay V2 hallmark — a hypothetical isSame() would return False here
    # because we did NOT mark these as the same BREP entity.
    body_a, body_b, _, _ = _shared_pair_bodies()
    spec = InterfaceSpec(patch_name="iface", mode="shared", body_a="A", body_b="B")
    [result] = detect_virtual_interfaces({"A": body_a, "B": body_b}, [spec])
    assert result.matched, "geometric heuristic must catch what isSame() misses"


def test_case4_endcap_mode_extreme_face():
    """Find +x-most planar face with normal aligned to +x."""
    face_minus = _face(
        area=1.0, bbox_min=(-0.01, 0.0, 0.0), bbox_max=(0.01, 1.0, 1.0),
        normal=(-1.0, 0.0, 0.0), centroid=(0.0, 0.5, 0.5),
    )
    face_plus = _face(
        area=1.0, bbox_min=(9.99, 0.0, 0.0), bbox_max=(10.01, 1.0, 1.0),
        normal=(1.0, 0.0, 0.0), centroid=(10.0, 0.5, 0.5),
    )
    body = BodyGeometry(
        name="B", faces=(face_minus, face_plus), centroid=(5.0, 0.5, 0.5),
    )
    spec = InterfaceSpec(patch_name="endcap", mode="endcap", body="B", axis="+x")
    [result] = detect_virtual_interfaces({"B": body}, [spec])
    assert result.matched
    assert result.face is face_plus
    assert result.normal_dot >= 0.9


def test_case5_threshold_sensitivity_below_bbox_min_not_matched():
    """Two faces with ~79% bbox overlap → faces_match_shared returns False."""
    a = _face(
        area=1.0, bbox_min=(0.0, 0.0, 0.0), bbox_max=(1.0, 1.0, 1.0),
        normal=(0.0, 0.0, 1.0), centroid=(0.5, 0.5, 0.5),
    )
    # b shifted +x by 0.21 → intersection volume 0.79, both bbox volumes
    # equal 1.0 → fraction = 0.79 (just under DEFAULT_BBOX_OVERLAP_MIN=0.80)
    b = _face(
        area=1.0, bbox_min=(0.21, 0.0, 0.0), bbox_max=(1.21, 1.0, 1.0),
        normal=(0.0, 0.0, -1.0), centroid=(0.71, 0.5, 0.5),
    )
    overlap = bbox_overlap_fraction(a, b)
    assert overlap < DEFAULT_BBOX_OVERLAP_MIN, f"setup error: overlap={overlap}"
    assert not faces_match_shared(a, b)


# ---------------------------------------------------------------- coverage report


def test_validate_interface_coverage_partial():
    spec1 = InterfaceSpec(patch_name="hit", mode="shared", body_a="A", body_b="B")
    spec2 = InterfaceSpec(patch_name="miss", mode="shared", body_a="X", body_b="Y")
    detected = [
        DetectedInterface(
            patch_name="hit", matched=True, body_owner="A", face=None,
            bbox_overlap_fraction=1.0, area_diff_fraction=0.0, normal_dot=-1.0,
            diagnostic="ok",
        ),
        DetectedInterface(
            patch_name="miss", matched=False, body_owner=None, face=None,
            bbox_overlap_fraction=0.0, area_diff_fraction=1.0, normal_dot=0.0,
            diagnostic="missing body",
        ),
    ]
    report = validate_interface_coverage(detected, [spec1, spec2])
    assert report["expected_count"] == 2
    assert report["landed_count"] == 1
    assert report["landed_patches"] == ["hit"]
    assert report["missed_patches"] == ["miss"]
    assert report["coverage_fraction"] == 0.5


def test_unknown_mode_returns_unmatched():
    body = BodyGeometry(name="X", faces=(), centroid=(0.0, 0.0, 0.0))
    spec = InterfaceSpec(patch_name="bogus", mode="random_mode_string")
    [result] = detect_virtual_interfaces({"X": body}, [spec])
    assert not result.matched
    assert "unknown mode" in result.diagnostic
