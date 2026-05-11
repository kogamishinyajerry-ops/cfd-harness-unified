"""gmsh API wrapper — open an imported STL, mesh it, write ``.msh``.

The route invokes :func:`run_gmsh_on_imported_case` after M5.0's ingest
step has confirmed the STL is watertight. The function is expected to
raise :class:`GmshMeshGenerationError` on failure; the route maps that
to HTTP 4xx with ``failing_check=gmsh_diverged``.

gmsh's Python API is stateful (a global session). We initialize on
entry, finalize in a ``finally`` block so a failed mesh doesn't leak
state into the next request.

M-PANELS Step 10 visual-smoke fix: gmsh.initialize() unconditionally
calls ``signal.signal(SIGINT, SIG_DFL)`` which raises
``ValueError: signal only works in main thread of the main interpreter``
when invoked from FastAPI's threadpool (sync route handlers run in
worker threads, not the asyncio main thread). The Python gmsh bindings
expose no flag to skip the signal-handler install. We work around it
by spawning a fresh subprocess for every mesh job: the subprocess gets
its own main thread, gmsh.initialize() succeeds, and the result
crosses back via a ``multiprocessing.Queue``. Process-per-mesh is
acceptable cost-wise — gmsh runs are O(seconds–minutes) and meshing
is already serialized at the route layer (D6: synchronous, threadpool).
"""
from __future__ import annotations

import multiprocessing
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.backend.schemas.mesh_refinement import MeshRefinementZone
    from ui.backend.schemas.mesh_sizing import MeshSizingField


# --- F2 path activation (F-NEW-22 + F-NEW-24 joint mitigation, case_003
# session 6-7 ramp; V36/V37/V41/V45) ---
#
# When the STL is industrial-CAD-scale multi-named-solid (e.g. CRM-HLS
# airframe + farfield boxes from the FreeCAD STEP bridge), the baseline
# classifySurfaces(angle=40°, boundary=True, forReparametrization=True)
# runs super-linear on the boundary flag (O(n²)-ish on facet count) and
# the default Geometry.Tolerance=1e-8 collapses near-coincident cross-
# solid vertices into collinear triangles (gmsh reports them as
# "degenerate" but the STL bytes are clean — see case_003 session 7
# ramp_log).
#
# The fast-classify path:
#   - Geometry.Tolerance=1e-12 preserves Q3-tessellation features
#   - classifySurfaces(angle=180°, boundary=False, forReparametrization=False)
#     runs ~80× faster (case_003: 1.5s vs >120s on 393k facets)
#   - createGeometry() is skipped (impossible without forReparametrization)
#   - Downstream code (partition_surfaces_by_body, named-solid voting,
#     addSurfaceLoop+addVolume) operates on classified surface tags
#     irrespective of parametric vs discrete representation
#
# Trade-off: Mesh.MeshSizeFromCurvature becomes a no-op without
# parametric surfaces. Acceptable for industrial CAD where
# sizing-fields + refinement-zones dominate over curvature-driven
# sizing.
#
# Activation gate: multi-named-solid (≥2) AND total facet count
# ≥ threshold. The threshold protects byte-identity on small test
# fixtures (seamed_multi_solid_box_stl has 12 facets) and small clean
# multi-patch geometries where the baseline path is fast enough.
_F2_PATH_FACET_THRESHOLD = 10_000
_F2_PATH_GEOMETRY_TOLERANCE = 1e-12


def _should_use_f2_path(
    named_solid_count: int,
    facet_count: int,
    *,
    threshold: int = _F2_PATH_FACET_THRESHOLD,
) -> bool:
    """Return True when the F2 fast-classify path should be engaged.

    Gate: ≥2 named solids AND ≥``threshold`` total facets. Below the
    threshold the baseline parametric path is fast and well-tested;
    above it the baseline path's super-linearity + tolerance artifact
    block real industrial CAD payloads (case_003).
    """
    return named_solid_count >= 2 and facet_count >= threshold


class GmshMeshGenerationError(RuntimeError):
    """Raised when gmsh fails to produce a valid 3D mesh."""


class GmshSubprocessError(RuntimeError):
    """Raised when the gmsh child process fails for a non-geometry
    reason (hard crash, ImportError, generic backend fault). The
    pipeline lets this bubble as 5xx — it is NOT a user-geometry
    rejection and must NOT be relabeled as ``gmsh_diverged`` / 422.

    Codex Round 5 P1 + Round 6 P1: distinguishing this from
    ``GmshMeshGenerationError`` is what keeps the route layer's
    "bad geometry vs backend fault" contract intact.
    """


class RefinementZoneError(ValueError):
    """Raised when a DEC-V61-136 refinement zone is invalid against the
    case AABB (no spatial overlap with the geometry, so the gmsh field
    would be a silent no-op). Pipeline maps to
    ``failing_check=refinement_zone_invalid`` (HTTP 422). Distinct from
    ``GmshMeshGenerationError`` so the rejection reason in the response
    points the engineer at the offending zone, not "gmsh diverged".
    """


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


# F-NEW-19 fix (case_003 substrate · 2026-05-11): industrial-plausibility
# range and unit factors for the airframe-class filter, matching
# ``unit_detector.bbox_plausible_units`` semantics. Kept inline here
# rather than imported to avoid cross-service coupling (ADR-001) — this
# is a small, stable contract pair (range + factors).
_INDUSTRIAL_EXTENT_RANGE_M: tuple[float, float] = (0.01, 100.0)
_UNIT_FACTORS_M: tuple[float, ...] = (1e-3, 1e-2, 1.0, 0.0254)  # mm, cm, m, inch


def _is_industrial_plausible_extent(extent: float) -> bool:
    """True iff ``extent`` (raw STL units) is industrial-CFD-plausible
    under at least one common unit (mm/cm/m/inch). Mirrors
    :func:`unit_detector.bbox_plausible_units` but returns a single
    plausibility bit instead of the unit list.
    """
    if extent <= 0:
        return False
    lo_m, hi_m = _INDUSTRIAL_EXTENT_RANGE_M
    for factor in _UNIT_FACTORS_M:
        extent_m = extent * factor
        if lo_m <= extent_m <= hi_m:
            return True
    return False


