"""P3 W3.0.6 · RunArtifactSlice multi-region extension contract tests.

DEC-V61-215: CoupledPatch + RegionSlice + RunArtifactSlice.regions field.
stdlib-only; trimesh-free (tests/p3/ to dodge the trimesh conftest).

Test map
--------
A  Backward-compat: RunArtifactSlice with no regions arg → regions is None.
   Legacy-shaped construction (run_id/case_id/success/exit_code only) works.

B  case_002b-shaped: 7-region slice (1 fluid + 6 Ti solid extrusions)
   with thermo_type + coupled_patches + refs populated.
   dataclasses.asdict round-trips to plain dicts/lists; reconstruction
   preserves every field.

C  case_011-shaped: 3-region slice (2 fluids + 1 aluminum solid) round-trip.

D  Presence-vs-payload: regions=None vs regions=[] vs regions=[RegionSlice
   with all payload None] are three DISTINCT, round-trip-stable states.

E  Frozen: attempting to set an attribute on RegionSlice / CoupledPatch /
   RunArtifactSlice raises FrozenInstanceError.

F  coupled_patches tuple: a RegionSlice with multiple CoupledPatch entries
   round-trips the tuple losslessly; coupling_type values from real vocab.

G  Byte-reproducibility (RS#36): adding regions to a slice does NOT change
   audit sidecar matched.json bytes — confirmed by asserting that the
   serialize path reads manifest["commentary"] only and never touches
   RunArtifactSlice.regions.
"""

from __future__ import annotations

import dataclasses
from dataclasses import FrozenInstanceError
from typing import Any, Dict, List, Optional

import pytest

from ui.backend.services.v9_advisor.pattern_matcher import (
    CoupledPatch,
    RegionSlice,
    RunArtifactSlice,
)

# ---------------------------------------------------------------------------
# Known coupling-type vocabulary (from W3.0.6 spec)
# ---------------------------------------------------------------------------
COUPLED_BAFFLE_MIXED = "compressible::turbulentTemperatureCoupledBaffleMixed"
COUPLED_RAD_MIXED = "compressible::turbulentTemperatureRadCoupledMixed"
HUMIDITY_COUPLED = "humidityTemperatureCoupledMixed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reconstruct_slice(d: Dict[str, Any]) -> RunArtifactSlice:
    """Reconstruct a RunArtifactSlice from the plain dict produced by
    dataclasses.asdict. Mirrors the _hydrate_slice pattern in
    test_v9_cross_language_parity.py — reconstructs CoupledPatch and
    RegionSlice instances from nested dicts/lists, preserving None vs []
    vs populated distinctions.
    """
    regions = None
    if d.get("regions") is not None:
        hydrated: List[RegionSlice] = []
        for r in d["regions"]:
            coupled_patches = None
            if r.get("coupled_patches") is not None:
                coupled_patches = tuple(
                    CoupledPatch(**cp) for cp in r["coupled_patches"]
                )
            hydrated.append(
                RegionSlice(
                    name=r["name"],
                    kind=r["kind"],
                    thermo_type=r.get("thermo_type"),
                    coupled_patches=coupled_patches,
                    shm_snapshot_ref=r.get("shm_snapshot_ref"),
                    thermo_snapshot_ref=r.get("thermo_snapshot_ref"),
                )
            )
        regions = hydrated
    return RunArtifactSlice(
        run_id=d["run_id"],
        case_id=d["case_id"],
        success=d["success"],
        exit_code=d["exit_code"],
        residuals=d.get("residuals"),
        forces=d.get("forces"),
        convergence_stats=d.get("convergence_stats"),
        gold_delta=d.get("gold_delta"),
        developed_region_gold_delta=d.get("developed_region_gold_delta"),
        integrated_drag_pct=d.get("integrated_drag_pct"),
        reference_comparison_band_summary=d.get("reference_comparison_band_summary"),
        regions=regions,
    )


