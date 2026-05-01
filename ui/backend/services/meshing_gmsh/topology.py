"""Topology partitioning for multi-body gmsh imports (DEC-V61-104).

After ``classifySurfaces`` + ``createGeometry``, gmsh has a flat list
of N parametric surfaces. The current single-volume construction
(``addVolume([single_loop])``) tetrahedralizes the entire convex hull
including any interior obstacle volumes — a thin blade in a cavity
gets meshed as fluid, not as a hole. This module groups surfaces by
topological body so the volume construction can subtract inner bodies
via ``addVolume([outer_loop, -inner_loop_1, -inner_loop_2, ...])``.

Body partitioning uses **shared-edge connectivity**: two parametric
surfaces belong to the same body iff they share at least one bounding
edge. Outer-body identification uses **largest bbox volume** computed
from the mesh nodes still attached to each surface (pre-generate(3)).

Backward compat: when only one connected body is found (single-shell
STL like LDC, channel, cylinder, naca0012), callers fall through to
the existing single-loop path so byte-identical mesh output is
preserved.
"""

from __future__ import annotations

from typing import Any


def partition_surfaces_by_body(
    gmsh: Any, surfaces: list[tuple[int, int]]
) -> list[list[int]]:
    """Group parametric surfaces by topological body via shared-edge
    connectivity, then sort bodies so the outer (largest-bbox) is
    first.

    ``surfaces`` is the result of ``gmsh.model.getEntities(dim=2)`` —
    a list of ``(dim, tag)`` pairs. Returns
    ``[[outer_surface_tags], [inner_1_tags], [inner_2_tags], ...]``.
    Each inner sublist becomes a negated surface loop in the volume
    construction (a hole in the fluid domain).

    Edge cases:
    - empty input → returns ``[]``
    - single body (no obstacles) → returns ``[[all_tags]]`` so callers
      can fall through to the legacy single-loop path
    - two bodies of equal bbox volume → ties broken arbitrarily by
      whichever the partitioner saw first; document as a limitation
      since CFD use cases never have multiple equal-size outer bodies
      in practice
    """
    if not surfaces:
        return []
    if len(surfaces) == 1:
        return [[surfaces[0][1]]]

    # Build edge → set-of-surface-tags index via gmsh.model.getBoundary.
    edge_to_surfaces: dict[int, set[int]] = {}
    for _dim, s_tag in surfaces:
        boundaries = gmsh.model.getBoundary([(2, s_tag)], oriented=False)
        for _bd_dim, e_tag in boundaries:
            edge_to_surfaces.setdefault(abs(int(e_tag)), set()).add(int(s_tag))

    # Union-find on surface tags via shared edges.
    parent: dict[int, int] = {int(tag): int(tag) for _d, tag in surfaces}

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        rx, ry = _find(x), _find(y)
        if rx != ry:
            parent[rx] = ry

    for shared in edge_to_surfaces.values():
        if len(shared) <= 1:
            continue
        first = next(iter(shared))
        for s in shared:
            if s != first:
                _union(first, s)

    # Group surfaces by their root.
    groups: dict[int, list[int]] = {}
    for _d, tag in surfaces:
        groups.setdefault(_find(int(tag)), []).append(int(tag))
    bodies: list[list[int]] = [sorted(g) for g in groups.values()]

    if len(bodies) <= 1:
        return bodies

    # Identify outer by largest bbox volume on the mesh nodes still
    # attached to each surface. classifySurfaces+createGeometry hasn't
    # destroyed the original STL triangle mesh yet, so the per-surface
    # nodes still cover the body's bounding region.
    sizes_with_idx = [
        (_bbox_volume(_body_bbox(gmsh, body)), idx)
        for idx, body in enumerate(bodies)
    ]
    sizes_with_idx.sort(reverse=True)  # largest first
    outer_idx = sizes_with_idx[0][1]
    outer = bodies[outer_idx]
    inners = [bodies[i] for i in range(len(bodies)) if i != outer_idx]
    return [outer] + inners


def _body_bbox(gmsh: Any, body_surface_tags: list[int]) -> tuple[float, ...]:
    """Return the axis-aligned bounding box ``(xmin, ymin, zmin, xmax,
    ymax, zmax)`` covering all triangle nodes in the body's surfaces.

    Uses ``gmsh.model.mesh.getElements`` + ``gmsh.model.mesh.getNode``
    to read the mesh node coords still attached to each parametric
    surface. Robust to surfaces that lost their elements (skips them
    rather than raising) — defensive for edge cases where
    classifySurfaces produced a degenerate parametric surface.
    """
    xmin = ymin = zmin = float("inf")
    xmax = ymax = zmax = float("-inf")
    seen_nodes: set[int] = set()
    for s_tag in body_surface_tags:
        try:
            _types, _elem_tags_list, node_tags_list = gmsh.model.mesh.getElements(
                dim=2, tag=s_tag
            )
        except Exception:  # noqa: BLE001 — gmsh raises generic Exception on bad tags
            continue
        if not node_tags_list or len(node_tags_list[0]) == 0:
            continue
        for nid in node_tags_list[0]:
            nid_int = int(nid)
            if nid_int in seen_nodes:
                continue
            seen_nodes.add(nid_int)
            try:
                c, _parametric, _dim, _tag = gmsh.model.mesh.getNode(nid_int)
            except Exception:  # noqa: BLE001
                continue
            xmin = min(xmin, c[0])
            ymin = min(ymin, c[1])
            zmin = min(zmin, c[2])
            xmax = max(xmax, c[0])
            ymax = max(ymax, c[1])
            zmax = max(zmax, c[2])
    if xmin == float("inf"):
        # Body had no readable nodes — return a degenerate bbox so the
        # body sorts last (zero volume) without crashing.
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return (xmin, ymin, zmin, xmax, ymax, zmax)


def _bbox_volume(bbox: tuple[float, ...]) -> float:
    """Volume of an axis-aligned bbox; clamps to non-negative for
    degenerate (zero-extent) bboxes."""
    xmin, ymin, zmin, xmax, ymax, zmax = bbox
    return (
        max(0.0, xmax - xmin)
        * max(0.0, ymax - ymin)
        * max(0.0, zmax - zmin)
    )
