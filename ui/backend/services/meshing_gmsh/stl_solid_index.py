"""Parse multi-solid ASCII STL files to recover per-solid triangle
centroids for post-classify patch-name remapping.

Adversarial-loop iter02 found that ``gmsh.merge(stl)`` followed by
``classifySurfaces(angle=40°)`` re-derives surface partitions from
dihedral angle and discards the original ``solid <name>`` headers.
gmshToFoam then writes a single ``patch0`` and the per-patch boundary
condition surface evaporates — all multi-patch CAD imports collapse
into one anonymous wall.

The STL triangles themselves survive ``classifySurfaces`` unmodified;
gmsh just regroups them. So the recovery path is: before the merge,
record each STL solid's triangle centroids; after ``createGeometry``,
for each parametric surface entity, compare its mesh element centroid
to the per-solid centroid clouds and pick the nearest. That mapping
lets us re-apply the original patch names as physical groups, which
gmshToFoam then translates to named OpenFOAM patches.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class SolidCentroids:
    name: str
    centroids: np.ndarray  # shape (n_tri, 3)


_SOLID_BLOCK_RE = re.compile(
    rb"^\s*solid\s+(\S+)[^\n]*$\n([\s\S]*?)^\s*endsolid\b[^\n]*$\n?",
    re.MULTILINE,
)
_FACET_RE = re.compile(rb"facet\s+normal[\s\S]*?endfacet", re.MULTILINE)
_VERTEX_RE = re.compile(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)")


def parse_named_solids(stl_bytes: bytes) -> list[SolidCentroids]:
    """Return one ``SolidCentroids`` per ``solid <name>`` block in the
    bytes. Empty list if the STL is binary or has no named solids
    (callers should fall through to the legacy single-merge path).

    Names are taken verbatim from the STL — the caller is responsible
    for OpenFOAM-token sanitization (the ``patch_detector`` module
    handles that on the route side).
    """
    out: list[SolidCentroids] = []
    for m in _SOLID_BLOCK_RE.finditer(stl_bytes):
        name = m.group(1).decode("ascii", errors="replace")
        body = m.group(2)
        centroids: list[list[float]] = []
        for facet in _FACET_RE.finditer(body):
            verts = _VERTEX_RE.findall(facet.group(0))
            if len(verts) != 3:
                continue
            try:
                pts = [[float(v[0]), float(v[1]), float(v[2])] for v in verts]
            except ValueError:
                continue
            centroids.append(
                [
                    (pts[0][0] + pts[1][0] + pts[2][0]) / 3.0,
                    (pts[0][1] + pts[1][1] + pts[2][1]) / 3.0,
                    (pts[0][2] + pts[1][2] + pts[2][2]) / 3.0,
                ]
            )
        if centroids:
            out.append(
                SolidCentroids(name=name, centroids=np.asarray(centroids, dtype=float))
            )
    return out


def parse_named_solids_from_path(stl_path: Path) -> list[SolidCentroids]:
    """File-path wrapper around :func:`parse_named_solids`."""
    return parse_named_solids(stl_path.read_bytes())


def assign_surface_to_solid(
    surface_centroid: np.ndarray,
    solids: list[SolidCentroids],
) -> str | None:
    """Pick the solid whose triangle cloud is nearest to ``surface_centroid``.

    Returns ``None`` if ``solids`` is empty. The "nearest cloud" test
    uses the minimum point-to-cloud distance — robust when patches are
    spatially well-separated (the canonical case for engineering CAD
    where inlet/outlet/walls live on distinct faces of the model).

    Edge case: if two patches share a sub-face (T-junctions, complex
    assemblies) this heuristic can mis-assign. Adversarial iter03+ will
    hunt for that case and the caller should switch to a more rigorous
    membership test (per-triangle vertex-set equality) at that point.
    """
    if not solids:
        return None
    best_name: str | None = None
    best_dist = float("inf")
    for s in solids:
        d = float(np.linalg.norm(s.centroids - surface_centroid, axis=1).min())
        if d < best_dist:
            best_dist = d
            best_name = s.name
    return best_name
