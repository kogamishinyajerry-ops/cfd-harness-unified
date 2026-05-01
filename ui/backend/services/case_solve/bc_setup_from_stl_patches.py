"""DEC-V61-103 Phase 1 · BC dict authoring driven by named polyMesh patches.

The legacy ``setup_ldc_bc`` and ``setup_channel_bc`` paths each assume
a fixed patch topology baked into the executor. Imported CAD geometries
that have proper named patches in ``polyMesh/boundary`` (after the
DEC-V61-102 defect-2a fix preserves them) need a 3rd executor that:

1. Reads the patch list from ``constant/polyMesh/boundary``
2. Maps each patch name to a default BC class via a project-level table
3. Authors 7 OpenFOAM-10 dicts referencing the actual patch names
4. Wraps the multi-file write in V61-102's ``_atomic_commit_dicts`` so
   the user-override invariant + 2-phase commit semantics apply

Engineers can fine-tune any field via the V61-102 raw-dict editor
post-author; this executor only sets sane defaults.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from ui.backend.services.case_manifest import (
    CaseLockError,
    case_lock,
    mark_ai_authored,
)
from ui.backend.services.render.polymesh_parser import (
    parse_faces,
    parse_points,
)

from .bc_setup import _atomic_commit_dicts


class BCClass(str, Enum):
    """BC archetype that determines the (U, p) field templates emitted
    for a given patch. Engineers pick the archetype via patch name; the
    raw-dict editor handles overrides for the long tail of cases this
    table doesn't cover.
    """

    VELOCITY_INLET = "velocity_inlet"
    PRESSURE_OUTLET = "pressure_outlet"
    NO_SLIP_WALL = "no_slip_wall"
    SYMMETRY = "symmetry"


# Default mapping by patch name (case-insensitive). The fallback for
# unrecognized names is NO_SLIP_WALL with a warning (the engineer can
# override via raw-dict editor).
_DEFAULT_PATCH_CLASS: dict[str, BCClass] = {
    "inlet": BCClass.VELOCITY_INLET,
    "in": BCClass.VELOCITY_INLET,
    "outlet": BCClass.PRESSURE_OUTLET,
    "out": BCClass.PRESSURE_OUTLET,
    "wall": BCClass.NO_SLIP_WALL,
    "walls": BCClass.NO_SLIP_WALL,
    "symmetry": BCClass.SYMMETRY,
    "sym": BCClass.SYMMETRY,
    "top": BCClass.NO_SLIP_WALL,
    "bottom": BCClass.NO_SLIP_WALL,
    "front": BCClass.NO_SLIP_WALL,
    "back": BCClass.NO_SLIP_WALL,
    "left": BCClass.NO_SLIP_WALL,
    "right": BCClass.NO_SLIP_WALL,
    "fixedwalls": BCClass.NO_SLIP_WALL,
    "blade": BCClass.NO_SLIP_WALL,
    "obstacle": BCClass.NO_SLIP_WALL,
}


# Inlet velocity magnitude (m/s) used when no override is present.
# Default 0.5 m/s; the direction is computed per-patch from face
# normals (defect-6 fix: rotated geometries used to have flow ram
# into walls because the direction was hardcoded to global +x).
_DEFAULT_INLET_SPEED: float = 0.5
_DEFAULT_NU: float = 1.0e-3
# icoFoam timestep + endTime defaults. Conservative — engineer can
# tune via raw-dict editor (system/controlDict).
_DEFAULT_DELTA_T: float = 0.01
_DEFAULT_END_TIME: float = 5.0


class StlPatchBCError(RuntimeError):
    """Raised when stl-patch-driven BC setup can't proceed.

    ``failing_check`` is one of:

    * ``mesh_not_setup`` — ``constant/polyMesh/boundary`` missing
    * ``no_named_patches`` — boundary file exists but has no patches
      (or only the legacy single-patch ``patch0``); caller should fall
      through to the LDC executor instead
    * ``write_failed`` — atomic commit failed (rolled back)
    * ``case_lock_failed`` — couldn't acquire case lock (concurrent
      writer); 409
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


