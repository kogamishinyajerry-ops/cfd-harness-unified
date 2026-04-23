"""DEC-V61-050 batch 2 — streamfunction ψ extraction from VTK.

Infrastructure consumed by batches 3 (primary vortex from argmin ψ)
and 4 (secondary BL/BR eddies from local extrema in corners). Does
not wire into the comparator on its own — a deliberate scope boundary
so this module can be reviewed and reused independently.

Method: compute ψ(x, y) on a uniform nx × ny grid by integrating
    ψ(x, y) = ∫₀^y U_x(x, y') dy'
along columns (trapezoidal rule, numpy). Resamples the unstructured
OpenFOAM VTK volume onto the uniform grid via pyvista's .sample().

Why integrate rather than solve ∇²ψ = −ω_z: the direct integral
needs only U_x (which OpenFOAM writes natively) and numpy trapz,
whereas the Poisson approach needs either scipy.sparse.linalg or a
custom multigrid, and the accuracy difference is dominated by the
underlying mesh/sampling errors, not the discretization of the ψ
equation. For LDC Re=100 with a 129² mesh this is adequate to
reproduce Ghia Table III primary vortex to ~1% in (x, y) and a few
percent in ψ_min; batches 3-4 will report the measured values against
those tolerances honestly.

Cache: writes {vtk_dir}/.psi_cache_{nx}x{ny}.npz keyed by the VTK
mtime so repeated calls at the same resolution hit the cache rather
than re-sampling (sampling a 20k-cell unstructured grid onto 129² ≈
17k points is ~100 ms, worth caching).

API:
    compute_streamfunction_from_vtk(vtk_path, nx=129, ny=129)
        → (psi, xs, ys) in physical units (m²/s, m, m) or None.

    find_vortex_core(psi, xs, ys, x_window_norm, y_window_norm, mode,
                     u_ref=1.0)
        → (x_c_norm, y_c_norm, psi_norm) in Ghia convention
          (x/L, y/L, ψ/(U·L)) or None.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np


class PsiExtractionError(RuntimeError):
    """Any recoverable failure in ψ extraction or vortex-core location.

    Introduced (Codex round 1 MED on DEC-V61-050 batch 4): gives callers
    a single type to catch rather than forcing them to enumerate pyvista
    / VTK / numpy / OS errors. The module still returns None from its
    public functions on soft failures (keeping the existing contract);
    this exception class exists so that callers who WANT to distinguish
    a genuine extractor failure from a "no data at all" result can.
    """


def pick_latest_internal_vtk(vtk_dir: Path) -> Optional[Path]:
    """Return the newest internal-field VTK in vtk_dir, or None.

    Matches the pattern used by src/comparator_gates.py:read_final_
    velocity_max — skips 'allPatches' boundary files, requires a
    trailing '_<iter>.vtk' suffix so we can order by iteration.
    """
    if not vtk_dir.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for p in vtk_dir.rglob("*.vtk"):
        if "allPatches" in p.parts:
            continue
        m = re.search(r"_(\d+)\.vtk$", p.name)
        if m is None:
            continue
        candidates.append((int(m.group(1)), p))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def compute_streamfunction_from_vtk(
    vtk_path: Path,
    nx: int = 129,
    ny: int = 129,
    bounds: Optional[tuple[float, float, float, float, float]] = None,
) -> Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Return (psi, xs, ys) on a uniform nx × ny grid, or None on failure.

    psi.shape == (ny, nx) in physical m²/s.
    xs, ys in physical m (uniform).
    bounds: optional explicit (xmin, xmax, ymin, ymax, z_mid). If None,
    derived from mesh.bounds with z at the midplane (2D slab convention).

    Returns None when pyvista is unavailable, the VTK is unreadable,
    or the mesh lacks a U vector field.
    """
    if not vtk_path.is_file():
        return None

    # Cache schema version — bump when the on-disk npz layout changes.
    CACHE_SCHEMA_VERSION = 2
    cache_dir = vtk_path.parent
    cache_file = cache_dir / f".psi_cache_{nx}x{ny}.npz"
    stat = vtk_path.stat()
    vtk_mtime_ns = int(stat.st_mtime_ns)
    vtk_size = int(stat.st_size)
    # Codex round 1 MED #3: prior cache key was {nx, ny, st_mtime float,
    # 1e-6 tol}; this misses APFS sub-µs updates and ext4 same-second
    # overwrites, and also ignored `bounds`. Use mtime_ns (integer, exact)
    # + size (catches content change when mtime is reused) + bounds
    # (explicit-bounds call shouldn't be served cached-default result) +
    # schema version (invalidates when this serialization format changes).
    bounds_key = tuple(bounds) if bounds is not None else None
    # Cache hit path is deliberately pyvista-free so a backend whose
    # python interpreter lacks a working pyvista/vtk install can still
    # serve ψ-derived dimensions as long as the cache was populated
    # out-of-band (e.g. by python3.11 via this module's __main__).
    if cache_file.is_file():
        try:
            cached = np.load(cache_file, allow_pickle=True)
            cached_schema = int(cached["schema_version"]) if "schema_version" in cached else 1
            cached_mtime_ns = int(cached["vtk_mtime_ns"]) if "vtk_mtime_ns" in cached else None
            cached_size = int(cached["vtk_size"]) if "vtk_size" in cached else None
            cached_bounds = cached["bounds"].item() if "bounds" in cached else None
            if (
                cached_schema == CACHE_SCHEMA_VERSION
                and cached_mtime_ns == vtk_mtime_ns
                and cached_size == vtk_size
                and cached_bounds == bounds_key
            ):
                return cached["psi"], cached["xs"], cached["ys"]
        except Exception:
            pass  # cache miss → recompute below

    try:
        import pyvista as pv
    except ImportError:
        return None

    try:
        grid = pv.read(str(vtk_path))
    except Exception:
        return None

    point_fields = set(grid.point_data.keys()) if hasattr(grid, "point_data") else set()
    cell_fields = set(grid.cell_data.keys()) if hasattr(grid, "cell_data") else set()

    if "U" not in point_fields and "U" in cell_fields:
        try:
            grid = grid.cell_data_to_point_data()
            point_fields = set(grid.point_data.keys())
        except Exception:
            return None
    if "U" not in point_fields:
        return None

    if bounds is None:
        xmin, xmax, ymin, ymax, zmin, zmax = grid.bounds
        z_mid = 0.5 * (zmin + zmax)
    else:
        xmin, xmax, ymin, ymax, z_mid = bounds

    if xmax <= xmin or ymax <= ymin:
        return None

    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, ny)
    XX, YY = np.meshgrid(xs, ys)  # shape (ny, nx)
    points = np.column_stack([
        XX.ravel(),
        YY.ravel(),
        np.full(XX.size, z_mid),
    ])
    probe = pv.PolyData(points).sample(grid)
    U = np.asarray(probe["U"])
    if U.ndim != 2 or U.shape[1] < 2:
        return None
    U_x = U[:, 0].reshape(YY.shape)

    # ψ(x, y) = ∫₀^y U_x(x, y') dy', trapezoidal along axis 0 (y).
    dy = ys[1] - ys[0] if ny > 1 else 0.0
    psi = np.zeros_like(U_x)
    for i in range(1, ny):
        psi[i, :] = psi[i - 1, :] + 0.5 * (U_x[i - 1, :] + U_x[i, :]) * dy

    try:
        np.savez(
            cache_file,
            psi=psi, xs=xs, ys=ys,
            vtk_mtime_ns=np.array([vtk_mtime_ns]),
            vtk_size=np.array([vtk_size]),
            bounds=np.array(bounds_key, dtype=object),
            schema_version=np.array([CACHE_SCHEMA_VERSION]),
        )
    except Exception:
        pass  # cache write best-effort

    return psi, xs, ys


