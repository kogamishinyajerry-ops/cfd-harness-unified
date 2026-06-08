"""P4 V71.B · low-Re k-omega-SST backward-facing-step QoI extractor (Execution Plane).

Computes the two benchmark QoIs of the wall-RESOLVED (y+<1) backward-facing-step
anchor (``backward_facing_step_lowre``) from a solved case's downstream
reattachment-floor faces:

    reattachment_xr_h  = x of the wall-shear tau_x POS→NEG zero-crossing / H
    floor_yplus_max    = max first-cell y+ over the reattachment-floor faces

Both are read off the floor faces selected by the SHARED mask in
``src.bfs_floor_region`` — the identical filter the live reattachment extractor in
``src.foam_agent_adapter`` (Path-1a) uses — so the y+<1 precondition is gated on
EXACTLY the faces the reattachment QoI is measured on (no mask drift,
cfd-vv-director condition, DEC-V61-235).

Two co-located data sources, one downstream computation
-------------------------------------------------------
  * ``floor_faces.csv`` (stdlib) — the FROZEN per-face ``(x, y, yplus, tau_x)``
    derived ONCE from the allPatches VTK with the shared mask. The offline gate
    replay reads this (no pyvista dependency → the gate test always runs).
  * ``VTK/allPatches/allPatches_*.vtk`` (pyvista) — the LIVE solver artifact the
    workbench produces during ``foam_agent_adapter.execute()``; the production
    gate reads this. ``write_floor_faces_csv`` derives the frozen CSV from it.

``extract_bfs_lowre(case_dir)`` resolves the CSV first (frozen replay), else the
VTK (live), and feeds both through the SAME ``_metrics_from_floor_faces`` core.

HONESTY (the load-bearing property of the downstream gate)
----------------------------------------------------------
Every QoI is computed from the solver's OWN field output (wall-shear stress and
y+ on the floor faces). The reattachment reference (6.26) and the y+<1 bar live
SOLELY in the gold + gate; the closed form is NEVER read here. The wall-shear
tau_x sign convention is OpenFOAM's: on a floor with +x flow the reported
``-tau_xy`` is NEGATIVE where the fluid runs forward (attached) and POSITIVE where
it reverses (recirculation), so reattachment is the first POS→NEG crossing (the
NEG→POS crossing is the spurious x≈1.3 corner-eddy feature). Reattachment is the
wall-shear definition — NOT a fixed-height U_x sign change, which is
grid-height-biased on the resolved mesh (high-Re first-cell y+≈5 happens to put a
y=0.02 probe in the first cell; the resolved y+<1 mesh does not). Missing / empty
/ non-crossing input → raise, never a fabricated default (fail-closed audit
discipline) — feed a wrong field and the gate FAILS.

ADR-001 plane assignment: **Execution Plane** (reads solver artifacts; imports
only stdlib + the shared Execution-plane floor mask + numpy/pyvista lazily for
the VTK path; NO Evaluation/Control imports — the comparator wiring lives in
``src.bfs_lowre_gate``, Control Plane).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .bfs_floor_region import is_floor_face

# step height H (normalization for Xr/H); the canonical BFS uses H=1.
_H_BFS: float = 1.0


@dataclass(frozen=True)
class BfsLowReMetrics:
    """Measured QoIs of a solved low-Re BFS reattachment floor (Execution output)."""

    reattachment_xr_h: float          # x of the wall-shear pos→neg zero-crossing / H
    floor_yplus_max: float            # max first-cell y+ over the reattachment floor
    n_floor_faces: int                # number of faces the shared floor mask selected
    n_pos_neg_crossings: int          # wall-shear tau_x pos→neg crossings (a clean run has 1)
    reattachment_method: str = "wall_shear_tau_x_zero_crossing"


def _metrics_from_floor_faces(
    xs: List[float], yplus: List[float], tau_x: List[float]
) -> BfsLowReMetrics:
    """Compute the QoIs from co-located floor-face arrays (stdlib, fail-closed).

    ``xs`` / ``yplus`` / ``tau_x`` are parallel per-face lists (one value per
    reattachment-floor face). Raises ``ValueError`` on empty input, length
    mismatch, or no wall-shear sign change (a recirculation bubble that never
    reattaches in the sampled window) — never fabricates a reattachment.
    """
    n = len(xs)
    if n == 0:
        raise ValueError("bfs_lowre extractor: no reattachment-floor faces (empty mask)")
    if not (len(yplus) == n and len(tau_x) == n):
        raise ValueError(
            f"bfs_lowre extractor: ragged floor-face arrays "
            f"(x={n}, yplus={len(yplus)}, tau_x={len(tau_x)})"
        )

    order = sorted(range(n), key=lambda i: xs[i])
    xs_s = [xs[i] for i in order]
    tx_s = [tau_x[i] for i in order]

    # Wall-shear pos→neg crossings (OpenFOAM convention: tau_x>0 = reversed/recirc,
    # tau_x<0 = forward/attached → reattachment is recirc→attached = pos→neg).
    crossings: List[float] = []
    for j in range(1, n):
        t1, t2 = tx_s[j - 1], tx_s[j]
        if t1 > 0 and t2 <= 0:
            denom = t2 - t1
            xc = (
                xs_s[j - 1] - t1 * (xs_s[j] - xs_s[j - 1]) / denom
                if abs(denom) > 1e-30
                else xs_s[j - 1]
            )
            crossings.append(xc)

    if not crossings:
        raise ValueError(
            "bfs_lowre extractor: wall-shear tau_x never crosses pos→neg on the "
            "reattachment floor (no reattachment detected — fail-closed)"
        )

    xr = crossings[0]
    if not (xr > 0.0):
        raise ValueError(f"bfs_lowre extractor: non-physical reattachment x={xr!r}")

    return BfsLowReMetrics(
        reattachment_xr_h=xr / _H_BFS,
        floor_yplus_max=max(yplus),
        n_floor_faces=n,
        n_pos_neg_crossings=len(crossings),
    )


def read_floor_faces_from_csv(
    csv_path: Path,
) -> Tuple[List[float], List[float], List[float]]:
    """Parse a frozen ``floor_faces.csv`` (stdlib) → ``(xs, yplus, tau_x)``.

    Header line ``x,y,yplus,tau_x``; ``#`` comment lines skipped. The frozen CSV is
    already floor-masked at derivation time, but each row is re-checked against the
    SHARED ``is_floor_face`` bounds so a hand-edited CSV cannot smuggle an
    off-floor face into the gate.
    """
    xs: List[float] = []
    yps: List[float] = []
    txs: List[float] = []
    text = csv_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("x,"):
            continue
        parts = s.split(",")
        if len(parts) < 4:
            continue
        x, y, yp, tx = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        if not is_floor_face(x, y):
            continue
        xs.append(x)
        yps.append(yp)
        txs.append(tx)
    return xs, yps, txs


def read_floor_faces_from_vtk(
    vtk_path: Path,
) -> Tuple[List[float], List[float], List[float]]:
    """Read floor faces from an allPatches VTK (pyvista) → ``(xs, yplus, tau_x)``.

    Applies the SHARED ``bfs_floor_mask`` to ``cell_centers()`` so the face set is
    byte-identical to the live adapter Path-1a reattachment extractor. Raises if
    pyvista is unavailable or the VTK lacks ``yPlus`` / ``wallShearStress`` (the
    yPlus + wallShearStress function objects must have run — fail-closed).
    """
    import numpy as _np  # noqa: PLC0415
    import pyvista as _pv  # noqa: PLC0415

    from .bfs_floor_region import bfs_floor_mask  # noqa: PLC0415

    ap = _pv.read(str(vtk_path))
    names = set(ap.array_names)
    missing = {"yPlus", "wallShearStress"} - names
    if missing:
        raise ValueError(
            f"bfs_lowre extractor: allPatches VTK missing {sorted(missing)} "
            f"(yPlus/wallShearStress function objects did not run)"
        )
    centres = _np.asarray(ap.cell_centers().points)
    mask = bfs_floor_mask(centres)
    xs = centres[mask, 0].tolist()
    yplus = _np.asarray(ap["yPlus"])[mask].tolist()
    tau_x = _np.asarray(ap["wallShearStress"])[mask, 0].tolist()
    return xs, yplus, tau_x


def write_floor_faces_csv(vtk_path: Path, csv_path: Path) -> None:
    """Freeze-utility: derive the stdlib ``floor_faces.csv`` from an allPatches VTK.

    Uses ``read_floor_faces_from_vtk`` (the SHARED mask), so the frozen CSV is a
    faithful, co-located serialization of the VTK floor faces (the fidelity test
    re-derives and compares).
    """
    import numpy as _np  # noqa: PLC0415
    import pyvista as _pv  # noqa: PLC0415

    from .bfs_floor_region import (  # noqa: PLC0415
        BFS_FLOOR_X_MAX,
        BFS_FLOOR_X_MIN,
        BFS_FLOOR_Y_MAX,
        bfs_floor_mask,
    )

    ap = _pv.read(str(vtk_path))
    centres = _np.asarray(ap.cell_centers().points)
    mask = bfs_floor_mask(centres)
    xs = centres[mask, 0]
    ys = centres[mask, 1]
    yp = _np.asarray(ap["yPlus"])[mask]
    tx = _np.asarray(ap["wallShearStress"])[mask, 0]
    order = _np.argsort(xs)
    lines = [
        "# V71.B backward_facing_step_lowre — downstream reattachment-floor faces",
        f"# derived from {vtk_path.name} via src.bfs_floor_region.bfs_floor_mask",
        f"# floor filter: y<{BFS_FLOOR_Y_MAX} AND x>{BFS_FLOOR_X_MIN} AND x<{BFS_FLOOR_X_MAX} (SINGLE SOURCE OF TRUTH)",
        "x,y,yplus,tau_x",
    ]
    for i in order:
        lines.append(f"{xs[i]:.6e},{ys[i]:.6e},{yp[i]:.6e},{tx[i]:.6e}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def extract_bfs_lowre(case_dir: Path) -> BfsLowReMetrics:
    """Resolve the floor-face source under ``case_dir`` and compute the QoIs.

    Resolution order: the frozen ``proof/floor_faces.csv`` (offline replay, stdlib)
    first, else the live ``VTK/allPatches/allPatches_*.vtk`` (pyvista). Raises if
    neither is present (fail-closed — never fabricates a verdict).
    """
    case_dir = Path(case_dir)
    csv_path = case_dir / "proof" / "floor_faces.csv"
    if csv_path.is_file():
        xs, yplus, tau_x = read_floor_faces_from_csv(csv_path)
        return _metrics_from_floor_faces(xs, yplus, tau_x)

    vtk_dir = case_dir / "VTK" / "allPatches"
    vtks = list(vtk_dir.glob("allPatches_*.vtk")) if vtk_dir.is_dir() else []
    if vtks:
        # Codex R1 P2: pick the latest snapshot by NUMERIC timestep, not
        # lexicographically — plain ``sorted`` orders ``allPatches_900.vtk`` AFTER
        # ``allPatches_3000.vtk`` ('9' > '3'), so the gate would measure an early,
        # unconverged field and return a wrong PASS/FAIL. Parse the trailing time
        # token (int or fractional) and fall back to -inf if it is unparseable
        # (those sort first, never chosen as "latest").
        def _vtk_timestep(p: Path) -> float:
            m = re.search(r"allPatches_([0-9]+(?:\.[0-9]+)?)\.vtk$", p.name)
            return float(m.group(1)) if m else float("-inf")

        latest = max(vtks, key=_vtk_timestep)
        xs, yplus, tau_x = read_floor_faces_from_vtk(latest)
        return _metrics_from_floor_faces(xs, yplus, tau_x)

    raise FileNotFoundError(
        f"bfs_lowre extractor: no floor-face source under {case_dir} "
        f"(expected proof/floor_faces.csv or VTK/allPatches/allPatches_*.vtk)"
    )


def to_key_quantities(metrics: BfsLowReMetrics) -> dict:
    """Project ``BfsLowReMetrics`` into the comparator ``key_quantities`` shape."""
    return {
        "reattachment_length": metrics.reattachment_xr_h,
        "reattachment_method": metrics.reattachment_method,
        "floor_yplus_max": metrics.floor_yplus_max,
        "n_floor_faces": float(metrics.n_floor_faces),
        "n_pos_neg_crossings": float(metrics.n_pos_neg_crossings),
    }
