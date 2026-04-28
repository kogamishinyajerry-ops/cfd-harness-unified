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
import time
from dataclasses import asdict, dataclass
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

    if not stl_path.exists():
        raise GmshMeshGenerationError(f"STL not found: {stl_path}")

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
            surface_loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surfaces])
            gmsh.model.geo.addVolume([surface_loop])
            gmsh.model.geo.synchronize()

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

            gmsh.write(str(output_msh_path))
        except GmshMeshGenerationError:
            raise
        except OSError:
            # Disk-full / permission-denied / read-only filesystem from
            # gmsh.write() or any other I/O. These are backend / host
            # faults, not user-geometry rejections — let them bubble
            # as 5xx so operators see the real cause.
            raise
        except Exception as exc:  # noqa: BLE001 — gmsh bindings raise plain Exception
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
        raise GmshMeshGenerationError(
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
        # as RuntimeError so FastAPI returns 5xx and operators see the
        # original ImportError class + message. NOT a user-geometry
        # fault — must not collapse to gmsh_diverged / 422.
        raise RuntimeError(
            f"gmsh subprocess could not initialize (deployment fault): {payload}"
        )
    # 'backend_error' (or any unknown kind from a future version) —
    # surface as RuntimeError so the route layer reports 5xx. Codex
    # Round 5 P1: this branch must NOT raise GmshMeshGenerationError,
    # otherwise child-bootstrap / unknown-cause faults would be
    # silently relabeled as "bad geometry" (HTTP 422).
    raise RuntimeError(
        f"gmsh subprocess raised an unhandled exception (kind={kind!r}): {payload}"
    )
