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
