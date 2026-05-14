"""Build advisor-stack input dicts from case_004 NREL Phase VI MRF v1 live state.

V63-A Tier 2 sub-DEC M-CASE-EXT-1 · 4th distinct numerics class Track C session.

case_004 substrate: ~/Desktop/case_004_nrel_phase_vi_mrf/
v1 substrate: inputs/parts_manifest.yaml + inputs/cad_codex_v1.step + case/constant/MRFProperties
NOT available: case/system/snappyHexMeshDict + case/constant/thermophysicalProperties
            -> A8 shm_dict_validator + A10 thermo_polynomial_range_advisor silent-skip
            (faithful representation; case_004 substrate predates V62-A YAML convention
             for those dicts)

Validation truth (per .planning/case_profiles/case_004_nrel_phase_vi_mrf.md):
- Tier-1 reference: NREL/TP-500-29955 (NREL Phase VI 10 m HAWT)
- numerics_class = incompressible_RANS_MRF_rotating_machinery
- Class NOT previously seen by stack — first rotating-machinery + first MRF case.
  Pattern 6 root per case profile (no V-finding inheritance from case_002a/b nor case_003).
- 12 parts manifest: 1 cellzone + 1 domain + 3 rotating_wall + 3 stationary_wall +
  2 stationary_wall_auxiliary_defect (D1 + D8) + 1 inlet + 1 outlet + 1 farfield
- BC catalog stressors (v1 placeholder strings that should trip D10):
  * 3 rotating_wall parts declare U = movingWallVelocity_or_MRF_consistent_noSlip
    (NOT a real OpenFOAM BC type; placeholder pending v2 sub-session resolution)
"""
from __future__ import annotations

from pathlib import Path

import yaml

CASE_DIR = Path("/Users/Zhuanz/Desktop/case_004_nrel_phase_vi_mrf")


def build_parts_manifest() -> dict:
    """Load inputs/parts_manifest.yaml directly (canonical YAML)."""
    return yaml.safe_load((CASE_DIR / "inputs" / "parts_manifest.yaml").read_text())


def build_shm_dict() -> dict | None:
    """case_004 has no snappyHexMeshDict at v1.

    Returning None makes assemble_stack skip A8 (shm_dict_validator) entirely.
    This is faithful to substrate state — pretending we have a sHM dict would
    be synthetic. A8 silent-skip is the correct dispatch outcome.
    """
    return None


def build_thermo_dict() -> dict | None:
    """case_004 has no thermophysicalProperties at v1.

    Solver target is simpleFoam (incompressible) — only a transportProperties
    file is needed at v2 substrate land time (not the thermo file A10 inspects).
    Returning None makes assemble_stack skip A10.
    """
    return None


def step_path() -> Path:
    return CASE_DIR / "inputs" / "cad_codex_v1.step"


__all__ = [
    "CASE_DIR",
    "build_parts_manifest",
    "build_shm_dict",
    "build_thermo_dict",
    "step_path",
]
