"""Build advisor-stack input dicts for case_006 ONERA M6 — TRACK-3-rerun.

M-STACK-TRACK-3-rerun re-runs the same case_006 substrate as TRACK-3
(retro `2026-05-14_stack_track_c_session_3_case_006.md`) but with the
two intervening Tier-2 milestones LANDED on origin/main:

  * DEC-V62-A-sub-REQ-SCHEMA-EXPAND — exposes step_path + step_bbox +
    step_extents + interface_bodies + interface_specs on
    AIReviewRequest; unblocks unit_detector via HTTP.
  * DEC-V62-A-sub-D10 — bc_type_name_validity_advisor LANDED; the
    advisor auto-extracts from parts_manifest's bc: blocks and flags
    foam-extend-only BC type names under fork='main'.

case_006 substrate is unchanged (read-only per dispatch); same
parts_manifest, snappyHexMeshDict, thermophysicalProperties, and STEP
file as TRACK-3. The only new wire artifacts are the step_path that
was previously route-stranded and the explicit bc_fork='main' selector
that pins D10 severity to critical for the case_006 farfield parts.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CASE_DIR = Path("/Users/Zhuanz/Desktop/case_006_onera_m6_transonic")
SUBSTRATE_CASE = CASE_DIR / "case"


def build_parts_manifest() -> dict:
    """Load inputs/parts_manifest.yaml directly (canonical YAML)."""
    return yaml.safe_load((CASE_DIR / "inputs" / "parts_manifest.yaml").read_text())


def build_shm_dict() -> dict:
    """Manual translation of case/system/snappyHexMeshDict v1."""
    return {
        "castellatedMesh": True,
        "snap": True,
        "addLayers": False,
        "geometry": {
            "wing_surface_reference": {
                "type": "triSurfaceMesh",
                "file": "wing_surface_reference.stl",
            },
            "tip_cap": {
                "type": "triSurfaceMesh",
                "file": "tip_cap.stl",
            },
            "root_fairing_pad": {
                "type": "triSurfaceMesh",
                "file": "root_fairing_pad.stl",
            },
            "root_fairing_cover": {
                "type": "triSurfaceMesh",
                "file": "root_fairing_cover.stl",
            },
            "tip_cap_sliver": {
                "type": "triSurfaceMesh",
                "file": "tip_cap_sliver.stl",
            },
        },
        "castellatedMeshControls": {
            "maxLocalCells": 4_000_000,
            "maxGlobalCells": 6_000_000,
            "minRefinementCells": 0,
            "nCellsBetweenLevels": 3,
            "resolveFeatureAngle": 30,
            "allowFreeStandingZoneFaces": True,
            "features": [],
            "refinementSurfaces": {
                "wing_surface_reference": {
                    "level": [4, 5],
                    "patchInfo": {"type": "wall"},
                },
                "tip_cap": {
                    "level": [4, 5],
                    "patchInfo": {"type": "wall"},
                },
                "root_fairing_pad": {
                    "level": [3, 4],
                    "patchInfo": {"type": "wall"},
                },
                "root_fairing_cover": {
                    "level": [3, 4],
                    "patchInfo": {"type": "wall"},
                },
                "tip_cap_sliver": {
                    "level": [1, 2],
                    "patchInfo": {"type": "wall"},
                },
            },
            "refinementRegions": {},
            "locationInMesh": [-5.0, 5.0, 5.0],
        },
        "snapControls": {
            "nSmoothPatch": 3,
            "tolerance": 2.0,
            "nSolveIter": 30,
            "nRelaxIter": 5,
            "nFeatureSnapIter": 10,
            "implicitFeatureSnap": False,
            "explicitFeatureSnap": True,
            "multiRegionFeatureSnap": False,
        },
        "addLayersControls": {
            "relativeSizes": True,
            "layers": {},
            "expansionRatio": 1.2,
            "finalLayerThickness": 0.4,
            "minThickness": 0.05,
        },
        "meshQualityControls": {},
        "mergeTolerance": 1e-6,
    }


def build_thermo_dict() -> dict:
    """case_006 v1 thermophysicalProperties — hePsiThermo + perfectGas +
    eConst + const transport. Non-polynomial form → A10 silent-skip."""
    return {
        "thermoType": {
            "type": "hePsiThermo",
            "mixture": "pureMixture",
            "transport": "const",
            "thermo": "eConst",
            "equationOfState": "perfectGas",
            "specie": "specie",
            "energy": "sensibleInternalEnergy",
        },
        "mixture": {
            "specie": {"molWeight": 28.96},
            "thermodynamics": {"Cv": 717.5, "Hf": 0},
            "transport": {"mu": 1.7894e-5, "Pr": 0.71},
        },
    }


def step_path() -> Path:
    return CASE_DIR / "inputs" / "cad_codex_v1.step"


# Project-default fork; case_006 targets opencfd/openfoam-default:2312.
BC_FORK_DEFAULT = "main"


__all__ = [
    "BC_FORK_DEFAULT",
    "CASE_DIR",
    "SUBSTRATE_CASE",
    "build_parts_manifest",
    "build_shm_dict",
    "build_thermo_dict",
    "step_path",
]
