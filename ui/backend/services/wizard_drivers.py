"""Wizard solver-driver abstractions.

Two implementations of the `SolverDriver` protocol share a single SSE
wire schema (`RunPhaseEvent`, audited mock-shape-free in Q13):

  - `MockSolverDriver` (Stage 8a) — fixed 5-phase script paced via
    asyncio.sleep, no Docker / no OpenFOAM. Source-of-truth demo path.
  - `RealSolverDriver` (M1 · 2026-04-26) — wraps
    `src.foam_agent_adapter.FoamAgentExecutor.execute()` (synchronous,
    blocking, ~10-300s) with thread-pool dispatch + heartbeat log
    events. Whitelist defaults only; M2 wires user_drafts overrides.

`get_driver()` picks by env var `CFD_HARNESS_WIZARD_SOLVER=mock|real`,
default `mock`. `routes/wizard.py` is a thin pass-through.

Line-A / Line-B isolation contract (per .planning/ROADMAP.md): this
module imports ONLY `FoamAgentExecutor.execute()` public surface from
`src.foam_agent_adapter` — never modifies internals. Imports of `src.*`
are deferred to call-time so test imports of `wizard_drivers` don't
pull in 8000+ LOC of adapter code.
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


# --- Real implementation (M1+M2 · Workbench Closed-Loop main-line) ---------
# Wraps `src.foam_agent_adapter.FoamAgentExecutor.execute()` (synchronous,
# blocking, ~10-300s for real Docker+OpenFOAM runs) into the same async-iter
# SSE contract MockSolverDriver satisfies.
#
# Source priority (M2):
#   1. ui/backend/user_drafts/{case_id}.yaml — what /workbench/case/{id}/edit
#      most recently saved (matches case_editor.py PUT semantics).
#   2. knowledge/whitelist.yaml entry — vanilla baseline.
#
# Bursty SSE warning: heartbeat log lines flow during the blocking execute()
# (every HEARTBEAT_INTERVAL_S), then a sudden burst of metric+phase_done
# +run_done events when execute() returns. This is acceptable —
# proves the integration. Real-time log tailing during execute() is M3/M4
# scope if it turns out to be necessary.


_HEARTBEAT_INTERVAL_S = 2.5  # 2-3s feels responsive without flooding


# --- M4 · Docker / OpenFOAM failure classifier -----------------------------
# Maps raw stderr / exception text → a small set of categories so the UI
# can show a readable banner instead of dumping the whole FOAM FATAL trace.
# First match wins; ordering matters — Docker-class hints precede solver-class
# hints because a Docker-down failure can cascade into "command not found"
# which would otherwise look like an openfoam_missing.

# Keep the categories closed-set so the frontend banner can have explicit
# colour + copy for each. Adding a new category needs both backend + frontend.
_FAILURE_CATEGORIES = (
    "docker_missing",
    "openfoam_missing",
    "mesh_failed",
    "solver_diverged",
    "postprocess_failed",
    "unknown_error",
)


# (pattern_lowercase, category) — pattern is a plain substring match against
# the lowercased haystack. Priority is the order of this list.
_FAILURE_HINTS: list[tuple[str, str]] = [
    # --- Docker daemon / CLI absent --------------------------------------
    ("cannot connect to the docker daemon", "docker_missing"),
    ("docker daemon is not running", "docker_missing"),
    ("docker daemon", "docker_missing"),
    ("error response from daemon", "docker_missing"),
    ("docker: command not found", "docker_missing"),
    ("docker.errors.dockerexception", "docker_missing"),
    # --- Container not running / image missing ---------------------------
    ("no such container", "openfoam_missing"),
    ("not found: name=cfd-openfoam", "openfoam_missing"),
    ("container cfd-openfoam", "openfoam_missing"),
    # --- OpenFOAM binary missing inside container ------------------------
    ("blockmesh: command not found", "openfoam_missing"),
    ("simplefoam: command not found", "openfoam_missing"),
    ("icofoam: command not found", "openfoam_missing"),
    ("buoyantfoam: command not found", "openfoam_missing"),
    ("pimplefoam: command not found", "openfoam_missing"),
    # --- Mesh generation failures (priority: explicit blockMesh phase) ---
    ("foam fatal error" , "solver_diverged"),  # default for FATAL — refined below
    # The blockMesh-specific markers below run BEFORE the generic FATAL
    # because we walk in order. They override solver_diverged when they
    # appear in the same haystack.
]


# Markers that, when found, REFINE an earlier classification. Each rule
# checks the haystack for a substring; if matched, it overrides the
# category that would have been picked above.
_FAILURE_OVERRIDES: list[tuple[str, str]] = [
    # Mesh-specific markers — refine generic FATAL → mesh_failed. We
    # intentionally do NOT have a bare "blockmesh" override here because
    # "blockMesh: command not found" should classify as openfoam_missing,
    # not mesh_failed. The non-orthogonality / negative-cell-volume markers
    # only fire on real mesh failures during blockMesh/snappyHexMesh runs.
    ("non-orthogonality", "mesh_failed"),
    ("negative cell volume", "mesh_failed"),
    # Solver-divergence markers
    ("continuity error", "solver_diverged"),
    ("floating point exception", "solver_diverged"),
    ("max(co)", "solver_diverged"),
    # Post-process failures — only after solver completed
    ("samplefile", "postprocess_failed"),
    ("foamtovtk", "postprocess_failed"),
    ("post-process", "postprocess_failed"),
]


_REMEDIATION_HINTS: dict[str, str] = {
    "docker_missing": (
        "Docker daemon is not reachable. Start Docker Desktop / colima / "
        "rootless docker and retry."
    ),
    "openfoam_missing": (
        "The cfd-openfoam container or its OpenFOAM binaries are missing. "
        "Run `docker compose up cfd-openfoam` (or your equivalent bootstrap)."
    ),
    "mesh_failed": (
        "Mesh generation (blockMesh / snappyHexMesh) failed. Check geometry "
        "parameters — non-orthogonality or negative cell volumes usually "
        "mean Re/mesh-size combination is too aggressive for this case."
    ),
    "solver_diverged": (
        "Solver diverged (continuity error, max(Co)>>1, or NaN). Lower Re, "
        "increase under-relaxation, or use smaller endTime / Δt."
    ),
    "postprocess_failed": (
        "Solver finished but post-processing (sample / foamToVTK) failed. "
        "Solver output is still on disk — check the run dir manually."
    ),
    "unknown_error": (
        "Failure didn't match any known pattern. Open the run detail page "
        "for the full error message and stderr."
    ),
}


def _classify_failure(text: str | None, _exit_code: int | None = None) -> str:
    """Return one of `_FAILURE_CATEGORIES` for the given haystack text.

    Priority: Docker / container errors first (because they cascade into
    bogus 'command not found' lower in the stack), then specific markers
    via _FAILURE_OVERRIDES, then a generic FOAM FATAL → solver_diverged
    fallback, then unknown_error if nothing matches.
    """
    if not text:
        return "unknown_error"
    haystack = text.lower()

    # First pass: high-priority hints (Docker / container).
    for pattern, category in _FAILURE_HINTS:
        if pattern in haystack:
            initial = category
            break
    else:
        initial = "unknown_error"

    # Second pass: refine — overrides only fire if their pattern appears.
    # Walk in order so later (more specific) overrides win over earlier.
    refined = initial
    for pattern, category in _FAILURE_OVERRIDES:
        if pattern in haystack:
            refined = category

    return refined


def failure_remediation(category: str) -> str:
    """Public lookup. Returns the user-facing remediation hint for a
    classified failure category."""
    return _REMEDIATION_HINTS.get(category, _REMEDIATION_HINTS["unknown_error"])


def _task_spec_from_case_id(case_id: str):
    """Build a TaskSpec for the given case_id.

    Source priority:
      1. ``ui/backend/user_drafts/{case_id}.yaml`` (single-case YAML doc as
         saved by ``case_editor.py``'s ``PUT /api/cases/{id}/yaml``) — lets
         /workbench/case/{id}/edit param overrides flow to the real solver.
      2. ``knowledge/whitelist.yaml`` entry — vanilla case definition.

    Raises KeyError if neither source resolves the case_id.

    NOTE: imports from `src.*` are deferred to call-time so module import
    of `wizard_drivers` doesn't pull in the 8000+ LOC foam_agent_adapter
    just to expose MockSolverDriver to tests.
    """
    import yaml
    from pathlib import Path

    from src.models import (
        Compressibility,
        FlowType,
        GeometryType,
        SteadyState,
        TaskSpec,
    )

    repo_root = Path(__file__).resolve().parents[3]

    # 1. Try user_drafts first (M2 override surface).
    draft_path = repo_root / "ui" / "backend" / "user_drafts" / f"{case_id}.yaml"
    entry: dict | None = None
    source_origin = "whitelist"
    if draft_path.exists():
        with draft_path.open("r", encoding="utf-8") as fh:
            entry = yaml.safe_load(fh) or {}
        if not isinstance(entry, dict) or "geometry_type" not in entry:
            # Malformed draft — refuse to silently fall through to whitelist;
            # surface a clean error so the user can fix the YAML in the editor.
            raise KeyError(
                f"user draft {draft_path} for {case_id!r} is malformed "
                "(must be a single-case dict with geometry_type field)"
            )
        source_origin = "draft"

    # 2. Fall back to whitelist.
    if entry is None:
        whitelist_path = repo_root / "knowledge" / "whitelist.yaml"
        with whitelist_path.open("r", encoding="utf-8") as fh:
            doc = yaml.safe_load(fh) or {}
        entry = next(
            (c for c in doc.get("cases", []) if c.get("id") == case_id),
            None,
        )
        if entry is None:
            raise KeyError(
                f"case_id {case_id!r} not in user_drafts nor knowledge/whitelist.yaml"
            )

    params = entry.get("parameters") or {}
    bcs = entry.get("boundary_conditions") or {}
    return TaskSpec(
        name=entry.get("name", case_id),
        geometry_type=GeometryType[entry["geometry_type"]],
        flow_type=FlowType[entry["flow_type"]],
        steady_state=SteadyState[entry.get("steady_state", "STEADY")],
        compressibility=Compressibility[entry.get("compressibility", "INCOMPRESSIBLE")],
        Re=params.get("Re"),
        Ra=params.get("Ra"),
        Re_tau=params.get("Re_tau"),
        Ma=params.get("Ma"),
        boundary_conditions=dict(bcs),
        description=(
            f"RealSolverDriver run · source={source_origin} · "
            f"ref={entry.get('reference', 'no ref')}"
        ),
    )


# Backward-compat alias retained for any pre-M2 callers that imported the
# whitelist-only name. Drops in a future cleanup pass.
_task_spec_from_whitelist = _task_spec_from_case_id


class RealSolverDriver:
    """Real OpenFOAM execution driver. Wraps FoamAgentExecutor.execute().

    Opt in via ``CFD_HARNESS_WIZARD_SOLVER=real``. Default remains ``mock``
    so the Stage 8a onboarding demo path stays mock-driven.

    Failure modes mapped to SSE:
      - case_id not in whitelist → run_done with exit_code=2, level=error
      - Executor raises (Docker missing, container crash, etc.) →
        phase_done status=fail + run_done with exit_code=1, level=error
      - ExecutionResult.success=False → phase_done status=fail, exit_code
        mirrors result.exit_code if set else 1
      - Success → phase_done status=ok + run_done with exit_code=0
    """

    name = "real"

    async def run(self, case_id: str) -> AsyncIterator[str]:
        # Defer src.* imports to call-time per the comment on
        # _task_spec_from_case_id above.
        from datetime import datetime, timezone

        from src.foam_agent_adapter import FoamAgentExecutor

        from ui.backend.services.run_history import (
            new_run_id,
            write_run_artifacts,
        )

        # M3: pre-allocate a run_id at the very top so we can include it in
        # every SSE event from this run. Frontend uses run_id on `run_done`
        # to auto-redirect to /workbench/case/{id}/run/{run_id}.
        run_id = new_run_id()
        started_at = datetime.now(timezone.utc)

        yield _sse({
            "type": "log", "phase": None, "t": time.time(),
            "run_id": run_id,
            "line": (
                f"[wizard] case_id={case_id} run_id={run_id} starting REAL solver pipeline "
                "(RealSolverDriver — user_drafts override → whitelist fallback)"
            ),
        })

        # --- 1. Resolve case_id → TaskSpec ----------------------------------
        source_origin = "unknown"
        try:
            task_spec = _task_spec_from_case_id(case_id)
            # Inspect description we set in _task_spec_from_case_id to derive
            # the source origin for run_history's summary.json. This is the
            # cheapest path; alternative would be returning a tuple.
            desc = task_spec.description or ""
            source_origin = "draft" if "source=draft" in desc else "whitelist"
        except KeyError as exc:
            yield _sse({
                "type": "log", "phase": None, "t": time.time(),
                "run_id": run_id,
                "line": f"[wizard] ERROR: {exc}",
                "level": "error", "stream": "stderr",
            })
            yield _sse({
                "type": "run_done", "phase": None, "t": time.time(),
                "run_id": run_id,
                "summary": f"unknown case_id={case_id} — not in whitelist",
                "exit_code": 2, "level": "error",
            })
            return

        yield _sse({
            "type": "log", "phase": None, "t": time.time(),
            "run_id": run_id,
            "line": (
                f"[wizard] resolved {case_id} → {task_spec.name} "
                f"({task_spec.flow_type.value}/{task_spec.geometry_type.value})"
            ),
        })

        # --- 2. Dispatch executor to thread pool, heartbeat in foreground ---
        yield _sse({
            "type": "phase_start", "phase": "solver", "t": time.time(),
            "run_id": run_id,
            "message": "Docker + OpenFOAM 求解器执行中（同步阻塞 ~10-300s）...",
        })

        executor = FoamAgentExecutor()
        exec_task = asyncio.create_task(
            asyncio.to_thread(executor.execute, task_spec)
        )

        # Heartbeat loop: wait up to HEARTBEAT_INTERVAL_S each iteration; if the
        # executor finishes within that window, break with the result; otherwise
        # emit a heartbeat log and try again. `asyncio.wait_for` uses
        # `loop.call_later` for the timeout (real wall-clock), independent of any
        # asyncio.sleep mocking that test fixtures may apply.
        t0 = time.time()
        result = None
        exec_exc: Exception | None = None
        while True:
            try:
                result = await asyncio.wait_for(
                    asyncio.shield(exec_task), timeout=_HEARTBEAT_INTERVAL_S
                )
                break
            except asyncio.TimeoutError:
                elapsed = time.time() - t0
                yield _sse({
                    "type": "log", "phase": "solver", "t": time.time(),
                    "run_id": run_id,
                    "line": f"[solver] running... ({elapsed:.0f}s elapsed)",
                })
                continue
            except Exception as exc:  # noqa: BLE001 — surface ANY executor failure
                exec_exc = exc
                break

        # --- 3. Drain ExecutionResult or exception --------------------------
        if exec_exc is not None:
            exc = exec_exc
            err_str = str(exc)
            duration_s = time.time() - t0
            # M4: classify the exception text for a readable verdict banner.
            failure_category = _classify_failure(
                f"{type(exc).__name__}: {err_str}", _exit_code=1
            )
            verdict_summary = (
                f"executor exception: {type(exc).__name__} ({failure_category})"
            )

            yield _sse({
                "type": "log", "phase": "solver", "t": time.time(),
                "run_id": run_id,
                "line": f"[solver] FATAL: {type(exc).__name__}: {err_str[:200]}",
                "level": "error", "stream": "stderr",
            })
            yield _sse({
                "type": "phase_done", "phase": "solver", "t": time.time(),
                "run_id": run_id,
                "status": "fail",
                "summary": verdict_summary,
                "failure_category": failure_category,
            })
            # Persist run history artifacts even on failure — the user's
            # /workbench/case/{id}/runs table needs to show the failed run.
            try:
                write_run_artifacts(
                    case_id=case_id,
                    run_id=run_id,
                    started_at=started_at,
                    task_spec=task_spec,
                    source_origin=source_origin,
                    success=False,
                    exit_code=1,
                    verdict_summary=verdict_summary,
                    duration_s=duration_s,
                    key_quantities=None,
                    residuals=None,
                    error_message=f"{type(exc).__name__}: {err_str[:500]}",
                    failure_category=failure_category,
                )
            except Exception as write_exc:  # noqa: BLE001
                # A failed write should never propagate up — the SSE
                # client already saw run_done is en route. Surface as a log
                # event so the operator sees it in the timeline.
                yield _sse({
                    "type": "log", "phase": None, "t": time.time(),
                    "run_id": run_id,
                    "line": f"[wizard] WARN: run-history writeback failed: {write_exc}",
                    "level": "warning", "stream": "stderr",
                })
            yield _sse({
                "type": "run_done", "phase": None, "t": time.time(),
                "run_id": run_id,
                "summary": (
                    f"run failed · case_id={case_id} · "
                    f"{type(exc).__name__}: {err_str[:120]}"
                ),
                "exit_code": 1, "level": "error",
                "failure_category": failure_category,
            })
            return

        # Residuals → metric events (numeric only)
        for k, v in (result.residuals or {}).items():
            try:
                yield _sse({
                    "type": "metric", "phase": "solver", "t": time.time(),
                    "run_id": run_id,
                    "metric_key": f"residual_{k}", "metric_value": float(v),
                })
            except (TypeError, ValueError):
                continue

        # Key quantities → metric events (numeric) or log lines (non-numeric)
        for k, v in (result.key_quantities or {}).items():
            try:
                fv = float(v)
                yield _sse({
                    "type": "metric", "phase": "solver", "t": time.time(),
                    "run_id": run_id,
                    "metric_key": str(k), "metric_value": fv,
                })
            except (TypeError, ValueError):
                yield _sse({
                    "type": "log", "phase": "solver", "t": time.time(),
                    "run_id": run_id,
                    "line": f"[result] {k} = {v!r}"[:200],
                })

        # --- 4. phase_done + run_done + run-history writeback ---------------
        elapsed_total = result.execution_time_s or (time.time() - t0)
        # M4: classify failure for failed runs only. None on success.
        failure_category: str | None = None
        if not result.success:
            failure_category = _classify_failure(
                result.error_message, _exit_code=result.exit_code
            )

        if result.success:
            verdict_summary = (
                f"OpenFOAM converged · {elapsed_total:.1f}s · "
                f"{len(result.key_quantities or {})} key quantities extracted"
            )
            yield _sse({
                "type": "phase_done", "phase": "solver", "t": time.time(),
                "run_id": run_id,
                "status": "ok",
                "summary": verdict_summary,
            })
            exit_code = result.exit_code if result.exit_code is not None else 0
            level = "info"
        else:
            err_msg = (result.error_message or "(no error message)")[:160]
            verdict_summary = f"OpenFOAM failed · {err_msg} ({failure_category})"
            yield _sse({
                "type": "phase_done", "phase": "solver", "t": time.time(),
                "run_id": run_id,
                "status": "fail",
                "summary": verdict_summary,
                "failure_category": failure_category,
            })
            exit_code = result.exit_code if result.exit_code is not None else 1
            level = "error"

        # Persist artifacts.
        try:
            write_run_artifacts(
                case_id=case_id,
                run_id=run_id,
                started_at=started_at,
                task_spec=task_spec,
                source_origin=source_origin,
                success=bool(result.success),
                exit_code=exit_code,
                verdict_summary=verdict_summary,
                duration_s=elapsed_total,
                key_quantities=dict(result.key_quantities or {}),
                residuals=dict(result.residuals or {}),
                error_message=result.error_message,
                failure_category=failure_category,
            )
        except Exception as write_exc:  # noqa: BLE001
            yield _sse({
                "type": "log", "phase": None, "t": time.time(),
                "run_id": run_id,
                "line": f"[wizard] WARN: run-history writeback failed: {write_exc}",
                "level": "warning", "stream": "stderr",
            })

        run_done_event: dict[str, object] = {
            "type": "run_done", "phase": None, "t": time.time(),
            "run_id": run_id,
            "summary": (
                f"run complete · case_id={case_id} · run_id={run_id} · "
                f"success={result.success} · {elapsed_total:.1f}s · "
                "real solver execution"
            ),
            "exit_code": exit_code,
            "level": level,
        }
        if failure_category is not None:
            run_done_event["failure_category"] = failure_category
        yield _sse(run_done_event)


_DRIVER_REGISTRY: dict[str, SolverDriver] = {
    "mock": MockSolverDriver(),
    "real": RealSolverDriver(),
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
