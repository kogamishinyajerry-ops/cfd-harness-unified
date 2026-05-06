"""Invoke ``snappyHexMesh`` (addLayers stage) inside the cfd-openfoam
container.

Mirrors the structural pattern of ``services/meshing_gmsh/to_foam.py``:
docker SDK only, retag tarball entries to the container's UID/GID,
push case dir → exec → pull polyMesh + log back. We intentionally
duplicate the docker calls (~150 LOC) rather than abstract them with
``to_foam`` because the two operations have different command shapes,
different success-detection logic, and different failure taxonomies.

Sequence:
    1. Verify case_dir / constant / polyMesh exists (gmsh stage ran)
    2. Verify the requested patch name is in
       constant/polyMesh/boundary
    3. Render system/snappyHexMeshDict from the engineer's payload
    4. Tarball the case dir → put into cfd-openfoam container
    5. exec ``snappyHexMesh -overwrite`` in the container
    6. Parse the addLayers log for layer-coverage stats
    7. Pull constant/polyMesh + log back to the host
"""
from __future__ import annotations

import io
import re
import shutil
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path

from ui.backend.schemas.mesh_prism_layers import PatchPrismConfig

from .addlayers_renderer import render_snappy_dict


CONTAINER_NAME = "cfd-openfoam"
CONTAINER_WORK_BASE = "/tmp/cfd-harness-cases-snappy"

_CONTAINER_UID = 98765
_CONTAINER_GID = 98765


class SnappyAddLayersError(RuntimeError):
    """Raised when snappyHexMesh's addLayers stage fails or does not
    converge. User-input fault (geometry / config produces unrunnable
    layer addition). Pipeline maps to 422.
    """


class SnappyContainerError(RuntimeError):
    """Raised when the container infrastructure is unavailable / faults
    during the snappyHexMesh invocation. Backend / deployment fault.
    Pipeline maps to 502 / 5xx.
    """


@dataclass(frozen=True, slots=True)
class SnappyRunResult:
    polyMesh_dir: Path  # absolute host path to refreshed constant/polyMesh
    log_path: Path
    layers_added: int
    coverage_fraction: float | None
    generation_time_s: float


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
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        tar.add(str(host_dir), arcname=host_dir.name, filter=_retag_for_container)
    return buf.getvalue()


