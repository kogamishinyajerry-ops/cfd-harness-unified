"""Simple physical-plausibility checks for AutoVerifier."""

from __future__ import annotations

import math
from typing import Any, Dict, cast

from .config import THRESHOLDS
from .schemas import PhysicsCheck


class PhysicsChecker:
    """Validate conservation and numeric sanity without mutating execution artifacts."""

    def check(self, sim_results: Dict[str, Any]) -> PhysicsCheck:
        warnings = []
        status = "PASS"

        mass_in = sim_results.get("mass_flow_in")
        mass_out = sim_results.get("mass_flow_out")
        if self._finite(mass_in) and self._finite(mass_out):
            mass_in_value = float(cast(float, mass_in))
            mass_out_value = float(cast(float, mass_out))
            if abs(mass_in_value) > 0.0:
                imbalance = abs(mass_in_value - mass_out_value) / abs(mass_in_value)
            else:
                imbalance = float("inf")
            if imbalance <= THRESHOLDS["TH-7-pass"]:
                pass
            elif imbalance <= THRESHOLDS["TH-7-warn"]:
                status = "WARN"
                warnings.append("mass_imbalance_warning")
            else:
                status = "FAIL"
                warnings.append("mass_imbalance_failure")
        else:
            status = "WARN"
            warnings.append("missing_boundary_evidence")

        if self._has_non_finite(sim_results):
            status = "FAIL"
            warnings.append("non_finite_simulation_value")

        if self._has_unreasonable_scale(sim_results):
            if status == "PASS":
                status = "WARN"
            warnings.append("order_of_magnitude_warning")

        return PhysicsCheck(status=status, warnings=warnings)

    def _has_non_finite(self, value: Any) -> bool:
        if isinstance(value, dict):
            return any(self._has_non_finite(item) for item in value.values())
        if isinstance(value, list):
            return any(self._has_non_finite(item) for item in value)
        if isinstance(value, (int, float)):
            return not math.isfinite(value)
        return False

    def _has_unreasonable_scale(self, value: Any) -> bool:
        if isinstance(value, dict):
            return any(self._has_unreasonable_scale(item) for item in value.values())
        if isinstance(value, list):
            return any(self._has_unreasonable_scale(item) for item in value)
        if isinstance(value, (int, float)):
            return abs(float(value)) > 1e9
        return False

    @staticmethod
    def _finite(value: Any) -> bool:
        return isinstance(value, (int, float)) and math.isfinite(value)
