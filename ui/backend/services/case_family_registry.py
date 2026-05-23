"""DEC-V61-202-SUB-M31-CYCLE4 · case_family form-helper registry.

Shared domain registry consolidating cycle 1-3's scattered constants:
  - cycle 1: `_FORM_HELPER_SKELETONS` in workbench_decide.py
  - cycle 3: `_SOLVER_TO_CASE_FAMILY_CANDIDATES` in analyzer.py
  - cycle 3 stopgap: `_CASE_FAMILIES_WITH_HELPERS` in analyzer.py
  - cycle 3 stopgap: `_case_family_helper_candidate_applies()` inline

Two consumers:
  - `ui/backend/services/workbench_decide.py` (skeleton lookup at
    rail-construction time)
  - `ui/backend/services/case_completeness/analyzer.py` (advisory
    gate at completeness-analysis time)

This module has NO project-internal imports — pure data + small
predicate functions. Safe to import from both layers without
introducing cycles.

How to add a new entry (cycle 5+):
  1. Add `(field_path, case_family)` → skeleton dict to FORM_HELPER_SKELETONS
  2. Add `solver → frozenset({case_family, ...})` to
     SOLVER_TO_CASE_FAMILY_CANDIDATES (or extend an existing solver's set)
  3. If the new solver has special turbulence/regime gating, extend
     `helper_candidate_applies()`
  4. Add tests: skeleton attached, candidate fires, gate-negative cases
"""
from __future__ import annotations

from typing import Any


# ─────────────────────────── skeletons ───────────────────────────

# Keyed by (field_path, case_family). Skeletons are intentionally
# placeholder-heavy (velocity values, type strings) — they accelerate
# dict-shape typing; engineers must visit each field post-apply to
# enter real values. Per Codex cycle-1 R1: skeletons do NOT substitute
# for domain knowledge.
FORM_HELPER_SKELETONS: dict[tuple[str, str], dict[str, Any]] = {
    # Cycle 1: interFoam VOF baseline.
    ("bc.patches", "ship_vof"): {
        "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [1.0, 0.0, 0.0]}},
        "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
        "wall":   {"patch_type": "noSlip",       "fields": {}},
    },
    # Cycle 3: simpleFoam RANS baseline (placeholder velocity 10 m/s
    # matches flat_plate_rans_sst fixture default).
    ("bc.patches", "rans_steady_incompressible"): {
        "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [10.0, 0.0, 0.0]}},
        "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
        "wall":   {"patch_type": "noSlip",       "fields": {}},
    },
    # Cycle 4: pisoFoam LES baseline (placeholder velocity 5 m/s —
    # intermediate scale between ship_vof's 1 m/s and RANS's 10 m/s,
    # signaling a different operating regime).
    ("bc.patches", "les_incompressible"): {
        "inlet":  {"patch_type": "fixedValue",   "fields": {"U": [5.0, 0.0, 0.0]}},
        "outlet": {"patch_type": "zeroGradient", "fields": {"p": "zeroGradient"}},
        "wall":   {"patch_type": "noSlip",       "fields": {}},
    },
}


# ─────────────────────────── solver → family candidates ───────────────────────────

# Maps solver name → frozenset of case_family values that COULD apply.
# The candidate set means "labeling this case as one of these families
# could unlock a Step-4 skeleton". The set is NOT a classification —
# per Codex cycle-1 R1, solver alone is not a sound discriminator
# (interFoam covers ship_vof / sloshing / dam-break / multiphase pipes;
# simpleFoam covers RANS / laminar / transitional; pisoFoam covers
# LES / DES / transient RANS / DNS). Engineers explicitly label.
SOLVER_TO_CASE_FAMILY_CANDIDATES: dict[str, frozenset[str]] = {
    "interFoam": frozenset({"ship_vof"}),
    "simpleFoam": frozenset({"rans_steady_incompressible"}),
    # Codex cycle-4 R0 P1 fix: `derive_solver(regime=LES-stub)` maps to
    # `pimpleFoam`, not `pisoFoam`. The supported workbench LES path
    # goes through pimpleFoam. pisoFoam is kept as an alias for cases
    # imported from non-workbench LES studies.
    "pimpleFoam": frozenset({"les_incompressible"}),
    "pisoFoam": frozenset({"les_incompressible"}),
}


