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
    ForcesEntry,
    GoldDelta,
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
    return RunArtifactSlice(
        run_id=d["run_id"],
        case_id=d["case_id"],
        success=d["success"],
        exit_code=d["exit_code"],
        residuals=d.get("residuals"),
        forces=forces,
        convergence_stats=convergence_stats,
        gold_delta=gold_delta,
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
