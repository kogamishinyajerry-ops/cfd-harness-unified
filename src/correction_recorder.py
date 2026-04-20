"""CorrectionSpec 生成器：把偏差分析转化为可追溯的修正记录"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from .error_attributor import ErrorAttributor
from .models import (
    ComparisonResult,
    CorrectionSpec,
    ErrorType,
    ExecutionResult,
    GeometryType,
    ImpactScope,
    SteadyState,
    TaskSpec,
)

logger = logging.getLogger(__name__)


class CorrectionRecorder:
    """根据 ComparisonResult 自动生成 CorrectionSpec

    自动推断 error_type 和 impact_scope；
    human_reason / root_cause / fix_action 提供基于规则的默认文本，
    后续由工程师补充。
    """

    def __init__(self) -> None:
        self._attributor = ErrorAttributor()

    def record(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison: ComparisonResult,
    ) -> CorrectionSpec:
        """生成 CorrectionSpec"""
        error_type = self._infer_error_type(task_spec, exec_result, comparison)
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

        # Phase 4: 误差自动归因链
        attribution = None
        if comparison.deviations and not comparison.passed:
            attribution = self._attributor.attribute(task_spec, exec_result, comparison)
            if attribution and attribution.chain_complete:
                # 用归因链的详细信息增强 root_cause 和 fix_action
                root_cause = self._enrich_root_cause(root_cause, attribution)
                fix_action = self._enrich_fix_action(fix_action, attribution)

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
            created_at=datetime.datetime.now(datetime.timezone.utc)
            .replace(tzinfo=None)
            .isoformat()
            + "Z",
            attribution=attribution,
        )

    # ------------------------------------------------------------------
    # 推断辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_error_type(
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison: ComparisonResult,
    ) -> ErrorType:
        # Phase 5 T3: structured error type detection
        if not exec_result.success:
            return ErrorType.CONVERGENCE_FAILURE
        if any(d.actual is None for d in comparison.deviations):
            return ErrorType.COMPARATOR_SCHEMA_MISMATCH
        if (
            task_spec.steady_state == SteadyState.TRANSIENT
            and "strouhal" not in exec_result.key_quantities
            and comparison.deviations
        ):
            return ErrorType.INSUFFICIENT_TRANSIENT_SAMPLING
        if (
            task_spec.geometry_type == GeometryType.BACKWARD_FACING_STEP
            and any("reattachment" in d.quantity.lower() for d in comparison.deviations)
        ):
            return ErrorType.GEOMETRY_MODEL_MISMATCH
        if (
            comparison.deviations
            and (task_spec.Ra is not None or task_spec.Re_tau is not None)
            and not CorrectionRecorder._parameter_injection_detected(task_spec, exec_result)
        ):
            return ErrorType.PARAMETER_PLUMBING_MISMATCH
        if comparison.deviations:
            return ErrorType.QUANTITY_DEVIATION
        return ErrorType.OTHER

    @staticmethod
    def _parameter_injection_detected(
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
    ) -> bool:
        """Check if Ra/Re_tau tokens appear in the execution result."""
        parameter_tokens = []
        if task_spec.Ra is not None:
            parameter_tokens.extend(["ra", f"{task_spec.Ra}"[:4].lower()])
        if task_spec.Re_tau is not None:
            parameter_tokens.extend(["re_tau", "retau", f"{task_spec.Re_tau}"[:4].lower()])

        searchable_parts = [
            exec_result.error_message or "",
            " ".join(str(k).lower() for k in exec_result.key_quantities.keys()),
            " ".join(str(v).lower() for v in exec_result.key_quantities.values()),
        ]
        searchable_text = " ".join(searchable_parts)
        return any(token and token in searchable_text for token in parameter_tokens)

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
            ErrorType.PARAMETER_PLUMBING_MISMATCH: "任务参数未正确传递到求解配置，Ra/Re_tau 等关键参数可能被静默忽略或回退为默认值",
            ErrorType.COMPARATOR_SCHEMA_MISMATCH: "结果对比器未找到目标物理量，执行结果字段与 Gold Standard schema 不一致",
            ErrorType.GEOMETRY_MODEL_MISMATCH: "生成的几何模型与基准案例不一致，导致再附点等几何敏感量系统性偏差",
            ErrorType.INSUFFICIENT_TRANSIENT_SAMPLING: "瞬态采样不足，缺少 Strouhal 等非定常统计量，当前结果不足以和基准对比",
            ErrorType.BUOYANT_ENERGY_SETUP_INCOMPLETE: "浮力/能量方程设置不完整，热力学字段或 p_rgh/T/alphat 等初始条件缺失",
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
            ErrorType.PARAMETER_PLUMBING_MISMATCH: "检查批量重建与求解器输入模板，确认 Ra/Re_tau 等参数已写入 case 文件",
            ErrorType.COMPARATOR_SCHEMA_MISMATCH: "扩展 ResultComparator quantity fallback，并校对 Gold Standard 字段命名",
            ErrorType.GEOMETRY_MODEL_MISMATCH: "核对 geometry_type 路由与几何生成参数，确保案例几何与 benchmark 定义一致",
            ErrorType.INSUFFICIENT_TRANSIENT_SAMPLING: "延长 endTime 或增加采样窗口，输出 Strouhal 等瞬态统计量后再比较",
            ErrorType.BUOYANT_ENERGY_SETUP_INCOMPLETE: "补齐 buoyantFoam 所需字段与热物性设置，重点检查 T、p_rgh、alphat 和 thermo/g 配置",
            ErrorType.OTHER: "人工审查执行日志",
        }
        return fixes.get(error_type, "人工审查")

    @staticmethod
    def _enrich_root_cause(base: str, attr) -> str:
        """用 AttributionReport 增强 root_cause"""
        if attr is None:
            return base
        parts = [base]
        if attr.primary_cause != "unknown":
            parts.append(f"[归因链] 主根因: {attr.primary_cause} (置信度 {attr.confidence:.0%})")
        if attr.worst_quantity:
            parts.append(f"最大偏差: {attr.worst_quantity} ({attr.max_relative_error:.1%})")
        if attr.secondary_causes:
            parts.append(f"次要原因: {', '.join(attr.secondary_causes)}")
        if attr.similar_cases:
            parts.append(f"同类案例: {', '.join(attr.similar_cases)}")
        return " | ".join(parts)

    @staticmethod
    def _enrich_fix_action(base: str, attr) -> str:
        """用 AttributionReport 增强 fix_action"""
        if attr is None:
            return base
        parts = [base]
        if attr.mesh_recommendation:
            parts.append(f"[mesh] {attr.mesh_recommendation}")
        if attr.turbulence_recommendation:
            parts.append(f"[turbulence] {attr.turbulence_recommendation}")
        if attr.bc_recommendation:
            parts.append(f"[BC] {attr.bc_recommendation}")
        if attr.solver_recommendation:
            parts.append(f"[solver] {attr.solver_recommendation}")
        if attr.recommended_turbulence_models:
            models = ", ".join(attr.recommended_turbulence_models)
            parts.append(f"[知识库] 可用湍流模型: {models}")
        return "\n".join(parts)
