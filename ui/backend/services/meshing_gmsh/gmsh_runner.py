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


def _gmsh_inline(
    *,
    stl_path: Path,
    output_msh_path: Path,
    mesh_mode: str,
    characteristic_length_override: float | None,
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
                    _types, elem_tags_list, node_tags_list = (
                        gmsh.model.mesh.getElements(dim=2, tag=tag)
                    )
                    if not node_tags_list or len(node_tags_list[0]) == 0:
                        unassigned.append(tag)
                        continue
                    # Build per-triangle centroids. node_tags_list[0]
                    # is a flat array; triangle elements use 3 nodes
                    # each, in row-major order.
                    flat_nodes = node_tags_list[0]
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
    """
    try:
        result = _gmsh_inline(
            stl_path=Path(stl_path_str),
            output_msh_path=Path(output_msh_path_str),
            mesh_mode=mesh_mode,
            characteristic_length_override=characteristic_length_override,
        )
        # asdict() handles the Path → str translation for the dataclass
        # via a custom default factory; do it explicitly for safety.
        payload = asdict(result)
        payload["msh_path"] = str(payload["msh_path"])
        queue.put(("ok", payload))
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
) -> GmshRunResult:
    """Mesh ``stl_path`` with gmsh and write ``output_msh_path``.

    Spawns a child process so gmsh's mandatory signal-handler install
    lands on a fresh main thread (FastAPI threadpool workers are not
    the main thread; see module docstring).
    """
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