@dataclass(frozen=True, slots=True)
class StlPatchBCResult:
    case_id: str
    case_dir: Path
    patches: tuple[tuple[str, BCClass], ...]
    # Per-patch inlet velocity vector (only populated for VELOCITY_INLET
    # patches; defect-6 fix means the direction follows each patch's
    # inward normal). ``inlet_speed`` is the scalar magnitude common
    # to all inlets.
    inlet_speed: float
    inlet_velocities: tuple[tuple[str, tuple[float, float, float]], ...]
    nu: float
    delta_t: float
    end_time: float
    written_files: tuple[str, ...]
    skipped_user_overrides: tuple[str, ...]
    warnings: tuple[str, ...]


_PATCH_RE = re.compile(
    r"(\w+)\s*\{[^}]*nFaces\s+(\d+)[^}]*startFace\s+(\d+)[^}]*\}",
    re.DOTALL,
)


def _read_patch_ranges(boundary_path: Path) -> list[tuple[str, int, int]]:
    """Return ordered ``[(name, startFace, nFaces), ...]`` from
    ``constant/polyMesh/boundary``. Skips the OpenFOAM ``FoamFile``
    header dict.
    """
    text = boundary_path.read_text()
    out: list[tuple[str, int, int]] = []
    for m in _PATCH_RE.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        nfaces = int(m.group(2))
        start = int(m.group(3))
        out.append((name, start, nfaces))
    return out


def _read_named_patches(boundary_path: Path) -> list[str]:
    """Convenience wrapper returning patch names only."""
    return [name for name, _start, _n in _read_patch_ranges(boundary_path)]


