"""Foam-Agent 调用适配器：MockExecutor（测试）+ FoamAgentExecutor（占位符）"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional

from .models import CFDExecutor, TaskSpec, ExecutionResult


class MockExecutor:
    """测试专用执行器：is_mock=True，返回预设结果"""

    # 预设每种流动类型的返回量
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


class FoamAgentExecutor:
    """真实 Foam-Agent 调用适配器（占位符）

    真实使用时需：
    1. 配置 config/foam_agent_config.yaml
    2. 安装 Foam-Agent（https://github.com/csml-rpi/Foam-Agent）
    3. 安装 OpenFOAM
    """

    def __init__(
        self,
        foam_agent_path: Optional[str] = None,
        openfoam_path: Optional[str] = None,
        work_dir: str = "/tmp/cfd-harness-runs",
        timeout_seconds: int = 3600,
    ) -> None:
        self._foam_agent_path = foam_agent_path
        self._openfoam_path = openfoam_path
        self._work_dir = work_dir
        self._timeout = timeout_seconds

    def execute(self, task_spec: TaskSpec) -> ExecutionResult:
        """调用 Foam-Agent 执行仿真（占位符）"""
        raise NotImplementedError(
            "FoamAgentExecutor 未配置。请填写 config/foam_agent_config.yaml "
            "并确保 Foam-Agent 和 OpenFOAM 已安装。"
        )
