"""DEC-V61-126 · Docker checkMesh runner.

Invokes ``checkMesh`` inside the cfd-openfoam container against a case's
``constant/polyMesh`` and parses the stdout for canonical quality
metrics: max non-orthogonality, max skewness, max aspect ratio,
``Mesh OK`` / ``Failed N mesh checks`` verdict, severe-non-orthogonal
face count.

Mirrors ``services.meshing_gmsh.to_foam`` Docker SDK error contract:
container missing → ``container_unavailable``; container stopped →
``container_not_running``; SDK errors → ``docker_sdk_error``;
checkMesh exit nonzero → ``checkmesh_exit_nonzero``. The parser
handles partial/malformed output by returning ``None`` for missing
metrics rather than raising.

Per V61-122's separation of concerns, this module does NOT import
from ``meshing_gmsh.to_foam`` — the Docker SDK calls are duplicated
intentionally so V126 stays decoupled from the meshing pipeline's
hardening lineage. Same pattern V108 uses for its container ops.
"""
from __future__ import annotations

import io
import re
import tarfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path


# Container conventions match services.meshing_gmsh.to_foam — the
# cfd-openfoam container lives at the same name with the same UID/GID
# expectations. Different work dir to avoid colliding with gmshToFoam's
# staging area; checkMesh is read-only over polyMesh, so the dir can
# be cleaned up between calls without affecting the meshing pipeline.
CONTAINER_NAME = "cfd-openfoam"
CONTAINER_WORK_BASE = "/tmp/cfd-harness-cases-checkmesh"

# UID/GID retag for the openfoam user — same as to_foam._retag_for_container.
_CONTAINER_UID = 98765
_CONTAINER_GID = 98765


# V126 R1 P1: checkMesh refuses to start without system/controlDict.
# This is the minimum dictionary OpenFOAM 10 accepts — application
# label is informational, the time-control fields are required-but-
# unused (checkMesh only reads polyMesh). Same shape as the dictionary
# services/case_scaffold/bc_injector.write_control_dict() produces but
# trimmed to the absolute minimum so this module stays self-contained
# (parallel-new per surface-scan, no cross-import on bc_injector).
_MINIMAL_CONTROL_DICT = """\
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     checkMesh;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         0;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
"""


class CheckMeshError(RuntimeError):
    """Raised when checkMesh cannot run or its output cannot be parsed.

    ``failing_check`` enumerates the structural problem so the route
    surfaces a stable detail without leaking traceback contents:
      * ``polymesh_missing`` — case_dir/constant/polyMesh absent
      * ``docker_sdk_missing`` — docker SDK not installed
      * ``container_unavailable`` — container not found
      * ``container_not_running`` — container exists but stopped
      * ``docker_sdk_error`` — generic Docker SDK failure
      * ``checkmesh_exit_nonzero`` — checkMesh returned nonzero exit
        (distinct from "Mesh has issues but was parseable" which is
        exit 0 + Failed marker in stdout — handled by parser)
      * ``parse_error`` — output unrecognizable
    """

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


@dataclass(frozen=True, slots=True)
class CheckMeshResult:
    """Parsed checkMesh output. Numeric fields are ``None`` when the
    corresponding metric line was not found in stdout (e.g. checkMesh
    aborted mid-stream). ``mesh_ok`` is False unless the canonical
    "Mesh OK" line was matched."""

    max_non_orthogonality_deg: float | None
    max_skewness: float | None
    max_aspect_ratio: float | None
    mesh_ok: bool
    n_severe_non_ortho_faces: int | None
    failed_checks: list[str] = field(default_factory=list)
    raw_log_excerpt: str = ""
    # V129a: face indices written by checkMesh -allTopology -allGeometry
    # to constant/polyMesh/sets/nonOrthoFaces. Empty tuple when the set
    # file was absent (mesh passed the orthogonality check) OR when
    # parsing the file failed. Frozen tuple so the dataclass stays
    # hashable / immutable.
    severe_non_ortho_face_ids: tuple[int, ...] = ()


# ────────── Regex bank ──────────

# checkMesh's output format has been stable for these lines since
# OpenFOAM 4.x. The cfd-openfoam container ships OpenFOAM 10. The
# patterns are anchored on the canonical labels rather than precise
# whitespace, so future minor format adjustments don't break them.