def _airframe_class_diagonal(
    body_bboxes: list[tuple[float, ...]],
    fallback_diagonal: float,
) -> float:
    """Compute the union-bbox diagonal of airframe-class bodies, filtering
    out CFD-domain-class bodies whose max extent is industrially
    implausible under every common unit.

    F-NEW-19 fix (V198 session 5 · case_003 substrate): when a
    multi-class STEP (airframe + CFD-domain walls) is meshed, the
    overall bbox diagonal is dominated by farfield/symmetry boxes
    (e.g. case_003 raw 2.44 M ≈ 2.44 km if treated as m, far above
    the 100 m industrial cap). The resulting default
    ``lc = diagonal / 30`` is then orders of magnitude coarser than
    the airframe surface tessellation can absorb, and gmsh spends
    unbounded CPU reconciling. Filtering out implausible bodies and
    taking the union bbox of the survivors yields a sensible lc.

    Returns the filtered diagonal, or ``fallback_diagonal`` if the
    filter discards everything (e.g. ship/large-vehicle geometries
    where all bodies legitimately exceed 100 m — see F-NEW-17). When
    no body is filtered out, returns ``fallback_diagonal`` unchanged
    to preserve byte-identical mesh output on single-class loads.
    """
    if not body_bboxes:
        return fallback_diagonal
    kept_bboxes: list[tuple[float, ...]] = []
    for bbox in body_bboxes:
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        max_extent = max(xmax - xmin, ymax - ymin, zmax - zmin)
        if _is_industrial_plausible_extent(max_extent):
            kept_bboxes.append(bbox)
    if not kept_bboxes:
        # All bodies industrially implausible — let the caller fall back
        # to the full diagonal rather than producing a zero lc.
        return fallback_diagonal
    if len(kept_bboxes) == len(body_bboxes):
        # No body filtered out — preserve byte-identical behavior on
        # single-class loads by returning the full diagonal exactly.
        return fallback_diagonal
    xmin = min(b[0] for b in kept_bboxes)
    ymin = min(b[1] for b in kept_bboxes)
    zmin = min(b[2] for b in kept_bboxes)
    xmax = max(b[3] for b in kept_bboxes)
    ymax = max(b[4] for b in kept_bboxes)
    zmax = max(b[5] for b in kept_bboxes)
    dx = xmax - xmin
    dy = ymax - ymin
    dz = zmax - zmin
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _geometry_aabb(
    points: list[tuple[float, float, float]]
) -> tuple[float, float, float, float, float, float] | None:
    """Compute axis-aligned bounding box from gmsh node coordinates.

    Returns ``(xmin, ymin, zmin, xmax, ymax, zmax)`` or ``None`` for
    degenerate input (no points). Used by DEC-V61-136 (N2.2) refinement-
    zone validation: a zone whose bbox/sphere has zero overlap with the
    geometry AABB would produce a silent no-op gmsh field.
    """
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def _box_intersects_aabb(
    bbox: list[float],
    aabb: tuple[float, float, float, float, float, float],
) -> bool:
    """True if axis-aligned ``bbox`` (xmin..zmax) intersects geometry
    ``aabb``. Uses standard separating-axis check (any-axis disjoint =
    no intersection).
    """
    xmin, ymin, zmin, xmax, ymax, zmax = bbox
    a_xmin, a_ymin, a_zmin, a_xmax, a_ymax, a_zmax = aabb
    return not (
        xmax < a_xmin
        or xmin > a_xmax
        or ymax < a_ymin
        or ymin > a_ymax
        or zmax < a_zmin
        or zmin > a_zmax
    )


def _sphere_intersects_aabb(
    center: list[float],
    radius: float,
    aabb: tuple[float, float, float, float, float, float],
) -> bool:
    """True if sphere intersects geometry AABB. Standard "closest point
    on AABB to sphere center within radius" test.
    """
    cx, cy, cz = center[0], center[1], center[2]
    a_xmin, a_ymin, a_zmin, a_xmax, a_ymax, a_zmax = aabb
    dx = max(a_xmin - cx, 0.0, cx - a_xmax)
    dy = max(a_ymin - cy, 0.0, cy - a_ymax)
    dz = max(a_zmin - cz, 0.0, cz - a_zmax)
    return (dx * dx + dy * dy + dz * dz) <= (radius * radius)


def _validate_refinement_zones(
    zones: list[dict],
    aabb: tuple[float, float, float, float, float, float] | None,
) -> None:
    """Raise :class:`RefinementZoneError` on the first zone that has
    zero overlap with the geometry AABB. Pure validation — does not
    mutate gmsh state. Pydantic has already enforced shape (positive
    extents, level in 1..3, etc.); this layer covers the geometric
    "is this zone meaningful for THIS geometry" check.
    """
    if not zones or aabb is None:
        return
    for idx, zone in enumerate(zones):
        geom = zone.get("geometry")
        if geom == "box":
            if not _box_intersects_aabb(zone["bbox"], aabb):
                raise RefinementZoneError(
                    f"refinement_zones[{idx}] (box) bbox={zone['bbox']} "
                    f"has no overlap with case AABB={list(aabb)}; "
                    "the gmsh field would be a no-op."
                )
        elif geom == "sphere":
            if not _sphere_intersects_aabb(
                zone["center"], float(zone["radius"]), aabb
            ):
                raise RefinementZoneError(
                    f"refinement_zones[{idx}] (sphere) center="
                    f"{zone['center']} radius={zone['radius']} has no "
                    f"overlap with case AABB={list(aabb)}; the gmsh "
                    "field would be a no-op."
                )
        else:
            # Schema layer guards this; defensive backstop only.
            raise RefinementZoneError(
                f"refinement_zones[{idx}] has unknown geometry={geom!r}"
            )


def _lc_from_target_cell_count(diagonal: float, target_cell_count: int) -> float:
    """DEC-V61-124: convert an AI-proposed cell-count target to a
    characteristic length using a cube approximation.

    Derivation (see DEC-V61-124 §"Why this formula"):
      * tetrahedral mesh of bbox volume V with characteristic length lc
        produces ~6 × V / lc**3 cells
      * for a cube of side s and diagonal d = s × sqrt(3), V = (d/sqrt(3))**3
      * therefore lc ≈ d × (1.155 / N)**(1/3) ≈ d × 1.05 / N**(1/3)

    Calibrated to match beginner (d/30 → ~30k cells) and power
    (d/60 → ~250k cells) presets within 1.5% on a unit cube.
    Real-world non-cube geometries diverge from this approximation by
    up to ±50%; the cell_budget guard catches gross overshoots.

    Returns 0.0 for degenerate diagonals so the caller falls back to
    gmsh's default sizing.
    """
    if diagonal <= 0 or target_cell_count <= 0:
        return 0.0
    return diagonal * 1.05 / (target_cell_count ** (1.0 / 3.0))


