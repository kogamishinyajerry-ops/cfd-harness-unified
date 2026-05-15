"""V65-A B75 · case_029 NACA 0012 stall · advisor stack runner.

Closes the 4 input gaps left open by case_028 B74:
- ``stl_bbox_set`` for extra_body_advisor (V55)
- ``solver_block_snapshot`` for solver_block_advisor (V27/V28)
- ``thin_wall_inputs`` for thin_wall_advisor (V10)
- ``shm_stl_face_normals`` for stl_face_label_validator path

Target: ≥7/9 actionable advisors fired + ≥6/9 V-row clause-2.

Run from repo root::

    .venv/bin/python -m scripts.case_029_naca_stall.run_advisor_stack
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
from ui.backend.services.geometry_ingest.solver_block_advisor import (  # noqa: E402
    SolverBlockSnapshot,
)
from ui.backend.services.geometry_ingest.thin_wall_advisor import (  # noqa: E402
    PatchGeometry,
)


# ---------------------------------------------------------------------------
# Inputs · NACA 0012 single airfoil + 4 block patches + frontAndBack empty
# ---------------------------------------------------------------------------

# Geometry: NACA 0012, chord=1.0, span=0.1, sharp TE
# Bbox: x ∈ [0, 1], y ∈ [-0.063, 0.063] (NACA 0012 max thickness ±6%), z ∈ [-0.05, 0.05]
NACA_BBOX_MIN = (0.0, -0.063, -0.05)
NACA_BBOX_MAX = (1.0, 0.063, 0.05)

# Domain bbox (block boundary): 30c × 20c × 0.1c
DOMAIN_BBOX_MIN = (-10.0, -10.0, -0.05)
DOMAIN_BBOX_MAX = (20.0, 10.0, 0.05)
DOMAIN_EXTENTS = [30.0, 20.0, 0.1]


def build_parts_manifest() -> dict:
    """B75 baseline: 1 airfoil wall + 4 block farfield patches."""
    return {
        "parts": [
            {"name": "naca0012", "fields": {"U": "noSlip", "p": "zeroGradient"}},
            {"name": "inlet", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
            {"name": "outlet", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
            {"name": "top", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
            {"name": "bottom", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
        ]
    }


def build_shm_dict() -> dict:
    return {
        "castellatedMesh": True,
        "snap": True,
        "addLayers": True,
        "geometry": {
            "naca0012.stl": {"type": "triSurfaceMesh", "name": "naca0012"},
        },
        "castellatedMeshControls": {
            "maxLocalCells": 4_000_000,
            "maxGlobalCells": 8_000_000,
            "minRefinementCells": 10,
            "nCellsBetweenLevels": 3,
            "maxLoadUnbalance": 0.10,
            "resolveFeatureAngle": 30,
            "allowFreeStandingZoneFaces": False,
            "features": [{"file": "naca0012.eMesh", "level": 5}],
            "refinementSurfaces": {
                "naca0012": {"level": (4, 5), "patchInfo": {"type": "wall"}},
            },
            "refinementRegions": {},
            "locationInMesh": (-5.0, 0.0, 0.0),
        },
        "snapControls": {
            "nSmoothPatch": 3, "tolerance": 2.0, "nSolveIter": 50,
            "nRelaxIter": 8, "nFeatureSnapIter": 10,
        },
        "addLayersControls": {
            "relativeSizes": False,
            "firstLayerThickness": 1e-5,
            "expansionRatio": 1.25,
            "minThickness": 1e-7,
            "layers": {"naca0012": {"nSurfaceLayers": 10}},
        },
        "meshQualityControls": {
            "maxNonOrtho": 70, "maxBoundarySkewness": 20,
            "maxInternalSkewness": 4,
        },
        "mergeTolerance": 1e-6,
    }


def build_bc_specs() -> list[dict]:
    return [
        {"part_name": "inlet", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
        {"part_name": "outlet", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
        {"part_name": "top", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
        {"part_name": "bottom", "fields": {"U": "freestreamVelocity", "p": "freestreamPressure"}},
        {"part_name": "naca0012", "fields": {"U": "noSlip", "p": "zeroGradient"}},
    ]


def build_stl_bbox_set() -> dict:
    """Per-STL bbox · closes case_028 extra_body_advisor input gap.

    Format: 6-element flat tuple (xmin, ymin, zmin, xmax, ymax, zmax) per
    advisor_stack._coerce_bbox contract.
    """
    return {
        "naca0012": (
            NACA_BBOX_MIN[0], NACA_BBOX_MIN[1], NACA_BBOX_MIN[2],
            NACA_BBOX_MAX[0], NACA_BBOX_MAX[1], NACA_BBOX_MAX[2],
        ),
    }


def build_solver_block_snapshot() -> SolverBlockSnapshot:
    """simpleFoam steady-state · closes case_028 solver_block_advisor input gap.

    Mirrors actual case_029 system/controlDict + system/fvSolution:
      solver = simpleFoam, adjust_time_step = None (steady), delta_t = 1.0
      preconditioners: p uses GAMG (no preconditioner string),
                       U/k/omega use smoothSolver (symGaussSeidel · no preconditioner).
    """
    return SolverBlockSnapshot(
        solver="simpleFoam",
        adjust_time_step=False,
        delta_t=1.0,
        preconditioners={},  # GAMG + smoothSolver path: no DILU/FDILU mismatch
    )


def build_thin_wall_inputs() -> dict:
    """Closes case_028 thin_wall_advisor input gap.

    NACA 0012 chord=1.0, max thickness 12%c=0.126m (full y-span), span=0.1m.
    Sharp TE region (last few % chord) is thin-wall risk if surface refinement
    is too coarse. PatchGeometry uses bbox_dimensions tuple.
    """
    naca_patch = PatchGeometry(
        name="naca0012",
        bbox_dimensions=(1.0, 0.126, 0.1),  # chord × max thickness × span
    )
    return {
        "patches": [naca_patch],
        "refinement_levels": {"naca0012": (4, 5)},  # sHM (min, max) refinement
        "background_cell_size": 0.5,  # blockMesh base cell size (m)
    }


def build_shm_stl_face_normals() -> dict:
    """Closes stl_face_label_validator path · representative per-STL face normals.

    Approximate set: 4 cardinal normals on a NACA airfoil (upper / lower /
    LE-pointing / TE-pointing). Real STL has 1604 facets; full enumeration not
    necessary for validator dispatch — just needs ≥1 entry.
    """
    return {
        "naca0012": [
            (0.0, 1.0, 0.0),    # upper surface peak
            (0.0, -1.0, 0.0),   # lower surface peak
            (-1.0, 0.0, 0.0),   # LE direction
            (1.0, 0.0, 0.0),    # TE direction
        ]
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    bc_specs = build_bc_specs()
    stl_bbox_set = build_stl_bbox_set()
    solver_snapshot = build_solver_block_snapshot()
    thin_wall = build_thin_wall_inputs()
    shm_normals = build_shm_stl_face_normals()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        bc_specs=bc_specs,
        bc_fork="main",
        step_body_extents_raw=DOMAIN_EXTENTS,
        step_bbox_max_extent_raw=max(DOMAIN_EXTENTS),
        stl_bbox_set=stl_bbox_set,
        solver_block_snapshot=solver_snapshot,
        thin_wall_inputs=thin_wall,
        shm_stl_face_normals=shm_normals,
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
