"""Build advisor-stack input dicts from case_006 ONERA M6 v1 live state.

Track C session 3 (M-STACK-TRACK-3) · validation case.

case_006 substrate: ~/Desktop/case_006_onera_m6_transonic/
v1 case dicts: case/system/snappyHexMeshDict + case/constant/thermophysicalProperties
parts manifest: inputs/parts_manifest.yaml (canonical V62-A convention)
STEP CAD: inputs/cad_codex_v1.step (387 KB, mm units per defect_manifest)

Validation truth (per .planning/case_profiles/case_006_onera_m6_transonic.md):
- Tier-1 reference geometry (ONERA M6, AGARD AR-138 / Schmitt 1979)
- Published Cp at 7 eta stations (0.20 .. 0.99)
- 7 net-new V-findings (V26-V32) surfaced during case-thread v1 baseline
- numerics_class = compressible_shock_density_based (rhoCentralFoam)
- Class NOT previously seen by stack (steady-laminar-CHT-multi-stream case_011
  + compressible-DES-acoustic case_016 are the LANDED prior classes)
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


__all__ = [
    "CASE_DIR",
    "SUBSTRATE_CASE",
    "build_parts_manifest",
    "build_shm_dict",
    "build_thermo_dict",
    "step_path",
]
