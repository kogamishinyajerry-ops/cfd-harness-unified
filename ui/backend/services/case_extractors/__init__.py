"""case_extractors · case-dir → advisor-kwargs extractors.

Per DEC-V61-211 + DEC-V61-212 (Stage-2 2b extension sub-DECs), this
sub-package houses pure-function readers that build the structured
inputs `assemble_stack` consumes (`SolverBlockSnapshot`, `shm_dict`,
`thermo_dict`, `step_path`, etc.) from on-disk OpenFOAM case
directories.

v0.1 + V61-212 + V61-213 + V61-214 + V61-217-W3.0 + V61-217-W3.0.1 + V61-217-W3.0.2 ships SEVEN extractors:
  - `solver_block_extractor.extract` → `SolverBlockSnapshot | None`
    (DEC-V61-211 — `system/controlDict`)
  - `shm_dict_extractor.extract`     → `Mapping[str, Any] | None`
    (DEC-V61-212 — `system/snappyHexMeshDict`)
  - `thermo_dict_extractor.extract`  → `(Mapping, ThermoModelTags) | None`
    (DEC-V61-213 — `constant/thermophysicalProperties`)
  - `step_extractor.extract`         → `StepArtifacts | None`
    (DEC-V61-214 — `*.step` / `cad/bbox.json` / `manifest.json` discovery)
  - `region_properties_reader.extract` → `RegionPropertiesSnapshot | None`
    (DEC-V61-217 W3.0 — `constant/regionProperties`)
  - `shm_dict_multi_region.extract`  → `Mapping[str, RegionShmSnapshot | None] | None`
    (DEC-V61-217 W3.0.1 — master sHM per-region cellZone-derived mapping)
  - `thermo_dict_multi_region.extract` → `Mapping[str, RegionThermoSnapshot | None] | None`
    (DEC-V61-217 W3.0.2 / sub-DEC V61-220 — per-region thermophysicalProperties multi-region reader)

Other extractors are deferred to follow-on sub-DECs (see DEC-V61-211
"Out of scope") — adding to this package later is additive.

All extractors are:
  - **Pure**: read files, return dataclasses or Mappings; no writes,
    no I/O beyond `Path.read_text`, no globals.
  - **Honest**: return `None` (not a defaulted snapshot / not partial
    fabrication) when the source file is absent or unparseable; never
    fabricate values.
  - **Stdlib only**: no third-party deps (no PyFoam / fluidfoam / foamlib);
    crucially no import from `ui.backend.services.geometry_ingest` (would
    pull `trimesh` transitively via `__init__.py → health_check`).
  - **Scope-locked**: each extractor's docstring records explicitly what
    OpenFOAM-dict features it does NOT parse, so callers cannot assume
    more than is implemented.
"""

from .region_properties_reader import extract as extract_region_properties_snapshot
from .shm_dict_extractor import extract as extract_shm_dict
from .shm_dict_multi_region import extract as extract_shm_dict_multi_region
from .solver_block_extractor import extract as extract_solver_block_snapshot
from .step_extractor import extract as extract_step_path_snapshot
from .thermo_dict_extractor import extract as extract_thermo_dict_snapshot
from .thermo_dict_multi_region import extract as extract_thermo_dict_multi_region

__all__ = [
    "extract_region_properties_snapshot",
    "extract_shm_dict",
    "extract_shm_dict_multi_region",
    "extract_solver_block_snapshot",
    "extract_step_path_snapshot",
    "extract_thermo_dict_snapshot",
    "extract_thermo_dict_multi_region",
]
