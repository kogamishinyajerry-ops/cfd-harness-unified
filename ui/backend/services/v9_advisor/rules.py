"""V91.1 + V91.2 · V9.C ruleset Python binding.

Loads the JSON SSOT at ``ui/frontend/src/data/v9_advisor_rules.json`` and
joins commentary + provenance + severity with Python predicate functions
by rule id. The TS binding at ``ui/frontend/src/data/v9_advisor_rules.ts``
does the analogous join.

V130: this module reads ONE file — the JSON SSOT — at import time. No
network · no subprocess · no other filesystem reads. The predicate
functions are pure (no side effects).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .pattern_matcher import (
    AdvisorRule,
    MatchSite,
    RunArtifactSlice,
    js_to_exponential,
    js_to_fixed,
)

# JSON SSOT location · repo-rooted, both TS and Python read this file.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_JSON_PATH = _REPO_ROOT / "ui" / "frontend" / "src" / "data" / "v9_advisor_rules.json"


# ---------------------------------------------------------------------------
# Predicate helpers (mirror v9_advisor_rules.ts helpers exactly)
# ---------------------------------------------------------------------------

def _recent_residuals(
    slice_: RunArtifactSlice, quantity: str, count: int
) -> List[float]:
    if slice_.residuals is None:
        return []
    history = slice_.residuals.get(quantity)
    if history is None or len(history) < count:
        return []
    return list(history[-count:])


def _is_monotonically_decreasing(values: List[float]) -> bool:
    if len(values) < 2:
        return False
    for i in range(1, len(values)):
        if values[i] >= values[i - 1]:
            return False
    return True


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _is_oscillating(values: List[float], threshold_ratio: float) -> bool:
    if len(values) < 4:
        return False
    mean = sum(values) / len(values)
    mean_mag = abs(mean)
    if mean_mag == 0:
        return False

    sign_flips = 0
    max_amplitude_ratio = 0.0
    for i in range(1, len(values)):
        prev = values[i - 1] - mean
        curr = values[i] - mean
        # Mirror TS: Math.sign(prev) !== Math.sign(curr) && Math.sign(curr) !== 0
        if _sign(prev) != _sign(curr) and _sign(curr) != 0:
            sign_flips += 1
        max_amplitude_ratio = max(
            max_amplitude_ratio,
            abs(values[i] - mean) / mean_mag,
        )
    return sign_flips >= 2 and max_amplitude_ratio > threshold_ratio


# ---------------------------------------------------------------------------
# Predicates (id-keyed · 1:1 with TS PREDICATES_BY_ID)
# ---------------------------------------------------------------------------

def _pred_residual_oscillation_p(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    last8 = _recent_residuals(slice_, "p", 8)
    if len(last8) < 8:
        return None
    if not _is_oscillating(last8, 0.3):
        return None
    final_iter = (
        slice_.convergence_stats.final_iter
        if slice_.convergence_stats is not None
        else len(last8)
    )
    return MatchSite(matched_at=f"iter_{final_iter}_p_residual")


def _pred_max_iters_reached(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None or not slice_.convergence_stats.max_iters_reached:
        return None
    return MatchSite(matched_at="convergence_stats")


def _pred_run_failed_nonzero_exit(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.success is not False:
        return None
    if slice_.exit_code == 0:
        return None
    return MatchSite(matched_at=f"exit_code_{slice_.exit_code}")


def _pred_gold_delta_exceeds_5_pct(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.gold_delta is None:
        return None
    pct = slice_.gold_delta.max_abs_pct
    if pct is None or pct <= 5:
        return None
    return MatchSite(matched_at=f"gold_delta_{js_to_fixed(pct, 2)}pct")


def _pred_forces_not_converged(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    forces = slice_.forces
    if forces is None or len(forces) < 10:
        return None
    last10 = forces[-10:]
    cds = [f.Cd for f in last10]
    cd_mean = sum(cds) / len(cds)
    if abs(cd_mean) < 1e-9:
        return None
    max_drift_pct = max(abs((cd - cd_mean) / cd_mean) for cd in cds) * 100
    if max_drift_pct <= 1:
        return None
    return MatchSite(matched_at=f"forces_drift_{js_to_fixed(max_drift_pct, 2)}pct")


def _pred_slow_convergence(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None:
        return None
    if not slice_.convergence_stats.converged:
        return None
    final = slice_.convergence_stats.final_iter
    if final < 5000:
        return None
    return MatchSite(matched_at=f"iter_{final}_slow_converge")


def _pred_residual_plateau_u(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    last20 = _recent_residuals(slice_, "U", 20)
    if len(last20) < 20:
        return None
    mean = sum(last20) / len(last20)
    mean_mag = abs(mean)
    if mean_mag < 1e-12:
        return None
    variance = sum((v - mean) ** 2 for v in last20) / len(last20)
    std_dev = math.sqrt(variance)
    variation_pct = (std_dev / mean_mag) * 100
    if variation_pct >= 2 or mean_mag < 1e-4:
        return None
    return MatchSite(matched_at=f"U_plateau_{js_to_exponential(mean_mag, 2)}")


def _pred_healthy_convergence(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None or not slice_.convergence_stats.converged:
        return None
    last8 = _recent_residuals(slice_, "p", 8)
    if len(last8) < 8:
        return None
    if not _is_monotonically_decreasing(last8):
        return None
    return MatchSite(matched_at="healthy_convergence_p")


_PREDICATES_BY_ID: Dict[str, Callable[[RunArtifactSlice], Optional[MatchSite]]] = {
    "RESIDUAL_OSCILLATION_P_V9_R1": _pred_residual_oscillation_p,
    "MAX_ITERS_REACHED_V9_R2": _pred_max_iters_reached,
    "RUN_FAILED_NONZERO_EXIT_V9_R3": _pred_run_failed_nonzero_exit,
    "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4": _pred_gold_delta_exceeds_5_pct,
    "FORCES_NOT_CONVERGED_V9_R5": _pred_forces_not_converged,
    "SLOW_CONVERGENCE_V9_R6": _pred_slow_convergence,
    "RESIDUAL_PLATEAU_U_V9_R7": _pred_residual_plateau_u,
    "HEALTHY_CONVERGENCE_V9_R8": _pred_healthy_convergence,
}


# ---------------------------------------------------------------------------
# Rule loader — joins JSON SSOT data with predicates
# ---------------------------------------------------------------------------

def _load_corpus() -> Tuple[str, List[AdvisorRule]]:
    text = _JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(text)
    version = data["version"]
    rules: List[AdvisorRule] = []
    for r in data["rules"]:
        pid = r["id"]
        predicate = _PREDICATES_BY_ID.get(pid)
        if predicate is None:
            raise RuntimeError(
                f"V91.1 join error: JSON rule id {pid!r} has no matching Python predicate"
            )
        if not r["provenance"]:
            raise RuntimeError(f"V90 RS#32: rule {pid!r} has empty provenance")
        rules.append(
            AdvisorRule(
                id=pid,
                severity=r["severity"],
                commentary=r["commentary"],
                provenance=r["provenance"],
                predicate=predicate,
            )
        )
    return version, rules


V9_RULESET_VERSION, V9_ADVISOR_RULES = _load_corpus()
