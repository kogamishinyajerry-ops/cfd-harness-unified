"""Multi-panel research-grade post-processing for Step 5 (2026-04-30).

The original Phase-1A `velocity_slice.py` rendered a single hand-rolled
PIL heatmap of |U| on the z-midplane. User feedback: that's far below
the multi-contour, multi-data reports the line-B pipeline produces.

This module renders four matplotlib figures from the same case_dir:

* ``contour-streamlines.png`` — |U| filled tricontour + streamplot
* ``pressure.png``            — p filled tricontour (gauge pressure)
* ``vorticity.png``           — ω_z = ∂Uy/∂x − ∂Ux/∂y filled contour
* ``centerline.png``          — U_x(y)|x=mid + U_y(x)|y=mid line plots

All four are computed from the FINAL time directory's U + p volume
fields plus the cell-centre field C (postProcess writes C the same way
velocity_slice.py already does — that helper is reused here).

Plane selection auto-picks the two non-degenerate axes (LDC = xy,
NACA = xz, etc.). Pseudo-2D meshes one cell thick in z behave like
LDC; truly 3D meshes fall back to a thin slab around the midplane of
the smallest-extent axis (same heuristic as velocity_slice.py).

Caching: each figure is written to
``<case_dir>/reports/<final_time>/{name}.png``. Reads short-circuit when
the cached file's mtime is newer than the corresponding U field. The
final_time directory name is part of the cache key so a re-solve
invalidates automatically.
"""
from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ui.backend.services.case_visualize.velocity_slice import (
    VelocitySliceError,
    _ensure_cell_centres,
    _list_time_dirs,
    _parse_volVectorField,
)


class ReportBundleError(RuntimeError):
    """Raised when field parsing or matplotlib rendering fails."""


# Codex round-5 P2 (2026-04-30): matplotlib is in the [workbench] extra
# but the documented backend install is `.[ui,dev]`. Importing
# matplotlib at module load made the case_visualize PACKAGE
# unimportable in stock UI installs — including the three legacy
# Pillow-only routes (bc-overlay, residual-history, velocity-slice)
# that have nothing to do with matplotlib.
#
# Defer the import to first-call instead. The package now imports
# cleanly without matplotlib; only build_report_bundle / the four
# renderers fail (with a clear actionable error) when matplotlib is
# missing. Legacy routes keep working unchanged.
_MPL_LOADED = False


def _ensure_matplotlib() -> None:
    """Import matplotlib + matplotlib.tri on first call. Raises
    ReportBundleError with install hint when matplotlib isn't
    available so the route can map it to a clean 503 response.
    """
    global _MPL_LOADED, plt, mtri  # noqa: PLW0603 — deliberate module-level cache
    if _MPL_LOADED:
        return
    try:
        import matplotlib  # type: ignore[import-not-found]

        # Headless Agg backend BEFORE pyplot import — we run inside
        # the FastAPI worker which has no display. Mirrors
        # render_case_report.py.
        matplotlib.use("Agg")
        import matplotlib.pyplot as _plt  # type: ignore[import-not-found]
        import matplotlib.tri as _mtri  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ReportBundleError(
            "matplotlib is required for the Step 5 report bundle but is "
            "not installed. Install the workbench extras: "
            "`.venv/bin/pip install -e '.[workbench]'` and restart the "
            "backend."
        ) from exc
    plt = _plt
    mtri = _mtri
    _MPL_LOADED = True
    # Dark-theme rcParams set once on first import.
    _apply_rcparams()


# Module-scope handles populated by _ensure_matplotlib(). Typed as Any
# so the renderers can use plt./mtri. without static-import errors;
# at runtime they're only touched after _ensure_matplotlib() succeeds.
plt = None  # type: ignore[assignment]
mtri = None  # type: ignore[assignment]


_DPI = 120
_CMAP_VEL = "viridis"
_CMAP_PRESSURE = "RdBu_r"
_CMAP_VORTICITY = "RdBu_r"
_CONTOUR_LEVELS = 22
_GRID_RES = 220  # for streamplot regrid + vorticity finite-diff
# Per-renderer percentile clips. The LDC corner singularity emits |U|,
# |p|, and |ω| values 5–50× the bulk value, so a uniform 99-pctl clip
# (which used to be a single _PCTL_CLIP constant) saturated the
# colormap on the outlier and made the bulk vortex render in the
# colormap's near-white band. Tightening per-field gets bulk
# variation back into the colored portion of the LUT. Velocity has the
# narrowest dynamic range so it stays at 99; pressure and vorticity
# move down to 90.
_PCTL_CLIP_VELOCITY = 99.0
_PCTL_CLIP_PRESSURE = 90.0
_PCTL_CLIP_VORTICITY = 90.0

