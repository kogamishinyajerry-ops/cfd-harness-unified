"""DEC-V61-139 (N3 charter) · physics / materials service module.

Lives above the case_dicts raw-edit allowlist (DEC-V61-102) — provides
**structured** wire contracts (MaterialContract, future RegimeContract)
that the engineer fills via the Step Physics panel. The module's
writer translates these into the legacy OpenFOAM dict files
(``constant/physicalProperties``, ``constant/momentumTransport``).

Public surface (built up across N3.1-N3.5):
  * MATERIAL_PRESETS       — bundled fluid library (N3.1)
  * get_material_preset()  — preset lookup (N3.1)
  * future N3.2: REGIME_PRESETS, get_regime_preset
  * future N3.3: write_physics_dicts(case_dir, contract) — writer
  * future N3.4: derive_solver(regime) — solver derivation table
"""
from __future__ import annotations

from ui.backend.services.physics.materials_library import (
    MATERIAL_PRESETS,
    MaterialPreset,
    get_material_preset,
    list_material_preset_ids,
)

__all__ = [
    "MATERIAL_PRESETS",
    "MaterialPreset",
    "get_material_preset",
    "list_material_preset_ids",
]
