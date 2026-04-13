"""误差自动归因链：从偏差到根因到修正方案的完整链路"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .knowledge_db import KnowledgeDB
from .models import (
    AttributionReport,
    ComparisonResult,
    DeviationDetail,
    ErrorType,
    ExecutionResult,
    TaskSpec,
)

logger = logging.getLogger(__name__)


# 湍流模型推荐规则（按雷诺数范围）
_TURBULENCE_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "laminar": {
        "range": (0, 2300),
        "models": ["laminar"],
        "reason": "Re < 2300: 层流 regime",
    },
    "k-epsilon": {
        "range": (2300, 50000),
        "models": ["k-epsilon", "RNG k-epsilon"],
        "reason": "Re 2300-50000: 中等湍流，k-epsilon 足够",
    },
    "k-omega SST": {
        "range": (50000, 1_000_000),
        "models": ["k-omega SST"],
        "reason": "Re 50000+: k-omega SST 适合逆压梯度近壁",
    },
    "DES": {
        "range": (1_000_000, float("inf")),
        "models": ["k-omega SST", "DES"],
        "reason": "Re > 1e6: 分离流/大尺度涡，建议 DES 或 LES",
    },
}


def _get_turbulence_for_re(turbulence_model: str, Re: Optional[float]) -> Dict[str, Any]:
    """根据当前湍流模型和雷诺数推荐"""
    recommendations = []
    if Re is not None:
        for label, info in _TURBULENCE_RECOMMENDATIONS.items():
            lo, hi = info["range"]
            if lo < Re <= hi:
                recommendations = info["models"]
                break

    if turbulence_model.lower() in ("laminar", "k-epsilon", "k-omega sst", "rng k-epsilon"):
        current = turbulence_model
    else:
        current = turbulence_model or "unknown"

    return {
        "current": current,
        "recommended": recommendations if recommendations else ["k-omega SST"],
        "reason": next(
            (v["reason"] for k, v in _TURBULENCE_RECOMMENDATIONS.items()
             if current.lower().replace("-", "").replace(" ", "") in k.lower().replace("-", "").replace(" ", "")
             or any(current.lower() == m.lower() for m in v["models"])),
            "基于雷诺数推荐 k-omega SST"
        ),
    }


def _classify_mesh_issue(
    deviations: List[DeviationDetail],
    residuals: Dict[str, float],
) -> bool:
    """判断是否是网格问题：残差收敛但物理量偏差"""
    if not residuals:
        return False
    residual_values = list(residuals.values())
    if not residual_values:
        return False
    max_residual = max(residual_values)
    # 如果最大残差 < 1e-3（已收敛）但物理量偏差 → 网格分辨率不足
    return max_residual < 1e-3 and len(deviations) > 0


def _classify_bc_issue(
    deviations: List[DeviationDetail],
    residuals: Dict[str, float],
) -> bool:
    """判断是否是边界条件问题：残差未收敛或 inlet/outlet 偏差"""
    if not residuals:
        return False
    max_residual = max(residuals.values())
    # 残差未收敛（> 1e-3）
    if max_residual > 1e-3:
        return True
    # inlet velocity profile 偏差（如果有 velocity 相关的 deviations）
    for d in deviations:
        if "u_" in d.quantity.lower() or "velocity" in d.quantity.lower():
            return True
    return False


def _classify_turbulence_issue(
    deviations: List[DeviationDetail],
    Re: Optional[float],
    turbulence_model: str,
) -> bool:
    """判断是否是湍流模型问题"""
    if Re is None:
        return False
    # 检查当前模型是否适合当前 Re
    for label, info in _TURBULENCE_RECOMMENDATIONS.items():
        lo, hi = info["range"]
        if lo < Re <= hi:
            if turbulence_model.lower() not in [m.lower() for m in info["models"]]:
                return True
    return False


class ErrorAttributor:
    """误差自动归因链引擎

    链路: 偏差 → 定量分析 → 根因分类 → 知识库检索 → 修正建议
    """

    def __init__(self, knowledge_db: Optional[KnowledgeDB] = None) -> None:
        self._db = knowledge_db or KnowledgeDB()

    def attribute(
        self,
        task_spec: TaskSpec,
        exec_result: ExecutionResult,
        comparison: ComparisonResult,
    ) -> AttributionReport:
        """生成完整的误差归因报告"""
        if not comparison.deviations:
            return AttributionReport(chain_complete=True)

        # Step 1: 定量分析
        max_err, worst_qty = self._find_worst_deviation(comparison.deviations)
        mag_pct = self._deviation_magnitude(comparison.deviations)

        # Step 2: 根因分类
        primary, confidence, secondaries = self._classify_root_cause(
            comparison, exec_result, task_spec
        )

        # Step 3: 生成修正建议
        mesh_fix = self._suggest_mesh_fix(primary, task_spec, max_err)
        turb_fix = self._suggest_turbulence_fix(primary, task_spec)
        bc_fix = self._suggest_bc_fix(primary, task_spec)
        solver_fix = self._suggest_solver_fix(primary, task_spec)

        # Step 4: 知识库检索
        similar = self._find_similar_cases(task_spec)
        solvers = self._db.list_solver_for_geometry(task_spec.geometry_type)
        turb_models = self._db.list_turbulence_models(task_spec.geometry_type).get(
            task_spec.geometry_type.value, []
        )

        return AttributionReport(
            chain_complete=True,
            max_relative_error=max_err,
            worst_quantity=worst_qty,
            deviation_magnitude_pct=mag_pct,
            primary_cause=primary,
            confidence=confidence,
            secondary_causes=secondaries,
            mesh_recommendation=mesh_fix,
            turbulence_recommendation=turb_fix,
            bc_recommendation=bc_fix,
            solver_recommendation=solver_fix,
            similar_cases=similar,
            recommended_solvers=solvers,
            recommended_turbulence_models=turb_models,
        )

    # ------------------------------------------------------------------
    # 定量分析
    # ------------------------------------------------------------------

    @staticmethod
    def _find_worst_deviation(
        deviations: List[DeviationDetail],
    ) -> tuple[float, str]:
        worst = max(deviations, key=lambda d: d.relative_error or 0.0)
        return worst.relative_error or 0.0, worst.quantity

    @staticmethod
    def _deviation_magnitude(deviations: List[DeviationDetail]) -> float:
        """计算平均偏差幅度百分比"""
        if not deviations:
            return 0.0
        errs = [d.relative_error for d in deviations if d.relative_error is not None]
        if not errs:
            return 0.0
        return float(sum(errs) / len(errs))

    # ------------------------------------------------------------------
    # 根因分类
    # ------------------------------------------------------------------

    def _classify_root_cause(
        self,
        comparison: ComparisonResult,
        exec_result: ExecutionResult,
        task_spec: TaskSpec,
    ) -> tuple[str, float, List[str]]:
        """推断主根因和置信度"""
        residuals = exec_result.residuals
        deviations = comparison.deviations
        Re = task_spec.Re
        turbulence = self._get_turbulence_model_from_task(task_spec)

        scores: Dict[str, float] = {
            "mesh": 0.0,
            "boundary_condition": 0.0,
            "turbulence": 0.0,
            "solver": 0.0,
            "parameters": 0.0,
        }

        # 残差分析
        if residuals:
            max_res = max(residuals.values()) if residuals else 0.0
            if max_res > 1e-2:
                scores["solver"] += 0.4
                scores["boundary_condition"] += 0.3
            elif max_res > 1e-3:
                scores["mesh"] += 0.3
                scores["turbulence"] += 0.2

        # 网格问题检测
        if _classify_mesh_issue(deviations, residuals):
            scores["mesh"] += 0.5

        # 边界条件检测
        if _classify_bc_issue(deviations, residuals):
            scores["boundary_condition"] += 0.4

        # 湍流模型检测
        if _classify_turbulence_issue(deviations, Re, turbulence):
            scores["turbulence"] += 0.4

        # 雷诺数敏感性
        if Re is not None:
            if Re > 1e6:
                scores["turbulence"] += 0.2
            elif Re < 2300:
                scores["turbulence"] -= 0.3

        # 基于 ErrorType
        error_type_scores = {
            ErrorType.CONVERGENCE_FAILURE: {"solver": 0.5, "mesh": 0.2},
            ErrorType.QUANTITY_DEVIATION: {"mesh": 0.3, "turbulence": 0.3, "parameters": 0.2},
            ErrorType.WRONG_BOUNDARY: {"boundary_condition": 0.7},
            ErrorType.WRONG_TURBULENCE_MODEL: {"turbulence": 0.8},
            ErrorType.WRONG_MESH: {"mesh": 0.8},
            ErrorType.WRONG_SOLVER: {"solver": 0.7},
            ErrorType.OTHER: {},
        }

        for d in deviations:
            pass

        # 取最高分
        primary = max(scores, key=lambda k: scores[k])
        confidence = min(scores[primary], 1.0)
        secondaries = [k for k, v in scores.items() if v > 0.2 and k != primary]

        return primary, confidence, secondaries

    def _get_turbulence_model_from_task(self, task_spec: TaskSpec) -> str:
        """从知识库获取当前 case 的湍流模型"""
        chain = self._db.get_execution_chain(task_spec.name)
        if chain:
            return chain.get("turbulence_model", "unknown")
        return "unknown"

    # ------------------------------------------------------------------
    # 修正建议
    # ------------------------------------------------------------------

    @staticmethod
    def _suggest_mesh_fix(
        primary_cause: str,
        task_spec: TaskSpec,
        max_error: float,
    ) -> Optional[str]:
        if primary_cause != "mesh":
            return None
        geom = task_spec.geometry_type.value
        if max_error > 0.5:
            suggestion = f"对 {geom} 加密网格：建议将 ncx/ncy 加倍（当前误差 {max_error:.0%} > 50%）"
        elif max_error > 0.2:
            suggestion = f"对 {geom} 适度加密：在速度梯度大的区域（分离/再附点附近）局部加密"
        else:
            suggestion = f"对 {geom} 网格无关性验证：分别在当前网格和 2x 密度下运行，对比结果"
        return suggestion

    @staticmethod
    def _suggest_turbulence_fix(
        primary_cause: str,
        task_spec: TaskSpec,
    ) -> Optional[str]:
        if primary_cause != "turbulence":
            return None
        Re = task_spec.Re
        geom = task_spec.geometry_type.value
        turb_rec = _get_turbulence_for_re("k-omega SST", Re)
        return f"{geom} (Re={Re}) 推荐: {', '.join(turb_rec['recommended'])} — {turb_rec['reason']}"

    @staticmethod
    def _suggest_bc_fix(
        primary_cause: str,
        task_spec: TaskSpec,
    ) -> Optional[str]:
        if primary_cause != "boundary_condition":
            return None
        bcs = task_spec.boundary_conditions
        if bcs:
            return f"检查边界条件设置: {bcs} — 对照 {task_spec.description} 原始文献验证"
        return "按 Gold Standard 参考文献重新设置 inlet/outlet 边界条件"

    @staticmethod
    def _suggest_solver_fix(
        primary_cause: str,
        task_spec: TaskSpec,
    ) -> Optional[str]:
        if primary_cause != "solver":
            return None
        flow = task_spec.flow_type.value
        steady = task_spec.steady_state.value
        if flow == "NATURAL_CONVECTION":
            return "buoyantSimpleFoam: 检查重力方向和 Boussinesq 参数"
        elif steady == "TRANSIENT":
            return "pimpleFoam: 尝试减小时间步长或调整松弛因子"
        elif flow == "EXTERNAL":
            return "simpleFoam: 检查压力速度耦合 (SIMPLE/SIMPLEC/PISO)"
        return "尝试调整求解器松弛因子或压力速度耦合算法"

    # ------------------------------------------------------------------
    # 知识库检索
    # ------------------------------------------------------------------

    def _find_similar_cases(self, task_spec: TaskSpec) -> List[str]:
        """找同类几何/流型的案例"""
        results = self._db.query_cases(
            geometry_type=task_spec.geometry_type,
            flow_type=task_spec.flow_type,
        )
        return [c.get("id", c.get("name", "")) for c in results[:3]]
