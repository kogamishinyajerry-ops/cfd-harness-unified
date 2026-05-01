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

from ui.backend.services.case_manifest import (
    CaseLockError,
    case_lock,
    mark_ai_authored,
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


# Inlet velocity (m/s) used when no override is present. Picked to be
# small enough that low-Re cavity geometries converge, large enough
# that the dimensional residuals are well above floating-point noise.
_DEFAULT_INLET_U: tuple[float, float, float] = (0.5, 0.0, 0.0)
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
    inlet_velocity: tuple[float, float, float]
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


def _read_named_patches(boundary_path: Path) -> list[str]:
    """Return ordered list of patch names from ``constant/polyMesh/boundary``.
    Skips the OpenFOAM ``FoamFile`` header dict.
    """
    text = boundary_path.read_text()
    names: list[str] = []
    for m in _PATCH_RE.finditer(text):
        name = m.group(1)
        if name == "FoamFile":
            continue
        names.append(name)
    return names


def _classify_patch(name: str) -> tuple[BCClass, str | None]:
    """Map a patch name to a BCClass via the project default table.
    Returns (class, warning_or_None). Unrecognized names fall through
    to NO_SLIP_WALL with a warning.

    Lookup order:
        1. Exact case-insensitive match against ``_DEFAULT_PATCH_CLASS``
        2. Prefix match — strip a trailing ``_<digits>`` or ``<digits>``
           suffix and re-lookup. Handles canonical multi-instance naming
           like ``inlet_1`` / ``inlet_2`` / ``walls01`` that CAD exporters
           emit when one logical patch is split into multiple meshing
           regions.
        3. Fall through to NO_SLIP_WALL with warning.
    """
    lower = name.lower()
    cls = _DEFAULT_PATCH_CLASS.get(lower)
    if cls is not None:
        return cls, None
    # Strip ``_<digits>`` or trailing digits and retry.
    stripped = re.sub(r"_?\d+$", "", lower)
    if stripped and stripped != lower:
        cls = _DEFAULT_PATCH_CLASS.get(stripped)
        if cls is not None:
            return cls, None
    return (
        BCClass.NO_SLIP_WALL,
        f"patch {name!r} not in default classification table; "
        f"defaulting to no-slip wall (override via raw-dict editor "
        f"if needed)",
    )


def _u_block(name: str, cls: BCClass, inlet_u: tuple[float, float, float]) -> str:
    if cls == BCClass.VELOCITY_INLET:
        return (
            f"    {name}\n"
            f"    {{\n"
            f"        type            fixedValue;\n"
            f"        value           uniform ({inlet_u[0]} {inlet_u[1]} {inlet_u[2]});\n"
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
    inlet_u: tuple[float, float, float],
    nu: float,
    delta_t: float,
    end_time: float,
) -> list[tuple[str, str]]:
    """Compose the 7-dict (rel, content) plan for the named patches."""
    u_blocks = "".join(
        _u_block(name, cls, inlet_u) for name, cls in patches_with_class
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
    inlet_u: tuple[float, float, float] = _DEFAULT_INLET_U,
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
    patch_names = _read_named_patches(boundary_path)
    if not patch_names:
        raise StlPatchBCError(
            f"polyMesh/boundary has no patches at {boundary_path}",
            failing_check="no_named_patches",
        )
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

    plan = _build_dict_plan(
        patches_with_class,
        inlet_u=inlet_u,
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
        inlet_velocity=inlet_u,
        nu=nu,
        delta_t=delta_t,
        end_time=end_time,
        written_files=written,
        skipped_user_overrides=skipped,
        warnings=tuple(warnings),
    )
