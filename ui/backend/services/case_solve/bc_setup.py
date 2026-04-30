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

from ui.backend.services.case_manifest import (
    CaseLockError,
    case_lock,
    is_user_override,
    mark_ai_authored,
)

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
    # DEC-V61-102 Phase 1.4: paths skipped because the engineer carries
    # a `source: user` manifest entry — preserved across re-runs of
    # setup_ldc_bc so manual rescues survive AI re-author cycles.
    skipped_user_overrides: tuple[str, ...] = ()


# DEC-V61-101: minimal laminar channel executor. Defaults locked in
# the DEC; see `2026-04-29_v61_101_minimal_channel_executor.md` §
# "Default BCs".
_CHANNEL_INLET_VELOCITY: tuple[float, float, float] = (1.0, 0.0, 0.0)
_CHANNEL_NU: float = 0.01


@dataclass(frozen=True, slots=True)
class ChannelBCSetupResult:
    """DEC-V61-101 channel executor result. Distinct from BCSetupResult
    because the patch topology differs (inlet+outlet+walls vs
    lid+fixedWalls) and the dict tree carries different BC values.
    """

    case_id: str
    case_dir: Path
    n_inlet_faces: int
    n_outlet_faces: int
    n_wall_faces: int
    inlet_velocity: tuple[float, float, float]
    nu: float
    reynolds: float  # rough estimate U·L_char/ν using bbox max-extent
    written_files: tuple[str, ...]
    # DEC-V61-102 Phase 1.4: same semantics as BCSetupResult — paths the
    # engineer manually edited are preserved, never silently re-authored.
    skipped_user_overrides: tuple[str, ...] = ()


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


def _restore_pre_split_if_present(polymesh: Path) -> None:
    """Idempotency support for setup_*_bc. If a previous invocation
    saved polyMesh.pre_split (the original gmshToFoam single-patch
    state), restore it BEFORE re-splitting so the regex-based
    boundary parser sees the original {nFaces, startFace} pair
    instead of post-split per-patch values.

    Without this, calling setup_ldc_bc/setup_channel_bc twice on the
    same case_dir parses only the first patch's nFaces/startFace,
    truncating the boundary face range and raising spurious
    BCSetupErrors. The docstring used to claim idempotency but the
    implementation didn't deliver — surfaced by DEC-V61-101's off-axis
    topology test on 2026-04-30.
    """
    backup = polymesh.parent / "polyMesh.pre_split"
    if not backup.is_dir():
        return
    # Restore: blow away current polyMesh, copy backup over it.
    shutil.rmtree(polymesh)
    shutil.copytree(backup, polymesh)


def _split_lid_walls(
    polymesh: Path,
) -> tuple[int, int, int]:
    """Reorder boundary faces in ``faces`` and ``owner`` so lid faces
    come first, walls after. Rewrite ``boundary`` with two patches.

    Returns (n_lid, n_walls, b_start). Raises BCSetupError if the
    polyMesh isn't shaped like a single-patch gmshToFoam output.

    Idempotent: if a polyMesh.pre_split backup exists from a previous
    invocation, the original single-patch state is restored before
    the regex-based parse runs.
    """
    _restore_pre_split_if_present(polymesh)
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


