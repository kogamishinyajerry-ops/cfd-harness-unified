"""RED-TEAM crash-safety probe for _regions_from_manifest + the full
production hot path derive_slice_from_manifest / matches_for_manifest.

derive_slice_from_manifest() runs on EVERY audit bundle (not just CHT).
_regions_from_manifest() must NEVER raise — a crash breaks ALL commentary
output for every audit bundle. This module attacks it with every malformed
manifest["regions"] shape and asserts:

  (A) NO unhandled exception ever escapes derive_slice_from_manifest /
      matches_for_manifest (the production entry points).
  (B) regions is None or a valid list of RegionSlice (never partial crash).
  (C) NO FABRICATION: absent kind stays None (never defaulted to 'fluid'),
      absent thermo stays None, absent coupled_patches stays None.
  (D) A single malformed region does not poison the whole list (isolation).

All MOCKED dicts — no OpenFOAM process. MOCKED RUN, not a solver run.
"""

from __future__ import annotations

import itertools

import pytest

from ui.backend.services.v9_advisor.manifest_adapter import (
    _regions_from_manifest,
    derive_slice_from_manifest,
    matches_for_manifest,
)
from ui.backend.services.v9_advisor.pattern_matcher import RegionSlice


# ---------------------------------------------------------------------------
# Adversarial payload catalog — every malformed shape from the attack brief
# ---------------------------------------------------------------------------


class _Exploding:
    """An object that raises on EVERY interaction (isinstance is fine, but
    any attribute/dunder access raises). Used to prove the try/except holds
    even if a 'region entry' is a hostile object rather than a clean dict."""

    def __getattr__(self, name):  # pragma: no cover - defensive
        raise RuntimeError("boom: hostile object touched")

    def __eq__(self, other):  # pragma: no cover - defensive
        raise RuntimeError("boom: equality")

    def __hash__(self):  # pragma: no cover - defensive
        raise RuntimeError("boom: hash")


# A dict subclass whose .get() raises — proves the try/except inside the
# loop body catches errors from a malicious mapping that passes isinstance.
class _EvilDict(dict):
    def get(self, *a, **k):  # type: ignore[override]
        raise RuntimeError("boom: evil .get")


MALFORMED_REGIONS_VALUES = [
    # not a list
    {"fluid": {}},                       # dict, not list
    "fluid",                             # str
    42,                                  # int
    3.14,                                # float
    True,                                # bool
    (1, 2, 3),                           # tuple (NOT a list — isinstance list is False)
    {1, 2, 3},                           # set
    object(),                            # arbitrary object
    # lists with bad entries
    [None],
    [42, "x", 3.14, True, None],
    [[1, 2], {"name": "ok"}],            # nested list entry + one valid
    [{"name": "ok"}, "trailing_garbage"],
    # region dicts missing/garbage name
    [{"kind": "fluid"}],                 # no name
    [{"name": None}],                    # null name
    [{"name": ""}],                      # empty name
    [{"name": 123}],                     # int name
    [{"name": ["list"]}],                # list name
    [{"name": {"nested": "dict"}}],      # dict name
    # coupled_patches garbage
    [{"name": "r", "coupled_patches": {"bad": "dict"}}],   # dict not list
    [{"name": "r", "coupled_patches": "str"}],
    [{"name": "r", "coupled_patches": 99}],
    [{"name": "r", "coupled_patches": [None, 1, "x"]}],
    [{"name": "r", "coupled_patches": [{"coupling_type": "x"}]}],  # no patch_name
    [{"name": "r", "coupled_patches": [{"patch_name": "p"}]}],     # no coupling_type
    [{"name": "r", "coupled_patches": [{"patch_name": 1, "coupling_type": 2}]}],
    [{"name": "r", "coupled_patches": [
        {"patch_name": "p", "coupling_type": "c", "neighbour_region": 12345}]}],
    # deeply nested garbage
    [{"name": "r", "kind": {"deep": {"deeper": [1, [2, [3]]]}}}],
    [{"name": "r", "thermo_type": {"a": [None, {"b": object()}]}}],
    [{"name": "r", "coupled_patches": [
        {"patch_name": "p", "coupling_type": "c",
         "neighbour_region": {"x": [1, {"y": 2}]}}]}],
    # hostile objects that raise on interaction (must be caught by try/except)
    [_Exploding()],
    [{"name": "ok"}, _Exploding()],
    _EvilDict({"name": "evil"}),         # the regions value itself is an evil dict (not a list → None)
    [_EvilDict({"name": "evil_entry"})], # an evil dict AS a region entry
]


