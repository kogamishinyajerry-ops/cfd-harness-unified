"""Invoke ``gmshToFoam`` inside the cfd-openfoam container.

This is the bridge from gmsh's ``.msh`` output (M6.0 produces it on the
host) to the OpenFOAM ``constant/polyMesh/`` format that the executor
(M6.1 + M7) consumes.

We intentionally do NOT import any helper from
``src.foam_agent_adapter`` — that lives in the trust-core / line-B
plane and importing from it would re-introduce the line-A → trust-core
coupling that ADR-001 forbids. The Docker SDK calls duplicated here are
small (~40 LOC) and self-contained.
"""
from __future__ import annotations

import io
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path


CONTAINER_NAME = "cfd-openfoam"
CONTAINER_WORK_BASE = "/tmp/cfd-harness-cases-mesh"


class GmshToFoamError(RuntimeError):
    """Raised when gmshToFoam fails to convert ``.msh`` → polyMesh."""


@dataclass(frozen=True, slots=True)
class GmshToFoamResult:
    polyMesh_dir: Path  # absolute host path: case_dir / constant / polyMesh
    log_path: Path
    used_container: bool


# The cfd-openfoam container runs as uid=98765(openfoam). The host
# typically runs as a different uid (often 502/dialout on macOS).
# When ``put_archive`` extracts files preserving host uid/gid, the
# openfoam user can't write into the directories it doesn't own —
# gmshToFoam fails with "POSIX directory write permission denied"
# trying to ``mkdir constant/polyMesh/``. Re-tag every entry to the
# openfoam uid/gid + a permissive mode (M-PANELS Step 10 visual-smoke
# fix) so the container side has full control of the staged case dir.
_CONTAINER_UID = 98765
_CONTAINER_GID = 98765


def _retag_for_container(info: "tarfile.TarInfo") -> "tarfile.TarInfo":
    info.uid = _CONTAINER_UID
    info.gid = _CONTAINER_GID
    info.uname = "openfoam"
    info.gname = "openfoam"
    if info.isdir():
        info.mode = 0o755
    else:
        info.mode = 0o644
    return info


def _make_tarball(host_dir: Path) -> bytes:
    """Pack ``host_dir`` recursively into an in-memory tarball, retagged
    for the cfd-openfoam container's UID/GID so gmshToFoam can write
    polyMesh + log files into the staged case dir.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        tar.add(str(host_dir), arcname=host_dir.name, filter=_retag_for_container)
    return buf.getvalue()


def _extract_tarball(stream_bytes: bytes, dest_dir: Path) -> None:
    """Unpack a tarball produced by ``container.get_archive`` into
    ``dest_dir``. Used to copy ``constant/polyMesh/`` back from the
    container.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(stream_bytes)
    with tarfile.open(fileobj=buf, mode="r") as tar:
        tar.extractall(path=dest_dir, filter="data")


def _safe_log_name(command: str) -> str:
    return "log." + (re.sub(r"[^A-Za-z0-9]", "_", command).strip("_") or "cmd")


