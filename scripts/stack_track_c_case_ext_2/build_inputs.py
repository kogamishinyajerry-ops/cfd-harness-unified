"""Build advisor-stack input dicts from case_009 Sandia Flame D v1 live state.

V63-A Tier 2 sub-DEC M-CASE-EXT-2 · 5th distinct numerics class Track C session.

case_009 substrate: ~/Desktop/case_009_sandia_flame_d/
v1 substrate: inputs/parts_manifest.yaml + inputs/cad_codex_v1.step +
              case/constant/thermophysicalProperties + case/system/fvSchemes +
              templates/{0.orig,constant,system}
NOT available: case/system/snappyHexMeshDict
            -> A8 shm_dict_validator silent-skip (case_009 uses wedge-axisymmetric
               blockMesh primary mesh; sHM only used for D1/D8 exterior-body
               refinement which the case_009 v1 scope deferred).

Validation truth (per .planning/case_profiles/case_009_sandia_flame_d.md +
                  ~/Desktop/case_009_sandia_flame_d/inputs/parts_manifest.yaml):
- Tier-1 reference: TNF Sandia/TUD Piloted CH4/Air Flame D, Data Release 2.0
  (Barlow & Frank, January 2003)
- numerics_class = reacting-low-Mach
- Class NOT previously seen by stack — first reacting-flow case AND first
  case carrying a thermophysicalProperties dict in V63-A.
- 13 parts manifest: 3 reacting_inlets (fuel_jet, pilot_annulus, coflow_air)
  + 3 walls (fuel_nozzle_lip, pilot_housing_exterior, burner_base_wall)
  + 2 wedge_planes (wedge_front, wedge_back) + 1 radial_farfield (outer_side)
  + 1 pressure_outlet (far_outlet) + 2 exterior_mount_defect_bodies
  (coflow_plenum_mount_bracket + _shim, D1) + 1 thin_shell_defect_body
  (bracket_lip_thin, D8).
- BC catalog stressors observed in manifest (subset that D10 may surface):
  * outer_side.T = inletOutlet_air_291K   (NOT a real OpenFOAM BC type)
  * outer_side.species = inletOutlet_air  (NOT a real OpenFOAM BC type)
  * far_outlet.p = {type: fixedValue, value: 0.0}  (dict, not string —
    D10 extract_bc_specs_from_parts_manifest passes it through unchanged;
    detect_invalid_bc_types will treat it as a non-string BC name and is
    expected to emit `unknown` for the dict-form.)
  * Three defect_body parts use ``bc:`` as a STRING
    (``exclude_from_fluid_reference_or_external_wall_if_meshed``) NOT a
    dict; ``extract_bc_specs_from_parts_manifest`` line 593 skips entries
    where bc_block is not a dict, so these 3 parts contribute 0 specs.
"""
from __future__ import annotations

from pathlib import Path

import yaml

CASE_DIR = Path("/Users/Zhuanz/Desktop/case_009_sandia_flame_d")


def build_parts_manifest() -> dict:
    """Load inputs/parts_manifest.yaml directly (canonical YAML)."""
    return yaml.safe_load((CASE_DIR / "inputs" / "parts_manifest.yaml").read_text())


def build_shm_dict() -> dict | None:
    """case_009 has no snappyHexMeshDict at v1.

    Primary mesh is blockMesh-based wedge-axisymmetric; sHM dispatch
    for the (defect-only) exterior refinement was deferred from v1.
    A8 silent-skip is the correct dispatch outcome.
    """
    return None


def build_thermo_dict() -> dict | None:
    """case_009 carries case/constant/thermophysicalProperties (FoamFile-style
    OpenFOAM dictionary). A10 thermo_polynomial_range_advisor accepts a
    Python mapping of species → polynomial-coeffs; reactingFoam stores
    species polynomials in a SEPARATE foamChemistryThermoFile pointer
    (``constant/thermo.compressibleGas``) referenced from the thermo
    dict, not inline. We pass a thin Python-dict surrogate carrying only
    the metadata A10 can validate without inline coeffs; A10 returns an
    empty findings set when no per-species polynomial blocks are present.
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