def _gmsh_inline(
    *,
    stl_path: Path,
    output_msh_path: Path,
    mesh_mode: str,
    characteristic_length_override: float | None,
    target_cell_count: int | None = None,
    sizing_field: dict | None = None,
    refinement_zones: list[dict] | None = None,
) -> GmshRunResult:
    """The original gmsh-API meshing logic. Runs in a subprocess so
    ``gmsh.initialize()``'s ``signal.signal()`` call lands on a fresh
    main thread — see module docstring.
    """
    # Deferred import: gmsh is optional (``[workbench]`` extra). Importing
    # at module top would crash the base ``[ui]`` install.
    import gmsh

    # Codex Round 7 P2: a missing STL is a filesystem / operator fault,
    # not a user-geometry fault. Surface as FileNotFoundError (⊂ OSError)
    # so the wrapper marshals it as 'os_error' → 5xx, NOT as
    # GmshMeshGenerationError → gmsh_diverged → 422.
    if not stl_path.exists():
        raise FileNotFoundError(f"STL not found: {stl_path}")

    output_msh_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    # F2 path pre-merge probe (V45): parse STL for named-solid count +
    # facet count BEFORE gmsh.initialize() so we can decide whether to
    # set Geometry.Tolerance ahead of merge. parse_named_solids_from_path
    # is a sub-second regex parse, cheap even on 80 MB STLs.
    from .stl_solid_index import parse_named_solids_from_path

    _f2_named_solids_preview = parse_named_solids_from_path(stl_path)
    _f2_facet_count_preview = sum(
        s.centroids.shape[0] for s in _f2_named_solids_preview
    )
    _f2_active = _should_use_f2_path(
        named_solid_count=len(_f2_named_solids_preview),
        facet_count=_f2_facet_count_preview,
    )

    gmsh.initialize()
    # Wrap the entire post-init gmsh-API region in a single
    # GmshMeshGenerationError boundary. The gmsh Python bindings raise
    # plain `Exception` at many call sites (merge / classifySurfaces /
    # addSurfaceLoop / addVolume / synchronize / generate /
    # getEntities / getElements / write); per-call wrappers proved
    # brittle (Codex round-3 caught merge/classify/generate, round-4
    # caught synchronize). One outer boundary covers all of them
    # without losing the GmshMeshGenerationError contract.
    try:
        try:
            # Quiet logs — gmsh is chatty by default and the route only
            # needs the structured result.
            gmsh.option.setNumber("General.Terminal", 0)
            gmsh.option.setNumber("General.Verbosity", 1)

            # M-PANELS Step 10 visual-smoke fix: force gmsh's legacy MSH
            # format 2.2 output. gmsh defaults to format 4.1, but
            # OpenFOAM 10's gmshToFoam parses only up to 2.x reliably
            # ("Attempt to get back from bad stream" on 4.x ASCII files).
            # Format 2.2 is the lingua franca every gmshToFoam version
            # accepts.
            gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)

            # Merge the STL as a discrete surface. ``Mesh.Algorithm3D = 1``
            # selects gmsh's Delaunay 3D — robust default for closed
            # triangulated surfaces from real-world CAD exports.
            gmsh.option.setNumber("Mesh.Algorithm3D", 1)

            # F2 path (F-NEW-24 mitigation): tighten Geometry.Tolerance
            # BEFORE gmsh.merge so cross-solid vertex dedup uses an
            # absolute tolerance well below Q3 STL deflection. Default
            # 1e-8 collapses Q3 features on km-scale industrial CAD.
            if _f2_active:
                gmsh.option.setNumber(
                    "Geometry.Tolerance", _F2_PATH_GEOMETRY_TOLERANCE
                )
            # NOTE: Codex R11 Finding 1 suggested wrapping gmsh.merge()
            # to relabel plain-Exception failures as OSError when the
            # STL still exists (host read-side faults on a permission-
            # denied mount). REJECTED on review: this conflicts with
            # the R2/R3 architectural contract documented in
            # test_gmsh_runner_normalizes_raw_binding_exception —
            # gmsh.merge plain Exception is the canonical signal for
            # "STL geometry is unparseable / malformed", which is the
            # geometry-rejection 4xx the route layer expects. Real
            # OSError from the underlying read is already caught by
            # the explicit `except OSError` boundary below; only
            # gmsh's binding-wrapped re-raises reach the catch-all,
            # and those are dominantly geometry-side, not host-side.
            gmsh.merge(str(stl_path))

            # Reclassify the imported triangles as a surface, then build
            # a volume from the surface loop. Standard gmsh incantation
            # for "STL → tetrahedral volume mesh".
            #
            # F2 path (F-NEW-22 mitigation, V36/V37): on industrial-scale
            # multi-named-solid loads, the baseline (angle=40°,
            # boundary=True, forReparametrization=True) is super-linear
            # in facet count. The fast variant (angle=180°, boundary=False,
            # forReparametrization=False) is ~80× faster on 393k facets
            # and produces classified surface tags that the downstream
            # named-solid voting + topology partition code accepts. The
            # cost: createGeometry() cannot be called without
            # forReparametrization=True, so we skip it on the F2 path.
            if _f2_active:
                gmsh.model.mesh.classifySurfaces(
                    angle=180.0 * 3.141592653589793 / 180.0,
                    boundary=False,
                    forReparametrization=False,
                    curveAngle=180.0 * 3.141592653589793 / 180.0,
                )
                # createGeometry() deliberately omitted on F2 path.
            else:
                gmsh.model.mesh.classifySurfaces(
                    angle=40.0 * 3.141592653589793 / 180.0,
                    boundary=True,
                    forReparametrization=True,
                    curveAngle=180.0 * 3.141592653589793 / 180.0,
                )
                gmsh.model.mesh.createGeometry()

            surfaces = gmsh.model.getEntities(dim=2)
            if not surfaces:
                raise GmshMeshGenerationError(
                    "gmsh found no 2D surfaces after classifying the STL "
                    "(likely a corrupt or non-watertight upload that slipped "
                    "past M5.0's health check)."
                )

            # DEC-V61-104 Phase 1: partition surfaces by topological body
            # so interior obstacles (turbine blades, valve seats,
            # instrument probes) become holes in the fluid volume rather
            # than getting tetrahedralized as fluid cells.
            #
            # Single-body geometries (LDC, channel, naca0012, cylinder)
            # fall through to the single-loop path so byte-identical
            # mesh output is preserved.
            from .topology import (
                TopologyPartitionError,
                partition_surfaces_by_body,
            )

            try:
                bodies = partition_surfaces_by_body(gmsh, surfaces)
            except TopologyPartitionError as exc:
                # Codex post-merge MED guard: disconnected exterior
                # shells, not interior obstacles. Surface as a 4xx-class
                # mesh failure with a clear message rather than silently
                # corrupting the geometry.
                raise GmshMeshGenerationError(
                    f"topology partition rejected the STL: {exc}"
                ) from exc
            if len(bodies) <= 1:
                surface_loop = gmsh.model.geo.addSurfaceLoop(
                    [s[1] for s in surfaces]
                )
                gmsh.model.geo.addVolume([surface_loop])
            else:
                # bodies[0] is the outer (largest bbox + verified to
                # contain all others); the rest are interior obstacles.
                # Each inner loop is negated in the addVolume call so
                # gmsh treats it as a hole rather than a second fluid
                # region. (Note: gmsh's geo-kernel hole subtraction is
                # unreliable for thin obstacles — see
                # tools/adversarial/results/iter01_v61_104_phase1_partial_findings.md
                # for the Phase 1.5 follow-up scope.)
                outer_loop = gmsh.model.geo.addSurfaceLoop(bodies[0])
                inner_loops = [
                    gmsh.model.geo.addSurfaceLoop(body) for body in bodies[1:]
                ]
                gmsh.model.geo.addVolume(
                    [outer_loop] + [-loop for loop in inner_loops]
                )
            gmsh.model.geo.synchronize()

            # Adversarial-loop iter02 fix (defect 2a): re-attach STL
            # ``solid <name>`` identity to the post-classify parametric
            # surfaces. Without this, gmshToFoam writes a single
            # ``patch0`` for every multi-patch CAD import — the named
            # inlet/outlet/walls metadata that the engineer encoded in
            # the STL evaporates between merge() and write(). For each
            # parametric surface we compute a representative centroid
            # from its mesh nodes (still the original STL triangles at
            # this point — generate(3) hasn't run yet) and match to the
            # nearest STL solid's centroid cloud. Surfaces sharing a
            # solid name are grouped under one PhysicalGroup so
            # gmshToFoam emits one Foam patch per named solid.
            from .stl_solid_index import (
                AmbiguousSurfaceAssignment,
                assign_surface_to_solid_by_voting,
                parse_named_solids_from_path,
            )

            named_solids = parse_named_solids_from_path(stl_path)
            if named_solids:
                surfaces_by_name: dict[str, list[int]] = {}
                # Codex review R1 MED-2: completeness check. When
                # named-solid mode is active, every classified
                # parametric surface MUST resolve to one of the
                # source solids — otherwise that surface's triangles
                # silently disappear from MSH 2.2 export (gmsh's
                # implicit "physical groups exist → drop untagged
                # elements" behavior) and gmshToFoam emits a
                # boundary file missing whole patches. Track
                # unassigned surfaces and raise instead of falling
                # through.
                #
                # Adversarial iter04 (L-bend) upgrade: switched from
                # single-centroid match to per-triangle voting. The
                # L-bend's walls patch extends close to the inlet
                # end-cap, and the single-point centroid match would
                # fire the ambiguity threshold even though majority
                # of triangles in each parametric surface clearly
                # belong to one source solid. Voting handles the
                # mixed-source case correctly.
                unassigned: list[int] = []
                import numpy as _np

                for _dim, tag in surfaces:
                    elem_types, elem_tags_list, node_tags_list = (
                        gmsh.model.mesh.getElements(dim=2, tag=tag)
                    )
                    if not node_tags_list or len(node_tags_list[0]) == 0:
                        unassigned.append(tag)
                        continue
                    # DEC-V61-105 Phase 2.4 defensive check #1:
                    # surface element-type guard. The voting block
                    # below consumes ``node_tags_list[0]`` as a flat
                    # 3N-node array assuming Triangle3 (gmsh element
                    # type 2). A higher-order surface element
                    # (Triangle6 = type 9, Quad4 = 3, Quad8 = 16,
                    # etc.) would silently misinterpret the array —
                    # Triangle6 reads as 2× the actual count with
                    # wrong centroids, leading to wrong patch
                    # assignments without any surfaced error. Current
                    # pipeline only emits Triangle3 (Mesh.Algorithm3D
                    # = 1 over STL input), so this guard is
                    # forward-looking for the Phase 2.3 parametric
                    # generator and any future curved/higher-order
                    # branch. Raise loudly rather than silently
                    # misinterpret.
                    non_triangle3 = [
                        int(et) for et in elem_types if int(et) != 2
                    ]
                    if non_triangle3:
                        raise GmshMeshGenerationError(
                            f"named-solid voting requires Triangle3 "
                            f"(gmsh element type 2) surface elements; "
                            f"parametric surface tag={tag} reported "
                            f"types={[int(et) for et in elem_types]} "
                            f"(unsupported: {non_triangle3}). The "
                            f"per-triangle voting block assumes "
                            f"Triangle3 row-major node arrays — "
                            f"re-mesh with Mesh.ElementOrder=1 + "
                            f"Mesh.SecondOrderIncomplete=0, or extend "
                            f"the voting block to handle higher-order "
                            f"elements."
                        )
                    # Build per-triangle centroids. node_tags_list[0]
                    # is a flat array; triangle elements use 3 nodes
                    # each, in row-major order.
                    flat_nodes = node_tags_list[0]
                    # DEC-V61-105 Phase 2.4 defensive check #2:
                    # malformed Triangle3 node array guard. Each
                    # Triangle3 emits exactly 3 node tags; a flat
                    # array length not divisible by 3 means gmsh
                    # returned a corrupted/truncated payload (partial
                    # element write mid-iteration, plugin-induced
                    # inconsistency, binding-version mismatch).
                    # Without this guard ``len(flat_nodes) // 3``
                    # silently drops the truncated remainder and the
                    # loop iterates over only the well-formed prefix.
                    #
                    # Codex R1 P2 (V61-105 Phase 2.4): this is a
                    # BACKEND fault (binding/version mismatch /
                    # internal corruption), not a user-geometry
                    # fault. Raising GmshMeshGenerationError would
                    # map to ``gmsh_diverged`` / HTTP 422 and falsely
                    # blame the operator's STL. Raise OSError
                    # instead so the existing ``except OSError:
                    # raise`` boundary at the catch-all layer (and
                    # the ``os_error`` queue kind in
                    # _subprocess_target) carries it through as 5xx,
                    # matching the project's "backend/host fault →
                    # 5xx, never relabeled as bad-geometry" contract
                    # already enforced for disk-full / permission
                    # failures.
                    if len(flat_nodes) % 3 != 0:
                        raise OSError(
                            f"gmsh returned a malformed Triangle3 "
                            f"node array on parametric surface "
                            f"tag={tag}: length {len(flat_nodes)} "
                            f"not divisible by 3. This indicates a "
                            f"corrupted or truncated gmsh element "
                            f"payload (binding/version mismatch or "
                            f"internal inconsistency) — re-run "
                            f"meshing or report as a gmsh-binding "
                            f"bug."
                        )
                    n_tri = len(flat_nodes) // 3
                    if n_tri == 0:
                        unassigned.append(tag)
                        continue
                    # Cache node coords; many triangles share nodes.
                    node_coord_cache: dict[int, list[float]] = {}
                    tri_centroids: list[list[float]] = []
                    tri_areas: list[float] = []
                    for i in range(n_tri):
                        n0, n1, n2 = (
                            int(flat_nodes[3 * i]),
                            int(flat_nodes[3 * i + 1]),
                            int(flat_nodes[3 * i + 2]),
                        )
                        coords = []
                        for nid in (n0, n1, n2):
                            if nid not in node_coord_cache:
                                c, _, _, _ = gmsh.model.mesh.getNode(nid)
                                node_coord_cache[nid] = [c[0], c[1], c[2]]
                            coords.append(node_coord_cache[nid])
                        a, b, c = coords[0], coords[1], coords[2]
                        tri_centroids.append(
                            [
                                (a[0] + b[0] + c[0]) / 3.0,
                                (a[1] + b[1] + c[1]) / 3.0,
                                (a[2] + b[2] + c[2]) / 3.0,
                            ]
                        )
                        # Triangle area = 0.5 * |(b - a) x (c - a)|.
                        # Codex post-merge finding (defect-5 follow-up):
                        # area-weighted voting prevents skewed triangle
                        # distributions (many tiny refined triangles
                        # along an edge) from outvoting fewer large
                        # triangles that represent the true patch face.
                        u0, u1, u2 = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                        v0, v1, v2 = c[0] - a[0], c[1] - a[1], c[2] - a[2]
                        cx = u1 * v2 - u2 * v1
                        cy = u2 * v0 - u0 * v2
                        cz = u0 * v1 - u1 * v0
                        tri_areas.append(
                            0.5 * (cx * cx + cy * cy + cz * cz) ** 0.5
                        )
                    centroids_arr = _np.asarray(tri_centroids, dtype=float)
                    areas_arr = _np.asarray(tri_areas, dtype=float)
                    try:
                        name = assign_surface_to_solid_by_voting(
                            centroids_arr,
                            named_solids,
                            triangle_areas=areas_arr,
                        )
                    except AmbiguousSurfaceAssignment as exc:
                        # MED-1 ambiguity guard. Surface as a mesh
                        # generation failure so the engineer sees a
                        # 422 with a structured error and can decide
                        # to disambiguate via raw-dict editor or
                        # re-export the STL with cleaner solid
                        # boundaries.
                        raise GmshMeshGenerationError(
                            f"named-solid patch assignment ambiguous on "
                            f"parametric surface {tag}: {exc}"
                        ) from exc
                    if name is None:
                        unassigned.append(tag)
                        continue
                    surfaces_by_name.setdefault(name, []).append(tag)
                if unassigned:
                    raise GmshMeshGenerationError(
                        f"named-solid mode failed to assign "
                        f"{len(unassigned)} classified surface(s) to a "
                        f"source solid; surface tags={unassigned}. This "
                        f"would silently drop boundary triangles from "
                        f"MSH export — re-author the STL with cleaner "
                        f"per-patch surfaces or use single-solid mode."
                    )
                for name, tags in surfaces_by_name.items():
                    pg_tag = gmsh.model.addPhysicalGroup(2, tags)
                    gmsh.model.setPhysicalName(2, pg_tag, name)
                # gmsh's MSH 2.2 export only writes elements that
                # belong to a physical group when any physical group
                # exists; ``Mesh.SaveAll=1`` is meant to override that
                # but in practice it also strips the per-element
                # physical tags, leaving gmshToFoam with no
                # patch information. The robust workaround is to add
                # a physical group for the volume too, so every
                # element gets a non-zero tag through export. The
                # name is internal-only (gmshToFoam treats dim=3
                # physical groups as cellZones, not patches).
                volume_entities = gmsh.model.getEntities(dim=3)
                if volume_entities:
                    vol_pg = gmsh.model.addPhysicalGroup(
                        3, [t for _d, t in volume_entities]
                    )
                    gmsh.model.setPhysicalName(3, vol_pg, "fluid")

            # Characteristic length sizing: explicit override >
            # bbox-derived default. The cap layer (cell_budget.py) is
            # the ultimate guard.
            nodes = gmsh.model.mesh.getNodes()
            if nodes and len(nodes) >= 2 and len(nodes[1]) > 0:
                xyz = nodes[1].reshape(-1, 3).tolist()
                point_tuples = [(p[0], p[1], p[2]) for p in xyz]
                diagonal = _bbox_diagonal(point_tuples)
                geometry_aabb = _geometry_aabb(point_tuples)
            else:
                diagonal = 0.0
                geometry_aabb = None

            # F-NEW-19 fix (V198 session 5 · case_003 substrate): when
            # multi-class STEP (airframe + CFD-domain walls) lands here,
            # the overall ``diagonal`` is dominated by domain walls and
            # default ``lc = diagonal / 30`` runs unworkably coarse for
            # the airframe surface. Filter out industrially-implausible
            # bodies and recompute the diagonal from the airframe-class
            # union when applicable. Single-class loads (all bodies
            # plausible OR all implausible) return ``diagonal`` unchanged,
            # preserving byte-identical mesh output.
            if len(bodies) > 1:
                from .topology import _body_bbox
                body_bboxes = [_body_bbox(gmsh, body) for body in bodies]
                diagonal = _airframe_class_diagonal(body_bboxes, diagonal)

            # V136 (N2.2): validate refinement zones BEFORE expensive
            # 3D mesh generation. Pydantic already enforced shape;
            # this layer covers spatial overlap with the case AABB.
            # An out-of-domain zone would produce a silent no-op gmsh
            # field, which the engineer would only catch by inspecting
            # the resulting mesh — failing fast here is friendlier.
            if refinement_zones:
                _validate_refinement_zones(refinement_zones, geometry_aabb)

            # V135 (N2.1): sizing_field > target_cell_count >
            # characteristic_length_override > preset-derived default.
            # The cell_budget guard (cell_budget.py) is the ultimate
            # cap regardless of which path supplied lc.
            sf = sizing_field or {}
            sf_active = any(sf.get(k) is not None for k in (
                "base_lc", "min_lc", "max_lc",
                "curvature_target_size", "proximity_layers",
            ))
            if sf_active:
                # base_lc (or fallback to preset) drives the nominal lc;
                # min_lc / max_lc override the ±0.5x default bounds.
                base = sf.get("base_lc")
                if base is None:
                    base = _default_characteristic_length(diagonal, mesh_mode)
                lc = base if base and base > 0 else 0.0
                lc_min = sf.get("min_lc") if sf.get("min_lc") is not None else (lc * 0.5 if lc > 0 else 0.0)
                lc_max = sf.get("max_lc") if sf.get("max_lc") is not None else lc
                # Codex R0 P2 #1: schema-level ordering check only fires
                # when the engineer supplied both endpoints. With a
                # one-sided field (e.g. only max_lc set) the missing
                # bound is derived from the preset fallback, which can
                # invert the range. Re-check after the merge so the
                # gmsh options are never inverted.
                if (
                    lc_min is not None
                    and lc_max is not None
                    and lc_min > 0
                    and lc_max > 0
                    and lc_min > lc_max
                ):
                    raise GmshMeshGenerationError(
                        "sizing_field produces inverted gmsh range "
                        f"(min={lc_min}, max={lc_max}) after merging "
                        "with preset fallback. Supply base_lc or both "
                        "min_lc/max_lc explicitly."
                    )
                if lc_min and lc_min > 0:
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc_min)
                if lc_max and lc_max > 0:
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc_max)
                if sf.get("curvature_target_size") is not None:
                    # gmsh option semantics: target N elements per 2π of
                    # curvature radius. The schema field name uses
                    # "_target_size" loosely — in gmsh terminology this
                    # is "MeshSizeFromCurvature" (an integer angle-quotient).
                    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", float(sf["curvature_target_size"]))
                if sf.get("proximity_layers") is not None:
                    gmsh.option.setNumber("Mesh.MeshSizeFromBoundary", 1)
                    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", int(sf["proximity_layers"]))
            else:
                if target_cell_count is not None:
                    lc = _lc_from_target_cell_count(diagonal, target_cell_count)
                elif characteristic_length_override is not None:
                    lc = characteristic_length_override
                else:
                    lc = _default_characteristic_length(diagonal, mesh_mode)
                if lc > 0:
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMin", lc * 0.5)
                    gmsh.option.setNumber("Mesh.CharacteristicLengthMax", lc)

            # V136 (N2.2): refinement-zone gmsh fields. Each zone gets
            # its own Box/Ball field with VIn = effective_lc / 2**level
            # and VOut = effective_lc (no-op outside zone). All zone
            # fields are combined into a Min field that we register as
            # the background mesh; gmsh then takes the minimum of the
            # background field and the global CharacteristicLengthMin/Max
            # bounds set above. The cell_budget guard remains the
            # ultimate cap regardless of how many zones the engineer
            # supplies.
            if refinement_zones:
                # Effective lc to scale zone VIn against. Sizing-field
                # branch tracks lc_max; preset branch tracks lc. Use
                # the larger of the two as the "outside-zone" baseline
                # so VOut never accidentally tightens the global bound.
                if sf_active:
                    base_for_zones = lc_max if lc_max and lc_max > 0 else (lc if lc > 0 else 0.0)
                else:
                    base_for_zones = lc if lc > 0 else 0.0
                if base_for_zones <= 0:
                    # Degenerate fallback: gmsh's default sizing wins.
                    # Still apply zones with a synthesized scale derived
                    # from the geometry diagonal so the field is
                    # meaningful instead of zero-valued.
                    base_for_zones = diagonal / 30.0 if diagonal > 0 else 1.0

                zone_field_tags: list[int] = []
                for zone in refinement_zones:
                    geom = zone.get("geometry")
                    level = int(zone.get("level", 1))
                    # 2**(-level) — keep in sync with
                    # mesh_refinement.lc_scale_for_level for parity with
                    # the schema's documented mapping.
                    v_in = base_for_zones * (2.0 ** (-level))
                    v_out = base_for_zones
                    if geom == "box":
                        tag = gmsh.model.mesh.field.add("Box")
                        gmsh.model.mesh.field.setNumber(tag, "VIn", v_in)
                        gmsh.model.mesh.field.setNumber(tag, "VOut", v_out)
                        bbox = zone["bbox"]
                        gmsh.model.mesh.field.setNumber(tag, "XMin", float(bbox[0]))
                        gmsh.model.mesh.field.setNumber(tag, "YMin", float(bbox[1]))
                        gmsh.model.mesh.field.setNumber(tag, "ZMin", float(bbox[2]))
                        gmsh.model.mesh.field.setNumber(tag, "XMax", float(bbox[3]))
                        gmsh.model.mesh.field.setNumber(tag, "YMax", float(bbox[4]))
                        gmsh.model.mesh.field.setNumber(tag, "ZMax", float(bbox[5]))
                        # Soft transition shell: smooth ramp from VIn to
                        # VOut over a thickness equal to v_in (one zone-
                        # interior cell). Without this, gmsh produces a
                        # hard size discontinuity at the box face that
                        # often causes mesher-quality warnings on the
                        # boundary tetrahedra.
                        gmsh.model.mesh.field.setNumber(tag, "Thickness", v_in)
                        zone_field_tags.append(tag)
                    elif geom == "sphere":
                        tag = gmsh.model.mesh.field.add("Ball")
                        gmsh.model.mesh.field.setNumber(tag, "VIn", v_in)
                        gmsh.model.mesh.field.setNumber(tag, "VOut", v_out)
                        center = zone["center"]
                        gmsh.model.mesh.field.setNumber(tag, "XCenter", float(center[0]))
                        gmsh.model.mesh.field.setNumber(tag, "YCenter", float(center[1]))
                        gmsh.model.mesh.field.setNumber(tag, "ZCenter", float(center[2]))
                        gmsh.model.mesh.field.setNumber(tag, "Radius", float(zone["radius"]))
                        gmsh.model.mesh.field.setNumber(tag, "Thickness", v_in)
                        zone_field_tags.append(tag)
                    # Unknown geometry already rejected by
                    # _validate_refinement_zones above.

                if zone_field_tags:
                    # Combine all zone fields into a single Min field —
                    # gmsh evaluates each at every spatial point and
                    # uses the minimum, so overlapping zones compose
                    # naturally (deepest level wins in the overlap).
                    min_tag = gmsh.model.mesh.field.add("Min")
                    gmsh.model.mesh.field.setNumbers(
                        min_tag, "FieldsList", [float(t) for t in zone_field_tags]
                    )
                    gmsh.model.mesh.field.setAsBackgroundMesh(min_tag)

            gmsh.model.mesh.generate(3)

            # Element type 4 = 4-node tetrahedron in gmsh's element-type
            # numbering. Counting only those keeps the cell_count honest
            # if the model picks up stray surface elements.
            elem_types, elem_tags, _ = gmsh.model.mesh.getElements(dim=3)
            cell_count = sum(len(tags) for et, tags in zip(elem_types, elem_tags) if et == 4)
            if cell_count == 0:
                raise GmshMeshGenerationError(
                    "gmsh produced zero 3D tetrahedral elements — meshing "
                    "failed to converge on this geometry."
                )

            # Faces (2D elements on the boundary) and points for the
            # summary. Re-fetch nodes after generate(3) so point_count
            # reflects the volume mesh, not the input STL surface.
            face_types, face_tags, _ = gmsh.model.mesh.getElements(dim=2)
            face_count = sum(len(tags) for tags in face_tags)
            post_nodes = gmsh.model.mesh.getNodes()
            point_count = len(post_nodes[0]) if post_nodes and len(post_nodes) >= 1 else 0

            # Codex R10 Finding 1: gmsh.write() can raise plain Exception
            # for write-time backend faults (most importantly ENOSPC /
            # disk-full) where os.access(W_OK) and dir-existence still
            # report OK. Falling through to the generic catch-all below
            # would relabel that as GmshMeshGenerationError → 4xx
            # geometry rejection — the exact misclassification this
            # chain is closing. Wrap gmsh.write() in its own try/except
            # so any write-time failure surfaces as OSError (5xx) before
            # the geometry-side catch-all sees it.
            try:
                gmsh.write(str(output_msh_path))
            except OSError:
                raise
            except Exception as exc:  # noqa: BLE001 — gmsh write raises plain Exception
                output_dir = output_msh_path.parent
                if not output_dir.exists():
                    raise FileNotFoundError(
                        f"output directory disappeared during gmsh.write: {output_dir}"
                    ) from exc
                raise OSError(
                    f"gmsh.write failed for {output_msh_path} (likely disk-full / "
                    f"permission / I/O error): {exc}"
                ) from exc
        except RefinementZoneError:
            # V136 (N2.2): zone-validation rejection must escape the
            # generic gmsh-API catch-all below, otherwise it would be
            # relabeled as GmshMeshGenerationError → gmsh_diverged
            # and the engineer would lose the structured zone-index +
            # AABB diagnostic.
            raise
        except GmshMeshGenerationError:
            raise
        except OSError:
            # Disk-full / permission-denied / read-only filesystem from
            # gmsh.write() or any other I/O. These are backend / host
            # faults, not user-geometry rejections — let them bubble
            # as 5xx so operators see the real cause.
            raise
        except Exception as exc:  # noqa: BLE001 — gmsh bindings raise plain Exception
            # Codex R8 Finding 1 + R9 Finding 1: gmsh's bindings raise
            # plain ``Exception`` for both geometry-level failures AND
            # for I/O failures (input STL vanished, output dir not
            # writable, disk full at gmsh.write time). The catch-all
            # used to relabel everything as GmshMeshGenerationError →
            # gmsh_diverged / 422, which silently 4xx-relabels host
            # faults as user-geometry rejections.
            #
            # Discriminate via filesystem reality: if the input STL
            # is gone or the output directory is non-writable, that
            # is the actual cause. Surface as OSError so the wrapper
            # marshals it as ``os_error`` → 5xx. Otherwise the gmsh
            # failure was geometry-side and the GmshMeshGenerationError
            # relabel is correct.
            if not stl_path.exists():
                raise FileNotFoundError(
                    f"STL disappeared during gmsh meshing: {stl_path}"
                ) from exc
            output_dir = output_msh_path.parent
            if not output_dir.exists() or not os.access(output_dir, os.W_OK):
                raise OSError(
                    f"output directory not writable for gmsh.write: {output_dir}"
                ) from exc
            raise GmshMeshGenerationError(
                f"gmsh API failure during mesh generation: {exc}"
            ) from exc
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


