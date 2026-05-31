"""P3 W3.1 · CHT advisor rules R13–R14 tests (R15+R16 DEFERRED).

Tests the two shipped V9 advisor rules for conjugate heat transfer (CHT)
topology analysis:
    R13 COUPLED_INTERFACE_DANGLING_REF_V9_R13
    R14 PER_REGION_THERMO_MISSING_V9_R14

R15 CONDUCTION_DOMINANCE and R16 FACE_ZONE_LOSS are DEFERRED per Codex R1
(DEC-V61-222): the frozen W3.0.6 RegionSlice schema carries DECLARED topology
(kind from regionProperties, shm_snapshot_ref distinguishing sHM-vs-extruded)
but NOT produced-mesh presence. R16's shm_snapshot_ref=None means "extruded,
not sHM'd" for case_002b's 6 solids (healthy), NOT "face-zone lost"
→ false-positive. R15's kind comes from regionProperties so a mesh-lost fluid
still reads kind='fluid' → R15 cannot fire faithfully on V92. Faithful R15/R16
require a future W3.2 per-region mesh-presence field.

Evidence: synthetic V-row-replay fixtures derived from the following
industrial case death-chains per the P3 W3.1 task specification:
    V94 — case_011 v1 0.orig BC files referencing non-existent coupled patches
    V14 — chtMultiRegionSimpleFoam crash mid-Time=1, missing-field sentinel ±1e+300
    V92 — region_solid 0 cells, absent from final polyMesh

Executor mode: mocked (no OpenFOAM process invoked; all slices are
synthetic Python objects — MOCKED RUN, not a real solver run).

=== FOUR-QUESTION GATE (per rule, per DEC-V61-217 W3.1 contract) ===

R13 COUPLED_INTERFACE_DANGLING_REF_V9_R13:
    LLM offline: YES — predicate is a pure function over CoupledPatch.neighbour_region
                 vs the region-name inventory set; no LLM call, no IO, no subprocess.
    Artifacts canonical: YES — commentary + provenance written to JSON SSOT
                         v9_advisor_rules.json (RS#37 enforced by contract test).
    TrustGate-explainable: YES — fires only when a cp.neighbour_region is NOT in the
                           assembled region-name set; matched_at names the exact
                           dangling path (region.patch->missing_neighbour).
    Advisory-only: YES — severity 'warn'; does not modify TrustGate verdict logic
                   or any tolerance threshold. Advisor-not-driver (Law-3).

R14 PER_REGION_THERMO_MISSING_V9_R14:
    LLM offline: YES — pure function over RegionSlice.thermo_type + .thermo_snapshot_ref.
    Artifacts canonical: YES — provenance non-empty (RS#32 enforced at import).
    TrustGate-explainable: YES — fires when BOTH thermo payload fields are None;
                           matched_at names the region and reason 'thermo_missing'.
    Advisory-only: YES — severity 'warn'; no gate verdict change.
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
from ui.backend.services.v9_advisor.rules import _load_corpus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_for(slice_: RunArtifactSlice) -> List[dict]:
    """Run the full ruleset and return dicts of MatchedCommentary."""
    return [dataclasses.asdict(m) for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)]


def _rule_ids(matches: List[dict]) -> List[str]:
    return [m["rule_id"] for m in matches]


def _make_base_slice(**kwargs) -> RunArtifactSlice:
    """Minimal healthy-baseline slice with no CHT regions."""
    defaults = dict(
        run_id="R-BASE",
        case_id="test",
        success=True,
        exit_code=0,
    )
    defaults.update(kwargs)
    return RunArtifactSlice(**defaults)


def _region(
    name: str,
    kind,
    thermo_type=None,
    thermo_snapshot_ref=None,
    coupled_patches=None,
    shm_snapshot_ref=None,
) -> RegionSlice:
    return RegionSlice(
        name=name,
        kind=kind,
        thermo_type=thermo_type,
        thermo_snapshot_ref=thermo_snapshot_ref,
        coupled_patches=coupled_patches,
        shm_snapshot_ref=shm_snapshot_ref,
    )


# ---------------------------------------------------------------------------
# Import / join integrity
# ---------------------------------------------------------------------------

def test_load_corpus_still_builds():
    """_load_corpus() must build cleanly with all 14 rules (join integrity).

    W3.1 shipped R13 + R14; R15 + R16 deferred (Codex R1, DEC-V61-222).
    """
    version, rules = _load_corpus()
    ids = {r.id for r in rules}
    for expected_id in (
        "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
        "PER_REGION_THERMO_MISSING_V9_R14",
    ):
        assert expected_id in ids, f"Missing rule id after _load_corpus(): {expected_id}"
    for deferred_id in (
        "CONDUCTION_DOMINANCE_V9_R15",
        "FACE_ZONE_LOSS_V9_R16",
    ):
        assert deferred_id not in ids, (
            f"Deferred rule {deferred_id} must NOT appear in the shipped corpus "
            f"(Codex R1 deferral, DEC-V61-222)"
        )
    assert len(rules) == 14


def test_all_new_rules_have_non_empty_provenance():
    """RS#32: provenance must be non-empty for all shipped CHT rules (R13 + R14)."""
    for rule in V9_ADVISOR_RULES:
        if rule.id in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
        ):
            assert rule.provenance, f"RS#32 violation: {rule.id} has empty provenance"
            assert len(rule.provenance) > 0


