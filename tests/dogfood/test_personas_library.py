"""Tests for scripts/dogfood/personas/library.py."""
from __future__ import annotations

import pytest

from scripts.dogfood.personas.library import (
    PERSONA_NAMES,
    Persona,
    PersonaPromptError,
    PersonaRegistryError,
    get_persona,
    list_personas,
    validate_prompt,
)


def test_persona_names_are_three_charter_archetypes() -> None:
    assert set(PERSONA_NAMES) == {"novice", "experienced_fluent", "debug"}


@pytest.mark.parametrize("name", ["novice", "experienced_fluent", "debug"])
def test_get_persona_loads_prompt(name: str) -> None:
    persona = get_persona(name)
    assert isinstance(persona, Persona)
    assert persona.name == name
    assert len(persona.system_prompt) > 200
    assert persona.description


def test_unknown_persona_raises() -> None:
    with pytest.raises(PersonaRegistryError):
        get_persona("vibes")


def test_list_personas_returns_three() -> None:
    personas = list_personas()
    assert len(personas) == 3
    assert {p.name for p in personas} == set(PERSONA_NAMES)


@pytest.mark.parametrize("name", ["novice", "experienced_fluent", "debug"])
def test_each_persona_prompt_contains_v130_advisory_marker(name: str) -> None:
    text = get_persona(name).system_prompt.lower()
    assert "advisor" in text
    assert "advisory" in text


@pytest.mark.parametrize("name", ["novice", "experienced_fluent", "debug"])
def test_each_persona_prompt_forbids_external_tools(name: str) -> None:
    text = get_persona(name).system_prompt.lower()
    assert "do not invoke any tool other than" in text


@pytest.mark.parametrize("name", ["novice", "experienced_fluent", "debug"])
def test_each_persona_prompt_anti_laundering(name: str) -> None:
    text = get_persona(name).system_prompt.lower()
    assert "never explain" in text
    assert "told me" in text


@pytest.mark.parametrize("name", ["novice", "experienced_fluent", "debug"])
def test_each_persona_prompt_offline_continuity(name: str) -> None:
    text = get_persona(name).system_prompt.lower()
    assert "llm_available" in text
    assert "rule-based" in text


def test_validate_prompt_rejects_missing_advisor_marker() -> None:
    bad = "You are an engineer. Do not read files. Never explain told me. llm_available rule-based"
    with pytest.raises(PersonaPromptError, match="advisor_advisory"):
        validate_prompt(bad)


def test_validate_prompt_rejects_missing_anti_laundering() -> None:
    bad = (
        "You are an engineer. The advisor is advisory. Do not read files. "
        "llm_available rule-based fallback."
    )
    with pytest.raises(PersonaPromptError, match="anti_laundering"):
        validate_prompt(bad)


def test_validate_prompt_rejects_missing_offline_continuity() -> None:
    bad = (
        "You are an engineer. The advisor is advisory. Do not read files. "
        "Never explain told me."
    )
    with pytest.raises(PersonaPromptError, match="offline_continuity"):
        validate_prompt(bad)


def test_validate_prompt_passes_minimal_valid_text() -> None:
    good = (
        "You are an engineer. The advisor is read-only and advisory. "
        "Do not read files or invoke shell. Never explain a mutation as "
        "the advisor told me. If llm_available is false, use rule-based findings."
    )
    validate_prompt(good)