def run_gmsh_to_foam(
    *,
    case_host_dir: Path,
    msh_relpath: str = "imported.msh",
    container_name: str = CONTAINER_NAME,
) -> GmshToFoamResult:
    """Convert ``case_host_dir / msh_relpath`` into
    ``case_host_dir / constant / polyMesh/`` using ``gmshToFoam`` inside
    the configured Docker container.

    On success, returns a :class:`GmshToFoamResult` whose ``polyMesh_dir``
    exists and contains at least the canonical files
    (``points``, ``faces``, ``owner``, ``neighbour``, ``boundary``).

    Raises :class:`GmshToFoamError` if Docker is unavailable, the
    container is missing, or ``gmshToFoam`` reports failure.
    """
    # Codex Round 8 Finding 2: collapse the exists()→stat()/use() TOCTTOU
    # window. We can't fully eliminate the gap before the tarball is built,
    # but stat() with FileNotFoundError catch turns the structured
    # GmshToFoamError contract into the actual observable signal regardless
    # of whether the file was missing at moment-of-check or moment-of-use.
    msh_path = case_host_dir / msh_relpath
    try:
        msh_path.stat()
    except FileNotFoundError as exc:
        raise GmshToFoamError(
            f"expected gmsh output at {msh_path}, but it does not exist — "
            "did the gmsh runner succeed?"
        ) from exc

    try:
        import docker  # type: ignore[import-not-found]
        import docker.errors  # type: ignore[import-not-found]
    except ImportError as exc:
        raise GmshToFoamError(
            "docker SDK is not installed — install with `pip install "
            "'docker>=7.0'` (already in the [ui] extra). gmshToFoam "
            "must run inside the cfd-openfoam container."
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            raise GmshToFoamError(
                f"container '{container_name}' is not running "
                f"(status={container.status!r}); start it with "
                f"`docker start {container_name}`."
            )
    except docker.errors.NotFound as exc:
        raise GmshToFoamError(
            f"container '{container_name}' not found. Bring up the "
            f"cfd-openfoam container before importing geometry."
        ) from exc
    except docker.errors.DockerException as exc:
        raise GmshToFoamError(
            f"docker client init failed: {exc}"
        ) from exc

    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
    # Wrap the rest of the container interaction in a single try/except
    # so any raw docker SDK error (APIError / connection drop /
    # archive failure) surfaces as GmshToFoamError. The pipeline +
    # route layers expect that contract.
    try:
        container.exec_run(
            cmd=["bash", "-c", f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}"]
        )
        archive_ok = container.put_archive(
            path=CONTAINER_WORK_BASE,
            data=_make_tarball(case_host_dir),
        )
    except docker.errors.DockerException as exc:
        raise GmshToFoamError(
            f"docker SDK error preparing container workspace: {exc}"
        ) from exc

    if not archive_ok:
        raise GmshToFoamError(
            f"failed to copy case dir into container at {container_work_dir}"
        )

    log_filename = _safe_log_name("gmshToFoam")
    bash_cmd = (
        f"source /opt/openfoam10/etc/bashrc && "
        f"cd {container_work_dir} && "
        f"gmshToFoam {msh_relpath} > {log_filename} 2>&1"
    )
    try:
        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
    except docker.errors.DockerException as exc:
        raise GmshToFoamError(
            f"docker SDK error invoking gmshToFoam: {exc}"
        ) from exc

    # Pull the log + the polyMesh dir back to the host so the caller can
    # inspect them. Always pull the log first — if gmshToFoam failed, we
    # need it for the rejection message.
    try:
        bits, _ = container.get_archive(f"{container_work_dir}/{log_filename}")
        log_dest = case_host_dir / log_filename
        _extract_tarball(b"".join(chunk for chunk in bits), case_host_dir.parent)
        # Tar extraction places it under a top-level dir named after
        # the archived file's parent; flatten if needed.
        if not log_dest.exists():
            shutil.move(str(case_host_dir.parent / log_filename), str(log_dest))
    except Exception:  # noqa: BLE001 — best-effort log copy
        log_dest = case_host_dir / log_filename
        log_dest.write_text(
            "(log file could not be retrieved from container)\n",
            encoding="utf-8",
        )

    if exec_result.exit_code != 0:
        raise GmshToFoamError(
            f"gmshToFoam exit_code={exec_result.exit_code}; see "
            f"{log_dest} for full output."
        )

    # Pull constant/polyMesh back to the host case dir.
    polyMesh_host = case_host_dir / "constant" / "polyMesh"
    polyMesh_host.parent.mkdir(parents=True, exist_ok=True)
    try:
        bits, _ = container.get_archive(f"{container_work_dir}/constant/polyMesh")
        _extract_tarball(
            b"".join(chunk for chunk in bits),
            case_host_dir / "constant",
        )
    except docker.errors.NotFound as exc:
        raise GmshToFoamError(
            "gmshToFoam ran without error but produced no "
            "constant/polyMesh/ directory in the container. See log."
        ) from exc
    except docker.errors.DockerException as exc:
        raise GmshToFoamError(
            f"docker SDK error retrieving polyMesh from container: {exc}"
        ) from exc

    # Codex Round 8 Finding 2: collapse the exists()→iterdir() TOCTTOU
    # window. If the polyMesh dir disappears between the two syscalls
    # (concurrent cleanup, host-side rm -rf), iterdir() raises
    # FileNotFoundError; treat that as the same "directory missing"
    # signal the explicit-check produced — required-files set is the
    # full canonical list.
    required = {"points", "faces", "owner", "neighbour", "boundary"}
    try:
        present = {p.name for p in polyMesh_host.iterdir()}
    except FileNotFoundError:
        present = set()
    missing = required - present
    if missing:
        raise GmshToFoamError(
            f"polyMesh is missing canonical files: {sorted(missing)}. "
            f"See {log_dest}."
        )

    return GmshToFoamResult(
        polyMesh_dir=polyMesh_host,
        log_path=log_dest,
        used_container=True,
    )
