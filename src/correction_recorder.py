"""CorrectionSpec 生成器：把偏差分析转化为可追溯的修正记录"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from .models import (
    ComparisonResult,
    CorrectionSpec,
    ErrorType,
    ExecutionResult,
    ImpactScope,
    TaskSpec,
)

logger = logging.getLogger(__name__)


class CorrectionRecorder:
    """根据 ComparisonResult 自动生成 CorrectionSpec

    自动推断 error_type 和 impact_scope；
    human_reason / root_cause / fix_action 提供基于规则的默认文本，
    后续由工程师补充。
    """

    def record(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison: ComparisonResult,
    ) -> CorrectionSpec:
        """生成 CorrectionSpec"""
        error_type = self._infer_error_type(exec_result, comparison)
        impact_scope = self._infer_impact_scope(task_spec, comparison)

        wrong_output = {
            "key_quantities": exec_result.key_quantities,
            "residuals": exec_result.residuals,
        }
        correct_output = self._build_correct_output(comparison)

        evidence = self._build_evidence(comparison)
        human_reason = f"Automatic detection: {len(comparison.deviations)} quantity deviation(s) exceed tolerance"
        root_cause = self._infer_root_cause(error_type, task_spec)
        fix_action = self._suggest_fix(error_type, task_spec)

        return CorrectionSpec(
            error_type=error_type,
            wrong_output=wrong_output,
            correct_output=correct_output,
            human_reason=human_reason,
            evidence=evidence,
            impact_scope=impact_scope,
            root_cause=root_cause,
            fix_action=fix_action,
            needs_replay=True,
            task_spec_name=task_spec.name,
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
        )

    # ------------------------------------------------------------------
    # 推断辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_error_type(
        exec_result: ExecutionResult,
        comparison: ComparisonResult,
    ) -> ErrorType:
        if not exec_result.success:
            return ErrorType.CONVERGENCE_FAILURE
        # 如果存在偏差，默认为物理量偏差
        if comparison.deviations:
            return ErrorType.QUANTITY_DEVIATION
        return ErrorType.OTHER

    @staticmethod
    def _infer_impact_scope(
        task_spec: TaskSpec,
        comparison: ComparisonResult,
    ) -> ImpactScope:
        # 多个物理量同时失败 → 可能是系统性问题
        if len(comparison.deviations) >= 3:
            return ImpactScope.CLASS
        return ImpactScope.LOCAL

    @staticmethod
    def _build_correct_output(comparison: ComparisonResult) -> dict:
        """把 Gold Standard 的期望值汇总为 correct_output"""
        return {
            d.quantity: d.expected
            for d in comparison.deviations
        }

    @staticmethod
    def _build_evidence(comparison: ComparisonResult) -> str:
        lines = [f"Comparison summary: {comparison.summary}"]
        for d in comparison.deviations[:5]:  # 最多列 5 条
            rel_err_str = f"{d.relative_error:.1%}" if d.relative_error is not None else "N/A"
            lines.append(
                f"  {d.quantity}: expected={d.expected}, actual={d.actual}, rel_err={rel_err_str}"
            )
        return "\n".join(lines)

    @staticmethod
    def _infer_root_cause(error_type: ErrorType, task_spec: TaskSpec) -> str:
        causes = {
            ErrorType.CONVERGENCE_FAILURE: "求解器未收敛，可能原因：网格质量差、时间步长过大或边界条件不合理",
            ErrorType.QUANTITY_DEVIATION: f"关键物理量偏离参考值，可能原因：{task_spec.geometry_type.value} 几何下网格分辨率不足或湍流模型选择不当",
            ErrorType.WRONG_BOUNDARY: "边界条件设置错误",
            ErrorType.WRONG_SOLVER: "求解器选择不匹配当前流动类型",
            ErrorType.WRONG_TURBULENCE_MODEL: "湍流模型不适用于当前雷诺数范围",
            ErrorType.WRONG_MESH: "网格质量不满足要求",
            ErrorType.OTHER: "原因未知，需人工分析",
        }
        return causes.get(error_type, "需人工分析")

    @staticmethod
    def _suggest_fix(error_type: ErrorType, task_spec: TaskSpec) -> str:
        fixes = {
            ErrorType.CONVERGENCE_FAILURE: "降低时间步长、优化网格、检查边界条件",
            ErrorType.QUANTITY_DEVIATION: "加密关键区域网格，重新运行并对比",
            ErrorType.WRONG_BOUNDARY: "按参考文献重新设置边界条件",
            ErrorType.WRONG_SOLVER: "根据流动类型切换合适求解器",
            ErrorType.WRONG_TURBULENCE_MODEL: f"Re={task_spec.Re} 下建议使用 k-ε 或 k-ω SST",
            ErrorType.WRONG_MESH: "重新划分网格，保证 y+ 满足要求",
            ErrorType.OTHER: "人工审查执行日志",
        }
        return fixes.get(error_type, "人工审查")
