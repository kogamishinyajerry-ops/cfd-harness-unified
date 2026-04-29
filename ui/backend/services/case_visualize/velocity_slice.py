"""Render |U| on the z=0 midplane as a viridis-colormapped heatmap.

Pipeline:

1. Ensure cell-center field ``C`` exists in some time directory (the
   container's ``postProcess -func writeCellCentres`` writes ``0/C``
   the first time it runs). If it doesn't exist, run postProcess
   inside the cfd-openfoam container — same docker-SDK pattern as
   :mod:`solver_runner` + :mod:`to_foam`.
2. Read U from the FINAL time directory + C from wherever it landed.
3. Filter cells whose centroid z is within ±slab of the midplane.
4. Build a 2D regular grid in (x, y), find the nearest sampled cell
   for each grid point via SciPy KD-tree, look up |U|.
5. Apply the viridis colormap (hand-rolled polynomial) and encode PNG.

The ``slab_thickness`` defaults to 5% of the bbox z-extent — tight
enough that we're sampling the midplane, loose enough to catch a
reasonable number of cells from the gmsh tet mesh which is
non-uniform.
"""
from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ui.backend.services.meshing_gmsh.to_foam import (
    CONTAINER_NAME,
    CONTAINER_WORK_BASE,
    _extract_tarball,
    _make_tarball,
)


class VelocitySliceError(RuntimeError):
    """Raised when the U field, C field, or container interaction fails."""


_IMAGE_SIZE = (520, 540)
_GRID_RES = 200  # Sample on a 200×200 grid; nearest-neighbor against ~26k cells
_SLAB_FRACTION = 0.05  # ±5% of bbox extent around the midplane
# Colormap clamp: gmsh tet meshes of an LDC cube produce a corner-
# singularity overshoot near the lid edges with |U| > U_lid. Plotting
# the raw range [0, |U|_max] would saturate the colorbar at that
# overshoot and make the entire bulk vortex appear dark. Clip the
# upper bound to a "lid-speed normalized" value so the user sees the
# vortex pattern instead of the artifact.
_COLORMAP_CLAMP_PCTL = 95.0  # use 95th percentile, not max

_BG = (12, 14, 22)
_TEXT = (220, 225, 235)
_AXIS = (160, 165, 180)
_PADDING_LEFT = 60
_PADDING_RIGHT = 90
_PADDING_TOP = 56  # extra room for the title
_PADDING_BOTTOM = 30


# ---- viridis colormap (5-stop polynomial approximation) ----------------------
# Real viridis is a 256-entry LUT; this 5-stop linear interp matches it
# closely enough for a demo heatmap and avoids a 1KB constant table.
_VIRIDIS_STOPS = [
    (0.00, (68, 1, 84)),
    (0.25, (59, 82, 139)),
    (0.50, (33, 145, 140)),
    (0.75, (94, 201, 98)),
    (1.00, (253, 231, 37)),
]


def _viridis(t: float) -> tuple[int, int, int]:
    """Map t∈[0,1] to viridis RGB."""
    t = max(0.0, min(1.0, t))
    for i in range(1, len(_VIRIDIS_STOPS)):
        t0, c0 = _VIRIDIS_STOPS[i - 1]
        t1, c1 = _VIRIDIS_STOPS[i]
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))  # type: ignore[return-value]
    return _VIRIDIS_STOPS[-1][1]


def _parse_volVectorField(path: Path) -> np.ndarray:
    text = path.read_text()
    m = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\n\(\s*\n",
        text,
    )
    if not m:
        # Fallback: uniform field (rare for cell centers)
        m_uni = re.search(
            r"internalField\s+uniform\s+\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+"
            r"([-0-9.eE+]+)\)\s*;",
            text,
        )
        if m_uni:
            return np.array(
                [[float(m_uni.group(i)) for i in (1, 2, 3)]], dtype=np.float64
            )
        raise VelocitySliceError(
            f"can't parse volVectorField in {path}"
        )
    n = int(m.group(1))
    body_start = m.end()
    body_end = text.index("\n)", body_start)
    body = text[body_start:body_end]
    arr = np.empty((n, 3), dtype=np.float64)
    i = 0
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        mm = re.match(r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)", line)
        if mm and i < n:
            arr[i] = (
                float(mm.group(1)),
                float(mm.group(2)),
                float(mm.group(3)),
            )
            i += 1
    if i != n:
        raise VelocitySliceError(
            f"parsed {i} entries but declared {n} in {path}"
        )
    return arr


