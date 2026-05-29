"""V91.2 RS#38 · Cross-language parity test (Python side).

Loads the frozen fixture at `ui/frontend/src/data/__fixtures__/
v9_parity_fixtures.json` and asserts the Python matcher produces
byte-identical output. A TS test at `ui/frontend/src/data/__tests__/
v9_cross_language_parity.contract.test.ts` does the same on the TS side.
If both pass, both bindings produce identical MatchedCommentary output
given identical input slices.

This is the V91 RS#38 enforcement point.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ui.backend.services.v9_advisor import (
    ConvergenceStats,
    DevelopedRegionGoldDelta,
    ForcesEntry,
    GoldDelta,
    IntegratedDragPct,
    ReferenceBandSummary,
    RunArtifactSlice,
    V9_ADVISOR_RULES,
    match_advisor_patterns,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "ui/frontend/src/data/__fixtures__/v9_parity_fixtures.json"


def _hydrate_slice(d: Dict[str, Any]) -> RunArtifactSlice:
    """Reverse of dataclasses.asdict — rebuild typed slice from dict."""
    forces = None
    if d.get("forces") is not None:
        forces = [ForcesEntry(**f) for f in d["forces"]]
    convergence_stats = None
    if d.get("convergence_stats") is not None:
        convergence_stats = ConvergenceStats(**d["convergence_stats"])
    gold_delta = None
    if d.get("gold_delta") is not None:
        gold_delta = GoldDelta(**d["gold_delta"])
    # W2.0.6 · DEC-V61-209 NASA-convention regional structured fields.
    # Each field is None when absent OR explicitly null in fixture JSON
    # (per_point gate cases) — only the nasa_integrated fixture populates
    # all three. _hydrate_slice pipes them through so a round-trip
    # dataclasses.asdict(slice) byte-equals the fixture dict.
    developed_region_gold_delta = None
    if d.get("developed_region_gold_delta") is not None:
        developed_region_gold_delta = DevelopedRegionGoldDelta(**d["developed_region_gold_delta"])
    integrated_drag_pct = None
    if d.get("integrated_drag_pct") is not None:
        integrated_drag_pct = IntegratedDragPct(**d["integrated_drag_pct"])
    reference_comparison_band_summary = None
    if d.get("reference_comparison_band_summary") is not None:
        reference_comparison_band_summary = ReferenceBandSummary(
            **d["reference_comparison_band_summary"]
        )
    return RunArtifactSlice(
        run_id=d["run_id"],
        case_id=d["case_id"],
        success=d["success"],
        exit_code=d["exit_code"],
        residuals=d.get("residuals"),
        forces=forces,
        convergence_stats=convergence_stats,
        gold_delta=gold_delta,
        developed_region_gold_delta=developed_region_gold_delta,
        integrated_drag_pct=integrated_drag_pct,
        reference_comparison_band_summary=reference_comparison_band_summary,
    )


def _load_fixtures() -> List[Dict[str, Any]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["fixtures"]


@pytest.mark.parametrize("fx", _load_fixtures(), ids=lambda fx: fx["name"])
def test_python_matcher_reproduces_fixture(fx):
    """Python matcher output must equal expected_matches byte-identically."""
    slice_ = _hydrate_slice(fx["slice"])
    expected = fx["expected_matches"]
    actual = [dataclasses.asdict(m) for m in match_advisor_patterns(slice_, V9_ADVISOR_RULES)]
    assert actual == expected, (
        f"V91 RS#38 parity break on {fx['name']!r}:\n"
        f"  expected: {expected}\n  actual: {actual}"
    )


def test_fixture_file_canonical():
    """RS#37: parity fixture file itself must be canonical."""
    raw = FIXTURE_PATH.read_text(encoding="utf-8")
    expected = json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    assert raw == expected


def test_fixture_covers_all_rules():
    """Every V9 rule must appear in at least one fixture."""
    fixtures = _load_fixtures()
    all_matched_rule_ids = set()
    for fx in fixtures:
        for m in fx["expected_matches"]:
            all_matched_rule_ids.add(m["rule_id"])
    rule_ids = {r.id for r in V9_ADVISOR_RULES}
    missing = rule_ids - all_matched_rule_ids
    assert not missing, (
        f"V91.2 parity fixtures incomplete · missing rules: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# W2.0.6 · DEC-V61-209 NASA-convention slice extension parity
# ---------------------------------------------------------------------------


def test_hydrate_slice_pipes_new_fields_through():
    """W2.0.6: _hydrate_slice must round-trip the three new structured fields
    through the dataclass constructor — the dec209_known_deviation_pattern
    fixture exercises the populated path; all three fields' nested dicts
    must byte-equal the fixture dict via dataclasses.asdict.
    """
    fixtures = {fx["name"]: fx for fx in _load_fixtures()}
    assert "dec209_known_deviation_pattern" in fixtures, (
        "W2.0.6: dec209_known_deviation_pattern fixture must exist"
    )
    fx = fixtures["dec209_known_deviation_pattern"]
    slice_ = _hydrate_slice(fx["slice"])

    # All three new fields must round-trip cleanly via dataclasses.asdict.
    assert slice_.developed_region_gold_delta is not None
    assert slice_.integrated_drag_pct is not None
    assert slice_.reference_comparison_band_summary is not None

    assert dataclasses.asdict(slice_.developed_region_gold_delta) == (
        fx["slice"]["developed_region_gold_delta"]
    )
    assert dataclasses.asdict(slice_.integrated_drag_pct) == (
        fx["slice"]["integrated_drag_pct"]
    )
    assert dataclasses.asdict(slice_.reference_comparison_band_summary) == (
        fx["slice"]["reference_comparison_band_summary"]
    )


def test_per_point_fixture_leaves_new_fields_none():
    """W2.0.6: per_point gate fixture must hydrate to None for all three new
    fields (graceful scope-out, not partial). Pins the data-shape contract
    so a future hydration regression that defaulted to {} instead of None
    would surface here."""
    fixtures = {fx["name"]: fx for fx in _load_fixtures()}
    assert "dec209_developed_region_clean_per_point_mode" in fixtures
    fx = fixtures["dec209_developed_region_clean_per_point_mode"]
    slice_ = _hydrate_slice(fx["slice"])
    assert slice_.developed_region_gold_delta is None
    assert slice_.integrated_drag_pct is None
    assert slice_.reference_comparison_band_summary is None
