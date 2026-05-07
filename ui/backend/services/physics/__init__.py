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
from ui.backend.services.physics.regimes_library import (
    REGIME_PRESETS,
    RegimePreset,
    get_regime_preset,
    list_regime_preset_ids,
)
from ui.backend.services.physics.solver_derivation import (
    SOLVER_DERIVATIONS,
    SolverDerivation,
    SolverName,
    derive_solver,
)
from ui.backend.services.physics.tolerance_binding import (
    TOLERANCE_TEMPLATES,
    ToleranceTemplate,
    ToleranceTier,
    derive_default_tolerance_tier,
    derive_tolerance_for_regime,
    get_tolerance_template,
)
from ui.backend.services.physics.urf_advisor import (
    HintSeverity,
    StabilityHint,
    derive_stability_hints,
)
from ui.backend.services.physics.writer import (
    render_momentum_transport,
    render_physical_properties,
    write_physics_dicts,
)

__all__ = [
    "MATERIAL_PRESETS",
    "MaterialPreset",
    "REGIME_PRESETS",
    "RegimePreset",
    "SOLVER_DERIVATIONS",
    "SolverDerivation",
    "SolverName",
    "HintSeverity",
    "StabilityHint",
    "TOLERANCE_TEMPLATES",
    "ToleranceTemplate",
    "ToleranceTier",
    "derive_default_tolerance_tier",
    "derive_stability_hints",
    "derive_solver",
    "derive_tolerance_for_regime",
    "get_tolerance_template",
    "get_material_preset",
    "get_regime_preset",
    "list_material_preset_ids",
    "list_regime_preset_ids",
    "render_momentum_transport",
    "render_physical_properties",
    "write_physics_dicts",
]
