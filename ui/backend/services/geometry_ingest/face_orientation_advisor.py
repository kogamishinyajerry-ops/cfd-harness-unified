"""Face-orientation advisor (A4).

Detects bodies whose dominant face normal deviates from a declared or
sibling-consensus orientation by more than a per-group tolerance. Closes
the D7 advisor-stack-scope-gap surfaced by V79 (case_012 louver vane
38° rotation around Z) and V87 (case_013 blade-3 LE chunk 22° rotation
around an XY-plane chord axis).

Design choice — pure dict consumer (mirrors A5
:mod:`inlet_outlet_validator`):

The advisor consumes a parts_manifest dict whose body entries already
carry a pre-computed ``actual_face_normal``. Normal extraction is the
caller's responsibility — typically via FreeCAD ``face.normalAt()`` on
the dominant planar face (case_012 Z-axis topology) or via the tilt-
from-XY-plane signature on LE-band side faces (case_013 chord-axis
topology). Keeping FreeCAD out of the advisor:

* matches the A5/A7 sibling pattern (pure dict in → dataclass report
  out, no runtime CAD-library dependency)
* makes the advisor unit-testable without FreeCAD installed in CI
* lets the caller pick the right measurement method for the topology
  per V87 §Fix ("the productized advisor must auto-select method
  based on declared rotation_axis in parts_manifest")

References:

- V79 in ``industrial_case_solver_findings.md`` (case_012 first injection)
- V87 in ``industrial_case_solver_findings.md`` (case_013 cross-topology
  promotion-gate completion)
- Draft patch ``.planning/patches/draft_a4_face_orientation_2026-05-13.md``
- Parent sub-DEC: V61-198-sub-A4 (2026-05-13)
- Sibling validator pattern: ``inlet_outlet_validator.py`` (A5)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

Vec3 = tuple[float, float, float]

DEFAULT_TOLERANCE_DEG: float = 5.0
"""Severity boundary 1: angle ≤ tol → not reported."""

# Severity boundary 2: tol < angle ≤ 2·tol → warning;
# angle > 2·tol → critical. Mapping documented in `_classify_severity`.


@dataclass(frozen=True)
class FaceOrientationFinding:
    """One audit result for one body whose orientation deviates."""

    body_name: str
    intended_normal: Vec3
    actual_normal: Vec3
    angle_deviation_deg: float
    tolerance_deg: float
    severity: str  # "warning" | "critical"


@dataclass(frozen=True)
class FaceOrientationReport:
    """Outcome of :func:`check_face_orientation`."""

    findings: tuple[FaceOrientationFinding, ...]
    bodies_checked: int
    bodies_with_intended_normal: int
    bodies_skipped: int

    @property
    def is_clean(self) -> bool:
        """True iff no body produced a warning or critical finding."""
        return len(self.findings) == 0


def _normalize(v: Vec3) -> Vec3 | None:
    mag = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if mag < 1e-12:
        return None
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _angle_deg(a: Vec3, b: Vec3) -> float:
    """Angle between two unit vectors, with sign-ambiguous-plane semantics.

    Plane-face normals (the dominant-planar-face case_012 topology and
    the tilt-from-XY-plane case_013 topology both apply) are
    sign-ambiguous: a face's outward normal is geometrically equivalent
    to its negation. Use ``abs(dot)`` so a 180° flip counts as 0°
    agreement.
    """
    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    dot = max(-1.0, min(1.0, abs(dot)))
    return math.degrees(math.acos(dot))


def _classify_severity(angle_deg: float, tol_deg: float) -> str | None:
    """Map (angle, tolerance) → severity label, or None if below tol."""
    if angle_deg <= tol_deg:
        return None
    if angle_deg <= 2.0 * tol_deg:
        return "warning"
    return "critical"


def _median_per_axis(normals: list[Vec3]) -> Vec3:
    """Robust per-axis median of unit vectors.

    Used for sibling-consensus when ``expected_face_normal`` is absent.
    Per draft patch §7 R1, use median (not mean) so a single rotated
    outlier in a group of ≥ 3 does not pull the consensus toward
    itself. The median is computed independently on each axis; the
    result is re-normalized.
    """
    xs = sorted(n[0] for n in normals)
    ys = sorted(n[1] for n in normals)
    zs = sorted(n[2] for n in normals)
    n = len(normals)
    if n % 2 == 1:
        mx, my, mz = xs[n // 2], ys[n // 2], zs[n // 2]
    else:
        mx = 0.5 * (xs[n // 2 - 1] + xs[n // 2])
        my = 0.5 * (ys[n // 2 - 1] + ys[n // 2])
        mz = 0.5 * (zs[n // 2 - 1] + zs[n // 2])
    norm = _normalize((mx, my, mz))
    if norm is None:
        # Degenerate (all-zero median) — fall back to the first sibling
        # to avoid a NaN downstream. Caller-supplied data should never
        # land here in practice.
        return normals[0]
    return norm


def _as_vec3(value: Any) -> Vec3 | None:
    """Coerce a 3-element iterable to a normalized Vec3, or None.

    Accepts list/tuple of length 3 with finite float-able entries.
    Anything else (None, wrong length, non-numeric) → None so the
    caller can decide to skip the body.
    """
    if value is None:
        return None
    try:
        if len(value) != 3:
            return None
    except TypeError:
        return None
    try:
        v: Vec3 = (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None
    return _normalize(v)


def check_face_orientation(
    parts_manifest: dict[str, Any],
    *,
    default_tolerance_deg: float = DEFAULT_TOLERANCE_DEG,
    per_body_tolerance_deg: dict[str, float] | None = None,
) -> FaceOrientationReport:
    """Audit each body's actual-vs-intended dominant-face orientation.

    Expected schema (subset; only fields read here are documented):

    .. code-block:: yaml

       parts:
         - name: louver_vane_2
           actual_face_normal: [0.7880, -0.6157, 0.0]   # caller-extracted
           expected_face_normal: [0.0, -1.0, 0.0]       # OPTIONAL
           sibling_group: louver_vanes                  # OPTIONAL (alternate)
           tolerance_deg: 2.0                           # OPTIONAL per-body override

    Mode selection per body:

    - ``actual_face_normal`` missing or non-coercible → body skipped
    - ``expected_face_normal`` present → direct compare (wins over sibling)
    - ``sibling_group`` present → consensus = median-per-axis of all
      siblings' ``actual_face_normal`` (skipping any sibling missing
      its own actual), compare each member to consensus
    - neither present → body skipped

    Tolerance priority per body:

    1. ``per_body_tolerance_deg[name]`` (caller override) if provided
    2. body's own ``tolerance_deg`` field in the manifest
    3. ``default_tolerance_deg`` (5.0° unless caller overrides)

    Severity mapping:

    - angle ≤ tol → not reported (passes silently)
    - tol < angle ≤ 2·tol → ``warning``
    - angle > 2·tol → ``critical``
    """
    parts = parts_manifest.get("parts") or []
    per_body_overrides = per_body_tolerance_deg or {}

    # Pre-pass: extract every body's actual normal so siblings can
    # consult each other without re-coercing on every lookup.
    actuals: dict[str, Vec3] = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        name = part.get("name")
        if not isinstance(name, str):
            continue
        actual = _as_vec3(part.get("actual_face_normal"))
        if actual is not None:
            actuals[name] = actual

    # Build sibling-group → [normals] index. A body without an
    # actual_face_normal cannot contribute to consensus.
    sibling_normals: dict[str, list[Vec3]] = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        name = part.get("name")
        group = part.get("sibling_group")
        if not (isinstance(name, str) and isinstance(group, str)):
            continue
        if name in actuals:
            sibling_normals.setdefault(group, []).append(actuals[name])

    findings: list[FaceOrientationFinding] = []
    bodies_checked = 0
    bodies_with_intended = 0
    bodies_skipped = 0

    for part in parts:
        if not isinstance(part, dict):
            continue
        name = part.get("name")
        if not isinstance(name, str):
            continue

        if name not in actuals:
            # No measurement available — caller is expected to attach
            # actual_face_normal upstream. Skip silently to mirror A5's
            # "no through-flow role → ignored" pattern.
            bodies_skipped += 1
            continue

        actual = actuals[name]
        expected = _as_vec3(part.get("expected_face_normal"))
        group = part.get("sibling_group") if isinstance(
            part.get("sibling_group"), str
        ) else None

        intended: Vec3 | None = None
        if expected is not None:
            intended = expected
        elif group is not None:
            members = sibling_normals.get(group) or []
            # Need ≥ 2 siblings for a meaningful consensus (otherwise
            # the body's own normal IS the consensus). Per draft patch
            # §7 R1, a group of ≥ 3 is needed for robust median against
            # a single outlier; with exactly 2 the median equals the
            # mean and one outlier biases consensus equally — still
            # surfaces SOME deviation, just less robust.
            if len(members) >= 2:
                intended = _median_per_axis(members)

        if intended is None:
            bodies_skipped += 1
            continue

        bodies_checked += 1
        bodies_with_intended += 1

        tol_deg = float(
            per_body_overrides.get(name)
            if name in per_body_overrides
            else part.get("tolerance_deg", default_tolerance_deg)
        )

        angle = _angle_deg(actual, intended)
        severity = _classify_severity(angle, tol_deg)
        if severity is None:
            continue

        findings.append(
            FaceOrientationFinding(
                body_name=name,
                intended_normal=intended,
                actual_normal=actual,
                angle_deviation_deg=round(angle, 6),
                tolerance_deg=tol_deg,
                severity=severity,
            )
        )

    return FaceOrientationReport(
        findings=tuple(findings),
        bodies_checked=bodies_checked,
        bodies_with_intended_normal=bodies_with_intended,
        bodies_skipped=bodies_skipped,
    )