def _list_time_dirs(case_dir: Path) -> list[tuple[float, Path]]:
    out: list[tuple[float, Path]] = []
    for entry in case_dir.iterdir():
        if not entry.is_dir():
            continue
        if entry.name in ("constant", "system"):
            continue
        try:
            out.append((float(entry.name), entry))
        except ValueError:
            continue
    return sorted(out, key=lambda t: t[0])


def _ensure_cell_centres(case_host_dir: Path) -> Path:
    """Make sure a ``C`` (cell centres) field is on disk somewhere.
    Returns the path to the C file. Runs ``postProcess -func
    writeCellCentres`` in the cfd-openfoam container if needed.
    """
    times = _list_time_dirs(case_host_dir)
    # Look for an existing C file in any time directory (postProcess
    # writes it into the directory whose time matches `-time` — by
    # default the latest).
    for _, td in times:
        if (td / "C").is_file():
            return td / "C"

    # Run postProcess in the container.
    try:
        import docker  # type: ignore[import-not-found]
        import docker.errors  # type: ignore[import-not-found]
    except ImportError as exc:
        raise VelocitySliceError(
            "docker SDK is not installed — install with "
            "`pip install 'docker>=7.0'`."
        ) from exc

    try:
        client = docker.from_env()
        container = client.containers.get(CONTAINER_NAME)
        if container.status != "running":
            raise VelocitySliceError(
                f"container '{CONTAINER_NAME}' is not running."
            )
    except docker.errors.NotFound as exc:
        raise VelocitySliceError(
            f"container '{CONTAINER_NAME}' not found."
        ) from exc
    except docker.errors.DockerException as exc:
        raise VelocitySliceError(f"docker init failed: {exc}") from exc

    container_work_dir = f"{CONTAINER_WORK_BASE}/{case_host_dir.name}"

    # Stage case → container → run postProcess → pull C back
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
            raise VelocitySliceError(
                "failed to stage case for cell-centre extraction"
            )
    except docker.errors.DockerException as exc:
        raise VelocitySliceError(
            f"docker SDK error preparing container workspace: {exc}"
        ) from exc

    bash_cmd = (
        "source /opt/openfoam10/etc/bashrc && "
        f"cd {container_work_dir} && "
        "postProcess -func writeCellCentres -latestTime > log.postProcess 2>&1"
    )
    try:
        result = container.exec_run(cmd=["bash", "-c", bash_cmd])
    except docker.errors.DockerException as exc:
        raise VelocitySliceError(f"postProcess invocation failed: {exc}") from exc
    if result.exit_code != 0:
        raise VelocitySliceError(
            f"postProcess exited {result.exit_code}: "
            f"{result.output.decode(errors='replace')[:400]}"
        )

    # postProcess -latestTime writes C only into the latest time
    # directory's C file inside the container. ``container.get_archive``
    # of a single file returns a tarball where the file is the
    # top-level entry — extracting to ``dest`` puts it at ``dest/C``,
    # not ``dest/<time>/C``. Iterate from latest to earliest so we hit
    # the actual C-bearing dir first.
    import shutil as _shutil

    for _, td in reversed(times):
        try:
            bits, _ = container.get_archive(f"{container_work_dir}/{td.name}/C")
        except docker.errors.NotFound:
            continue
        except docker.errors.DockerException as exc:
            raise VelocitySliceError(
                f"docker SDK error pulling C from time {td.name}: {exc}"
            ) from exc
        tmp = td.parent / "_tmp_C_pull"
        try:
            _extract_tarball(b"".join(bits), tmp)
            stray = tmp / "C"
            if stray.is_file():
                stray.replace(td / "C")
                return td / "C"
        finally:
            if tmp.is_dir():
                _shutil.rmtree(tmp, ignore_errors=True)

    raise VelocitySliceError(
        "ran postProcess but no C field landed in any time directory."
    )


