"""Tests for ``geometry_ingest.inlet_outlet_validator`` (A5 advisor).

Coverage:
1. Pattern 1 thin_extrusion within 1.5 mm → pass
2. Pattern 2 createPatch_carve with carve_metadata → pass
3. Sealed-room explicit annotation → warning (acceptable)
4. Through-flow body missing boundary_emission → critical fail
5. thin_extrusion bbox max dim > 1.5 mm → fail (V81 failure mode)
6. createPatch_carve without carve_metadata → fail
7. Unknown emission value → fail
8. Non-through-flow role (e.g. wall, occupant) ignored
9. Pattern 2 via boundary_zones cross-reference (no boundary_emission
   on the part itself but body name listed in boundary_zones) → pass
"""
from __future__ import annotations

from ui.backend.services.geometry_ingest.inlet_outlet_validator import (
    THIN_EXTRUSION_MAX_MM,
    InletOutletValidationReport,
    validate_inlet_outlet_emission,
)


def test_thin_extrusion_within_ceiling_passes():
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "boundary_emission": "thin_extrusion",
                # 200 x 100 x 1 mm slot — max dim is 200 mm (in-plane),
                # but the boundary-normal thickness 1 mm is what matters
                # for sHM. The validator checks bbox-max because the
                # V81 failure was "3D box" — any axis above 1.5 mm is
                # the failure indicator. Test the canonical 1 mm case
                # by using a small in-plane geometry too.
                "bbox": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert isinstance(report, InletOutletValidationReport)
    assert report.is_valid
    assert report.fail_count == 0
    assert report.pass_count == 1
    assert report.findings[0].severity == "pass"
    assert report.findings[0].emission_pattern == "thin_extrusion"


def test_create_patch_carve_with_metadata_passes():
    manifest = {
        "parts": [
            {
                "name": "return_outlet",
                "role": "outlet",
                "boundary_emission": "createPatch_carve",
                "carve_metadata": {
                    "parent_patch": "ceiling",
                    "bbox": [1.0, 1.0, 2.4, 1.5, 1.5, 2.4],
                },
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert report.is_valid
    assert report.pass_count == 1
    assert report.findings[0].emission_pattern == "createPatch_carve"


def test_sealed_room_explicit_annotation_yields_warning():
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "boundary_emission": "sealed_room_natural_convection",
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    # warnings are non-blocking — the case explicitly opted out of
    # through-flow physics; validator surfaces the relaxation without
    # failing.
    assert report.is_valid
    assert report.warning_count == 1
    assert report.fail_count == 0
    assert "sealed_room" in report.findings[0].reason


def test_missing_boundary_emission_critical_fail():
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                # no boundary_emission field — this is the V81 failure
                # mode (Codex emitted 3D solid body with no annotation).
                "bbox": [0.0, 0.0, 0.0, 0.2, 0.1, 0.01],
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert not report.is_valid
    assert report.fail_count == 1
    finding = report.findings[0]
    assert finding.severity == "fail"
    assert finding.emission_pattern is None
    assert "boundary_emission" in finding.reason


def test_thin_extrusion_exceeding_ceiling_fails():
    # The V81 root cause: cq.box(0.2, 0.1, 0.5) emitted as inlet — the
    # 0.5 m (= 500 mm) axis exceeds the 1.5 mm thin-shape ceiling.
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "boundary_emission": "thin_extrusion",
                "bbox": [0.0, 0.0, 0.0, 200.0, 100.0, 500.0],
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert not report.is_valid
    finding = report.findings[0]
    assert finding.severity == "fail"
    assert f"{THIN_EXTRUSION_MAX_MM}" in finding.reason


def test_create_patch_carve_without_metadata_fails():
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "boundary_emission": "createPatch_carve",
                # carve_metadata deliberately absent
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert not report.is_valid
    assert "carve_metadata" in report.findings[0].reason


def test_unknown_emission_value_fails():
    manifest = {
        "parts": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "boundary_emission": "magic_patch_creation",
            }
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert not report.is_valid
    assert "unknown boundary_emission" in report.findings[0].reason


def test_non_through_flow_role_ignored():
    manifest = {
        "parts": [
            {"name": "occupant_1", "role": "occupant"},
            {"name": "north_wall", "role": "wall"},
            {"name": "ceiling_lamp", "role": "equipment"},
        ]
    }
    report = validate_inlet_outlet_emission(manifest)
    assert report.is_valid
    assert report.findings == ()
    assert report.fail_count == report.warning_count == report.pass_count == 0


def test_boundary_zones_cross_reference_passes():
    # Pattern 2 in the methodology: the part may be omitted entirely
    # and the inlet emitted as a metadata-only boundary_zones entry.
    # The validator accepts the cross-reference when a part with
    # role=inlet exists but has no boundary_emission field, as long
    # as its name appears in boundary_zones.
    manifest = {
        "parts": [
            {"name": "supply_inlet", "role": "inlet"},
        ],
        "boundary_zones": [
            {
                "name": "supply_inlet",
                "role": "inlet",
                "type": "patch",
                "bbox": [0.5, 0.5, 2.4, 1.0, 1.0, 2.4],
                "carve_from_patch": "ceiling",
            }
        ],
    }
    report = validate_inlet_outlet_emission(manifest)
    assert report.is_valid
    assert report.pass_count == 1
    assert report.findings[0].emission_pattern == "createPatch_carve"
