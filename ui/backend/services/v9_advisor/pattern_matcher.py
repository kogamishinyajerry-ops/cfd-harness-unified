"""V91.2 · V9.B Python pattern matcher port.

Python port of `ui/frontend/src/data/advisor_pattern_matcher.ts`. Same
data shape, same predicate semantics, byte-identical commentary output
given the same RunArtifactSlice fixture.

V130 invariant honored BY CONSTRUCTION:
    - Pure function · no I/O · no fetch · no LLM · no subprocess
    - Only stdlib + typing imports
    - Reverse-stop #35: import-allowlist contract test enforces

Cross-language parity (RS#38): the TS matcher and this Python matcher
both load `ui/frontend/src/data/v9_advisor_rules.json` and dispatch
predicates by rule id. The parity test fixture (`__fixtures__/
v9_parity_fixtures.json`) is consumed by BOTH binders to verify they
emit byte-identical MatchedCommentary lists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Literal, Optional, Sequence

Severity = Literal["info", "warn", "advise"]


@dataclass(frozen=True)
class ForcesEntry:
    iteration: int
    Cd: float
    Cl: float
    Cm: float


@dataclass(frozen=True)
class ConvergenceStats:
    final_iter: int
    max_iters_reached: bool
    converged: bool
    elapsed_seconds: float


@dataclass(frozen=True)
class GoldDelta:
    max_abs_pct: float


@dataclass(frozen=True)
class RunArtifactSlice:
    run_id: str
    case_id: str
    success: bool
    exit_code: int
    residuals: Optional[Dict[str, List[float]]] = None
    forces: Optional[List[ForcesEntry]] = None
    convergence_stats: Optional[ConvergenceStats] = None
    gold_delta: Optional[GoldDelta] = None


@dataclass(frozen=True)
class MatchSite:
    matched_at: str


@dataclass(frozen=True)
class AdvisorRule:
    id: str
    severity: Severity
    commentary: str
    provenance: str
    # Pure predicate · returns MatchSite when triggered, None otherwise.
    # MUST NOT have side effects · MUST NOT call fetch/IO/LLM.
    predicate: Callable[[RunArtifactSlice], Optional[MatchSite]]


@dataclass(frozen=True)
class MatchedCommentary:
    rule_id: str
    matched_at: str
    commentary_excerpt: str
    provenance: str
    severity: Severity


_SEVERITY_RANK: Dict[str, int] = {"advise": 0, "warn": 1, "info": 2}


def _excerpt(commentary: str) -> str:
    """Truncate to first 240 chars · matches TS slice(0, 237) + '…'."""
    if len(commentary) > 240:
        return commentary[:237] + "…"  # U+2026 HORIZONTAL ELLIPSIS
    return commentary


def match_advisor_patterns(
    slice_: RunArtifactSlice,
    rules: Sequence[AdvisorRule],
) -> List[MatchedCommentary]:
    """Match a run artifact against the curated ruleset.

    Pure · deterministic · runs in <5ms for typical artifact sizes.
    Predicate exceptions are caught and treated as no-match (V90 carry).
    """
    matched: List[MatchedCommentary] = []

    for rule in rules:
        site: Optional[MatchSite]
        try:
            site = rule.predicate(slice_)
        except Exception:
            # V90 reverse-stop carry: matcher MUST NOT crash on malformed
            # artifact. Treat predicate exceptions as no-match · skip.
            site = None
        if site is None:
            continue

        matched.append(
            MatchedCommentary(
                rule_id=rule.id,
                matched_at=site.matched_at,
                commentary_excerpt=_excerpt(rule.commentary),
                provenance=rule.provenance,
                severity=rule.severity,
            )
        )

    # Stable sort: advise > warn > info, then by rule_id for tie-breaks.
    matched.sort(key=lambda m: (_SEVERITY_RANK[m.severity], m.rule_id))
    return matched


# ---------------------------------------------------------------------------
# Numeric formatting helpers · match JavaScript Number prototype output
# ---------------------------------------------------------------------------

def js_to_fixed(value: float, digits: int) -> str:
    """Mimic JS Number.prototype.toFixed(N) — fixed-point with N digits."""
    return f"{value:.{digits}f}"


def js_to_exponential(value: float, digits: int) -> str:
    """Mimic JS Number.prototype.toExponential(N).

    JS produces e.g. ``"1.23e-5"`` (1-digit exponent, no leading zero).
    Python ``:.2e`` produces ``"1.23e-05"`` (2-digit padded). This helper
    bridges the gap so R7's ``matched_at`` is byte-identical across TS
    and Python bindings (RS#38 cross-language parity).
    """
    s = f"{value:.{digits}e}"
    if "e" not in s:
        return s
    mantissa, exp = s.split("e")
    sign = exp[0] if exp[0] in "+-" else "+"
    digits_part = exp.lstrip("+-").lstrip("0") or "0"
    return f"{mantissa}e{sign}{digits_part}"