# Canonical artifact filenames. Routes pull these names directly so the
# file layout is the contract.
ARTIFACT_NAMES = (
    "contour_streamlines",
    "pressure",
    "vorticity",
    "centerline",
)

def _apply_rcparams() -> None:
    """Dark-theme matplotlib styling so the panels match the workbench
    UI (slate background, light text). Called once from
    _ensure_matplotlib() on first matplotlib load.
    """
    plt.rcParams.update(
        {
            "figure.facecolor": "#0b0d12",
            "axes.facecolor": "#0e1117",
            "axes.edgecolor": "#3a3f4a",
            "axes.labelcolor": "#cbd5e1",
            "axes.titlecolor": "#e2e8f0",
            "xtick.color": "#94a3b8",
            "ytick.color": "#94a3b8",
            "grid.color": "#1f242f",
            "savefig.facecolor": "#0b0d12",
            "savefig.edgecolor": "#0b0d12",
            "font.size": 10,
        }
    )


@dataclass(frozen=True, slots=True)
class _SliceFields:
    """All field samples on the chosen 2D plane. ``mask`` selects the
    midplane slab from the global cell list; ``axes`` reports which
    Cartesian axes were picked (e.g. ``("x", "y")``)."""

    Cx: np.ndarray  # (n_slab,) coords on axis-1
    Cy: np.ndarray  # (n_slab,) coords on axis-2
    Ux: np.ndarray  # (n_slab,) velocity along axis-1
    Uy: np.ndarray  # (n_slab,) velocity along axis-2
    p: np.ndarray | None  # (n_slab,) gauge pressure, or None if missing
    final_time: float
    axes: tuple[str, str]


