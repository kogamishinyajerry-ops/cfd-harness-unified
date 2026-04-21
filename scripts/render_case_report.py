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
RENDER_SUPPORTED_CASES = frozenset({"lid_driven_cavity"})


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


def render_residuals_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """Matplotlib PNG: log-y residual convergence for Ux, Uy, p."""
    csv = artifact_dir / "residuals.csv"
    if not csv.is_file():
        raise RenderError(f"residuals.csv missing: {csv}")
    iters, fields = _load_residuals_csv(csv)

    fig, ax = plt.subplots()
    palette = {"Ux": "#1f77b4", "Uy": "#2ca02c", "p": "#d62728"}
    for name, series in fields.items():
        color = palette.get(name, "#7f7f7f")
        # Use NaN-safe masking so iter-0 'N/A' doesn't break log plot.
        mask = np.isfinite(series) & (series > 0)
        ax.semilogy(iters[mask], series[mask], color=color, label=name)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Initial residual (log)")
    ax.set_title(f"{case_id} — solver residual convergence")
    ax.legend(loc="upper right", frameon=False)
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


def render_contour_u_magnitude_png(
    case_id: str,
    artifact_dir: Path,
    renders_dir: Path,
) -> Path:
    """LDC MVP contour: uses the sample/{iter}/uCenterline.xy which is a 1D profile
    along x=0.5 centerline. For a true 2D contour we'd need to parse the full VTK
    volume, which requires the `vtk` package — deferred to Phase 7b polish.

    Instead, render a stylized 1D heatmap strip showing U_x(y) along the centerline.
    This is honestly labeled as "centerline slice" not "full field contour".
    """
    latest = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest / "uCenterline.xy")
    y_norm = y_sim / max(y_sim.max(), 1e-12)

    fig, ax = plt.subplots(figsize=(4, 6))
    # Tile the 1D profile horizontally to make a strip heatmap visible.
    strip = np.tile(u_sim.reshape(-1, 1), (1, 20))
    im = ax.imshow(
        strip,
        aspect="auto",
        origin="lower",
        extent=[0, 1, float(y_norm.min()), float(y_norm.max())],
        cmap="RdBu_r",
        vmin=-1.0, vmax=1.0,
    )
    ax.set_xlabel("(tile axis)")
    ax.set_ylabel("y / L")
    ax.set_title(f"{case_id} — U_x centerline slice\n(Phase 7b MVP — full 2D VTK contour\ndeferred to 7b-polish)")
    cbar = fig.colorbar(im, ax=ax, fraction=0.08, pad=0.04)
    cbar.set_label("U_x / U_lid")
    out = renders_dir / "contour_u_magnitude.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_all(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Render all 7b MVP figures for a given case/run. Returns {name: path, ...}."""
    if case_id not in RENDER_SUPPORTED_CASES:
        raise RenderError(
            f"case_id={case_id!r} not opted-in for Phase 7b rendering. "
            f"Supported: {sorted(RENDER_SUPPORTED_CASES)}. "
            f"Other cases unlock in Phase 7c Sprint-2."
        )
    timestamp = _resolve_run_timestamp(case_id, run_label)
    artifact_dir = _artifact_dir(case_id, timestamp)
    renders_dir = _renders_dir(case_id, timestamp)

    outputs: dict[str, Path] = {}
    renderers = [
        ("profile_png", render_profile_png),
        ("profile_plotly_json", render_profile_plotly_json),
        ("residuals_png", render_residuals_png),
        ("pointwise_deviation_png", render_pointwise_deviation_png),
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
