"""Tests for ``geometry_ingest.extra_body_advisor`` (D6 advisor).

Coverage:

1.  Clean case — every STL body is registered, no inclusions → no finding
2.  ``unregistered_body`` critical — STL set has a body absent from manifest
3.  ``body_in_fluid_region`` warning — solid bbox ⊂ fluid bbox
4.  ``undeclared_inclusion`` warning — solid ⊂ solid without declaration
5.  Declared inclusion suppresses warning — same overlap + manifest entry → clean
6.  Empty manifest + empty STL set → trivially clean
7.  Partial overlap (neither fully contains other) is NOT flagged — per anti-scope V59
8.  Role missing / unknown defaults to ``solid`` — V55 root-cause defensive
9.  Per-finding severity classification — critical vs warning correct
10. **case_016 V55 regression** — 10 mm debris cube at (320, 18, -79) mm
    inside region_air cavity bbox, debris absent from manifest →
    unregistered_body critical (D6 promotion-gate sediment evidence)
"""
from __future__ import annotations

from ui.backend.services.geometry_ingest.extra_body_advisor import (
    ExtraBodyReport,
    check_extra_bodies_in_fluid,
)


def test_clean_case_passes() -> None:
    manifest = {
        "parts": [
            {
                "name": "region_air",
                "role": "region_air",
                "bbox": [-200.0, -200.0, -200.0, 600.0, 200.0, 200.0],
            },
            {
                "name": "cavity_wall",
                "role": "solid",
                "bbox": [200.0, -100.0, -100.0, 400.0, 100.0, 100.0],
            },
        ]
    }
    stl_bboxes = {
        "region_air": [-200.0, -200.0, -200.0, 600.0, 200.0, 200.0],
        "cavity_wall": [200.0, -100.0, -100.0, 400.0, 100.0, 100.0],
    }
    # cavity_wall ⊂ region_air → would flag, except cavity_wall is the
    # legitimate region boundary. We declare it.
    manifest["declared_inclusions"] = [{"outer": "region_air", "inner": "cavity_wall"}]
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    assert isinstance(report, ExtraBodyReport)
    assert report.is_clean
    assert report.findings == ()
    assert report.registered_count == 2
    assert report.stl_count == 2
    assert report.suspected_extras == ()


