"""P3 W3.2a (DEC-V61-223) — case_family_registry CHT registration tests.

Per DEC-V61-217 charter row W3.2 (d): register the
``cht_steady_laminar_multi_region`` family, closing the
DEC-V61-202-SUB-M31-CYCLE4 deferred-target commitment. Lives in ``tests/p3``
(clean conftest) — the ``ui/backend/tests`` suite is blocked by an unrelated
``trimesh`` import in its conftest; the same registry assertions are also driven
there once trimesh is available.
"""
from __future__ import annotations

from ui.backend.services.case_family_registry import (
    CASE_FAMILIES_WITH_HELPERS,
    FORM_HELPER_SKELETONS,
    SOLVER_TO_CASE_FAMILY_CANDIDATES,
    helper_candidate_applies,
)

FAMILY = "cht_steady_laminar_multi_region"


def test_cht_steady_family_registered() -> None:
    assert FAMILY in CASE_FAMILIES_WITH_HELPERS
    assert ("bc.patches", FAMILY) in FORM_HELPER_SKELETONS
    assert SOLVER_TO_CASE_FAMILY_CANDIDATES["chtMultiRegionSimpleFoam"] == frozenset({FAMILY})


def test_skeleton_is_three_patch_with_coupled_baffle_wall() -> None:
    """3-patch inlet/outlet/wall convention; the wall is the CHT-specific
    coupled-baffle interface placeholder (NOT a plain noSlip)."""
    skel = FORM_HELPER_SKELETONS[("bc.patches", FAMILY)]
    assert set(skel.keys()) == {"inlet", "outlet", "wall"}
    assert skel["wall"]["patch_type"] == "compressible::turbulentTemperatureCoupledBaffleMixed"


def test_helper_applies_for_laminar_target_regime() -> None:
    """CHT gate MIRRORS simpleFoam: laminar IS the target regime (charter Q4)."""
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "laminar") is True
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "LAMINAR") is True
    # solid regions carry no turbulence model → unspecified still applies
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", None) is True
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "") is True


def test_helper_rejects_turbulent_cht_deferred() -> None:
    """Turbulent CHT is deferred (charter Q4) — only the steady-laminar family
    is registered, so an explicit turbulence model does NOT match."""
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "kOmegaSST") is False
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "kEpsilon") is False


def test_transient_cht_stays_unregistered() -> None:
    """Transient chtMultiRegionFoam is NOT registered (charter Q4: steady first)."""
    assert "chtMultiRegionFoam" not in SOLVER_TO_CASE_FAMILY_CANDIDATES
    assert helper_candidate_applies("chtMultiRegionFoam", "laminar") is False
    assert helper_candidate_applies("chtMultiRegionFoam", None) is False


def test_candidate_family_has_a_registered_skeleton() -> None:
    """The new candidate must point to a family that actually has a skeleton."""
    candidates = set()
    for fam_set in SOLVER_TO_CASE_FAMILY_CANDIDATES.values():
        candidates.update(fam_set)
    assert candidates <= CASE_FAMILIES_WITH_HELPERS
