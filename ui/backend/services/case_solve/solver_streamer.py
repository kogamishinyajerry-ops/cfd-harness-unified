"""Streaming variant of :mod:`solver_runner` for live UI feedback.

The blocking ``run_icofoam`` waits ~60s before returning a single
SolveSummary. The user reported (2026-04-29) that watching a spinner
for 60s with no feedback is unacceptable — Step 4 should "实时监控
求解器的残差图". This module runs icoFoam with
``container.exec_run(stream=True)`` so log lines arrive incrementally;
each parseable line becomes an SSE event the UI can consume.

Protocol (one event per parseable line, plus a final summary):

* ``time``       — start of a new PISO timestep. ``{"t": 0.005}``
* ``residual``   — one solver-iteration residual line.
                   ``{"field": "p"|"Ux"|"Uy"|"Uz", "init": 0.5,
                       "final": 0.001, "iters": 21, "t": 0.005}``
* ``continuity`` — PISO continuity-error closing line.
                   ``{"sum_local": 1e-6, "global": 1e-19, "t": 0.005}``
* ``done``       — end of run. ``{"converged": true, ...SolveSummary}``
* ``error``      — fatal error mid-run. ``{"detail": "..."}``

This stream-based design also dovetails with the SSE frontend: the
React component subscribes via ``EventSource`` and renders a live
chart instead of waiting for a static PNG render at the end.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import tarfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ui.backend.services.meshing_gmsh.to_foam import (
    CONTAINER_NAME,
    CONTAINER_WORK_BASE,
    _extract_tarball,
    _make_tarball,
)


# Reuse parsers from solver_runner so the SSE summary at the end
# matches what the blocking endpoint would have returned.
from .solver_runner import (
    SolverRunError,
    SolverRunResult,
    _is_converged,
    _parse_log,
)


# Line-level patterns (single-line variants of solver_runner regexes).
_TIME_LINE = re.compile(r"^Time\s*=\s*([0-9.eE+-]+)s?\s*$")
_RES_U_LINE = re.compile(
    r"smoothSolver:\s+Solving for U([xyz]),\s+Initial residual\s*=\s*"
    r"([0-9.eE+-]+),\s+Final residual\s*=\s*([0-9.eE+-]+),\s+"
    r"No Iterations\s+(\d+)"
)
_RES_P_LINE = re.compile(
    r"DICPCG:\s+Solving for p,\s+Initial residual\s*=\s*"
    r"([0-9.eE+-]+),\s+Final residual\s*=\s*([0-9.eE+-]+),\s+"
    r"No Iterations\s+(\d+)"
)
_CONT_LINE = re.compile(
    r"time step continuity errors\s*:\s*sum local\s*=\s*"
    r"([0-9.eE+-]+),\s+global\s*=\s*([0-9.eE+-]+)"
)
_FOAM_FATAL = re.compile(r"^--> FOAM FATAL ERROR")


def _sse(event: str, data: dict[str, Any]) -> bytes:
    """Format an SSE message. Each event has its own ``event:`` line so
    EventSource clients can subscribe to specific event types.
    """
    payload = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


def _parse_line_to_events(
    line: str,
    *,
    current_time: list[float | None],
    last_p: list[float | None],
    fatal_seen: list[bool],
) -> Iterator[bytes]:
    """Mutate the parser-state lists and yield SSE bytes for any
    events the line generates. Mutating-arg pattern lets us keep
    state across calls without a class.
    """
    line = line.rstrip()

    if _FOAM_FATAL.match(line):
        fatal_seen[0] = True
        yield _sse("error", {"detail": line})
        return

    m_t = _TIME_LINE.match(line)
    if m_t:
        t = float(m_t.group(1))
        current_time[0] = t
        yield _sse("time", {"t": t})
        return

    if current_time[0] is None:
        # Pre-time-loop chatter (initialization) — ignore.
        return

    m_u = _RES_U_LINE.search(line)
    if m_u:
        comp = m_u.group(1)
        yield _sse(
            "residual",
            {
                "field": f"U{comp}",
                "init": float(m_u.group(2)),
                "final": float(m_u.group(3)),
                "iters": int(m_u.group(4)),
                "t": current_time[0],
            },
        )
        return

    m_p = _RES_P_LINE.search(line)
    if m_p:
        last_p[0] = float(m_p.group(1))
        yield _sse(
            "residual",
            {
                "field": "p",
                "init": last_p[0],
                "final": float(m_p.group(2)),
                "iters": int(m_p.group(3)),
                "t": current_time[0],
            },
        )
        return

    m_c = _CONT_LINE.search(line)
    if m_c:
        yield _sse(
            "continuity",
            {
                "sum_local": float(m_c.group(1)),
                "global": float(m_c.group(2)),
                "t": current_time[0],
            },
        )


def stream_icofoam(
    *,
    case_host_dir: Path,
    container_name: str = CONTAINER_NAME,
) -> Iterator[bytes]:
    """Run icoFoam with streamed output. Yields SSE-formatted bytes
    that an EventSource client can consume directly.

    This is the streaming counterpart to :func:`run_icofoam`; the
    final ``done`` event mirrors the SolverRunResult that the
    blocking variant would have returned.

    Failures are surfaced as either an SSE ``error`` event (mid-run)
    or — for setup failures before icoFoam starts — by raising
    :class:`SolverRunError` BEFORE the first yield. The route layer
    catches the latter and converts to an HTTP 4xx/5xx; the former
    becomes part of the in-stream payload.
    """
    if not case_host_dir.is_dir():
        raise SolverRunError(f"case dir not found: {case_host_dir}")
    if not (case_host_dir / "system" / "controlDict").is_file():
        raise SolverRunError(
            f"no system/controlDict at {case_host_dir} — run "
            "setup-bc first."
        )

    try:
        import docker  # type: ignore[import-not-found]
        import docker.errors  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SolverRunError(
            "docker SDK is not installed."
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            raise SolverRunError(
                f"container '{container_name}' is not running."
            )
    except docker.errors.NotFound as exc:
        raise SolverRunError(
            f"container '{container_name}' not found."
        ) from exc
    except docker.errors.DockerException as exc:
        raise SolverRunError(f"docker init failed: {exc}") from exc

    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"

    # Stage the case (same as the blocking variant).
    try:
        container.exec_run(
            cmd=[
                "bash",
                "-c",
                f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}",
            ]
        )
        ok = container.put_archive(
            path=CONTAINER_WORK_BASE,
            data=_make_tarball(case_host_dir),
        )
        if not ok:
            raise SolverRunError(
                "failed to stage case for streaming icoFoam"
            )
    except docker.errors.DockerException as exc:
        raise SolverRunError(
            f"docker SDK error preparing container workspace: {exc}"
        ) from exc

    # Run icoFoam WITHOUT redirecting to a log file so exec_run can
    # stream the output. ``stdbuf -oL`` line-buffers stdout so PISO
    # iterations arrive promptly instead of in 4KB chunks.
    bash_cmd = (
        "source /opt/openfoam10/etc/bashrc && "
        f"cd {container_work_dir} && "
        "stdbuf -oL -eL icoFoam 2>&1"
    )

    # ``exec_run(stream=True, demux=False)`` returns an ExecResult whose
    # .output is an iterator of bytes (each yield is whatever was in
    # the buffer at flush time, NOT necessarily one line).
    try:
        exec_result = container.exec_run(
            cmd=["bash", "-c", bash_cmd],
            stream=True,
            demux=False,
        )
    except docker.errors.DockerException as exc:
        raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc

    # Buffer + line-by-line parse + accumulate full log on host.
    log_dest = case_host_dir / "log.icoFoam"
    log_buf = io.BytesIO()
    line_buf = b""
    current_time: list[float | None] = [None]
    last_p: list[float | None] = [None]
    fatal_seen: list[bool] = [False]

    try:
        for chunk in exec_result.output:
            if not chunk:
                continue
            log_buf.write(chunk)
            # Append chunk to the line buffer, split on \n, parse each
            # complete line. The trailing partial line stays in the
            # buffer for the next chunk.
            line_buf += chunk
            while b"\n" in line_buf:
                raw_line, _, line_buf = line_buf.partition(b"\n")
                try:
                    line_str = raw_line.decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    continue
                yield from _parse_line_to_events(
                    line_str,
                    current_time=current_time,
                    last_p=last_p,
                    fatal_seen=fatal_seen,
                )
    except Exception as exc:  # noqa: BLE001 — stream interruption
        yield _sse("error", {"detail": f"stream interrupted: {exc}"})
        # Don't re-raise — let the done event below close the stream
        # cleanly; the client will see error then done(converged=false).

    # Flush the trailing partial line.
    if line_buf:
        try:
            line_str = line_buf.decode("utf-8", errors="replace")
            yield from _parse_line_to_events(
                line_str,
                current_time=current_time,
                last_p=last_p,
                fatal_seen=fatal_seen,
            )
        except Exception:  # noqa: BLE001
            pass

    # Persist the full log on the host so downstream tools (the
    # /residual-history.png renderer, the audit package, etc) can
    # read it.
    try:
        log_dest.write_bytes(log_buf.getvalue())
    except OSError as exc:
        yield _sse(
            "error",
            {"detail": f"failed to persist log on host: {exc}"},
        )

    # Pull time directories back for the results extractor.
    pulled: list[str] = []
    try:
        ls_out = container.exec_run(
            cmd=[
                "bash",
                "-c",
                f"cd {container_work_dir} && ls -d [0-9]* 2>/dev/null",
            ]
        )
        time_dirs_raw = ls_out.output.decode(errors="replace").strip().split()
        for td in time_dirs_raw:
            try:
                bits, _ = container.get_archive(f"{container_work_dir}/{td}")
                _extract_tarball(b"".join(bits), case_host_dir)
                pulled.append(td)
            except docker.errors.DockerException:
                continue
    except docker.errors.DockerException as exc:
        yield _sse(
            "error",
            {"detail": f"docker SDK error pulling time dirs: {exc}"},
        )
    except (OSError, tarfile.TarError) as exc:
        yield _sse(
            "error",
            {"detail": f"host fault pulling time dirs: {exc}"},
        )

    # Final summary event — mirrors SolverRunResult shape.
    parsed = _parse_log(log_buf.getvalue().decode("utf-8", errors="replace"))
    converged = _is_converged(parsed) and not fatal_seen[0]
    summary = {
        "case_id": case_host_dir.name,
        "end_time_reached": float(parsed["end_time_reached"]),
        "last_initial_residual_p": parsed["p"],
        "last_initial_residual_U": [
            parsed["Ux"],
            parsed["Uy"],
            parsed["Uz"],
        ],
        "last_continuity_error": parsed["continuity"],
        "n_time_steps_written": len(pulled),
        "time_directories": sorted(pulled, key=lambda s: float(s)),
        "wall_time_s": float(parsed["wall_clock"]),
        "converged": converged,
    }
    yield _sse("done", summary)