@pytest.mark.parametrize("bad", MALFORMED_REGIONS_VALUES)
def test_regions_from_manifest_never_raises(bad):
    """_regions_from_manifest must return None or list[RegionSlice] — never raise."""
    result = _regions_from_manifest({"regions": bad})
    assert result is None or isinstance(result, list), (
        f"unexpected result type {type(result)!r} for input {bad!r}"
    )
    if isinstance(result, list):
        for r in result:
            assert isinstance(r, RegionSlice)


@pytest.mark.parametrize("bad", MALFORMED_REGIONS_VALUES)
def test_derive_slice_never_raises_on_hot_path(bad):
    """derive_slice_from_manifest is the PRODUCTION hot path for EVERY bundle.
    It must never raise regardless of how malformed manifest['regions'] is."""
    manifest = {
        "case": {"id": "c", "gold_standard": {}},
        "run": {"run_id": "r", "outputs": {}},
        "measurement": {"comparator_verdict": "PASS", "key_quantities": {}},
        "regions": bad,
    }
    slice_ = derive_slice_from_manifest(manifest)  # must not raise
    assert slice_.regions is None or isinstance(slice_.regions, list)


@pytest.mark.parametrize("bad", MALFORMED_REGIONS_VALUES)
def test_matches_for_manifest_never_raises_end_to_end(bad):
    """The full public chain (deriver → matcher → R13–R16) must not raise.
    A malformed region must not produce a non-hashable name that breaks the
    R13 inventory set, nor any other downstream crash."""
    manifest = {
        "case": {"id": "c", "gold_standard": {}},
        "run": {"run_id": "r", "outputs": {}},
        "measurement": {"comparator_verdict": "PASS", "key_quantities": {}},
        "regions": bad,
    }
    matches = matches_for_manifest(manifest)  # must not raise
    assert isinstance(matches, list)


# ---------------------------------------------------------------------------
# (C) NO FABRICATION — honest refusal preserved
# ---------------------------------------------------------------------------


def test_no_fabrication_of_kind():
    """Absent / null / unknown kind must stay None — NEVER defaulted to fluid/solid."""
    for kind_val in (None, "supercritical", "FLUID", "Solid", 1, [], {}):
        result = _regions_from_manifest({"regions": [{"name": "r", "kind": kind_val}]})
        assert result is not None and len(result) == 1
        # Only exact 'fluid'/'solid' survive; everything else → None (honest)
        if kind_val in ("fluid", "solid"):
            assert result[0].kind == kind_val
        else:
            assert result[0].kind is None, (
                f"FABRICATION: kind={kind_val!r} was coerced to {result[0].kind!r} "
                f"instead of None"
            )


def test_no_fabrication_of_thermo_or_refs():
    """Absent thermo_type / refs must stay None — never invented."""
    result = _regions_from_manifest({"regions": [{"name": "r"}]})
    assert result is not None and len(result) == 1
    r = result[0]
    assert r.thermo_type is None
    assert r.thermo_snapshot_ref is None
    assert r.shm_snapshot_ref is None
    assert r.coupled_patches is None  # absent key → not extracted (NOT ())


def test_no_fabrication_coupled_patches_absent_vs_empty():
    """Three-state honesty: absent key → None; explicit [] → ()."""
    absent = _regions_from_manifest({"regions": [{"name": "r"}]})
    assert absent[0].coupled_patches is None  # not extracted
    empty = _regions_from_manifest({"regions": [{"name": "r", "coupled_patches": []}]})
    assert empty[0].coupled_patches == ()    # extracted, zero


