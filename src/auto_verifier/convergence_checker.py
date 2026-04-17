"""Residual-based convergence classification."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List

from .config import THRESHOLDS
from .schemas import ConvergenceReport

_RESIDUAL_RE = re.compile(
    r"Solving for\s+([A-Za-z_]+),\s+Initial residual = ([0-9.eE+-]+),\s+Final residual = ([0-9.eE+-]+)"
)


class ConvergenceChecker:
    """Classify solver convergence from OpenFOAM-style logs."""

    def __init__(self, target_residual: float = THRESHOLDS["TH-2"]) -> None:
        self._target_residual = target_residual

    def check(self, log_file: Path) -> ConvergenceReport:
        warnings: List[str] = []
        if not log_file.exists() or log_file.stat().st_size == 0:
            warnings.append("missing_or_empty_log")
            return ConvergenceReport(
                status="UNKNOWN",
                final_residual=None,
                target_residual=self._target_residual,
                residual_ratio=None,
                warnings=warnings,
            )

        history: List[float] = []
        latest_by_field: Dict[str, float] = {}
        first_initial_residual: float | None = None

        for line in log_file.read_text(encoding="utf-8").splitlines():
            match = _RESIDUAL_RE.search(line)
            if not match:
                continue
            field, initial_str, final_str = match.groups()
            initial = float(initial_str)
            final = float(final_str)
            if first_initial_residual is None:
                first_initial_residual = initial
            history.append(final)
            latest_by_field[field] = final

        if not history:
            warnings.append("unparseable_residual_history")
            return ConvergenceReport(
                status="UNKNOWN",
                final_residual=None,
                target_residual=self._target_residual,
                residual_ratio=None,
                warnings=warnings,
            )

        initial_residual = first_initial_residual if first_initial_residual is not None else history[0]
        final_residual = max(latest_by_field.values()) if latest_by_field else history[-1]
        residual_ratio = final_residual / self._target_residual if self._target_residual else None

        if initial_residual > 0.0 and final_residual > THRESHOLDS["TH-9"] * initial_residual:
            status = "DIVERGED"
        else:
            window = history[-int(THRESHOLDS["TH-4"]):]
            deltas = [window[index] - window[index - 1] for index in range(1, len(window))]
            positive_rebounds = sum(1 for delta in deltas if delta > 0.0)
            oscillation_ratio = positive_rebounds / len(deltas) if deltas else 0.0
            if oscillation_ratio > THRESHOLDS["TH-3"]:
                status = "OSCILLATING"
            elif residual_ratio is not None and residual_ratio <= THRESHOLDS["TH-1"]:
                status = "CONVERGED"
            else:
                status = "UNKNOWN"

        if not math.isfinite(final_residual):
            warnings.append("non_finite_residual")
            status = "DIVERGED"

        return ConvergenceReport(
            status=status,
            final_residual=final_residual,
            target_residual=self._target_residual,
            residual_ratio=residual_ratio,
            warnings=warnings,
        )
