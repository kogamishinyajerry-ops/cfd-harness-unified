"""
Build capability radar comparison: cfd-harness-unified vs STAR-CCM+ vs ANSYS Fluent vs OpenFOAM vanilla.

8 axes, 0-10 scale, 4 overlaid polygons.

Scores are honest project self-assessment (not marketing). Justifications
written in adjacent COMMENTARY.md so each score is auditable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "capability_radar.png"

# Chinese font setup for axis labels
mpl.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

# ────────── Axes ──────────
AXES = [
    "CAD/几何 ingest",
    "网格生成",
    "物理模型覆盖",
    "求解器健壮性",
    "后处理质量",
    "CLI/自动化",
    "AI 智能辅助",
    "可重现/审计",
]

# ────────── Scores (0-10, honest assessment) ──────────
# See COMMENTARY.md for per-cell justification.

SCORES = {
    "cfd-harness-unified": [6, 6, 7, 6, 7, 9, 8, 9],
    "STAR-CCM+":            [9, 9, 10, 9, 9, 5, 2, 6],
    "ANSYS Fluent":         [8, 8, 10, 9, 8, 4, 1, 5],
    "OpenFOAM (vanilla)":   [3, 5, 9, 6, 5, 9, 0, 7],
}

COLORS = {
    "cfd-harness-unified": "#3b82f6",   # blue
    "STAR-CCM+":            "#ef4444",   # red
    "ANSYS Fluent":         "#a855f7",   # purple
    "OpenFOAM (vanilla)":   "#10b981",   # green
}

LINESTYLES = {
    "cfd-harness-unified": "-",
    "STAR-CCM+":            "--",
    "ANSYS Fluent":         "--",
    "OpenFOAM (vanilla)":   ":",
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    N = len(AXES)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]  # close polygon

    fig, ax = plt.subplots(figsize=(13, 11),
                           subplot_kw=dict(polar=True),
                           facecolor="#f8f9fb")
    ax.set_facecolor("#f8f9fb")

    # Axis setup
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Axis labels (rotated to face outward)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(AXES, fontsize=13, fontweight="bold")

    # Radial grid: 0, 2, 4, 6, 8, 10
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=9, color="#6b7280")
    ax.grid(True, color="#cbd5e1", linewidth=0.8, linestyle="-", alpha=0.7)
    ax.spines["polar"].set_color("#94a3b8")

    # Plot each project
    for name, scores in SCORES.items():
        vals = scores + scores[:1]  # close polygon
        color = COLORS[name]
        ls = LINESTYLES[name]
        lw = 3 if name == "cfd-harness-unified" else 1.8
        alpha_fill = 0.22 if name == "cfd-harness-unified" else 0.06
        ax.plot(angles, vals, color=color, linewidth=lw, linestyle=ls,
                label=name, marker="o", markersize=6, zorder=3)
        ax.fill(angles, vals, color=color, alpha=alpha_fill, zorder=2)

    # Legend below the chart
    legend = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.12),
                       ncol=4, fontsize=11, frameon=False)

    # Title + subtitle
    fig.suptitle("CFD 工程能力雷达图 · 4-way 对标 (0–10 评分)",
                 fontsize=18, fontweight="bold", y=0.97, color="#1f2937")
    fig.text(0.5, 0.92,
             "cfd-harness-unified 项目能力定位 · 2026-05-13",
             ha="center", fontsize=11, color="#6b7280")

    # Bottom-right project tag
    fig.text(0.95, 0.02, "cfd-harness-unified · 自我评估 · 见 COMMENTARY.md",
             ha="right", fontsize=8, color="#9ca3af", style="italic")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"✓ {OUT_PNG}")
    print(f"  size: {OUT_PNG.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
