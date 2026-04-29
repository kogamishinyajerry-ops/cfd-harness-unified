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
import secrets
import shutil
import tarfile
import threading
from collections.abc import Iterator
from dataclasses import dataclass
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


class SolveAlreadyRunning(SolverRunError):
    """Raised when a prior solve for the same case_id is still active.

    Codex round-1 HIGH-2: prior to the run_id system, a navigate-away
    or remount could leave run A's icoFoam alive while run B started
    in the same container_work_dir; both runs would race on
    log.icoFoam and the time directories. Now the route returns 409
    when this happens and the user retries after the prior run exits.
    """


# Codex round-1 HIGH-2: per-case lock so concurrent solves cannot
# share container_work_dir + log path. Sync threading lock is
# appropriate because FastAPI runs the sync generator in a worker
# thread (StreamingResponse iterates the generator from the worker).
_runs_lock = threading.Lock()
_active_runs: dict[str, str] = {}  # case_id → run_id


def _claim_run(case_id: str) -> str:
    """Allocate a run_id for ``case_id``; raise if one is already in flight."""
    with _runs_lock:
        if case_id in _active_runs:
            raise SolveAlreadyRunning(
                f"solve already running for case {case_id!r} "
                f"(run_id={_active_runs[case_id]})"
            )
        run_id = secrets.token_hex(6)  # 12-char hex, plenty for collision-free
        _active_runs[case_id] = run_id
    return run_id


def _release_run(case_id: str, run_id: str) -> None:
    """Drop the in-flight registration. Idempotent if run_id mismatches."""
    with _runs_lock:
        if _active_runs.get(case_id) == run_id:
            del _active_runs[case_id]


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


@dataclass(frozen=True, slots=True)
class _PreparedStream:
    """Output of :func:`_prepare_stream_icofoam`. Contains everything
    the generator needs to start producing SSE bytes — Docker has
    already been validated and icoFoam has already been spawned.

    Codex round-1 HIGH-1: previously the preflight (validate Docker,
    stage tarball, spawn icoFoam) lived inside the generator body, so
    the route's try/except was dead code — generator instantiation
    doesn't run the body, only first iteration does, by which point
    StreamingResponse has already returned 200. Splitting the
    preflight into a non-generator helper means real HTTP errors
    surface BEFORE the response starts.
    """
    case_host_dir: Path
    run_id: str
    container: Any
    container_work_dir: str
    exec_result: Any  # docker ExecResult


def _prepare_stream_icofoam(
    *,
    case_host_dir: Path,
    container_name: str = CONTAINER_NAME,
    run_id: str | None = None,
) -> _PreparedStream:
    """Eager-mode preflight + staging + spawning.

    Validates the case, claims a per-case run_id (HIGH-2), connects to
    Docker, stages the tarball, and spawns icoFoam with
    ``exec_run(stream=True)``. All of these can raise
    :class:`SolverRunError` (or its :class:`SolveAlreadyRunning`
    subclass) — the route layer catches and translates to HTTP 4xx/5xx
    BEFORE returning the StreamingResponse.

    On any failure here, the run_id is released so a retry can claim
    it again.
    """
    if not case_host_dir.is_dir():
        raise SolverRunError(f"case dir not found: {case_host_dir}")
    if not (case_host_dir / "system" / "controlDict").is_file():
        raise SolverRunError(
            f"no system/controlDict at {case_host_dir} — run "
            "setup-bc first."
        )

    case_id = case_host_dir.name
    if run_id is None:
        run_id = _claim_run(case_id)
    else:
        # Caller-supplied run_id (tests). Still register so concurrent
        # callers see the in-flight state.
        with _runs_lock:
            if case_id in _active_runs:
                raise SolveAlreadyRunning(
                    f"solve already running for case {case_id!r} "
                    f"(run_id={_active_runs[case_id]})"
                )
            _active_runs[case_id] = run_id

    try:
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

        # Codex round-1 HIGH-2: container_work_dir is now run_id-suffixed
        # so concurrent runs (in spite of the lock, e.g. abandoned runs
        # whose lock entry was cleared by /finally) cannot collide on
        # log.icoFoam or the time directories.
        container_work_dir = f"{CONTAINER_WORK_BASE}/{case_id}-{run_id}"

        try:
            container.exec_run(
                cmd=[
                    "bash",
                    "-c",
                    f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}",
                ]
            )
            # Stage the case files under the run_id-suffixed dir. We
            # tar from case_host_dir, but extract under container_work_dir
            # whose basename matches case_host_dir.name only if run_id
            # is empty — so we send the tarball to a parent path and
            # rename. Simpler: send to CONTAINER_WORK_BASE then move.
            ok = container.put_archive(
                path=CONTAINER_WORK_BASE,
                data=_make_tarball(case_host_dir),
            )
            if not ok:
                raise SolverRunError(
                    "failed to stage case for streaming icoFoam"
                )
            # Rename the extracted dir from <case_id> to <case_id>-<run_id>.
            # Use mv so the rename is atomic even if multiple runs land
            # close together; if the source already vanished (parallel
            # rename), `mv` returns non-zero and we fall through.
            container.exec_run(
                cmd=[
                    "bash",
                    "-c",
                    f"if [ -d {CONTAINER_WORK_BASE}/{case_id} ] && "
                    f"[ ! -d {container_work_dir} ]; then "
                    f"mv {CONTAINER_WORK_BASE}/{case_id} {container_work_dir}; fi",
                ]
            )
        except docker.errors.DockerException as exc:
            raise SolverRunError(
                f"docker SDK error preparing container workspace: {exc}"
            ) from exc

        # Spawn icoFoam. ``stdbuf -oL`` line-buffers stdout so PISO
        # iterations arrive promptly instead of in 4KB chunks.
        bash_cmd = (
            "source /opt/openfoam10/etc/bashrc && "
            f"cd {container_work_dir} && "
            "stdbuf -oL -eL icoFoam 2>&1"
        )
        try:
            exec_result = container.exec_run(
                cmd=["bash", "-c", bash_cmd],
                stream=True,
                demux=False,
            )
        except docker.errors.DockerException as exc:
            raise SolverRunError(f"docker SDK error invoking icoFoam: {exc}") from exc
    except BaseException:
        # Any failure during preflight releases the lock so the user
        # can retry. The generator path takes ownership of the lock
        # release on its own try/finally.
        _release_run(case_id, run_id)
        raise

    return _PreparedStream(
        case_host_dir=case_host_dir,
        run_id=run_id,
        container=container,
        container_work_dir=container_work_dir,
        exec_result=exec_result,
    )


