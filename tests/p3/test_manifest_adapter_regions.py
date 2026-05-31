"""P3 W3.1 Codex R0 fix · manifest_adapter regions wiring tests.

Two test classes:

TestProductionPathReachability
    Proves the manifest → _regions_from_manifest → derive_slice_from_manifest →
    matches_for_manifest() production chain surfaces CHT rules R13–R16 end-to-end
    through the REAL deriver (no synthetic shortcut). This is the Codex P1 crux:
    before this fix matches_for_manifest() could NEVER return any of R13–R16 because
    regions was always None.

    Tests use the REAL public API (matches_for_manifest) to verify:
      - manifest WITH regions containing an unhealthy region → R14 fires
      - manifest WITHOUT regions key → no CHT rule fires (silent / graceful)
      - manifest WITH regions containing dangling neighbour → R13 fires
      - manifest WITH all-solid regions → R15 fires
      - manifest WITH partial shm_snapshot_ref → R16 fires

TestRegionsManifestParsingGraceful
    Proves _regions_from_manifest / derive_slice_from_manifest return gracefully
    (regions=None, no exception) on every class of malformed manifest["regions"]:
      - not a list
      - list with a non-dict entry
      - region dict missing "name"
      - region dict with wrong-typed fields
      - region dict with null name
      - manifest key present but value is null
      - deeply malformed coupled_patches entries

All execution: MOCKED (no OpenFOAM process invoked; all manifests are synthetic
Python dicts — MOCKED RUN, not a real solver run).
"""

from __future__ import annotations

import pytest

from ui.backend.services.v9_advisor.manifest_adapter import (
    _regions_from_manifest,
    derive_slice_from_manifest,
    matches_for_manifest,
)


# ---------------------------------------------------------------------------
# Minimal valid manifest helpers
# ---------------------------------------------------------------------------

def _minimal_manifest(**extra) -> dict:
    """Minimal manifest with the standard top-level keys that the deriver reads.
    The deriver only requires that keys are dicts (or absent); we keep them
    minimal to avoid polluting the test with unrelated fields.
    """
    m: dict = {
        "case": {"id": "cht_test", "gold_standard": {}},
        "run": {"run_id": "R-test", "outputs": {}},
        "measurement": {"comparator_verdict": "PASS", "key_quantities": {}},
    }
    m.update(extra)
    return m


def _region_entry(
    name: str,
    kind=None,
    thermo_type=None,
    thermo_snapshot_ref=None,
    coupled_patches=None,
    shm_snapshot_ref=None,
) -> dict:
    """Build a manifest region entry dict (mirrors the W3.2 contract)."""
    return {
        "name": name,
        "kind": kind,
        "thermo_type": thermo_type,
        "thermo_snapshot_ref": thermo_snapshot_ref,
        "coupled_patches": coupled_patches,
        "shm_snapshot_ref": shm_snapshot_ref,
    }


def _rule_ids(matches: list) -> list:
    return [m["rule_id"] for m in matches]


# ---------------------------------------------------------------------------
# TestProductionPathReachability — the Codex P1 crux
# ---------------------------------------------------------------------------

