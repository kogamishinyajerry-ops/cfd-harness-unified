"""Tests for ``geometry_ingest.face_orientation_advisor`` (A4 advisor).

Coverage:

1. Declared normal within tolerance → no finding
2. Declared normal above 2·tol → critical (V79 + V87 D7 class)
3. Declared normal between tol and 2·tol → warning
4. Sibling-consensus with one rotated outlier in a group of 4 → outlier
   critical, others pass (per-axis median robust to single outlier per
   draft patch §7 R1)
5. Body with no actual_face_normal → skipped
6. Body with actual but neither expected nor sibling_group → skipped
7. Per-body tolerance override (caller arg) wins over manifest field
8. **case_012 D7 regression** — louver_vane_2 38° XY-plane rotation
   from intended (V79 ground truth)
9. **case_013 D7 regression** — blade_3 LE chunk 22° XY-axis rotation
   producing 0.3743 z-tilt (V87 ground truth from
   ``defect_verification_d7.json``)
"""
from __future__ import annotations

import math

from ui.backend.services.geometry_ingest.face_orientation_advisor import (
    FaceOrientationReport,
    check_face_orientation,
)


def test_declared_normal_within_tol_passes() -> None:
    manifest = {
        "parts": [
            {
                "name": "vane_a",
                "actual_face_normal": [0.0, 1.0, 0.0],
                "expected_face_normal": [0.0, 1.0, 0.0],
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert isinstance(report, FaceOrientationReport)
    assert report.is_clean
    assert report.bodies_checked == 1
    assert report.bodies_with_intended_normal == 1
    assert report.bodies_skipped == 0
    assert report.findings == ()


def test_declared_normal_above_critical_threshold() -> None:
    # 12° deviation, default 5° tol → 12 > 2·5 = 10 → critical
    angle = math.radians(12.0)
    manifest = {
        "parts": [
            {
                "name": "vane_b",
                "actual_face_normal": [math.sin(angle), math.cos(angle), 0.0],
                "expected_face_normal": [0.0, 1.0, 0.0],
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.body_name == "vane_b"
    assert f.severity == "critical"
    assert abs(f.angle_deviation_deg - 12.0) < 1e-6
    assert f.tolerance_deg == 5.0


def test_declared_normal_in_warning_band() -> None:
    # 7° deviation, default 5° tol → 5 < 7 ≤ 10 → warning
    angle = math.radians(7.0)
    manifest = {
        "parts": [
            {
                "name": "vane_c",
                "actual_face_normal": [math.sin(angle), math.cos(angle), 0.0],
                "expected_face_normal": [0.0, 1.0, 0.0],
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert len(report.findings) == 1
    assert report.findings[0].severity == "warning"


def test_sibling_consensus_with_one_outlier() -> None:
    # 4 louver vanes — 3 pointing +Y, 1 rotated 30° from sibling
    # consensus. Per-axis median takes the +Y consensus from the 3
    # good vanes; the outlier should be the only finding.
    rot = math.radians(30.0)
    manifest = {
        "parts": [
            {
                "name": "vane_0",
                "sibling_group": "louvers",
                "actual_face_normal": [0.0, 1.0, 0.0],
            },
            {
                "name": "vane_1",
                "sibling_group": "louvers",
                "actual_face_normal": [0.0, 1.0, 0.0],
            },
            {
                "name": "vane_2",
                "sibling_group": "louvers",
                "actual_face_normal": [math.sin(rot), math.cos(rot), 0.0],
            },
            {
                "name": "vane_3",
                "sibling_group": "louvers",
                "actual_face_normal": [0.0, 1.0, 0.0],
            },
        ]
    }
    report = check_face_orientation(manifest)
    finding_names = {f.body_name for f in report.findings}
    assert finding_names == {"vane_2"}
    assert report.findings[0].severity == "critical"
    assert abs(report.findings[0].angle_deviation_deg - 30.0) < 1e-6
    assert report.bodies_checked == 4
    assert report.bodies_with_intended_normal == 4


def test_body_without_actual_face_normal_is_skipped() -> None:
    manifest = {
        "parts": [
            {
                "name": "vane_no_actual",
                "expected_face_normal": [0.0, 1.0, 0.0],
                # actual_face_normal deliberately absent — caller never
                # extracted it (FreeCAD step failed, or body has no
                # planar face)
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert report.is_clean
    assert report.bodies_skipped == 1
    assert report.bodies_checked == 0
    assert report.bodies_with_intended_normal == 0


def test_body_without_expected_or_sibling_group_is_skipped() -> None:
    # Has actual_face_normal but no reference to compare against.
    # Mirrors the A5 "non-through-flow role → silently ignored" idiom.
    manifest = {
        "parts": [
            {
                "name": "loose_body",
                "actual_face_normal": [1.0, 0.0, 0.0],
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert report.is_clean
    assert report.bodies_skipped == 1
    assert report.bodies_checked == 0


def test_per_body_tolerance_override_argument_wins() -> None:
    # 6° deviation, default tol 5° → warning band.
    # Tighten via caller arg to 2° → 6 > 2·2 = 4 → critical.
    angle = math.radians(6.0)
    manifest = {
        "parts": [
            {
                "name": "tight",
                "actual_face_normal": [math.sin(angle), math.cos(angle), 0.0],
                "expected_face_normal": [0.0, 1.0, 0.0],
                "tolerance_deg": 4.0,  # manifest-level — should be overridden
            }
        ]
    }
    report = check_face_orientation(
        manifest,
        per_body_tolerance_deg={"tight": 2.0},
    )
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.tolerance_deg == 2.0
    assert f.severity == "critical"


def test_case_012_louver_vane_2_regression() -> None:
    """V79 ground truth — case_012_hvac_supply_diffuser D7.

    Per ``~/Desktop/case_012_hvac_supply_diffuser/scripts/check_face_normal.py``:
    intended normal for louver_vane_2 at base_angle=180° rotation about
    Z = (0, -1, 0). The D7 defect adds 38° additional rotation about Z,
    so the actual face normal is rotated 38° in the XY plane from
    intended.

    The advisor with default 5° tol must flag this as critical
    (38° > 2·5° = 10°). Mirrors the case_012 ``check_face_normal.py``
    measurement of 38.000° exact.
    """
    defect_deg = 38.0
    rot = math.radians(defect_deg)
    # Intended = (0, -1, 0). Rotation about Z by 38° rotates the normal
    # into the XY plane: (sin θ · 0 + cos θ · 0, ...). Easier: build
    # actual directly from intended ⊗ rotation about Z.
    intended = (0.0, -1.0, 0.0)
    actual = (
        intended[0] * math.cos(rot) - intended[1] * math.sin(rot),
        intended[0] * math.sin(rot) + intended[1] * math.cos(rot),
        0.0,
    )
    manifest = {
        "parts": [
            {
                "name": "louver_vane_2",
                "actual_face_normal": list(actual),
                "expected_face_normal": list(intended),
                "tolerance_deg": 2.0,
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.body_name == "louver_vane_2"
    assert f.severity == "critical"
    # case_012 measurement was 38.000° exact; allow 1e-6 numeric noise
    assert abs(f.angle_deviation_deg - defect_deg) < 1e-6


def test_case_013_blade_3_regression() -> None:
    """V87 ground truth — case_013_centrifugal_pump_cavitating D7.

    Per ``~/Desktop/case_013_centrifugal_pump_cavitating/evidence/v1/defect_verification_d7.json``:
    blade_3's leading-edge chunk is rotated 22° about a chord axis
    that lies in the XY plane. The injected geometry's max-tilt side
    face has measured ``normal = [-0.9017, -0.2166, 0.3743]`` (peak
    tilt-from-XY-plane = 21.979°). Baseline side faces all have
    n_z ≈ 0.

    To exercise the advisor on case_013's actual measurement: intended
    is the XY-plane projection of the actual (re-normalized) — the
    baseline same-centroid face normal would lie in XY since the
    baseline LE has no z-tilt. Angle between actual and intended =
    arcsin(|n_z|) = 21.979°, matching the JSON's
    ``measured_angle_deg``.

    With tolerance 4° (matching the case_013 verification harness),
    21.979° > 2·4° = 8° → critical.
    """
    actual = (-0.9017, -0.2166, 0.3743)
    # XY-projection of actual, re-normalized — this is what the
    # baseline geometry's same-centroid face normal would look like
    # (no Z component because the LE chord is in XY).
    xy_mag = math.sqrt(actual[0] ** 2 + actual[1] ** 2)
    intended = (actual[0] / xy_mag, actual[1] / xy_mag, 0.0)
    manifest = {
        "parts": [
            {
                "name": "blade_3",
                "actual_face_normal": list(actual),
                "expected_face_normal": list(intended),
                "tolerance_deg": 4.0,
            }
        ]
    }
    report = check_face_orientation(manifest)
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.body_name == "blade_3"
    assert f.severity == "critical"
    # JSON evidence reports 21.979°; allow modest numeric tolerance
    # since the unit-vector inputs are rounded to 4 decimals
    assert abs(f.angle_deviation_deg - 21.979) < 0.05