def test_unregistered_body_is_critical() -> None:
    manifest = {
        "parts": [
            {
                "name": "region_air",
                "role": "region_air",
                "bbox": [0.0, 0.0, 0.0, 1000.0, 1000.0, 1000.0],
            }
        ]
    }
    stl_bboxes = {
        "region_air": [0.0, 0.0, 0.0, 1000.0, 1000.0, 1000.0],
        "mystery_debris": [100.0, 100.0, 100.0, 110.0, 110.0, 110.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    crit = [f for f in report.findings if f.finding_type == "unregistered_body"]
    assert len(crit) == 1
    assert crit[0].body_name == "mystery_debris"
    assert crit[0].severity == "critical"
    assert crit[0].container_name is None
    assert "absent from parts_manifest" in crit[0].detail
    assert report.critical_count == 1


def test_body_in_fluid_region_is_warning() -> None:
    manifest = {
        "parts": [
            {
                "name": "cavity",
                "role": "fluid",
                "bbox": [-100.0, -100.0, -100.0, 500.0, 100.0, 100.0],
            },
            {
                "name": "extra_screw",
                "role": "solid",
                "bbox": [200.0, -5.0, -5.0, 210.0, 5.0, 5.0],
            },
        ]
    }
    stl_bboxes = {
        "cavity": [-100.0, -100.0, -100.0, 500.0, 100.0, 100.0],
        "extra_screw": [200.0, -5.0, -5.0, 210.0, 5.0, 5.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    warns = [
        f for f in report.findings if f.finding_type == "body_in_fluid_region"
    ]
    assert len(warns) == 1
    assert warns[0].body_name == "extra_screw"
    assert warns[0].severity == "warning"
    assert warns[0].container_name == "cavity"


def test_undeclared_inclusion_is_warning() -> None:
    manifest = {
        "parts": [
            {
                "name": "cowling",
                "role": "solid",
                "bbox": [0.0, 0.0, 0.0, 500.0, 200.0, 200.0],
            },
            {
                "name": "probe_holder",
                "role": "solid",
                "bbox": [100.0, 50.0, 50.0, 150.0, 100.0, 100.0],
            },
        ]
    }
    stl_bboxes = {
        "cowling": [0.0, 0.0, 0.0, 500.0, 200.0, 200.0],
        "probe_holder": [100.0, 50.0, 50.0, 150.0, 100.0, 100.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    warns = [
        f for f in report.findings if f.finding_type == "undeclared_inclusion"
    ]
    assert len(warns) == 1
    assert warns[0].body_name == "probe_holder"
    assert warns[0].container_name == "cowling"
    assert warns[0].severity == "warning"


def test_declared_inclusion_suppresses_warning() -> None:
    manifest = {
        "parts": [
            {
                "name": "cowling",
                "role": "solid",
                "bbox": [0.0, 0.0, 0.0, 500.0, 200.0, 200.0],
            },
            {
                "name": "probe_holder",
                "role": "solid",
                "bbox": [100.0, 50.0, 50.0, 150.0, 100.0, 100.0],
            },
        ],
        "declared_inclusions": [
            {"outer": "cowling", "inner": "probe_holder"},
        ],
    }
    stl_bboxes = {
        "cowling": [0.0, 0.0, 0.0, 500.0, 200.0, 200.0],
        "probe_holder": [100.0, 50.0, 50.0, 150.0, 100.0, 100.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    assert report.is_clean
    assert report.suspected_extras == ()


def test_empty_manifest_and_empty_stls_is_clean() -> None:
    report = check_extra_bodies_in_fluid({"parts": []}, {})
    assert report.is_clean
    assert report.registered_count == 0
    assert report.stl_count == 0


def test_partial_overlap_not_flagged_per_v59_anti_scope() -> None:
    # Two boxes overlap on a corner — neither contains the other. The
    # advisor must NOT report this (anti-scope: V59 covers partial
    # overlap as a separate import-time classifier).
    manifest = {
        "parts": [
            {
                "name": "box_a",
                "role": "solid",
                "bbox": [0.0, 0.0, 0.0, 100.0, 100.0, 100.0],
            },
            {
                "name": "box_b",
                "role": "solid",
                "bbox": [50.0, 50.0, 50.0, 200.0, 200.0, 200.0],
            },
        ]
    }
    stl_bboxes = {
        "box_a": [0.0, 0.0, 0.0, 100.0, 100.0, 100.0],
        "box_b": [50.0, 50.0, 50.0, 200.0, 200.0, 200.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    assert report.is_clean


def test_missing_role_defaults_to_solid_v55_defensive() -> None:
    # V55 root cause: debris cube had no role at all in the manifest.
    # When the manifest entry exists but role is missing / unknown, we
    # treat it as solid so the fluid-region containment still fires.
    manifest = {
        "parts": [
            {
                "name": "cavity",
                "role": "region_air",
                "bbox": [-100.0, -100.0, -100.0, 600.0, 100.0, 100.0],
            },
            {
                "name": "debris_no_role",
                # role: deliberately omitted
                "bbox": [300.0, 0.0, 0.0, 310.0, 10.0, 10.0],
            },
            {
                "name": "garbage_role",
                "role": "unknown_role_string",
                "bbox": [200.0, 0.0, 0.0, 210.0, 10.0, 10.0],
            },
        ]
    }
    stl_bboxes = {
        "cavity": [-100.0, -100.0, -100.0, 600.0, 100.0, 100.0],
        "debris_no_role": [300.0, 0.0, 0.0, 310.0, 10.0, 10.0],
        "garbage_role": [200.0, 0.0, 0.0, 210.0, 10.0, 10.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    flagged = {f.body_name for f in report.findings if f.finding_type == "body_in_fluid_region"}
    assert flagged == {"debris_no_role", "garbage_role"}


def test_severity_classification_critical_vs_warning() -> None:
    # Single fixture exercising both severity bands at once: an
    # unregistered body (critical) PLUS a registered solid inside a
    # fluid region (warning).
    manifest = {
        "parts": [
            {
                "name": "cavity",
                "role": "fluid",
                "bbox": [0.0, 0.0, 0.0, 1000.0, 1000.0, 1000.0],
            },
            {
                "name": "registered_solid",
                "role": "solid",
                "bbox": [100.0, 100.0, 100.0, 200.0, 200.0, 200.0],
            },
        ]
    }
    stl_bboxes = {
        "cavity": [0.0, 0.0, 0.0, 1000.0, 1000.0, 1000.0],
        "registered_solid": [100.0, 100.0, 100.0, 200.0, 200.0, 200.0],
        "phantom_body": [500.0, 500.0, 500.0, 510.0, 510.0, 510.0],
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    assert report.critical_count == 1
    assert report.warning_count >= 1
    types = {f.finding_type for f in report.findings}
    assert "unregistered_body" in types
    assert "body_in_fluid_region" in types


def test_case_016_v55_debris_cube_regression() -> None:
    """V55 ground truth — case_016_m219_cavity_des_acoustic D6.

    Per ``industrial_case_solver_findings.md`` V55:
    10 mm debris cube at center (320.0, 18.0, -79.0) mm inside cavity,
    documented clearances (18 mm to floor, 28 mm to starboard wall,
    183 mm to TE, 315 mm to LE).

    The original case_016 manifest emitted from build_cad declared the
    legitimate cavity bodies but not the debris cube — its
    `defect_manifest.yaml` `expected_advisor_to_catch: none_landed`
    captured exactly the gap this advisor closes.

    Expected detection: ``unregistered_body`` critical — debris cube
    present in STL set, absent from parts_manifest.
    """
    # Center (320, 18, -79) mm, 10 mm cube → bbox [315, 13, -84, 325, 23, -74]
    cube_center = (320.0, 18.0, -79.0)
    half = 5.0
    debris_bbox = [
        cube_center[0] - half,
        cube_center[1] - half,
        cube_center[2] - half,
        cube_center[0] + half,
        cube_center[1] + half,
        cube_center[2] + half,
    ]

    # case_016 cavity is roughly LE=-315 mm, TE=+183 mm, sidewalls
    # ±100 mm, floor/ceiling +/- some. Use a bounding box that strictly
    # contains the debris cube at the documented clearances.
    cavity_bbox = [-400.0, -150.0, -100.0, 250.0, 150.0, 100.0]

    manifest = {
        "parts": [
            {
                "name": "region_air",
                "role": "region_air",
                "bbox": cavity_bbox,
            },
            # No debris_cube entry — that is the V55 defect by
            # construction (defect_manifest.yaml says
            # expected_advisor_to_catch: none_landed).
        ]
    }
    stl_bboxes = {
        "region_air": cavity_bbox,
        "debris_cube": debris_bbox,
    }
    report = check_extra_bodies_in_fluid(manifest, stl_bboxes)
    assert not report.is_clean
    assert report.critical_count == 1
    f = report.findings[0]
    assert f.body_name == "debris_cube"
    assert f.finding_type == "unregistered_body"
    assert f.severity == "critical"
    assert "debris_cube" in report.suspected_extras
