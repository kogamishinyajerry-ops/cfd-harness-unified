"""Per-case face annotations (M-AI-COPILOT Tier-A · DEC-V61-098).

The face_annotations.yaml file is the user-authoritative SSOT for
boundary face naming, BC assignment, and physics notes for an
imported case. AI actions READ this file before deciding; user-
authoritative entries override AI guesses.

Schema (spec_v2 §B.1):

    schema_version: 1
    case_id: <string>
    revision: <int>             # monotonic, bumped on every PUT
    last_modified: <ISO8601>
    faces:
      - face_id: <string · "fid_" + 16-hex>
        name: <string>
        patch_type: "patch" | "wall" | "symmetry" | "empty" | "cyclic"
        bc:
          U: { type: "fixedValue", value: "(...)" }
          p: { type: "zeroGradient" }
        physics_notes: <string>
        confidence: "user_authoritative" | "ai_confident" | "ai_uncertain"
        annotated_by: "human" | "ai:<source>"
        annotated_at: <ISO8601>

face_id is a sha1 hash of the polyMesh face's vertex-coordinate set
(sorted, rounded to 9 decimals to absorb floating-point drift). It is
stable across deterministic mesh regen as long as topology is
unchanged. See ``face_id()`` below.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ui.backend.services.case_annotations._yaml_io import (
    AnnotationsIOError,
    AnnotationsRevisionConflict,
    load_annotations,
    save_annotations,
)

__all__ = [
    "AnnotationsIOError",
    "AnnotationsRevisionConflict",
    "FACE_ID_HASH_LEN",
    "FACE_ID_PREFIX",
    "FACE_ID_ROUND_DECIMALS",
    "SCHEMA_VERSION",
    "empty_annotations",
    "face_id",
    "load_annotations",
    "merge_face",
    "save_annotations",
]


SCHEMA_VERSION = 1
FACE_ID_PREFIX = "fid_"
FACE_ID_HASH_LEN = 16
FACE_ID_ROUND_DECIMALS = 9


def face_id(face_vertices: list[tuple[float, float, float]]) -> str:
    """Return a stable hash for an OpenFOAM polyMesh face.

    Independent of vertex ordering within the face — coordinates are
    rounded then sorted before hashing. As long as ``gmshToFoam`` is
    deterministic (which it is for the same input geometry) and the
    mesh topology hasn't changed, this id survives mesh regen.

    Args:
        face_vertices: list of ``(x, y, z)`` tuples for each vertex on
            the face. Order does not matter.

    Returns:
        A string of the form ``"fid_<16hex>"``.

    Examples:
        >>> v1 = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        >>> v2 = [(1.0, 1.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        >>> face_id(v1) == face_id(v2)  # same face, different vertex order
        True
        >>> face_id(v1).startswith("fid_")
        True
        >>> len(face_id(v1)) == 4 + 16
        True
    """
    rounded = [
        tuple(round(c, FACE_ID_ROUND_DECIMALS) for c in v)
        for v in face_vertices
    ]
    sorted_verts = sorted(rounded)
    h = hashlib.sha1(repr(sorted_verts).encode("utf-8")).hexdigest()
    return f"{FACE_ID_PREFIX}{h[:FACE_ID_HASH_LEN]}"


def empty_annotations(case_id: str) -> dict[str, Any]:
    """Return a fresh annotations document with no faces.

    The ``revision`` starts at 0; the first ``save_annotations`` bumps
    it to 1.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "revision": 0,
        "last_modified": datetime.now(timezone.utc).isoformat(),
        "faces": [],
    }


def merge_face(
    annotations: dict[str, Any],
    new_face: dict[str, Any],
    *,
    annotated_by: str,
) -> dict[str, Any]:
    """Insert or update a face entry in the annotations document.

    Sticky invariant: a face with ``confidence == "user_authoritative"``
    is NOT overwritten by an AI write (``annotated_by`` starting with
    ``"ai:"``). The AI write is silently dropped for that face; the
    caller can detect this by comparing the returned annotations vs the
    input.

    Args:
        annotations: the annotations document (mutated in place AND
            returned for chaining).
        new_face: a face dict with at minimum ``face_id``; other fields
            (``name``, ``patch_type``, ``bc``, ``physics_notes``,
            ``confidence``) are merged.
        annotated_by: source identifier · ``"human"`` or ``"ai:<source>"``
            (e.g. ``"ai:rule-based"``, ``"ai:gpt-4"``).

    Returns:
        The annotations document.
    """
    fid = new_face["face_id"]
    is_ai_write = annotated_by.startswith("ai:")

    existing_face = next(
        (f for f in annotations["faces"] if f["face_id"] == fid), None
    )

    if (
        existing_face is not None
        and existing_face.get("confidence") == "user_authoritative"
        and is_ai_write
    ):
        # Sticky: AI cannot overwrite user-authoritative entries.
        return annotations

    timestamp = datetime.now(timezone.utc).isoformat()
    merged_face = {
        **(existing_face or {}),
        **new_face,
        "annotated_by": annotated_by,
        "annotated_at": timestamp,
    }

    if existing_face is not None:
        annotations["faces"] = [
            merged_face if f["face_id"] == fid else f
            for f in annotations["faces"]
        ]
    else:
        annotations["faces"].append(merged_face)

    annotations["last_modified"] = timestamp
    return annotations


def annotations_path(case_dir: Path) -> Path:
    """Return the canonical annotations file path for a case dir."""
    return case_dir / "face_annotations.yaml"
