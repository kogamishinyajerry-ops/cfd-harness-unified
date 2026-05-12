"""Tests for scripts/dogfood/personas/assignment.py — charter table."""
from __future__ import annotations

import pytest

from scripts.dogfood.llm_clients import OpusPersonaForbidden, assert_non_opus
from scripts.dogfood.personas.assignment import (
    CASE_IDS,
    PersonaAssignment,
    PersonaAssignmentError,
    get_assignment,
    list_assignments,
)
from scripts.dogfood.personas.library import PERSONA_NAMES, PersonaRegistryError


# ---------------------------------------------------------------------------
# Charter table verbatim verification
# ---------------------------------------------------------------------------


_CHARTER_TABLE = {
    ("naca0012", "novice"): ("anthropic", "claude-sonnet-4-6"),
    ("naca0012", "experienced_fluent"): ("deepseek", "deepseek-chat"),
    ("naca0012", "debug"): ("openai_compat", "gpt-5.4"),
    ("backward_step", "novice"): ("deepseek", "deepseek-chat"),
    ("backward_step", "experienced_fluent"): ("openai_compat", "gpt-5.4"),
    ("backward_step", "debug"): ("anthropic", "claude-sonnet-4-6"),
    ("pipe_expansion", "novice"): ("openai_compat", "gpt-5.4"),
    ("pipe_expansion", "experienced_fluent"): ("anthropic", "claude-sonnet-4-6"),
    ("pipe_expansion", "debug"): ("deepseek", "deepseek-chat"),
}


@pytest.mark.parametrize("cell", sorted(_CHARTER_TABLE.items()))
def test_each_charter_cell_resolves(cell: tuple[tuple[str, str], tuple[str, str]]) -> None:
    (case_id, persona), (family, model_id) = cell
    assignment = get_assignment(case_id, persona)
    assert isinstance(assignment, PersonaAssignment)
    assert assignment.case_id == case_id
    assert assignment.persona == persona
    assert assignment.family == family
    assert assignment.model_id == model_id


def test_list_assignments_yields_nine_unique_cells() -> None:
    cells = list_assignments()
    assert len(cells) == 9
    keys = {(c.case_id, c.persona) for c in cells}
    assert keys == set(_CHARTER_TABLE.keys())


def test_each_model_family_covers_all_three_cases_and_personas() -> None:
    """Cross-Cartesian property — charter §rationale: any model-specific
    blind spot surfaces in ≥3 runs."""
    family_cases: dict[str, set[str]] = {}
    family_personas: dict[str, set[str]] = {}
    for c in list_assignments():
        family_cases.setdefault(c.family, set()).add(c.case_id)
        family_personas.setdefault(c.family, set()).add(c.persona)
    assert set(family_cases) == {"anthropic", "deepseek", "openai_compat"}
    for family, cases in family_cases.items():
        assert cases == set(CASE_IDS), f"family {family} missing case coverage"
    for family, personas in family_personas.items():
        assert personas == set(PERSONA_NAMES), (
            f"family {family} missing persona coverage"
        )


def test_all_nine_cells_are_non_opus() -> None:
    for cell in list_assignments():
        # Should not raise
        assert_non_opus(cell.model_id)


def test_unknown_case_raises() -> None:
    with pytest.raises(PersonaAssignmentError):
        get_assignment("ldc_cube", "novice")


def test_unknown_persona_raises() -> None:
    with pytest.raises(PersonaRegistryError):
        get_assignment("naca0012", "vibes")


def test_table_size_is_three_by_three() -> None:
    assert len(CASE_IDS) == 3
    assert len(PERSONA_NAMES) == 3
    assert len(list_assignments()) == 9


def test_get_assignment_would_reject_opus_if_table_were_corrupted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense-in-depth: assert_non_opus runs on every lookup so a future
    table edit accidentally introducing an Opus model fails immediately."""
    from scripts.dogfood.personas import assignment as mod

    bad_table = dict(mod._TABLE)
    bad_table[("naca0012", "novice")] = ("anthropic", "claude-opus-4-7")
    monkeypatch.setattr(mod, "_TABLE", bad_table)
    with pytest.raises(OpusPersonaForbidden):
        mod.get_assignment("naca0012", "novice")
