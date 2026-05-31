"""RED-TEAM regression · W3.0.6 RunArtifactSlice JSON round-trip fidelity.

The existing W3.0.6 contract tests (test_run_artifact_slice_multi_region.py)
assert that ``dataclasses.asdict`` preserves ``coupled_patches`` as a *tuple*
(e.g. test_asdict_round_trip line 217, test_tuple_round_trips_in_asdict
line 500). That property holds for the in-memory ``asdict`` output, but the
ONLY persistence/transport path in this subsystem is canonical JSON
(src.audit_package.serialize._canonical_json). JSON has no tuple type, so a
tuple becomes a list across that boundary.

These tests pin down the TRUE invariant: the project's own _canonical_json
flattens the tuple to a list, AND the _hydrate / _reconstruct path must
re-wrap it into a tuple so the reconstructed slice is == the original.
This guards against a future W3.1 wiring that persists regions through JSON
and then naively compares container types (which the misleading
isinstance(..., tuple) assertions in the contract file would suggest is safe).
"""

from __future__ import annotations

import dataclasses
import json

from src.audit_package.serialize import _canonical_json
from ui.backend.services.v9_advisor.pattern_matcher import (
    CoupledPatch,
    RegionSlice,
    RunArtifactSlice,
)


def _reconstruct(d):
    regions = None
    if d.get("regions") is not None:
        regions = []
        for r in d["regions"]:
            cps = None
            if r.get("coupled_patches") is not None:
                cps = tuple(CoupledPatch(**cp) for cp in r["coupled_patches"])
            regions.append(
                RegionSlice(
                    name=r["name"],
                    kind=r["kind"],
                    thermo_type=r.get("thermo_type"),
                    coupled_patches=cps,
                    shm_snapshot_ref=r.get("shm_snapshot_ref"),
                    thermo_snapshot_ref=r.get("thermo_snapshot_ref"),
                )
            )
    return RunArtifactSlice(
        run_id=d["run_id"], case_id=d["case_id"], success=d["success"],
        exit_code=d["exit_code"], regions=regions,
    )


def _slice():
    return RunArtifactSlice(
        run_id="R", case_id="case_011", success=True, exit_code=0,
        regions=[
            RegionSlice(
                name="aluminum", kind="solid",
                thermo_type="heSolidThermo",
                coupled_patches=(
                    CoupledPatch("al_to_hot", "compressible::turbulentTemperatureCoupledBaffleMixed", "air_hot"),
                    CoupledPatch("al_to_cold", "compressible::turbulentTemperatureCoupledBaffleMixed", "air_cold"),
                ),
            ),
        ],
    )


def test_canonical_json_flattens_coupled_patches_tuple_to_list():
    """The project's OWN serializer turns the tuple into a JSON list — the
    in-memory asdict tuple-preservation property does NOT survive transport."""
    d = dataclasses.asdict(_slice())
    raw = _canonical_json(d)            # what would land in the audit zip
    back = json.loads(raw.decode("utf-8"))
    cps = back["regions"][0]["coupled_patches"]
    assert isinstance(cps, list), "JSON has no tuple type; expected list after canonical-json round-trip"
    assert not isinstance(cps, tuple)
    assert len(cps) == 2


def test_reconstruct_after_json_rewraps_to_tuple_and_equals_original():
    """Lossless end-to-end only because _reconstruct re-wraps list→tuple.
    If a future hydrate path drops the tuple() wrap, this fails."""
    orig = _slice()
    back = json.loads(_canonical_json(dataclasses.asdict(orig)).decode("utf-8"))
    rebuilt = _reconstruct(back)
    assert isinstance(rebuilt.regions[0].coupled_patches, tuple)
    assert rebuilt == orig


def test_none_vs_empty_vs_populated_survive_canonical_json():
    """Presence-vs-payload three-state must survive the actual JSON path,
    not just in-memory asdict."""
    states = {
        "none": RunArtifactSlice("R", "c", True, 0),
        "empty": RunArtifactSlice("R", "c", True, 0, regions=[]),
        "populated": RunArtifactSlice("R", "c", True, 0, regions=[RegionSlice("f", "fluid")]),
    }
    decoded = {
        k: json.loads(_canonical_json(dataclasses.asdict(v)).decode("utf-8"))["regions"]
        for k, v in states.items()
    }
    assert decoded["none"] is None
    assert decoded["empty"] == []
    assert decoded["populated"] is not None and len(decoded["populated"]) == 1
    # The three are mutually distinct after JSON
    assert decoded["none"] != decoded["empty"]
    assert decoded["empty"] != decoded["populated"]
