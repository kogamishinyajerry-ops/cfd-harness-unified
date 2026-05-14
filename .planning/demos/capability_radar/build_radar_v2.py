"""
Build capability radar v2: cfd-harness-unified vs STAR-CCM+ vs Fluent vs OpenFOAM vanilla.

v2 is the M-RADAR-V2 milestone deliverable. Re-paints after substrate work since v1
(2026-05-13):

  - 3 Track C sessions (case_011 v3 chtMR · case_009 v1.5 reacting · case_003 CRM-HLS)
  - 2 new LANDED advisors (A8 shm_dict_validator · A10 thermo_polynomial_range_advisor)
  - A6 unit_detector V96/V97 hardening fix (max_bytes 64KB→1MB · bbox cap 100m→1000m)
  - case_002a M-APU-RESTORE NEGATIVE evidence (V95)
  - V-series corpus 84 → 98 rows (+14 new rows: V85-V98 series)
  - ARC-GOAL #4 e2e numerics class counter: 1/3 → 3/3

Commercial baselines (STAR-CCM+/Fluent/OpenFOAM vanilla) NOT changed — only the
cfd-harness-unified column is re-scored. The v1 capability_radar.png is preserved
unmodified as governance baseline (NOT deleted).

Scores are calibrated against COMMENTARY_V2.md per-cell justifications. The +1.0 /
+0.5 / 0 deltas follow v1.5 SCORE-DELTA's own forecasting criteria — see COMMENTARY_V2
§"Delta vs v1 justification".

Determinism: identical input → identical PNG (matplotlib + Hiragino Sans GB font).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "capability_radar_v2.png"

# Chinese font setup for axis labels (same as v1)
mpl.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

# ────────── Axes (unchanged from v1) ──────────
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
# See COMMENTARY_V2.md for per-cell justification + v1→v2 delta reasoning.
# Commercial baselines unchanged (per hard constraint).

SCORES = {
    # cfd-harness v1: [6, 6, 7, 6, 7, 9, 8, 9]   → left half 6.4 · right half 8.67
    # cfd-harness v2: [7, 6.5, 8, 7, 7, 9, 9, 9.5] → left half 7.1 · right half 9.17
    "cfd-harness-unified": [7.0, 6.5, 8.0, 7.0, 7.0, 9.0, 9.0, 9.5],
    "STAR-CCM+":            [9.0, 9.0, 10.0, 9.0, 9.0, 5.0, 2.0, 6.0],
    "ANSYS Fluent":         [8.0, 8.0, 10.0, 9.0, 8.0, 4.0, 1.0, 5.0],
    "OpenFOAM (vanilla)":   [3.0, 5.0, 9.0, 6.0, 5.0, 9.0, 0.0, 7.0],
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

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(AXES, fontsize=13, fontweight="bold")

    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=9, color="#6b7280")
    ax.grid(True, color="#cbd5e1", linewidth=0.8, linestyle="-", alpha=0.7)
    ax.spines["polar"].set_color("#94a3b8")

    for name, scores in SCORES.items():
        vals = scores + scores[:1]
        color = COLORS[name]
        ls = LINESTYLES[name]
        lw = 3 if name == "cfd-harness-unified" else 1.8
        alpha_fill = 0.22 if name == "cfd-harness-unified" else 0.06
        ax.plot(angles, vals, color=color, linewidth=lw, linestyle=ls,
                label=name, marker="o", markersize=6, zorder=3)
        ax.fill(angles, vals, color=color, alpha=alpha_fill, zorder=2)

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.12),
              ncol=4, fontsize=11, frameon=False)

    fig.suptitle("CFD 工程能力雷达图 v2 · 4-way 对标 (0–10 评分)",
                 fontsize=18, fontweight="bold", y=0.97, color="#1f2937")
    fig.text(0.5, 0.92,
             "cfd-harness-unified 项目能力定位 · 2026-05-14 · post-substrate re-paint",
             ha="center", fontsize=11, color="#6b7280")

    fig.text(0.95, 0.02,
             "cfd-harness-unified v2 · 自我评估 · 见 COMMENTARY_V2.md",
             ha="right", fontsize=8, color="#9ca3af", style="italic")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"✓ {OUT_PNG}")
    print(f"  size: {OUT_PNG.stat().st_size / 1024:.0f} KB")

    # Sanity check half-axis averages (logged for retro audit)
    left = SCORES["cfd-harness-unified"][:5]
    right = SCORES["cfd-harness-unified"][5:]
    print(f"  left half average  (axes 1-5): {sum(left)/len(left):.2f}")
    print(f"  right half average (axes 6-8): {sum(right)/len(right):.2f}")


if __name__ == "__main__":
    main()