# ---------------------------------------------------------------------------
# R13 COUPLED_INTERFACE_DANGLING_REF_V9_R13
# ---------------------------------------------------------------------------

class TestR13CoupledInterfaceDanglingRef:
    """Synthetic V-row replay: V94 dangling coupled-interface reference."""

    def test_fires_on_dangling_neighbour_region(self):
        """V94 replay: coupled_patch.neighbour_region='domain0' not in region inventory."""
        slice_ = _make_base_slice(
            run_id="R-V94-R13",
            case_id="cht_v94_dangling_ref",
            regions=[
                _region(
                    name="region_hot_fluid",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap_hot",
                    shm_snapshot_ref="shm_hot",
                    coupled_patches=(
                        CoupledPatch(
                            patch_name="region_hot_fluid_to_domain0",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region="domain0",  # NOT in region inventory → FIRE
                        ),
                        CoupledPatch(
                            patch_name="region_hot_fluid_to_region_solid",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region="region_solid",  # present → OK
                        ),
                    ),
                ),
                _region(
                    name="region_solid",
                    kind="solid",
                    thermo_type="heSolidThermo",
                    thermo_snapshot_ref="snap_solid",
                    shm_snapshot_ref="shm_solid",
                    coupled_patches=(
                        CoupledPatch(
                            patch_name="region_solid_to_hot",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region="region_hot_fluid",  # present → OK
                        ),
                    ),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" in ids
        r13 = next(m for m in matches if m["rule_id"] == "COUPLED_INTERFACE_DANGLING_REF_V9_R13")
        assert "dangling_coupled_ref" in r13["matched_at"]
        assert "region_hot_fluid" in r13["matched_at"]
        assert "domain0" in r13["matched_at"]
        assert r13["severity"] == "warn"

    def test_silent_on_all_refs_resolve_healthy_case(self):
        """Healthy: every coupled_patch.neighbour_region is present in the inventory."""
        slice_ = _make_base_slice(
            run_id="R-HEALTHY-REFS",
            case_id="case_011_healthy_refs",
            regions=[
                _region(
                    name="fluid_hot",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap_fh",
                    shm_snapshot_ref="shm_fh",
                    coupled_patches=(
                        CoupledPatch(
                            patch_name="hot_to_solid",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region="solid",  # present in inventory → silent
                        ),
                    ),
                ),
                _region(
                    name="solid",
                    kind="solid",
                    thermo_type="heSolidThermo",
                    thermo_snapshot_ref="snap_s",
                    shm_snapshot_ref="shm_s",
                    coupled_patches=(
                        CoupledPatch(
                            patch_name="solid_to_hot",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region="fluid_hot",  # present in inventory → silent
                        ),
                    ),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids

    def test_silent_on_two_independent_consistent_interfaces_old_false_positive(self):
        """REGROUNDED (was FALSE POSITIVE): two independent interfaces each with
        internally consistent refs → ALL refs resolve → SILENT.

        This was the false-positive case of the old WALL_COUPLING_MISMATCH predicate
        (which fired incorrectly here because it did a case-wide 'Rad' substring split).
        The regrounded predicate checks neighbour_region resolution — since every
        neighbour_region (solidA, fluidA, solidB, fluidB) IS in the inventory,
        R13 MUST NOT fire.
        """
        slice_ = _make_base_slice(
            run_id="R-TWO-CONSISTENT",
            case_id="cht_two_consistent_interfaces",
            regions=[
                _region("fluidA", "fluid", "heRhoThermo", "sfa", coupled_patches=(
                    CoupledPatch("fa_to_sa",
                                 "compressible::turbulentTemperatureRadCoupledMixed",
                                 "solidA"),), shm_snapshot_ref="shmfa"),
                _region("solidA", "solid", "heSolidThermo", "ssa", coupled_patches=(
                    CoupledPatch("sa_to_fa",
                                 "compressible::turbulentTemperatureRadCoupledMixed",
                                 "fluidA"),), shm_snapshot_ref="shmsa"),
                _region("fluidB", "fluid", "heRhoThermo", "sfb", coupled_patches=(
                    CoupledPatch("fb_to_sb",
                                 "compressible::turbulentTemperatureCoupledBaffleMixed",
                                 "solidB"),), shm_snapshot_ref="shmfb"),
                _region("solidB", "solid", "heSolidThermo", "ssb", coupled_patches=(
                    CoupledPatch("sb_to_fb",
                                 "compressible::turbulentTemperatureCoupledBaffleMixed",
                                 "fluidB"),), shm_snapshot_ref="shmsb"),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids, (
            "Regrounded R13 MUST NOT fire on two independent consistent interfaces — "
            "all neighbour_region refs resolve; this was the old false positive."
        )

    def test_silent_on_neighbour_region_none(self):
        """Graceful skip: cp.neighbour_region=None — neighbour not extracted; cannot judge."""
        slice_ = _make_base_slice(
            run_id="R-NR-NONE",
            case_id="cht_neighbour_none",
            regions=[
                _region(
                    name="fluid",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap",
                    shm_snapshot_ref="shm",
                    coupled_patches=(
                        CoupledPatch(
                            patch_name="f_to_s",
                            coupling_type="compressible::turbulentTemperatureCoupledBaffleMixed",
                            neighbour_region=None,  # not extracted — cannot judge
                        ),
                    ),
                ),
                _region(
                    name="solid",
                    kind="solid",
                    thermo_type="heSolidThermo",
                    thermo_snapshot_ref="snaps",
                    shm_snapshot_ref="shms",
                    coupled_patches=(),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids

    def test_silent_on_legacy_regions_none(self):
        """Graceful skip: regions=None is the legacy/scalar slice sentinel."""
        slice_ = _make_base_slice(run_id="R-LEG", case_id="legacy")
        assert slice_.regions is None
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids

    def test_silent_on_empty_regions_list(self):
        """Graceful skip: regions=[] — list present but no regions surfaced."""
        slice_ = _make_base_slice(
            run_id="R-EMPTY", case_id="cht_empty_regions", regions=[]
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids

    def test_silent_when_coupled_patches_not_extracted(self):
        """Graceful skip: coupled_patches=None — coupling not extracted."""
        slice_ = _make_base_slice(
            run_id="R-NO-CP",
            case_id="cht_no_coupling_data",
            regions=[
                _region(
                    name="fluid",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap",
                    shm_snapshot_ref="shm",
                    coupled_patches=None,  # not extracted
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids


# ---------------------------------------------------------------------------
# R14 PER_REGION_THERMO_MISSING_V9_R14
# ---------------------------------------------------------------------------

class TestR14PerRegionThermoMissing:
    """Synthetic V-row replay: V14 (solver crash + missing payload) + V92 (0-cell region)."""

    def test_fires_when_both_thermo_fields_absent(self):
        """V14/V92 replay: a region has thermo_type=None AND thermo_snapshot_ref=None."""
        slice_ = _make_base_slice(
            run_id="R-V14-R14",
            case_id="cht_missing_thermo",
            regions=[
                _region(
                    name="fluid_hot",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap_fluid",
                    shm_snapshot_ref="shm_fluid",
                    coupled_patches=(),
                ),
                _region(
                    name="solid_plate",
                    kind="solid",
                    thermo_type=None,
                    thermo_snapshot_ref=None,
                    shm_snapshot_ref="shm_solid",
                    coupled_patches=(),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" in ids
        r14 = next(m for m in matches if m["rule_id"] == "PER_REGION_THERMO_MISSING_V9_R14")
        assert r14["matched_at"] == "region:solid_plate:thermo_missing"
        assert r14["severity"] == "warn"

    def test_silent_when_thermo_type_present(self):
        """Healthy: thermo_type present means payload extracted; ref being None is OK."""
        slice_ = _make_base_slice(
            run_id="R-THERMO-HEALTHY",
            case_id="cht_healthy_thermo",
            regions=[
                _region(
                    name="fluid",
                    kind="fluid",
                    thermo_type="heRhoThermo",  # present — payload extracted
                    thermo_snapshot_ref=None,   # ref absent — decoupling artifact, NOT missing
                    shm_snapshot_ref="shm",
                    coupled_patches=(),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" not in ids

    def test_silent_on_fully_populated_cht_case(self):
        """Healthy: all regions have thermo_type populated (case_002b/case_011 analog)."""
        slice_ = _make_base_slice(
            run_id="R-FULL-CHT",
            case_id="cht_healthy_full",
            regions=[
                _region(
                    name="fluid",
                    kind="fluid",
                    thermo_type="heRhoThermo",
                    thermo_snapshot_ref="snap_f",
                    shm_snapshot_ref="shm_f",
                    coupled_patches=(),
                ),
                _region(
                    name="solid",
                    kind="solid",
                    thermo_type="heSolidThermo",
                    thermo_snapshot_ref="snap_s",
                    shm_snapshot_ref="shm_s",
                    coupled_patches=(),
                ),
            ],
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" not in ids

    def test_silent_on_legacy_regions_none(self):
        """Graceful skip: regions=None is the legacy/scalar slice sentinel."""
        slice_ = _make_base_slice(run_id="R-LEG2", case_id="legacy")
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" not in ids

    def test_silent_on_empty_regions_list(self):
        """Graceful skip: regions=[] — no regions to check."""
        slice_ = _make_base_slice(
            run_id="R-EMPTY2", case_id="cht_empty", regions=[]
        )
        matches = _matches_for(slice_)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" not in ids


# ---------------------------------------------------------------------------
# RED-TEAM PINS (regrounded) · R13 COUPLED_INTERFACE_DANGLING_REF_V9_R13
# ---------------------------------------------------------------------------
#
# The old Red Team found that WALL_COUPLING_MISMATCH_V9_R13 false-fired on
# healthy mixed-physics cases (two independent consistent interfaces) and was
# blind to its own cited V94 death-chain (single-family dangling ref).
#
# R13 is now REGROUNDED as COUPLED_INTERFACE_DANGLING_REF_V9_R13. These tests
# pin the CORRECTED behavior:
#   1. The old false-positive (two independent consistent interfaces) is now SILENT.
#   2. The old "blind spot" (V94 shape: single-family with a dangling ref) now FIRES.

class TestR13RedTeamRegrounded:
    """Pins regrounded R13 behavior against the original Red Team findings."""

    def test_old_false_positive_now_silent(self):
        """FIXED: two independent consistent interfaces → SILENT (was FALSE POSITIVE).

        Old R13 fired here because Rad and non-Rad both appeared case-wide.
        Regrounded R13 checks neighbour_region resolution: all refs resolve → SILENT.
        """
        slice_ = _make_base_slice(
            run_id="R-RT-R13-FP-FIXED",
            case_id="cht_two_consistent_interfaces",
            regions=[
                _region("fluidA", "fluid", "heRhoThermo", "sfa", coupled_patches=(
                    CoupledPatch("fa_to_sa",
                                 "compressible::turbulentTemperatureRadCoupledMixed",
                                 "solidA"),), shm_snapshot_ref="shmfa"),
                _region("solidA", "solid", "heSolidThermo", "ssa", coupled_patches=(
                    CoupledPatch("sa_to_fa",
                                 "compressible::turbulentTemperatureRadCoupledMixed",
                                 "fluidA"),), shm_snapshot_ref="shmsa"),
                _region("fluidB", "fluid", "heRhoThermo", "sfb", coupled_patches=(
                    CoupledPatch("fb_to_sb",
                                 "compressible::turbulentTemperatureCoupledBaffleMixed",
                                 "solidB"),), shm_snapshot_ref="shmfb"),
                _region("solidB", "solid", "heSolidThermo", "ssb", coupled_patches=(
                    CoupledPatch("sb_to_fb",
                                 "compressible::turbulentTemperatureCoupledBaffleMixed",
                                 "fluidB"),), shm_snapshot_ref="shmsb"),
            ],
        )
        ids = _rule_ids(_matches_for(slice_))
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" not in ids, (
            "Regrounded R13 MUST be silent on two independent consistent interfaces "
            "(old false-positive now correctly suppressed)."
        )

    def test_v94_death_chain_shape_now_fires(self):
        """FIXED: V94 dangling-ref shape now FIRES (was blind spot in old R13).

        V94: region_hot_fluid BC references 'domain0' which does NOT exist as a
        region in the inventory. Old R13 (family heuristic) was blind to this.
        Regrounded R13 (neighbour_region check) correctly fires.
        """
        slice_ = _make_base_slice(
            run_id="R-RT-R13-V94-FIXED",
            case_id="cht_v94_dangling_patch",
            regions=[
                _region("region_hot_fluid", "fluid", "heRhoThermo", "shf",
                        coupled_patches=(
                            CoupledPatch("region_hot_fluid_to_domain0",
                                         "compressible::turbulentTemperatureCoupledBaffleMixed",
                                         "domain0"),),  # NOT in inventory → FIRE
                        shm_snapshot_ref="shm_hot"),
                _region("region_solid", "solid", "heSolidThermo", "ss",
                        coupled_patches=(
                            CoupledPatch("region_solid_to_hot",
                                         "compressible::turbulentTemperatureCoupledBaffleMixed",
                                         "region_hot_fluid"),),  # present → OK
                        shm_snapshot_ref="shm_solid"),
            ],
        )
        ids = _rule_ids(_matches_for(slice_))
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" in ids, (
            "Regrounded R13 MUST fire on V94 dangling-ref shape "
            "(neighbour_region='domain0' not in inventory)."
        )


# ---------------------------------------------------------------------------
# Existing R1–R12 non-regression
# ---------------------------------------------------------------------------

def test_existing_rules_unaffected_by_cht_regions_none():
    """Legacy slices (regions=None) must still trigger R1-R12 normally."""
    # Trigger R2 (max iters reached) on a legacy slice — must still fire.
    from ui.backend.services.v9_advisor import ConvergenceStats
    slice_ = RunArtifactSlice(
        run_id="R-LEGACY-R2",
        case_id="lid_driven",
        success=True,
        exit_code=0,
        convergence_stats=ConvergenceStats(
            final_iter=5000,
            max_iters_reached=True,
            converged=False,
            elapsed_seconds=60.0,
        ),
    )
    assert slice_.regions is None
    matches = _matches_for(slice_)
    ids = _rule_ids(matches)
    assert "MAX_ITERS_REACHED_V9_R2" in ids
    # None of the CHT rules (R13–R14 shipped) should fire on a legacy slice
    for r_id in ("COUPLED_INTERFACE_DANGLING_REF_V9_R13", "PER_REGION_THERMO_MISSING_V9_R14"):
        assert r_id not in ids, f"{r_id} must not fire on legacy regions=None slice"
