"""Tests for scripts/dogfood/cases — briefs + STL fixtures + reference values."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.dogfood.case_brief import check_verdict, load_brief
from scripts.dogfood.cases import (
    CASE_IDS,
    GENERATORS,
    brief_path,
    parse_stl_facet_count,
    regenerate_all,
    stl_path,
)


# ---------------------------------------------------------------------------
# Briefs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_brief_loads_for_each_case(case_id: str) -> None:
    brief = load_brief(brief_path(case_id))
    assert brief.case_id == case_id
    assert brief.title
    assert brief.geometry
    assert brief.question
    assert brief.reference.metric
    assert brief.reference.source


def test_naca0012_reference_matches_charter() -> None:
    brief = load_brief(brief_path("naca0012"))
    assert brief.reference.metric == "Cl"
    assert brief.reference.value == pytest.approx(0.44)
    assert brief.reference.tolerance == pytest.approx(0.05)
    assert brief.reference.tolerance_kind == "rel"
    assert "Abbott" in brief.reference.source


def test_backward_step_reference_matches_charter() -> None:
    brief = load_brief(brief_path("backward_step"))
    assert brief.reference.metric == "L_over_h"
    assert brief.reference.value == pytest.approx(6.0)
    assert brief.reference.tolerance == pytest.approx(0.10)
    assert "Kim" in brief.reference.source


def test_pipe_expansion_reference_matches_charter() -> None:
    brief = load_brief(brief_path("pipe_expansion"))
    assert brief.reference.metric == "Kp"
    assert brief.reference.value == pytest.approx(0.5625)
    assert brief.reference.tolerance == pytest.approx(0.05)
    assert "White" in brief.reference.source


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_brief_persona_text_includes_metric_and_question(case_id: str) -> None:
    brief = load_brief(brief_path(case_id))
    text = brief.to_persona_text()
    assert brief.reference.metric in text
    assert brief.question.split(".")[0] in text


# ---------------------------------------------------------------------------
# Verdict boundary behavior
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_verdict_passes_at_reference_value(case_id: str) -> None:
    brief = load_brief(brief_path(case_id))
    result = check_verdict(brief, observed=brief.reference.value)
    assert result.passed is True


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_verdict_fails_at_one_point_five_x_tolerance(case_id: str) -> None:
    brief = load_brief(brief_path(case_id))
    bad = brief.reference.value * (1.0 + 1.5 * brief.reference.tolerance)
    result = check_verdict(brief, observed=bad)
    assert result.passed is False


# ---------------------------------------------------------------------------
# STL fixtures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_stl_fixture_exists_and_parses(case_id: str) -> None:
    text = stl_path(case_id).read_text(encoding="utf-8")
    assert text.startswith(f"solid {case_id}")
    assert text.rstrip().endswith(f"endsolid {case_id}")
    facets = parse_stl_facet_count(text)
    assert facets >= 12  # smallest fixture (BFS) has ≥ 12 facets


def test_naca0012_facet_count() -> None:
    text = stl_path("naca0012").read_text(encoding="utf-8")
    assert parse_stl_facet_count(text) == 240


def test_backward_step_facet_count() -> None:
    text = stl_path("backward_step").read_text(encoding="utf-8")
    assert parse_stl_facet_count(text) == 20


def test_pipe_expansion_facet_count() -> None:
    text = stl_path("pipe_expansion").read_text(encoding="utf-8")
    assert parse_stl_facet_count(text) == 128


# ---------------------------------------------------------------------------
# Determinism: regenerate matches committed bytes
# ---------------------------------------------------------------------------


def test_geometry_generators_are_deterministic(tmp_path: Path) -> None:
    counts = regenerate_all(tmp_path)
    assert set(counts) == set(CASE_IDS)
    for case_id in CASE_IDS:
        regenerated = (tmp_path / f"{case_id}.stl").read_text(encoding="utf-8")
        committed = stl_path(case_id).read_text(encoding="utf-8")
        assert regenerated == committed, (
            f"{case_id}: regenerated STL differs from committed fixture; "
            "run `python -m scripts.dogfood.cases.geometry_generators` and re-commit."
        )


def test_generators_dict_matches_case_ids() -> None:
    assert set(GENERATORS) == set(CASE_IDS)


# ---------------------------------------------------------------------------
# Brief × STL alignment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_brief_case_id_matches_stl_filename(case_id: str) -> None:
    brief = load_brief(brief_path(case_id))
    assert brief.case_id == case_id
    assert stl_path(case_id).name == f"{case_id}.stl"


# ---------------------------------------------------------------------------
# JSON safety: brief refs are floats not formulas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_brief_reference_value_is_numeric_literal(case_id: str) -> None:
    raw = json.loads(brief_path(case_id).read_text(encoding="utf-8"))
    assert isinstance(raw["reference"]["value"], (int, float))
    assert isinstance(raw["reference"]["tolerance"], (int, float))
