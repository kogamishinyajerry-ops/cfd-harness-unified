"""gmsh API wrapper — open an imported STL, mesh it, write ``.msh``.

The route invokes :func:`run_gmsh_on_imported_case` after M5.0's ingest
step has confirmed the STL is watertight. The function is expected to
raise :class:`GmshMeshGenerationError` on failure; the route maps that
to HTTP 4xx with ``failing_check=gmsh_diverged``.

gmsh's Python API is stateful (a global session). We initialize on
entry, finalize in a ``finally`` block so a failed mesh doesn't leak
state into the next request.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path


class GmshMeshGenerationError(RuntimeError):
    """Raised when gmsh fails to produce a valid 3D mesh."""


@dataclass(frozen=True, slots=True)
class GmshRunResult:
    msh_path: Path
    cell_count: int
    face_count: int
    point_count: int
    characteristic_length_used: float
    generation_time_s: float


def _bbox_diagonal(points: list[tuple[float, float, float]]) -> float:
    if not points:
        return 0.0
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _default_characteristic_length(diagonal: float, mesh_mode: str) -> float:
    """Fallback sizing when the caller doesn't supply ``cell_count_target``.

    Beginner mode aims for a few hundred thousand cells on a typical box
    geometry by setting ``lc ≈ diagonal / 30``. Power mode targets a
    finer mesh (``diagonal / 60``) — still an order of magnitude below
    the 50M hard cap on most geometries.
    """
    if diagonal <= 0:
        # Degenerate input — let gmsh decide. The cap layer will reject
        # if the result is unreasonable.
        return 0.0
    return diagonal / (60.0 if mesh_mode == "power" else 30.0)


def run_gmsh_on_imported_case(
    *,
    stl_path: Path,
    output_msh_path: Path,
    mesh_mode: str = "beginner",
    characteristic_length_override: float | None = None,
) -> GmshRunResult:
    """Mesh ``stl_path`` with gmsh and write ``output_msh_path``.

    The STL is loaded as a triangulated surface, a volume is defined
    from its surfaces, and a 3D unstructured tetrahedral mesh is
    generated. Output is written in MSH format (gmsh native), which
    ``gmshToFoam`` consumes.

    Raises :class:`GmshMeshGenerationError` if gmsh fails or produces
    a zero-element mesh.
    """
    # Deferred import: gmsh is optional (``[workbench]`` extra). Importing
    # at module top would crash the base ``[ui]`` install.
    import gmsh

    if not stl_path.exists():
        raise GmshMeshGenerationError(f"STL not found: {stl_path}")

    output_msh_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    gmsh.initialize()
    try:
        # Quiet logs — gmsh is chatty by default and the route only
        # needs the structured result.
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("General.Verbosity", 1)

        # Merge the STL as a discrete surface. ``Mesh.Algorithm3D = 1``
        # selects gmsh's Delaunay 3D — robust default for closed
        # triangulated surfaces from real-world CAD exports.
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        try:
            gmsh.merge(str(stl_path))
        except Exception as exc:  # noqa: BLE001 — gmsh raises plain Exception
            raise GmshMeshGenerationError(
                f"gmsh failed to load the STL: {exc}"
            ) from exc

        # Reclassify the imported triangles as a surface, then build a
        # volume from the surface loop. This is the standard gmsh
        # incantation for "STL → tetrahedral volume mesh".
        try:
            gmsh.model.mesh.classifySurfaces(
                angle=40.0 * 3.141592653589793 / 180.0,
                boundary=True,
                forReparametrization=True,
                curveAngle=180.0 * 3.141592653589793 / 180.0,
            )
            gmsh.model.mesh.createGeometry()
        except Exception as exc:  # noqa: BLE001 — gmsh raises plain Exception
            raise GmshMeshGenerationError(
                f"gmsh failed to derive geometry from the STL surface: {exc}"
            ) from exc

        surfaces = gmsh.model.getEntities(dim=2)
        if not surfaces:
            raise GmshMeshGenerationError(
                "gmsh found no 2D surfaces after classifying the STL "
                "(likely a corrupt or non-watertight upload that slipped "
                "past M5.0's health check)."
            )
        surface_loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surfaces])
        gmsh.model.geo.addVolume([surface_loop])
        gmsh.model.geo.synchronize()

        # Characteristic length sizing: explicit override > bbox-derived
        # default. The cap layer (cell_budget.py) is the ultimate guard.
        nodes = gmsh.model.mesh.getNodes()
        if nodes and len(nodes) >= 2 and len(nodes[1]) > 0:
            xyz = nodes[1].reshape(-1, 3).tolist()
            diagonal = _bbox_diagonal([(p[0], p[1], p[2]) for p in xyz])
        else:
            diagonal = 0.0

        lc = (
            characteristic_length_override
            if characteristic_length_override is not None
            else _default_characteristic_length(diagonal, mesh_mode)
        )
        if lc > 0:
            gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.5)
            gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)

        try:
            gmsh.model.mesh.generate(3)
        except Exception as exc:  # noqa: BLE001 — gmsh raises plain Exception
            raise GmshMeshGenerationError(
                f"gmsh 3D mesh generation failed: {exc}"
            ) from exc

        # Element type 4 = 4-node tetrahedron in gmsh's element-type
        # numbering. Counting only those keeps the cell_count honest if
        # the model picks up stray surface elements.
        elem_types, elem_tags, _ = gmsh.model.mesh.getElements(dim=3)
        cell_count = sum(len(tags) for et, tags in zip(elem_types, elem_tags) if et == 4)
        if cell_count == 0:
            raise GmshMeshGenerationError(
                "gmsh produced zero 3D tetrahedral elements — meshing "
                "failed to converge on this geometry."
            )

        # Faces (2D elements on the boundary) and points for the summary.
        face_types, face_tags, _ = gmsh.model.mesh.getElements(dim=2)
        face_count = sum(len(tags) for tags in face_tags)
        # Re-fetch nodes — the earlier `nodes` variable was sampled
        # before generate(3) and only reflects the input STL's surface
        # vertices. Reporting the volume-mesh point count is what the
        # UI summary actually wants.
        post_nodes = gmsh.model.mesh.getNodes()
        point_count = len(post_nodes[0]) if post_nodes and len(post_nodes) >= 1 else 0

        gmsh.write(str(output_msh_path))
    finally:
        gmsh.finalize()

    return GmshRunResult(
        msh_path=output_msh_path,
        cell_count=cell_count,
        face_count=face_count,
        point_count=point_count,
        characteristic_length_used=lc if lc > 0 else 0.0,
        generation_time_s=time.monotonic() - t0,
    )