# ---------------------------------------------------------------------------
# A · Backward-compat
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_no_regions_arg_gives_none(self):
        """Additive-non-breaking: omitting regions → regions is None."""
        s = RunArtifactSlice(
            run_id="R-LEGACY-1",
            case_id="duct_flow",
            success=True,
            exit_code=0,
        )
        assert s.regions is None

    def test_legacy_construction_minimal(self):
        """Legacy sites that pass only 4 positional/keyword args still work."""
        s = RunArtifactSlice(
            run_id="R-LEGACY-2",
            case_id="lid_driven",
            success=False,
            exit_code=1,
        )
        assert s.run_id == "R-LEGACY-2"
        assert s.regions is None

    def test_legacy_construction_all_pre_w306_fields(self):
        """Sites using all pre-W3.0.6 fields still compile unchanged."""
        s = RunArtifactSlice(
            run_id="R-LEGACY-3",
            case_id="flat_plate",
            success=True,
            exit_code=0,
            residuals={"p": [1e-2, 1e-3]},
            forces=None,
            convergence_stats=None,
            gold_delta=None,
            developed_region_gold_delta=None,
            integrated_drag_pct=None,
            reference_comparison_band_summary=None,
        )
        assert s.regions is None


# ---------------------------------------------------------------------------
# B · case_002b-shaped: 7-region round-trip
# ---------------------------------------------------------------------------

def _make_case_002b_slice() -> RunArtifactSlice:
    """Build a 7-region CHT slice shaped like case_002b:
    1 fluid + 6 Ti solid extrusions, radiation coupling.
    """
    fluid_region = RegionSlice(
        name="fluid",
        kind="fluid",
        thermo_type="heRhoThermo",
        coupled_patches=tuple(
            CoupledPatch(
                patch_name=f"fluid_to_heater_{i}",
                coupling_type=COUPLED_RAD_MIXED,
                neighbour_region=f"heater_{i}",
            )
            for i in range(6)
        ),
        shm_snapshot_ref="shm://case_002b/fluid",
        thermo_snapshot_ref="thermo://case_002b/fluid",
    )
    solid_regions = [
        RegionSlice(
            name=f"heater_{i}",
            kind="solid",
            thermo_type="heSolidThermo",
            coupled_patches=(
                CoupledPatch(
                    patch_name=f"heater_{i}_to_fluid",
                    coupling_type=COUPLED_RAD_MIXED,
                    neighbour_region="fluid",
                ),
            ),
            shm_snapshot_ref=f"shm://case_002b/heater_{i}",
            thermo_snapshot_ref=f"thermo://case_002b/heater_{i}",
        )
        for i in range(6)
    ]
    return RunArtifactSlice(
        run_id="R-002B-1",
        case_id="case_002b",
        success=True,
        exit_code=0,
        regions=[fluid_region] + solid_regions,
    )