def _compute_patch_inward_normals(
    case_dir: Path,
    patch_ranges: list[tuple[str, int, int]],
) -> dict[str, np.ndarray]:
    """For each patch, compute the average INWARD-pointing unit normal
    (the direction flow must enter to actually go into the fluid).

    OpenFOAM boundary face normals point OUT of the fluid domain
    (away from the cell that owns the face). For a velocity inlet,
    the BC velocity vector should point INWARD = ``-outward_normal``.

    Returns a dict ``{patch_name: unit_inward_normal_3vec}``. Patches
    with degenerate (zero-area) face sets get a zero vector — the
    caller falls back to the legacy hardcoded direction in that case.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    points_path = polymesh / "points"
    faces_path = polymesh / "faces"
    if not points_path.is_file() or not faces_path.is_file():
        return {name: np.zeros(3) for name, _s, _n in patch_ranges}
    try:
        points = parse_points(points_path)
        faces = parse_faces(faces_path)
    except Exception:  # noqa: BLE001 — parser raises on malformed; treat as no-data
        return {name: np.zeros(3) for name, _s, _n in patch_ranges}

    out: dict[str, np.ndarray] = {}
    for name, start, n in patch_ranges:
        if n <= 0:
            out[name] = np.zeros(3)
            continue
        # Average the per-face Newell-method normal (sum of outward
        # cross products around each polygon ring), normalize to unit
        # length. Newell handles non-planar quads/n-gons gracefully.
        avg_n = np.zeros(3)
        for face_idx in range(start, start + n):
            if face_idx >= len(faces):
                continue
            ring = faces[face_idx]
            # Newell's method: sum of (curr × next) cross products.
            n_v = np.zeros(3)
            for i in range(len(ring)):
                p_curr = points[ring[i]]
                p_next = points[ring[(i + 1) % len(ring)]]
                n_v[0] += (p_curr[1] - p_next[1]) * (p_curr[2] + p_next[2])
                n_v[1] += (p_curr[2] - p_next[2]) * (p_curr[0] + p_next[0])
                n_v[2] += (p_curr[0] - p_next[0]) * (p_curr[1] + p_next[1])
            avg_n += n_v
        norm = float(np.linalg.norm(avg_n))
        if norm < 1e-12:
            out[name] = np.zeros(3)
        else:
            outward = avg_n / norm
            # Inward = -outward (flow into fluid is opposite to the
            # outward boundary normal).
            out[name] = -outward
    return out


# Canonical role tokens scanned across compound patch names. Priority
# order matters: a name like ``inlet_wall_seam`` should classify as an
# inlet (the actual flow boundary) rather than a wall, so inlet/outlet/
# symmetry are checked before wall. Each entry is (token_substring,
# class). Tokens are matched as substrings of the lowercased name.
_CANONICAL_ROLE_TOKENS: tuple[tuple[str, BCClass], ...] = (
    ("inlet", BCClass.VELOCITY_INLET),
    ("outlet", BCClass.PRESSURE_OUTLET),
    ("symmetry", BCClass.SYMMETRY),
    ("wall", BCClass.NO_SLIP_WALL),
)


def _classify_patch(name: str) -> tuple[BCClass, str | None]:
    """Map a patch name to a BCClass via the project default table.
    Returns (class, warning_or_None). Unrecognized names fall through
    to NO_SLIP_WALL with a warning.

    Lookup order:
        1. Exact case-insensitive match against ``_DEFAULT_PATCH_CLASS``
           (covers single-token names like ``inlet``, ``walls``,
           ``left``, ``top``).
        2. Strip a trailing ``_<digits>`` or ``<digits>`` suffix and
           retry (canonical multi-instance numbering like ``inlet_1``,
           ``walls01``).
        3. Canonical role-token scan: search for ``inlet`` / ``outlet`` /
           ``symmetry`` / ``wall`` as a substring (priority order: inlet
           before outlet before symmetry before wall). Handles compound
           CAD-export names where the role token is embedded:
           ``outlet_branch`` → outlet, ``left_inlet`` → inlet,
           ``inlet_main`` → inlet, ``walls_perimeter`` → wall.
           Codex post-merge finding (defect-7 follow-up): the previous
           strip-after-first-underscore rule mis-classified ``left_inlet``
           as wall because ``left`` matched the default wall token.
        4. Fall through to NO_SLIP_WALL with warning.
    """
    lower = name.lower()
    cls = _DEFAULT_PATCH_CLASS.get(lower)
    if cls is not None:
        return cls, None
    # Step 2: strip trailing digits.
    stripped = re.sub(r"_?\d+$", "", lower)
    if stripped and stripped != lower:
        cls = _DEFAULT_PATCH_CLASS.get(stripped)
        if cls is not None:
            return cls, None
    # Step 3: canonical role-token substring scan, prioritized.
    for token, token_cls in _CANONICAL_ROLE_TOKENS:
        if token in lower:
            return token_cls, None
    return (
        BCClass.NO_SLIP_WALL,
        f"patch {name!r} not in default classification table; "
        f"defaulting to no-slip wall (override via raw-dict editor "
        f"if needed)",
    )


def _u_block(
    name: str,
    cls: BCClass,
    inlet_u: tuple[float, float, float],
) -> str:
    if cls == BCClass.VELOCITY_INLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            fixedValue;\n"
            f"        value           uniform ({inlet_u[0]:.6g} {inlet_u[1]:.6g} {inlet_u[2]:.6g});\n"
            f"    }}\n"
        )
    if cls == BCClass.PRESSURE_OUTLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            zeroGradient;\n"
            f"    }}\n"
        )
    if cls == BCClass.NO_SLIP_WALL:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            noSlip;\n"
            f"    }}\n"
        )
    if cls == BCClass.SYMMETRY:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            symmetry;\n"
            f"    }}\n"
        )
    raise ValueError(f"unhandled BCClass: {cls}")


def _p_block(name: str, cls: BCClass) -> str:
    if cls == BCClass.PRESSURE_OUTLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            fixedValue;\n"
            f"        value           uniform 0;\n"
            f"    }}\n"
        )
    if cls == BCClass.SYMMETRY:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            symmetry;\n"
            f"    }}\n"
        )
    # Velocity inlet + walls both use zeroGradient on p.
    return (
        f"    {name}\n"
        f"    {{\n"
        f"        type            zeroGradient;\n"
        f"    }}\n"
    )


def _build_dict_plan(
    patches_with_class: list[tuple[str, BCClass]],
    *,
    inlet_u_per_patch: dict[str, tuple[float, float, float]],
    nu: float,
    delta_t: float,
    end_time: float,
) -> list[tuple[str, str]]:
    """Compose the 7-dict (rel, content) plan for the named patches.

    ``inlet_u_per_patch`` carries one velocity vector per VELOCITY_INLET
    patch (defect-6 fix: each inlet's direction comes from its own
    polyMesh face normals, so rotated geometries get flow heading into
    the duct rather than into walls).
    """
    u_blocks = "".join(
        _u_block(name, cls, inlet_u_per_patch.get(name, (0.0, 0.0, 0.0)))
        for name, cls in patches_with_class
    )
    p_blocks = "".join(_p_block(name, cls) for name, cls in patches_with_class)

    plan: list[tuple[str, str]] = [
        (
            "0/U",
            'FoamFile { version 2.0; format ascii; class volVectorField; '
            'location "0"; object U; }\n'
            "dimensions      [0 1 -1 0 0 0 0];\n"
            "internalField   uniform (0 0 0);\n"
            "boundaryField\n"
            "{\n"
            f"{u_blocks}"
            "}\n",
        ),
        (
            "0/p",
            'FoamFile { version 2.0; format ascii; class volScalarField; '
            'location "0"; object p; }\n'
            "dimensions      [0 2 -2 0 0 0 0];\n"
            "internalField   uniform 0;\n"
            "boundaryField\n"
            "{\n"
            f"{p_blocks}"
            "}\n",
        ),
        (
            "constant/physicalProperties",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "constant"; object physicalProperties; }\n'
            "transportModel  Newtonian;\n"
            f"nu              [0 2 -1 0 0 0 0] {nu};\n",
        ),
        (
            "constant/momentumTransport",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "constant"; object momentumTransport; }\n'
            "simulationType laminar;\n",
        ),
        (
            "system/controlDict",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object controlDict; }\n'
            "application icoFoam;\n"
            "startFrom startTime;\n"
            "startTime 0;\n"
            "stopAt endTime;\n"
            f"endTime {end_time};\n"
            f"deltaT {delta_t};\n"
            "writeControl runTime;\n"
            "writeInterval 1.0;\n"
            "purgeWrite 0;\n"
            "writeFormat ascii;\n"
            "writePrecision 6;\n"
            "writeCompression off;\n"
            "timeFormat general;\n"
            "timePrecision 6;\n"
            "runTimeModifiable true;\n",
        ),
        (
            "system/fvSchemes",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSchemes; }\n'
            "ddtSchemes  { default Euler; }\n"
            "gradSchemes { default Gauss linear; }\n"
            "divSchemes  { default none; div(phi,U) Gauss linear; }\n"
            "laplacianSchemes { default Gauss linear orthogonal; }\n"
            "interpolationSchemes { default linear; }\n"
            "snGradSchemes { default orthogonal; }\n",
        ),
        (
            "system/fvSolution",
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSolution; }\n'
            "solvers\n"
            "{\n"
            "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; "
            "relTol 0.05; }\n"
            "    pFinal { $p; relTol 0; }\n"
            "    U  { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-05; relTol 0; }\n"
            "}\n"
            "PISO\n"
            "{\n"
            "    nCorrectors 2;\n"
            "    nNonOrthogonalCorrectors 2;\n"
            "    pRefCell 0;\n"
            "    pRefValue 0;\n"
            "}\n",
        ),
    ]
    return plan


def setup_bc_from_stl_patches(
    case_dir: Path,
    *,
    case_id: str,
    inlet_speed: float = _DEFAULT_INLET_SPEED,
    nu: float = _DEFAULT_NU,
    delta_t: float = _DEFAULT_DELTA_T,
    end_time: float = _DEFAULT_END_TIME,
) -> StlPatchBCResult:
    """Author the icoFoam dict tree using named patches from polyMesh/boundary.

    Idempotent. The atomic commit + V61-102 user-override invariant
    means: dicts the engineer manually edited (via raw-dict editor →
    manifest source=user) are NOT clobbered by re-runs.

    Raises ``StlPatchBCError`` with structured ``failing_check`` for
    every detectable failure mode; the route maps each to an HTTP 4xx
    code.
    """
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    if not boundary_path.is_file():
        raise StlPatchBCError(
            f"polyMesh/boundary missing at {boundary_path} — run mesh "
            "generation before BC setup",
            failing_check="mesh_not_setup",
        )
    patch_ranges = _read_patch_ranges(boundary_path)
    if not patch_ranges:
        raise StlPatchBCError(
            f"polyMesh/boundary has no patches at {boundary_path}",
            failing_check="no_named_patches",
        )
    patch_names = [name for name, _s, _n in patch_ranges]
    if patch_names == ["patch0"]:
        # Legacy single-patch (defaultFaces) path — the LDC or channel
        # executor is the right entry point, not this one.
        raise StlPatchBCError(
            "polyMesh/boundary has only the legacy ``patch0`` — the "
            "STL was imported without named solids. Use setup_ldc_bc "
            "or setup_channel_bc instead.",
            failing_check="no_named_patches",
        )

    patches_with_class: list[tuple[str, BCClass]] = []
    warnings: list[str] = []
    for name in patch_names:
        cls, warning = _classify_patch(name)
        patches_with_class.append((name, cls))
        if warning:
            warnings.append(warning)

    # Defect-6 fix: compute per-patch inward normals so velocity inlets
    # get flow direction matching the actual patch orientation. For
    # axis-aligned cases this still resolves to ±x/±y/±z (matching the
    # iter02/iter03 pre-defect-6 behavior); for rotated geometries
    # (iter04 Codex L-bend) it produces the correct rotated direction.
    inward_normals = _compute_patch_inward_normals(case_dir, patch_ranges)
    inlet_u_per_patch: dict[str, tuple[float, float, float]] = {}
    fallback_axis = np.array([1.0, 0.0, 0.0])
    for name, cls in patches_with_class:
        if cls != BCClass.VELOCITY_INLET:
            continue
        n_in = inward_normals.get(name, np.zeros(3))
        if float(np.linalg.norm(n_in)) < 1e-9:
            # Degenerate patch (no readable faces) — fall back to +x
            # axis. Engineers can override via raw-dict editor.
            n_in = fallback_axis
            warnings.append(
                f"patch {name!r}: could not read face normals from "
                f"polyMesh; defaulting inlet velocity to {inlet_speed} "
                f"m/s along +x. Override via raw-dict editor if the "
                f"geometry isn't axis-aligned."
            )
        u_vec = inlet_speed * n_in
        inlet_u_per_patch[name] = (float(u_vec[0]), float(u_vec[1]), float(u_vec[2]))

    plan = _build_dict_plan(
        patches_with_class,
        inlet_u_per_patch=inlet_u_per_patch,
        nu=nu,
        delta_t=delta_t,
        end_time=end_time,
    )

    try:
        with case_lock(case_dir):
            try:
                written, skipped = _atomic_commit_dicts(case_dir, plan)
            except OSError as exc:
                raise StlPatchBCError(
                    f"atomic commit failed: {exc}",
                    failing_check="write_failed",
                ) from exc
            if written:
                mark_ai_authored(
                    case_dir,
                    relative_paths=list(written),
                    action="setup_bc_from_stl_patches",
                    detail={
                        "patches": [
                            {"name": name, "bc_class": cls.value}
                            for name, cls in patches_with_class
                        ],
                        "warnings": warnings,
                    },
                )
    except CaseLockError as exc:
        raise StlPatchBCError(
            f"case lock acquisition failed: {exc}",
            failing_check="case_lock_failed",
        ) from exc

    return StlPatchBCResult(
        case_id=case_id,
        case_dir=case_dir,
        patches=tuple(patches_with_class),
        inlet_speed=inlet_speed,
        inlet_velocities=tuple(inlet_u_per_patch.items()),
        nu=nu,
        delta_t=delta_t,
        end_time=end_time,
        written_files=written,
        skipped_user_overrides=skipped,
        warnings=tuple(warnings),
    )