def _extract_tarball(stream_bytes: bytes, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(stream_bytes)
    with tarfile.open(fileobj=buf, mode="r") as tar:
        tar.extractall(path=dest_dir)


def _safe_log_name(command: str) -> str:
    return "log." + (re.sub(r"[^A-Za-z0-9]", "_", command).strip("_") or "cmd")


def _read_boundary_patch_names(polyMesh_dir: Path) -> set[str]:
    """Return the set of patch names declared in
    ``constant/polyMesh/boundary``.

    OpenFOAM's polyMesh boundary file is small enough to scan with a
    simple regex; we only care about the per-block names that follow
    the opening list bracket. Returns an empty set when the file is
    missing or unparseable — caller raises a structured rejection in
    that case.
    """
    boundary_file = polyMesh_dir / "boundary"
    try:
        text = boundary_file.read_text(encoding="utf-8")
    except OSError:
        return set()

    # The boundary file structure is:
    #     N
    #     (
    #         patch_name_a
    #         {
    #             type ...;
    #             ...
    #         }
    #         patch_name_b
    #         { ... }
    #     )
    # We capture the identifier that appears on its own line just
    # before an opening brace. The simple regex below is a defensive
    # match — production reading would use a proper FoamFile parser
    # but that's a much bigger dep. The names are declarative; this
    # is enough for "is patch X in boundary".
    names: set[str] = set()
    for match in re.finditer(
        r"^\s*([A-Za-z_][A-Za-z0-9_.\-]*)\s*\n\s*\{",
        text,
        flags=re.MULTILINE,
    ):
        candidate = match.group(1)
        # Skip the FoamFile header block keys.
        if candidate in {"FoamFile", "boundary"}:
            continue
        names.add(candidate)
    return names


def _parse_addlayers_log(
    log_text: str,
) -> tuple[int | None, float | None, bool]:
    """Return ``(layers_added, coverage_fraction, definite_zero)`` from
    a snappyHexMesh addLayers log.

    R0 P1 + P2 (Codex 86gs): the previous version returned ``(0, None)``
    on unparseable logs and the caller mapped 0 → 422
    snappy_addlayers_did_not_converge. That conflated "log wording
    differs from our exact regex" with "snappyHexMesh actually
    refused to add layers", so a successful run on a different
    OpenFOAM build would surface as a failure even though it produced
    a perfectly good mesh.

    Three-state return:
      * ``layers_added`` — non-None positive int when a layer count
        was successfully extracted; None when the log is silent.
      * ``coverage_fraction`` — float in [0, 1] when extracted;
        None otherwise.
      * ``definite_zero`` — True ONLY when the log contains a strong
        explicit "no layers were added" signal (e.g. an explicit
        ``Layers added: 0`` line or a per-patch summary saying
        "0 layers requested 0 layers added"). The caller uses this
        as the trigger for the addlayers-did-not-converge rejection;
        an unparseable / silent log no longer maps to a failure.

    Coverage normalization (R0 P2): the percent vs fraction
    discriminator now looks for the literal ``%`` token in the
    matched substring rather than a value-magnitude heuristic — a
    real ``Overall layer coverage: 0.8 %`` is 0.008, not 0.8.
    """
    layers: int | None = None
    coverage: float | None = None
    definite_zero = False

    # Coverage fraction. Capture both the value AND any trailing
    # ``%`` so the normalization is robust against small percent
    # values (the old > 1.0 heuristic mis-handled "0.8 %" as a
    # fraction). The match window is the immediate substring after
    # "Overall layer coverage" through the ``%`` (if present).
    cov_match = re.search(
        r"Overall layer coverage[^\d-]+(-?[0-9]*\.?[0-9]+)\s*(%?)",
        log_text,
    )
    if cov_match:
        try:
            cov_val = float(cov_match.group(1))
            has_percent = cov_match.group(2) == "%"
            coverage = cov_val / 100.0 if has_percent else cov_val
            # Clamp into [0, 1] in case of weirdly-formatted log.
            if coverage is not None:
                if coverage < 0.0:
                    coverage = 0.0
                elif coverage > 1.0:
                    coverage = 1.0
        except ValueError:
            coverage = None

    # "Layers added" header from OpenFOAM. Capture the number; if it's
    # explicitly 0 that's the strong signal we mark as definite_zero.
    layer_match = re.search(
        r"Layers? added(?: at finalisation)?[\s:]+(\d+)",
        log_text,
        flags=re.IGNORECASE,
    )
    if layer_match:
        try:
            n = int(layer_match.group(1))
            layers = n
            if n == 0:
                definite_zero = True
        except ValueError:
            layers = None

    if layers is None:
        # Fallback 1: per-patch summary lines of the form
        # "<patch>  N requested  M added". If every per-patch line
        # reports 0 added (and there is at least one such line),
        # that's a strong signal of definite zero.
        per_patch = re.findall(
            r"(?P<requested>\d+)\s+(?:layers?\s+)?requested[,\s]+"
            r"(?P<added>\d+)\s+(?:layers?\s+)?added",
            log_text,
            flags=re.IGNORECASE,
        )
        if per_patch:
            added_counts = [int(a) for _, a in per_patch]
            if added_counts:
                layers = max(added_counts)
                if layers == 0:
                    definite_zero = True

    if layers is None:
        # Fallback 2: count addLayer iterations performed. If there
        # are iteration markers, snappyHexMesh got into the addLayers
        # phase — bound the answer at the iteration count. NOT a
        # definite_zero signal regardless.
        iters = re.findall(r"Layer addition iteration (\d+)", log_text)
        if iters:
            try:
                layers = max(int(s) for s in iters)
            except ValueError:
                layers = None

    return layers, coverage, definite_zero


def run_snappy_addlayers(
    *,
    case_host_dir: Path,
    patches: list[PatchPrismConfig],
    container_name: str = CONTAINER_NAME,
) -> SnappyRunResult:
    """Run the addLayers stage of snappyHexMesh on the existing
    polyMesh under ``case_host_dir``.

    Raises:
        SnappyAddLayersError — pre-checks failed (no polyMesh, patch
            name mismatch) OR snappyHexMesh exited non-zero.
        SnappyContainerError — docker / container-side failure.
    """
    polyMesh_dir = case_host_dir / "constant" / "polyMesh"
    if not polyMesh_dir.is_dir() or not (polyMesh_dir / "boundary").is_file():
        raise SnappyAddLayersError(
            f"polyMesh not ready under {polyMesh_dir} — run the gmsh "
            "stage (POST /api/import/{case_id}/mesh) first."
        )

    declared_patches = _read_boundary_patch_names(polyMesh_dir)
    requested_patches = {p.patch for p in patches}
    missing = requested_patches - declared_patches
    if missing:
        raise SnappyAddLayersError(
            f"patch(es) {sorted(missing)} not present in "
            f"{polyMesh_dir / 'boundary'} — declared patches are "
            f"{sorted(declared_patches)}. Did the gmsh stage produce "
            "the expected boundary?"
        )

    # Render dict to disk so the audit trail captures exactly what
    # was sent to snappyHexMesh.
    system_dir = case_host_dir / "system"
    system_dir.mkdir(parents=True, exist_ok=True)
    dict_path = system_dir / "snappyHexMeshDict"
    dict_path.write_text(render_snappy_dict(patches), encoding="utf-8")

    try:
        import docker  # type: ignore[import-not-found]
        import docker.errors  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SnappyContainerError(
            "docker SDK is not installed — install with `pip install "
            "'docker>=7.0'`. snappyHexMesh must run inside the "
            "cfd-openfoam container."
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status != "running":
            raise SnappyContainerError(
                f"container '{container_name}' is not running "
                f"(status={container.status!r}); start it with "
                f"`docker start {container_name}`."
            )
    except docker.errors.NotFound as exc:
        raise SnappyContainerError(
            f"container '{container_name}' not found. Bring up the "
            "cfd-openfoam container before adding prism layers."
        ) from exc
    except docker.errors.DockerException as exc:
        raise SnappyContainerError(
            f"docker client init failed: {exc}"
        ) from exc

    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"
    try:
        container.exec_run(
            cmd=[
                "bash",
                "-c",
                f"mkdir -p {container_work_dir} && chmod 777 {container_work_dir}",
            ]
        )
        archive_ok = container.put_archive(
            path=CONTAINER_WORK_BASE,
            data=_make_tarball(case_host_dir),
        )
    except docker.errors.DockerException as exc:
        raise SnappyContainerError(
            f"docker SDK error preparing snappy workspace: {exc}"
        ) from exc
    except FileNotFoundError as exc:
        raise SnappyContainerError(
            f"case dir vanished while building tarball for "
            f"{case_host_dir.name}: {exc}"
        ) from exc
    except OSError as exc:
        raise SnappyContainerError(
            f"failed to build snappy tarball for {case_host_dir.name} "
            f"(host filesystem fault): {exc}"
        ) from exc

    if not archive_ok:
        raise SnappyContainerError(
            f"failed to copy case dir into container at {container_work_dir}"
        )

    log_filename = _safe_log_name("snappyHexMesh")
    bash_cmd = (
        f"source /opt/openfoam10/etc/bashrc && "
        f"cd {container_work_dir} && "
        f"snappyHexMesh -overwrite > {log_filename} 2>&1"
    )
    t0 = time.monotonic()
    try:
        exec_result = container.exec_run(cmd=["bash", "-c", bash_cmd])
    except docker.errors.DockerException as exc:
        raise SnappyContainerError(
            f"docker SDK error invoking snappyHexMesh: {exc}"
        ) from exc

    # Pull log first so a failure still yields a rejection reason.
    try:
        bits, _ = container.get_archive(f"{container_work_dir}/{log_filename}")
        log_dest = case_host_dir / log_filename
        _extract_tarball(b"".join(chunk for chunk in bits), case_host_dir.parent)
        if not log_dest.exists():
            shutil.move(
                str(case_host_dir.parent / log_filename),
                str(log_dest),
            )
    except Exception:  # noqa: BLE001 — best-effort log copy
        log_dest = case_host_dir / log_filename
        try:
            log_dest.write_text(
                "(log file could not be retrieved from container)\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise SnappyContainerError(
                f"failed to persist fallback snappy log at {log_dest}: {exc}"
            ) from exc

    if exec_result.exit_code != 0:
        # Read whatever log we managed to retrieve so the route can
        # surface the actual snappyHexMesh stderr message.
        tail = ""
        try:
            tail = log_dest.read_text(encoding="utf-8")[-2000:]
        except OSError:
            tail = "(unable to read log)"
        raise SnappyAddLayersError(
            f"snappyHexMesh exit_code={exec_result.exit_code}; see "
            f"{log_dest}. Tail:\n{tail}"
        )

    # R0 P1 (Codex 86gs): pull + stage refreshed polyMesh BEFORE
    # parsing/validating; do NOT swap into place yet. The previous
    # version swapped first then raised on layers_added==0, leaving
    # the host with a mutated mesh while the route reported failure.
    # Now we extract to a staging dir, validate the run via the log,
    # and only commit the swap on definite success.
    staging = case_host_dir / ".snappy_pull"
    try:
        poly_bits, _ = container.get_archive(
            f"{container_work_dir}/constant/polyMesh"
        )
        if staging.exists():
            shutil.rmtree(staging)
        _extract_tarball(b"".join(chunk for chunk in poly_bits), staging)
        new_poly = staging / "polyMesh"
        if not new_poly.is_dir():
            raise SnappyContainerError(
                f"snappyHexMesh did not produce {new_poly} on extraction"
            )
    except docker.errors.DockerException as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise SnappyContainerError(
            f"docker SDK error pulling polyMesh back from container: {exc}"
        ) from exc
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise SnappyContainerError(
            f"failed to extract polyMesh to staging (host filesystem fault): {exc}"
        ) from exc

    # Parse the log for layers-added + coverage stats. R0 P1 (Codex
    # 86gs): only definite_zero blocks the swap; an unparseable log
    # no longer fails the run (different OpenFOAM builds emit
    # different summary wording).
    log_text = ""
    try:
        log_text = log_dest.read_text(encoding="utf-8")
    except OSError:
        log_text = ""
    layers_added, coverage, definite_zero = _parse_addlayers_log(log_text)

    if definite_zero:
        # Discard the staged polyMesh — host's existing polyMesh
        # remains untouched, contract is "failure means no mutation".
        shutil.rmtree(staging, ignore_errors=True)
        # R1 P2 (Codex 86gs): keep the substring "no layers were
        # actually added" in the message so pipeline.apply_prism_layers
        # maps this to failing_check=snappy_addlayers_did_not_converge
        # instead of falling back to the generic snappy_diverged
        # bucket. The substring is the dispatch contract between the
        # runner and the pipeline.
        raise SnappyAddLayersError(
            "snappyHexMesh exit_code=0 but no layers were actually "
            "added (definite_zero signal: log explicitly reports 0 "
            "layers added or per-patch summary shows 0/N). Most "
            "common cause: geometry has high curvature or non-"
            "orthogonal faces near the wall; reduce first_cell_height "
            "or expansion_ratio. (Host polyMesh unchanged.)"
        )

    # R2 P2 (Codex 86gs): clean up the stale polyMesh.pre_split
    # backup BEFORE swapping the new polyMesh into place. If we
    # swapped first and rmtree(pre_split) then failed, the route
    # would return snappy_container_failed → frontend skips
    # mesh:mutated invalidation → UI shows the OLD mesh while the
    # disk holds the NEW one → engineer's retry runs addLayers on
    # an already-mutated mesh. Cleaning before the swap means a
    # cleanup failure leaves the host pre-swap (untouched polyMesh)
    # and the failure is genuine "no mutation happened".
    pre_split = polyMesh_dir.with_suffix(".pre_split")
    if pre_split.exists():
        try:
            shutil.rmtree(pre_split)
        except OSError as exc:
            shutil.rmtree(staging, ignore_errors=True)
            raise SnappyContainerError(
                f"refusing to add prism layers because stale {pre_split} "
                f"could not be removed — leaving it would silently revert "
                f"the prism mesh on the next BC setup. Manual cleanup "
                f"required: `rm -rf {pre_split}`. Underlying error: {exc}"
            ) from exc

    # Commit the swap. Atomic-ish: rename existing polyMesh →
    # polyMesh.prev, move the new tree in, drop the previous.
    try:
        prev = polyMesh_dir.with_suffix(".prev")
        if prev.exists():
            shutil.rmtree(prev)
        shutil.move(str(polyMesh_dir), str(prev))
        shutil.move(str(new_poly), str(polyMesh_dir))
        shutil.rmtree(prev, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)
    except OSError as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise SnappyContainerError(
            f"failed to swap polyMesh on host (filesystem fault): {exc}"
        ) from exc

    return SnappyRunResult(
        polyMesh_dir=polyMesh_dir,
        log_path=log_dest,
        # R0 P1 (Codex 86gs): layers_added is None when the log was
        # unparseable BUT the run succeeded (no definite_zero, swap
        # committed). Fall back to 0 in the schema — the engineer can
        # inspect log_path for ground truth. Coverage_fraction None
        # already conveys "summary unparsed".
        layers_added=layers_added if layers_added is not None else 0,
        coverage_fraction=coverage,
        generation_time_s=time.monotonic() - t0,
    )