class TestCase002b:
    def test_region_count(self):
        s = _make_case_002b_slice()
        assert s.regions is not None
        assert len(s.regions) == 7

    def test_fluid_solid_split(self):
        s = _make_case_002b_slice()
        assert s.regions is not None
        kinds = [r.kind for r in s.regions]
        assert kinds.count("fluid") == 1
        assert kinds.count("solid") == 6

    def test_asdict_inmemory_then_reconstruct(self):
        """IN-MEMORY asdict → reconstruct restores identical field values.

        NOTE (red-team carry-back): this asserts the *in-memory* asdict property
        only — dataclasses.asdict keeps ``coupled_patches`` as a tuple. It does
        NOT round-trip through the subsystem's JSON serializer, which has no
        tuple type and flattens tuple→list. That JSON boundary (tuple→list, and
        the required _reconstruct re-wrap) is pinned separately in
        ``tests/p3/test_run_artifact_slice_json_roundtrip_redteam.py``. A future
        W3.1 hydrate/persist path MUST NOT compare raw post-JSON container types
        to ``tuple``.
        """
        s = _make_case_002b_slice()
        d = dataclasses.asdict(s)
        # regions is a list of dicts after asdict
        assert isinstance(d["regions"], list)
        assert len(d["regions"]) == 7
        # asdict (in-memory) keeps the tuple; JSON would flatten it to a list
        # (see the json_roundtrip_redteam file for the persistence-boundary pin).
        assert isinstance(d["regions"][0]["coupled_patches"], tuple)
        assert len(d["regions"][0]["coupled_patches"]) == 6
        # Reconstruct and assert equality
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert len(s2.regions) == 7
        assert s2.regions[0].name == "fluid"
        assert s2.regions[0].kind == "fluid"
        assert s2.regions[0].thermo_type == "heRhoThermo"
        assert s2.regions[0].coupled_patches is not None
        assert len(s2.regions[0].coupled_patches) == 6
        for cp in s2.regions[0].coupled_patches:
            assert cp.coupling_type == COUPLED_RAD_MIXED

    def test_refs_survive_round_trip(self):
        s = _make_case_002b_slice()
        d = dataclasses.asdict(s)
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert s2.regions[0].shm_snapshot_ref == "shm://case_002b/fluid"
        assert s2.regions[0].thermo_snapshot_ref == "thermo://case_002b/fluid"
        assert s2.regions[1].shm_snapshot_ref == "shm://case_002b/heater_0"

    def test_solid_region_thermo_type(self):
        s = _make_case_002b_slice()
        assert s.regions is not None
        for r in s.regions[1:]:
            assert r.thermo_type == "heSolidThermo"
            assert r.kind == "solid"


# ---------------------------------------------------------------------------
# C · case_011-shaped: 3-region round-trip
# ---------------------------------------------------------------------------

def _make_case_011_slice() -> RunArtifactSlice:
    """Build a 3-region CHT slice shaped like case_011:
    2 fluids (hot + cold air) + 1 aluminum solid, conduction coupling.
    """
    air_hot = RegionSlice(
        name="air_hot",
        kind="fluid",
        thermo_type="heRhoThermo",
        coupled_patches=(
            CoupledPatch(
                patch_name="hot_to_aluminum",
                coupling_type=COUPLED_BAFFLE_MIXED,
                neighbour_region="aluminum",
            ),
        ),
        shm_snapshot_ref="shm://case_011/air_hot",
        thermo_snapshot_ref="thermo://case_011/air_hot",
    )
    air_cold = RegionSlice(
        name="air_cold",
        kind="fluid",
        thermo_type="heRhoThermo",
        coupled_patches=(
            CoupledPatch(
                patch_name="cold_to_aluminum",
                coupling_type=COUPLED_BAFFLE_MIXED,
                neighbour_region="aluminum",
            ),
        ),
        shm_snapshot_ref="shm://case_011/air_cold",
        thermo_snapshot_ref="thermo://case_011/air_cold",
    )
    aluminum = RegionSlice(
        name="aluminum",
        kind="solid",
        thermo_type="heSolidThermo",
        coupled_patches=(
            CoupledPatch(
                patch_name="aluminum_to_hot",
                coupling_type=COUPLED_BAFFLE_MIXED,
                neighbour_region="air_hot",
            ),
            CoupledPatch(
                patch_name="aluminum_to_cold",
                coupling_type=COUPLED_BAFFLE_MIXED,
                neighbour_region="air_cold",
            ),
        ),
        shm_snapshot_ref="shm://case_011/aluminum",
        thermo_snapshot_ref="thermo://case_011/aluminum",
    )
    return RunArtifactSlice(
        run_id="R-011-1",
        case_id="case_011",
        success=True,
        exit_code=0,
        regions=[air_hot, air_cold, aluminum],
    )


