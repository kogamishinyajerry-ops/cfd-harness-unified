"""OpenFOAM polyMesh + wallShearStress parser — pure functions.

Sub-commit 2d Layer-2: extract per-face `(x_m, tau_w_magnitude)` rows on a
named boundary patch by parsing `constant/polyMesh/{points,faces,boundary}`
plus `<time>/wallShearStress`. Pure Python — no docker, no OpenFOAM bindings.

Why parse the files directly instead of running `postProcess -func`?

  1. The trust harness must work post-mortem on any case dir, including
     ones produced by an OpenFOAM version slightly different from the
     image we'd otherwise need to invoke.
  2. Adding another docker invocation per `cfdtrust run` doubles
     wall-clock cost on Apple Silicon emulation.
  3. The OpenFOAM file format is documented + stable; the docker post-
     processing CLI surface is not.

Scope discipline: this module ONLY knows how to extract enough geometry
+ field data to drive `flat_plate_cf.compare_against_reference`. It is
NOT a general-purpose OpenFOAM reader. Wider needs (cell-centered
fields, time-history, parallel-decomposed cases) belong in a later phase.

Honesty contract:
  - Every parse function raises `ValueError` with the offending file +
    excerpt rather than returning silently-empty data.
  - `extract_wall_cf` BLOCKS with a structured reason if any required
    file is missing — refuses to fabricate Cf from nothing.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


# ---------- low-level OpenFOAM-ascii primitives ----------


# OpenFOAM ascii files start with a `FoamFile { ... }` header block. After
# that comes the payload, which for these three files begins with an integer
# `N` (count) followed by `(` ... `)`.
_FOAMFILE_BLOCK_RE = re.compile(r"FoamFile\s*\{[^}]*\}", re.DOTALL)
# R16-F-02 fix: detect binary format at parse time. OpenFOAM emits binary
# when `writeFormat binary;` is set in controlDict. This parser only
# handles ASCII; surface that as a structured BLOCK instead of a confusing
# downstream parse error.
_BINARY_FORMAT_RE = re.compile(r"\bformat\s+binary\s*;")


def _assert_ascii_foamfile(text: str, filename: str) -> None:
    """Raise ValueError if `text` declares `format binary` in its
    FoamFile header. The pure-Python parsers in this module read only
    ASCII; binary OpenFOAM data files use a different layout that we
    do NOT silently mis-parse."""
    # Look for the FoamFile block first; if there's no header at all
    # we let the downstream parser surface its own error.
    m = _FOAMFILE_BLOCK_RE.search(text)
    if m is None:
        return
    block = m.group(0)
    if _BINARY_FORMAT_RE.search(block):
        raise ValueError(
            f"{filename}: declares `format binary` in FoamFile header; "
            "the cfdtrust wall_shear parser only handles ASCII. "
            "Set `writeFormat ascii;` in system/controlDict and re-run."
        )


def _strip_comments_and_header(text: str) -> str:
    """Remove OpenFOAM comments (`//` to EOL and `/* ... */`) AND the
    FoamFile { ... } header block. The remaining payload is what every
    polyMesh parser actually needs to scan.

    Done as a string transform rather than a tokenizer because the files
    we care about (points, faces, boundary, wallShearStress) are simple
    enough that a tokenizer would be over-engineering.
    """
    # Block comments first (greedy across newlines).
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments.
    text = re.sub(r"//[^\n]*", "", text)
    # FoamFile header.
    text = _FOAMFILE_BLOCK_RE.sub("", text, count=1)
    return text


def _parse_count_paren_block(payload: str) -> Tuple[int, str]:
    """Find the first ``<int> ( ... )`` block in `payload` and return
    `(int, inner_text)`. Used for points (N + N vectors), faces (N + N
    face-records), and the `value nonuniform List<...> N ( ... )` body of
    boundary-field entries.

    Raises ValueError if no such block can be located.
    """
    # Match: optional `List<...>` discriminant, then count, then `(...)`.
    m = re.search(
        r"(?:List<[a-zA-Z<>]+>\s*)?(\d+)\s*\(", payload
    )
    if m is None:
        raise ValueError(
            "expected '<int> (' block; first 200 chars: "
            + repr(payload[:200])
        )
    n = int(m.group(1))
    open_idx = m.end() - 1  # index of '('
    # Find matching ')'. Parens nest inside vector tuples `(x y z)`.
    depth = 0
    for i in range(open_idx, len(payload)):
        c = payload[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return n, payload[open_idx + 1: i]
    raise ValueError("unbalanced parentheses in count-paren block")


# ---------- polyMesh/{boundary, faces, points} parsers ----------


def parse_polymesh_boundary(text: str, filename: str = "boundary") -> Dict[str, Dict[str, int]]:
    """Parse `constant/polyMesh/boundary` and return a patch-name → metadata
    map: ``{name: {"startFace": int, "nFaces": int}}``.

    Example input shape (post-strip):
        5
        (
            inlet { type patch; nFaces 60; startFace 11840; }
            ...
            wall  { type wall;  nFaces 100; startFace 11960; }
            ...
        )
    """
    _assert_ascii_foamfile(text, filename)
    payload = _strip_comments_and_header(text)
    _, inner = _parse_count_paren_block(payload)
    # Each patch entry is `name { ... }`. Names are valid OpenFOAM words
    # (alphanumeric + underscore).
    out: Dict[str, Dict[str, int]] = {}
    # Iterate over `<name> { ... }` blocks.
    for m in re.finditer(r"(\w+)\s*\{([^{}]*)\}", inner):
        name = m.group(1)
        block = m.group(2)
        # Extract nFaces and startFace from the block body.
        nf_match = re.search(r"\bnFaces\s+(\d+)\s*;", block)
        sf_match = re.search(r"\bstartFace\s+(\d+)\s*;", block)
        if nf_match is None or sf_match is None:
            raise ValueError(
                f"boundary patch {name!r} missing nFaces or startFace: {block!r}"
            )
        out[name] = {
            "startFace": int(sf_match.group(1)),
            "nFaces": int(nf_match.group(1)),
        }
    if not out:
        raise ValueError("no patches found in boundary file")
    return out


def parse_polymesh_points(text: str, filename: str = "points") -> List[Tuple[float, float, float]]:
    """Parse `constant/polyMesh/points` → list of `(x, y, z)` tuples,
    indexed in the same order they appear in the file (the implicit
    mesh point index)."""
    _assert_ascii_foamfile(text, filename)
    payload = _strip_comments_and_header(text)
    n, inner = _parse_count_paren_block(payload)
    pts: List[Tuple[float, float, float]] = []
    for m in re.finditer(r"\(\s*([^()\s]+)\s+([^()\s]+)\s+([^()\s]+)\s*\)", inner):
        pts.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    if len(pts) != n:
        raise ValueError(
            f"points: declared {n} but parsed {len(pts)} vertices"
        )
    return pts


def parse_polymesh_faces(text: str, filename: str = "faces") -> List[List[int]]:
    """Parse `constant/polyMesh/faces` → list of face vertex-index lists.

    Each face line is shaped `K(v0 v1 ... v_{K-1})` where K is the vertex
    count. OpenFOAM mesh faces in 3D are typically K=4 (quad) for
    structured blockMesh, but K is honored as-declared.
    """
    _assert_ascii_foamfile(text, filename)
    payload = _strip_comments_and_header(text)
    n, inner = _parse_count_paren_block(payload)
    faces: List[List[int]] = []
    # Pattern matches `K(<verts>)` where verts is whitespace-separated ints.
    for m in re.finditer(r"(\d+)\s*\(([^()]+)\)", inner):
        k = int(m.group(1))
        verts = m.group(2).split()
        if len(verts) != k:
            raise ValueError(
                f"face record declared {k} verts but parsed {len(verts)}: {m.group(0)!r}"
            )
        faces.append([int(v) for v in verts])
    if len(faces) != n:
        raise ValueError(
            f"faces: declared {n} but parsed {len(faces)} face records"
        )
    return faces


# ---------- wallShearStress boundary field parser ----------


def parse_boundary_field_vectors(text: str, patch_name: str, filename: str = "wallShearStress") -> List[Tuple[float, float, float]]:
    """Parse a `<time>/wallShearStress` (or any volVectorField) file and
    return the per-face vector values on the named patch.

    OpenFOAM 11 boundary-field block shape:

        boundaryField
        {
            wall
            {
                type            calculated;
                value           nonuniform List<vector>
        100
        (
        (tx0 ty0 tz0)
        ...
        )
        ;
            }
            ...
        }

    Raises ValueError if the patch is missing OR the value block is
    `uniform` (calling code requires per-face data; a uniform field is a
    sign that the FO didn't fire on this run, which is itself a BLOCK
    condition).
    """
    _assert_ascii_foamfile(text, filename)
    payload = _strip_comments_and_header(text)
    # Find the `boundaryField { ... }` block. We use a depth-counter walk
    # because the block can contain nested `{ ... }` for each patch.
    bf_start = payload.find("boundaryField")
    if bf_start < 0:
        raise ValueError("wallShearStress file has no boundaryField block")
    brace_open = payload.find("{", bf_start)
    if brace_open < 0:
        raise ValueError("boundaryField block missing opening brace")
    depth = 0
    brace_close = -1
    for i in range(brace_open, len(payload)):
        c = payload[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                brace_close = i
                break
    if brace_close < 0:
        raise ValueError("boundaryField block has unbalanced braces")
    bf_body = payload[brace_open + 1: brace_close]

    # Inside bf_body, find `<patch_name> { ... }`. Patch blocks may contain
    # other braces (in rare cases). Use same depth-counter walk.
    pn_match = re.search(rf"\b{re.escape(patch_name)}\b\s*\{{", bf_body)
    if pn_match is None:
        raise ValueError(
            f"patch {patch_name!r} not found in boundaryField"
        )
    p_open = pn_match.end() - 1
    p_depth = 0
    p_close = -1
    for i in range(p_open, len(bf_body)):
        c = bf_body[i]
        if c == "{":
            p_depth += 1
        elif c == "}":
            p_depth -= 1
            if p_depth == 0:
                p_close = i
                break
    if p_close < 0:
        raise ValueError(f"patch {patch_name!r} block has unbalanced braces")
    patch_body = bf_body[p_open + 1: p_close]

    # `value uniform (x y z)` → BLOCK condition.
    if re.search(r"value\s+uniform\b", patch_body):
        raise ValueError(
            f"patch {patch_name!r} has a uniform value block — the wallShearStress "
            "FO did not emit per-face data; this is a BLOCK condition not a "
            "PASS-with-zeros."
        )

    # `value nonuniform List<vector> N ( ... )`.
    value_start = re.search(r"value\s+nonuniform", patch_body)
    if value_start is None:
        # `value` could be absent entirely for `calculated` type
        # without a written field. BLOCK.
        raise ValueError(
            f"patch {patch_name!r} has no nonuniform value block — "
            "wallShearStress FO did not produce per-face data."
        )
    after_value = patch_body[value_start.end():]
    n, inner = _parse_count_paren_block(after_value)
    vectors: List[Tuple[float, float, float]] = []
    for m in re.finditer(r"\(\s*([^()\s]+)\s+([^()\s]+)\s+([^()\s]+)\s*\)", inner):
        vectors.append((float(m.group(1)), float(m.group(2)), float(m.group(3))))
    if len(vectors) != n:
        raise ValueError(
            f"patch {patch_name!r}: declared {n} vectors but parsed {len(vectors)}"
        )
    return vectors


# ---------- geometry helper ----------


def face_centers(
    points: List[Tuple[float, float, float]],
    faces: List[List[int]],
    start: int,
    count: int,
) -> List[Tuple[float, float, float]]:
    """Return the centroid (mean of vertices) of each of the `count` faces
    starting at face index `start`. Indices reference `faces` (flat list)
    and the vertex indices in each face reference `points`."""
    out: List[Tuple[float, float, float]] = []
    for fi in range(start, start + count):
        if fi < 0 or fi >= len(faces):
            raise ValueError(
                f"face index {fi} out of range [0, {len(faces)})"
            )
        verts = faces[fi]
        if not verts:
            raise ValueError(f"face {fi} has zero vertices")
        sx = sy = sz = 0.0
        for vi in verts:
            if vi < 0 or vi >= len(points):
                raise ValueError(
                    f"face {fi} references vertex {vi} out of range [0, {len(points)})"
                )
            x, y, z = points[vi]
            sx += x; sy += y; sz += z
        k = float(len(verts))
        out.append((sx / k, sy / k, sz / k))
    return out


# ---------- top-level orchestration ----------


def extract_wall_cf(
    case_dir: Path,
    time: str,
    *,
    patch: str = "wall",
    u_inf_m_s: float,
) -> List[Tuple[float, float]]:
    """Read polyMesh + `<time>/wallShearStress` and return a list of
    `(x_m, Cf)` rows for the named patch, sorted by x.

    Cf is computed from the wall shear stress magnitude using the
    incompressible-CFD convention:

        Cf = |tau_w| / (0.5 * U_inf^2)

    (OpenFOAM's `wallShearStress` FO writes `tau_w / rho` — i.e. the
    KINEMATIC wall shear stress — because the underlying solver
    `simpleFoam` operates on the kinematic pressure. Hence rho cancels
    out of the standard Cf definition; we do NOT include it. This is the
    same convention NASA TMR's CFL3D Cf data follows.)

    Raises FileNotFoundError if any required file is missing.
    """
    if u_inf_m_s <= 0:
        raise ValueError(f"u_inf_m_s must be positive, got {u_inf_m_s!r}")

    pm_dir = case_dir / "constant" / "polyMesh"
    wss_path = case_dir / time / "wallShearStress"

    for required in (pm_dir / "boundary", pm_dir / "faces", pm_dir / "points", wss_path):
        if not required.exists():
            raise FileNotFoundError(
                f"required OpenFOAM file missing: {required.relative_to(case_dir)}"
            )

    boundary = parse_polymesh_boundary((pm_dir / "boundary").read_text())
    if patch not in boundary:
        raise ValueError(
            f"patch {patch!r} not in polyMesh/boundary; available: {sorted(boundary)}"
        )
    meta = boundary[patch]
    start = meta["startFace"]
    count = meta["nFaces"]

    points = parse_polymesh_points((pm_dir / "points").read_text())
    faces = parse_polymesh_faces((pm_dir / "faces").read_text())

    centers = face_centers(points, faces, start, count)

    wss = parse_boundary_field_vectors(wss_path.read_text(), patch)
    if len(wss) != count:
        raise ValueError(
            f"patch {patch!r}: boundary declared {count} faces but "
            f"wallShearStress has {len(wss)} vector values"
        )

    q_inf = 0.5 * u_inf_m_s * u_inf_m_s
    rows: List[Tuple[float, float]] = []
    for (cx, _, _), (tx, ty, tz) in zip(centers, wss):
        tau_mag = (tx * tx + ty * ty + tz * tz) ** 0.5
        cf = tau_mag / q_inf
        rows.append((cx, cf))

    rows.sort(key=lambda r: r[0])
    return rows