@dataclass(frozen=True, slots=True)
class _SliceData:
    grid_x: np.ndarray
    grid_y: np.ndarray
    u_mag_grid: np.ndarray  # shape (nx, ny)
    u_mag_min: float  # robust lower bound (5th pctl)
    u_mag_max: float  # robust upper bound (95th pctl)
    u_mag_raw_max: float  # actual max — for the overshoot disclosure
    final_time: float
    cells_in_slab: int


def _compute_slice(case_dir: Path) -> _SliceData:
    times = _list_time_dirs(case_dir)
    if not times:
        raise VelocitySliceError("no time directories under case dir")
    final_time, final_dir = max(times, key=lambda t: t[0])
    if final_time == 0.0:
        raise VelocitySliceError(
            "only initial condition (0/) exists — solver hasn't run."
        )

    u_path = final_dir / "U"
    if not u_path.is_file():
        raise VelocitySliceError(
            f"U field missing in {final_dir} — solver may have crashed."
        )

    c_path = _ensure_cell_centres(case_dir)
    U = _parse_volVectorField(u_path)
    C = _parse_volVectorField(c_path)
    if len(U) != len(C):
        raise VelocitySliceError(
            f"U has {len(U)} cells but C has {len(C)} — mesh changed?"
        )

    # Find slab: ±slab_thickness of the midplane.
    z_min, z_max = C[:, 2].min(), C[:, 2].max()
    z_mid = (z_min + z_max) / 2
    slab = (z_max - z_min) * _SLAB_FRACTION
    mask = np.abs(C[:, 2] - z_mid) < slab
    if mask.sum() < 4:
        # Slab too thin — widen to whatever captures at least 50 cells.
        slab = (z_max - z_min) * 0.5
        mask = np.abs(C[:, 2] - z_mid) < slab
    cells_in_slab = int(mask.sum())
    if cells_in_slab < 4:
        raise VelocitySliceError(
            f"only {cells_in_slab} cells found in z-slab — mesh too sparse "
            "for slice rendering."
        )

    xy = C[mask, :2]
    u_mag = np.linalg.norm(U[mask], axis=1)

    # Nearest-neighbor query via scipy KD-tree.
    from scipy.spatial import cKDTree

    tree = cKDTree(xy)
    x_min, y_min = C[:, 0].min(), C[:, 1].min()
    x_max, y_max = C[:, 0].max(), C[:, 1].max()
    grid_x = np.linspace(x_min, x_max, _GRID_RES)
    grid_y = np.linspace(y_min, y_max, _GRID_RES)
    GX, GY = np.meshgrid(grid_x, grid_y, indexing="ij")
    grid_pts = np.column_stack([GX.ravel(), GY.ravel()])
    _, nearest = tree.query(grid_pts, k=1)
    u_grid = u_mag[nearest].reshape(_GRID_RES, _GRID_RES)

    # Robust colormap range: clip to [5th, 95th] percentile of |U|
    # so the corner-singularity overshoot doesn't dominate the
    # colorbar. The actual max is reported separately so the user
    # can see the overshoot exists.
    u_mag_clip_lo = float(np.percentile(u_mag, 100 - _COLORMAP_CLAMP_PCTL))
    u_mag_clip_hi = float(np.percentile(u_mag, _COLORMAP_CLAMP_PCTL))
    u_mag_raw_max = float(u_mag.max())

    return _SliceData(
        grid_x=grid_x,
        grid_y=grid_y,
        u_mag_grid=u_grid,
        u_mag_min=u_mag_clip_lo,
        u_mag_max=u_mag_clip_hi,
        u_mag_raw_max=u_mag_raw_max,
        final_time=final_time,
        cells_in_slab=cells_in_slab,
    )


