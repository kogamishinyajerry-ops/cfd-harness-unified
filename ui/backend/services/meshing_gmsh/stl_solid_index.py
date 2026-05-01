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


class AmbiguousSurfaceAssignment(ValueError):
    """The nearest-cloud match for a parametric surface is too close
    to its second-best to be safely picked. The caller should escalate
    to a per-triangle vote or surface this as a hard mesh-generation
    error so an engineer reviews the geometry before BC assignment.
    """

    def __init__(self, best_name: str, second_name: str, best_dist: float, second_dist: float) -> None:
        super().__init__(
            f"surface→solid match ambiguous: {best_name!r} (d={best_dist:.4g}) "
            f"vs {second_name!r} (d={second_dist:.4g}); ratio={best_dist / max(second_dist, 1e-12):.3f}"
        )
        self.best_name = best_name
        self.second_name = second_name
        self.best_dist = best_dist
        self.second_dist = second_dist


def assign_surface_to_solid(
    surface_centroid: np.ndarray,
    solids: list[SolidCentroids],
    *,
    ambiguity_ratio: float = 0.7,
) -> str | None:
    """Pick the solid whose triangle cloud is nearest to ``surface_centroid``.

    Returns ``None`` if ``solids`` is empty. The "nearest cloud" test
    uses the minimum point-to-cloud distance — robust when patches are
    spatially well-separated (the canonical case for engineering CAD
    where inlet/outlet/walls live on distinct faces of the model).

    Raises ``AmbiguousSurfaceAssignment`` when the best-candidate
    distance is within ``ambiguity_ratio`` of the second-best
    (Codex review R1 MED-1). This catches T-junctions, concentric
    shells, and overlapping near-patches where centroid matching
    could silently mis-assign. The caller is expected to surface this
    as a mesh-generation failure rather than guessing — the engineer
    can then disambiguate via the raw-dict editor or the eventual
    per-triangle voting upgrade.

    ``ambiguity_ratio=0.7`` means "best must be at least 30 % closer
    than second-best"; tuned empirically against the inlet/outlet/walls
    duct cases where best/second-best ratios are ≪ 0.5.
    """
    if not solids:
        return None
    if len(solids) == 1:
        return solids[0].name
    distances: list[tuple[float, str]] = []
    for s in solids:
        d = float(np.linalg.norm(s.centroids - surface_centroid, axis=1).min())
        distances.append((d, s.name))
    distances.sort(key=lambda t: t[0])
    best_dist, best_name = distances[0]
    second_dist, second_name = distances[1]
    # Ratio guard: if best/second ≥ ambiguity_ratio (e.g. 0.7), the
    # call is too close to make confidently. Equality (ratio = 1.0)
    # is the worst case. Identical distances (best = second = 0.0)
    # also tip into ambiguity (ratio undefined → treat as ambiguous).
    if second_dist <= 0.0 or best_dist / second_dist >= ambiguity_ratio:
        raise AmbiguousSurfaceAssignment(
            best_name=best_name,
            second_name=second_name,
            best_dist=best_dist,
            second_dist=second_dist,
        )
    return best_name
