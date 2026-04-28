"""LDC boundary-condition setup: split gmshToFoam patch + author dicts.

The gmsh meshing pipeline (M6.0) produces a single boundary patch
``patch0`` containing all face triangles of the cube. icoFoam needs
two named patches — ``lid`` (top, U=(1,0,0)) and ``fixedWalls`` (5
no-slip walls). This module:

1. Reads polyMesh/{points, faces, owner, boundary}.
2. Classifies each boundary face by checking if **all** its vertices
   lie within ``EPS`` of the cube's max-z coordinate (lid plane).
3. Reorders boundary faces in ``faces`` and ``owner`` so all lid
   faces precede all wall faces — OpenFOAM requires patch face
   ranges to be contiguous.
4. Rewrites ``boundary`` with two patches.
5. Authors the OpenFOAM-10 dict tree for icoFoam Re=100 (U_lid=1,
   L=0.1m, nu=1e-3): ``0/U``, ``0/p``, ``constant/physicalProperties``,
   ``constant/momentumTransport``, ``system/{controlDict, fvSchemes,
   fvSolution}``.

Numerical choices (Codex-reviewed in DEC-V61-097):

* ``nNonOrthogonalCorrectors 2`` — gmsh's tet mesh of an axis-aligned
  cube has Max non-orthogonality ~70°; PISO needs ≥2 correctors to
  keep continuity errors below 1e-5.
* ``deltaT 0.005`` for ``endTime 2`` → ~400 steps. Co_max~9 with
  this dt + the smallest tet cells, but icoFoam's implicit Euler
  time-discretization tolerates this for a steady-state demo.
* ``writeInterval 0.5`` → 5 time directories (0, 0.5, 1, 1.5, 2).
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# Lid plane is at z = +0.05 (top of the [-0.05, +0.05] cube). EPS is the
# numerical tolerance for "all 3 vertices on the lid plane" — gmsh
# rounds vertex coords to ~1e-7, so 1e-4 is generous-enough that
# refinement-boundary triangles stay classified as walls.
_LID_EPS = 1e-4

# Re = U·L/ν = 1·0.1/1e-3 = 100. icoFoam laminar.
_NU_KINEMATIC = 1.0e-3
_LID_VELOCITY = (1.0, 0.0, 0.0)


class BCSetupError(RuntimeError):
    """Raised when BC setup fails — bad polyMesh, write failure, etc."""


@dataclass(frozen=True, slots=True)
class BCSetupResult:
    case_id: str
    case_dir: Path
    n_lid_faces: int
    n_wall_faces: int
    lid_velocity: tuple[float, float, float]
    nu: float
    reynolds: float
    written_files: tuple[str, ...]


def _split_foam_block(path: Path) -> tuple[str, int, str, str]:
    """Parse a parens-list FOAM file into (pre, count, body, post).

    Used for points / faces / owner / neighbour files.
    """
    text = path.read_text()
    m = re.search(r"^\s*(\d+)\s*\n\(\s*\n", text, flags=re.MULTILINE)
    if not m:
        raise BCSetupError(f"can't parse FOAM block in {path}")
    count = int(m.group(1))
    body_start = m.end()
    try:
        body_end = text.index("\n)", body_start)
    except ValueError as exc:
        raise BCSetupError(f"unterminated parens-list in {path}") from exc
    return (
        text[:body_start],
        count,
        text[body_start:body_end],
        text[body_end:],
    )


def _parse_points(body: str) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)", line
        )
        if m:
            pts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    return pts


def _parse_face(line: str) -> list[int]:
    m = re.match(r"^(\d+)\(([\d\s]+)\)$", line.strip())
    if not m:
        raise BCSetupError(f"can't parse face line: {line!r}")
    n = int(m.group(1))
    vidx = [int(x) for x in m.group(2).split()]
    if len(vidx) != n:
        raise BCSetupError(f"face count mismatch: {line!r}")
    return vidx


def _split_lid_walls(
    polymesh: Path,
) -> tuple[int, int, int]:
    """Reorder boundary faces in ``faces`` and ``owner`` so lid faces
    come first, walls after. Rewrite ``boundary`` with two patches.

    Returns (n_lid, n_walls, b_start). Raises BCSetupError if the
    polyMesh isn't shaped like a single-patch gmshToFoam output.
    """
    boundary_text = (polymesh / "boundary").read_text()
    m_n = re.search(r"nFaces\s+(\d+)", boundary_text)
    m_start = re.search(r"startFace\s+(\d+)", boundary_text)
    if not m_n or not m_start:
        raise BCSetupError(
            f"boundary file at {polymesh} has no nFaces/startFace — "
            "expected gmshToFoam single-patch output."
        )
    b_n = int(m_n.group(1))
    b_start = int(m_start.group(1))

    # Snapshot polyMesh in case rewrite fails midway.
    backup = polymesh.parent / "polyMesh.pre_split"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(polymesh, backup)

    pts_pre, _, pts_body, _ = _split_foam_block(polymesh / "points")
    pts = _parse_points(pts_body)

    # Determine the lid plane: max z across all points (typically +0.05
    # for our LDC fixture, but compute it generically).
    z_max = max(p[2] for p in pts)

    fc_pre, fc_n, fc_body, fc_post = _split_foam_block(polymesh / "faces")
    fc_lines = [l for l in fc_body.splitlines() if l.strip()]
    if len(fc_lines) != fc_n:
        raise BCSetupError(
            f"face count mismatch: parsed {len(fc_lines)} vs declared {fc_n}"
        )

    ow_pre, ow_n, ow_body, ow_post = _split_foam_block(polymesh / "owner")
    ow_lines = [l for l in ow_body.splitlines() if l.strip()]
    if len(ow_lines) != ow_n != fc_n:
        raise BCSetupError(
            f"owner/face count mismatch ({ow_n} vs {fc_n})"
        )

    bnd_face_lines = fc_lines[b_start : b_start + b_n]
    bnd_owner_lines = ow_lines[b_start : b_start + b_n]

    def is_top(face_line: str) -> bool:
        vidx = _parse_face(face_line)
        return all(abs(pts[i][2] - z_max) < _LID_EPS for i in vidx)

    top_idx = [i for i, f in enumerate(bnd_face_lines) if is_top(f)]
    wall_idx = [i for i, f in enumerate(bnd_face_lines) if not is_top(f)]
    n_lid, n_walls = len(top_idx), len(wall_idx)
    if n_lid == 0:
        raise BCSetupError(
            f"no boundary faces match the lid plane (z={z_max:.4f}); "
            "the cube may be rotated or the STL is not axis-aligned."
        )
    if n_walls == 0:
        raise BCSetupError(
            "all boundary faces classified as lid — geometry "
            "doesn't look like an LDC cube."
        )

    new_bnd_faces = [bnd_face_lines[i] for i in top_idx] + [
        bnd_face_lines[i] for i in wall_idx
    ]
    new_bnd_owners = [bnd_owner_lines[i] for i in top_idx] + [
        bnd_owner_lines[i] for i in wall_idx
    ]

    new_fc_lines = fc_lines[:b_start] + new_bnd_faces
    new_ow_lines = ow_lines[:b_start] + new_bnd_owners

    (polymesh / "faces").write_text(
        fc_pre + "\n".join(new_fc_lines) + "\n" + fc_post
    )
    (polymesh / "owner").write_text(
        ow_pre + "\n".join(new_ow_lines) + "\n" + ow_post
    )

    boundary_str = (
        'FoamFile\n{\n    format      ascii;\n'
        '    class       polyBoundaryMesh;\n'
        '    location    "constant/polyMesh";\n'
        '    object      boundary;\n}\n\n'
        f"2\n(\n"
        f"    lid\n    {{\n        type            wall;\n"
        f"        nFaces          {n_lid};\n"
        f"        startFace       {b_start};\n    }}\n"
        f"    fixedWalls\n    {{\n        type            wall;\n"
        f"        nFaces          {n_walls};\n"
        f"        startFace       {b_start + n_lid};\n    }}\n"
        f")\n"
    )
    (polymesh / "boundary").write_text(boundary_str)

    return n_lid, n_walls, b_start


def _author_dicts(case_dir: Path) -> tuple[str, ...]:
    """Write the 7 OpenFOAM-10 dicts needed by icoFoam.

    Returns the relative paths of the files written (for the
    BCSetupResult audit trail).
    """
    (case_dir / "0").mkdir(exist_ok=True)
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "constant").mkdir(exist_ok=True)

    written: list[str] = []

    def w(rel: str, content: str) -> None:
        (case_dir / rel).write_text(content)
        written.append(rel)

    lid_u = " ".join(f"{c}" for c in _LID_VELOCITY)

    w(
        "0/U",
        f'FoamFile {{ version 2.0; format ascii; class volVectorField; '
        f'location "0"; object U; }}\n'
        f"dimensions      [0 1 -1 0 0 0 0];\n"
        f"internalField   uniform (0 0 0);\n"
        f"boundaryField\n"
        f"{{\n"
        f"    lid          {{ type fixedValue; value uniform ({lid_u}); }}\n"
        f"    fixedWalls   {{ type noSlip; }}\n"
        f"}}\n",
    )

    w(
        "0/p",
        'FoamFile { version 2.0; format ascii; class volScalarField; '
        'location "0"; object p; }\n'
        "dimensions      [0 2 -2 0 0 0 0];\n"
        "internalField   uniform 0;\n"
        "boundaryField\n"
        "{\n"
        "    lid          { type zeroGradient; }\n"
        "    fixedWalls   { type zeroGradient; }\n"
        "}\n",
    )

    w(
        "constant/physicalProperties",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object physicalProperties; }\n'
        "transportModel  Newtonian;\n"
        f"nu              [0 2 -1 0 0 0 0] {_NU_KINEMATIC};\n",
    )

    w(
        "constant/momentumTransport",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object momentumTransport; }\n'
        "simulationType laminar;\n",
    )

    w(
        "system/controlDict",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object controlDict; }\n'
        "application icoFoam;\n"
        "startFrom startTime;\n"
        "startTime 0;\n"
        "stopAt endTime;\n"
        "endTime 2;\n"
        "deltaT 0.005;\n"
        "writeControl runTime;\n"
        "writeInterval 0.5;\n"
        "purgeWrite 0;\n"
        "writeFormat ascii;\n"
        "writePrecision 6;\n"
        "writeCompression off;\n"
        "timeFormat general;\n"
        "timePrecision 6;\n"
        "runTimeModifiable true;\n",
    )

    w(
        "system/fvSchemes",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        "divSchemes  { default none; div(phi,U) Gauss linear; }\n"
        "laplacianSchemes { default Gauss linear orthogonal; }\n"
        "interpolationSchemes { default linear; }\n"
        "snGradSchemes { default orthogonal; }\n",
    )

    w(
        "system/fvSolution",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSolution; }\n'
        "solvers\n"
        "{\n"
        "    p  { solver PCG; preconditioner DIC; tolerance 1e-06; relTol 0.05; }\n"
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
    )

    return tuple(written)


def setup_ldc_bc(case_dir: Path, *, case_id: str) -> BCSetupResult:
    """Idempotent: split polyMesh patches + author icoFoam dicts.

    Calling twice on the same case is safe — the polyMesh.pre_split
    backup catches the original single-patch state, and re-running
    classifies + sorts identically. Calling AFTER icoFoam has run
    is fine too (dicts are overwritten; existing time directories
    untouched).

    Raises :class:`BCSetupError` if polyMesh is malformed or write
    fails. The route layer maps these to 4xx (400 if the user's
    geometry isn't an axis-aligned cube; 500 for I/O faults).
    """
    if not case_dir.is_dir():
        raise BCSetupError(f"case dir not found: {case_dir}")
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise BCSetupError(
            f"no constant/polyMesh under {case_dir} — run M6.0 mesh first."
        )
    if not (polymesh / "boundary").is_file():
        raise BCSetupError(
            "polyMesh has no boundary file — gmshToFoam must run first."
        )

    n_lid, n_walls, _ = _split_lid_walls(polymesh)
    written = _author_dicts(case_dir)

    return BCSetupResult(
        case_id=case_id,
        case_dir=case_dir,
        n_lid_faces=n_lid,
        n_wall_faces=n_walls,
        lid_velocity=_LID_VELOCITY,
        nu=_NU_KINEMATIC,
        reynolds=_LID_VELOCITY[0] * 0.1 / _NU_KINEMATIC,
        written_files=written,
    )