class TestCase011:
    def test_region_count(self):
        s = _make_case_011_slice()
        assert s.regions is not None
        assert len(s.regions) == 3

    def test_fluid_solid_split(self):
        s = _make_case_011_slice()
        assert s.regions is not None
        kinds = [r.kind for r in s.regions]
        assert kinds.count("fluid") == 2
        assert kinds.count("solid") == 1

    def test_asdict_round_trip(self):
        s = _make_case_011_slice()
        d = dataclasses.asdict(s)
        assert isinstance(d["regions"], list)
        assert len(d["regions"]) == 3
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert len(s2.regions) == 3
        # Solid (aluminum) has 2 coupled patches
        aluminum = s2.regions[2]
        assert aluminum.name == "aluminum"
        assert aluminum.kind == "solid"
        assert aluminum.coupled_patches is not None
        assert len(aluminum.coupled_patches) == 2
        for cp in aluminum.coupled_patches:
            assert cp.coupling_type == COUPLED_BAFFLE_MIXED

    def test_coupling_type_in_vocab(self):
        s = _make_case_011_slice()
        assert s.regions is not None
        for r in s.regions:
            if r.coupled_patches:
                for cp in r.coupled_patches:
                    assert cp.coupling_type == COUPLED_BAFFLE_MIXED


# ---------------------------------------------------------------------------
# D · Presence-vs-payload: None vs [] vs populated-with-no-payload
# ---------------------------------------------------------------------------

