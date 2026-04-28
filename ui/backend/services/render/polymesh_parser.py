"""Minimal ASCII polyMesh parser — points + faces only.

Tier-A scope (M-RENDER-API spec_v2 §B.2): parse OpenFOAM ASCII
``constant/polyMesh/points`` and ``constant/polyMesh/faces`` files into
numpy arrays so the wireframe builder can extract unique edges.

Scope explicitly NOT covered (deferred):
    - binary polyMesh format (read uncompressed ASCII only)
    - gzipped polyMesh files (.gz)
    - owner / neighbour / boundary / cellZones (wireframe doesn't need them)
    - patch-aware edge tagging (M-VIZ.advanced)

OpenFOAM ASCII grammar relevant to us:

    FoamFile
    {
        version     2.0;
        format      ascii;
        class       vectorField;        // for points / faceList for faces
        location    "constant/polyMesh";
        object      points;
    }

    8                                    // count
    (
    (0 0 0)                              // entry · format depends on class
    (1 0 0)
    ...
    )

We parse the count line + the parenthesized list. Anything before the
count (including the FoamFile dict, blank lines, and ``// ...`` /
``/* ... */`` comments) is skipped. This works for the M6.0
gmsh-toFoam output we expect to consume.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np


_POINT_RE = re.compile(
    r"\(\s*(?P<x>-?\d+\.?\d*(?:[eE][+-]?\d+)?)"
    r"\s+(?P<y>-?\d+\.?\d*(?:[eE][+-]?\d+)?)"
    r"\s+(?P<z>-?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*\)"
)
# faces are <count>(v0 v1 ... v_{count-1}) — count is a separate
# integer prefix, not part of the parenthesised vertex list itself.
_FACE_RE = re.compile(r"(\d+)\s*\(\s*([\d\s]+?)\s*\)")


class PolyMeshParseError(ValueError):
    """Raised when the polyMesh ASCII file cannot be parsed.

    The message is route-safe (carries no untrusted user input verbatim
    beyond a path basename) so it can flow through HTTPException detail.
    """


def _strip_comments(text: str) -> str:
    """Drop ``// ...`` and ``/* ... */`` so our regexes don't trip on them."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _strip_foamfile_header(text: str) -> str:
    """Drop the leading ``FoamFile { ... }`` dict if present.

    We do NOT need any header field for wireframe assembly, so the
    cheapest correct strategy is to find the first ``{`` after the
    optional ``FoamFile`` token and skip to its matching ``}``.
    """
    m = re.search(r"\bFoamFile\b", text)
    if not m:
        return text
    open_idx = text.find("{", m.end())
    if open_idx < 0:
        return text
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1 :]
    return text


def parse_points(points_path: Path) -> np.ndarray:
    """Return an ``(N, 3)`` float64 array of vertex coordinates."""
    raw = points_path.read_text(encoding="utf-8", errors="replace")
    body = _strip_foamfile_header(_strip_comments(raw))
    matches = _POINT_RE.findall(body)
    if not matches:
        raise PolyMeshParseError(
            f"no point entries parsed from {points_path.name}"
        )
    arr = np.asarray(matches, dtype=np.float64)
    return arr


def parse_faces(faces_path: Path) -> list[list[int]]:
    """Return a list of faces; each face is a list of vertex indices.

    OpenFOAM faces are general polygons (3+ vertices). We do NOT require
    triangles or quads.
    """
    raw = faces_path.read_text(encoding="utf-8", errors="replace")
    body = _strip_foamfile_header(_strip_comments(raw))
    faces: list[list[int]] = []
    for count_str, payload in _FACE_RE.findall(body):
        verts = [int(v) for v in payload.split() if v]
        if int(count_str) != len(verts):
            raise PolyMeshParseError(
                f"face count {count_str} did not match payload length {len(verts)} "
                f"in {faces_path.name}"
            )
        if len(verts) < 3:
            raise PolyMeshParseError(
                f"face with <3 vertices in {faces_path.name}"
            )
        faces.append(verts)
    if not faces:
        raise PolyMeshParseError(
            f"no face entries parsed from {faces_path.name}"
        )
    return faces


def validate_face_indices(faces: list[list[int]], n_points: int) -> None:
    """Raise PolyMeshParseError if any face references a point ID outside [0, n_points).

    Round-2 Finding 4: ``parse_faces`` only enforces face arity against
    its count prefix. A malformed face like ``4(0 1 2 999)`` (with
    n_points = 8) survived parsing; downstream the indices accessor
    in the LINES glTF would point past the POSITION buffer. This
    validator runs after ``parse_points`` + ``parse_faces`` so callers
    have ``n_points`` available for the bound check.

    Negative indices (which can't appear via the regex but could appear
    if the parser is ever extended) are also rejected.
    """
    if n_points <= 0:
        raise PolyMeshParseError(
            f"refusing to validate faces against n_points={n_points}"
        )
    for face_idx, verts in enumerate(faces):
        for v in verts:
            if v < 0 or v >= n_points:
                raise PolyMeshParseError(
                    f"face {face_idx} references vertex {v} but only "
                    f"{n_points} points were parsed"
                )


def extract_unique_edges(faces: list[list[int]]) -> np.ndarray:
    """Return an ``(M, 2)`` uint32 array of unique vertex-pair edges.

    Each face contributes its closed-ring edges (v0-v1, v1-v2, ...,
    v_{n-1}-v0). Edges are deduplicated by sorted-pair so (a, b) and
    (b, a) collapse into a single entry. The output ordering is
    deterministic (sorted lexicographically) so cache hashes are
    stable and tests can assert exact arrays.
    """
    seen: set[tuple[int, int]] = set()
    for face in faces:
        n = len(face)
        for i in range(n):
            a = face[i]
            b = face[(i + 1) % n]
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            seen.add(key)
    if not seen:
        raise PolyMeshParseError("face list produced zero edges")
    edges = np.asarray(sorted(seen), dtype=np.uint32)
    return edges
