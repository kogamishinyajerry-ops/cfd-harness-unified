"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（真实）"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import CFDExecutor, ExecutionResult, FlowType, TaskSpec

# ---------------------------------------------------------------------------
# MockExecutor — unchanged, used for testing
# ---------------------------------------------------------------------------


class MockExecutor:
    """测试专用执行器：is_mock=True，返回预设结果"""

    _PRESET: Dict[str, Dict[str, Any]] = {
        "INTERNAL": {
            "residuals": {"p": 1e-6, "U": 1e-6},
            "key_quantities": {"u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0]},
        },
        "EXTERNAL": {
            "residuals": {"p": 1e-5, "U": 1e-5},
            "key_quantities": {"strouhal_number": 0.165, "cd_mean": 1.36},
        },
        "NATURAL_CONVECTION": {
            "residuals": {"p": 1e-6, "T": 1e-7},
            "key_quantities": {"nusselt_number": 4.52},
        },
    }

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        preset = self._PRESET.get(task_spec.flow_type.value, self._PRESET["INTERNAL"])
        return ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),
            key_quantities=dict(preset["key_quantities"]),
            execution_time_s=0.01,
            raw_output_path=None,
        )


# ---------------------------------------------------------------------------
# FoamAgentExecutor — real adapter
# ---------------------------------------------------------------------------

#: FlowType → foam-agent solver / model key (sensible defaults)
_FLOW_TYPE_MODEL: Dict[FlowType, str] = {
    FlowType.INTERNAL: "simpleFoam",
    FlowType.EXTERNAL: "rhoSimpleFoam",
    FlowType.NATURAL_CONVECTION: "buoyantBoussinesqSimpleFoam",
}