class TestPresenceVsPayload:
    def test_regions_none_distinct_from_empty_list(self):
        """None = no region info at all (different from empty list)."""
        s_none = RunArtifactSlice(
            run_id="R-P-1", case_id="c1", success=True, exit_code=0,
        )
        s_empty = RunArtifactSlice(
            run_id="R-P-2", case_id="c1", success=True, exit_code=0,
            regions=[],
        )
        assert s_none.regions is None
        assert s_empty.regions == []
        assert s_none.regions != s_empty.regions

    def test_regions_empty_list_round_trip(self):
        """regions=[] survives asdict round-trip as an empty list (not None)."""
        s = RunArtifactSlice(
            run_id="R-P-3", case_id="c1", success=True, exit_code=0,
            regions=[],
        )
        d = dataclasses.asdict(s)
        assert d["regions"] == []
        s2 = _reconstruct_slice(d)
        assert s2.regions == []
        assert s2.regions is not None

    def test_regions_none_round_trip(self):
        """regions=None survives asdict round-trip as None."""
        s = RunArtifactSlice(
            run_id="R-P-4", case_id="c1", success=True, exit_code=0,
        )
        d = dataclasses.asdict(s)
        assert d["regions"] is None
        s2 = _reconstruct_slice(d)
        assert s2.regions is None

    def test_region_slice_payload_none_is_distinct(self):
        """RegionSlice with name+kind only (all payload None) is a DISTINCT
        state from one that has thermo_type or coupled_patches populated."""
        r_payload_none = RegionSlice(name="fluid", kind="fluid")
        r_with_thermo = RegionSlice(name="fluid", kind="fluid", thermo_type="heRhoThermo")
        assert r_payload_none.thermo_type is None
        assert r_with_thermo.thermo_type == "heRhoThermo"
        assert r_payload_none != r_with_thermo

    def test_region_slice_payload_none_round_trip(self):
        """RegionSlice(name, kind only) round-trips with all payload as None."""
        s = RunArtifactSlice(
            run_id="R-P-5", case_id="c1", success=True, exit_code=0,
            regions=[RegionSlice(name="fluid", kind="fluid")],
        )
        d = dataclasses.asdict(s)
        assert d["regions"][0]["thermo_type"] is None
        assert d["regions"][0]["coupled_patches"] is None
        assert d["regions"][0]["shm_snapshot_ref"] is None
        assert d["regions"][0]["thermo_snapshot_ref"] is None
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert s2.regions[0].thermo_type is None
        assert s2.regions[0].coupled_patches is None

    # --- per-FIELD presence-vs-payload (red-team lens-2 P2#1) ---
    # The DEC-V61-213 three-state contract applies at the coupled_patches field
    # too — None (coupling not extracted) vs () (extracted, zero patches) vs
    # populated. W3.1 R13 WALL_COUPLING_MISMATCH branches on exactly this axis.

    def test_coupled_patches_none_vs_empty_tuple_distinct(self):
        """coupled_patches=None (not extracted) != () (extracted, zero patches)."""
        r_unknown = RegionSlice(name="fluid", kind="fluid", coupled_patches=None)
        r_zero = RegionSlice(name="fluid", kind="fluid", coupled_patches=())
        assert r_unknown.coupled_patches is None
        assert r_zero.coupled_patches == ()
        assert r_zero.coupled_patches is not None
        assert r_unknown != r_zero

    def test_coupled_patches_empty_tuple_round_trip(self):
        """coupled_patches=() survives asdict + reconstruct as () (not collapsed to None)."""
        s = RunArtifactSlice(
            run_id="R-P-CP", case_id="c1", success=True, exit_code=0,
            regions=[RegionSlice(name="solid", kind="solid", coupled_patches=())],
        )
        d = dataclasses.asdict(s)
        # asdict keeps the empty tuple in-memory; reconstruct must restore () not None.
        assert d["regions"][0]["coupled_patches"] == ()
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert s2.regions[0].coupled_patches == ()
        assert s2.regions[0].coupled_patches is not None

    def test_kind_none_ambiguous_round_trip(self):
        """kind=None (ambiguous upstream classification, per W3.0.2
        RegionThermoSnapshot.kind domain) is a legitimate honest value and must
        round-trip as None — never fabricated into a fluid/solid label (red-team
        lens-2 P2#2). W3.1 R15 must skip a None-kind region, not guess.
        """
        r_ambiguous = RegionSlice(name="weird_zone", kind=None)
        assert r_ambiguous.kind is None
        # distinct from a classified region of the same name
        assert r_ambiguous != RegionSlice(name="weird_zone", kind="fluid")
        s = RunArtifactSlice(
            run_id="R-P-AMB", case_id="c1", success=True, exit_code=0,
            regions=[r_ambiguous],
        )
        d = dataclasses.asdict(s)
        assert d["regions"][0]["kind"] is None
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        assert s2.regions[0].kind is None

    def test_three_states_are_all_distinct(self):
        """Explicit three-state distinction: None vs [] vs [no-payload-region]."""
        s_none = RunArtifactSlice(
            run_id="R-P-6", case_id="c", success=True, exit_code=0,
        )
        s_empty = RunArtifactSlice(
            run_id="R-P-6", case_id="c", success=True, exit_code=0,
            regions=[],
        )
        s_populated = RunArtifactSlice(
            run_id="R-P-6", case_id="c", success=True, exit_code=0,
            regions=[RegionSlice(name="fluid", kind="fluid")],
        )
        assert s_none.regions is None
        assert s_empty.regions == []
        assert s_populated.regions is not None and len(s_populated.regions) == 1
        # All three have the same run_id/case_id but differ in regions
        assert s_none != s_empty
        assert s_empty != s_populated
        assert s_none != s_populated


# ---------------------------------------------------------------------------
# E · Frozen: FrozenInstanceError on mutation attempt
# ---------------------------------------------------------------------------

