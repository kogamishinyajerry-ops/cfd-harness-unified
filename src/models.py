"""共享数据类型：Enum、dataclass、Protocol 定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class FlowType(Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"
    NATURAL_CONVECTION = "NATURAL_CONVECTION"


class GeometryType(Enum):
    SIMPLE_GRID = "SIMPLE_GRID"
    BACKWARD_FACING_STEP = "BACKWARD_FACING_STEP"
    BODY_IN_CHANNEL = "BODY_IN_CHANNEL"
    NATURAL_CONVECTION_CAVITY = "NATURAL_CONVECTION_CAVITY"
    AIRFOIL = "AIRFOIL"
    IMPINGING_JET = "IMPINGING_JET"
    CUSTOM = "CUSTOM"


class SteadyState(Enum):
    STEADY = "STEADY"
    TRANSIENT = "TRANSIENT"


class Compressibility(Enum):
    INCOMPRESSIBLE = "INCOMPRESSIBLE"
    COMPRESSIBLE = "COMPRESSIBLE"


class ErrorType(Enum):
    WRONG_BOUNDARY = "WRONG_BOUNDARY"
    WRONG_SOLVER = "WRONG_SOLVER"
    WRONG_TURBULENCE_MODEL = "WRONG_TURBULENCE_MODEL"
    WRONG_MESH = "WRONG_MESH"
    CONVERGENCE_FAILURE = "CONVERGENCE_FAILURE"
    QUANTITY_DEVIATION = "QUANTITY_DEVIATION"
    OTHER = "OTHER"


class ImpactScope(Enum):
    LOCAL = "LOCAL"       # 影响单个案例
    CLASS = "CLASS"       # 影响同类型案例
    GLOBAL = "GLOBAL"     # 影响所有案例


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskSpec:
    """从 Notion 读取的任务规格"""
    name: str
    geometry_type: GeometryType
    flow_type: FlowType
    steady_state: SteadyState
    compressibility: Compressibility
    Re: Optional[float] = None
    Ma: Optional[float] = None
    boundary_conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    notion_task_id: Optional[str] = None


@dataclass
class ExecutionResult:
    """CFD 执行结果"""
    success: bool
    is_mock: bool
    residuals: Dict[str, float] = field(default_factory=dict)
    key_quantities: Dict[str, Any] = field(default_factory=dict)
    execution_time_s: float = 0.0
    raw_output_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeviationDetail:
    """单个物理量的偏差记录"""
    quantity: str
    expected: Any
    actual: Any
    relative_error: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class ComparisonResult:
    """结果 vs Gold Standard 对比"""
    passed: bool
    deviations: List[DeviationDetail] = field(default_factory=list)
    summary: str = ""
    gold_standard_id: Optional[str] = None


@dataclass
class CorrectionSpec:
    """修正规格：记录偏差并描述如何修复"""
    error_type: ErrorType
    wrong_output: Dict[str, Any]
    correct_output: Dict[str, Any]
    human_reason: str
    evidence: str
    impact_scope: ImpactScope
    root_cause: str
    fix_action: str
    needs_replay: bool = False
    task_spec_name: Optional[str] = None
    created_at: Optional[str] = None
    # 误差自动归因链 (Phase 4)
    attribution: Optional["AttributionReport"] = None


@dataclass
class AttributionReport:
    """结构化误差归因报告：偏差→定量分析→根因分类→修正建议"""
    # 归因链状态
    chain_complete: bool = False
    # 定量分析
    max_relative_error: Optional[float] = None
    worst_quantity: Optional[str] = None
    deviation_magnitude_pct: Optional[float] = None  # 偏差幅度百分比
    # 根因分类
    primary_cause: str = "unknown"  # mesh / boundary_condition / turbulence / solver / parameters
    confidence: float = 0.0  # 0.0-1.0
    secondary_causes: List[str] = field(default_factory=list)
    # 定量修正建议
    mesh_recommendation: Optional[str] = None  # e.g. "increase ncx from 40 to 80 in separation zone"
    turbulence_recommendation: Optional[str] = None  # e.g. "switch to k-omega SST for better near-wall"
    bc_recommendation: Optional[str] = None  # e.g. "verify velocity inlet profile"
    solver_recommendation: Optional[str] = None  # e.g. "try pimpleFoam for better convergence"
    # 知识库检索结果
    similar_cases: List[str] = field(default_factory=list)  # similar case IDs from knowledge DB
    recommended_solvers: List[str] = field(default_factory=list)
    recommended_turbulence_models: List[str] = field(default_factory=list)


@dataclass
class SystematicPattern:
    """批量级别系统性误差模式"""
    cause: str  # e.g. "mesh", "turbulence", "mock_executor", "sample_config_mismatch"
    affected_cases: List[str] = field(default_factory=list)
    frequency: float = 0.0  # affected / total
    confidence: str = "low"  # high (>0.5), medium (>0.3), low
    recommendation: str = ""


@dataclass
class BatchResult:
    """批量执行汇总结果"""
    total: int
    passed: int
    failed: int
    errors: List[str]
    results: List["ComparisonResult"] = field(default_factory=list)
    attribution_reports: List[Optional["AttributionReport"]] = field(default_factory=list)
    systematic_patterns: List[SystematicPattern] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CFDExecutor Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class CFDExecutor(Protocol):
    """CFD 执行引擎接口（Protocol，不用 ABC）"""

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        """执行 CFD 仿真，返回结果"""
        ...