def _subprocess_target(
    stl_path_str: str,
    output_msh_path_str: str,
    mesh_mode: str,
    characteristic_length_override: float | None,
    target_cell_count: int | None,
    sizing_field: dict | None,
    refinement_zones: list[dict] | None,
    queue: "multiprocessing.Queue[tuple[str, object]]",
) -> None:
    """Run the gmsh meshing job inside a child process and post back the
    serialized result (or error) on ``queue``. Top-level so it can be
    pickled by the 'spawn' start method on macOS.

    Error-kind dispatch matters: the parent translates 'gmsh_error' to
    GmshMeshGenerationError (user-geometry fault → 422), but every
    backend/setup fault must surface as something OTHER than
    GmshMeshGenerationError so the pipeline routes it as 5xx. Codex
    Round 5 P1: a missing ``gmsh`` install, child-bootstrap failure,
    or similar backend fault must NOT be reported as "bad geometry".

    V136 (N2.2): adds 'refinement_zone_error' kind so an out-of-domain
    zone surfaces as failing_check=refinement_zone_invalid (422) rather
    than getting collapsed into gmsh_diverged.
    """
    try:
        result = _gmsh_inline(
            stl_path=Path(stl_path_str),
            output_msh_path=Path(output_msh_path_str),
            mesh_mode=mesh_mode,
            characteristic_length_override=characteristic_length_override,
            target_cell_count=target_cell_count,
            sizing_field=sizing_field,
            refinement_zones=refinement_zones,
        )
        # asdict() handles the Path → str translation for the dataclass
        # via a custom default factory; do it explicitly for safety.
        payload = asdict(result)
        payload["msh_path"] = str(payload["msh_path"])
        queue.put(("ok", payload))
    except RefinementZoneError as exc:
        queue.put(("refinement_zone_error", str(exc)))
    except GmshMeshGenerationError as exc:
        queue.put(("gmsh_error", str(exc)))
    except ImportError as exc:
        # ModuleNotFoundError ⊂ ImportError. gmsh missing from the
        # [workbench] extra is a deployment fault, not user geometry.
        queue.put(("import_error", f"{type(exc).__name__}: {exc}"))
    except OSError as exc:
        queue.put(("os_error", str(exc)))
    except BaseException as exc:  # noqa: BLE001 — bubble unknown failures with type info
        queue.put(("backend_error", f"{type(exc).__name__}: {exc}"))