class FoamAgentExecutor:
    """真实 Foam-Agent 调用适配器。

    通过 ``foam-agent run --spec <spec_file> --output <result_file>`` 执行
    OpenFOAM 仿真，并解析 JSON 结果构建 :class:`ExecutionResult`。

    参数
    ----
    foam_agent_path:
        ``foam-agent`` 可执行文件路径。默认为 ``"foam-agent"``（从 PATH 查找）。
    openfoam_path:
        OpenFOAM 安装根目录（可选，设置环境变量 ``WM_PROJECT_DIR``）。
    work_dir:
        存放临时 spec 文件和输出文件的目录。
    timeout_seconds:
        单次仿真超时秒数。
    """

    def __init__(
        self,
        foam_agent_path: Optional[str] = None,
        openfoam_path: Optional[str] = None,
        work_dir: str = "/tmp/cfd-harness-runs",
        timeout_seconds: int = 3600,
    ) -> None:
        self._foam_agent_path = foam_agent_path or "foam-agent"
        self._openfoam_path = openfoam_path
        self._work_dir = work_dir
        self._timeout = timeout_seconds

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        """将 ``task_spec`` 写入临时 YAML 文件，调用 ``foam-agent``，
        解析结果返回 :class:`ExecutionResult`。 """
        t0 = time.monotonic()

        # 1. 找到 foam-agent
        agent_cmd = self._resolve_agent()
        if isinstance(agent_cmd, ExecutionResult):
            return agent_cmd  # 返回错误结果，不 crash

        # 2. 准备工作目录
        work = Path(self._work_dir)
        work.mkdir(parents=True, exist_ok=True)

        # 3. 构建并写入 spec 文件
        spec_path = work / f"spec_{os.getpid()}_{id(task_spec)}.yaml"
        try:
            self._write_spec(task_spec, spec_path)
        except Exception as exc:
            return self._fail(
                f"Failed to write foam-agent spec file: {exc}",
                time.monotonic() - t0,
            )

        # 4. 调用 foam-agent
        result_path = work / f"result_{os.getpid()}_{id(task_spec)}.json"
        try:
            self._run_agent(agent_cmd, spec_path, result_path)
        except Exception as exc:
            return self._fail(
                f"foam-agent execution failed: {exc}",
                time.monotonic() - t0,
            )
        finally:
            spec_path.unlink(missing_ok=True)

        # 5. 解析结果文件
        try:
            parsed = self._parse_result(result_path)
        except Exception as exc:
            return self._fail(
                f"Failed to parse foam-agent output: {exc}",
                time.monotonic() - t0,
                raw_output_path=str(result_path),
            )
        finally:
            result_path.unlink(missing_ok=True)

        elapsed = time.monotonic() - t0
        return ExecutionResult(
            success=True,
            is_mock=False,
            residuals=parsed.get("residuals", {}),
            key_quantities=parsed.get("key_quantities", {}),
            execution_time_s=elapsed,
            raw_output_path=str(result_path) if result_path.exists() else None,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_agent(self) -> str | ExecutionResult:
        """确认 foam-agent 可用并返回其路径。不可用时返回错误结果。"""
        path = self._foam_agent_path
        if path != "foam-agent" and not Path(path).is_file():
            return self._fail(
                f"foam-agent not found at configured path: {path}",
                0.0,
            )
        found = shutil.which(path)
        if not found:
            return self._fail(
                f"foam-agent not found in PATH. "
                f"Install Foam-Agent (https://github.com/csml-rpi/Foam-Agent) "
                f"and ensure it is accessible.",
                0.0,
            )
        return found

    def _write_spec(self, task_spec: TaskSpec, dest: Path) -> None:
        """将 TaskSpec 序列化为 foam-agent YAML spec 文件。"""
        spec: Dict[str, Any] = {
            "name": task_spec.name,
            "flow_type": task_spec.flow_type.value,
            "geometry_type": task_spec.geometry_type.value,
            "steady_state": task_spec.steady_state.value,
            "compressibility": task_spec.compressibility.value,
            # foam-agent 模型选择
            "model": _FLOW_TYPE_MODEL.get(task_spec.flow_type, "simpleFoam"),
        }

        if task_spec.Re is not None:
            spec["Re"] = task_spec.Re
        if task_spec.Ma is not None:
            spec["Ma"] = task_spec.Ma

        if task_spec.boundary_conditions:
            spec["boundary_conditions"] = dict(task_spec.boundary_conditions)

        if task_spec.description:
            spec["description"] = task_spec.description

        dest.write_text(yaml.dump(spec, sort_keys=False), encoding="utf-8")

    def _run_agent(
        self,
        agent_cmd: str,
        spec_path: Path,
        result_path: Path,
    ) -> None:
        """执行 ``foam-agent run --spec <spec> --output <output>`` 。"""
        env = os.environ.copy()
        if self._openfoam_path:
            env["WM_PROJECT_DIR"] = self._openfoam_path

        # foam-agent 会将结果写入 --output 指定路径
        completed = subprocess.run(
            [
                agent_cmd,
                "run",
                "--spec",
                str(spec_path),
                "--output",
                str(result_path),
            ],
            capture_output=True,
            text=True,
            timeout=self._timeout,
            env=env,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "(no stderr)"
            raise RuntimeError(
                f"foam-agent returned code {completed.returncode}: {stderr}"
            )

    def _parse_result(self, result_path: Path) -> Dict[str, Any]:
        """解析 foam-agent JSON 输出文件。"""
        # foam-agent 输出文件（ --output 指定的位置）
        raw = result_path.read_text(encoding="utf-8")
        data = json.loads(raw)

        # 支持两种常见格式：
        #   {"success": true, "residuals": {...}, "key_quantities": {...}}
        #   {"results": {"residuals": {...}, "key_quantities": {...}}}
        if "results" in data:
            data = data["results"]

        return {
            "residuals": data.get("residuals", {}),
            "key_quantities": data.get("key_quantities", {}),
        }

    @staticmethod
    def _fail(message: str, elapsed: float, raw_output_path: Optional[str] = None) -> ExecutionResult:
        """返回一个表示失败的 ExecutionResult（不 raise）。"""
        return ExecutionResult(
            success=False,
            is_mock=False,
            residuals={},
            key_quantities={},
            execution_time_s=elapsed,
            raw_output_path=raw_output_path,
            error_message=message,
        )