def render_velocity_slice_png(case_dir: Path) -> bytes:
    """Render the |U| heatmap on z=0 as a PNG. Raises VelocitySliceError on failure."""
    data = _compute_slice(case_dir)

    # Heatmap → image. Map the GRID_RES×GRID_RES array to the heatmap
    # area of the canvas (between paddings). Use Image.fromarray for
    # speed: build an RGB image at GRID_RES, then upscale.
    rgb = np.zeros((_GRID_RES, _GRID_RES, 3), dtype=np.uint8)
    u_max = max(data.u_mag_max, 1.0e-9)
    u_min = data.u_mag_min
    span = u_max - u_min if u_max > u_min else 1.0
    for i in range(_GRID_RES):
        for j in range(_GRID_RES):
            t = (data.u_mag_grid[i, j] - u_min) / span
            rgb[j, i] = _viridis(float(t))  # j first → image row = -y

    heatmap_img = Image.fromarray(rgb, mode="RGB")
    plot_w = _IMAGE_SIZE[0] - _PADDING_LEFT - _PADDING_RIGHT
    plot_h = _IMAGE_SIZE[1] - _PADDING_TOP - _PADDING_BOTTOM
    heatmap_img = heatmap_img.resize((plot_w, plot_h), Image.NEAREST)

    canvas = Image.new("RGB", _IMAGE_SIZE, _BG)
    canvas.paste(heatmap_img, (_PADDING_LEFT, _PADDING_TOP))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None

    # Axis frame
    draw.rectangle(
        (
            _PADDING_LEFT - 1,
            _PADDING_TOP - 1,
            _PADDING_LEFT + plot_w,
            _PADDING_TOP + plot_h,
        ),
        outline=_AXIS,
        width=1,
    )

    # X / Y axis labels: 5 ticks each
    for i in range(5):
        f = i / 4
        x_val = data.grid_x[0] + f * (data.grid_x[-1] - data.grid_x[0])
        px = _PADDING_LEFT + f * plot_w
        draw.text(
            (px - 12, _PADDING_TOP + plot_h + 4),
            f"{x_val:.3f}",
            fill=_TEXT,
            font=font,
        )
        y_val = data.grid_y[0] + f * (data.grid_y[-1] - data.grid_y[0])
        py = _PADDING_TOP + (1 - f) * plot_h
        draw.text(
            (8, py - 6),
            f"{y_val:.3f}",
            fill=_TEXT,
            font=font,
        )

    draw.text((_IMAGE_SIZE[0] // 2 - 30, 4), "x [m]", fill=_TEXT, font=font)
    draw.text((4, _IMAGE_SIZE[1] // 2 - 6), "y", fill=_TEXT, font=font)

    # Colorbar
    cb_x0 = _IMAGE_SIZE[0] - _PADDING_RIGHT + 18
    cb_y0 = _PADDING_TOP
    cb_w = 14
    cb_h = plot_h
    for j in range(cb_h):
        t = 1 - j / max(cb_h - 1, 1)
        color = _viridis(t)
        draw.line([(cb_x0, cb_y0 + j), (cb_x0 + cb_w, cb_y0 + j)], fill=color)
    draw.rectangle(
        (cb_x0, cb_y0, cb_x0 + cb_w, cb_y0 + cb_h),
        outline=_AXIS,
        width=1,
    )
    # Colorbar ticks: max at top, mid, min at bottom
    for f, label in [(0.0, f"{u_max:.3f}"), (0.5, f"{(u_min + u_max) / 2:.3f}"), (1.0, f"{u_min:.3f}")]:
        py = cb_y0 + f * cb_h
        draw.line(
            [(cb_x0 + cb_w, py), (cb_x0 + cb_w + 4, py)],
            fill=_AXIS,
        )
        draw.text((cb_x0 + cb_w + 6, py - 6), label, fill=_TEXT, font=font)
    draw.text(
        (cb_x0 - 4, _PADDING_TOP - 16),
        "|U| [m/s]",
        fill=_TEXT,
        font=font,
    )

    # Title — concise ASCII-only lines that fit in 370px of plot
    # width with PIL's default font.
    draw.text(
        (_PADDING_LEFT, 6),
        f"|U| at z=0  ·  t={data.final_time}s  ·  {data.cells_in_slab} cells",
        fill=_TEXT,
        font=font,
    )
    if data.u_mag_raw_max > data.u_mag_max * 1.05:
        draw.text(
            (_PADDING_LEFT, 22),
            f"clipped at 95% ({data.u_mag_max:.3f}); raw max "
            f"{data.u_mag_raw_max:.3f} = corner overshoot",
            fill=(220, 180, 100),
            font=font,
        )
    else:
        draw.text(
            (_PADDING_LEFT, 22),
            f"range {data.u_mag_min:.3f} to {data.u_mag_max:.3f} m/s",
            fill=(180, 185, 200),
            font=font,
        )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
