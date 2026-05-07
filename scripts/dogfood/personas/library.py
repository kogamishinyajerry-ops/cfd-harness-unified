"""Persona registry — loads system prompts from `prompts/<name>.md`.

Each persona is one of the engineer archetypes from charter
DEC-V61-162 §rationale: novice / experienced_fluent / debug.

The registry validates every loaded prompt against a guardrail
checklist (V130 advisory-only markers, anti-laundering markers,
forbidden-tool markers); a future prompt edit that drops any
required marker fails the test suite immediately.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PERSONA_NAMES: tuple[str, ...] = ("novice", "experienced_fluent", "debug")

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class PersonaRegistryError(KeyError):
    """Raised when an unknown persona name is requested."""


class PersonaPromptError(ValueError):
    """Raised when a persona prompt fails the guardrail validator."""


@dataclass(frozen=True)
class Persona:
    """One persona definition consumed by the dogfood harness."""

    name: str
    system_prompt: str
    description: str


# ---------------------------------------------------------------------------
# Guardrail validation
# ---------------------------------------------------------------------------


# Each entry: (label, list of substrings; ALL must appear)
_GUARDRAILS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("advisor_advisory", ("advisor", "advisory")),
    ("engineer_role", ("engineer", "you")),
    ("forbid_tools", ("do not", "file")),
    ("anti_laundering", ("never explain", "told me")),
    ("offline_continuity", ("llm_available", "rule-based")),
)


def validate_prompt(text: str) -> None:
    """Verify required guardrail substrings appear in the prompt.

    Case-insensitive substring check. Loose-by-design — the harness
    HTTP allowlist (`workbench_tools.WorkbenchToolExecutor`) is the
    actual security boundary; this validator is defense-in-depth so
    a prompt edit cannot silently strip a required marker.
    """
    lowered = text.lower()
    missing: list[str] = []
    for label, substrings in _GUARDRAILS:
        for needle in substrings:
            if needle.lower() not in lowered:
                missing.append(f"{label}:{needle!r}")
                break
    if missing:
        raise PersonaPromptError(
            "persona prompt missing required guardrail markers: "
            + ", ".join(missing)
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_DESCRIPTIONS: dict[str, str] = {
    "novice": (
        "Junior engineer ~2 yrs experience; reads docs carefully; "
        "asks the AI advisor often; surfaces UX/affordance gaps."
    ),
    "experienced_fluent": (
        "12+ yr ANSYS Fluent expert transitioning to OpenFOAM via "
        "this workbench; brings strong Fluent priors; surfaces mismatch."
    ),
    "debug": (
        "Senior debug-mode engineer; residual-trajectory-driven; uses "
        "AI 诊断 heavily but trusts rule-based classifier signal most."
    ),
}


def _load_prompt(name: str) -> str:
    if name not in PERSONA_NAMES:
        raise PersonaRegistryError(
            f"Unknown persona {name!r}; expected one of {PERSONA_NAMES}"
        )
    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise PersonaPromptError(f"persona prompt file missing: {path}")
    text = path.read_text(encoding="utf-8")
    validate_prompt(text)
    return text


def get_persona(name: str) -> Persona:
    """Resolve a persona by name; validates the prompt on every call."""
    prompt = _load_prompt(name)
    return Persona(
        name=name,
        system_prompt=prompt,
        description=_DESCRIPTIONS.get(name, ""),
    )


def list_personas() -> list[Persona]:
    return [get_persona(n) for n in PERSONA_NAMES]


__all__ = [
    "PERSONA_NAMES",
    "Persona",
    "PersonaPromptError",
    "PersonaRegistryError",
    "get_persona",
    "list_personas",
    "validate_prompt",
]
