"""结果 vs Gold Standard 对比器"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models import ComparisonResult, DeviationDetail, ExecutionResult

logger = logging.getLogger(__name__)


class ResultComparator:
    """对比 ExecutionResult 与 Gold Standard

    支持标量比较（单个数值）和向量比较（列表，取最大偏差）。
    """

    def __init__(self, threshold: float = 0.10) -> None:
        """
        Args:
            threshold: 默认相对误差阈值（0.10 = 10%），
                       whitelist 中有显式 tolerance 时以 whitelist 为准。
        """
        self._default_threshold = threshold

    def compare(
        self,
        result: ExecutionResult,
        gold: Dict[str, Any],
    ) -> ComparisonResult:
        """执行对比，返回 ComparisonResult"""
        quantity_key = gold.get("quantity")
        if quantity_key is None:
            logger.warning("Gold standard missing 'quantity' key, skipping comparison")
            return ComparisonResult(passed=True, summary="No gold standard quantity defined")

        actual_value = result.key_quantities.get(quantity_key)
        if actual_value is None:
            deviation = DeviationDetail(
                quantity=quantity_key,
                expected=gold.get("reference_values"),
                actual=None,
            )
            return ComparisonResult(
                passed=False,
                deviations=[deviation],
                summary=f"Quantity '{quantity_key}' not found in execution result",
            )

        tolerance = gold.get("tolerance", self._default_threshold)
        reference_values = gold.get("reference_values", [])
        deviations: List[DeviationDetail] = []

        if isinstance(actual_value, list) and reference_values:
            actual_y = result.key_quantities.get(f"{quantity_key}_y")
            deviations = self._compare_vector(
                quantity_key, actual_value, reference_values, tolerance, actual_y=actual_y
            )
        elif isinstance(actual_value, (int, float)) and reference_values:
            deviations = self._compare_scalar(quantity_key, actual_value, reference_values, tolerance)
        else:
            logger.debug("Cannot compare quantity '%s': type mismatch or missing reference", quantity_key)

        passed = len(deviations) == 0
        summary_parts = [f"Quantity: {quantity_key}", f"Tolerance: {tolerance:.1%}"]
        if not passed:
            summary_parts.append(f"Failed: {len(deviations)} deviation(s)")
        else:
            summary_parts.append("PASS")

        return ComparisonResult(
            passed=passed,
            deviations=deviations,
            summary=" | ".join(summary_parts),
            gold_standard_id=gold.get("id"),
        )

    # ------------------------------------------------------------------
    # 内部比较方法
    # ------------------------------------------------------------------

    def _compare_scalar(
        self,
        quantity: str,
        actual: float,
        reference_values: List[Dict[str, Any]],
        tolerance: float,
    ) -> List[DeviationDetail]:
        """标量比较：从 reference_values 取第一个 value"""
        deviations = []
        for ref in reference_values:
            expected = ref.get("value")
            if expected is None:
                continue
            rel_err = abs(actual - expected) / (abs(expected) + 1e-12)
            if rel_err > tolerance:
                deviations.append(DeviationDetail(
                    quantity=quantity,
                    expected=expected,
                    actual=actual,
                    relative_error=rel_err,
                    tolerance=tolerance,
                ))
            break  # 标量只比较第一个参考值
        return deviations

    def _compare_vector(
        self,
        quantity: str,
        actual_list: List[float],
        reference_values: List[Dict[str, Any]],
        tolerance: float,
        actual_y: Optional[List[float]] = None,
    ) -> List[DeviationDetail]:
        """向量比较：支持 y-aware 插值比较。

        如果 actual_y 提供（与 actual_list 等长），则在 Gold Standard 的 y 位置
        对 actual_list 进行线性插值后再比较。
        否则退化为 index-based positional matching。
        """
        deviations = []
        ref_scalars = [r.get("u") or r.get("value") for r in reference_values]
        ref_ys = [r.get("y") for r in reference_values]

        # y-aware 插值比较：只有当 actual_y 可用且 reference 有 y 坐标时才启用
        use_interp = (
            actual_y is not None
            and len(actual_y) == len(actual_list)
            and all(y is not None for y in ref_ys)
        )

        if use_interp:
            # 构建 actual profile 并在 Gold Standard y 位置插值
            actual_pairs = sorted(zip(actual_y, actual_list))
            act_y_sorted = [p[0] for p in actual_pairs]
            act_u_sorted = [p[1] for p in actual_pairs]

            for i, (ref_y, ref_u) in enumerate(zip(ref_ys, ref_scalars)):
                if ref_u is None:
                    continue
                # 线性插值
                sim_u = self._interp1d(act_y_sorted, act_u_sorted, ref_y)
                rel_err = abs(sim_u - ref_u) / (abs(ref_u) + 1e-12)
                if rel_err > tolerance:
                    deviations.append(DeviationDetail(
                        quantity=f"{quantity}[y={ref_y:.4f}]",
                        expected=ref_u,
                        actual=sim_u,
                        relative_error=rel_err,
                        tolerance=tolerance,
                    ))
        else:
            # Fallback: positional matching
            for i, (act, ref) in enumerate(zip(actual_list, ref_scalars)):
                if ref is None:
                    continue
                rel_err = abs(act - ref) / (abs(ref) + 1e-12)
                if rel_err > tolerance:
                    deviations.append(DeviationDetail(
                        quantity=f"{quantity}[{i}]",
                        expected=ref,
                        actual=act,
                        relative_error=rel_err,
                        tolerance=tolerance,
                    ))
        return deviations

    @staticmethod
    def _interp1d(xs: List[float], ys: List[float], x_target: float) -> float:
        """线性插值。xs 必须单调递增。"""
        if x_target <= xs[0]:
            return ys[0]
        if x_target >= xs[-1]:
            return ys[-1]
        for k in range(len(xs) - 1):
            if xs[k] <= x_target <= xs[k + 1]:
                if xs[k + 1] == xs[k]:
                    return ys[k]
                frac = (x_target - xs[k]) / (xs[k + 1] - xs[k])
                return ys[k] + frac * (ys[k + 1] - ys[k])
        return ys[-1]