_RE_NON_ORTHO = re.compile(
    r"Mesh non-orthogonality Max:\s*([\d.eE+-]+)\s+average:\s*([\d.eE+-]+)"
)
_RE_SKEWNESS = re.compile(r"Max skewness\s*=\s*([\d.eE+-]+)")
_RE_ASPECT = re.compile(r"Max aspect ratio\s*=\s*([\d.eE+-]+)")
# The "(> N degrees)" parenthetical is OpenFOAM-version-dependent text
# but the leading "Number of severely non-orthogonal" prefix is stable.
_RE_SEVERE_NON_ORTHO = re.compile(
    r"Number of severely non-orthogonal[^:]*:\s*(\d+)"
)
_RE_MESH_OK = re.compile(r"^Mesh OK\.?\s*$", re.MULTILINE)
_RE_FAILED = re.compile(r"Failed\s+(\d+)\s+mesh\s+check")

# V129a: faceSet body parser. The OpenFOAM-10 faceSet file looks like
#   FoamFile { ... object nonOrthoFaces; }
#   // ... separator
#   <count>
#   (
#   <face_id>
#   ...
#   )
# We lock onto the integer count line followed by `(`, then collect
# nonnegative integers up to the matching `)`. Header text varies
# (banner whitespace, license string) so a single regex over the
# whole file is brittle; the line-iter approach is more tolerant.
_RE_FACESET_OPEN = re.compile(r"^\s*\(\s*$")
_RE_FACESET_CLOSE = re.compile(r"^\s*\)\s*$")
_RE_FACESET_INT = re.compile(r"^\s*(\d+)\s*$")


# ────────── Helpers ──────────


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


