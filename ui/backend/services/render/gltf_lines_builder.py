"""Minimal binary glTF 2.0 (.glb) builder for a single LINES primitive.

M-RENDER-API spec_v2 §B.2 (DEC-V61-095). trimesh.export only handles
triangle meshes; for the polyMesh wireframe endpoint we need
``mode: LINES``, so we assemble the glb directly using stdlib only.

glTF 2.0 binary layout:

    [12-byte header]
        uint32 magic   = 0x46546C67  ('glTF')
        uint32 version = 2
        uint32 length  = total file size

    [JSON chunk]
        uint32 chunk_length
        uint32 chunk_type = 0x4E4F534A  ('JSON')
        bytes  chunk_data         (UTF-8 JSON, padded to 4-byte alignment with 0x20)

    [BIN chunk]
        uint32 chunk_length
        uint32 chunk_type = 0x004E4942  ('BIN\\0')
        bytes  chunk_data         (binary buffer, padded to 4-byte alignment with 0x00)

References:
    - glTF 2.0 spec: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
    - GLB layout: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#binary-gltf-layout
"""
from __future__ import annotations

import json
import struct

import numpy as np


_GLB_MAGIC = 0x46546C67          # 'glTF'
_JSON_CHUNK_TYPE = 0x4E4F534A    # 'JSON'
_BIN_CHUNK_TYPE = 0x004E4942     # 'BIN\0'

# glTF accessor componentType values
_COMPONENT_FLOAT = 5126           # FLOAT  (4 bytes)
_COMPONENT_UNSIGNED_INT = 5125    # UNSIGNED_INT (4 bytes)

# glTF buffer-view target values
_TARGET_ARRAY_BUFFER = 34962
_TARGET_ELEMENT_ARRAY_BUFFER = 34963

# glTF primitive mode values
_MODE_LINES = 1


def _pad_to_4(payload: bytes, fill: bytes) -> bytes:
    """Pad ``payload`` to a 4-byte boundary using ``fill``."""
    rem = (4 - (len(payload) % 4)) % 4
    if rem:
        payload = payload + fill * rem
    return payload


def build_lines_glb(points: np.ndarray, edges: np.ndarray) -> bytes:
    """Return a binary glTF (.glb) carrying the LINES primitive.

    ``points``: ``(N, 3)`` float-compatible — coerced to float32.
    ``edges``: ``(M, 2)`` uint-compatible — coerced to uint32. Each row
    is a vertex-pair (start, end). The resulting primitive uses
    ``mode: LINES``, which renders each consecutive index pair as a
    discrete line segment.
    """
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points must be (N, 3); got {points.shape}")
    if edges.ndim != 2 or edges.shape[1] != 2:
        raise ValueError(f"edges must be (M, 2); got {edges.shape}")
    if len(points) == 0 or len(edges) == 0:
        raise ValueError("points and edges must each be non-empty")

    points32 = np.ascontiguousarray(points, dtype=np.float32)
    indices32 = np.ascontiguousarray(edges.reshape(-1), dtype=np.uint32)

    points_bytes = points32.tobytes()
    indices_bytes = indices32.tobytes()

    # bufferViews are concatenated into one buffer; each view starts
    # at a 4-byte boundary (both 5126 FLOAT and 5125 UINT are 4-byte
    # aligned naturally, but pad defensively in case of future formats).
    points_offset = 0
    indices_offset = len(points_bytes)
    if indices_offset % 4 != 0:
        pad = (4 - (indices_offset % 4)) % 4
        points_bytes = points_bytes + b"\x00" * pad
        indices_offset = len(points_bytes)

    buffer_payload = points_bytes + indices_bytes
    total_buffer_len = len(buffer_payload)

    p_min = points32.min(axis=0).tolist()
    p_max = points32.max(axis=0).tolist()

    gltf_json = {
        "asset": {"version": "2.0", "generator": "cfd-harness M-RENDER-API"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "mode": _MODE_LINES,
                    }
                ]
            }
        ],
        "buffers": [{"byteLength": total_buffer_len}],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": points_offset,
                "byteLength": len(points32.tobytes()),
                "target": _TARGET_ARRAY_BUFFER,
            },
            {
                "buffer": 0,
                "byteOffset": indices_offset,
                "byteLength": len(indices_bytes),
                "target": _TARGET_ELEMENT_ARRAY_BUFFER,
            },
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": _COMPONENT_FLOAT,
                "count": len(points32),
                "type": "VEC3",
                "min": p_min,
                "max": p_max,
            },
            {
                "bufferView": 1,
                "componentType": _COMPONENT_UNSIGNED_INT,
                "count": len(indices32),
                "type": "SCALAR",
            },
        ],
    }

    json_bytes = json.dumps(gltf_json, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    json_chunk = _pad_to_4(json_bytes, b" ")
    bin_chunk = _pad_to_4(buffer_payload, b"\x00")

    json_chunk_header = struct.pack("<II", len(json_chunk), _JSON_CHUNK_TYPE)
    bin_chunk_header = struct.pack("<II", len(bin_chunk), _BIN_CHUNK_TYPE)

    total_length = (
        12  # GLB header
        + 8 + len(json_chunk)
        + 8 + len(bin_chunk)
    )

    glb_header = struct.pack("<III", _GLB_MAGIC, 2, total_length)

    return (
        glb_header
        + json_chunk_header + json_chunk
        + bin_chunk_header + bin_chunk
    )