class TestProductionPathReachability:
    """End-to-end production path: manifest → matches_for_manifest → CHT rules.

    These tests call the REAL production entry point matches_for_manifest() —
    not the rule predicates directly. This proves the manifest → RegionSlice
    → rule chain works end-to-end through the real deriver.
    """

    def test_r14_fires_via_manifest_with_unhealthy_region(self):
        """P1 crux: manifest WITH regions, solid region missing thermo → R14.

        Before the fix: regions was always None in the slice, so R14 could
        never fire. After the fix: the populated regions key is parsed and
        R14 fires on the solid region that has thermo_type=None and
        thermo_snapshot_ref=None.
        """
        manifest = _minimal_manifest(regions=[
            _region_entry(
                name="fluid_hot",
                kind="fluid",
                thermo_type="heRhoThermo",
                thermo_snapshot_ref="snap_fluid",
                shm_snapshot_ref="shm_fluid",
                coupled_patches=[],
            ),
            _region_entry(
                name="solid_plate",
                kind="solid",
                thermo_type=None,          # missing — R14 trigger
                thermo_snapshot_ref=None,  # missing — R14 trigger
                shm_snapshot_ref="shm_solid",
                coupled_patches=[],
            ),
        ])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        assert "PER_REGION_THERMO_MISSING_V9_R14" in ids, (
            "R14 must fire end-to-end via matches_for_manifest when a region "
            "has thermo_type=None AND thermo_snapshot_ref=None"
        )
        r14 = next(m for m in matches if m["rule_id"] == "PER_REGION_THERMO_MISSING_V9_R14")
        assert r14["matched_at"] == "region:solid_plate:thermo_missing"
        assert r14["severity"] == "warn"

    def test_no_cht_rule_when_manifest_has_no_regions_key(self):
        """Graceful silent: no 'regions' key → regions=None → R13–R16 all silent.

        This covers every current real audit bundle (W3.2 not yet emitted).
        """
        manifest = _minimal_manifest()
        assert "regions" not in manifest
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        for rule_id in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
            "CONDUCTION_DOMINANCE_V9_R15",
            "FACE_ZONE_LOSS_V9_R16",
        ):
            assert rule_id not in ids, (
                f"{rule_id} must be silent when manifest has no 'regions' key"
            )

    def test_r13_fires_via_manifest_with_dangling_neighbour_region(self):
        """R13 fires end-to-end: a coupled_patch references a neighbour_region
        that is NOT in the assembled region-name inventory.
        """
        manifest = _minimal_manifest(regions=[
            _region_entry(
                name="region_fluid",
                kind="fluid",
                thermo_type="heRhoThermo",
                thermo_snapshot_ref="snap_f",
                shm_snapshot_ref="shm_f",
                coupled_patches=[{
                    "patch_name": "fluid_to_ghost",
                    "coupling_type": "compressible::turbulentTemperatureCoupledBaffleMixed",
                    "neighbour_region": "ghost_region",  # NOT in inventory → R13
                }],
            ),
            _region_entry(
                name="region_solid",
                kind="solid",
                thermo_type="heSolidThermo",
                thermo_snapshot_ref="snap_s",
                shm_snapshot_ref="shm_s",
                coupled_patches=[],
            ),
        ])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        assert "COUPLED_INTERFACE_DANGLING_REF_V9_R13" in ids, (
            "R13 must fire end-to-end when neighbour_region is not in region inventory"
        )

    def test_r15_fires_via_manifest_all_solid_regions(self):
        """R15 fires end-to-end: all regions have kind='solid', no fluid present."""
        manifest = _minimal_manifest(regions=[
            _region_entry(
                name="plate_1", kind="solid",
                thermo_type="heSolidThermo", thermo_snapshot_ref="s1",
                shm_snapshot_ref="shm1", coupled_patches=[],
            ),
            _region_entry(
                name="plate_2", kind="solid",
                thermo_type="heSolidThermo", thermo_snapshot_ref="s2",
                shm_snapshot_ref="shm2", coupled_patches=[],
            ),
        ])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        assert "CONDUCTION_DOMINANCE_V9_R15" in ids, (
            "R15 must fire end-to-end when all manifest regions are solid"
        )

    def test_r16_fires_via_manifest_partial_shm_snapshot(self):
        """R16 fires end-to-end: one region has shm_snapshot_ref, one does not (XOR)."""
        manifest = _minimal_manifest(regions=[
            _region_entry(
                name="fluid",
                kind="fluid",
                thermo_type="heRhoThermo",
                thermo_snapshot_ref="snap_f",
                shm_snapshot_ref="shm_f",  # present
                coupled_patches=[],
            ),
            _region_entry(
                name="solid_lost",
                kind="solid",
                thermo_type="heSolidThermo",
                thermo_snapshot_ref="snap_s",
                shm_snapshot_ref=None,  # absent — R16 trigger
                coupled_patches=[],
            ),
        ])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        assert "FACE_ZONE_LOSS_V9_R16" in ids, (
            "R16 must fire end-to-end when one region lacks shm_snapshot_ref "
            "while at least one other region has it"
        )

    def test_no_cht_rule_when_manifest_regions_empty_list(self):
        """Empty regions list → R13–R16 all silent (zero regions to check)."""
        manifest = _minimal_manifest(regions=[])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        for rule_id in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
            "CONDUCTION_DOMINANCE_V9_R15",
            "FACE_ZONE_LOSS_V9_R16",
        ):
            assert rule_id not in ids, (
                f"{rule_id} must be silent when manifest['regions'] == []"
            )

    def test_healthy_regions_all_rules_silent(self):
        """Healthy CHT: both fluid+solid with full thermo + matching patches → all CHT rules silent."""
        manifest = _minimal_manifest(regions=[
            _region_entry(
                name="fluid",
                kind="fluid",
                thermo_type="heRhoThermo",
                thermo_snapshot_ref="snap_f",
                shm_snapshot_ref="shm_f",
                coupled_patches=[{
                    "patch_name": "f_to_s",
                    "coupling_type": "compressible::turbulentTemperatureCoupledBaffleMixed",
                    "neighbour_region": "solid",  # valid — in inventory
                }],
            ),
            _region_entry(
                name="solid",
                kind="solid",
                thermo_type="heSolidThermo",
                thermo_snapshot_ref="snap_s",
                shm_snapshot_ref="shm_s",
                coupled_patches=[{
                    "patch_name": "s_to_f",
                    "coupling_type": "compressible::turbulentTemperatureCoupledBaffleMixed",
                    "neighbour_region": "fluid",  # valid — in inventory
                }],
            ),
        ])
        matches = matches_for_manifest(manifest)
        ids = _rule_ids(matches)
        for rule_id in (
            "COUPLED_INTERFACE_DANGLING_REF_V9_R13",
            "PER_REGION_THERMO_MISSING_V9_R14",
            "CONDUCTION_DOMINANCE_V9_R15",
            "FACE_ZONE_LOSS_V9_R16",
        ):
            assert rule_id not in ids, (
                f"{rule_id} must be silent on a healthy CHT manifest"
            )


