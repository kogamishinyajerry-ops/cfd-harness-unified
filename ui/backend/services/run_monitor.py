"""Run Monitor backing service (Phase 3).

Phase 3 scope: emit a **synthetic** residual stream that plausibly
tracks real solver behaviour (exponential decay with stochastic
jitter + occasional plateau). No real OpenFOAM invocation — that's
Phase 3.5 / Phase 5 scope.

The SSE endpoint publishes one event ~80-160 ms apart, each line a
JSON blob:

    {
      "iter": 42,
      "t_sec": 0.84,
      "residuals": {"Ux": 1.2e-5, "Uy": 3.4e-5, "p": 8.9e-4},
      "phase": "linear_solver" | "postprocess" | "done"
    }

Checkpoints are a derived concept: every N iters emit one
`phase: "checkpoint"` event for the UI timeline.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(slots=True)
class RunProfile:
    case_id: str
    target_iters: int = 180
    checkpoint_every: int = 40
    # Decay rates per residual channel (log10 drop per 100 iters).
    decay_log10: tuple[tuple[str, float], ...] = (
        ("Ux", 2.2),
        ("Uy", 2.0),
        ("p", 1.6),
    )
    initial_log10: float = -0.3
    tick_ms_range: tuple[int, int] = (70, 160)

    # Per-case personality (seeds vary between cases so charts look distinct).
    def seed(self) -> int:
        return abs(hash(self.case_id)) % (2**31 - 1)


def _sample_residual(initial: float, decay: float, iter_i: int, rng: random.Random) -> float:
    log10 = initial - decay * (iter_i / 100.0)
    noise = rng.gauss(0.0, 0.18)
    # Occasional plateau: clamp every ~25 iters to introduce a visual step.
    if iter_i > 0 and iter_i % 27 == 0:
        noise += 0.08
    return float(10.0 ** (log10 + noise))


async def stream_run(case_id: str) -> AsyncIterator[str]:
    """Async generator yielding pre-formatted SSE lines."""
    profile = RunProfile(case_id=case_id)
    rng = random.Random(profile.seed())
    t_start = 0.0
    yield _sse_line({
        "iter": 0,
        "t_sec": 0.0,
        "residuals": None,
        "phase": "init",
        "message": f"Initialising mock solver for {case_id}",
    })
    for iter_i in range(1, profile.target_iters + 1):
        tick_ms = rng.randint(*profile.tick_ms_range)
        await asyncio.sleep(tick_ms / 1000.0)
        t_start += tick_ms / 1000.0
        residuals = {
            name: _sample_residual(profile.initial_log10, decay, iter_i, rng)
            for name, decay in profile.decay_log10
        }
        phase = "linear_solver"
        if iter_i % profile.checkpoint_every == 0:
            phase = "checkpoint"
        yield _sse_line({
            "iter": iter_i,
            "t_sec": round(t_start, 3),
            "residuals": residuals,
            "phase": phase,
            "message": f"case={case_id} iter={iter_i}",
        })
    yield _sse_line({
        "iter": profile.target_iters,
        "t_sec": round(t_start, 3),
        "residuals": None,
        "phase": "done",
        "message": "mock run complete (Phase 3 synthetic; real solver wiring lands in Phase 3.5)",
    })


def _sse_line(event: dict[str, object]) -> str:
    """Format one SSE message with exactly two trailing newlines."""
    return f"data: {json.dumps(event)}\n\n"


def snapshot_last_n_checkpoints(n: int = 8) -> list[dict]:
    """Return a synthetic checkpoint roster for rendering in the UI
    table when no live stream is active. Phase 3.5 will populate this
    from reports/**/checkpoints.yaml."""
    now = 0.0
    out: list[dict] = []
    for i in range(n):
        now += 11.3
        out.append(
            {
                "iter": (i + 1) * 25,
                "t_sec": round(now, 2),
                "residual_Ux": 10 ** (-0.3 - 0.22 * (i + 1)),
                "residual_Uy": 10 ** (-0.5 - 0.2 * (i + 1)),
                "residual_p":  10 ** (-0.1 - 0.16 * (i + 1)),
                "phase": "checkpoint",
            }
        )
    return out
