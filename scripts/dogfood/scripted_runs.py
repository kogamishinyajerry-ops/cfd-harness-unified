"""Scripted mock-LLM responses per (case, persona) cell.

Each script is a list of `AssistantMessage` returned in order by a
`ScriptedMockClient`. They simulate plausible persona behavior: a
few advisor queries, some Step 1-4 mutation calls (with rationale
text matching persona voice), then a `submit_verdict` or
`submit_drop`.

Used by orchestrator's `--dry-run` mode and by `tests/dogfood/`
to validate the orchestration without burning API budget.
"""
from __future__ import annotations

from typing import Callable

from scripts.dogfood.llm_clients import AssistantMessage, ToolCall

ScriptBuilder = Callable[[], list[AssistantMessage]]


def _msg(text: str, *tool_calls: ToolCall, in_tokens: int = 100, out_tokens: int = 30) -> AssistantMessage:
    return AssistantMessage(
        text=text,
        tool_calls=tuple(tool_calls),
        raw_usage={"input_tokens": in_tokens, "output_tokens": out_tokens},
    )


def _verdict(value: float, rationale: str) -> ToolCall:
    return ToolCall(
        call_id="verdict",
        tool_name="submit_verdict",
        arguments={"observed_value": value, "rationale": rationale},
    )


def _drop(reason: str) -> ToolCall:
    return ToolCall(
        call_id="drop",
        tool_name="submit_drop",
        arguments={"reason": reason},
    )


def _get(case_id: str, suffix: str, rationale: str, idx: int = 0) -> ToolCall:
    return ToolCall(
        call_id=f"get_{idx}",
        tool_name="http_get",
        arguments={
            "url": f"/api/cases/{case_id}/{suffix}",
            "rationale": rationale,
        },
    )


# ---------------------------------------------------------------------------
# Per-cell scripts
# ---------------------------------------------------------------------------


def _naca0012_novice() -> list[AssistantMessage]:
    """Novice on NACA0012: asks advisor multiple times, lands close."""
    return [
        _msg(
            "Starting by checking case state.",
            _get("naca0012", "state", "verify case is reachable", 1),
        ),
        _msg(
            "Asking advisor for review before mesh.",
            _get(
                "naca0012",
                "ai-review",
                "novice user — want to know what to do next",
                2,
            ),
        ),
        _msg(
            "Querying diagnose advisor for solver hints.",
            _get(
                "naca0012",
                "ai-diagnose",
                "want a starting hypothesis from rule-based",
                3,
            ),
        ),
        _msg(
            "Submitting Cl=0.42 based on solver output.",
            _verdict(0.42, "computed Cl from surface integration; novice judgment"),
        ),
    ]


def _naca0012_experienced_fluent() -> list[AssistantMessage]:
    """Experienced Fluent: drives confidently, hits Cl right at reference."""
    return [
        _msg(
            "Routine external aero. Re=1e6 fully turbulent, k-omega-SST.",
            _get("naca0012", "state", "orient", 1),
        ),
        _msg(
            "Lone advisor check before solver.",
            _get(
                "naca0012",
                "ai-review",
                "Fluent prior on this regime; sanity-check workbench expectations",
                2,
            ),
        ),
        _msg(
            "Submitting verdict.",
            _verdict(0.44, "k-omega-SST RANS converged; matches my Fluent prior"),
        ),
    ]


def _naca0012_debug() -> list[AssistantMessage]:
    """Debug: methodical, watches residuals, lands within tolerance."""
    return [
        _msg(
            "Checking initial state.",
            _get("naca0012", "state", "always orient first", 1),
        ),
        _msg(
            "Reading review for any mesh issues.",
            _get("naca0012", "ai-review", "audit before solver start", 2),
        ),
        _msg(
            "Querying diagnose for residual baseline.",
            _get(
                "naca0012",
                "ai-diagnose?problem=stalled_residuals",
                "establish residual classifier baseline",
                3,
            ),
        ),
        _msg(
            "Re-checking review post-solver.",
            _get("naca0012", "ai-review", "post-converge sanity", 4),
        ),
        _msg(
            "Submitting Cl with residuals at 1e-5.",
            _verdict(
                0.43,
                "U-residual monotonic to 5e-6; Cl integration converged; per residual_diagnostics chunk",
            ),
        ),
    ]


def _backward_step_novice() -> list[AssistantMessage]:
    """Novice on BFS: advisor-heavy, lands within tolerance."""
    return [
        _msg(
            "Reading state.",
            _get("backward_step", "state", "orient", 1),
        ),
        _msg(
            "Asking review for setup guidance.",
            _get("backward_step", "ai-review", "what does workbench want here", 2),
        ),
        _msg(
            "Submitting reattachment length.",
            _verdict(5.7, "post-processing showed wall shear sign change at L/h≈5.7"),
        ),
    ]


