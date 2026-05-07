"""Tests for scripts/dogfood/case_brief.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dogfood.case_brief import (
    CaseBrief,
    Reference,
    check_verdict,
    load_brief,
)


def _fixture_dict() -> dict:
    return {
        "case_id": "naca0012_re1e6",
        "title": "NACA0012 airfoil at AoA=4°",
        "geometry": "NACA0012, chord=1m",
        "physics": {"regime": "incompressible_steady", "Re": 1_000_000},
        "question": "Compute lift coefficient Cl",
        "reference": {
            "metric": "Cl",
            "value": 0.45,
            "tolerance": 0.05,
            "tolerance_kind": "rel",
            "source": "Abbott & Doenhoff 1959",
        },
        "notes": "Use a C-grid; refine near sharp trailing edge.",
    }


def test_load_brief_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "case.json"
    p.write_text(json.dumps(_fixture_dict()), encoding="utf-8")
    brief = load_brief(p)
    assert brief.case_id == "naca0012_re1e6"
    assert brief.reference.metric == "Cl"
    assert brief.reference.tolerance_kind == "rel"
    assert brief.physics["Re"] == 1_000_000


def test_persona_text_includes_reference_and_question() -> None:
    brief = load_brief_inline(_fixture_dict())
    text = brief.to_persona_text()
    assert "Cl" in text
    assert "0.45" in text
    assert "Abbott & Doenhoff" in text
    assert "lift coefficient" in text


def test_relative_tolerance_pass_within_band() -> None:
    brief = load_brief_inline(_fixture_dict())
    result = check_verdict(brief, observed=0.46)  # +2.2%
    assert result.passed is True
    assert result.observed == 0.46


def test_relative_tolerance_fail_outside_band() -> None:
    brief = load_brief_inline(_fixture_dict())
    result = check_verdict(brief, observed=0.50)  # +11%
    assert result.passed is False
    assert "err=" in result.detail


def test_absolute_tolerance() -> None:
    brief = CaseBrief(
        case_id="x",
        title="abs",
        geometry="cube",
        physics={},
        question="q",
        reference=Reference(
            metric="L",
            value=6.0,
            tolerance=0.6,
            tolerance_kind="abs",
            source="Kim 1980",
        ),
    )
    assert check_verdict(brief, 6.5).passed is True
    assert check_verdict(brief, 7.0).passed is False


def test_observed_none_returns_drop_failure() -> None:
    brief = load_brief_inline(_fixture_dict())
    result = check_verdict(brief, None)
    assert result.passed is False
    assert "did not produce" in result.detail


def test_relative_tolerance_zero_reference_falls_back_to_abs() -> None:
    brief = CaseBrief(
        case_id="z",
        title="zero",
        geometry="g",
        physics={},
        question="q",
        reference=Reference(
            metric="DeltaP",
            value=0.0,
            tolerance=0.01,
            tolerance_kind="rel",
            source="textbook",
        ),
    )
    assert check_verdict(brief, 0.005).passed is True
    assert check_verdict(brief, 0.05).passed is False


def test_load_brief_supplies_default_tolerance_kind(tmp_path: Path) -> None:
    raw = _fixture_dict()
    raw["reference"].pop("tolerance_kind")
    p = tmp_path / "c.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    brief = load_brief(p)
    assert brief.reference.tolerance_kind == "rel"


# helper -------------------------------------------------------------------


def load_brief_inline(d: dict) -> CaseBrief:
    """Build a CaseBrief from a dict without round-tripping through disk."""
    ref = d["reference"]
    return CaseBrief(
        case_id=d["case_id"],
        title=d["title"],
        geometry=d["geometry"],
        physics=d.get("physics", {}),
        question=d["question"],
        reference=Reference(
            metric=ref["metric"],
            value=float(ref["value"]),
            tolerance=float(ref["tolerance"]),
            tolerance_kind=ref.get("tolerance_kind", "rel"),
            source=ref.get("source", ""),
        ),
        notes=d.get("notes", ""),
    )