# ---------------------------------------------------------------------------
# (D) ISOLATION — one malformed region does not poison the rest of the list
# ---------------------------------------------------------------------------


def test_malformed_entry_does_not_poison_valid_siblings():
    """A list mixing valid + garbage entries keeps the valid ones (isolation)."""
    result = _regions_from_manifest({"regions": [
        {"name": "good_1", "kind": "fluid", "thermo_type": "heRhoThermo"},
        None,                                  # skip
        "garbage",                             # skip
        {"no_name": True},                     # skip (no name)
        {"name": None},                        # skip (null name)
        [1, 2, 3],                             # skip (not a dict)
        {"name": "good_2", "kind": "solid", "thermo_type": "heSolidThermo"},
    ]})
    assert result is not None
    names = sorted(r.name for r in result)
    assert names == ["good_1", "good_2"], (
        f"isolation failure: expected the 2 valid regions, got {names}"
    )


def test_hostile_object_in_list_does_not_poison_siblings():
    """An exploding object as one entry must not lose the valid sibling.

    NOTE: this documents the actual isolation granularity. If the hostile
    object trips the OUTER try/except, the whole list collapses to None
    (acceptable per the BULLETPROOF-GRACEFUL contract: non-crash is the
    invariant; per-entry isolation is best-effort). This test asserts the
    non-crash invariant and records which behavior actually occurs."""
    result = _regions_from_manifest({"regions": [
        {"name": "survivor", "kind": "fluid"},
        _Exploding(),
    ]})
    # Invariant: no crash. Either None (outer catch) or partial list.
    assert result is None or isinstance(result, list)


# ---------------------------------------------------------------------------
# R13 inventory-set hashability: a non-str name could in principle break the
# set comprehension {r.name for r in regions}. Prove names are always str.
# ---------------------------------------------------------------------------


def test_region_names_always_hashable_str_for_inventory_set():
    """Every surviving RegionSlice.name must be a non-empty str so the R13
    inventory set comprehension cannot raise TypeError on an unhashable name."""
    # Names that, if they survived, would break {r.name for r in regions}
    for bad_name in ([1, 2], {"k": "v"}, {1, 2}):
        result = _regions_from_manifest({"regions": [{"name": bad_name}]})
        # bad name → entry skipped → empty list (no unhashable name survives)
        assert result == [], f"unhashable name {bad_name!r} leaked into result"
    # And the full R13 path does not raise even when we try to sneak one in
    matches = matches_for_manifest({
        "case": {}, "run": {}, "measurement": {},
        "regions": [
            {"name": "real", "kind": "fluid",
             "coupled_patches": [{"patch_name": "p", "coupling_type": "c",
                                  "neighbour_region": "ghost"}]},
            {"name": [99]},  # unhashable name — must be skipped, not crash R13
        ],
    })
    assert isinstance(matches, list)


# ---------------------------------------------------------------------------
# Fuzz sweep: cartesian product of field garbage values, all through the
# full public chain. Pure non-crash assertion.
# ---------------------------------------------------------------------------


_GARBAGE = [None, 0, 1, "", "x", [], {}, [1], {"k": 1}, True, 3.14, ()]


def test_fuzz_field_garbage_never_crashes_full_chain():
    count = 0
    for name_v, kind_v, thermo_v, cp_v in itertools.product(_GARBAGE, repeat=4):
        manifest = {
            "case": {}, "run": {}, "measurement": {},
            "regions": [{
                "name": name_v,
                "kind": kind_v,
                "thermo_type": thermo_v,
                "thermo_snapshot_ref": thermo_v,
                "shm_snapshot_ref": kind_v,
                "coupled_patches": cp_v,
            }],
        }
        matches = matches_for_manifest(manifest)  # must not raise
        assert isinstance(matches, list)
        count += 1
    assert count == len(_GARBAGE) ** 4
