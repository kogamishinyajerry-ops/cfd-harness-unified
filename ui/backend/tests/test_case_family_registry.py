"""DEC-V61-202-SUB-M31-CYCLE4 · case_family_registry contract tests.

Pins the shared registry contract so future cycle additions can't
silently drift from cycle-1/3/4 invariants:
  - All registered skeletons carry inlet/outlet/wall keys
  - CASE_FAMILIES_WITH_HELPERS auto-derives correctly from
    FORM_HELPER_SKELETONS
  - Per-solver gate behaves as documented
"""
from __future__ import annotations

import pytest

from ui.backend.services.case_family_registry import (
    CASE_FAMILIES_WITH_HELPERS,
    FORM_HELPER_SKELETONS,
    SOLVER_TO_CASE_FAMILY_CANDIDATES,
    helper_candidate_applies,
)


def test_registry_has_at_least_3_skeletons():
    """Cycle 4 adds the 3rd skeleton; the extraction trigger fires
    at this threshold. Pinning the count guards against accidental
    deletion. Cycle 5+ can raise the floor as new families land.
    """
    # P3 W3.2a (DEC-V61-223): floor raised 3 → 4 with the
    # cht_steady_laminar_multi_region skeleton.
    assert len(FORM_HELPER_SKELETONS) >= 4


def test_registered_families_match_cycle_1_3_4_set():
    """Pin the exact set of registered case_family values for
    cycle 1-4. Cycle 5+ updates this assertion as new families land.
    """
    registered_families = {
        family for (_field_path, family) in FORM_HELPER_SKELETONS.keys()
    }
    assert registered_families == {
        "ship_vof",
        "rans_steady_incompressible",
        "les_transient_incompressible",
        # P3 W3.2a (DEC-V61-223): steady-laminar CHT multi-region.
        "cht_steady_laminar_multi_region",
    }


def test_case_families_with_helpers_auto_derives_from_skeletons():
    """The cycle-3 stopgap (`_CASE_FAMILIES_WITH_HELPERS` hand-mirrored
    the family list) is replaced in cycle 4 by auto-derivation. This
    test pins the derivation so a new skeleton entry can't get
    forgotten in the CASE_FAMILIES_WITH_HELPERS set.
    """
    expected = frozenset(
        family for (_fp, family) in FORM_HELPER_SKELETONS.keys()
    )
    assert CASE_FAMILIES_WITH_HELPERS == expected


def test_all_skeletons_share_3_patch_inlet_outlet_wall_shape():
    """Cycle 1's structural convention: each skeleton is 3 patches
    keyed inlet/outlet/wall. Cycle 5+ may extend (e.g. ground/sky
    for atmospheric BL), but the cycle 1-4 entries must hold.
    """
    for key, skeleton in FORM_HELPER_SKELETONS.items():
        assert set(skeleton.keys()) == {"inlet", "outlet", "wall"}, (
            f"Skeleton {key} drifted from canonical 3-patch shape"
        )


@pytest.mark.parametrize(
    "solver,turbulence,expected",
    [
        # interFoam: any turbulence flows through (VOF is geometric)
        ("interFoam", "laminar", True),
        ("interFoam", "kOmegaSST", True),
        ("interFoam", None, True),
        ("interFoam", "", True),
        # simpleFoam: gated on non-laminar turbulence
        ("simpleFoam", "kOmegaSST", True),
        ("simpleFoam", "kEpsilon", True),
        ("simpleFoam", "SpalartAllmaras", True),
        ("simpleFoam", "laminar", False),
        ("simpleFoam", "LAMINAR", False),  # case-insensitive
        # pisoFoam: gated on LES-class turbulence (raw + prefixed forms)
        ("pisoFoam", "Smagorinsky", True),
        ("pisoFoam", "dynamicSmagorinsky", True),
        ("pisoFoam", "kEqn", True),
        ("pisoFoam", "dynamicKEqn", True),
        ("pisoFoam", "WALE", True),
        ("pisoFoam", "kOmegaSST", False),  # RANS, not LES
        ("pisoFoam", "laminar", False),    # DNS, not LES
        ("pisoFoam", None, False),
        ("pisoFoam", "", False),
        # pimpleFoam: same LES gate (Codex cycle-4 R0 P1 — pimpleFoam
        # is the supported workbench LES solver per derive_solver)
        ("pimpleFoam", "Smagorinsky", True),
        ("pimpleFoam", "WALE", True),
        ("pimpleFoam", "kOmegaSST", False),  # transient RANS, not LES
        ("pimpleFoam", "laminar", False),    # transient laminar
        ("pimpleFoam", None, False),
        # Codex cycle-4 R0 P2: LES_*-prefixed model names also count
        ("pimpleFoam", "LES_WALE", True),
        ("pimpleFoam", "LES_kEqn", True),
        ("pimpleFoam", "LES_TURBULENCE", True),  # generic LES sentinel
        ("pimpleFoam", "LES_Smagorinsky", True),
        ("pisoFoam", "LES_WALE", True),
        ("pisoFoam", "LES_TURBULENCE", True),
        # Codex cycle-4 R1 P2: bare "LES" used in dogfood / frontend
        # (per usePhysicsState.ts::tm.includes("les") convention)
        ("pimpleFoam", "LES", True),
        ("pisoFoam", "LES", True),
        # Codex cycle-4 R1 P2: case-insensitive "les" substring match
        # for lowercase variants from external tooling
        ("pimpleFoam", "les", True),
        ("pimpleFoam", "les_wale", True),
        ("pisoFoam", "LesDynamic", True),
        # P3 W3.2a (DEC-V61-223): steady CHT gate — MIRROR of simpleFoam
        # (laminar IS the target regime; turbulent CHT deferred per charter Q4).
        ("chtMultiRegionSimpleFoam", "laminar", True),
        ("chtMultiRegionSimpleFoam", "LAMINAR", True),  # case-insensitive
        ("chtMultiRegionSimpleFoam", None, True),       # solid regions: no turb model
        ("chtMultiRegionSimpleFoam", "", True),
        ("chtMultiRegionSimpleFoam", "kOmegaSST", False),  # turbulent CHT deferred
        # Unregistered solvers: never fire
        ("rhoSimpleFoam", "kOmegaSST", False),
        # Transient chtMultiRegionFoam stays UNregistered (charter Q4 deferral) —
        # only the steady SimpleFoam variant is registered by W3.2a.
        ("chtMultiRegionFoam", None, False),
        ("chtMultiRegionFoam", "laminar", False),
        ("buoyantPimpleFoam", "LES_WALE", False),  # not in registry yet
        # Edge cases
        (None, "kOmegaSST", False),
        ("", "Smagorinsky", False),
    ],
)
def test_helper_candidate_applies_matrix(solver, turbulence, expected):
    """Per-solver gate behavior matrix. Cycle 5+ adds rows as new
    solvers land in the registry.
    """
    assert helper_candidate_applies(solver, turbulence) is expected


def test_solver_to_case_family_candidates_covers_all_registered_families():
    """Every solver in the candidate map must point to families that
    exist in the skeleton registry. Otherwise the advisory could
    suggest a family that produces no skeleton (cycle-3 R0 P2 contract).
    """
    candidate_families = set()
    for family_set in SOLVER_TO_CASE_FAMILY_CANDIDATES.values():
        candidate_families.update(family_set)
    assert candidate_families <= CASE_FAMILIES_WITH_HELPERS, (
        f"Candidate families {candidate_families - CASE_FAMILIES_WITH_HELPERS} "
        "have no skeleton registered — drift detected"
    )
