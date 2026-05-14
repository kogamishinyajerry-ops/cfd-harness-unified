"""Build advisor-stack input dicts from case_011 v5b live state.

Track C session 1 (M-STACK-TRACK-1).

case_011 v5b substrate: ~/Desktop/case_011_plate_fin_compact_hx/
v5b live snappyHexMeshDict: case/system/snappyHexMeshDict (mtime 2026-05-13 22:56)
v5b mesh: 3 regions (hot 3.34M / cold 2.98M / solid 5.85M cells)
v5b thin_wall_d8.json: evidence/v1/thin_wall_d8.json (0.6mm cold fin → critical)
v5b STEP: inputs/cad_codex_v1.step (mtime 2026-05-09)

No advisor-input YAMLs exist under inputs/ — case_011 substrate predates the
V62-A canonical convention. Inputs are derived from raw artifacts here.
"""
from __future__ import annotations

import json
from pathlib import Path

CASE_DIR = Path("/Users/Zhuanz/Desktop/case_011_plate_fin_compact_hx")
SUBSTRATE_CASE = CASE_DIR / "case"


def build_shm_dict() -> dict:
    """Manual translation of case/system/snappyHexMeshDict (v5b live)."""
    return {
        "castellatedMesh": True,
        "snap": True,
        "addLayers": False,
        "geometry": {
            "region_hot_fluid.stl":  {"type": "triSurfaceMesh", "name": "region_hot_fluid"},
            "region_cold_fluid.stl": {"type": "triSurfaceMesh", "name": "region_cold_fluid"},
            "region_solid.stl":      {"type": "triSurfaceMesh", "name": "region_solid"},
        },
        "castellatedMeshControls": {
            "maxLocalCells": 200000,
            "maxGlobalCells": 8000000,
            "minRefinementCells": 10,
            "nCellsBetweenLevels": 2,
            "resolveFeatureAngle": 30,
            "features": [
                {"file": "region_hot_fluid.eMesh",  "level": 2},
                {"file": "region_cold_fluid.eMesh", "level": 2},
                {"file": "region_solid.eMesh",      "level": 2},
            ],
            "refinementSurfaces": {
                "region_hot_fluid": {
                    "level": [1, 2],
                    "cellZone": "region_hot_fluid",
                    "faceZone": "region_hot_fluid",
                    "cellZoneInside": "insidePoint",
                    "insidePoint": [0.090, 0.05825, 0.045],
                },
                "region_cold_fluid": {
                    "level": [2, 3],
                    "cellZone": "region_cold_fluid",
                    "faceZone": "region_cold_fluid",
                    "cellZoneInside": "inside",
                },
                "region_solid": {
                    "level": [3, 4],
                    "cellZone": "region_solid",
                    "faceZone": "region_solid",
                    "cellZoneInside": "insidePoint",
                    "insidePoint": [0.090, 0.060, 0.0191],
                },
            },
            "refinementRegions": {},
            "locationInMesh": [0.090, 0.06175, 0.045],
            "allowFreeStandingZoneFaces": True,
        },
        "snapControls": {
            "nSmoothPatch": 3,
            "tolerance": 2.0,
            "nSolveIter": 30,
            "nRelaxIter": 5,
            "nFeatureSnapIter": 10,
            "implicitFeatureSnap": True,
            "explicitFeatureSnap": False,
            "multiRegionFeatureSnap": True,
        },
        "addLayersControls": {
            "relativeSizes": True,
            "layers": {},
            "expansionRatio": 1.2,
            "finalLayerThickness": 0.5,
            "minThickness": 0.1,
            "nGrow": 0,
            "featureAngle": 180,
            "nRelaxIter": 3,
            "nSmoothSurfaceNormals": 1,
            "nSmoothNormals": 3,
            "nSmoothThickness": 10,
            "maxFaceThicknessRatio": 0.5,
            "maxThicknessToMedialRatio": 0.3,
            "minMedialAxisAngle": 90,
            "nBufferCellsNoExtrude": 0,
            "nLayerIter": 50,
        },
        "meshQualityControls": {"#include": "meshQualityDict"},
        "debug": 0,
        "mergeTolerance": 1e-6,
    }


def build_parts_manifest() -> dict:
    """parts_manifest reflecting case_011 v5b's three STL bodies.

    Honest reflection of v5b reality:
    - STL files have NO labeled inlet/outlet face-zones (V94 caveat documented
      in v3 sub-DEC § footer). Solver ran degenerate pure-conduction problem.
    - parts_manifest below has 'role: cellZone' (not inlet/outlet) so
      inlet_outlet_validator skips them all — this exposes the V94 gap.
    - actual_face_normal not measurable from raw STL without face-zone labels;
      face_orientation_advisor will skip these parts (bodies skipped, advisor
      runs but reports zero findings).
    """
    return {
        "parts": [
            {"name": "region_hot_fluid",  "role": "cellZone",
             "boundary_emission": "sealed_room_natural_convection",
             "bbox": [0.0, 0.0, 0.0, 0.18, 0.118, 0.090]},
            {"name": "region_cold_fluid", "role": "cellZone",
             "boundary_emission": "sealed_room_natural_convection",
             "bbox": [0.0, 0.0, 0.0, 0.18, 0.118, 0.090]},
            {"name": "region_solid",      "role": "cellZone",
             "boundary_emission": "sealed_room_natural_convection",
             "bbox": [0.0, 0.0, 0.0, 0.18, 0.118, 0.090]},
        ],
        "boundary_zones": [],
    }


def build_thin_wall_inputs() -> dict:
    """Lift from evidence/v1/thin_wall_d8.json (canonical D8 falsification)."""
    return {
        "patches": [
            {
                "name": "cold_fin_rear_third",
                "bbox_dimensions": [0.0006, 0.016, 0.18],
            }
        ],
        "refinement_levels": {"cold_fin_rear_third": [1, 2]},
        "background_cell_size": 0.004,
    }


# thermo_dict skipped — case_011 uses const/hConst thermo, NOT JANAF tables.
# thermo_polynomial_range_advisor expects per-species Tlow/Thigh fields; the
# const-thermo dict has no Tlow → advisor either skips or reports nothing.
# Including it would muddy the dispatch trail; document the absence instead.


def build_step_payload() -> dict:
    """Step path for unit_detector. Real case_011 input."""
    return {
        "step_path": str(CASE_DIR / "inputs" / "cad_codex_v1.step"),
        "step_bbox_max_extent_raw": 0.180,  # 180 mm = 0.180 m, plausible m-units
    }


def assemble_payload() -> dict:
    """Assemble all input artifacts for stack dispatch."""
    return {
        "case_label": "case_011_v5b",
        "parts_manifest": build_parts_manifest(),
        "shm_dict": build_shm_dict(),
        "thin_wall_inputs": build_thin_wall_inputs(),
        **build_step_payload(),
    }


if __name__ == "__main__":
    payload = assemble_payload()
    out = Path(__file__).parent / "case_011_v5b_payload.json"
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"payload written: {out}")
    print(f"shm geometry keys: {list(payload['shm_dict']['geometry'].keys())}")
    print(f"parts count: {len(payload['parts_manifest']['parts'])}")
    print(f"thin_wall patches: {len(payload['thin_wall_inputs']['patches'])}")
