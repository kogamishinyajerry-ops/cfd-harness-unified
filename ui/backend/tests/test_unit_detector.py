"""Tests for V198 P0 · unit_detector.

Covers STEP header parsing, bbox-plausibility heuristics, and the combined
detect_unit() decision tree. Pure-logic — no FreeCAD, no fixtures larger
than inline strings.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.geometry_ingest.unit_detector import (
    GeometricUnit,
    UnitDetection,
    bbox_plausible_units,
    detect_unit,
    parse_step_header_unit,
)


_STEP_HEADER_MM = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('STEP AP203'),'1');
FILE_NAME('test.step','2026-05-11',(''),(''),'','','');
FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));
ENDSEC;
DATA;
#1 = APPLICATION_PROTOCOL_DEFINITION('','config_control_design',1994,#2);
#10 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
ENDSEC;
END-ISO-10303-21;
"""

_STEP_HEADER_M = """ISO-10303-21;
HEADER;
ENDSEC;
DATA;
#10 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT($,.METRE.) );
ENDSEC;
END-ISO-10303-21;
"""

_STEP_HEADER_INCH = """ISO-10303-21;
HEADER;
ENDSEC;
DATA;
#22 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
#23 = ( CONVERSION_BASED_UNIT('INCH',#24) LENGTH_UNIT() NAMED_UNIT(#22) );
#24 = LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#22);
ENDSEC;
END-ISO-10303-21;
"""

_STEP_HEADER_NO_UNIT = """ISO-10303-21;
HEADER;
ENDSEC;
DATA;
#1 = APPLICATION_PROTOCOL_DEFINITION('','config_control_design',1994,#2);
ENDSEC;
END-ISO-10303-21;
"""


# ───── parse_step_header_unit ─────


def test_parse_step_header_mm(tmp_path: Path):
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    unit, ev = parse_step_header_unit(p)
    assert unit == GeometricUnit.MM
    assert any("MILLI" in line for line in ev)


def test_parse_step_header_meter(tmp_path: Path):
    p = tmp_path / "m.step"
    p.write_text(_STEP_HEADER_M)
    unit, _ = parse_step_header_unit(p)
    assert unit == GeometricUnit.M


def test_parse_step_header_inch(tmp_path: Path):
    p = tmp_path / "inch.step"
    p.write_text(_STEP_HEADER_INCH)
    unit, ev = parse_step_header_unit(p)
    assert unit == GeometricUnit.INCH
    assert any("INCH" in line for line in ev)


def test_parse_step_header_no_unit_declaration(tmp_path: Path):
    p = tmp_path / "nope.step"
    p.write_text(_STEP_HEADER_NO_UNIT)
    unit, ev = parse_step_header_unit(p)
    assert unit is None
    assert any("not contain" in line for line in ev)


def test_parse_step_header_file_not_found(tmp_path: Path):
    p = tmp_path / "missing.step"
    unit, ev = parse_step_header_unit(p)
    assert unit is None
    assert any("not found" in line for line in ev)


# ───── bbox_plausible_units ─────


def test_bbox_plausible_industrial_mm_only():
    # 50000 mm = 50 m (✓); 50000 m too big; 50000 inch = 1270 m too big; 50000 cm = 500 m too big.
    assert bbox_plausible_units(50000.0) == (GeometricUnit.MM,)


def test_bbox_plausible_zero_or_negative_empty():
    assert bbox_plausible_units(0.0) == ()
    assert bbox_plausible_units(-1.0) == ()


def test_bbox_plausible_tiny_below_floor():
    # 0.001 raw under any common unit is below 0.01 m industrial floor.
    assert bbox_plausible_units(0.001) == ()


def test_bbox_plausible_multiple_candidates():
    # 200 raw: mm=0.2m ✓, cm=2m ✓, m=200m ✗, inch=5.08m ✓ → (MM, CM, INCH)
    result = bbox_plausible_units(200.0)
    assert GeometricUnit.MM in result
    assert GeometricUnit.CM in result
    assert GeometricUnit.INCH in result
    assert GeometricUnit.M not in result


def test_bbox_plausible_meter_only():
    # 50 raw: mm=0.05m ✓, cm=0.5m ✓, m=50m ✓, inch=1.27m ✓ → all four
    result = bbox_plausible_units(50.0)
    assert set(result) == {
        GeometricUnit.MM,
        GeometricUnit.CM,
        GeometricUnit.M,
        GeometricUnit.INCH,
    }


# ───── detect_unit (combined) ─────


def test_detect_unit_header_alone_no_bbox(tmp_path: Path):
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    result = detect_unit(step_path=p)
    assert result.decision == GeometricUnit.MM
    assert 0.5 < result.confidence < 1.0
    assert result.declared_unit == GeometricUnit.MM


def test_detect_unit_header_agrees_with_unique_bbox(tmp_path: Path):
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    # 50000 raw → only MM plausible → header confirms → confidence 1.0
    result = detect_unit(step_path=p, bbox_max_extent_raw=50000.0)
    assert result.decision == GeometricUnit.MM
    assert result.confidence == 1.0


