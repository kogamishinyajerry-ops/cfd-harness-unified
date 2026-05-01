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