class TestFrozen:
    def test_run_artifact_slice_is_frozen(self):
        s = RunArtifactSlice(
            run_id="R-F-1", case_id="c", success=True, exit_code=0,
        )
        with pytest.raises(FrozenInstanceError):
            s.regions = []  # type: ignore[misc]

    def test_region_slice_is_frozen(self):
        r = RegionSlice(name="fluid", kind="fluid")
        with pytest.raises(FrozenInstanceError):
            r.thermo_type = "heRhoThermo"  # type: ignore[misc]

    def test_coupled_patch_is_frozen(self):
        cp = CoupledPatch(
            patch_name="fluid_to_heater",
            coupling_type=COUPLED_BAFFLE_MIXED,
        )
        with pytest.raises(FrozenInstanceError):
            cp.coupling_type = "something_else"  # type: ignore[misc]

    def test_region_slice_cannot_mutate_name(self):
        r = RegionSlice(name="solid_1", kind="solid")
        with pytest.raises(FrozenInstanceError):
            r.name = "solid_2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# F · coupled_patches tuple: round-trip, multi-patch, vocab values
# ---------------------------------------------------------------------------

class TestCoupledPatchesTuple:
    def test_tuple_type_preserved(self):
        """coupled_patches is stored as a tuple (not a list)."""
        patches = (
            CoupledPatch("patch_a", COUPLED_BAFFLE_MIXED, "region_b"),
            CoupledPatch("patch_b", COUPLED_RAD_MIXED, "region_c"),
            CoupledPatch("patch_c", HUMIDITY_COUPLED, None),
        )
        r = RegionSlice(name="fluid", kind="fluid", coupled_patches=patches)
        assert isinstance(r.coupled_patches, tuple)
        assert len(r.coupled_patches) == 3

    def test_tuple_round_trips_in_asdict(self):
        """dataclasses.asdict keeps tuples as tuples (Python 3.12+ behavior);
        reconstruction from the asdict output restores CoupledPatch objects."""
        patches = (
            CoupledPatch("patch_a", COUPLED_BAFFLE_MIXED, "region_b"),
            CoupledPatch("patch_b", COUPLED_RAD_MIXED, "region_c"),
        )
        r = RegionSlice(name="fluid", kind="fluid", coupled_patches=patches)
        s = RunArtifactSlice(
            run_id="R-CP-1", case_id="c", success=True, exit_code=0,
            regions=[r],
        )
        d = dataclasses.asdict(s)
        # asdict keeps tuple as tuple; entries are plain dicts
        cp_seq = d["regions"][0]["coupled_patches"]
        assert isinstance(cp_seq, tuple)
        assert len(cp_seq) == 2
        assert cp_seq[0]["coupling_type"] == COUPLED_BAFFLE_MIXED
        assert cp_seq[1]["coupling_type"] == COUPLED_RAD_MIXED
        # Reconstruction restores CoupledPatch objects in a tuple
        s2 = _reconstruct_slice(d)
        assert s2.regions is not None
        r2 = s2.regions[0]
        assert isinstance(r2.coupled_patches, tuple)
        assert len(r2.coupled_patches) == 2
        assert r2.coupled_patches[0].patch_name == "patch_a"
        assert r2.coupled_patches[1].coupling_type == COUPLED_RAD_MIXED

    def test_all_three_vocab_values_accepted(self):
        """All three real coupling-type vocab values are accepted without error."""
        for ct in [COUPLED_BAFFLE_MIXED, COUPLED_RAD_MIXED, HUMIDITY_COUPLED]:
            cp = CoupledPatch(patch_name="p", coupling_type=ct)
            assert cp.coupling_type == ct

    def test_neighbour_region_optional(self):
        """neighbour_region defaults None and survives round-trip."""
        cp = CoupledPatch(patch_name="patch_x", coupling_type=COUPLED_BAFFLE_MIXED)
        assert cp.neighbour_region is None
        d = dataclasses.asdict(cp)
        assert d["neighbour_region"] is None

    def test_single_patch_tuple_round_trip(self):
        """Single-element tuple round-trips correctly."""
        r = RegionSlice(
            name="solid",
            kind="solid",
            coupled_patches=(
                CoupledPatch("s_to_f", COUPLED_RAD_MIXED, "fluid"),
            ),
        )
        d = dataclasses.asdict(r)
        assert len(d["coupled_patches"]) == 1
        restored = tuple(CoupledPatch(**cp) for cp in d["coupled_patches"])
        assert restored[0].patch_name == "s_to_f"
        assert restored[0].neighbour_region == "fluid"


