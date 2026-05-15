"""V65-A B74 · case_028 APU bay ventilation · advisor stack runner.

Invokes ``assemble_stack`` on case_028 substrate inputs and prints findings +
V-row attributions. Target ≥5/9 V-row clause-2 attribution.

Run from repo root::

    .venv/bin/python -m scripts.case_028_apu_bay.run_advisor_stack
    (or)  PYTHONPATH=. python3 scripts/case_028_apu_bay/run_advisor_stack.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 4Q gate Q1: strip LLM keys before any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402


# ---------------------------------------------------------------------------
# Inputs (mirror case_028 substrate · in-memory · no file IO into backend)
# ---------------------------------------------------------------------------

# 29 per_solid components · all walls in B74 baseline
COMPONENTS = [
    "Outer_Surf", "Inner_Surf", "Plane_Outer_Surf",
    "intake_duct", "vent_door", "door", "plenum",
    "exhaust_pipe_1", "exhaust_section", "bleed_air_pipe", "ejector",
    "gearbox_1", "gearbox_2", "compressor", "load_compressor", "load_volute",
    "combustion_chamber", "fuel_valve",
    "firewall_front", "firewall_behind",
    "Frame_1", "Frame_2", "Frame_3", "Frame_4", "Frame_5", "Frame_6",
    "beam_1", "beam_2", "beam_3",
]


def build_parts_manifest() -> dict:
    """B74 baseline: all per_solid components → noSlip walls."""
    return {
        "parts": [
            {
                "name": name,
                "fields": {"U": "noSlip", "p": "zeroGradient"},
            }
            for name in COMPONENTS
        ]
    }


def build_shm_dict() -> dict:
    """Mirror system/snappyHexMeshDict refinementSurfaces structure."""
    return {
        "castellatedMesh": True,
        "snap": True,
        "addLayers": False,
        "geometry": {f"{name}.stl": {"type": "triSurfaceMesh", "name": name} for name in COMPONENTS},
        "castellatedMeshControls": {
            "maxLocalCells": 5_000_000,
            "maxGlobalCells": 10_000_000,
            "minRefinementCells": 10,
            "nCellsBetweenLevels": 2,
            "maxLoadUnbalance": 0.10,
            "resolveFeatureAngle": 60,
            "allowFreeStandingZoneFaces": False,
            "features": [],
            "refinementSurfaces": {
                name: {"level": (0, 1), "patchInfo": {"type": "wall"}}
                for name in COMPONENTS
            },
            "refinementRegions": {},
            "locationInMesh": (63.8, 0.5, 0.0),
        },
        "snapControls": {
            "nSmoothPatch": 3, "tolerance": 2.0, "nSolveIter": 30,
            "nRelaxIter": 5, "nFeatureSnapIter": 10,
        },
        "meshQualityControls": {
            "maxNonOrtho": 65, "maxBoundarySkewness": 20,
            "maxInternalSkewness": 4,
        },
        "mergeTolerance": 1e-6,
    }


def build_bc_specs() -> list[dict]:
    """Boundary conditions per case_028 0/U · 0/p (block patches + STL walls)."""
    specs = [
        {"part_name": "inlet", "fields": {"U": "fixedValue", "p": "zeroGradient"}},
        {"part_name": "outlet", "fields": {"U": "zeroGradient", "p": "fixedValue"}},
        {"part_name": "bay_top", "fields": {"U": "slip", "p": "slip"}},
        {"part_name": "bay_bottom", "fields": {"U": "slip", "p": "slip"}},
        {"part_name": "bay_side_p", "fields": {"U": "slip", "p": "slip"}},
        {"part_name": "bay_side_n", "fields": {"U": "slip", "p": "slip"}},
    ]
    for name in COMPONENTS:
        specs.append({"part_name": name, "fields": {"U": "noSlip", "p": "zeroGradient"}})
    return specs


def build_step_body_extents() -> list[float]:
    """Bay enclosure bbox dimensions (m) · unit_detector input."""
    # bbox: (63.5, -1.0, -1.5) to (67.5, 2.5, 1.5) → 4 × 3.5 × 3 m
    return [4.0, 3.5, 3.0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    bc_specs = build_bc_specs()
    body_extents = build_step_body_extents()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        bc_specs=bc_specs,
        bc_fork="main",
        step_body_extents_raw=body_extents,
        step_bbox_max_extent_raw=max(body_extents),
    )

    summary = {
        "advisor_count": report.advisor_count,
        "advisor_calls": [c.advisor_name for c in report.advisor_calls],
        "finding_count": len(report.findings),
        "findings_by_advisor": {},
        "evidence_refs": sorted(set(report.evidence_refs)),
    }
    for f in report.findings:
        summary["findings_by_advisor"].setdefault(f.source_advisor, []).append({
            "severity": getattr(f, "severity", "?"),
            "code": getattr(f, "code", "?"),
            "message": getattr(f, "message", "?")[:200],
        })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