def test_detect_unit_header_agrees_with_multi_plausible_bbox(tmp_path: Path):
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    # 200 raw plausible as (MM, CM, INCH); header picks MM
    result = detect_unit(step_path=p, bbox_max_extent_raw=200.0)
    assert result.decision == GeometricUnit.MM
    assert result.confidence == 0.85


def test_detect_unit_header_contradicts_bbox_flags_unknown(tmp_path: Path):
    # Header says MM, but bbox extent 5 raw → mm=0.005m (below 0.01m floor).
    # Plausible only as (CM, M, INCH). Header contradicts → UNKNOWN + warning.
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    result = detect_unit(step_path=p, bbox_max_extent_raw=5.0)
    assert result.decision == GeometricUnit.UNKNOWN
    assert result.confidence == 0.0
    assert any("WARNING" in line for line in result.evidence)


def test_detect_unit_no_header_single_plausible_bbox():
    # Bbox 50000 raw + no STEP → MM only plausible
    result = detect_unit(bbox_max_extent_raw=50000.0)
    assert result.decision == GeometricUnit.MM
    assert result.confidence == 0.5
    assert result.declared_unit is None


def test_detect_unit_no_header_multi_plausible_bbox_returns_unknown():
    # Bbox 50 raw plausible under 4 units → engineer must confirm
    result = detect_unit(bbox_max_extent_raw=50.0)
    assert result.decision == GeometricUnit.UNKNOWN
    assert result.confidence == 0.0
    assert any("confirmation required" in line for line in result.evidence)


def test_detect_unit_no_signals_at_all():
    result = detect_unit()
    assert result.decision == GeometricUnit.UNKNOWN
    assert result.confidence == 0.0


def test_detect_unit_returns_unit_detection_dataclass():
    result = detect_unit(bbox_max_extent_raw=50000.0)
    assert isinstance(result, UnitDetection)
    assert isinstance(result.evidence, tuple)


# ───── body-class filter (F-NEW-12 · 2026-05-11) ─────


def test_detect_unit_body_class_filter_case_003_like(tmp_path: Path):
    """case_003 archetype: airframe + 3 defects are mm-plausible; inlet /
    outlet / farfield_* / symmetry are flagged as CFD-domain class because
    their raw extents (1.5M–2.4M mm = 1500–2400 m) are implausible under
    any common unit. Decision should lock to MM via the airframe-class
    extent, not UNKNOWN via the overall bbox.
    """
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    # Mirror session 1 probe numbers (raw mm): airframe 182880, defects
    # 18290/27430/12700, domain walls 1600200/1540764/2438552.
    body_extents = [182880.0, 18290.0, 27430.0, 12700.0,
                    1600200.0, 1540764.0, 2438552.0]
    result = detect_unit(
        step_path=p,
        bbox_max_extent_raw=2438552.0,  # overall would be domain wall → UNKNOWN
        body_extents_raw=body_extents,
    )
    assert result.decision == GeometricUnit.MM
    assert result.confidence >= 0.85
    assert any("body-class filter" in line and "discarded" in line
               for line in result.evidence)
    assert any("airframe-class extent" in line for line in result.evidence)
    # Substrate finding: 4 of 7 bodies filter out (3 CFD-domain walls +
    # the Codex-3×-scaled airframe at 182m exceeds the 100m industrial
    # upper bound; 3 defects at 12.7/18.3/27.4 m carry the unit decision).
    assert any("4/7" in line for line in result.evidence)


def test_detect_unit_body_class_filter_all_implausible_falls_back(tmp_path: Path):
    """When every body has an implausible extent, body filter abstains
    and the existing bbox_max_extent_raw path runs unchanged."""
    p = tmp_path / "mm.step"
    p.write_text(_STEP_HEADER_MM)
    result = detect_unit(
        step_path=p,
        bbox_max_extent_raw=2438552.0,
        body_extents_raw=[1600200.0, 2438552.0, 1540764.0],
    )
    # Header says MM but bbox 2.4M mm = 2400 m is implausible under any
    # unit; matches existing "contradiction → UNKNOWN" path.
    assert result.decision == GeometricUnit.UNKNOWN
    assert any("all" in line and "implausible" in line
               for line in result.evidence)


def test_detect_unit_no_body_extents_backward_compat():
    """Calls without body_extents_raw behave exactly as before."""
    result = detect_unit(bbox_max_extent_raw=50000.0)
    # Existing behavior: 50000 raw is mm-plausible only (50 m) → MM.
    assert result.decision == GeometricUnit.MM


# ───── V130 advisor contract: must not be in mutation registry ─────


def test_unit_detector_module_not_in_mutation_registry():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for fn in KNOWN_MUTATION_FUNCTIONS:
        module = getattr(fn, "__module__", "")
        assert "unit_detector" not in module