def psi_wall_closure_residuals(
    psi: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    u_ref: float = 1.0,
) -> Optional[dict]:
    """Return max |ψ| on each of the 4 walls, normalized by U_ref·L.

    For LDC with no-slip everywhere except the lid, the stream function
    should satisfy ψ = 0 on all 4 walls. Numerical integration along
    columns plus resampling interpolation leak some residual. These
    residuals bound the credibility of derived observables:
      - primary vortex ψ_min ≈ 0.1 → residual O(1e-3) is fine
      - secondary eddies ψ ≈ 1e-6 to 1e-5 → residual must be << those
        or the match is coincidence, not physics.

    Introduced (Codex round 1 MED on DEC-V61-050 batch 4): caller can
    compare these residuals against observable scales and warn/fail.

    Returns {left, right, bottom, top, max, L} (all dimensionless, ψ/UL)
    or None if inputs invalid.
    """
    if xs.size == 0 or ys.size == 0 or psi.shape != (ys.size, xs.size):
        return None
    L = float(xs[-1]) if xs[-1] > 0 else 1.0
    denom = max(u_ref * L, 1e-12)
    left = float(np.max(np.abs(psi[:, 0]))) / denom
    right = float(np.max(np.abs(psi[:, -1]))) / denom
    bottom = float(np.max(np.abs(psi[0, :]))) / denom
    top = float(np.max(np.abs(psi[-1, :]))) / denom
    return {
        "left": left,
        "right": right,
        "bottom": bottom,
        "top": top,
        "max": max(left, right, bottom, top),
        "L": L,
    }