def _backward_step_experienced_fluent() -> list[AssistantMessage]:
    """Experienced: terse, drops quickly if BFS turbulence model surprises them."""
    return [
        _msg(
            "Standard recirculation case.",
            _get("backward_step", "state", "orient", 1),
        ),
        _msg(
            "Submitting L/h.",
            _verdict(6.1, "k-omega-SST steady RANS; matches Kim 1980 mid-range"),
        ),
    ]


def _backward_step_debug() -> list[AssistantMessage]:
    """Debug: residual oscillation noted, gets close to reference."""
    return [
        _msg(
            "State first.",
            _get("backward_step", "state", "orient", 1),
        ),
        _msg(
            "Diagnose for wake oscillation.",
            _get(
                "backward_step",
                "ai-diagnose?problem=stalled_residuals",
                "BFS wake known to oscillate; check classifier signal",
                2,
            ),
        ),
        _msg(
            "Re-reviewing post-converge.",
            _get("backward_step", "ai-review", "audit final state", 3),
        ),
        _msg(
            "Submitting reattachment.",
            _verdict(5.9, "wall shear sign change at L/h=5.9; residuals oscillate ±2% but mean stable"),
        ),
    ]


def _pipe_expansion_novice() -> list[AssistantMessage]:
    """Novice on pipe expansion: drops because axisymmetric BC unfamiliar."""
    return [
        _msg(
            "State check.",
            _get("pipe_expansion", "state", "orient", 1),
        ),
        _msg(
            "Reading review for axisymmetric setup help.",
            _get(
                "pipe_expansion",
                "ai-review",
                "novice — confused about axisymmetric vs full-3D",
                2,
            ),
        ),
        _msg(
            "Asking diagnose for stalled solver.",
            _get(
                "pipe_expansion",
                "ai-diagnose",
                "convergence not happening, want hint",
                3,
            ),
        ),
        _msg(
            "Dropping — couldn't get past BC step.",
            _drop("axisymmetric BC type unclear from corpus; need more guidance"),
        ),
    ]


def _pipe_expansion_experienced_fluent() -> list[AssistantMessage]:
    """Experienced: lands close, mild Fluent-prior friction."""
    return [
        _msg(
            "Borda-Carnot expected ~0.56.",
            _get("pipe_expansion", "state", "orient", 1),
        ),
        _msg(
            "Single review check.",
            _get(
                "pipe_expansion",
                "ai-review",
                "workbench BC nomenclature unfamiliar — verify mapping",
                2,
            ),
        ),
        _msg(
            "Submitting Kp.",
            _verdict(
                0.56,
                "p_recovery measured 8 diameters downstream; matches Borda-Carnot",
            ),
        ),
    ]


def _pipe_expansion_debug() -> list[AssistantMessage]:
    """Debug: methodical, lands at reference."""
    return [
        _msg(
            "State.",
            _get("pipe_expansion", "state", "orient", 1),
        ),
        _msg(
            "Review pre-solver.",
            _get("pipe_expansion", "ai-review", "BC and mesh audit", 2),
        ),
        _msg(
            "Diagnose check post-solver.",
            _get(
                "pipe_expansion",
                "ai-diagnose?problem=stalled_residuals",
                "verify solver converged cleanly",
                3,
            ),
        ),
        _msg(
            "Submitting Kp.",
            _verdict(
                0.5625,
                "pressure differential settled by x/D=8; matches White §6.10 closed-form",
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_SCRIPTS: dict[tuple[str, str], ScriptBuilder] = {
    ("naca0012", "novice"): _naca0012_novice,
    ("naca0012", "experienced_fluent"): _naca0012_experienced_fluent,
    ("naca0012", "debug"): _naca0012_debug,
    ("backward_step", "novice"): _backward_step_novice,
    ("backward_step", "experienced_fluent"): _backward_step_experienced_fluent,
    ("backward_step", "debug"): _backward_step_debug,
    ("pipe_expansion", "novice"): _pipe_expansion_novice,
    ("pipe_expansion", "experienced_fluent"): _pipe_expansion_experienced_fluent,
    ("pipe_expansion", "debug"): _pipe_expansion_debug,
}


def get_script(case_id: str, persona: str) -> list[AssistantMessage]:
    """Resolve scripted mock LLM responses for a (case, persona) cell."""
    builder = _SCRIPTS.get((case_id, persona))
    if builder is None:
        raise KeyError(f"no scripted run for ({case_id!r}, {persona!r})")
    return builder()


def list_cells() -> list[tuple[str, str]]:
    return sorted(_SCRIPTS.keys())


__all__ = ["get_script", "list_cells"]
