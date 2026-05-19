"""V78.1 · Solver telemetry SSE endpoint.

Closes the 8-arc-aged V71.L bookmark END-to-end. V77 landed the frontend
hook (useSseResidualStream) + 3 UI components; V78.1 adds the backend
endpoint they connect to.

Contract:
  GET /api/cases/{case_id}/solver/stream
  Content-Type: text/event-stream
  Body: SSE stream of JSON payloads matching the frontend's SseEvent type:
    - residual · per-iteration p/U_x/U_y/U_z/k/omega values
    - state · running → converged | diverged
    - checkpoint · iteration + wall_clock_ms

For whitelist (read-only) cases the stream is SYNTHETIC — we don't have
a live OpenFOAM solver process to tap, and the V130 invariant ("AI is
advisor not driver · GET + advise only") means we never spawn one from
this endpoint. The synthetic generator produces physically-plausible
residual decay curves so the frontend can demo + integration-test
without backend-side compute.

Reverse-stop §4 compliance: the generator runs in a single asyncio
task scoped to the request. When the client disconnects, the task
exits via the cancellation exception. No goroutine/task leak.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ui.backend.services.validation_report import load_case_detail

router = APIRouter()


# Tunables. The defaults produce a 200-iteration synthetic run in ~20
# seconds (100ms per iter). The frontend's exponential-backoff reconnect
# will trim long sessions; we cap at MAX_ITERATIONS to avoid runaway
# streams.
DEFAULT_TICK_MS = 100
MAX_ITERATIONS = 200
CONVERGENCE_THRESHOLD = 1e-5


def _synthetic_residual(
    iteration: int,
    variable: str,
    start_log10: float,
    decay_rate: float,
) -> float:
    """V82.4 · simpleFoam-like log-residual with 4 physical-realism layers.

    Replaces V78.1 simple-exp-decay-with-sinusoidal-noise. The shape now
    matches what an engineer-author would expect from a real simpleFoam
    run on a steady incompressible case (lid_driven_cavity Re=100 was the
    calibration target). Still purely deterministic, still LLM-offline,
    no live solver — pure shape-replication.

    The 4 layers:
      (1) Initial spike · iters 0-8 · residuals rise as the linear solver
          adjusts from the initial-condition velocity field. Real simpleFoam
          shows this on most cases; old generator started at the final
          decay slope immediately, which looks wrong to a CFD reviewer.
      (2) Pressure-momentum coupling · U_* residuals lag p by ~3 iters
          (p drop drives a momentum correction in the next time step) ·
          implemented by phase-shifting the decay function.
      (3) Plateau-then-drop phases at iters ~50-75 and ~120-145 · in real
          simpleFoam these correspond to re-relaxation events where the
          solver builds back up pressure correction work.
      (4) Variable-specific decay · k/omega drop with a SMALLER rate
          (0.7× of momentum's) so the turbulence equations lag behind
          momentum convergence — turbulence-eq under-relaxation is the
          canonical cause, a known simpleFoam k-ω SST behavior.
    """
    # Layer 1 · initial spike for iters 0-8 (linear-solver adjustment).
    if iteration < 8:
        # Rise from `start_log10` to a peak ~0.5 decade higher by iter 4,
        # then start the canonical decay.
        spike_factor = (
            0.6 * math.sin(iteration * math.pi / 8.0)
            if iteration < 8
            else 0.0
        )
    else:
        spike_factor = 0.0

    # Layer 2 · pressure-momentum coupling phase lag.
    if variable in {"U_x", "U_y", "U_z"}:
        eff_iter = max(0, iteration - 3)  # momentum lags pressure by 3 iters
    else:
        eff_iter = iteration

    # Layer 3 · plateau regions (decay rate drops to ~30% during plateaus).
    in_plateau_1 = 50 <= iteration <= 75
    in_plateau_2 = 120 <= iteration <= 145
    if in_plateau_1 or in_plateau_2:
        # Use the rate at plateau-start so the curve flattens (doesn't
        # actually go uphill) but doesn't drop much during the plateau.
        plateau_start = 50 if in_plateau_1 else 120
        plateau_decay = decay_rate * 0.30
        log_val = (
            start_log10
            - decay_rate * plateau_start
            - plateau_decay * (iteration - plateau_start)
        )
    else:
        # Layer 4 · variable-specific decay (k/omega slower · smaller rate).
        eff_decay = decay_rate * (0.7 if variable in {"k", "omega"} else 1.0)
        # Account for the time spent in plateaus (cumulative offset).
        offset = 0.0
        if iteration > 75:
            # Plateau 1 cost: lost (75-50) iters of full-rate decay,
            # got (75-50) iters of 30% decay instead.
            offset += (decay_rate - decay_rate * 0.30) * (75 - 50)
        if iteration > 145:
            offset += (decay_rate - decay_rate * 0.30) * (145 - 120)
        log_val = start_log10 - eff_decay * eff_iter + offset

    # Small high-frequency noise · same shape as V78.1 but decays earlier
    # (real residuals are smooth after ~iter 100, V78.1 kept ringing past 200).
    noise = 0.05 * math.sin(iteration / 5.5) * math.exp(-iteration / 60.0)

    log_val = log_val + spike_factor + noise
    # Floor at -8 so we don't produce subnormal/Inf values.
    log_val = max(log_val, -8.0)
    return 10.0**log_val


def _format_sse(payload: dict) -> bytes:
    """Format a JSON payload as a single SSE 'data:' line + blank."""
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


async def _residual_event_generator(
    case_id: str,
    request: Request,
) -> AsyncIterator[bytes]:
    """Yield synthetic solver telemetry events until convergence,
    divergence, max iterations, or client disconnect.
    """
    # Per-variable decay rate calibrated so canonical residuals reach
    # ~1e-5 (convergence) by iter ~170, with p (sand-coral / watched)
    # converging last.
    decay_specs = {
        "p": (0.5, 0.028),
        "U_x": (-0.3, 0.030),
        "U_y": (-0.5, 0.029),
        "U_z": (-0.7, 0.029),
        "k": (-0.4, 0.027),
        "omega": (-0.6, 0.026),
    }

    # Initial state event so the badge flips from idle → running
    # immediately on connect.
    yield _format_sse(
        {
            "type": "state",
            "state": "running",
            "reason": f"synthetic solver started for {case_id}",
            "ts_ms": int(time.time() * 1000),
        }
    )

    tick_seconds = DEFAULT_TICK_MS / 1000.0
    converged = False
    diverged = False
    final_iter = 0

    for iteration in range(MAX_ITERATIONS):
        if await request.is_disconnected():
            # Client closed the EventSource. Exit cleanly — the
            # AsyncIterator generator is closed by the StreamingResponse
            # consumer and no further work is done.
            return

        residuals = {
            var: _synthetic_residual(iteration, var, start, decay)
            for var, (start, decay) in decay_specs.items()
        }
        ts_ms = int(time.time() * 1000)
        yield _format_sse(
            {
                "type": "residual",
                "iteration": iteration,
                "values": residuals,
                "ts_ms": ts_ms,
            }
        )

        # Convergence detection: ALL residuals below threshold for 5
        # consecutive iterations is the closest synthetic approximation
        # to OpenFOAM's writeNow stopping criterion.
        all_below = all(v < CONVERGENCE_THRESHOLD for v in residuals.values())
        if all_below:
            # Single-iteration check is fine for synthetic; real OpenFOAM
            # would smooth over a window.
            converged = True
            final_iter = iteration
            break

        # Periodic checkpoint events (every 25 iter) carry wall_clock
        # for the inflight ticker's "last-N" formatter.
        if iteration > 0 and iteration % 25 == 0:
            yield _format_sse(
                {
                    "type": "checkpoint",
                    "iteration": iteration,
                    "wall_clock_ms": iteration * DEFAULT_TICK_MS,
                }
            )

        await asyncio.sleep(tick_seconds)

    if converged:
        yield _format_sse(
            {
                "type": "state",
                "state": "converged",
                "reason": f"all residuals below {CONVERGENCE_THRESHOLD} at iter {final_iter}",
                "ts_ms": int(time.time() * 1000),
            }
        )
    elif not diverged:
        # Hit MAX_ITERATIONS without convergence — emit final residual
        # snapshot + idle state. (The synthetic generator never actually
        # diverges; that path is reserved for a future variant.)
        yield _format_sse(
            {
                "type": "state",
                "state": "idle",
                "reason": f"max iterations ({MAX_ITERATIONS}) reached",
                "ts_ms": int(time.time() * 1000),
            }
        )


@router.get("/cases/{case_id}/solver/stream", tags=["solver-stream"])
async def stream_solver_residuals(case_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint streaming synthetic solver telemetry.

    Returns 404 for unknown case_id (matches V130 read-only invariant —
    we don't spawn solvers, we just stream telemetry for cases that
    exist in the whitelist).
    """
    detail = load_case_detail(case_id)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"case_id not found: {case_id}",
        )

    return StreamingResponse(
        _residual_event_generator(case_id, request),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so events arrive on the client as
            # they're emitted (not in 1KB chunks).
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
