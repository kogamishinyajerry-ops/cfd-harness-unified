"""Unit tests for ``assign_surface_to_solid_by_voting``.

Codex post-merge finding (defect-5 follow-up): equal-weight voting
is fooled by skewed triangle distributions where many small triangles
along a refined edge outvote fewer large triangles representing the
true patch face. Area-weighted voting fixes this. Regression tests
below verify both behaviors.
"""

from __future__ import annotations

import numpy as np
import pytest

from ui.backend.services.meshing_gmsh.stl_solid_index import (
    AmbiguousSurfaceAssignment,
    SolidCentroids,
    assign_surface_to_solid_by_voting,
)


def _solid(name: str, points: list[list[float]]) -> SolidCentroids:
    return SolidCentroids(name=name, centroids=np.asarray(points, dtype=float))


def test_equal_weight_voting_legacy_behavior_preserved():
    """No areas passed → falls back to count-based voting (1 vote per
    triangle). Verifies the existing iter04 L-bend behavior still
    works without area instrumentation."""
    solid_a = _solid("walls", [[0.0, 0.0, 0.0]])
    solid_b = _solid("inlet", [[10.0, 0.0, 0.0]])
    centroids = np.array(
        [
            [0.1, 0.0, 0.0],  # near walls
            [0.2, 0.0, 0.0],  # near walls
            [0.3, 0.0, 0.0],  # near walls
            [9.9, 0.0, 0.0],  # near inlet
        ]
    )
    name = assign_surface_to_solid_by_voting(centroids, [solid_a, solid_b])
    assert name == "walls"


def test_area_weighting_overrides_equal_count_when_skewed():
    """Adversarial case: 6 tiny near-walls triangles vs 1 large
    near-inlet triangle. Equal-weight: walls wins (6:1). Area-
    weighted: inlet wins because the single large triangle covers
    more surface than the 6 tiny ones combined."""
    solid_a = _solid("walls", [[0.0, 0.0, 0.0]])
    solid_b = _solid("inlet", [[10.0, 0.0, 0.0]])
    centroids = np.array(
        [
            [0.1, 0.0, 0.0],
            [0.2, 0.0, 0.0],
            [0.3, 0.0, 0.0],
            [0.4, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.6, 0.0, 0.0],
            [9.9, 0.0, 0.0],
        ]
    )
    areas = np.array([0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 1.0])

    # Equal-weight (no areas): walls wins 6:1.
    equal = assign_surface_to_solid_by_voting(centroids, [solid_a, solid_b])
    assert equal == "walls"

    # Area-weighted: inlet wins (1.0 vs 0.006 → 99.4 % share).
    weighted = assign_surface_to_solid_by_voting(
        centroids, [solid_a, solid_b], triangle_areas=areas
    )
    assert weighted == "inlet"


def test_area_weighted_majority_threshold_still_enforced():
    """Even with area weighting, sub-min_majority shares raise
    AmbiguousSurfaceAssignment so the engineer can disambiguate."""
    solid_a = _solid("a", [[0.0, 0.0, 0.0]])
    solid_b = _solid("b", [[10.0, 0.0, 0.0]])
    centroids = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    areas = np.array([0.55, 0.45])  # 55 % a, 45 % b — below 0.6 threshold
    with pytest.raises(AmbiguousSurfaceAssignment):
        assign_surface_to_solid_by_voting(
            centroids, [solid_a, solid_b], triangle_areas=areas, min_majority=0.6
        )


def test_area_weighted_clear_majority_succeeds():
    """0.7 vs 0.3 area weighting → winner share 70 % ≥ min_majority."""
    solid_a = _solid("a", [[0.0, 0.0, 0.0]])
    solid_b = _solid("b", [[10.0, 0.0, 0.0]])
    centroids = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    areas = np.array([0.7, 0.3])
    name = assign_surface_to_solid_by_voting(
        centroids, [solid_a, solid_b], triangle_areas=areas
    )
    assert name == "a"


def test_mismatched_areas_length_raises():
    solid_a = _solid("a", [[0.0, 0.0, 0.0]])
    solid_b = _solid("b", [[10.0, 0.0, 0.0]])
    centroids = np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    areas = np.array([1.0])  # length mismatch
    with pytest.raises(ValueError, match="triangle_areas length"):
        assign_surface_to_solid_by_voting(
            centroids, [solid_a, solid_b], triangle_areas=areas
        )


def test_single_solid_short_circuit():
    """Single source solid → no voting needed, returns immediately."""
    only = _solid("only", [[0.0, 0.0, 0.0]])
    centroids = np.array([[1.0, 2.0, 3.0]])
    name = assign_surface_to_solid_by_voting(centroids, [only])
    assert name == "only"


def test_zero_triangles_returns_none():
    solid_a = _solid("a", [[0.0, 0.0, 0.0]])
    solid_b = _solid("b", [[10.0, 0.0, 0.0]])
    centroids = np.empty((0, 3), dtype=float)
    assert assign_surface_to_solid_by_voting(centroids, [solid_a, solid_b]) is None
