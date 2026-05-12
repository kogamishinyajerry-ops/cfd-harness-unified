"""Shared test helpers for ui.backend.tests."""

from __future__ import annotations

import io

import trimesh


def box_stl(size: float = 0.1) -> bytes:
    """Binary-STL bytes for a watertight cube of the given edge length."""
    m = trimesh.creation.box([size, size, size])
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


def open_box_stl() -> bytes:
    """Non-watertight: cube with the first 2 triangles removed (open top)."""
    m = trimesh.creation.box([0.1, 0.1, 0.1])
    open_mesh = trimesh.Trimesh(vertices=m.vertices, faces=m.faces[2:].copy())
    buf = io.BytesIO()
    open_mesh.export(buf, file_type="stl")
    return buf.getvalue()


def seamed_multi_solid_box_stl(
    *,
    inlet: str = "inlet",
    outlet: str = "outlet",
    walls: str = "walls",
    size: float = 0.1,
) -> bytes:
    """Compose an ASCII STL where a single watertight cube is split into
    three named patches whose triangles share seam vertices.

    This mirrors the canonical CAD-export form: ParaView/Salome/FreeCAD
    write one ``solid <name>`` block per surface group of the same body,
    and the inlet/walls/outlet blocks share vertices at the patch seams.
    ``multi_solid_ascii_stl`` (translated disjoint cubes) does NOT
    exercise that seam topology — ``stl_loader.combine`` must call
    ``merge_vertices`` for this case to pass watertight checks.
    """
    import numpy as np

    import re as _re

    box = trimesh.creation.box([size, size, size])
    normals = box.face_normals
    inlet_mask = np.isclose(normals[:, 0], -1.0)
    outlet_mask = np.isclose(normals[:, 0], 1.0)
    walls_mask = ~(inlet_mask | outlet_mask)

    solid_re = _re.compile(rb"^\s*solid\b[^\n]*", _re.MULTILINE)
    endsolid_re = _re.compile(rb"^\s*endsolid\b[^\n]*", _re.MULTILINE)

    chunks: list[bytes] = []
    for name, mask in (
        (inlet, inlet_mask),
        (outlet, outlet_mask),
        (walls, walls_mask),
    ):
        face_index = np.flatnonzero(mask)
        patch = box.submesh([face_index], append=True, repair=False)
        raw = patch.export(file_type="stl_ascii")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        encoded = name.encode("ascii")
        raw = solid_re.sub(b"solid " + encoded, raw, count=1)
        raw = endsolid_re.sub(b"endsolid " + encoded, raw, count=1)
        if not raw.endswith(b"\n"):
            raw += b"\n"
        chunks.append(raw)
    return b"".join(chunks)


def large_seamed_multi_solid_box_stl(
    *,
    subdivisions: int = 5,
    inlet: str = "inlet",
    outlet: str = "outlet",
    walls: str = "walls",
    size: float = 0.1,
) -> bytes:
    """Industrial-scale variant of :func:`seamed_multi_solid_box_stl`.

    Subdivides the base 12-facet box ``subdivisions`` times (4× per iter)
    so the total facet count crosses the F2 path activation threshold
    (``_F2_PATH_FACET_THRESHOLD = 10_000``). At ``subdivisions=5`` the
    total is 12,288 facets (4096 per ±x-normal patch, 4096 per +x, 4096
    on the 4 walls combined) — just over threshold so F2 activates
    without monkeypatching.

    Used by session 9 to validate F2 path on a fixture that:
      - trips the real activation gate (no monkeypatch needed)
      - is clean (no overlap, no self-intersection — unlike case_003's
        Codex-generated source per session 8 F-NEW-26 finding)
      - exercises the named-solid voting block at scale
    """
    import numpy as np
    import re as _re

    box = trimesh.creation.box([size, size, size])
    for _ in range(subdivisions):
        box = box.subdivide()
    normals = box.face_normals
    inlet_mask = np.isclose(normals[:, 0], -1.0)
    outlet_mask = np.isclose(normals[:, 0], 1.0)
    walls_mask = ~(inlet_mask | outlet_mask)

    solid_re = _re.compile(rb"^\s*solid\b[^\n]*", _re.MULTILINE)
    endsolid_re = _re.compile(rb"^\s*endsolid\b[^\n]*", _re.MULTILINE)

    chunks: list[bytes] = []
    for name, mask in (
        (inlet, inlet_mask),
        (outlet, outlet_mask),
        (walls, walls_mask),
    ):
        face_index = np.flatnonzero(mask)
        patch = box.submesh([face_index], append=True, repair=False)
        raw = patch.export(file_type="stl_ascii")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        encoded = name.encode("ascii")
        raw = solid_re.sub(b"solid " + encoded, raw, count=1)
        raw = endsolid_re.sub(b"endsolid " + encoded, raw, count=1)
        if not raw.endswith(b"\n"):
            raw += b"\n"
        chunks.append(raw)
    return b"".join(chunks)


