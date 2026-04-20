"""本地知识库：YAML 驱动的 Gold Standard 和 CorrectionSpec 存储"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import (
    Compressibility,
    CorrectionSpec,
    ErrorType,
    FlowType,
    GeometryType,
    ImpactScope,
    SteadyState,
    TaskSpec,
)

logger = logging.getLogger(__name__)

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


class KnowledgeDB:
    """本地 YAML 知识库

    目录结构：
        knowledge/
        ├── whitelist.yaml          # 冷启动白名单
        ├── gold_standards/         # 每个案例一个 YAML 文件（可选）
        └── corrections/            # CorrectionSpec 历史
    """

    def __init__(self, knowledge_dir: Optional[Path] = None) -> None:
        self._root = knowledge_dir or _DEFAULT_KNOWLEDGE_DIR
        self._whitelist_path = self._root / "whitelist.yaml"
        self._corrections_dir = self._root / "corrections"
        self._corrections_dir.mkdir(parents=True, exist_ok=True)

        # 缓存已加载的白名单
        self._whitelist: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Gold Standard
    # ------------------------------------------------------------------

    def load_gold_standard(self, task_name: str) -> Optional[Dict[str, Any]]:
        """按任务名加载对应的 Gold Standard 数据"""
        whitelist = self._load_whitelist()
        for case in whitelist.get("cases", []):
            if case.get("name") == task_name or case.get("id") == task_name:
                return case.get("gold_standard")
        return None

    def list_whitelist_cases(self) -> List[TaskSpec]:
        """返回白名单中所有案例的 TaskSpec 列表"""
        whitelist = self._load_whitelist()
        result = []
        for case in whitelist.get("cases", []):
            try:
                spec = TaskSpec(
                    name=case["name"],
                    geometry_type=GeometryType(case.get("geometry_type", "SIMPLE_GRID")),
                    flow_type=FlowType(case.get("flow_type", "INTERNAL")),
                    steady_state=SteadyState(case.get("steady_state", "STEADY")),
                    compressibility=Compressibility(case.get("compressibility", "INCOMPRESSIBLE")),
                    Re=case.get("parameters", {}).get("Re"),
                    Ma=case.get("parameters", {}).get("Ma"),
                    boundary_conditions=case.get("boundary_conditions", {}),
                    description=case.get("reference", ""),
                )
                result.append(spec)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed whitelist case %s: %s", case.get("id"), e)
        return result

    # ------------------------------------------------------------------
    # Knowledge Query API — geometry→turbulence→BC→mesh→result 链路查询
    # ------------------------------------------------------------------

    def query_cases(
        self,
        geometry_type: Optional[GeometryType] = None,
        flow_type: Optional[FlowType] = None,
        steady_state: Optional[SteadyState] = None,
        compressibility: Optional[Compressibility] = None,
    ) -> List[Dict[str, Any]]:
        """通用查询：按条件筛选白名单案例。

        Returns:
            List of matching case dicts with full metadata (including gold_standard).
        """
        whitelist = self._load_whitelist()
        results = []
        for case in whitelist.get("cases", []):
            if geometry_type and case.get("geometry_type") != geometry_type.value:
                continue
            if flow_type and case.get("flow_type") != flow_type.value:
                continue
            if steady_state and case.get("steady_state") != steady_state.value:
                continue
            if compressibility and case.get("compressibility") != compressibility.value:
                continue
            results.append(case)
        return results

    def get_execution_chain(self, case_id: str) -> Optional[Dict[str, Any]]:
        """返回指定案例的完整执行链路：geometry→turbulence→BC→mesh→result。

        Returns:
            Dict with keys: geometry_type, flow_type, solver, turbulence_model,
            boundary_conditions, mesh_strategy, gold_standard. Returns None if not found.
        """
        whitelist = self._load_whitelist()
        for case in whitelist.get("cases", []):
            if case.get("id") == case_id or case.get("name") == case_id:
                return self._build_chain(case)
        return None

    def list_turbulence_models(
        self, geometry_type: Optional[GeometryType] = None
    ) -> Dict[str, List[str]]:
        """返回每种 geometry_type 对应的湍流模型列表。

        用于 Knowledge Query API：给定几何，返回可用湍流模型。
        """
        whitelist = self._load_whitelist()
        model_map: Dict[str, List[str]] = {}
        for case in whitelist.get("cases", []):
            geom = case.get("geometry_type")
            turb = case.get("turbulence_model", "k-epsilon (default)")
            if geometry_type and geom != geometry_type.value:
                continue
            if geom not in model_map:
                model_map[geom] = []
            if turb not in model_map[geom]:
                model_map[geom].append(turb)
        return model_map

    def list_solver_for_geometry(
        self, geometry_type: GeometryType, steady_state: Optional[SteadyState] = None
    ) -> List[str]:
        """返回给定几何类型对应的推荐求解器列表。"""
        whitelist = self._load_whitelist()
        solvers: List[str] = []
        for case in whitelist.get("cases", []):
            if case.get("geometry_type") != geometry_type.value:
                continue
            if steady_state and case.get("steady_state") != steady_state.value:
                continue
            solver = case.get("solver", self._default_solver(
                FlowType(case.get("flow_type", "INTERNAL")),
                SteadyState(case.get("steady_state", "STEADY")),
            ))
            if solver not in solvers:
                solvers.append(solver)
        return solvers

    def get_solver_for_case(self, case_name: str) -> Optional[str]:
        """根据case名称从whitelist返回期望的solver（用于dispatch归因）"""
        whitelist = self._load_whitelist()
        for case in whitelist.get('cases', []):
            name = case.get('name', '')
            # match by id (slug) or name
            if case.get('id') == case_name or name == case_name:
                return case.get('solver')
        return None

    def _build_chain(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """为单个 case 构建完整的执行链路描述。"""
        flow = FlowType(case.get("flow_type", "INTERNAL"))
        steady = SteadyState(case.get("steady_state", "STEADY"))
        return {
            "case_id": case.get("id"),
            "case_name": case.get("name"),
            "reference": case.get("reference"),
            "geometry_type": case.get("geometry_type"),
            "flow_type": case.get("flow_type"),
            "steady_state": case.get("steady_state"),
            "compressibility": case.get("compressibility"),
            "parameters": case.get("parameters", {}),
            "boundary_conditions": case.get("boundary_conditions", {}),
            "solver": case.get("solver", self._default_solver(flow, steady)),
            "turbulence_model": case.get("turbulence_model", self._default_turbulence(flow)),
            "mesh_strategy": case.get("mesh_strategy", "structured (blockMesh)"),
            "gold_standard": case.get("gold_standard"),
        }

    @staticmethod
    def _default_solver(flow: FlowType, steady: SteadyState) -> str:
        """根据流型和稳态类型推荐求解器。"""
        if flow == FlowType.NATURAL_CONVECTION:
            return "buoyantSimpleFoam"
        if steady == SteadyState.TRANSIENT:
            return "pimpleFoam"
        if flow == FlowType.EXTERNAL:
            return "simpleFoam"
        return "icoFoam"

    @staticmethod
    def _default_turbulence(flow: FlowType) -> str:
        """根据流型推荐湍流模型。"""
        if flow == FlowType.NATURAL_CONVECTION:
            return "k-omega SST"
        if flow == FlowType.EXTERNAL:
            return "k-omega SST"
        return "k-epsilon"

    # ------------------------------------------------------------------
    # CorrectionSpec
    # ------------------------------------------------------------------

    def save_correction(self, correction: CorrectionSpec) -> Path:
        """把 CorrectionSpec 序列化为 YAML 文件，返回文件路径"""
        ts = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        safe_name = (correction.task_spec_name or "unknown").replace(" ", "_").lower()
        filename = f"{ts}_{safe_name}_{correction.error_type.value}.yaml"
        path = self._corrections_dir / filename
        data = {
            "error_type": correction.error_type.value,
            "wrong_output": correction.wrong_output,
            "correct_output": correction.correct_output,
            "human_reason": correction.human_reason,
            "evidence": correction.evidence,
            "impact_scope": correction.impact_scope.value,
            "root_cause": correction.root_cause,
            "fix_action": correction.fix_action,
            "needs_replay": correction.needs_replay,
            "task_spec_name": correction.task_spec_name,
            "created_at": correction.created_at or ts,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        logger.info("Saved correction: %s", path)
        return path

    def load_corrections(self, task_name: Optional[str] = None) -> List[CorrectionSpec]:
        """从 corrections/ 目录加载历史 CorrectionSpec 列表"""
        results = []
        for yaml_path in sorted(self._corrections_dir.glob("*.yaml")):
            try:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if task_name and data.get("task_spec_name") != task_name:
                    continue
                spec = CorrectionSpec(
                    error_type=ErrorType(data["error_type"]),
                    wrong_output=data.get("wrong_output", {}),
                    correct_output=data.get("correct_output", {}),
                    human_reason=data.get("human_reason", ""),
                    evidence=data.get("evidence", ""),
                    impact_scope=ImpactScope(data.get("impact_scope", "LOCAL")),
                    root_cause=data.get("root_cause", ""),
                    fix_action=data.get("fix_action", ""),
                    needs_replay=data.get("needs_replay", False),
                    task_spec_name=data.get("task_spec_name"),
                    created_at=data.get("created_at"),
                )
                results.append(spec)
            except (KeyError, ValueError, yaml.YAMLError) as e:
                logger.warning("Skipping malformed correction file %s: %s", yaml_path, e)
        return results

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _load_whitelist(self) -> Dict[str, Any]:
        if self._whitelist is None:
            if not self._whitelist_path.exists():
                logger.warning("whitelist.yaml not found at %s", self._whitelist_path)
                self._whitelist = {"cases": []}
            else:
                with open(self._whitelist_path, encoding="utf-8") as f:
                    self._whitelist = yaml.safe_load(f) or {"cases": []}
        return self._whitelist