# ---------------------------------------------------------------------------
# TestRegionsManifestParsingGraceful — crash-safety on malformed input
# ---------------------------------------------------------------------------

class TestRegionsManifestParsingGraceful:
    """_regions_from_manifest must NEVER raise on any malformed input.

    The deriver runs on the production hot path (every audit bundle). Any
    crash here breaks all audit bundle commentary. Every malformed input must
    yield None or graceful partial result — no exception propagation.
    """

    def test_no_regions_key_returns_none(self):
        assert _regions_from_manifest({}) is None
        assert _regions_from_manifest({"case": {}, "run": {}}) is None

    def test_regions_not_a_list_returns_none(self):
        assert _regions_from_manifest({"regions": "not_a_list"}) is None
        assert _regions_from_manifest({"regions": 42}) is None
        assert _regions_from_manifest({"regions": {"fluid": {}}}) is None

    def test_regions_null_returns_none(self):
        # explicit null in manifest → treat as not-extracted
        assert _regions_from_manifest({"regions": None}) is None

    def test_empty_list_returns_empty_list(self):
        result = _regions_from_manifest({"regions": []})
        assert result == []

    def test_non_dict_entry_skipped_gracefully(self):
        # A list with a non-dict entry — the non-dict is skipped, valid entries kept
        result = _regions_from_manifest({
            "regions": [
                "not_a_dict",
                42,
                None,
                {"name": "fluid", "kind": "fluid"},
            ]
        })
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "fluid"

    def test_region_missing_name_skipped(self):
        result = _regions_from_manifest({
            "regions": [
                {"kind": "fluid"},  # no name key → skip
                {"name": None, "kind": "fluid"},  # null name → skip
                {"name": "", "kind": "fluid"},  # empty name → skip
                {"name": "solid", "kind": "solid"},  # valid
            ]
        })
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "solid"

    def test_wrong_typed_fields_coerced_to_none(self):
        """Non-string thermo_type / shm_snapshot_ref / thermo_snapshot_ref → None."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                "thermo_type": 12345,       # wrong type → None
                "shm_snapshot_ref": True,   # wrong type → None
                "thermo_snapshot_ref": [],  # wrong type → None
            }]
        })
        assert result is not None
        assert len(result) == 1
        r = result[0]
        assert r.name == "fluid"
        assert r.thermo_type is None
        assert r.shm_snapshot_ref is None
        assert r.thermo_snapshot_ref is None

    def test_unknown_kind_coerced_to_none(self):
        """kind not in ('fluid', 'solid', None) → coerce to None (honest)."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "mystery",
                "kind": "supercritical",  # unknown → None
            }]
        })
        assert result is not None
        assert result[0].kind is None

    def test_coupled_patches_not_a_list_yields_none(self):
        """Malformed coupled_patches (not a list) → None (not extracted)."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                "coupled_patches": "wrong_type",
            }]
        })
        assert result is not None
        r = result[0]
        assert r.coupled_patches is None

    def test_coupled_patches_explicit_null_yields_none(self):
        """coupled_patches: null → None (not extracted / treat same as absent)."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                "coupled_patches": None,
            }]
        })
        assert result is not None
        r = result[0]
        assert r.coupled_patches is None

    def test_coupled_patches_empty_list_yields_empty_tuple(self):
        """coupled_patches: [] → () (extracted, zero patches — three-state)."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                "coupled_patches": [],
            }]
        })
        assert result is not None
        r = result[0]
        assert r.coupled_patches == ()

    def test_malformed_coupled_patch_entries_skipped(self):
        """Non-dict or missing patch_name/coupling_type entries are skipped."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                "coupled_patches": [
                    "not_a_dict",           # skip
                    42,                     # skip
                    {"coupling_type": "x"}, # missing patch_name → skip
                    {"patch_name": "p"},    # missing coupling_type → skip
                    {
                        "patch_name": "valid_patch",
                        "coupling_type": "compressible::turbulentTemperatureCoupledBaffleMixed",
                        "neighbour_region": "solid",
                    },
                ],
            }]
        })
        assert result is not None
        r = result[0]
        assert r.coupled_patches is not None
        assert len(r.coupled_patches) == 1
        assert r.coupled_patches[0].patch_name == "valid_patch"

    def test_derive_slice_never_raises_on_malformed_regions(self):
        """derive_slice_from_manifest must not raise on any malformed regions."""
        bad_manifests = [
            {"regions": "not_a_list", "case": {}, "run": {}, "measurement": {}},
            {"regions": [None, 42, "bad"], "case": {}, "run": {}, "measurement": {}},
            {"regions": [{"name": None}], "case": {}, "run": {}, "measurement": {}},
            {"regions": [{"name": "r", "coupled_patches": {"bad": "dict"}}],
             "case": {}, "run": {}, "measurement": {}},
        ]
        for manifest in bad_manifests:
            # Must not raise — just return a valid slice
            slice_ = derive_slice_from_manifest(manifest)
            # regions must be None or a valid list (never partial crash)
            assert slice_.regions is None or isinstance(slice_.regions, list)

    def test_three_state_none_vs_empty_vs_populated(self):
        """Verify three-state: absent → None · [] → [] · populated → list."""
        # State 1: absent key → None
        r1 = _regions_from_manifest({"case": {}, "run": {}})
        assert r1 is None

        # State 2: empty list → []
        r2 = _regions_from_manifest({"regions": []})
        assert r2 == []

        # State 3: populated list → non-empty list
        r3 = _regions_from_manifest({
            "regions": [{"name": "fluid", "kind": "fluid"}]
        })
        assert r3 is not None and len(r3) == 1

    def test_coupled_patches_absent_key_yields_none(self):
        """coupled_patches key absent → None (key not in dict, not extracted)."""
        result = _regions_from_manifest({
            "regions": [{
                "name": "fluid",
                "kind": "fluid",
                # coupled_patches key is completely absent
            }]
        })
        assert result is not None
        r = result[0]
        # Key absent → not extracted → None
        assert r.coupled_patches is None