# ─────────────────────────── derived: families with helpers ───────────────────────────

# Auto-derived from FORM_HELPER_SKELETONS keys — eliminates the
# cycle-3 stopgap duplication. When a new skeleton lands, this set
# updates automatically.
CASE_FAMILIES_WITH_HELPERS: frozenset[str] = frozenset(
    family for (_field_path, family) in FORM_HELPER_SKELETONS.keys()
)


# ─────────────────────────── per-solver candidate gate ───────────────────────────

# LES-class turbulence models. pisoFoam / pimpleFoam imports running
# these match the les_incompressible skeleton. RANS-class or laminar
# transient runs are excluded.
#
# Codex cycle-4 R0 P2 fix: this repo's audit / cfdtrust layer uses
# `LES_`-prefixed model names (LES_WALE, LES_kEqn, LES_TURBULENCE)
# while test fixtures sometimes carry the raw OpenFOAM names. Both
# conventions need to match the gate. `LES_TURBULENCE` is a sentinel
# meaning "LES regime, sub-grid model TBD" (per N3.3 LES-stub
# convention) — it counts as LES for the advisory purpose because
# the engineer is committed to LES; choice of sub-grid model is the
# downstream TODO the workbench surfaces.
_LES_TURBULENCE_MODELS: frozenset[str] = frozenset({
    # Raw OpenFOAM model names (test fixtures + future renames)
    "Smagorinsky",
    "dynamicSmagorinsky",
    "kEqn",
    "dynamicKEqn",
    "WALE",
    # LES_*-prefixed forms (cfdtrust / audit / ingest convention)
    "LES_Smagorinsky",
    "LES_dynamicSmagorinsky",
    "LES_kEqn",
    "LES_dynamicKEqn",
    "LES_WALE",
    "LES_TURBULENCE",  # generic LES sentinel
})


def helper_candidate_applies(
    solver: str | None,
    turbulence_model: str | None,
) -> bool:
    """True iff a registered helper plausibly applies for this
    (solver, turbulence_model) combination.

    Per-solver gating logic:
      - interFoam: any turbulence (VOF is geometric, not turbulent —
        ship_vof skeleton works regardless of turbulence model)
      - simpleFoam: turbulence_model != "laminar" (RANS-class only —
        Codex cycle-3 R0 P1 fix; laminar steady incompressible
        doesn't match RANS skeleton)
      - pisoFoam: turbulence_model in LES-class (cycle 4; transient
        incompressible LES; RANS/laminar pisoFoam runs excluded)
      - other solvers: no candidate (cycle 5+ extension scope)

    Codex R7 / user-ratified defeat (cycle 1) inherited contract:
    this function reads ONLY manifest values. Merged-source with
    flat-draft was attempted in cycle-1 R5/R6 and abandoned per
    R7 — the precedence ambiguity has no single solution. Both
    solver and turbulence_model live on the same manifest read here.
    """
    if not isinstance(solver, str) or not solver:
        return False
    if solver not in SOLVER_TO_CASE_FAMILY_CANDIDATES:
        return False

    normalized_turb = (
        turbulence_model.strip().lower()
        if isinstance(turbulence_model, str)
        else ""
    )

    if solver == "simpleFoam":
        # RANS gate: laminar excluded.
        if normalized_turb == "laminar":
            return False
        return True

    if solver in ("pisoFoam", "pimpleFoam"):
        # LES gate: turbulence_model must be LES-class (exact-match,
        # case-sensitive — OpenFOAM keys are case-sensitive). Both
        # raw model names (Smagorinsky) and prefixed forms (LES_WALE)
        # are accepted (Codex cycle-4 R0 P2). pimpleFoam handles the
        # workbench's `derive_solver(LES-stub)` path; pisoFoam covers
        # non-workbench imports (Codex cycle-4 R0 P1).
        if not isinstance(turbulence_model, str) or not turbulence_model:
            return False
        return turbulence_model in _LES_TURBULENCE_MODELS

    # interFoam (or any future ungated solver): no extra gate.
    return True
