"""Charter assignment table: case × persona → (family, model_id).

Encodes DEC-V61-162 §rationale 3×3 cross-Cartesian mapping. Each
model family covers all 3 cases × all 3 personas, so any
model-specific blind spot surfaces in ≥3 runs.

Lookup is deterministic; harness aborts on unknown case or persona.
All 9 cells are non-Opus (charter §threat-model echo chamber).
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.dogfood.llm_clients import assert_non_opus
from scripts.dogfood.personas.library import PERSONA_NAMES, PersonaRegistryError

CASE_IDS: tuple[str, ...] = ("naca0012", "backward_step", "pipe_expansion")


class PersonaAssignmentError(KeyError):
    """Raised when (case, persona) does not resolve to a charter cell."""


@dataclass(frozen=True)
class PersonaAssignment:
    """One cell in the charter case × persona × model table."""

    case_id: str
    persona: str
    family: str
    model_id: str


# Charter DEC-V61-162 §rationale table (verbatim)
_TABLE: dict[tuple[str, str], tuple[str, str]] = {
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


def get_assignment(case_id: str, persona: str) -> PersonaAssignment:
    """Resolve (case, persona) to a PersonaAssignment.

    Raises `PersonaAssignmentError` if the cell is not in the charter
    table; raises `OpusPersonaForbidden` (via `assert_non_opus`) if a
    future edit accidentally introduces an Opus model id.
    """
    if case_id not in CASE_IDS:
        raise PersonaAssignmentError(
            f"unknown case {case_id!r}; expected one of {CASE_IDS}"
        )
    if persona not in PERSONA_NAMES:
        raise PersonaRegistryError(
            f"unknown persona {persona!r}; expected one of {PERSONA_NAMES}"
        )
    cell = _TABLE.get((case_id, persona))
    if cell is None:  # pragma: no cover - guarded by membership above
        raise PersonaAssignmentError(
            f"no assignment for ({case_id!r}, {persona!r})"
        )
    family, model_id = cell
    assert_non_opus(model_id)
    return PersonaAssignment(
        case_id=case_id,
        persona=persona,
        family=family,
        model_id=model_id,
    )


def list_assignments() -> list[PersonaAssignment]:
    """All 9 charter cells, in (case, persona) order."""
    out: list[PersonaAssignment] = []
    for case in CASE_IDS:
        for persona in PERSONA_NAMES:
            out.append(get_assignment(case, persona))
    return out


__all__ = [
    "CASE_IDS",
    "PersonaAssignment",
    "PersonaAssignmentError",
    "get_assignment",
    "list_assignments",
]