def _author_dicts(case_dir: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Write the 7 OpenFOAM-10 dicts needed by icoFoam.

    Returns ``(written, skipped)``: ``written`` are paths the AI just
    re-authored; ``skipped`` are paths the engineer manually edited
    (manifest ``source: user``) and we left untouched. The 0/* and
    constant/polyMesh paths are NEVER subject to user override (face_id-
    coupled — see `case_dicts.allowlist`); only the dicts in the
    allowlist can carry a `source: user` entry.

    DEC-V61-102 Phase 1.4: this is the executor side of the
    user-override invariant. Without this guard, every re-click of
    [AI 处理] silently clobbers manual edits the engineer staged via
    POST /cases/{id}/dicts/{path}.
    """
    (case_dir / "0").mkdir(exist_ok=True)
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "constant").mkdir(exist_ok=True)

    written: list[str] = []
    skipped: list[str] = []

    def w(rel: str, content: str) -> None:
        if is_user_override(case_dir, relative_path=rel):
            skipped.append(rel)
            return
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

    return tuple(written), tuple(skipped)


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

    # Codex round-2 P1-HIGH closure: the is_user_override check + write
    # + mark_ai_authored sequence runs inside an exclusive per-case lock
    # so a concurrent POST /dicts manual edit can't slip in between
    # is_user_override returning False and the AI write. Without the
    # lock, manifest.source=user could persist while disk content was
    # silently re-authored by AI (manifest+disk divergence).
    try:
        with case_lock(case_dir):
            written, skipped = _author_dicts(case_dir)
            if written:
                mark_ai_authored(
                    case_dir,
                    relative_paths=list(written),
                    action="setup_ldc_bc",
                    detail={"skipped_user_overrides": list(skipped)} if skipped else None,
                )
    except CaseLockError as exc:
        # Round-3: translate to BCSetupError so the caller (route layer)
        # gets a uniform "setup_bc_failed" envelope instead of a raw
        # OSError percolating up.
        raise BCSetupError(
            f"could not acquire case lock for setup_ldc_bc: {exc}"
        ) from exc

    return BCSetupResult(
        case_id=case_id,
        case_dir=case_dir,
        n_lid_faces=n_lid,
        n_wall_faces=n_walls,
        lid_velocity=_LID_VELOCITY,
        nu=_NU_KINEMATIC,
        reynolds=_LID_VELOCITY[0] * 0.1 / _NU_KINEMATIC,
        written_files=written,
        skipped_user_overrides=skipped,
    )


# ────────── DEC-V61-101 · channel executor ──────────


def _split_channel_patches(
    polymesh: Path,
    inlet_face_ids: tuple[str, ...],
    outlet_face_ids: tuple[str, ...],
) -> tuple[int, int, int, int]:
    """Reorder boundary faces in ``faces`` and ``owner`` so inlet
    faces come first, outlet faces second, walls third. Rewrite
    ``boundary`` with three named patches.

    Returns (n_inlet, n_outlet, n_walls, b_start). Raises BCSetupError
    if the polyMesh shape doesn't match gmshToFoam single-patch output
    or any pin's face_id can't be located among the boundary faces
    (the classifier should have rejected this case before we got here,
    but defend in depth).

    Idempotent: if a polyMesh.pre_split backup exists from a previous
    invocation, the original single-patch state is restored before
    the regex parse — engineer can safely re-click [AI 处理] without
    triggering spurious channel_pin_mismatch errors.
    """
    from ui.backend.services.case_annotations import face_id as compute_face_id

    _restore_pre_split_if_present(polymesh)
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

    fc_pre, fc_n, fc_body, fc_post = _split_foam_block(polymesh / "faces")
    fc_lines = [l for l in fc_body.splitlines() if l.strip()]
    if len(fc_lines) != fc_n:
        raise BCSetupError(
            f"face count mismatch: parsed {len(fc_lines)} vs declared {fc_n}"
        )

    ow_pre, ow_n, ow_body, ow_post = _split_foam_block(polymesh / "owner")
    ow_lines = [l for l in ow_body.splitlines() if l.strip()]
    if ow_n != fc_n:
        raise BCSetupError(
            f"owner/face count mismatch ({ow_n} vs {fc_n})"
        )

    bnd_face_lines = fc_lines[b_start : b_start + b_n]
    bnd_owner_lines = ow_lines[b_start : b_start + b_n]

    inlet_set = set(inlet_face_ids)
    outlet_set = set(outlet_face_ids)

    inlet_idx: list[int] = []
    outlet_idx: list[int] = []
    wall_idx: list[int] = []
    for i, face_line in enumerate(bnd_face_lines):
        vidx = _parse_face(face_line)
        verts_xyz = [
            (float(pts[v][0]), float(pts[v][1]), float(pts[v][2]))
            for v in vidx
        ]
        fid = compute_face_id(verts_xyz)
        if fid in inlet_set:
            inlet_idx.append(i)
        elif fid in outlet_set:
            outlet_idx.append(i)
        else:
            wall_idx.append(i)

    n_inlet, n_outlet, n_walls = len(inlet_idx), len(outlet_idx), len(wall_idx)
    if n_inlet == 0:
        raise BCSetupError(
            f"no boundary face matched any inlet pin {sorted(inlet_set)} — "
            "did the mesh regenerate after the face was pinned?"
        )
    if n_outlet == 0:
        raise BCSetupError(
            f"no boundary face matched any outlet pin {sorted(outlet_set)} — "
            "did the mesh regenerate after the face was pinned?"
        )
    if n_walls == 0:
        raise BCSetupError(
            "all boundary faces classified as inlet/outlet — channel needs "
            "at least one wall face."
        )
    # Codex DEC-V61-101 R1 HIGH closure: the previous "≥1 matched"
    # check let a partially-stale pin set slip through silently. Prove
    # EVERY face_id in the inlet/outlet sets was actually consumed by
    # the routing, otherwise raise — defends classifier-executor parity
    # exactly the way the LDC R2 fix did.
    consumed_inlet_ids = {
        compute_face_id(
            [
                (float(pts[v][0]), float(pts[v][1]), float(pts[v][2]))
                for v in _parse_face(bnd_face_lines[i])
            ]
        )
        for i in inlet_idx
    }
    consumed_outlet_ids = {
        compute_face_id(
            [
                (float(pts[v][0]), float(pts[v][1]), float(pts[v][2]))
                for v in _parse_face(bnd_face_lines[i])
            ]
        )
        for i in outlet_idx
    }
    missing_inlet = inlet_set - consumed_inlet_ids
    missing_outlet = outlet_set - consumed_outlet_ids
    if missing_inlet or missing_outlet:
        problems = []
        if missing_inlet:
            problems.append(
                f"inlet pin(s) {sorted(missing_inlet)} not on current boundary"
            )
        if missing_outlet:
            problems.append(
                f"outlet pin(s) {sorted(missing_outlet)} not on current boundary"
            )
        raise BCSetupError(
            "stale pins after classifier verification — "
            + "; ".join(problems)
            + " (mesh may have been regenerated mid-flight)."
        )

    new_bnd_faces = (
        [bnd_face_lines[i] for i in inlet_idx]
        + [bnd_face_lines[i] for i in outlet_idx]
        + [bnd_face_lines[i] for i in wall_idx]
    )
    new_bnd_owners = (
        [bnd_owner_lines[i] for i in inlet_idx]
        + [bnd_owner_lines[i] for i in outlet_idx]
        + [bnd_owner_lines[i] for i in wall_idx]
    )

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
        f"3\n(\n"
        f"    inlet\n    {{\n        type            patch;\n"
        f"        nFaces          {n_inlet};\n"
        f"        startFace       {b_start};\n    }}\n"
        f"    outlet\n    {{\n        type            patch;\n"
        f"        nFaces          {n_outlet};\n"
        f"        startFace       {b_start + n_inlet};\n    }}\n"
        f"    walls\n    {{\n        type            wall;\n"
        f"        nFaces          {n_walls};\n"
        f"        startFace       {b_start + n_inlet + n_outlet};\n    }}\n"
        f")\n"
    )
    (polymesh / "boundary").write_text(boundary_str)

    return n_inlet, n_outlet, n_walls, b_start


def _author_channel_dicts(case_dir: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Write the pimpleFoam dict tree for a laminar channel.

    Same physics (laminar incompressible) as the LDC path — only the
    BCs change to inlet/outlet/walls. ν=0.01 keeps the channel laminar
    (Re=U·D/ν=1·1/0.01=100 for the 1×1 cross-section default).

    Returns ``(written, skipped)`` — see `_author_dicts` for the
    user-override semantics; identical here.
    """
    (case_dir / "0").mkdir(exist_ok=True)
    (case_dir / "system").mkdir(exist_ok=True)
    (case_dir / "constant").mkdir(exist_ok=True)

    written: list[str] = []
    skipped: list[str] = []

    def w(rel: str, content: str) -> None:
        if is_user_override(case_dir, relative_path=rel):
            skipped.append(rel)
            return
        (case_dir / rel).write_text(content)
        written.append(rel)

    inlet_u = " ".join(f"{c}" for c in _CHANNEL_INLET_VELOCITY)

    w(
        "0/U",
        f'FoamFile {{ version 2.0; format ascii; class volVectorField; '
        f'location "0"; object U; }}\n'
        f"dimensions      [0 1 -1 0 0 0 0];\n"
        f"internalField   uniform (0 0 0);\n"
        f"boundaryField\n"
        f"{{\n"
        f"    inlet   {{ type fixedValue; value uniform ({inlet_u}); }}\n"
        f"    outlet  {{ type zeroGradient; }}\n"
        f"    walls   {{ type noSlip; }}\n"
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
        "    inlet   { type zeroGradient; }\n"
        "    outlet  { type fixedValue; value uniform 0; }\n"
        "    walls   { type zeroGradient; }\n"
        "}\n",
    )

    w(
        "constant/physicalProperties",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "constant"; object physicalProperties; }\n'
        "transportModel  Newtonian;\n"
        f"nu              [0 2 -1 0 0 0 0] {_CHANNEL_NU};\n",
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
        # pimpleFoam (NOT icoFoam): incompressible laminar transient
        # solver with PISO/PIMPLE hybrid that honors adjustTimeStep.
        # Codex cce9c29 review P1 (2026-04-30): icoFoam in OpenFOAM-10
        # has no setDeltaT.H include, so the adjustTimeStep/maxCo/
        # maxDeltaT keys here would be silently ignored if icoFoam
        # were used — leaving deltaT fixed at the seed value and
        # producing either "5x too many timesteps" (small seed) or
        # "user-reported crawl" (large seed + fine mesh + Courant
        # blowup). pimpleFoam includes setDeltaT.H (verified against
        # /opt/openfoam10/applications/solvers/incompressible/
        # pimpleFoam/pimpleFoam.C) so the keys actually take effect.
        "application pimpleFoam;\n"
        "startFrom startTime;\n"
        "startTime 0;\n"
        "stopAt endTime;\n"
        "endTime 5;\n"
        # Seed deltaT is intentionally larger than the icoFoam-era
        # 0.005 because pimpleFoam will scale it down on the first
        # CourantNo evaluation if the seed is too aggressive. Caps
        # below protect against unbounded scale-up on coarse meshes.
        "deltaT 0.005;\n"
        "writeControl runTime;\n"
        "writeInterval 1;\n"
        "purgeWrite 0;\n"
        "writeFormat ascii;\n"
        "writePrecision 6;\n"
        "writeCompression off;\n"
        "timeFormat general;\n"
        "timePrecision 6;\n"
        "runTimeModifiable true;\n"
        "adjustTimeStep yes;\n"
        "maxCo 0.5;\n"
        # Cap deltaT so even an empty/over-coarse mesh (where Co stays
        # low at any step size) cannot stretch a single timestep past
        # the resolution we want to record residuals at.
        "maxDeltaT 0.05;\n",
    )

    w(
        "system/fvSchemes",
        'FoamFile { version 2.0; format ascii; class dictionary; '
        'location "system"; object fvSchemes; }\n'
        "ddtSchemes  { default Euler; }\n"
        "gradSchemes { default Gauss linear; }\n"
        # pimpleFoam (vs icoFoam) routes through the turbulence
        # model's divDevReff which evaluates ``div((nuEff*dev2(T(grad(U)))))``
        # every step — even with ``simulationType laminar``. Without
        # an explicit scheme here, OpenFOAM-10's createFields aborts
        # on the first timestep with "keyword ... is undefined".
        # Codex a1b5e29 review P1 closure 2026-04-30.
        "divSchemes  { default none; div(phi,U) Gauss linear; "
        "div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n"
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
        "    UFinal { $U; relTol 0; }\n"
        "}\n"
        # pimpleFoam reads ``PIMPLE``, not ``PISO``. Setting
        # nOuterCorrectors=1 makes pimpleFoam behave like icoFoam
        # (single PISO loop per timestep) so the numerics are the
        # closest possible to the icoFoam baseline. Bumping to 2+
        # would enable PIMPLE under-relaxation but is unnecessary
        # for laminar channel flow at modest Re.
        "PIMPLE\n"
        "{\n"
        "    nOuterCorrectors 1;\n"
        "    nCorrectors 2;\n"
        "    nNonOrthogonalCorrectors 2;\n"
        "    pRefCell 0;\n"
        "    pRefValue 0;\n"
        "}\n",
    )

    return tuple(written), tuple(skipped)


def setup_channel_bc(
    case_dir: Path,
    *,
    case_id: str,
    inlet_face_ids: tuple[str, ...],
    outlet_face_ids: tuple[str, ...],
) -> ChannelBCSetupResult:
    """DEC-V61-101: split boundary into inlet/outlet/walls based on
    user-pinned face_ids and author the laminar icoFoam dict tree.

    The classifier must have already verified each face_id is actually
    on the polyMesh boundary (see `_boundary_face_ids` in classifier).
    Defense-in-depth: this function still raises BCSetupError if any
    pin doesn't resolve, so a contract drift between classifier and
    executor is loud rather than silent.

    Idempotent in the same sense as setup_ldc_bc: repeated calls
    classify + sort identically given the same inputs.
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
    if not inlet_face_ids:
        raise BCSetupError("inlet_face_ids is empty — classifier contract violated")
    if not outlet_face_ids:
        raise BCSetupError("outlet_face_ids is empty — classifier contract violated")

    n_inlet, n_outlet, n_walls, _ = _split_channel_patches(
        polymesh, inlet_face_ids, outlet_face_ids
    )
    # Codex round-2 P1-HIGH closure: see setup_ldc_bc — lock the
    # author + manifest-record sequence so concurrent POST /dicts can't
    # race past is_user_override.
    try:
        with case_lock(case_dir):
            written, skipped = _author_channel_dicts(case_dir)
            if written:
                mark_ai_authored(
                    case_dir,
                    relative_paths=list(written),
                    action="setup_channel_bc",
                    detail={"skipped_user_overrides": list(skipped)} if skipped else None,
                )
    except CaseLockError as exc:
        raise BCSetupError(
            f"could not acquire case lock for setup_channel_bc: {exc}"
        ) from exc

    # Codex DEC-V61-101 R1 LOW closure: use the MIN bbox extent as
    # L_char (hydraulic-diameter approximation for narrow channels).
    # Using max-extent inflated Re by 10× on a 1×1×10 fixture (Re=1000)
    # which contradicts the DEC's "Re~100 default" claim. Min-extent
    # gives Re=100 on the same fixture, matching the locked DEC text.
    pts_pre, _, pts_body, _ = _split_foam_block(polymesh / "points")
    pts = _parse_points(pts_body)
    if pts:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        zs = [p[2] for p in pts]
        extents = [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)]
        # Filter out near-zero extents (degenerate axis); fall back to
        # max if all are degenerate (shouldn't happen — classifier
        # would have rejected).
        nonzero = [e for e in extents if e > 1e-9]
        l_char = min(nonzero) if nonzero else max(extents) if extents else 1.0
    else:
        l_char = 1.0
    u_mag = sum(c * c for c in _CHANNEL_INLET_VELOCITY) ** 0.5
    reynolds = u_mag * l_char / _CHANNEL_NU if _CHANNEL_NU > 0 else 0.0

    return ChannelBCSetupResult(
        case_id=case_id,
        case_dir=case_dir,
        n_inlet_faces=n_inlet,
        n_outlet_faces=n_outlet,
        n_wall_faces=n_walls,
        inlet_velocity=_CHANNEL_INLET_VELOCITY,
        nu=_CHANNEL_NU,
        reynolds=reynolds,
        written_files=written,
        skipped_user_overrides=skipped,
    )
