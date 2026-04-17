"""Contract-aware Gold Standard comparison for anchor cases."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, cast

from .config import PROFILE_VALUE_KEYS, THRESHOLDS, ZERO_REFERENCE_EPSILON
from .schemas import GoldStandardComparison, ObservableCheck


class GoldStandardComparator:
    """Compare contract observables against simulated results."""

    def compare(self, gold_standard: Dict[str, Any], sim_results: Dict[str, Any]) -> GoldStandardComparison:
        observables = gold_standard.get("observables", [])
        if not observables:
            return GoldStandardComparison(overall="SKIPPED", warnings=["missing_gold_standard_observables"])

        checks: List[ObservableCheck] = []
        for observable in observables:
            checks.append(self._compare_observable(observable, sim_results))

        pass_count = sum(1 for check in checks if check.within_tolerance)
        ratio = pass_count / len(checks)
        if pass_count == len(checks):
            overall = "PASS"
        elif ratio >= THRESHOLDS["TH-8"]:
            overall = "PASS_WITH_DEVIATIONS"
        else:
            overall = "FAIL"

        return GoldStandardComparison(overall=overall, observables=checks)

    def _compare_observable(self, observable: Dict[str, Any], sim_results: Dict[str, Any]) -> ObservableCheck:
        name = observable["name"]
        ref_value = observable["ref_value"]
        tolerance = observable.get("tolerance", {"mode": "relative", "value": THRESHOLDS["TH-5"]})
        sim_value = sim_results.get(name)

        if sim_value is None:
            return ObservableCheck(
                name=name,
                ref_value=ref_value,
                sim_value=None,
                rel_error=None,
                abs_error=None,
                tolerance=tolerance,
                within_tolerance=False,
            )

        if isinstance(ref_value, list):
            return self._compare_profile(name, ref_value, sim_value, sim_results, tolerance)
        if isinstance(ref_value, dict):
            return self._compare_mapping(name, ref_value, sim_value, tolerance)
        return self._compare_scalar(name, ref_value, sim_value, tolerance)

    def _compare_scalar(
        self,
        name: str,
        ref_value: Any,
        sim_value: Any,
        tolerance: Dict[str, Any],
    ) -> ObservableCheck:
        if not self._is_finite_number(sim_value):
            return ObservableCheck(name, ref_value, sim_value, None, None, tolerance, False)

        rel_error, abs_error, within = self._compare_number(float(ref_value), float(sim_value), tolerance)
        return ObservableCheck(name, ref_value, sim_value, rel_error, abs_error, tolerance, within)

    def _compare_mapping(
        self,
        name: str,
        ref_value: Dict[str, Any],
        sim_value: Any,
        tolerance: Dict[str, Any],
    ) -> ObservableCheck:
        if not isinstance(sim_value, dict):
            return ObservableCheck(name, ref_value, sim_value, None, None, tolerance, False)

        rel_errors, abs_errors, within_all = self._compare_mapping_entries(ref_value, sim_value, tolerance)

        return ObservableCheck(
            name=name,
            ref_value=ref_value,
            sim_value=sim_value,
            rel_error=max(rel_errors) if rel_errors else None,
            abs_error=max(abs_errors) if abs_errors else None,
            tolerance=tolerance,
            within_tolerance=within_all,
        )

    def _compare_mapping_entries(
        self,
        ref_value: Dict[str, Any],
        sim_value: Dict[str, Any],
        tolerance: Dict[str, Any],
    ) -> Tuple[List[float], List[float], bool]:
        rel_errors: List[float] = []
        abs_errors: List[float] = []
        within_all = True

        for key, expected in ref_value.items():
            actual = sim_value.get(key)
            if isinstance(expected, dict):
                if not isinstance(actual, dict):
                    within_all = False
                    continue
                nested_rel, nested_abs, nested_within = self._compare_mapping_entries(expected, actual, tolerance)
                rel_errors.extend(nested_rel)
                abs_errors.extend(nested_abs)
                within_all = within_all and nested_within
                continue

            if not self._is_finite_number(expected) or not self._is_finite_number(actual):
                within_all = False
                continue

            expected_value = float(cast(float, expected))
            actual_value = float(cast(float, actual))
            rel_error, abs_error, within = self._compare_number(expected_value, actual_value, tolerance)
            if rel_error is not None:
                rel_errors.append(rel_error)
            if abs_error is not None:
                abs_errors.append(abs_error)
            within_all = within_all and within

        return rel_errors, abs_errors, within_all

    def _compare_profile(
        self,
        name: str,
        ref_points: List[Dict[str, Any]],
        sim_value: Any,
        sim_results: Dict[str, Any],
        tolerance: Dict[str, Any],
    ) -> ObservableCheck:
        value_key = self._profile_value_key(ref_points[0].keys())
        axis_key = self._profile_axis_key(ref_points, value_key)
        if value_key is None:
            return ObservableCheck(name, ref_points, sim_value, None, None, tolerance, False)

        ref_axis = [float(point.get(axis_key, index)) for index, point in enumerate(ref_points)]
        ref_series = [point[value_key] for point in ref_points]
        sim_series, sim_axis = self._profile_series(name, sim_value, sim_results, axis_key, len(ref_points))

        if sim_series is None or sim_axis is None:
            return ObservableCheck(name, ref_points, sim_value, None, None, tolerance, False)

        rel_errors: List[float] = []
        abs_errors: List[float] = []
        within_all = True
        actual_values: List[float] = []
        for expected_axis, expected_value in zip(ref_axis, ref_series):
            actual_value = self._interp1d(sim_axis, sim_series, float(expected_axis))
            rel_error, abs_error, within = self._compare_number(float(expected_value), float(actual_value), tolerance)
            if rel_error is not None:
                rel_errors.append(rel_error)
            if abs_error is not None:
                abs_errors.append(abs_error)
            actual_values.append(actual_value)
            within_all = within_all and within

        return ObservableCheck(
            name=name,
            ref_value=ref_points,
            sim_value=actual_values,
            rel_error=max(rel_errors) if rel_errors else None,
            abs_error=max(abs_errors) if abs_errors else None,
            tolerance=tolerance,
            within_tolerance=within_all,
        )

    @staticmethod
    def _profile_value_key(keys: Iterable[str]) -> Optional[str]:
        for candidate in PROFILE_VALUE_KEYS:
            if candidate in keys:
                return candidate
        return None

    @staticmethod
    def _profile_axis_key(ref_points: Sequence[Dict[str, Any]], value_key: Optional[str]) -> str:
        if value_key is None:
            return "index"
        candidate_keys = [key for key in ref_points[0].keys() if key != value_key]
        varying_keys = []
        for key in candidate_keys:
            unique_values = {point.get(key) for point in ref_points}
            if len(unique_values) > 1:
                varying_keys.append(key)
        if varying_keys:
            return varying_keys[-1]
        if candidate_keys:
            return candidate_keys[0]
        return "index"

    @staticmethod
    def _profile_series(
        name: str,
        sim_value: Any,
        sim_results: Dict[str, Any],
        axis_key: str,
        fallback_length: int,
    ) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        if isinstance(sim_value, list) and sim_value and isinstance(sim_value[0], dict):
            value_key = None
            keys = sim_value[0].keys()
            for candidate in PROFILE_VALUE_KEYS:
                if candidate in keys:
                    value_key = candidate
                    break
            if value_key is None:
                return None, None
            series = [float(point[value_key]) for point in sim_value]
            axis = [float(point.get(axis_key, index)) for index, point in enumerate(sim_value)]
            return series, axis

        if isinstance(sim_value, list):
            axis_values = sim_results.get(f"{name}_{axis_key}")
            if axis_values is None:
                axis_values = [float(index) for index in range(len(sim_value))]
            return [float(value) for value in sim_value], [float(value) for value in axis_values]

        return None, None

    @staticmethod
    def _compare_number(ref_value: float, sim_value: float, tolerance: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], bool]:
        abs_error = abs(sim_value - ref_value)
        if abs(ref_value) < ZERO_REFERENCE_EPSILON:
            threshold = THRESHOLDS["TH-6"]
            return None, abs_error, abs_error <= threshold

        tolerance_value = tolerance.get("value", THRESHOLDS["TH-5"]) if isinstance(tolerance, dict) else float(tolerance)
        rel_error = abs_error / abs(ref_value)
        if isinstance(tolerance, dict) and tolerance.get("mode") == "absolute":
            return rel_error, abs_error, abs_error <= tolerance_value
        return rel_error, abs_error, rel_error <= tolerance_value

    @staticmethod
    def _interp1d(xs: List[float], ys: List[float], x_target: float) -> float:
        if len(xs) != len(ys):
            raise ValueError("Profile axis/value lengths must match")
        if x_target <= xs[0]:
            return ys[0]
        if x_target >= xs[-1]:
            return ys[-1]
        for index in range(len(xs) - 1):
            if xs[index] <= x_target <= xs[index + 1]:
                x0, x1 = xs[index], xs[index + 1]
                y0, y1 = ys[index], ys[index + 1]
                if x1 == x0:
                    return y0
                fraction = (x_target - x0) / (x1 - x0)
                return y0 + fraction * (y1 - y0)
        return ys[-1]

    @staticmethod
    def _is_finite_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and math.isfinite(value)