# ---------------------------------------------------------------------------
# G · Byte-reproducibility (RS#36): sidecar path does not read slice.regions
# ---------------------------------------------------------------------------

class TestByteReproducibilitySidecar:
    def test_serialize_path_does_not_reference_run_artifact_slice(self):
        """RS#36 assertion: the audit sidecar serialize path writes
        manifest['commentary'] (a plain dict), never RunArtifactSlice.regions.
        Confirmed by importing the serialize module and verifying it has no
        direct dependency on RunArtifactSlice."""
        from src.audit_package import serialize as _ser

        # The serialize module must not import from pattern_matcher
        import inspect
        source = inspect.getsource(_ser)
        assert "RunArtifactSlice" not in source, (
            "RS#36 broken: serialize.py references RunArtifactSlice — "
            "adding regions field would alter sidecar bytes"
        )

    def test_regions_field_does_not_affect_matched_json_bytes(self):
        """RS#36 byte-invariance — exercised through the REAL matcher + serializer
        (Codex R1 P3#1). Run ``match_advisor_patterns`` on a slice WITH regions
        vs an otherwise-identical slice WITHOUT regions, serialize each matched-
        commentary list with the REAL ``_canonical_json``, and assert byte-
        identical output. No shipped V9 rule (R1–R9) reads ``regions``, so the
        matched commentary — the only thing the sidecar serializes — cannot
        differ. This genuinely fences a future leak of ``regions`` into the
        serialized output (the prior version serialized one synthetic dict twice
        — a tautology that fenced nothing).
        """
        from ui.backend.services.v9_advisor.pattern_matcher import (
            match_advisor_patterns,
        )
        from ui.backend.services.v9_advisor.rules import V9_ADVISOR_RULES
        from src.audit_package.serialize import _canonical_json

        base = dict(run_id="R-RS36", case_id="c", success=True, exit_code=0)
        slice_no_regions = RunArtifactSlice(**base)
        slice_with_regions = RunArtifactSlice(
            **base,
            regions=[
                RegionSlice(name="fluid", kind="fluid", thermo_type="heRhoThermo"),
                RegionSlice(
                    name="solid", kind="solid",
                    coupled_patches=(
                        CoupledPatch(patch_name="iface", coupling_type=COUPLED_BAFFLE_MIXED),
                    ),
                ),
            ],
        )

        def matched_bytes(s: RunArtifactSlice) -> bytes:
            matches = match_advisor_patterns(s, V9_ADVISOR_RULES)
            return _canonical_json([dataclasses.asdict(m) for m in matches])

        assert matched_bytes(slice_with_regions) == matched_bytes(slice_no_regions)

    def test_regions_field_disjoint_from_commentary(self):
        """The slice dict and the commentary sidecar are disjoint (Codex R1 P3#2).
        Covers the regions=None branch this test previously MISLABELED (it built a
        populated slice). asdict of a regions=None slice → regions is None at top
        level and there is NO 'commentary' key; a populated-regions slice likewise
        carries regions only in the slice dict, never under a commentary key.
        """
        s_none = RunArtifactSlice(
            run_id="R-SR-1", case_id="c", success=True, exit_code=0,
        )
        d_none = dataclasses.asdict(s_none)
        assert d_none["regions"] is None          # the documented None branch
        assert "commentary" not in d_none

        s_pop = RunArtifactSlice(
            run_id="R-SR-2", case_id="c", success=True, exit_code=0,
            regions=[RegionSlice(name="fluid", kind="fluid")],
        )
        d_pop = dataclasses.asdict(s_pop)
        assert d_pop["regions"][0]["name"] == "fluid"
        assert "commentary" not in d_pop