def _make_polymesh_tarball(polymesh_dir: Path) -> bytes:
    """Pack just the polyMesh subset for checkMesh — typically 1-50 MB
    even for million-cell meshes, much faster than packing the full
    case_dir. The tar arcname keeps the polyMesh leaf so the container
    sees ``constant/polyMesh/`` after extraction."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        tar.add(
            str(polymesh_dir),
            arcname="polyMesh",
            filter=_retag_for_container,
        )
    return buf.getvalue()


def _parse_faceset_body(text: str) -> tuple[int, ...]:
    """Parse an OpenFOAM faceSet dictionary body into a tuple of face
    indices. Tolerant of header banner / FoamFile dict / blank text:
    returns empty tuple when no list body is found.

    Format (verified against OpenFOAM-10 checkMesh output):
        FoamFile { ... }
        // separator
        <count>
        (
        <id>
        <id>
        ...
        )
    """
    if not text or not text.strip():
        return ()
    lines = text.splitlines()
    in_list = False
    ids: list[int] = []
    for line in lines:
        if not in_list:
            if _RE_FACESET_OPEN.match(line):
                in_list = True
            continue
        if _RE_FACESET_CLOSE.match(line):
            break
        m = _RE_FACESET_INT.match(line)
        if m:
            ids.append(int(m.group(1)))
    return tuple(ids)


def _parse_checkmesh_output(stdout: str) -> CheckMeshResult:
    """Parse checkMesh stdout into a structured result.

    Missing metrics return None (graceful — checkMesh aborted partway
    or output a non-canonical format). Parser does NOT raise; the
    raw_log_excerpt captures the last 50 lines for diagnosis.
    """
    non_ortho_match = _RE_NON_ORTHO.search(stdout)
    skewness_match = _RE_SKEWNESS.search(stdout)
    aspect_match = _RE_ASPECT.search(stdout)
    severe_match = _RE_SEVERE_NON_ORTHO.search(stdout)
    mesh_ok = bool(_RE_MESH_OK.search(stdout))
    failed_match = _RE_FAILED.search(stdout)

    failed_checks: list[str] = []
    if failed_match and not mesh_ok:
        # checkMesh marks specific failures with "***" — typically at
        # line start, but OpenFOAM 10 sometimes inlines the marker mid-
        # line (e.g. "Max skewness = 4.2 ***Max skewness = 4.2 > 4 --
        # SKEWED CELLS DETECTED."). Match anywhere in the stripped line.
        # Filter "OK"-line noise that still uses ***.
        for line in stdout.splitlines():
            stripped = line.strip()
            if "***" in stripped and "OK" not in stripped:
                # Capture the substring starting at the *** marker so
                # the surfaced failure text reads naturally.
                marker_idx = stripped.find("***")
                failed_checks.append(stripped[marker_idx:].lstrip("* ").rstrip())

    raw_excerpt = "\n".join(stdout.splitlines()[-50:])

    return CheckMeshResult(
        max_non_orthogonality_deg=(
            float(non_ortho_match.group(1)) if non_ortho_match else None
        ),
        max_skewness=(
            float(skewness_match.group(1)) if skewness_match else None
        ),
        max_aspect_ratio=(
            float(aspect_match.group(1)) if aspect_match else None
        ),
        mesh_ok=mesh_ok,
        n_severe_non_ortho_faces=(
            int(severe_match.group(1)) if severe_match else None
        ),
        failed_checks=failed_checks,
        raw_log_excerpt=raw_excerpt,
    )


# ────────── Public entry point ──────────


def run_checkmesh(
    case_dir: Path,
    *,
    container_name: str = CONTAINER_NAME,
) -> CheckMeshResult:
    """Run ``checkMesh`` inside the cfd-openfoam container against
    ``case_dir/constant/polyMesh`` and return parsed quality metrics.

    Raises :class:`CheckMeshError` whose ``failing_check`` attribute
    enumerates the structural problem so the caller can map it to a
    stable HTTP detail or graceful-degrade per V126's
    ``run_checkmesh=True`` opt-in semantics.

    The function is read-only over the host case_dir — only the in-
    memory tarball touches polyMesh, and the container's work area
    is independent of the host. Callers do NOT need to hold
    ``case_lock`` around this call.
    """
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        raise CheckMeshError(
            f"polyMesh directory missing at {polymesh}",
            failing_check="polymesh_missing",
        )

    try:
        import docker  # type: ignore[import-not-found]
        import docker.errors  # type: ignore[import-not-found]
    except ImportError as exc:
        raise CheckMeshError(
            "docker SDK is not installed — install with `pip install "
            "'docker>=7.0'` (already in the [ui] extra). checkMesh must "
            "run inside the cfd-openfoam container.",
            failing_check="docker_sdk_missing",
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            raise CheckMeshError(
                f"container '{container_name}' is not running "
                f"(status={container.status!r}); start it with "
                f"`docker start {container_name}`.",
                failing_check="container_not_running",
            )
    except docker.errors.NotFound as exc:
        raise CheckMeshError(
            f"container '{container_name}' not found. Bring up the "
            f"cfd-openfoam container before requesting checkMesh.",
            failing_check="container_unavailable",
        ) from exc
    except docker.errors.DockerException as exc:
        raise CheckMeshError(
            f"docker client init failed: {exc}",
            failing_check="docker_sdk_error",
        ) from exc

    # V126 R1 P2-1: per-call unique workspace so concurrent calls for
    # the same case don't clobber each other (a double-click or two
    # parallel users could otherwise race the rm -rf against an active
    # checkMesh and produce metrics from the wrong mesh or spurious
    # 502s). UUID hex is 32 chars; truncate to 12 for path readability.
    run_token = uuid.uuid4().hex[:12]
    container_work = f"{CONTAINER_WORK_BASE}/{case_dir.name}/{run_token}"
    # V126 R2 P2-2: wrap the entire workspace lifecycle in try/finally
    # so the unique dir is torn down on EVERY exit path, not just the
    # happy-path checkMesh exec. Without this, a put_archive=False
    # return, an exec_run raise during controlDict staging, or any
    # mid-setup CheckMeshError leaks polyMesh copies under
    # /tmp/cfd-harness-cases-checkmesh inside the container — and
    # since each run has a unique uuid, those dirs are never reused.
    try:
        try:
            # Provision a clean workspace with both 'constant' (for the
            # polyMesh tarball) and 'system' (for the controlDict
            # OpenFOAM requires before any utility will start).
            container.exec_run(
                cmd=[
                    "bash",
                    "-c",
                    f"mkdir -p {container_work}/constant {container_work}/system",
                ]
            )
            archive_ok = container.put_archive(
                path=f"{container_work}/constant",
                data=_make_polymesh_tarball(polymesh),
            )
        except docker.errors.DockerException as exc:
            raise CheckMeshError(
                f"docker SDK error preparing checkMesh workspace: {exc}",
                failing_check="docker_sdk_error",
            ) from exc
        except OSError as exc:
            raise CheckMeshError(
                f"failed to build checkMesh tarball for {case_dir.name} "
                f"(host filesystem fault): {exc}",
                failing_check="docker_sdk_error",
            ) from exc

        if not archive_ok:
            raise CheckMeshError(
                f"failed to copy polyMesh into container at {container_work}",
                failing_check="docker_sdk_error",
            )

        # V126 R1 P1: stage system/controlDict so checkMesh's OpenFOAM
        # bootstrap doesn't error out before producing any metrics.
        # heredoc-style write via bash -c keeps this self-contained
        # (no extra put_archive round trip).
        try:
            container.exec_run(
                cmd=[
                    "bash",
                    "-c",
                    f"cat > {container_work}/system/controlDict <<'CONTROLDICT_EOF'\n"
                    f"{_MINIMAL_CONTROL_DICT}"
                    f"CONTROLDICT_EOF",
                ]
            )
        except docker.errors.DockerException as exc:
            raise CheckMeshError(
                f"docker SDK error staging controlDict: {exc}",
                failing_check="docker_sdk_error",
            ) from exc

        # V129a: -allGeometry -allTopology enables the extra checks that
        # cause checkMesh to write `nonOrthoFaces` / `skewFaces` faceSets
        # to constant/polyMesh/sets/ when faces fail those thresholds.
        # We append a sentinel + cat the nonOrthoFaces set so the parser
        # can extract per-face IDs without a second exec round-trip.
        #
        # R1 P1 closure: capture checkMesh's exit code in `rc` BEFORE
        # the echo+cat tail, then `exit $rc` at the end so the chain's
        # exit status reflects checkMesh — not the always-success cat.
        # Without this, the existing `checkmesh_exit_nonzero` failing-
        # check path (corrupt polyMesh, missing required files) is
        # unreachable and fatal failures fall through as bogus
        # successful V126 responses.
        bash_cmd = (
            f"source /opt/openfoam10/etc/bashrc && "
            f"cd {container_work} && "
            f"checkMesh -allGeometry -allTopology 2>&1; rc=$?; "
            f"echo '__CFD_HARNESS_SET_BODY_DELIM__'; "
            f"cat constant/polyMesh/sets/nonOrthoFaces 2>/dev/null || true; "
            f"exit $rc"
        )
        try:
            exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
        except docker.errors.DockerException as exc:
            raise CheckMeshError(
                f"docker SDK error invoking checkMesh: {exc}",
                failing_check="docker_sdk_error",
            ) from exc
    finally:
        # Best-effort cleanup. Runs on every path — happy success,
        # CheckMeshError mid-setup, or unexpected exception. We swallow
        # any exception from the cleanup itself so a transient docker
        # issue here doesn't mask the original error the caller cares
        # about. R1's `rc=$?; rm -rf; exit $rc` inline trick was
        # insufficient because it only fired when the final exec_run
        # was actually reached.
        try:
            container.exec_run(cmd=["bash", "-c", f"rm -rf {container_work}"])
        except Exception:  # noqa: BLE001 — best-effort, never mask primary error
            pass

    output = exec_result.output.decode("utf-8", errors="replace")

    # V129a: split off the trailing nonOrthoFaces faceSet body before
    # surfacing the rest as checkMesh stdout. Keep the parser tolerant
    # of the absent-sentinel case so older container images that
    # somehow lack the cat-tail still produce a result (set ids stay
    # empty in that path).
    set_body = ""
    delim = "__CFD_HARNESS_SET_BODY_DELIM__"
    if delim in output:
        output, _, set_body = output.partition(delim)

    # checkMesh exit code semantics (OpenFOAM 10):
    #   * exit 0 + "Mesh OK" → healthy mesh
    #   * exit 0 + "Failed N mesh checks" → mesh has issues but checkMesh
    #     itself ran successfully; parser captures the failures
    #   * exit nonzero → fatal config error (e.g. polyMesh corrupt,
    #     missing required files). Surface as typed error.
    if exec_result.exit_code != 0:
        raise CheckMeshError(
            f"checkMesh exit_code={exec_result.exit_code}; "
            f"output excerpt: {output[-500:]!r}",
            failing_check="checkmesh_exit_nonzero",
        )

    base = _parse_checkmesh_output(output)
    severe_face_ids = _parse_faceset_body(set_body)
    if not severe_face_ids:
        return base
    # CheckMeshResult is frozen; re-emit a copy with the ids set.
    return CheckMeshResult(
        max_non_orthogonality_deg=base.max_non_orthogonality_deg,
        max_skewness=base.max_skewness,
        max_aspect_ratio=base.max_aspect_ratio,
        mesh_ok=base.mesh_ok,
        n_severe_non_ortho_faces=base.n_severe_non_ortho_faces,
        failed_checks=base.failed_checks,
        raw_log_excerpt=base.raw_log_excerpt,
        severe_non_ortho_face_ids=severe_face_ids,
    )