def stream_icofoam(
    *,
    case_host_dir: Path | None = None,
    container_name: str = CONTAINER_NAME,
    prepared: _PreparedStream | None = None,
) -> Iterator[bytes]:
    """Run icoFoam with streamed output. Yields SSE-formatted bytes
    that an EventSource client can consume directly.

    Two call shapes:

    * ``stream_icofoam(prepared=<_PreparedStream>)`` — preferred path
      used by the route. Preflight has already happened in
      :func:`_prepare_stream_icofoam`; this function only consumes the
      already-spawned exec result.
    * ``stream_icofoam(case_host_dir=...)`` — legacy entrypoint kept
      for tests + the blocking variant's parity. Internally calls
      ``_prepare_stream_icofoam`` then delegates.

    The first SSE event is always ``start`` with ``{"run_id": ...}``
    so the frontend can stamp every subsequent state-write with the
    matching run generation (HIGH-2 frontend half).

    Failures DURING the run land as in-stream ``error`` events; the
    HTTP status stays 200 because the stream has already started.
    """
    if prepared is None:
        if case_host_dir is None:
            raise TypeError(
                "stream_icofoam requires either prepared= or case_host_dir="
            )
        prepared = _prepare_stream_icofoam(
            case_host_dir=case_host_dir, container_name=container_name
        )

    case_host_dir = prepared.case_host_dir
    run_id = prepared.run_id
    container = prepared.container
    container_work_dir = prepared.container_work_dir
    exec_result = prepared.exec_result

    # Lazy-import docker.errors for the catch blocks below; the
    # ImportError path is unreachable here because preflight succeeded.
    import docker.errors  # type: ignore[import-not-found]

    # Buffer + line-by-line parse + accumulate full log on host.
    log_dest = case_host_dir / "log.icoFoam"
    log_buf = io.BytesIO()
    line_buf = b""
    current_time: list[float | None] = [None]
    last_p: list[float | None] = [None]
    fatal_seen: list[bool] = [False]

    # Codex rounds 2 & 3: wrap the ENTIRE generator body (including the
    # very first `start` yield) in an outer try/finally so a
    # GeneratorExit raised at ANY yield point — client disconnect on
    # the first event, FastAPI shutdown, mid-stream abort — releases
    # the per-case run lock and cleans up the container work dir.
    # Round 2 fixed the mid-loop case; round 3 caught that the start
    # yield was still OUTSIDE the try, so an immediate disconnect after
    # the very first SSE byte was still leaking _active_runs.
    try:
        # FIRST event: announce the run_id so the frontend can guard
        # state writes against stale runs. MUST stay inside the outer
        # try so a GeneratorExit on this yield still hits the finally.
        yield _sse("start", {"run_id": run_id, "case_id": case_host_dir.name})

        # Stream icoFoam output line-by-line.
        try:
            for chunk in exec_result.output:
                if not chunk:
                    continue
                log_buf.write(chunk)
                # Append chunk to the line buffer, split on \n, parse
                # each complete line. The trailing partial line stays
                # in the buffer for the next chunk.
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
            # Don't re-raise — let the done event below close the
            # stream cleanly; the client will see error then
            # done(converged=false).

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
    finally:
        # Always release the per-case run lock and (best-effort) clean
        # up the container work dir, even on GeneratorExit (client
        # disconnect mid-stream) or any other exception above.
        _release_run(case_host_dir.name, run_id)
        try:
            container.exec_run(
                cmd=["bash", "-c", f"rm -rf {container_work_dir}"]
            )
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass
