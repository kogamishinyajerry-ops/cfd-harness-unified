"""Red-team probes for W3.1 CHT advisor rules R13–R14 (FALSE-POSITIVE / CRASH lens).

These tests document failure modes found by the Red Team review (Lens 1 ·
false-positive discipline) and the regrounded behavior after the W3.1 fix cycle.

Two classes of test live here:
  1. ``TestR13Regrounded`` — pins the CORRECTED behavior of R13
     COUPLED_INTERFACE_DANGLING_REF_V9_R13 against the original Red Team
     findings (the old false-positive on two consistent interfaces is now
     SILENT; the old blind spot on V94 dangling-ref shape is now FIRE).
  2. ``TestCHTRulesNoCrash`` / negative-contract pins — confirm the rules do
     not raise on malformed input and stay silent on the documented
     graceful-skip cases.

Executor mode: mocked (no OpenFOAM process invoked).
"""

from __future__ import annotations

import dataclasses
from typing import List

import pytest

from ui.backend.services.v9_advisor import (
    CoupledPatch,
    RegionSlice,
    RunArtifactSlice,
    V9_ADVISOR_RULES,
    match_advisor_patterns,
)
from ui.backend.services.v9_advisor.rules import (
    _pred_coupled_interface_dangling_ref,
    _pred_per_region_thermo_missing,
)


def _base(**kwargs) -> RunArtifactSlice:
    defaults = dict(run_id="R", case_id="c", success=True, exit_code=0)
    defaults.update(kwargs)
    return RunArtifactSlice(**defaults)


def _ids(slice_: RunArtifactSlice) -> List[str]:
    return [m.rule_id for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)]


# ---------------------------------------------------------------------------
# REGROUNDED R13 — pins the corrected COUPLED_INTERFACE_DANGLING_REF_V9_R13
# behavior against the original Red Team findings.
# ---------------------------------------------------------------------------

class TestR13Regrounded:
    def test_old_false_positive_two_consistent_interfaces_now_silent(self):
        """FIXED (was RED TEAM false-positive): two independent consistent interfaces → SILENT.

        Old R13 (family heuristic) fired here. Regrounded R13 (neighbour_region
        check) is SILENT because all neighbour_region refs resolve to regions
        in the inventory.
        """
        regions = [
            RegionSlice(
                name="fluid_hot",
                kind="fluid",
                coupled_patches=(
                    CoupledPatch(
                        "hot_to_solid",
                        "compressible::turbulentTemperatureRadCoupledMixed",
                        "solid_hot",
                    ),
                ),
            ),
            RegionSlice(
                name="solid_hot",
                kind="solid",
                coupled_patches=(
                    CoupledPatch(
                        "solid_to_hot",
                        "compressible::turbulentTemperatureRadCoupledMixed",
                        "fluid_hot",
                    ),
                ),
            ),
            RegionSlice(
                name="fluid_cold",
                kind="fluid",
                coupled_patches=(
                    CoupledPatch(
                        "cold_to_solid",
                        "compressible::turbulentTemperatureCoupledBaffleMixed",
                        "solid_cold",
                    ),
                ),
            ),
            RegionSlice(
                name="solid_cold",
                kind="solid",
                coupled_patches=(
                    CoupledPatch(
                        "solid_to_cold",
                        "compressible::turbulentTemperatureCoupledBaffleMixed",
                        "fluid_cold",
                    ),
                ),
            ),
        ]
        slice_ = _base(case_id="cht_mixed_physics_healthy", regions=regions)
        site = _pred_coupled_interface_dangling_ref(slice_)
        assert site is None, (
            "Regrounded R13 MUST be silent on two independent consistent "
            "interfaces (old false-positive now correctly suppressed)."
        )

    def test_v94_dangling_ref_shape_now_fires(self):
        """FIXED (was RED TEAM blind spot): V94 dangling-ref shape now FIRES.

        Old R13 was blind because it used a case-wide Rad/non-Rad family split
        and could not see a single-family dangling reference. Regrounded R13
        checks neighbour_region membership and correctly fires when 'domain0'
        is not in the region inventory.
        """
        regions = [
            RegionSlice(
                name="region_hot_fluid",
                kind="fluid",
                coupled_patches=(
                    CoupledPatch(
                        "region_hot_fluid_to_domain0",
                        "compressible::turbulentTemperatureCoupledBaffleMixed",
                        "domain0",  # NOT in inventory → FIRE
                    ),
                ),
            ),
            RegionSlice(
                name="region_solid",
                kind="solid",
                coupled_patches=(
                    CoupledPatch(
                        "region_solid_to_hot",
                        "compressible::turbulentTemperatureCoupledBaffleMixed",
                        "region_hot_fluid",  # present → OK
                    ),
                ),
            ),
        ]
        slice_ = _base(case_id="cht_v94_dangling_ref", regions=regions)
        site = _pred_coupled_interface_dangling_ref(slice_)
        assert site is not None, (
            "Regrounded R13 MUST fire on V94 dangling-ref shape."
        )
        assert "dangling_coupled_ref" in site.matched_at
        assert "domain0" in site.matched_at


# ---------------------------------------------------------------------------
# Crash safety — predicates must not raise (or be caught by matcher)
# ---------------------------------------------------------------------------

class TestCHTRulesNoCrash:
    def test_all_none_payload_region_does_not_crash_matcher(self):
        r = RegionSlice(name="x", kind=None)  # every optional defaults None
        slice_ = _base(regions=[r])
        # Must not raise.
        ids = _ids(slice_)
        # R14 legitimately fires (both thermo fields None); R13 silent (no coupled patches).
        assert "PER_REGION_THERMO_MISSING_V9_R14" in ids
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids

    def test_malformed_coupling_type_none_does_not_crash_regrounded_r13(self):
        """Regrounded R13 does NOT use coupling_type at all — it only reads
        neighbour_region. A malformed slice with coupling_type=None is harmless
        to the regrounded predicate. The matcher stays silent because no
        dangling neighbour_region is present."""
        bad = RegionSlice(
            name="f",
            kind="fluid",
            coupled_patches=(CoupledPatch("p", None, "x"),),  # type: ignore[arg-type]
        )
        slice_ = _base(regions=[bad])
        # Regrounded predicate does NOT raise (it ignores coupling_type):
        site = _pred_coupled_interface_dangling_ref(slice_)
        # neighbour_region="x" but "x" is not in the inventory ["f"] → FIRE.
        # This is correct: "x" is a dangling reference.
        assert site is not None
        assert "dangling_coupled_ref" in site.matched_at
        # Matcher also handles it cleanly (no crash):
        ids = _ids(slice_)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" in ids

    def test_regions_none_all_rules_silent(self):
        slice_ = _base()  # regions defaults None
        assert slice_.regions is None
        ids = _ids(slice_)
        for rid in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
        ):
            assert rid not in ids

    def test_empty_regions_all_rules_silent(self):
        slice_ = _base(regions=[])
        ids = _ids(slice_)
        for rid in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
        ):
            assert rid not in ids
