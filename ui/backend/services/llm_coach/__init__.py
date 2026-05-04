"""DEC-V61-119 · LLM coaching service.

Composes a governance-aware system prompt from a
:class:`CaseCompletenessReport` (V61-116 output) and project rules,
then hands it to the V61-118 LLM provider for streamed completion.

The package is intentionally tiny — V1 is a single pure function
(:func:`build_coach_system_prompt`) plus a small project-rules
constant. No I/O, no LLM tool calling, no orchestration state.
The complexity lives in the route handler that wires this prompt
into the streamed response.

Public entry point:
    build_coach_system_prompt(report, project_rules=...) -> str
"""
from __future__ import annotations

from ui.backend.services.llm_coach.prompts import (
    DEFAULT_PROJECT_RULES,
    build_coach_system_prompt,
)

__all__ = [
    "DEFAULT_PROJECT_RULES",
    "build_coach_system_prompt",
]
