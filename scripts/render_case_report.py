#!/usr/bin/env python3
"""Phase 7b — render_case_report.py

Convert Phase 7a-captured field artifacts (reports/phase5_fields/{case}/{ts}/)
into visual renders (reports/phase5_renders/{case}/{ts}/):

- profile_u_centerline.png   — matplotlib static profile (sim vs gold)
- profile_u_centerline.html  — Plotly JSON (for frontend interactive)
- residuals.png              — log-y residual convergence history
- contour_u_magnitude.png    — 2D U-magnitude contour from final sample iter
- pointwise_deviation.png    — color heatmap of |dev|% per gold point

LDC MVP: works today for case_id=lid_driven_cavity. Other 9 cases will be
unlocked in Phase 7c Sprint-2 as their adapters emit Phase 7a function objects.

Usage:
    python scripts/render_case_report.py lid_driven_cavity
    python scripts/render_case_report.py lid_driven_cavity --run audit_real_run

Dependencies: matplotlib (2D plots), plotly (interactive JSON), numpy, PyYAML.
No PyVista / no VTK parser needed for MVP — uses the sample CSV directly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Codex round 1 HIGH (2026-04-21): enforce exact timestamp shape before
# composing filesystem paths, mirror ui/backend/services/comparison_report.py.
_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

import matplotlib

matplotlib.use("Agg")  # headless — CI-safe
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"
RENDERS_ROOT = REPO_ROOT / "reports" / "phase5_renders"
GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"

# Deterministic matplotlib style — locked for byte-reproducibility.
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "figure.dpi": 110,
    "savefig.dpi": 110,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.8,
})

# Phase 7a opt-in mirror — matches scripts/phase5_audit_run.py::_PHASE7A_OPTED_IN.
# GOLD_OVERLAY_CASES get the full 5-renderer treatment (profile overlay + deviation
# + Plotly JSON + residuals + 2D contour). VISUAL_ONLY_CASES (Tier C per DEC-V61-034)
# get only contour + residuals — every case shows real OpenFOAM evidence even
# when per-case gold-overlay plumbing is not yet wired. RENDER_SUPPORTED_CASES is
# the union (legacy name retained for test_audit_package_route.py references).
GOLD_OVERLAY_CASES = frozenset({"lid_driven_cavity"})
VISUAL_ONLY_CASES = frozenset({
    "backward_facing_step",
    "plane_channel_flow",
    "turbulent_flat_plate",
    "circular_cylinder_wake",
    "impinging_jet",
    "naca0012_airfoil",
    "rayleigh_benard_convection",
    "differential_heated_cavity",
    "duct_flow",
})
RENDER_SUPPORTED_CASES = GOLD_OVERLAY_CASES | VISUAL_ONLY_CASES


class RenderError(Exception):
    """Non-fatal render failure — caller decides whether to abort the batch."""


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _resolve_run_timestamp(case_id: str, run_label: str) -> str:
    """Read the per-run manifest written by phase5_audit_run.py and return its timestamp.

    Codex round 1 HIGH: enforce _TIMESTAMP_RE shape on the manifest value so a
    tampered manifest cannot steer downstream path composition outside
    reports/phase5_fields/.
    """
    manifest_path = FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"
    if not manifest_path.is_file():
        raise RenderError(f"no run manifest: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RenderError(f"manifest not an object: {manifest_path}")
    ts = data.get("timestamp")
    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
        raise RenderError(f"invalid timestamp shape in manifest: {ts!r}")
    return ts


def _artifact_dir(case_id: str, timestamp: str) -> Path:
    d = FIELDS_ROOT / case_id / timestamp
    # Containment check even though timestamp is already shape-gated upstream.
    try:
        d.resolve(strict=True).relative_to((FIELDS_ROOT / case_id).resolve())
    except (ValueError, OSError, FileNotFoundError):
        raise RenderError(f"artifact dir escapes fields root: {d}")
    if not d.is_dir():
        raise RenderError(f"artifact dir missing: {d}")
    return d


def _renders_dir(case_id: str, timestamp: str) -> Path:
    d = RENDERS_ROOT / case_id / timestamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load OpenFOAM `sample` output (.xy file, whitespace-separated).

    Column layout for uCenterline: y  U_x  U_y  U_z  p.
    Returns (y, U_x). Skips header lines starting with '#'.
    """
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        # Accept either 5 (y Ux Uy Uz p) or 2 (y Ux) column variants.
        try:
            y = float(parts[0])
            ux = float(parts[1])
        except (ValueError, IndexError):
            continue
        rows.append([y, ux])
    if not rows:
        raise RenderError(f"empty sample file: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _load_residuals_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load residuals.csv written by _capture_field_artifacts.

    Format: Time,Ux,Uy,p  — first data row may be "N/A" for iter 0.
    Returns (iterations, {field_name: array}).
    """
    raw = path.read_text(encoding="utf-8").splitlines()
    if not raw:
        raise RenderError(f"empty residuals: {path}")
    header = [c.strip() for c in raw[0].split(",")]
    if header[0].lower() not in ("time", "iter", "iteration"):
        raise RenderError(f"unexpected residuals header: {header}")
    fields = header[1:]
    iters: list[int] = []
    data: dict[str, list[float]] = {f: [] for f in fields}
    for line in raw[1:]:
        parts = [c.strip() for c in line.split(",")]
        if len(parts) != len(header):
            continue
        try:
            iters.append(int(float(parts[0])))
        except ValueError:
            continue
        for f, v in zip(fields, parts[1:]):
            if v.upper() == "N/A" or v == "":
                data[f].append(float("nan"))
            else:
                try:
                    data[f].append(float(v))
                except ValueError:
                    data[f].append(float("nan"))
    return np.array(iters), {k: np.array(v) for k, v in data.items()}


def _load_gold_ldc() -> tuple[list[float], list[float], str]:
    """Return (y_points, u_values, citation) from knowledge/gold_standards/lid_driven_cavity.yaml.

    File is multi-document YAML (u_centerline, v_centerline, primary_vortex_location).
    Iterate safe_load_all and pick the u_centerline document.
    """
    gold = GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold.is_file():
        raise RenderError(f"gold file missing: {gold}")
    docs = list(yaml.safe_load_all(gold.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise RenderError("no quantity: u_centerline doc in LDC gold YAML")
    refs = u_doc.get("reference_values", [])
    ys: list[float] = []
    us: list[float] = []
    for entry in refs:
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    citation = u_doc.get("source") or u_doc.get("citation") or \
        "Ghia, Ghia & Shin 1982 J. Comput. Phys. 47, 387-411 — Table I Re=100"
    return ys, us, citation


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def _latest_sample_iter(artifact_dir: Path) -> Path:
    """Return the highest-iteration sample directory (e.g. .../sample/1000/)."""
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise RenderError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise RenderError(f"no numeric iter subdirs under {sample_root}")
    return iters[-1]


def render_profile_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Matplotlib PNG: sim U_x(y) solid line + Ghia 1982 scatter markers."""
    latest = _latest_sample_iter(artifact_dir)
    xy = latest / "uCenterline.xy"
    y_sim, u_sim = _load_sample_xy(xy)

    # LDC is stored in physical coords (convertToMeters 0.1 → y ∈ [0, 0.1]).
    # Normalize to y_star ∈ [0, 1] for Ghia comparison.
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, citation = _load_gold_ldc()

    fig, ax = plt.subplots()
    ax.plot(u_sim, y_norm, color="#1f77b4", label="simpleFoam (sim)")
    ax.scatter(u_gold, y_gold, color="#d62728", s=36, zorder=5,
               label="Ghia 1982 (Table I, Re=100)", edgecolor="white", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xlabel(r"$U_x$ / $U_{\mathrm{lid}}$")
    ax.set_ylabel(r"$y\,/\,L$")
    ax.set_title(f"{case_id} — U centerline profile vs Ghia 1982")
    ax.legend(loc="upper left", frameon=False)
    ax.text(0.02, 0.02, citation[:80] + ("..." if len(citation) > 80 else ""),
            transform=ax.transAxes, fontsize=8, color="gray", style="italic")
    out = renders_dir / "profile_u_centerline.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_profile_plotly_json(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Plotly figure JSON (consumed by frontend for hover/zoom interactive)."""
    latest = _latest_sample_iter(artifact_dir)
    xy = latest / "uCenterline.xy"
    y_sim, u_sim = _load_sample_xy(xy)
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, citation = _load_gold_ldc()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=u_sim, y=y_norm, mode="lines", name="simpleFoam",
        line=dict(color="#1f77b4", width=2),
        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>sim</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=u_gold, y=y_gold, mode="markers", name="Ghia 1982",
        marker=dict(color="#d62728", size=9, line=dict(color="white", width=1)),
        hovertemplate="U<sub>x</sub>=%{x:.4f}<br>y/L=%{y:.4f}<extra>gold</extra>",
    ))
    fig.update_layout(
        title=f"{case_id} — U centerline profile vs {citation[:60]}",
        xaxis_title="U_x / U_lid",
        yaxis_title="y / L",
        template="plotly_white",
        hovermode="closest",
        margin=dict(l=50, r=20, t=50, b=50),
    )
    # Static JSON (no widget state). include_plotlyjs='cdn' on frontend side.
    payload = fig.to_json()
    out = renders_dir / "profile_u_centerline.plotly.json"
    out.write_text(payload, encoding="utf-8")
    return out