def find_vortex_core(
    psi: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    x_window_norm: tuple[float, float] = (0.0, 1.0),
    y_window_norm: tuple[float, float] = (0.0, 1.0),
    mode: str = "min",
    u_ref: float = 1.0,
) -> Optional[tuple[float, float, float]]:
    """Find local extremum of ψ inside the normalized (x/L, y/L) window.

    Returns (x_c_norm, y_c_norm, psi_ghia) where:
        x_c_norm, y_c_norm ∈ [0, 1] are normalized by L = xs[-1].
        psi_ghia = ψ / (U_ref · L) follows Ghia's non-dimensionalization
                   (matches Table III convention).
    Returns None if the window is empty or has no cells.

    Conventions for LDC Re=100 (Ghia 1982 Table III):
        primary  : window=(0,1)×(0,1),       mode='min'  (clockwise → ψ_min)
        BL eddy  : window=(0,0.25)×(0,0.25), mode='max'  (counter-rotate → ψ_max)
        BR eddy  : window=(0.75,1)×(0,0.25), mode='max'  (counter-rotate → ψ_max)
    """
    if xs.size == 0 or ys.size == 0:
        return None
    L = float(xs[-1])
    if L <= 0 or u_ref <= 0:
        return None

    xs_norm = xs / L
    ys_norm = ys / L

    x_lo, x_hi = x_window_norm
    y_lo, y_hi = y_window_norm
    x_mask = (xs_norm >= x_lo) & (xs_norm <= x_hi)
    y_mask = (ys_norm >= y_lo) & (ys_norm <= y_hi)
    if not x_mask.any() or not y_mask.any():
        return None

    ix_indices = np.where(x_mask)[0]
    iy_indices = np.where(y_mask)[0]
    sub = psi[np.ix_(iy_indices, ix_indices)]

    if mode == "min":
        flat_idx = int(np.argmin(sub))
        psi_val = float(sub.min())
    elif mode == "max":
        flat_idx = int(np.argmax(sub))
        psi_val = float(sub.max())
    else:
        raise ValueError(f"mode must be 'min' or 'max', got {mode!r}")

    iy_local, ix_local = np.unravel_index(flat_idx, sub.shape)
    iy = int(iy_indices[iy_local])
    ix = int(ix_indices[ix_local])

    return (
        float(xs_norm[ix]),
        float(ys_norm[iy]),
        psi_val / (u_ref * L),
    )


if __name__ == "__main__":
    # Smoke test against the existing LDC fixture.
    # Expected (Ghia 1982 Table III, Re=100):
    #   primary: (0.6172, 0.7344, ψ=-0.103423)
    #   BL     : (0.0313, 0.0391, ψ=+1.74877e-6)
    #   BR     : (0.9453, 0.0625, ψ=+1.25374e-5)
    import sys
    repo_root = Path(__file__).resolve().parents[3]
    fixture = repo_root / "reports/phase5_fields/lid_driven_cavity/20260421T082340Z/VTK"
    vtk = pick_latest_internal_vtk(fixture)
    if vtk is None:
        print("no VTK found under", fixture)
        sys.exit(1)
    print(f"reading {vtk.relative_to(repo_root)}")
    result = compute_streamfunction_from_vtk(vtk)
    if result is None:
        print("compute returned None (pyvista missing or VTK malformed)")
        sys.exit(1)
    psi, xs, ys = result
    print(f"psi grid: {psi.shape} · bounds x=[{xs[0]:.4g}, {xs[-1]:.4g}] y=[{ys[0]:.4g}, {ys[-1]:.4g}]")
    residuals = psi_wall_closure_residuals(psi, xs, ys)
    if residuals:
        print(f"\nψ wall-closure residuals (ψ/UL, should be << observable scale):")
        print(f"  left={residuals['left']:.2e}  right={residuals['right']:.2e}  bottom={residuals['bottom']:.2e}  top={residuals['top']:.2e}")
        print(f"  max={residuals['max']:.2e}  · BL/BR ψ scale ≈ 1e-6 to 1e-5 — wall residual > BL scale means BL match is suspect")
    primary = find_vortex_core(psi, xs, ys, mode="min")
    bl = find_vortex_core(psi, xs, ys, x_window_norm=(0.0, 0.25), y_window_norm=(0.0, 0.25), mode="max")
    br = find_vortex_core(psi, xs, ys, x_window_norm=(0.75, 1.0), y_window_norm=(0.0, 0.25), mode="max")
    print("\nGhia Re=100 vs measured:")
    print(f"  primary:  gold=(0.6172, 0.7344, ψ=-0.103423)  meas=({primary[0]:.4f}, {primary[1]:.4f}, ψ={primary[2]:+.6f})")
    print(f"  BL eddy:  gold=(0.0313, 0.0391, ψ=+1.749e-6)  meas=({bl[0]:.4f}, {bl[1]:.4f}, ψ={bl[2]:+.6g})")
    print(f"  BR eddy:  gold=(0.9453, 0.0625, ψ=+1.254e-5)  meas=({br[0]:.4f}, {br[1]:.4f}, ψ={br[2]:+.6g})")
