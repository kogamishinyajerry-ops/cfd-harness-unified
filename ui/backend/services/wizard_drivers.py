"""Wizard solver-driver abstractions · Stage 8b prep.

Stage 8a's `routes/wizard.py:_run_phase_script` mixed two concerns:
  1. The fixed mock script DATA (`_PHASE_SCRIPT` list of phase dicts)
  2. The walking LOGIC (yield phase_start / log / metric / phase_done /
     run_done events, paced via asyncio.sleep)

For Stage 8b — when `dec-v61-058..063 / feat/c3a..c` line-B branches
drain and `foam_agent_adapter` is no longer being actively iterated —
we need to swap the script DATA for real solver subprocess output WITHOUT
rewriting the walking LOGIC. Round-3 Q13 audit confirmed the wire
schema (RunPhaseEvent) is mock-shape-free, so the walker can stay
schema-stable while the source flips.

This module formalises that plug-in surface as a `SolverDriver`
protocol. `MockSolverDriver` is the Stage 8a implementation. Stage 8b
adds `RealSolverDriver` (subprocess wrapper) as a sibling — only THIS
file changes. `routes/wizard.py` picks a driver based on env var
(`CFD_HARNESS_WIZARD_SOLVER=mock|real`, default `mock` for now).

NOTE: this file does NOT import `foam_agent_adapter` or any line-B
code path. Stage 8b's RealSolverDriver lands as a future addition.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator, Protocol


# Standard SSE wire format: each yielded string is one `data: ...\n\n` line.
# Tests assert against this contract; do not change it without bumping
# the RunPhaseEvent schema version + frontend handler.
def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


class SolverDriver(Protocol):
    """Strategy interface for the wizard's run pipeline.

    Implementations must:
      - Yield SSE-formatted strings (not raw RunPhaseEvent objects;
        the SSE wrapping is part of the contract so the route is just
        a thin pass-through).
      - Walk through 5 phases in order: geometry → mesh → boundary →
        solver → compare.
      - Emit at minimum: `phase_start` per phase, `phase_done` per phase
        with status, and one `run_done` to close.
      - May emit any number of `log` events per phase, and `metric`
        events on the solver phase for residuals.
      - Honour the case_id by including it in early/run_done events for
        traceability.
    """

    async def run(self, case_id: str) -> AsyncIterator[str]:
        ...


# --- Mock implementation (Stage 8a behaviour, refactored) ------------------
# Identical event sequence to the original `routes/wizard.py:_run_phase_script`
# pre-refactor. Tests `test_run_stream_walks_five_phases_and_closes` and
# `test_q13_*` are the regression guards.

_PHASE_SCRIPT: list[dict] = [
    {
        "phase": "geometry",
        "open_msg": "正在生成几何与边界标记...",
        "logs": [
            "解析模板几何参数",
            "构造 blockMeshDict 拓扑骨架",
            "标记边界 patch (top / walls)",
        ],
        "summary_template": "geometry OK · {patch_count} patches · domain bounds 1×1 m",
        "patch_count": 4,
        "delay_per_log": 0.25,
    },
    {
        "phase": "mesh",
        "open_msg": "运行 blockMesh 生成结构化网格...",
        "logs": [
            "Reading blockMeshDict",
            "Creating block 0 (40 40 1)",
            "Creating mesh from blocks",
            "Writing polyMesh",
            "Mesh non-orthogonality Max: 0.0  average: 0.0",
            "Max skewness = 1.4e-15 OK.",
        ],
        "summary_template": "mesh OK · 1600 cells · skew 1e-15 · non-orth 0°",
        "delay_per_log": 0.15,
    },
    {
        "phase": "boundary",
        "open_msg": "写入 0/ 文件夹边界条件...",
        "logs": [
            "U  : top=fixedValue (1,0,0); walls=noSlip",
            "p  : zeroGradient on all walls; reference cell at (0,0,0)",
            "nu : 1.0e-2 (Re=100 with U=1, L=1)",
        ],
        "summary_template": "BCs OK · 3 fields written · ν=1e-2",
        "delay_per_log": 0.2,
    },
    {
        "phase": "solver",
        "open_msg": "icoFoam 求解器迭代中...",
        "logs": [
            "Time = 0.01s    Ux residual 1.2e-2    p residual 5.6e-3",
            "Time = 0.05s    Ux residual 4.1e-3    p residual 2.0e-3",
            "Time = 0.10s    Ux residual 1.3e-3    p residual 6.4e-4",
            "Time = 0.20s    Ux residual 3.8e-4    p residual 1.7e-4",
            "Time = 0.30s    Ux residual 1.1e-4    p residual 4.9e-5",
            "Time = 0.50s    Ux residual 2.3e-5    p residual 9.8e-6 (converged)",
        ],
        "summary_template": "converged · 6 timesteps · final p res 9.8e-6",
        "delay_per_log": 0.3,
        "metrics": [
            ("residual_p", 5.6e-3),
            ("residual_p", 2.0e-3),
            ("residual_p", 6.4e-4),
            ("residual_p", 1.7e-4),
            ("residual_p", 4.9e-5),
            ("residual_p", 9.8e-6),
        ],
    },
    {
        "phase": "compare",
        "open_msg": "采样观测量并对照 gold standard...",
        "logs": [
            "Sample u_centerline along x=0.5",
            "Compare to Ghia 1982 Table I (17 points)",
            "Max deviation: 4.2% at y=0.4375",
        ],
        "summary_template": "compare HAZARD · max deviation 4.2% (within 5% tolerance)",
        "delay_per_log": 0.4,
    },
]


class MockSolverDriver:
    """Stage 8a in-process mock pipeline. No subprocess, no I/O — just
    the fixed `_PHASE_SCRIPT` script paced via asyncio.sleep so the UI
    animates naturally.

    Source-of-truth for what every wizard run looks like in the absence
    of real OpenFOAM (CI environments, dev shells without docker, etc.)."""

    name = "mock"

    async def run(self, case_id: str) -> AsyncIterator[str]:
        yield _sse({
            "type": "log", "phase": None, "t": time.time(),
            "line": (
                f"[wizard] case_id={case_id} starting mock pipeline "
                "(Stage 8a · MockSolverDriver)"
            ),
        })

        for stage in _PHASE_SCRIPT:
            phase = stage["phase"]
            yield _sse({
                "type": "phase_start", "phase": phase, "t": time.time(),
                "message": stage["open_msg"],
            })
            await asyncio.sleep(0.1)

            metrics = stage.get("metrics") or []
            for i, line in enumerate(stage["logs"]):
                yield _sse({
                    "type": "log", "phase": phase, "t": time.time(), "line": line,
                })
                if i < len(metrics):
                    key, val = metrics[i]
                    yield _sse({
                        "type": "metric", "phase": phase, "t": time.time(),
                        "metric_key": key, "metric_value": val,
                    })
                await asyncio.sleep(stage["delay_per_log"])

            summary = stage["summary_template"].format(**stage)
            yield _sse({
                "type": "phase_done", "phase": phase, "t": time.time(),
                "status": "ok", "summary": summary,
            })
            await asyncio.sleep(0.05)

        yield _sse({
            "type": "run_done", "phase": None, "t": time.time(),
            "summary": (
                f"run complete · case_id={case_id} · 5 phases OK · "
                "mock execution (Stage 8a — real solver lands in 8b)"
            ),
        })


# Stage 8b plug-in point. When line-B drains and foam_agent_adapter
# stabilises, add a `RealSolverDriver` class here implementing the
# same `run(case_id)` async-iterator contract via subprocess wrappers
# around blockMesh / simpleFoam / etc. The route below picks driver
# by env var; default stays `mock` until the real driver is reviewed
# end-to-end.

_DRIVER_REGISTRY: dict[str, SolverDriver] = {
    "mock": MockSolverDriver(),
}


def get_driver(name: str | None = None) -> SolverDriver:
    """Look up driver by name. Defaults to 'mock'. Unknown names fall
    back to 'mock' with a stderr warning rather than 500ing the route —
    hands-off failure mode is the right default for an onboarding-tier
    surface."""
    import os
    import sys

    requested = (name or os.environ.get("CFD_HARNESS_WIZARD_SOLVER", "mock")).lower()
    if requested not in _DRIVER_REGISTRY:
        print(
            f"[wizard] unknown solver driver {requested!r}; falling back to "
            "'mock'. Available: " + ", ".join(_DRIVER_REGISTRY),
            file=sys.stderr,
        )
        requested = "mock"
    return _DRIVER_REGISTRY[requested]
