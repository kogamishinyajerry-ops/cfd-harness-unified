"""Virtual interface detector — geometric face matching across bodies.

Replaces case-local APU bay implementation
(``~/Desktop/apu-bay-ventilation/scripts/02_domain_subtract.py:92``)
with a generalized advisor. V2 finding: BREP 1:1 face matching fails
on non-manifold STEP exports; geometric heuristics (bbox / area /
normal) are robust where ``isSame()`` is not.

Two-layer design: algorithm functions on ``FaceGeometry`` (no FreeCAD
coupling); ``InterfaceSpec`` driver mirrors APU bay's config format.

V2 lesson: ``isSame()`` is NOT a fast-path — that reintroduces the bug.
V25 (closed by A2-v2): the v1 ``_run_shared`` returned hardcoded
``bbox_overlap_fraction=1.0`` and ``area_diff_fraction=0.0`` placeholder
fields regardless of actual face geometry, and never computed inter-face
gap. A2-v2 replaces the placeholders with real measurements and adds an
``inter_face_gap_mm`` field plus the
``should_have_been_shared_with_unintended_gap`` classifier — the
D1-class defect detector that case_003/004/005-v2/007/008/009/010/011/
012/015 PASS-with-placeholder reports were assumed (incorrectly) to
field-validate.

API contract: ``matched=True`` means A2 found facing-face candidates on
the planar-parallel geometry. ``inter_face_gap_mm`` carries the real
gap when both bodies contributed a facing face; the classifier above
converts gap to PASS/WARN/DEFECT verdict. ``matched=True`` is no longer
the defect-detection signal on its own — engineers must check the
classifier output.

V130/V132: read-only metadata, no mutating routes.
References: V2, V19, V25, V79 in ``industrial_case_solver_findings.md``;
sub-DEC V61-198-sub-A2v2-gap-detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

DEFAULT_BBOX_OVERLAP_MIN = 0.80
DEFAULT_AREA_DIFF_MAX = 0.05
DEFAULT_SHARED_NORMAL_DOT_MAX = -0.5
DEFAULT_FACING_DOT_MIN = 0.5
DEFAULT_ENDCAP_AXIS_DOT_MIN = 0.9


@dataclass(frozen=True)
class FaceGeometry:
    """Minimal face features for geometric (not topological) matching."""
    area: float
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    normal: tuple[float, float, float]
    centroid: tuple[float, float, float]


@dataclass(frozen=True)
class BodyGeometry:
    """One body — its planar faces + centroid."""
    name: str
    faces: tuple[FaceGeometry, ...]
    centroid: tuple[float, float, float]


@dataclass(frozen=True)
class InterfaceSpec:
    """``mode='shared'``: two bodies share an interface plane.
    ``mode='endcap'``: planar face aligned with ``axis`` (e.g. ``'+x'``).
    """
    patch_name: str
    mode: str
    body_a: str | None = None
    body_b: str | None = None
    body: str | None = None
    axis: str | None = None


@dataclass(frozen=True)
class DetectedInterface:
    """Per-spec detection result.

    A2-v2 added ``inter_face_gap_mm``: perpendicular distance between
    the two facing faces when both bodies contributed one, else None.
    Use ``should_have_been_shared_with_unintended_gap`` to classify
    D1-class defects (matched=True ∧ 0 < gap < threshold).
    """
    patch_name: str
    matched: bool
    body_owner: str | None
    face: FaceGeometry | None
    bbox_overlap_fraction: float
    area_diff_fraction: float
    normal_dot: float
    diagnostic: str
    inter_face_gap_mm: float | None = None


def bbox_overlap_fraction(a: FaceGeometry, b: FaceGeometry) -> float:
    """Volume of bbox intersection / volume of smaller bbox."""
    inter_min = tuple(max(a.bbox_min[i], b.bbox_min[i]) for i in range(3))
    inter_max = tuple(min(a.bbox_max[i], b.bbox_max[i]) for i in range(3))
    ext = tuple(max(0.0, inter_max[i] - inter_min[i]) for i in range(3))
    inter_vol = ext[0] * ext[1] * ext[2]

    def _vol(f: FaceGeometry) -> float:
        e = tuple(f.bbox_max[i] - f.bbox_min[i] for i in range(3))
        return e[0] * e[1] * e[2]

    smaller = min(_vol(a), _vol(b))
    return inter_vol / smaller if smaller > 0.0 else 0.0


def area_diff_fraction(a: FaceGeometry, b: FaceGeometry) -> float:
    """|area_a - area_b| / max(area_a, area_b). Returns 1.0 if both zero."""
    larger = max(a.area, b.area)
    return abs(a.area - b.area) / larger if larger > 0.0 else 1.0


def normal_dot(a: FaceGeometry, b: FaceGeometry) -> float:
    """Dot product of unit-length face normals."""
    return sum(a.normal[i] * b.normal[i] for i in range(3))


def faces_match_shared(
    a: FaceGeometry,
    b: FaceGeometry,
    *,
    bbox_thresh: float = DEFAULT_BBOX_OVERLAP_MIN,
    area_thresh: float = DEFAULT_AREA_DIFF_MAX,
    normal_thresh: float = DEFAULT_SHARED_NORMAL_DOT_MAX,
) -> bool:
    """Two faces share an interface iff bboxes overlap, areas match, normals oppose."""
    return (
        bbox_overlap_fraction(a, b) >= bbox_thresh
        and area_diff_fraction(a, b) <= area_thresh
        and normal_dot(a, b) <= normal_thresh
    )


def _unit_vector(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
    mag = (dx * dx + dy * dy + dz * dz) ** 0.5
    if mag < 1e-12:
        return (0.0, 0.0, 0.0)
    return (dx / mag, dy / mag, dz / mag)


def perpendicular_distance(fa: FaceGeometry, fb: FaceGeometry) -> float:
    """Perpendicular distance between two parallel-ish facing faces.

    Projects ``fb.centroid - fa.centroid`` onto ``fa.normal``. Returns
    absolute value (gap is always non-negative). For two touching
    interface faces (V2 pattern, centroids coincident) returns 0.0.
    For D1-class sub-mm gap defects (case_003/004/005 0.30-0.35 mm)
    returns the gap in the same units as the input bbox/centroid.
    """
    dx = fb.centroid[0] - fa.centroid[0]
    dy = fb.centroid[1] - fa.centroid[1]
    dz = fb.centroid[2] - fa.centroid[2]
    n = fa.normal
    proj = dx * n[0] + dy * n[1] + dz * n[2]
    return abs(proj)


def find_face_facing_target(
    faces: Sequence[FaceGeometry],
    target_dir: tuple[float, float, float],
    *,
    dot_min: float = DEFAULT_FACING_DOT_MIN,
) -> FaceGeometry | None:
    """Largest-area face whose normal projects onto ``target_dir`` ≥ ``dot_min``."""
    candidates = [
        f for f in faces
        if sum(f.normal[i] * target_dir[i] for i in range(3)) >= dot_min
    ]
    return max(candidates, key=lambda f: f.area) if candidates else None


def find_endcap_face(
    faces: Sequence[FaceGeometry],
    axis: str,
    *,
    dot_min: float = DEFAULT_ENDCAP_AXIS_DOT_MIN,
) -> FaceGeometry | None:
    """Planar face aligned with ``axis`` (e.g. ``'+x'``) at extreme coordinate."""
    if len(axis) != 2 or axis[0] not in "+-" or axis[1].lower() not in "xyz":
        raise ValueError(f"axis must be +/- x|y|z; got {axis!r}")
    sign = 1.0 if axis[0] == "+" else -1.0
    idx = "xyz".index(axis[1].lower())
    target = tuple(sign if i == idx else 0.0 for i in range(3))

    aligned = [
        f for f in faces
        if sum(f.normal[i] * target[i] for i in range(3)) >= dot_min
    ]
    return max(aligned, key=lambda f: sign * f.centroid[idx]) if aligned else None


def detect_virtual_interfaces(
    bodies: Mapping[str, BodyGeometry],
    specs: Sequence[InterfaceSpec],
) -> list[DetectedInterface]:
    """Run each spec against the body collection."""
    results: list[DetectedInterface] = []
    for spec in specs:
        if spec.mode == "shared":
            results.append(_run_shared(bodies, spec))
        elif spec.mode == "endcap":
            results.append(_run_endcap(bodies, spec))
        else:
            results.append(_miss(spec.patch_name, f"unknown mode {spec.mode!r}"))
    return results


def _miss(patch_name: str, diagnostic: str, body_owner: str | None = None) -> DetectedInterface:
    return DetectedInterface(
        patch_name=patch_name, matched=False, body_owner=body_owner, face=None,
        bbox_overlap_fraction=0.0, area_diff_fraction=1.0, normal_dot=0.0,
        diagnostic=diagnostic,
    )


def _run_shared(bodies: Mapping[str, BodyGeometry], spec: InterfaceSpec) -> DetectedInterface:
    obj_a = bodies.get(spec.body_a) if spec.body_a else None
    obj_b = bodies.get(spec.body_b) if spec.body_b else None
    if obj_a is None or obj_b is None:
        return _miss(spec.patch_name, f"missing body (a={spec.body_a!r} b={spec.body_b!r})")

    ba_dir = _unit_vector(*(obj_a.centroid[i] - obj_b.centroid[i] for i in range(3)))
    ab_dir = tuple(-c for c in ba_dir)

    fb = find_face_facing_target(obj_b.faces, ba_dir)
    fa = find_face_facing_target(obj_a.faces, ab_dir)

    # APU bay V2 lesson: only one side often has a clean interface
    # face — BREP-symmetric matching not required. Pick larger area.
    candidates = [(f, owner) for f, owner in ((fa, obj_a.name), (fb, obj_b.name)) if f is not None]
    if not candidates:
        return _miss(spec.patch_name, "no planar face on either body faces the other")

    chosen, owner = max(candidates, key=lambda t: t[0].area)
    other_dir = ab_dir if owner == obj_a.name else ba_dir

    # A2-v2 (V25 closure): compute real cross-body measurements when
    # both bodies contributed a facing face. Single-side detection
    # (V2 pattern) carries an honest None gap + sentinel measurements
    # instead of the v1 hardcoded 1.0 / 0.0 placeholders that masked
    # D1-class defects as "perfect interface".
    if fa is not None and fb is not None:
        bbox_ov = bbox_overlap_fraction(fa, fb)
        area_d = area_diff_fraction(fa, fb)
        gap_mm = perpendicular_distance(fa, fb)
        diag = (
            f"shared interface on {obj_a.name!r} <-> {obj_b.name!r} "
            f"(chosen={owner!r} area={chosen.area:.3g} gap_mm={gap_mm:.4g})"
        )
    else:
        # Only one side has a facing face — V2 "single-side interface".
        # Cross-body geometric measurements are not available; carry
        # sentinel values and document explicitly in diagnostic.
        bbox_ov = 0.0
        area_d = 1.0
        gap_mm = None
        diag = (
            f"shared face on {owner!r} (area={chosen.area:.3g}); "
            "single-side detection, cross-body measurements unavailable"
        )

    return DetectedInterface(
        patch_name=spec.patch_name, matched=True, body_owner=owner, face=chosen,
        bbox_overlap_fraction=bbox_ov, area_diff_fraction=area_d,
        normal_dot=sum(chosen.normal[i] * other_dir[i] for i in range(3)),
        diagnostic=diag,
        inter_face_gap_mm=gap_mm,
    )


def _run_endcap(bodies: Mapping[str, BodyGeometry], spec: InterfaceSpec) -> DetectedInterface:
    obj = bodies.get(spec.body) if spec.body else None
    if obj is None or spec.axis is None:
        return _miss(
            spec.patch_name,
            f"missing body or axis (body={spec.body!r} axis={spec.axis!r})",
            body_owner=obj.name if obj else None,
        )

    face = find_endcap_face(obj.faces, spec.axis)
    if face is None:
        return _miss(
            spec.patch_name,
            f"no planar face on {obj.name!r} aligned with axis {spec.axis!r}",
            body_owner=obj.name,
        )

    sign = 1.0 if spec.axis[0] == "+" else -1.0
    idx = "xyz".index(spec.axis[1].lower())
    target = tuple(sign if i == idx else 0.0 for i in range(3))
    return DetectedInterface(
        patch_name=spec.patch_name, matched=True, body_owner=obj.name, face=face,
        bbox_overlap_fraction=1.0, area_diff_fraction=0.0,
        normal_dot=sum(face.normal[i] * target[i] for i in range(3)),
        diagnostic=f"endcap on {obj.name!r} axis={spec.axis} area={face.area:.3g}",
    )


def should_have_been_shared_with_unintended_gap(
    detected: DetectedInterface,
    *,
    max_gap_mm: float = 1.0,
) -> bool:
    """A2-v2 D1-class defect classifier.

    Returns True when the detector found facing-face candidates
    (``matched=True``) AND measured a positive sub-mm gap below
    ``max_gap_mm`` — i.e. two bodies that the engineer intended to
    share an interface but accidentally separated by a small offset
    (D1 defect class; case_003/004/005 0.30-0.35 mm signatures).

    Returns False when:
      - ``matched`` is False (no facing-face candidates)
      - ``inter_face_gap_mm`` is None (single-side detection)
      - gap == 0 (V2 pattern: touching interface, clean)
      - gap >= max_gap_mm (bodies clearly separate, not "should-be-shared")

    Default ``max_gap_mm=1.0`` covers the observed D1 range and a
    margin; engineers should override per-case if the case has a
    different "near-miss" threshold (e.g. weld misalignment cases
    might use 0.1 mm).
    """
    if not detected.matched:
        return False
    if detected.inter_face_gap_mm is None:
        return False
    return 0.0 < detected.inter_face_gap_mm < max_gap_mm


def validate_interface_coverage(
    detected: Sequence[DetectedInterface],
    expected: Sequence[InterfaceSpec],
) -> dict:
    """Coverage report: which expected specs landed, which missed."""
    by_name = {d.patch_name: d for d in detected}
    landed = [s.patch_name for s in expected
              if by_name.get(s.patch_name) and by_name[s.patch_name].matched]
    missed = [s.patch_name for s in expected if s.patch_name not in landed]
    return {"expected_count": len(expected), "landed_count": len(landed),
            "landed_patches": landed, "missed_patches": missed,
            "coverage_fraction": len(landed) / len(expected) if expected else 1.0}