def _parse_volScalarField(path: Path) -> np.ndarray:
    """Parse a `volScalarField` (e.g. p) into a (n,) float array.

    Mirrors :func:`_parse_volVectorField` but for scalar values. Falls
    back to a uniform value when the field is uniform (rare for p in a
    converged case but legal in OpenFOAM dicts).
    """
    text = path.read_text()
    m = re.search(
        r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\n\(\s*\n",
        text,
    )
    if not m:
        m_uni = re.search(
            r"internalField\s+uniform\s+([-0-9.eE+]+)\s*;",
            text,
        )
        if m_uni:
            return np.array([float(m_uni.group(1))], dtype=np.float64)
        raise ReportBundleError(f"can't parse volScalarField in {path}")
    n = int(m.group(1))
    body_start = m.end()
    body_end = text.index("\n)", body_start)
    body = text[body_start:body_end]
    arr = np.empty(n, dtype=np.float64)
    i = 0
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            arr[i] = float(line)
            i += 1
        except ValueError:
            continue
    if i != n:
        raise ReportBundleError(
            f"parsed {i} entries but declared {n} in {path}"
        )
    return arr


def _pick_plane(C: np.ndarray) -> tuple[int, int, int, str, str]:
    """Pick the two non-degenerate Cartesian axes for the 2D rendering.

    Returns indices ``(i, j, k)`` where ``i, j`` are the two axes with
    largest extent (the rendering plane) and ``k`` is the slab axis.
    Also returns label strings for the picked axes.
    """
    spans = [
        (float(C[:, a].max() - C[:, a].min()), a)
        for a in range(3)
    ]
    spans.sort(key=lambda t: t[0], reverse=True)
    i, j = spans[0][1], spans[1][1]
    k = spans[2][1]
    label = ("x", "y", "z")
    return i, j, k, label[i], label[j]


def _select_slab(
    C: np.ndarray, U: np.ndarray, p: np.ndarray | None
) -> _SliceFields:
    """Restrict the cell list to a thin slab around the midplane on the
    smallest-extent axis. For pseudo-2D meshes (one cell thick in z)
    the slab catches all cells. For truly 3D meshes (rare in M-AI-COPILOT
    scope) it samples ~5% of the bbox extent on the slab axis.
    """
    i, j, k, lab_i, lab_j = _pick_plane(C)
    z_min = float(C[:, k].min())
    z_max = float(C[:, k].max())
    z_mid = 0.5 * (z_min + z_max)
    extent = z_max - z_min
    slab = max(extent * 0.05, 1e-9)
    mask = np.abs(C[:, k] - z_mid) <= slab
    if mask.sum() < 16:
        # Widen until we have at least 16 cells (so triangulation has
        # something to work with).
        slab = extent * 0.5 + 1e-9
        mask = np.abs(C[:, k] - z_mid) <= slab
    if mask.sum() < 4:
        raise ReportBundleError(
            "midplane slab found < 4 cells — mesh is degenerate."
        )
    Cx_raw = C[mask, i]
    Cy_raw = C[mask, j]
    Ux_raw = U[mask, i]
    Uy_raw = U[mask, j]
    p_raw = p[mask] if p is not None else None

    # Codex round-6 P2 (2026-04-30): for genuinely 3D meshes the slab
    # may catch multiple cells per (Cx, Cy) projected location with
    # different field values (different depth samples). matplotlib.tri
    # fails on exactly-coincident (x, y) points and would otherwise
    # pick one sample arbitrarily based on cell ordering — making the
    # contour, streamline, and vorticity panels non-physical. Bin
    # cells onto a regular (Cx, Cy) grid keyed by the slab-axis bbox
    # (~_GRID_RES bins per axis) and AVERAGE the field values that
    # land in each bin. Pseudo-2D one-cell-thick meshes already have
    # one sample per (Cx, Cy) so binning is a no-op for those.
    Cx_grid, Cy_grid, Ux_grid, Uy_grid, p_grid = _project_slab(
        Cx_raw,
        Cy_raw,
        Ux_raw,
        Uy_raw,
        p_raw,
    )
    return _SliceFields(
        Cx=Cx_grid,
        Cy=Cy_grid,
        Ux=Ux_grid,
        Uy=Uy_grid,
        p=p_grid,
        final_time=0.0,  # caller fills in
        axes=(lab_i, lab_j),
    )


def _project_slab(
    Cx: np.ndarray,
    Cy: np.ndarray,
    Ux: np.ndarray,
    Uy: np.ndarray,
    p: np.ndarray | None,
    n_bins: int = 0,  # legacy arg kept for signature stability; unused
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray | None]:
    """Collapse cells with EXACTLY-coincident (Cx, Cy) by averaging
    their field values. Preserves every distinct projection unchanged.

    Codex round 6 P2 asked for dedup so matplotlib.tri.Triangulation
    didn't choke on duplicate (x, y) for genuinely 3D meshes. Codex
    round 7 P2 noted that the round-6 implementation (fixed
    110×110 binning) blurred fine pseudo-2D meshes by merging
    unrelated samples that happened to land in the same coarse bin.

    This implementation collapses ONLY exact-equal (Cx, Cy) pairs:

    * Use np.unique with axis=0 to find unique (Cx, Cy) rows; cells
      that map to the same row get averaged via np.bincount.
    * For pseudo-2D meshes (every cell has a unique centroid) the
      output is identical to the input — fast path returns originals.
    * For genuinely 3D meshes (the rare case where two distinct cells
      have IDENTICAL float (x, y) centroids — possible after a
      structured-mesh extrusion), averaging is the right reduction.

    np.unique on float64 needs the values to be bit-equal — which is
    what we want here. Anything that round-trips through OpenFOAM's
    cell-centres parser stays bit-stable, so true projection
    duplicates from a structured mesh hit the average branch and
    everything else passes through.
    """
    del n_bins  # legacy
    n = len(Cx)
    if n == 0:
        return Cx, Cy, Ux, Uy, p
    coords = np.column_stack([Cx, Cy])
    unique_coords, inverse = np.unique(coords, axis=0, return_inverse=True)
    if len(unique_coords) == n:
        # No exact duplicates — every cell already has a distinct
        # (Cx, Cy). This is the common path on every gmsh-meshed
        # case we run today; matplotlib.tri can triangulate the
        # original (Cx, Cy) cloud directly without losing fidelity.
        return Cx, Cy, Ux, Uy, p

    counts = np.bincount(inverse, minlength=len(unique_coords)).astype(np.float64)

    def _avg(values: np.ndarray) -> np.ndarray:
        sums = np.bincount(
            inverse, weights=values, minlength=len(unique_coords)
        )
        return sums / counts

    Cx_out = unique_coords[:, 0]
    Cy_out = unique_coords[:, 1]
    Ux_out = _avg(Ux)
    Uy_out = _avg(Uy)
    p_out = _avg(p) if p is not None else None
    return Cx_out, Cy_out, Ux_out, Uy_out, p_out


def _bbox(Cx: np.ndarray, Cy: np.ndarray) -> tuple[float, float, float, float]:
    return float(Cx.min()), float(Cx.max()), float(Cy.min()), float(Cy.max())


def _regrid(
    Cx: np.ndarray, Cy: np.ndarray, values: np.ndarray, n: int = _GRID_RES
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Resample scattered (Cx, Cy, values) onto a regular n×n grid via
    matplotlib.tri's LinearTriInterpolator. Returns (xs, ys, grid)
    where grid is shape (n, n). NaN where extrapolation would happen.
    """
    xmin, xmax, ymin, ymax = _bbox(Cx, Cy)
    xs = np.linspace(xmin, xmax, n)
    ys = np.linspace(ymin, ymax, n)
    XX, YY = np.meshgrid(xs, ys)
    triang = mtri.Triangulation(Cx, Cy)
    interp = mtri.LinearTriInterpolator(triang, values)
    grid = interp(XX, YY)
    # Convert masked entries to NaN so streamplot stops at the boundary.
    grid_arr = np.array(grid.filled(np.nan), dtype=np.float64)
    return xs, ys, grid_arr


def _aspect_figsize(Cx: np.ndarray, Cy: np.ndarray) -> tuple[float, float]:
    """Pick figsize so elongated domains (channel L/H=10) don't get
    crammed into a square canvas. Mirrors render_case_report's logic.
    """
    xmin, xmax, ymin, ymax = _bbox(Cx, Cy)
    dx = xmax - xmin
    dy = ymax - ymin
    aspect = (dx / dy) if dy > 0 else 1.0
    if aspect >= 2.5:
        h = 4.4
        w = float(min(max(h * aspect * 0.9, 8.0), 14.0))
    elif aspect <= 0.4:
        w = 5.0
        h = float(min(max(w / aspect * 0.9, 6.0), 12.0))
    else:
        w, h = 7.5, 5.8
    return w, h


def _save(fig, path: Path) -> None:  # type: ignore[no-untyped-def]
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=_DPI)
    plt.close(fig)


def _render_contour_streamlines(slab: _SliceFields, out: Path) -> None:
    """|U| filled contour with white streamlines overlaid. Streamlines
    require a regular grid — regrid via Linear triangle interp.
    """
    Cx, Cy, Ux, Uy = slab.Cx, slab.Cy, slab.Ux, slab.Uy
    finite = np.isfinite(Ux) & np.isfinite(Uy)
    Ux = np.where(finite, Ux, 0.0)
    Uy = np.where(finite, Uy, 0.0)
    mag = np.sqrt(Ux * Ux + Uy * Uy)
    vmax = float(np.nanpercentile(mag, _PCTL_CLIP_VELOCITY))
    if not math.isfinite(vmax) or vmax <= 0:
        vmax = 1.0
    fig, ax = plt.subplots(figsize=_aspect_figsize(Cx, Cy))
    triang = mtri.Triangulation(Cx, Cy)
    levels = np.linspace(0.0, vmax, _CONTOUR_LEVELS)
    cf = ax.tricontourf(triang, np.clip(mag, 0, vmax), levels=levels, cmap=_CMAP_VEL)
    # Streamplot needs a regular grid.
    xs, ys, Ux_g = _regrid(Cx, Cy, Ux)
    _, _, Uy_g = _regrid(Cx, Cy, Uy)
    try:
        ax.streamplot(
            xs,
            ys,
            Ux_g,
            Uy_g,
            density=1.4,
            color="white",
            linewidth=0.6,
            arrowsize=0.9,
        )
    except (ValueError, RuntimeError):
        # Streamplot can fail on very small / degenerate domains.
        # The contour alone is still informative — degrade gracefully.
        pass
    ax.set_aspect("equal")
    ax.set_xlabel(f"{slab.axes[0]} [m]")
    ax.set_ylabel(f"{slab.axes[1]} [m]")
    ax.set_title(
        f"|U| contour + streamlines · t = {slab.final_time:g}s",
        pad=8,
    )
    cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("|U| [m/s]")
    _save(fig, out)


def _render_pressure(slab: _SliceFields, out: Path) -> None:
    """Gauge pressure (p / ρ for incompressible icoFoam) filled contour.
    Diverging colormap centred on zero so positive/negative regions are
    immediately readable.
    """
    if slab.p is None:
        # Render a placeholder card — solver may not have written p
        # (pure-Neumann case, etc.). Caller decides whether to expose.
        fig, ax = plt.subplots(figsize=(6, 4.5))
        ax.text(
            0.5,
            0.5,
            "pressure field not available\n(p missing in final time dir)",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color="#94a3b8",
            fontsize=11,
        )
        ax.set_axis_off()
        _save(fig, out)
        return
    Cx, Cy, p = slab.Cx, slab.Cy, slab.p
    finite = np.isfinite(p)
    p = np.where(finite, p, 0.0)
    pmax = float(np.nanpercentile(np.abs(p[finite]) if finite.any() else p, _PCTL_CLIP_PRESSURE))
    if not math.isfinite(pmax) or pmax <= 0:
        pmax = 1.0
    fig, ax = plt.subplots(figsize=_aspect_figsize(Cx, Cy))
    triang = mtri.Triangulation(Cx, Cy)
    levels = np.linspace(-pmax, pmax, _CONTOUR_LEVELS)
    cf = ax.tricontourf(
        triang,
        np.clip(p, -pmax, pmax),
        levels=levels,
        cmap=_CMAP_PRESSURE,
    )
    ax.set_aspect("equal")
    ax.set_xlabel(f"{slab.axes[0]} [m]")
    ax.set_ylabel(f"{slab.axes[1]} [m]")
    ax.set_title(
        f"gauge pressure (p/ρ) · t = {slab.final_time:g}s",
        pad=8,
    )
    cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("p/ρ [m²/s²]")
    _save(fig, out)


def _render_vorticity(slab: _SliceFields, out: Path) -> None:
    """Spanwise vorticity ω_k = ∂Uy/∂x − ∂Ux/∂y, computed via finite-
    differences on the regridded velocity field.
    """
    Cx, Cy, Ux, Uy = slab.Cx, slab.Cy, slab.Ux, slab.Uy
    xs, ys, Ux_g = _regrid(Cx, Cy, Ux)
    _, _, Uy_g = _regrid(Cx, Cy, Uy)
    # np.gradient: order is (axis-0=rows=y, axis-1=cols=x).
    dUy_dx = np.gradient(Uy_g, xs, axis=1)
    dUx_dy = np.gradient(Ux_g, ys, axis=0)
    omega = dUy_dx - dUx_dy
    finite = np.isfinite(omega)
    if not finite.any():
        omega_clipped = np.zeros_like(omega)
        wmax = 1.0
    else:
        wmax = float(np.nanpercentile(np.abs(omega[finite]), _PCTL_CLIP_VORTICITY))
        if not math.isfinite(wmax) or wmax <= 0:
            wmax = 1.0
        omega_clipped = np.where(finite, np.clip(omega, -wmax, wmax), 0.0)
    fig, ax = plt.subplots(figsize=_aspect_figsize(Cx, Cy))
    levels = np.linspace(-wmax, wmax, _CONTOUR_LEVELS)
    cf = ax.contourf(
        xs,
        ys,
        omega_clipped,
        levels=levels,
        cmap=_CMAP_VORTICITY,
    )
    ax.set_aspect("equal")
    ax.set_xlabel(f"{slab.axes[0]} [m]")
    ax.set_ylabel(f"{slab.axes[1]} [m]")
    ax.set_title(
        f"vorticity ω_{slab.axes[0]}{slab.axes[1]} · t = {slab.final_time:g}s",
        pad=8,
    )
    cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("ω [1/s]")
    _save(fig, out)


def _render_centerline(slab: _SliceFields, out: Path) -> None:
    """Two-panel centreline profiles:

    * Left: U_x(axis-2) at axis-1 = mid (LDC's vertical centreline)
    * Right: U_y(axis-1) at axis-2 = mid (LDC's horizontal centreline)

    Sampled from the regridded velocity (Linear triangle interp), 200
    points each. Rejection-prone if the slab has fewer than ~50 cells —
    falls back to NaN-filled axes with a "insufficient data" annotation.
    """
    Cx, Cy = slab.Cx, slab.Cy
    if len(Cx) < 50:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for ax in axes:
            ax.text(
                0.5,
                0.5,
                "insufficient slab cells for centreline interpolation",
                transform=ax.transAxes,
                ha="center",
                va="center",
                color="#94a3b8",
                fontsize=10,
            )
            ax.set_axis_off()
        _save(fig, out)
        return
    xs, ys, Ux_g = _regrid(Cx, Cy, slab.Ux)
    _, _, Uy_g = _regrid(Cx, Cy, slab.Uy)
    mid_x_idx = len(xs) // 2
    mid_y_idx = len(ys) // 2
    Ux_centreline = Ux_g[:, mid_x_idx]
    Uy_centreline = Uy_g[mid_y_idx, :]
    # Codex round-4 P3 (2026-04-30): the velocity components on the
    # picked plane are slab.Ux/slab.Uy, but those are PLANE-LOCAL
    # variables — the actual physical components depend on which two
    # axes _pick_plane chose. For an xz slab Uy slot is U_z; for yz
    # it's U_z too. Render labels with the actual axis letter so the
    # plot title doesn't lie about the observable.
    a0, a1 = slab.axes  # e.g. ("x", "y") for LDC, ("x", "z") for NACA
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    ax_l, ax_r = axes
    ax_l.plot(Ux_centreline, ys, color="#60a5fa", linewidth=1.6)
    ax_l.axvline(0, color="#475569", linewidth=0.6, linestyle=":")
    ax_l.set_xlabel(f"U_{a0} [m/s]")
    ax_l.set_ylabel(f"{a1} [m]")
    ax_l.set_title(f"U_{a0} along {a0} = mid", pad=8)
    ax_l.grid(True, alpha=0.25)
    ax_r.plot(xs, Uy_centreline, color="#fbbf24", linewidth=1.6)
    ax_r.axhline(0, color="#475569", linewidth=0.6, linestyle=":")
    ax_r.set_xlabel(f"{a0} [m]")
    ax_r.set_ylabel(f"U_{a1} [m/s]")
    ax_r.set_title(f"U_{a1} along {a1} = mid", pad=8)
    ax_r.grid(True, alpha=0.25)
    fig.suptitle(
        f"centreline velocity profiles · t = {slab.final_time:g}s",
        y=1.02,
    )
    _save(fig, out)


@dataclass(frozen=True, slots=True)
class ReportBundle:
    """Bundle metadata returned by /report-bundle. Field URLs are
    relative paths the frontend prefixes with the case-id base.

    ``cache_version`` is a stable token that changes whenever the
    rendered figures should be considered stale — combines final_time
    with the U field's mtime so an in-place re-solve into the same
    time directory still bumps the version. The route uses this as
    ``?v=<cache_version>`` on artifact URLs so the browser refetches
    after a re-solve (Codex round-2 P1, 2026-04-30).

    ``case_kind`` classifies the case based on the polyMesh boundary
    patch names so the frontend can gate semantics that only make
    sense for one geometry (e.g. the LDC recirculation banner is
    nonsensical on a through-flow channel — Codex round-4 P2).
    Values: "lid_driven_cavity", "channel", or "unknown".
    """

    final_time: float
    cell_count: int
    slab_cell_count: int
    plane_axes: tuple[str, str]
    artifacts: dict[str, str]  # logical name → relative URL fragment
    summary_text: str
    cache_version: str
    case_kind: str


def _slab_cache_dir(case_dir: Path, final_time: float) -> Path:
    """Per-final-time cache directory. Final-time is part of the path
    so a re-solve invalidates automatically (the directory name carries
    the version key). 6 decimal digits is enough to disambiguate the
    icoFoam time grids we use (deltaT ≥ 1e-3).
    """
    key = f"{final_time:.6f}".replace(".", "_")
    return case_dir / "reports" / key


def _classify_case_kind(case_dir: Path) -> str:
    """Inspect the polyMesh boundary file to classify the case kind.
    Returns "lid_driven_cavity" if a `lid` patch is present (the BC
    setup that the LDC executor writes), "channel" when both `inlet`
    and `outlet` are present, "unknown" otherwise. Pre-setup-bc the
    boundary only has gmsh-default patches → "unknown".
    Codex round-4 P2 (2026-04-30) added so the frontend can gate
    LDC-only semantics like the recirculation warning.
    """
    boundary = case_dir / "constant" / "polyMesh" / "boundary"
    if not boundary.is_file():
        return "unknown"
    try:
        text = boundary.read_text()
    except OSError:
        return "unknown"
    # Patch names appear as identifier-line followed by `{`. A simple
    # regex catches them; we don't need the full polyMesh parser here.
    names = set(re.findall(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*\n\s*\{", text, re.M))
    if "lid" in names:
        return "lid_driven_cavity"
    if "inlet" in names and "outlet" in names:
        return "channel"
    return "unknown"


def _stale(cached: Path, source: Path) -> bool:
    """Cached PNG is stale if it doesn't exist or the source U/p file
    is newer (defence against an in-place re-solve into the same time
    directory — uncommon but possible).
    """
    if not cached.is_file():
        return True
    try:
        return cached.stat().st_mtime < source.stat().st_mtime
    except OSError:
        return True


def build_report_bundle(case_dir: Path) -> ReportBundle:
    """Render (or read from cache) all four report figures.

    Returns a ReportBundle whose ``artifacts`` map points the frontend
    at the four PNG URLs. Caching is keyed on ``final_time`` and on
    each source field's mtime so a re-solve auto-invalidates.
    """
    # Codex round-5 P2: matplotlib import is deferred to first call
    # so the case_visualize package keeps importing on stock `.[ui]`
    # installs that haven't pulled in the [workbench] extras.
    _ensure_matplotlib()
    times = _list_time_dirs(case_dir)
    if not times:
        raise ReportBundleError("no time directories under case dir")
    final_time, final_dir = max(times, key=lambda t: t[0])
    if final_time == 0.0:
        raise ReportBundleError(
            "only initial condition (0/) exists — solver hasn't run."
        )

    u_path = final_dir / "U"
    if not u_path.is_file():
        raise ReportBundleError(
            f"U field missing in {final_dir} — solver may have crashed."
        )
    # Codex round-5 P1 (2026-04-30): _ensure_cell_centres returns the
    # first cached C file it finds in any time directory. After a
    # remesh + re-solve the cached C from a previous mesh has the OLD
    # cell count and the length check below would fail PERMANENTLY
    # ("U has 26332 cells but C has 8000 — mesh changed?"). Detect the
    # mismatch and recover by deleting the stale C files + retrying
    # _ensure_cell_centres which will re-run postProcess for the
    # current mesh.
    try:
        c_path = _ensure_cell_centres(case_dir)
    except VelocitySliceError as exc:
        raise ReportBundleError(str(exc)) from exc

    U = _parse_volVectorField(u_path)
    C = _parse_volVectorField(c_path)
    if len(U) != len(C):
        # Stale C from a prior mesh. Surgical recovery: delete only
        # the specific C file we just loaded and retry. If another
        # time directory has a C with the right cell count,
        # _ensure_cell_centres returns it on the next call. If no
        # valid C exists anywhere, it falls through to postProcess.
        # Loop because there may be multiple stale Cs (one per old
        # time dir from a prior mesh) — bounded by `len(times)`.
        max_attempts = len(times)
        for _ in range(max_attempts):
            try:
                c_path.unlink()
            except OSError:
                break
            try:
                c_path = _ensure_cell_centres(case_dir)
            except VelocitySliceError as exc:
                raise ReportBundleError(
                    f"stale C field detected (U has {len(U)} cells, C had "
                    f"{len(C)}); failed to regenerate: {exc}"
                ) from exc
            C = _parse_volVectorField(c_path)
            if len(U) == len(C):
                break
        if len(U) != len(C):
            raise ReportBundleError(
                f"U has {len(U)} cells but regenerated C has {len(C)}; "
                "mesh / solver state is inconsistent."
            )
    p_path = final_dir / "p"
    if p_path.is_file():
        p = _parse_volScalarField(p_path)
        # Codex round-2 P2 (2026-04-30): _parse_volScalarField returns a
        # length-1 array for `internalField uniform <val>` (a legal
        # OpenFOAM dict layout). The previous "len(p) != len(U) → drop"
        # branch hid these valid uniform-pressure fields behind the
        # placeholder card. Broadcast the uniform value to all cells
        # so the panel renders a flat-coloured contour (which is the
        # physically correct depiction).
        if len(p) == 1 and len(U) > 1:
            p = np.full(len(U), float(p[0]), dtype=np.float64)
        elif len(p) != len(U):
            # True size mismatch — likely a corrupt field. Better to
            # render 3/4 panels than 0/4.
            p = None
    else:
        p = None

    slab = _select_slab(C, U, p)
    # Inject final_time (frozen dataclass — replace via __dict__ would
    # need object.__setattr__; cleaner to wrap in a builder).
    slab = _SliceFields(
        Cx=slab.Cx,
        Cy=slab.Cy,
        Ux=slab.Ux,
        Uy=slab.Uy,
        p=slab.p,
        final_time=final_time,
        axes=slab.axes,
    )

    cache_dir = _slab_cache_dir(case_dir, final_time)

    renderers = (
        ("contour_streamlines", _render_contour_streamlines, u_path),
        ("vorticity", _render_vorticity, u_path),
        ("centerline", _render_centerline, u_path),
        ("pressure", _render_pressure, p_path if p_path.is_file() else u_path),
    )

    for name, fn, src in renderers:
        target = cache_dir / f"{name}.png"
        if _stale(target, src):
            fn(slab, target)

    artifacts = {
        name: f"reports/{cache_dir.name}/{name}.png"
        for name, _, _ in renderers
    }

    Umag = np.sqrt(slab.Ux * slab.Ux + slab.Uy * slab.Uy)
    Umag_finite = Umag[np.isfinite(Umag)]
    if Umag_finite.size > 0:
        u_mean = float(Umag_finite.mean())
        u_max = float(Umag_finite.max())
    else:
        u_mean = u_max = 0.0
    summary = (
        f"final time t = {final_time:g} s · {len(U):,} cells total · "
        f"{len(slab.Cx):,} on {''.join(slab.axes)}-midplane slab · "
        f"|U| mean = {u_mean:.3g}, max = {u_max:.3g} m/s"
    )

    # cache_version: combines final_time (changes on a re-solve into
    # a new time dir) with the U field's mtime (changes on an
    # in-place re-solve into the same time dir). Codex round-2 P1
    # (2026-04-30) showed final_time alone wasn't enough: icoFoam can
    # overwrite an existing time directory and the URL version
    # wouldn't move. Using the U mtime as part of the token closes
    # that gap. Falls back to "0" if mtime read fails (e.g. case dir
    # got removed mid-call) so the response is still well-formed.
    try:
        u_mtime_ns = u_path.stat().st_mtime_ns
    except OSError:
        u_mtime_ns = 0
    cache_version = f"{final_time:.6f}".replace(".", "_") + f"_{u_mtime_ns}"

    return ReportBundle(
        final_time=final_time,
        cell_count=len(U),
        slab_cell_count=int(len(slab.Cx)),
        plane_axes=slab.axes,
        artifacts=artifacts,
        summary_text=summary,
        cache_version=cache_version,
        case_kind=_classify_case_kind(case_dir),
    )


def read_report_artifact(case_dir: Path, name: str) -> bytes:
    """Read a cached artifact PNG by logical name. Calls
    :func:`build_report_bundle` first to ensure freshness, then returns
    the rendered bytes.
    """
    if name not in ARTIFACT_NAMES:
        raise ReportBundleError(f"unknown artifact: {name!r}")
    bundle = build_report_bundle(case_dir)
    rel = bundle.artifacts.get(name)
    if rel is None:
        raise ReportBundleError(f"artifact {name!r} missing from bundle")
    p = case_dir / rel
    if not p.is_file():
        raise ReportBundleError(f"artifact {name!r} not on disk at {p}")
    return p.read_bytes()


__all__ = [
    "ARTIFACT_NAMES",
    "ReportBundle",
    "ReportBundleError",
    "build_report_bundle",
    "read_report_artifact",
]
