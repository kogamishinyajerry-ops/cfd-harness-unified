"""Persona library for the B-arc dogfood harness (DEC-V61-164)."""
from scripts.dogfood.personas.assignment import (
    PersonaAssignment,
    PersonaAssignmentError,
    get_assignment,
    list_assignments,
)
from scripts.dogfood.personas.library import (
    Persona,
    PersonaPromptError,
    PersonaRegistryError,
    get_persona,
    list_personas,
    validate_prompt,
)

__all__ = [
    "Persona",
    "PersonaAssignment",
    "PersonaAssignmentError",
    "PersonaPromptError",
    "PersonaRegistryError",
    "get_assignment",
    "get_persona",
    "list_assignments",
    "list_personas",
    "validate_prompt",
]