def _parse_residuals_from_log(log_path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Fallback: parse initial residuals per iteration out of the solver log.

    Tier C (DEC-V61-034) — when the `residuals` functionObject was not emitted
    into controlDict (case generators that pre-date Phase 7a), OpenFOAM still
    writes one `Solving for X, Initial residual = <val>, ...` line per field
    per iteration into the solver log. Extract by regex so every captured run
    gets a residuals plot regardless of controlDict shape.
    """
    if not log_path.is_file():
        raise RenderError(f"solver log missing: {log_path}")
    text = log_path.read_text(encoding="utf-8", errors="replace")
    # Iteration boundaries marked by `Time = <iter>` or `Time = <iter>s` lines.
    # simpleFoam / buoyantFoam steady-state writes `Time = 35s`; pimpleFoam
    # transient writes `Time = 0.0125`. Accept both forms.
    iter_re = re.compile(r"^Time\s*=\s*([0-9.eE+\-]+)s?\s*$", re.MULTILINE)
    # Per-field lines: `Solving for Ux, Initial residual = 1.23e-05, ...`
    solving_re = re.compile(
        r"Solving for (\w+), Initial residual = ([0-9.eE+\-]+)"
    )
    # Walk the log sequentially; for each `Time = N` marker, collect all
    # `Solving for X` lines up to the next marker.
    per_iter: list[tuple[float, dict[str, float]]] = []
    pos = 0
    time_matches = list(iter_re.finditer(text))
    if not time_matches:
        raise RenderError(f"no 'Time =' markers in solver log: {log_path}")
    for i, m in enumerate(time_matches):
        try:
            t = float(m.group(1))
        except ValueError:
            continue
        start = m.end()
        end = time_matches[i + 1].start() if i + 1 < len(time_matches) else len(text)
        seg = text[start:end]
        field_data: dict[str, float] = {}
        for sm in solving_re.finditer(seg):
            field, val = sm.group(1), sm.group(2)
            try:
                # Only record the FIRST Initial residual per field per iter
                # (simpleFoam solves a field once per iteration).
                if field not in field_data:
                    field_data[field] = float(val)
            except ValueError:
                pass
        if field_data:
            per_iter.append((t, field_data))
    if not per_iter:
        raise RenderError(f"no 'Solving for X' lines in solver log: {log_path}")
    iters = np.array([t for t, _ in per_iter])
    # Collect union of field names; pad missing entries with NaN.
    all_fields: set[str] = set()
    for _, fd in per_iter:
        all_fields.update(fd.keys())
    fields: dict[str, np.ndarray] = {}
    for f in sorted(all_fields):
        series = np.array([fd.get(f, np.nan) for _, fd in per_iter], dtype=float)
        fields[f] = series
    return iters, fields


def _find_latest_solver_log(artifact_dir: Path) -> Optional[Path]:
    for logname in ("log.simpleFoam", "log.icoFoam", "log.pimpleFoam", "log.buoyantFoam"):
        p = artifact_dir / logname
        if p.is_file():
            return p
    return None


def render_residuals_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p (+ T, k, epsilon for
    turbulent / buoyant cases).

    Prefers `residuals.csv` from the Phase 7a `residuals` functionObject. When
    that file is absent (cases whose generator does not yet emit the
    functionObject block), falls back to parsing the solver log — every
    captured run has a log, so the plot is always renderable.
    """
    csv = artifact_dir / "residuals.csv"
    if csv.is_file():
        iters, fields = _load_residuals_csv(csv)
    else:
        log_path = _find_latest_solver_log(artifact_dir)
        if log_path is None:
            raise RenderError(
                f"neither residuals.csv nor solver log found in {artifact_dir}"
            )
        iters, fields = _parse_residuals_from_log(log_path)

    fig, ax = plt.subplots()
    # Fixed palette for common fields; auto-assign from Tab10 for any others
    # (k, epsilon, omega, T, alphat, h, nut) so buoyant/turbulent cases plot.
    palette = {
        "Ux": "#1f77b4", "Uy": "#2ca02c", "Uz": "#17becf",
        "p": "#d62728", "p_rgh": "#ff7f0e", "T": "#9467bd",
        "k": "#8c564b", "epsilon": "#e377c2", "omega": "#bcbd22",
    }
    tab_fallback = plt.cm.tab10.colors
    for i, (name, series) in enumerate(sorted(fields.items())):
        color = palette.get(name, tab_fallback[i % len(tab_fallback)])
        # Use NaN-safe masking so iter-0 'N/A' doesn't break log plot.
        mask = np.isfinite(series) & (series > 0)
        if mask.sum() == 0:
            continue
        ax.semilogy(iters[mask], series[mask], color=color, label=name)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Initial residual (log)")
    ax.set_title(f"{case_id} — solver residual convergence")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    out = renders_dir / "residuals.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def render_pointwise_deviation_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Bar chart of |dev|% per gold sample point (sim interpolated onto gold y-grid)."""
    latest = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
    y_sim_norm = y_sim / max(y_sim.max(), 1e-12)

    y_gold, u_gold, _ = _load_gold_ldc()
    if not y_gold:
        raise RenderError("no LDC gold reference_values")

    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
    # Guard against division by ~0.
    denom = np.where(np.abs(u_gold) < 1e-9, 1e-9, np.abs(u_gold))
    dev_pct = 100.0 * np.abs(u_sim_interp - np.array(u_gold)) / denom

    fig, ax = plt.subplots()
    # Color-code: green PASS (<5%), yellow WARN (5-10%), red FAIL (>10%).
    colors = ["#2ca02c" if d < 5 else ("#ff9900" if d < 10 else "#d62728")
              for d in dev_pct]
    ax.bar(range(len(y_gold)), dev_pct, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(5, color="gray", linewidth=0.6, linestyle="--", alpha=0.6)
    ax.set_xticks(range(len(y_gold)))
    ax.set_xticklabels([f"{y:.3f}" for y in y_gold], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("Gold sample y/L")
    ax.set_ylabel("|dev|% vs Ghia 1982")
    ax.set_title(f"{case_id} — pointwise deviation (5% tolerance)")
    # Annotate PASS/FAIL count.
    n_pass = int((dev_pct < 5).sum())
    ax.text(
        0.98, 0.95, f"{n_pass}/{len(dev_pct)} PASS",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=10, fontweight="bold",
        color="#2ca02c" if n_pass == len(dev_pct) else "#d62728",
    )
    out = renders_dir / "pointwise_deviation.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def _find_latest_vtk(artifact_dir: Path) -> Optional[Path]:
    """Return the highest-iteration VTK volume file (not the allPatches one)."""
    vtk_root = artifact_dir / "VTK"
    if not vtk_root.is_dir():
        return None
    # Volume VTK files are at VTK/*.vtk (direct children); boundary data is under VTK/allPatches/.
    candidates = sorted(
        p for p in vtk_root.glob("*.vtk") if p.is_file()
    )
    return candidates[-1] if candidates else None


def _render_structured_contour(
    case_id: str, Ux: np.ndarray, Uy: np.ndarray, Cx: np.ndarray, Cy: np.ndarray,
    out: Path,
) -> Optional[Path]:
    """Fast path for structured square grids (LDC). Returns Path on success, None on fail."""
    n = Ux.shape[0]
    side = int(round(n ** 0.5))
    if side * side != n:
        return None
    order = np.lexsort((Cx, Cy))
    try:
        Ux_r = Ux[order].reshape(side, side)
        Uy_r = Uy[order].reshape(side, side)
        x = Cx[order].reshape(side, side)
        y = Cy[order].reshape(side, side)
    except ValueError:
        return None
    mag = np.sqrt(Ux_r ** 2 + Uy_r ** 2)
    lid = max(float(y.max()), 1e-12)
    xn, yn = x / lid, y / lid
    x_min, x_max = float(xn.min()), float(xn.max())
    y_min, y_max = float(yn.min()), float(yn.max())
    x1d = np.linspace(x_min, x_max, side)
    y1d = np.linspace(y_min, y_max, side)
    # DEC-V61-049 batch D: bump figsize + dpi so LDC annotations stay
    # readable. Previous 6.5×6 inches @ default dpi gave ~650 px image
    # where vortex/secondary/provenance text was too small.
    fig, ax = plt.subplots(figsize=(9, 8))
    cf = ax.contourf(x1d, y1d, mag, levels=20, cmap="viridis")
    ax.streamplot(x1d, y1d, Ux_r, Uy_r, density=1.1, color="white",
                  linewidth=0.6, arrowsize=0.8)
    ax.set_aspect("equal")
    ax.set_xlabel("x / L")
    ax.set_ylabel("y / L")
    ax.set_title(f"{case_id} — actual OpenFOAM |U|/U_lid contour + streamlines")
    cbar = fig.colorbar(cf, ax=ax, fraction=0.045, pad=0.04)
    cbar.set_label("|U| / U_lid")

    # DEC-V61-049 batch D — LDC-specific novice annotations.
    # Codex CFD-novice walk Step 4: the structured contour was visually
    # recognizable but lacked the callouts a first-semester student needs
    # to map the image to the physics narrative (moving lid as sole
    # momentum source; primary vortex near Ghia's (0.6172, 0.7344);
    # secondary vortices in bottom corners). Only LDC gets these —
    # other cases fall through.
    if case_id.startswith("lid_driven_cavity"):
        # Stretch y a bit and give the title room so the lid annotation
        # does not collide with the title line.
        ax.set_ylim(-0.02, 1.08)
        ax.set_xlim(-0.02, 1.05)
        # 1. Lid arrows + label JUST BELOW y=1 so they sit inside the plot
        #    area and do not fight the suptitle. Arrows + label are placed
        #    between the top of the cavity (y=1) and the cavity interior.
        for xi in (0.18, 0.48, 0.78):
            ax.annotate(
                "", xy=(xi + 0.10, 0.965), xytext=(xi, 0.965),
                arrowprops=dict(arrowstyle="->", color="#f59e0b", lw=1.6),
            )
        ax.text(
            0.5, 1.045, "lid · U = U_lid →  (sole momentum source)",
            ha="center", color="#f59e0b", fontsize=9, fontweight="bold",
        )
        # 2. Primary vortex marker at Ghia Re=100 (0.6172, 0.7344).
        #    Callout moved to lower-left interior to avoid right-edge clip.
        ax.plot(0.6172, 0.7344, marker="o", markersize=11,
                markerfacecolor="none", markeredgecolor="#ef4444",
                markeredgewidth=2.2, zorder=5)
        ax.annotate(
            "primary vortex\nGhia Re=100: (0.6172, 0.7344)",
            xy=(0.6172, 0.7344), xytext=(0.15, 0.45),
            fontsize=8, color="#ef4444",
            ha="left",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#1f1515",
                      edgecolor="#ef4444", linewidth=0.6),
            arrowprops=dict(arrowstyle="->", color="#ef4444", lw=0.9,
                            connectionstyle="arc3,rad=0.2"),
        )
        # 3. Secondary vortex labels at bottom corners (tucked inside plot).
        ax.text(0.03, 0.10, "secondary\nvortex (BL)", fontsize=7.5,
                color="#c084fc", alpha=0.95,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#1e1b4b",
                          edgecolor="#c084fc", linewidth=0.6))
        ax.text(0.78, 0.10, "secondary\nvortex (BR)", fontsize=7.5,
                color="#c084fc", alpha=0.95,
                bbox=dict(boxstyle="round,pad=0.22", facecolor="#1e1b4b",
                          edgecolor="#c084fc", linewidth=0.6))
        # 4. Cavity outline (visual hint of 1×1 square)
        ax.plot([0, 1, 1, 0, 0], [0, 0, 1, 1, 0],
                color="#94a3b8", linewidth=0.9, alpha=0.7, linestyle="--")
        # 5. Provenance footnote so the student knows this is real solver output
        fig.text(
            0.5, 0.005,
            "actual simpleFoam audit_real_run output · NOT synthetic / NOT ansatz",
            ha="center", fontsize=7.5, color="#64748b", style="italic",
        )

    fig.savefig(out, bbox_inches="tight", dpi=120)
    plt.close(fig)
    return out


def _render_unstructured_contour(
    case_id: str, Ux: np.ndarray, Uy: np.ndarray, Cx: np.ndarray, Cy: np.ndarray,
    out: Path,
) -> Path:
    """Robust fallback for unstructured / non-square meshes (BFS, cylinder wake,
    airfoil, impinging jet, channel, etc.). Uses matplotlib.tri.Triangulation on
    the raw cell-centroid cloud to render a filled |U| contour. Streamlines are
    skipped (they need a regular grid); instead, a sparse velocity-arrow overlay
    gives a sense of the vector field.

    Handles divergent / diverged solutions robustly: clips |U| to a finite
    percentile range so matplotlib doesn't choke on inf / extreme values
    (common when a solver fails to converge and emits garbage last-iter fields).
    """
    import matplotlib.tri as mtri
    with np.errstate(over="ignore", invalid="ignore"):
        mag = np.sqrt(Ux ** 2 + Uy ** 2)
    # Replace non-finite with 0 for triangulation + clip the tail at the 99th
    # percentile of finite values so one runaway cell doesn't saturate colormap.
    finite = np.isfinite(mag)
    if not finite.any():
        mag = np.zeros_like(mag)
    else:
        vmax = float(np.nanpercentile(mag[finite], 99.0))
        if not np.isfinite(vmax) or vmax <= 0:
            vmax = 1.0
        mag = np.where(finite, np.clip(mag, 0.0, vmax), 0.0)
        Ux = np.where(np.isfinite(Ux), np.clip(Ux, -vmax, vmax), 0.0)
        Uy = np.where(np.isfinite(Uy), np.clip(Uy, -vmax, vmax), 0.0)
    # Aspect-adaptive figsize: elongated domains (BFS L=40/H=9, plane_channel
    # L=30/H=1, duct_flow L=5/H=0.4) crammed into a 7.5×5.5 canvas look
    # unreadable (titles overlap the domain, quiver arrows oversized). Scale
    # figsize to actual (dx, dy) span, capped so colorbar + labels fit.
    finite_xy = np.isfinite(Cx) & np.isfinite(Cy)
    if finite_xy.any():
        dx = float(Cx[finite_xy].max() - Cx[finite_xy].min())
        dy = float(Cy[finite_xy].max() - Cy[finite_xy].min())
    else:
        dx, dy = 1.0, 1.0
    aspect = (dx / dy) if dy > 0 else 1.0
    if aspect >= 2.5:
        fig_h = 4.2
        fig_w = min(max(fig_h * aspect * 0.9, 8.0), 14.0)
    elif aspect <= 0.4:
        fig_w = 5.0
        fig_h = min(max(fig_w / aspect * 0.9, 6.0), 12.0)
    else:
        fig_w, fig_h = 7.5, 5.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    # Attempt Delaunay triangulation; qhull fails on degenerate/collinear
    # geometries (e.g. NACA0012 after a solver divergence — all cells end up
    # at boundary or coincident). Fall through to scatter on failure.
    cf = None
    try:
        triang = mtri.Triangulation(Cx, Cy)
        cf = ax.tricontourf(triang, mag, levels=20, cmap="viridis")
    except Exception as e:
        print(f"[render] [WARN] tricontourf failed ({e}); using scatter fallback",
              file=sys.stderr)
    if cf is None:
        # Plain scatter-mag map — always works, no triangulation.
        cf = ax.scatter(Cx, Cy, c=mag, s=8, cmap="viridis", edgecolors="none")
    # Aspect-aware quiver density: target ~120-200 arrows laid out roughly
    # proportional to the domain aspect so elongated domains don't look like
    # a stripe of overlapping arrows. Prior uniform stride=sqrt(n)/8 produced
    # ~700 arrows on BFS → unreadable.
    n = len(Cx)
    target_arrows = 150
    stride = max(1, int(n / target_arrows))
    idx = np.arange(0, n, stride)
    ax.quiver(
        Cx[idx], Cy[idx], Ux[idx], Uy[idx],
        color="white", alpha=0.85, scale=None, width=0.0018,
        headwidth=3.2, headlength=3.8,
    )
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title(f"{case_id} — |U| contour (unstructured tricontour + quiver)",
                 fontsize=10, pad=6)
    cbar = fig.colorbar(cf, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("|U| [m/s]")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight", dpi=110)
    plt.close(fig)
    return out


def _pick_2d_plane(
    Cx: np.ndarray, Cy: np.ndarray, Cz: np.ndarray, U: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str, str]:
    """Return (axis1, axis2, vel1, vel2, label1, label2) for the 2D plane with
    non-degenerate coordinate variance. Pseudo-2D CFD cases are typically one
    cell thick in ONE of {x, y, z}; pick the two non-degenerate axes.

    Fallback: (Cx, Cy) if all three look non-degenerate.
    """
    def _span(arr: np.ndarray) -> float:
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return 0.0
        return float(arr.max() - arr.min())

    spans = [(_span(Cx), "x", Cx, U[:, 0]),
             (_span(Cy), "y", Cy, U[:, 1]),
             (_span(Cz), "z", Cz, U[:, 2])]
    # Sort descending; pick the top two.
    spans.sort(key=lambda s: s[0], reverse=True)
    (_, l1, c1, v1), (_, l2, c2, v2) = spans[0], spans[1]
    return c1, c2, v1, v2, l1, l2


def render_contour_u_magnitude_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """2D U-magnitude contour from the real VTK volume.

    Three-tier rendering path (tries each, falls through on failure):
    1. Structured grid: LDC-style square mesh → contourf + streamplot (publication quality).
    2. Unstructured: tricontourf on raw cell centroids + sparse quiver overlay —
       works for BFS, cylinder wake, airfoil, impinging jet, channel, etc.
    3. Scatter: final fallback when Delaunay triangulation fails (e.g. NACA0012
       after solver divergence → singular/collinear geometry).

    Auto-detects the 2D plane — not all cases are in the x-y plane (NACA0012
    uses x-z, some use y-z); picks the two axes with non-degenerate variance.
    """
    out = renders_dir / "contour_u_magnitude.png"
    vtk_path = _find_latest_vtk(artifact_dir)
    if vtk_path is not None:
        try:
            import pyvista as pv
            pv.OFF_SCREEN = True
            mesh = pv.read(str(vtk_path))
            cd = mesh.cell_data
            if "U" not in cd or "Cx" not in cd or "Cy" not in cd:
                raise RenderError(f"VTK missing U/Cx/Cy: {vtk_path}")
            U = np.asarray(cd["U"])
            Cx = np.asarray(cd["Cx"])
            Cy = np.asarray(cd["Cy"])
            Cz = np.asarray(cd["Cz"]) if "Cz" in cd else np.zeros_like(Cx)
            # Auto-pick the 2D plane with non-degenerate variance so that
            # cases meshed in x-z (NACA0012) or y-z still produce a contour.
            ax1, ax2, vel1, vel2, _, _ = _pick_2d_plane(Cx, Cy, Cz, U)
            # Try structured-grid path first (fast, publication-style).
            result = _render_structured_contour(case_id, vel1, vel2, ax1, ax2, out)
            if result is not None:
                return result
            # Fall through to unstructured tricontour.
            return _render_unstructured_contour(case_id, vel1, vel2, ax1, ax2, out)
        except Exception as e:  # noqa: BLE001 — try minimal fallback
            print(f"[render] [WARN] VTK contour failed ({e}); trying sample-strip fallback",
                  file=sys.stderr)

    # Minimal fallback — only works if sample/{iter}/uCenterline.xy exists
    # (LDC-only). Other cases without VTK or sample will raise.
    try:
        latest = _latest_sample_iter(artifact_dir)
        y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
    except Exception as e:  # noqa: BLE001
        raise RenderError(f"no VTK and no sample fallback available: {e}")
    y_norm = y_sim / max(y_sim.max(), 1e-12)
    fig, ax = plt.subplots(figsize=(4, 6))
    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
    im = ax.imshow(
        strip, aspect="auto", origin="lower",
        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
        cmap="RdBu_r", vmin=-1.0, vmax=1.0,
    )
    ax.set_xlabel("(tile axis)")
    ax.set_ylabel("y / L")
    ax.set_title(f"{case_id} — centerline slice (VTK parse failed, MVP fallback)")
    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
    cbar.set_label("U_x")
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Render figures for a given case/run. Returns {name: path, ...}.

    GOLD_OVERLAY_CASES (LDC today) get the full 5-renderer treatment (profile
    vs gold, pointwise deviation, Plotly JSON, residuals, contour).
    VISUAL_ONLY_CASES (Tier C fan-out, DEC-V61-034) get just residuals +
    contour — real OpenFOAM evidence without requiring per-case gold-overlay
    plumbing.
    """
    if case_id not in RENDER_SUPPORTED_CASES:
        raise RenderError(
            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}."
        )
    timestamp = _resolve_run_timestamp(case_id, run_label)
    artifact_dir = _artifact_dir(case_id, timestamp)
    renders_dir = _renders_dir(case_id, timestamp)

    outputs: dict[str, Path] = {}
    if case_id in GOLD_OVERLAY_CASES:
        renderers = [
            ("profile_png", render_profile_png),
            ("profile_plotly_json", render_profile_plotly_json),
            ("residuals_png", render_residuals_png),
            ("pointwise_deviation_png", render_pointwise_deviation_png),
            ("contour_u_magnitude_png", render_contour_u_magnitude_png),
        ]
    else:
        # Tier C — visual-only mode.
        renderers = [
            ("residuals_png", render_residuals_png),
            ("contour_u_magnitude_png", render_contour_u_magnitude_png),
        ]
    errors: dict[str, str] = {}
    for name, fn in renderers:
        try:
            outputs[name] = fn(case_id, artifact_dir, renders_dir)
        except Exception as e:  # noqa: BLE001  — keep batch alive
            errors[name] = f"{type(e).__name__}: {e}"
            print(f"[render] [WARN] {name} failed: {e}", file=sys.stderr)

    # Write per-run renders manifest (mirrors phase5_fields/{case}/runs/{label}.json).
    manifest_dir = RENDERS_ROOT / case_id / "runs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "case_id": case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "renders_dir_rel": str(renders_dir.relative_to(REPO_ROOT)),
        "outputs": {k: str(p.relative_to(REPO_ROOT)) for k, p in outputs.items()},
        "errors": errors,
    }
    manifest_path = manifest_dir / f"{run_label}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[render] {case_id} → {len(outputs)}/{len(renderers)} outputs; manifest={manifest_path}")
    return {"manifest": manifest_path, **outputs}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7b render pipeline for CFD audit artifacts")
    parser.add_argument("case_id", help="e.g. lid_driven_cavity")
    parser.add_argument("--run", dest="run_label", default="audit_real_run",
                        help="run_label (default: audit_real_run)")
    args = parser.parse_args(argv)
    try:
        render_all(args.case_id, args.run_label)
        return 0
    except RenderError as e:
        print(f"[render] FATAL {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
