"""Geometric unit detection for CAD ingest (V198 preprocessing engine · P0).

The most common silent preprocessing failure in industrial CFD is the
**unit mis-interpretation**: a STEP file authored in inches is read by a
CAD library that defaults to mm-as-numeric-units, producing a geometry
that is 25.4× the intended size. Downstream mesh sizing, BC velocity
references, and verdict tolerances are all silently wrong.

case_003 (CRM-HLS) paused at exactly this failure mode (V20 in V-series).
APU bay avoided it only because the engineer hand-coded a unit-scale check
into 02_domain_subtract.py.

This module surfaces two pure-logic signals:

1. **Declared unit** from the STEP header (regex over ASCII STEP file). No
   FreeCAD required.
2. **Plausibility from bbox magnitude** under each candidate unit, against
   an industrial-CFD-typical extent range (default 1cm-1km; V97 widened
   the upper bound from 100m to 1000m to cover full-aircraft / ship /
   civil-structure scale geometries).

The combined decision is **advisory only** (V130 advisor philosophy).
Decision = UNKNOWN flips the route layer into "engineer must confirm" mode;
decision = a specific unit with confidence is a recommendation, not a
mutation trigger.

V-series: V20 (case_003 unit-scale issue).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class GeometricUnit(str, Enum):
    MM = "mm"
    CM = "cm"
    M = "m"
    INCH = "inch"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UnitDetection:
    """Advisory result: declared unit (from header), plausible units (from
    bbox magnitude), combined decision + confidence, and human-readable
    evidence lines for TrustGate-style engineer review."""

    declared_unit: Optional[GeometricUnit]
    bbox_plausible_units: tuple[GeometricUnit, ...]
    decision: GeometricUnit
    confidence: float  # 0.0 - 1.0
    evidence: tuple[str, ...]


_SI_UNIT_RE = re.compile(
    # STEP EXPRESS prefix slot may be: $, *, .MILLI., .CENTI., .KILO., etc.,
    # or a bare . . (empty optional dot pair). Capture the recognized prefix.
    r"SI_UNIT\s*\(\s*(?:\$|\*|\.(MILLI|CENTI|KILO|MICRO|DECI)?\.)\s*,\s*\.METRE\.",
    re.IGNORECASE,
)
_CONVERSION_INCH_RE = re.compile(
    r"CONVERSION_BASED_UNIT\s*\(\s*'INCH'", re.IGNORECASE
)
_CONVERSION_FOOT_RE = re.compile(
    r"CONVERSION_BASED_UNIT\s*\(\s*'(FOOT|FT)'", re.IGNORECASE
)

_INDUSTRIAL_EXTENT_RANGE_M: tuple[float, float] = (0.01, 1000.0)
_UNIT_TO_METERS: dict[GeometricUnit, float] = {
    GeometricUnit.MM: 1e-3,
    GeometricUnit.CM: 1e-2,
    GeometricUnit.M: 1.0,
    GeometricUnit.INCH: 0.0254,
}


def parse_step_header_unit(
    step_path: Path | str,
    max_bytes: int = 1_048_576,
) -> tuple[Optional[GeometricUnit], list[str]]:
    """Extract the LENGTH unit declared in a STEP file header.

    Reads only the first `max_bytes` (default 1 MB) because STEP UNIT
    declarations may sit anywhere in the DATA section — ST-Developer /
    CATIA-V5 AP242 / HLPW6 exporters place GLOBAL_UNIT_ASSIGNED_CONTEXT
    near end-of-file (V96 sediment: HLPW6 source STEP has INCH decl at
    byte 707,430 of 716,110). The historical 64 KB default silently
    truncated industrial Tier-1 files. Returns
    (unit | None, [evidence_line, ...]). UNKNOWN means a recognized
    declaration was found but maps to something we don't handle (e.g.,
    FOOT, MICRO-METRE).
    """
    evidence: list[str] = []
    path = Path(step_path)
    if not path.exists():
        evidence.append(f"STEP file not found at {path}")
        return None, evidence
    try:
        with path.open("rb") as fh:
            data = fh.read(max_bytes)
        text = data.decode("ascii", errors="replace")
    except OSError as exc:
        evidence.append(f"Failed to read STEP header: {exc}")
        return None, evidence

    # Check imperial first — some STEP files declare imperial length + SI
    # angle/area, and we want the length signal.
    if _CONVERSION_INCH_RE.search(text):
        evidence.append("STEP header declares CONVERSION_BASED_UNIT('INCH')")
        return GeometricUnit.INCH, evidence
    if _CONVERSION_FOOT_RE.search(text):
        evidence.append(
            "STEP header declares CONVERSION_BASED_UNIT('FOOT') — unsupported in detector"
        )
        return GeometricUnit.UNKNOWN, evidence

    si_match = _SI_UNIT_RE.search(text)
    if si_match:
        prefix = (si_match.group(1) or "").upper()
        if prefix == "MILLI":
            evidence.append("STEP header declares SI_UNIT(.MILLI.,.METRE.)")
            return GeometricUnit.MM, evidence
        if prefix == "CENTI":
            evidence.append("STEP header declares SI_UNIT(.CENTI.,.METRE.)")
            return GeometricUnit.CM, evidence
        if prefix == "":
            evidence.append("STEP header declares SI_UNIT(*,.METRE.)")
            return GeometricUnit.M, evidence
        evidence.append(
            f"STEP header declares SI_UNIT(.{prefix}.,.METRE.) — prefix not in detector range"
        )
        return GeometricUnit.UNKNOWN, evidence

    evidence.append("STEP header does not contain a recognized LENGTH unit declaration")
    return None, evidence


def bbox_plausible_units(
    raw_max_extent: float,
    industrial_range_m: tuple[float, float] = _INDUSTRIAL_EXTENT_RANGE_M,
) -> tuple[GeometricUnit, ...]:
    """Return units under which the raw bbox extent value would put the
    geometry inside industrial-CFD-typical size range.

    Industrial CFD geometries span roughly 1 cm (small heat-exchanger fin)
    to 100 m (full aircraft / ship section). A raw value of 50000 is only
    plausible as mm (= 50 m); a raw value of 2.5 is plausible as m or
    inch but not as mm; etc.
    """
    if raw_max_extent <= 0:
        return ()
    lo_m, hi_m = industrial_range_m
    plausible: list[GeometricUnit] = []
    for unit in (GeometricUnit.MM, GeometricUnit.CM, GeometricUnit.M, GeometricUnit.INCH):
        extent_m = raw_max_extent * _UNIT_TO_METERS[unit]
        if lo_m <= extent_m <= hi_m:
            plausible.append(unit)
    return tuple(plausible)


def detect_unit(
    step_path: Optional[Path | str] = None,
    bbox_max_extent_raw: Optional[float] = None,
    body_extents_raw: Optional[list[float]] = None,
) -> UnitDetection:
    """Combine STEP header and bbox-magnitude signals into a single advisory.

    Either signal may be None; if both are None the result is UNKNOWN with
    zero confidence. The advisor strictly does not mutate; the caller is
    responsible for surfacing the decision to the engineer.

    When ``body_extents_raw`` is supplied (per-body max bbox extents), bodies
    whose extent is implausible under every common unit (mm/cm/m/inch) are
    discarded as "CFD-domain class" (F-NEW-12 fix). The largest extent among
    the surviving "airframe class" bodies replaces ``bbox_max_extent_raw``
    for the unit decision. If no body survives the filter, the supplied
    ``bbox_max_extent_raw`` is used as-is (backward-compatible).
    """
    evidence: list[str] = []
    declared: Optional[GeometricUnit] = None
    bbox_plaus: tuple[GeometricUnit, ...] = ()

    if step_path is not None:
        declared, header_ev = parse_step_header_unit(step_path)
        evidence.extend(header_ev)

    if body_extents_raw:
        plausible_bodies = [ext for ext in body_extents_raw
                            if ext > 0 and bbox_plausible_units(ext)]
        domain_count = len(body_extents_raw) - len(plausible_bodies)
        if plausible_bodies:
            airframe_extent = max(plausible_bodies)
            evidence.append(
                f"body-class filter: {domain_count}/{len(body_extents_raw)} bodies "
                f"discarded as CFD-domain class (implausible under any common unit). "
                f"Using largest airframe-class extent {airframe_extent:.4g} for unit decision."
            )
            bbox_max_extent_raw = airframe_extent
        else:
            evidence.append(
                f"body-class filter: all {len(body_extents_raw)} bodies have implausible "
                f"extents; falling back to overall bbox_max_extent_raw if supplied."
            )

    if bbox_max_extent_raw is not None:
        bbox_plaus = bbox_plausible_units(bbox_max_extent_raw)
        if bbox_plaus:
            evidence.append(
                f"bbox extent {bbox_max_extent_raw:.4g} (raw) is industrially plausible "
                f"if unit is one of: {', '.join(u.value for u in bbox_plaus)}"
            )
        else:
            evidence.append(
                f"bbox extent {bbox_max_extent_raw:.4g} (raw) is NOT industrially "
                f"plausible under any common unit (mm/cm/m/inch). Likely "
                f"source mis-scaling or non-CFD-sized geometry."
            )

    # Decision: declared signal trusted when present and not contradicted.
    if declared is not None and declared != GeometricUnit.UNKNOWN:
        if bbox_max_extent_raw is None:
            evidence.append(
                f"Decision based on STEP header alone: {declared.value} (no bbox cross-check)"
            )
            return UnitDetection(
                declared_unit=declared,
                bbox_plausible_units=(),
                decision=declared,
                confidence=0.8,
                evidence=tuple(evidence),
            )
        if declared in bbox_plaus:
            confidence = 1.0 if len(bbox_plaus) == 1 else 0.85
            evidence.append(
                f"Declared unit {declared.value} agrees with bbox plausibility "
                f"(confidence {confidence:.2f})"
            )
            return UnitDetection(
                declared_unit=declared,
                bbox_plausible_units=bbox_plaus,
                decision=declared,
                confidence=confidence,
                evidence=tuple(evidence),
            )
        # Contradiction — flag for engineer.
        evidence.append(
            f"WARNING: STEP declares {declared.value} but bbox magnitude only matches "
            f"{[u.value for u in bbox_plaus] or 'no plausible unit'}. "
            f"Likely a unit mismatch in the upstream CAD chain."
        )
        return UnitDetection(
            declared_unit=declared,
            bbox_plausible_units=bbox_plaus,
            decision=GeometricUnit.UNKNOWN,
            confidence=0.0,
            evidence=tuple(evidence),
        )

    # No declared signal (or UNKNOWN from header) — fall back to bbox only.
    if not bbox_plaus:
        return UnitDetection(
            declared_unit=declared,
            bbox_plausible_units=(),
            decision=GeometricUnit.UNKNOWN,
            confidence=0.0,
            evidence=tuple(evidence),
        )
    if len(bbox_plaus) == 1:
        evidence.append(
            f"Single plausible unit from bbox: {bbox_plaus[0].value}; "
            f"no STEP header confirmation."
        )
        return UnitDetection(
            declared_unit=declared,
            bbox_plausible_units=bbox_plaus,
            decision=bbox_plaus[0],
            confidence=0.5,
            evidence=tuple(evidence),
        )
    evidence.append(
        f"Multiple plausible units from bbox alone: {', '.join(u.value for u in bbox_plaus)}. "
        f"Engineer confirmation required."
    )
    return UnitDetection(
        declared_unit=declared,
        bbox_plausible_units=bbox_plaus,
        decision=GeometricUnit.UNKNOWN,
        confidence=0.0,
        evidence=tuple(evidence),
    )