def cube_with_interior_obstacle_stl(
    *,
    outer_size: float = 1.0,
    inner_size: float = 0.2,
) -> bytes:
    """Two concentric cubes as a single multi-solid binary STL: outer
    cavity (size ``outer_size``) + interior obstacle (size
    ``inner_size``). DEC-V61-104 fixture: exercises the topology
    partitioner's ability to identify two connected bodies and treat
    the smaller-bbox one as a hole.

    Both cubes are emitted with standard outward-facing normals (default
    trimesh orientation). gmsh's ``addVolume([outer_loop, -inner_loop])``
    handles the orientation reversal needed to mark the inner body as a
    hole rather than a second fluid region.
    """
    outer = trimesh.creation.box([outer_size, outer_size, outer_size])
    inner = trimesh.creation.box([inner_size, inner_size, inner_size])
    combined = trimesh.util.concatenate([outer, inner])
    buf = io.BytesIO()
    combined.export(buf, file_type="stl")
    return buf.getvalue()


def farfield_6_plate_stl(
    *,
    domain: float = 10.0,
    thickness: float = 0.5,
) -> bytes:
    """F-NEW-26 reproduction: 6 thick plates at the 6 faces of a CFD
    domain cuboid, emitted as a named-solid ASCII multi-solid STL.

    The plates' AABBs overlap at the 12 cube edges + 8 corners (the
    systematic CAD bug signature documented in
    ``.planning/cross_repo_tickets/2026-05-12_case_003_build_cad_farfield_overlap.md``).
    Each plate is an individually-watertight box; their faces
    interpenetrate at corners, but ``combine`` keeps the merged mesh
    watertight (each shell's edges still pair within itself), so the
    ``run_health_checks`` watertight branch passes and the F-NEW-26
    error is the only failure surfaced to the route.

    With ``domain=10`` and ``thickness=0.5`` the plates are far enough
    apart to keep the per-pair intersection volume small enough to be
    classified ``edge_overlap`` rather than ``significant`` (≥25% of
    smaller body's volume).
    """
    import re as _re

    L = domain
    t = thickness
    plates_specs: list[tuple[str, list[float], list[float]]] = [
        ("inlet",           [t,       L,       L],     [0.0,   L / 2, L / 2]),
        ("outlet",          [t,       L,       L],     [L,     L / 2, L / 2]),
        ("symmetry",        [L,       t,       L],     [L / 2, 0.0,   L / 2]),
        ("farfield_outer",  [L,       t,       L],     [L / 2, L,     L / 2]),
        ("farfield_bottom", [L,       L,       t],     [L / 2, L / 2, 0.0]),
        ("farfield_top",    [L,       L,       t],     [L / 2, L / 2, L]),
    ]

    solid_re = _re.compile(rb"^\s*solid\b[^\n]*", _re.MULTILINE)
    endsolid_re = _re.compile(rb"^\s*endsolid\b[^\n]*", _re.MULTILINE)

    chunks: list[bytes] = []
    for name, size, center in plates_specs:
        m = trimesh.creation.box(size)
        m.apply_translation(center)
        raw = m.export(file_type="stl_ascii")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        encoded = name.encode("ascii")
        raw = solid_re.sub(b"solid " + encoded, raw, count=1)
        raw = endsolid_re.sub(b"endsolid " + encoded, raw, count=1)
        if not raw.endswith(b"\n"):
            raw += b"\n"
        chunks.append(raw)
    return b"".join(chunks)


def multi_solid_ascii_stl(*names: str) -> bytes:
    """Compose a multi-solid ASCII STL with the given solid names. Each
    solid is a translated cube so trimesh ingests them as distinct
    geometries in a Scene."""
    if not names:
        raise ValueError("multi_solid_ascii_stl requires at least one name")
    chunks: list[bytes] = []
    for i, name in enumerate(names):
        m = trimesh.creation.box([0.1, 0.1, 0.1])
        m.apply_translation([0.2 * i, 0.0, 0.0])
        ascii_bytes = m.export(file_type="stl_ascii")
        if isinstance(ascii_bytes, str):
            ascii_bytes = ascii_bytes.encode("utf-8")
        # Rewrite first `solid` line + last `endsolid` line to carry the
        # caller's chosen name. trimesh emits a generic placeholder.
        text = ascii_bytes.decode("utf-8").splitlines()
        for j, line in enumerate(text):
            if line.lstrip().lower().startswith("solid"):
                text[j] = f"solid {name}"
                break
        for j in range(len(text) - 1, -1, -1):
            if text[j].lstrip().lower().startswith("endsolid"):
                text[j] = f"endsolid {name}"
                break
        chunks.append(("\n".join(text) + "\n").encode("utf-8"))
    return b"".join(chunks)