def run_gmsh_on_imported_case(
    *,
    stl_path: Path,
    output_msh_path: Path,
    mesh_mode: str = "beginner",
    characteristic_length_override: float | None = None,
    target_cell_count: int | None = None,
    sizing_field: "MeshSizingField | None" = None,
    refinement_zones: "list[MeshRefinementZone] | None" = None,
) -> GmshRunResult:
    """Mesh ``stl_path`` with gmsh and write ``output_msh_path``.

    Spawns a child process so gmsh's mandatory signal-handler install
    lands on a fresh main thread (FastAPI threadpool workers are not
    the main thread; see module docstring).

    DEC-V61-124: ``target_cell_count``, when provided, takes precedence
    over both ``characteristic_length_override`` and ``mesh_mode`` for
    lc derivation (cube approximation; see _lc_from_target_cell_count).

    DEC-V61-125 R1 P3 + R2 P2: validate
    ``characteristic_length_override`` here (parent process, before
    subprocess spawn) so a non-positive value fails fast with a clear
    ``ValueError`` rather than getting silently ignored by the
    ``if lc > 0`` guard inside ``_gmsh_inline``. The AI-coach path
    validates this at the ``RegenerateMeshArgs`` layer with Pydantic
    ``gt=0``; this guard is the defensive backstop for direct backend
    callers that bypass that schema.

    R2 P2: respect the documented precedence (target_cell_count >
    characteristic_length_override > mesh_mode). When
    ``target_cell_count`` is set the override would be ignored
    anyway, so validating it would reject previously-tolerated call
    shapes (e.g. a stale sentinel 0.0 carried over from an older
    caller). Validation is gated to fire only when the override is
    actually going to be consumed.

    DEC-V61-135 (N2.1): ``sizing_field`` (if active) takes precedence
    over both ``target_cell_count`` and ``characteristic_length_override``.
    Pydantic field-level validators on ``MeshSizingField`` already
    enforce positivity; we marshal it across the subprocess boundary
    as a dict (pydantic models are picklable but routinely cause
    'spawn' import-order pain on macOS).

    DEC-V61-136 (N2.2): ``refinement_zones`` (optional list of box /
    sphere zones) is layered on top of sizing_field via gmsh's Min
    field combinator. Empty list / None preserves N2.1 behavior.
    Geometric AABB validation runs inside ``_gmsh_inline`` (after STL
    merge) and surfaces as ``RefinementZoneError`` →
    ``failing_check=refinement_zone_invalid`` distinct from
    ``gmsh_diverged``. Like sizing_field, marshal as list-of-dicts
    across the subprocess boundary.
    """
    if (
        target_cell_count is None
        and characteristic_length_override is not None
        and characteristic_length_override <= 0
    ):
        raise ValueError(
            "characteristic_length_override must be positive, got "
            f"{characteristic_length_override!r}"
        )

    sizing_field_dict: dict | None = None
    if sizing_field is not None:
        # Avoid a cross-subprocess import of MeshSizingField — pass a
        # plain dict, _gmsh_inline reads keys by name.
        sizing_field_dict = sizing_field.model_dump(exclude_none=False)

    # V136 (N2.2): same marshalling discipline for refinement_zones —
    # list of pydantic discriminated-union members → list of plain
    # dicts so the spawned subprocess does not re-import the schema.
    refinement_zones_dict: list[dict] | None = None
    if refinement_zones:
        refinement_zones_dict = [z.model_dump() for z in refinement_zones]
    # Use 'spawn' explicitly: macOS defaults to 'spawn' since 3.8 and
    # Linux defaults to 'fork', which copies the parent process state
    # (including FastAPI / gmsh module-level imports). 'spawn' gives a
    # clean interpreter and avoids fork-after-import hazards from gmsh.
    ctx = multiprocessing.get_context("spawn")
    queue: "multiprocessing.Queue[tuple[str, object]]" = ctx.Queue()
    proc = ctx.Process(
        target=_subprocess_target,
        args=(
            str(stl_path),
            str(output_msh_path),
            mesh_mode,
            characteristic_length_override,
            target_cell_count,
            sizing_field_dict,
            refinement_zones_dict,
            queue,
        ),
    )
    proc.start()
    proc.join()

    if proc.exitcode != 0 and queue.empty():
        # Codex Round 6 P1: a hard child crash (segfault, OOM kill,
        # ``os._exit``, gmsh native abort) leaves no payload on the
        # queue. The previous code raised GmshMeshGenerationError here
        # which the pipeline mapped to gmsh_diverged / 422 — same
        # 4xx-relabel bug the Round 5 fix was supposed to close, just
        # on the no-payload crash path. Surface as GmshSubprocessError
        # so it bubbles as 5xx alongside the other deployment faults.
        raise GmshSubprocessError(
            f"gmsh subprocess exited with code {proc.exitcode} before "
            "posting a result (likely a hard crash inside gmsh's native code)."
        )

    kind, payload = queue.get()
    if kind == "ok":
        assert isinstance(payload, dict)
        return GmshRunResult(
            msh_path=Path(payload["msh_path"]),
            cell_count=int(payload["cell_count"]),
            face_count=int(payload["face_count"]),
            point_count=int(payload["point_count"]),
            characteristic_length_used=float(payload["characteristic_length_used"]),
            generation_time_s=float(payload["generation_time_s"]),
        )
    if kind == "refinement_zone_error":
        # V136 (N2.2): out-of-domain zone is a structured user-input
        # rejection (422). Re-raise as RefinementZoneError so the
        # pipeline maps it to failing_check=refinement_zone_invalid.
        raise RefinementZoneError(str(payload))
    if kind == "gmsh_error":
        raise GmshMeshGenerationError(str(payload))
    if kind == "os_error":
        # Disk-full / permission-denied — surface as OSError so the
        # pipeline layer reports a 5xx (matches the in-process contract).
        raise OSError(str(payload))
    if kind == "import_error":
        # gmsh module missing in the deployed [workbench] extra. Surface
        # as GmshSubprocessError so FastAPI returns 5xx and operators
        # see a structured cause class. NOT a user-geometry fault —
        # must not collapse to gmsh_diverged / 422.
        raise GmshSubprocessError(
            f"gmsh subprocess could not initialize (deployment fault): {payload}"
        )
    # 'backend_error' (or any unknown kind from a future version) —
    # surface as GmshSubprocessError so the route layer reports 5xx.
    # Codex Round 5 P1 + Round 6 P1: this branch must NOT raise
    # GmshMeshGenerationError, otherwise child-bootstrap / unknown-
    # cause faults would be silently relabeled as "bad geometry" (422).
    raise GmshSubprocessError(
        f"gmsh subprocess raised an unhandled exception (kind={kind!r}): {payload}"
    )
