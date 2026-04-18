"""误差自动归因链：从偏差到根因到修正方案的完整链路"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .auto_verifier.config import CASE_ID_TO_GOLD_FILE, TASK_NAME_TO_CASE_ID
from .knowledge_db import KnowledgeDB
from .models import (
    AttributionReport,
    ComparisonResult,
    DeviationDetail,
    ErrorType,
    ExecutionResult,
    GeometryType,
    SteadyState,
    TaskSpec,
)

_AUDIT_CONCERN_STATUS_PREFIXES = (
    "COMPATIBLE_WITH_SILENT_PASS_HAZARD",
    "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE",
)


def _resolve_audit_concern(
    task_spec: TaskSpec,
    comparison: ComparisonResult,
    *,
    exec_result: Optional[ExecutionResult] = None,
) -> Optional[str]:
    if not comparison.passed:
        return None
    case_id = TASK_NAME_TO_CASE_ID.get(task_spec.name, task_spec.name)
    gold_path = CASE_ID_TO_GOLD_FILE.get(case_id)
    if gold_path is None or not gold_path.exists():
        return None
    try:
        data = yaml.safe_load(gold_path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return None
    status = str((data.get("physics_contract") or {}).get("contract_status") or "")
    concern = next((p for p in _AUDIT_CONCERN_STATUS_PREFIXES if status.startswith(p)), None)
    if concern is None:
        return None
    if concern == "COMPATIBLE_WITH_SILENT_PASS_HAZARD" and exec_result is not None:
        kq = exec_result.key_quantities or {}
        if kq.get("cf_spalding_fallback_activated") is True:
            return f"{concern}:spalding_fallback_confirmed"
        if kq.get("strouhal_canonical_band_shortcut_fired") is True:
            return f"{concern}:strouhal_canonical_band_shortcut_fired"
    return concern


def _attach_audit_concern(
    report: AttributionReport,
    task_spec: TaskSpec,
    comparison: ComparisonResult,
    *,
    exec_result: Optional[ExecutionResult] = None,
) -> AttributionReport:
    report.audit_concern = _resolve_audit_concern(
        task_spec,
        comparison,
        exec_result=exec_result,
    )
    return report

logger = logging.getLogger(__name__)


# =============================================================================
# Solver-level error pattern registry
# Each entry: (regex_or_None, cause_label, confidence, suggestion_factory)
# suggestion_factory receives (match_dict) -> str
# =============================================================================
_SOLVER_PATTERNS: List[Tuple[Optional[re.Pattern], str, float, callable]] = []


def _register_solver_pattern(
    regex: str,
    cause: str,
    confidence: float,
    suggestion: str,
) -> None:
    """Decorator-free helper: compile and register a solver pattern."""
    compiled = re.compile(regex, re.IGNORECASE | re.MULTILINE)
    _SOLVER_PATTERNS.append((compiled, cause, confidence, lambda _: suggestion))


def _register_solver_pattern_group(
    regex: str,
    cause: str,
    confidence: float,
    suggestion_factory: callable,
) -> None:
    """Register a pattern with named capture groups for dynamic suggestion."""
    compiled = re.compile(regex, re.IGNORECASE | re.MULTILINE)
    _SOLVER_PATTERNS.append((compiled, cause, confidence, suggestion_factory))


# --- kOmegaSST dimension bug (OF10) ---
_register_solver_pattern_group(
    r"Arguments of min have different dimensions",
    "turbulence",
    0.9,
    lambda m: "kOmegaSST dimension bug in OF10 F2(). Switch to kEpsilon for buoyantFoam family.",
)

# --- generic dimension mismatch ---
_register_solver_pattern_group(
    r"Dimension of unit of field .+ is not correct",
    "turbulence",
    0.85,
    lambda m: "Field dimension mismatch. Check turbulence model compatibility with solver.",
)

# --- blockMesh failure ---
_register_solver_pattern_group(
    r"points is not closed|cannot match face planes|blockMesh error",
    "mesh",
    0.9,
    lambda m: "blockMesh geometry error. Check vertex coordinates and face connectivity in blockMeshDict.",
)

# --- solver divergence ---
_register_solver_pattern_group(
    r"Floating point exception|Maximum number of iterations exceeded",
    "solver",
    0.9,
    lambda m: "Solver divergence. Reduce deltaT, lower relaxation factors, or adjust scheme aggressiveness.",
)

# --- unknown_patch_field_type ---
_register_solver_pattern(
    r"Unknown patchField type\s+(?P<bc>\w+)",
    "boundary_condition",
    0.9,
    "Unsupported BC type for this OpenFOAM version. Replace with kqRWallFunction / kLowReWallFunction / fixedValue as appropriate.",
)

# --- missing_initial_field ---
_register_solver_pattern_group(
    r'Cannot find file ".*?/0/(?P<field>[UvpkomegaepsilonnutalphatTprgh]+)"',
    "solver",
    0.85,
    lambda m: f"Required field 0/{m['field']} is missing. Generate it before running the solver.",
)

# --- patch_name_mismatch ---
_register_solver_pattern_group(
    r"(?:Cannot find patch(?:Field)? entry for\s+|patch\s+)(\w+)",
    "boundary_condition",
    0.85,
    lambda m: f"Patch '{m[1]}' in 0/ boundary file not found in polyMesh/boundary. Derive BC files from final mesh patch list.",
)

# --- missing_bc_value ---
_register_solver_pattern(
    r"keyword value is undefined|Essential entry ['\"]value['\"] missing",
    "boundary_condition",
    0.9,
    "Incomplete boundary-condition stanza. Add explicit 'value uniform ...' entry.",
)

# --- floating_point_exception ---
_register_solver_pattern(
    r"Floating point exception|sigFpe|(?<![a-zA-Z])nan(?![a-zA-Z])|(?<![a-zA-Z])inf(?![a-zA-Z])",
    "solver",
    0.95,
    "Numerical blow-up (NaN/Inf). Reduce deltaT, enable adjustTimeStep, or lower scheme aggressiveness.",
)

# --- courant_number_explosion ---
_register_solver_pattern_group(
    r"Courant Number mean:\s*[0-9eE.+\-]+\s*max:\s*(?P<co>[0-9eE.+\-]+)",
    "solver",
    0.8,
    lambda m: f"Coupling number explosion (max Co={m['co']}). Set adjustTimeStep yes; maxCo 0.5.",
)

# --- turbulence_field_unbounded ---
_register_solver_pattern_group(
    r"bounding\s+(?P<field>k|epsilon|omega|nut)\b.*min:\s*-",
    "turbulence",
    0.85,
    lambda m: f"Turbulence field {m['field']} went negative (unbounded). Use safer initial fields, smaller deltaT, or different wall function.",
)

# --- linear_solver_breakdown ---
_register_solver_pattern(
    r"solution singularity|Final residual\s*=\s*nan|GAMG.*failed|DILUPBiCGStab.*failed",
    "solver",
    0.9,
    "Linear solver breakdown. Fix pressure reference/outlet BCs and initialization.",
)

# --- buoyant_setup_missing_field_or_property ---
_register_solver_pattern_group(
    r'Cannot find file ".*?/0/(?P<field>T|p_rgh|alphat)"|'
    r"keyword\s+(TRef|beta|Pr|Cp|g)\s+is undefined|Unknown thermoType",
    "solver",
    0.85,
    lambda m: f"BuoyantFoam setup incomplete: {m.get('field') or m.get(1)} missing or invalid. Validate g, thermo dictionaries, T, p_rgh, and buoyancy parameters.",
)

# --- parameter_plumbing_mismatch ---
# Ra/Re_tau/h_over_d/diameter silently dropped or default-used instead of user-specified
_register_solver_pattern(
    r"parameter.*not found|Ra\s*[=:]\s*1e10\s*(default|assumed)",
    "solver",
    0.7,
    "Parameter plumbing mismatch: Ra or Re_tau may have been silently defaulted. Verify parameter injection in batch reconstruction.",
)

# --- comparator_schema_mismatch ---
# Quantity key exists in result but gold standard schema uses incompatible keys (Nu/Cp/Cf/u_plus without value fallback)
_register_solver_pattern(
    r"quantity.*not found|no gold standard.*found",
    "solver",
    0.7,
    "Comparator schema mismatch: quantity exists but gold standard key schema is incompatible. Expand ResultComparator fallback.",
)

# --- geometry_model_mismatch ---
# Generated geometry differs from benchmark intent (e.g., rectangular pipe vs circular, simplified BFS geometry)
_register_solver_pattern(
    r"reattachment.*length.*mismatch|geometry.*mismatch|channel.*rectangular",
    "solver",
    0.6,
    "Geometry model mismatch: generated geometry differs from benchmark specification. Verify ncx/ncy and geometry type routing.",
)

# --- insufficient_transient_sampling ---
# Transient run completes but insufficient time-history for unsteady metrics (Strouhal etc.)
_register_solver_pattern(
    r"strouhal.*not.*found|no time.*history|transient.*incomplete|insufficient.*samples",
    "solver",
    0.75,
    "Insufficient transient sampling: run may have completed before vortex shedding statistics converged. Increase endTime or reduce time step.",
)

# --- dispatch_metadata_mismatch ---
# Non-regex: handled as a special case after pattern matching
# (see _try_dispatch_mismatch_detection)


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


def _key_coverage_ratio(
    gold_keys: List[str],
    executor_keys: List[str],
) -> float:
    """Compute ratio of gold_standard keys covered by executor output keys."""
    if not gold_keys:
        return 1.0
    covered = sum(1 for k in gold_keys if k in executor_keys)
    return covered / len(gold_keys)


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
        """生成完整的误差归因报告 (支持 solver-level 崩溃归因)"""
        # Stage 0: 无偏差时 — 尝试从 error_message 做 solver-level 归因
        if not comparison.deviations:
            solver_report = self._try_parse_solver_crash(exec_result, task_spec)
            if solver_report is not None:
                return _attach_audit_concern(
                    solver_report,
                    task_spec,
                    comparison,
                    exec_result=exec_result,
                )
            return _attach_audit_concern(
                AttributionReport(chain_complete=True),
                task_spec,
                comparison,
                exec_result=exec_result,
            )

        # Step 1: 定量分析
        max_err, worst_qty = self._find_worst_deviation(comparison.deviations)
        mag_pct = self._deviation_magnitude(comparison.deviations)

        # Step 1b: key_coverage 检测 — Mock 模式或 sampleDict 配置问题
        gold_keys = [d.quantity for d in comparison.deviations]
        executor_keys = list(exec_result.key_quantities.keys())
        coverage = _key_coverage_ratio(gold_keys, executor_keys)
        key_mismatch_cause: Optional[str] = None
        key_mismatch_confidence: float = 0.0
        key_mismatch_recommendation: Optional[str] = None
        if coverage < 0.5:
            if exec_result.is_mock:
                key_mismatch_cause = "mock_executor"
                key_mismatch_confidence = 0.95
                key_mismatch_recommendation = (
                    "MockExecutor key mismatch: returned keys do not cover gold_standard. "
                    "Run Docker real execution to validate."
                )
            else:
                key_mismatch_cause = "sample_config_mismatch"
                key_mismatch_confidence = 0.8
                key_mismatch_recommendation = (
                    f"Executor returned {executor_keys} but gold_standard needs {gold_keys}. "
                    "Check sampleDict field configuration."
                )

        # Step 2: 根因分类
        structured_override = self._match_structured_deviation_cause(
            comparison, exec_result, task_spec
        )
        if key_mismatch_cause and structured_override is None:
            primary, confidence, secondaries = key_mismatch_cause, key_mismatch_confidence, []
        elif structured_override is not None:
            primary, confidence, secondaries = structured_override[0], structured_override[1], []
        else:
            primary, confidence, secondaries = self._classify_root_cause(
                comparison, exec_result, task_spec
            )

        # Step 3: 生成修正建议
        mesh_fix = self._suggest_mesh_fix(primary, task_spec, max_err)
        turb_fix = self._suggest_turbulence_fix(primary, task_spec)
        bc_fix = self._suggest_bc_fix(primary, task_spec)
        solver_fix = self._suggest_solver_fix(primary, task_spec)
        if key_mismatch_recommendation and structured_override is None:
            solver_fix = key_mismatch_recommendation

        # Step 4: 知识库检索
        similar = self._find_similar_cases(task_spec)
        solvers = self._db.list_solver_for_geometry(task_spec.geometry_type)
        turb_models = self._db.list_turbulence_models(task_spec.geometry_type).get(
            task_spec.geometry_type.value, []
        )

        report = AttributionReport(
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
        return _attach_audit_concern(
            report,
            task_spec,
            comparison,
            exec_result=exec_result,
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

    @staticmethod
    def _match_structured_deviation_cause(
        comparison: ComparisonResult,
        exec_result: ExecutionResult,
        task_spec: TaskSpec,
    ) -> Optional[tuple[str, float]]:
        """Structured deviation → cause mapping for Phase 5 T3 patterns."""
        deviations = comparison.deviations

        # 1. COMPARATOR_SCHEMA_MISMATCH: quantity not found (actual=None)
        if any(d.actual is None for d in deviations):
            return ("comparator_schema_mismatch", 0.8)

        # 2. GEOMETRY_MODEL_MISMATCH: reattachment_length on BFS or SIMPLE_GRID
        if (
            task_spec.geometry_type
            in {GeometryType.SIMPLE_GRID, GeometryType.BACKWARD_FACING_STEP}
            and any(d.quantity == "reattachment_length" for d in deviations)
        ):
            return ("geometry_model_mismatch", 0.75)

        # 2b. GEOMETRY_MODEL_MISMATCH: AIRFOIL surrogate yields Cp coordinates
        # outside normalized chord space [0, 1], which indicates we are not
        # sampling a real airfoil surface distribution.
        airfoil_cp_x = exec_result.key_quantities.get("pressure_coefficient_x")
        if (
            task_spec.geometry_type == GeometryType.AIRFOIL
            and airfoil_cp_x
            and any(d.quantity.startswith("pressure_coefficient") for d in deviations)
        ):
            try:
                x_min = min(airfoil_cp_x)
                x_max = max(airfoil_cp_x)
            except TypeError:
                x_min = None
                x_max = None
            if x_min is not None and x_max is not None and (x_min < -0.1 or x_max > 1.1):
                return ("geometry_model_mismatch", 0.85)

        # 3. INSUFFICIENT_TRANSIENT_SAMPLING: TRANSIENT without strouhal
        if (
            task_spec.steady_state == SteadyState.TRANSIENT
            and "strouhal" not in exec_result.key_quantities
            and deviations
        ):
            return ("insufficient_transient_sampling", 0.75)

        # 4. PARAMETER_PLUMBING_MISMATCH: Ra/Re_tau present but deviations exist
        if deviations and (task_spec.Ra is not None or task_spec.Re_tau is not None):
            return ("parameter_plumbing_mismatch", 0.7)

        return None

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

        # Phase 5 T3: structured deviation patterns override scoring
        structured_match = self._match_structured_deviation_cause(
            comparison, exec_result, task_spec
        )
        if structured_match is not None:
            cause, confidence = structured_match
            return cause, confidence, []

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

        # 基于 ErrorType (Phase 5 T3: 5 new ErrorTypes added)
        error_type_scores = {
            ErrorType.CONVERGENCE_FAILURE: {"solver": 0.5, "mesh": 0.2},
            ErrorType.QUANTITY_DEVIATION: {"mesh": 0.3, "turbulence": 0.3, "parameters": 0.2},
            ErrorType.WRONG_BOUNDARY: {"boundary_condition": 0.7},
            ErrorType.WRONG_TURBULENCE_MODEL: {"turbulence": 0.8},
            ErrorType.WRONG_MESH: {"mesh": 0.8},
            ErrorType.WRONG_SOLVER: {"solver": 0.7},
            ErrorType.BUOYANT_ENERGY_SETUP_INCOMPLETE: {"solver": 0.7, "mesh": 0.1},
            ErrorType.PARAMETER_PLUMBING_MISMATCH: {"parameters": 0.8},
            ErrorType.COMPARATOR_SCHEMA_MISMATCH: {"solver": 0.6, "parameters": 0.3},
            ErrorType.GEOMETRY_MODEL_MISMATCH: {"solver": 0.7, "mesh": 0.2},
            ErrorType.INSUFFICIENT_TRANSIENT_SAMPLING: {"solver": 0.6, "parameters": 0.3},
            ErrorType.OTHER: {},
        }

        inferred_error_types: List[ErrorType] = []
        if not exec_result.success:
            inferred_error_types.append(ErrorType.CONVERGENCE_FAILURE)
        if deviations:
            inferred_error_types.append(ErrorType.QUANTITY_DEVIATION)

        for error_type in inferred_error_types:
            for cause, delta in error_type_scores.get(error_type, {}).items():
                scores[cause] += delta

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

    # --------------------------------------------------------------------------
    # Stage 0: Solver-level crash parser (T3 extension)
    # --------------------------------------------------------------------------

    def _try_parse_solver_crash(
        self,
        exec_result: ExecutionResult,
        task_spec: TaskSpec,
    ) -> Optional[AttributionReport]:
        """解析 solver 崩溃错误信息，返回归因报告（无可用偏差时）"""
        err = exec_result.error_message or ""
        if not err:
            return None

        best_cause = "solver"
        best_confidence = 0.0
        best_suggestion = "Solver failed. Check logs for details."
        best_bc_suggestion: Optional[str] = None
        best_solver_suggestion: Optional[str] = None

        # 1. Pattern-based detection
        for compiled_re, cause, confidence, suggestion_fn in _SOLVER_PATTERNS:
            m = compiled_re.search(err)
            if not m:
                continue

            match_dict = m.groupdict()
            effective_cause = cause
            # Phase 5 T3: T/p_rgh/alphat field errors → buoyant_energy_setup_incomplete
            if match_dict.get("field") in {"T", "p_rgh", "alphat"}:
                effective_cause = "buoyant_energy_setup_incomplete"

            should_take = confidence > best_confidence
            if effective_cause == "buoyant_energy_setup_incomplete" and confidence >= best_confidence:
                should_take = True
            if not should_take:
                continue

            best_confidence = confidence
            best_cause = effective_cause
            try:
                if callable(suggestion_fn) and not isinstance(suggestion_fn, str):
                    sug = suggestion_fn(match_dict)
                else:
                    sug = str(suggestion_fn)
            except Exception:
                sug = str(suggestion_fn) if isinstance(suggestion_fn, str) else "Fix required"

            if effective_cause == "boundary_condition":
                best_bc_suggestion = sug
            else:
                best_solver_suggestion = sug

        # 2. dispatch_metadata_mismatch — non-regex heuristic
        dispatch_suggestion = self._try_dispatch_mismatch_detection(exec_result, task_spec, err)
        if dispatch_suggestion is not None:
            best_cause = "solver"
            best_confidence = max(best_confidence, 0.9)
            best_solver_suggestion = (best_solver_suggestion or "") + " " + dispatch_suggestion

        if best_confidence < 0.1:
            return None

        similar = self._find_similar_cases(task_spec)
        solvers = self._db.list_solver_for_geometry(task_spec.geometry_type)
        turb_models = self._db.list_turbulence_models(task_spec.geometry_type).get(
            task_spec.geometry_type.value, []
        )

        return AttributionReport(
            chain_complete=True,
            max_relative_error=None,
            worst_quantity=None,
            deviation_magnitude_pct=None,
            primary_cause=best_cause,
            confidence=best_confidence,
            secondary_causes=[],
            mesh_recommendation=None,
            turbulence_recommendation=None,
            bc_recommendation=best_bc_suggestion,
            solver_recommendation=best_solver_suggestion,
            similar_cases=similar[:3],
            recommended_solvers=solvers,
            recommended_turbulence_models=turb_models,
        )

    def _try_dispatch_mismatch_detection(
        self,
        exec_result: ExecutionResult,
        task_spec: TaskSpec,
        err: str,
    ) -> Optional[str]:
        """检测运行时 solver/generator 与 whitelist benchmark 元数据不匹配的案例"""
        # Detect pimpleFoam being used when icoFoam + laminar is expected
        if "pimpleFoam" in err or "pimpleFoam failed" in err:
            expected_solver = self._db.get_solver_for_case(task_spec.name)
            if expected_solver and expected_solver != "pimpleFoam":
                return (
                    f"Dispatch mismatch: case configured for '{expected_solver}' "
                    f"but generated as pimpleFoam. "
                    f"Verify geometry_type ({task_spec.geometry_type.value}) + "
                    f"flow_type ({task_spec.flow_type.value}) routing."
                )
        return None
