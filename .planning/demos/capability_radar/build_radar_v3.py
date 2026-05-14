"""
Build capability radar v3: cfd-harness-unified vs STAR-CCM+ vs Fluent vs OpenFOAM vanilla.

v3 is the post-B20 (A8 widening) re-paint. Triggered by:

  - DEC-V61-198-sub-A8-widening-V99-V100 landed 2026-05-14 (commit 9a0b8cc)
  - shm_dict_validator: 5 → 7 detection paths (+196 / -13 LOC, 13 tests green)
  - V99 + V100 status [QUESTIONABLE] → [VALIDATED] (双 corpus)
  - V-series 98 → 100 rows (M-V100 closed 2026-05-14, commit b1303d2)

Score judgment call (transparent · see COMMENTARY_V3.md §"v3 vs v2 delta"):

  Mesh axis 6.5 → 6.75 (NOT 7.0): A8 widening earns +0.25 for coverage breadth
  expansion (V99 multi-normal constrained patch class + V100 entry-point type-guard),
  NOT the +0.5 that COMMENTARY_V2 forecasted as gap-close path. Reason: COMMENTARY_V2's
  +0.5 bar was "evidence that mesh-debug-loop reduces below v1.5's ≤3-iter on new
  case". B20 widening adds detection paths BUT does not yet have post-land case
  evidence demonstrating debug-loop reduction. Honest scoring per arc culture
  (M-APU-RESTORE CLOSED NEGATIVE honesty precedent).

Commercial baselines unchanged.

Determinism: identical input → identical PNG.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "capability_radar_v3.png"

mpl.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS']
mpl.rcParams['axes.unicode_minus'] = False

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

SCORES = {
    # cfd-harness v1:   [6,   6,   7,   6,   7,   9,   8,   9  ]   → left 6.40 · right 8.67
    # cfd-harness v2:   [7,   6.5, 8,   7,   7,   9,   9,   9.5]   → left 7.10 · right 9.17
    # cfd-harness v3:   [7,   6.75,8,   7,   7,   9,   9,   9.5]   → left 7.15 · right 9.17
    "cfd-harness-unified": [7.0, 6.75, 8.0, 7.0, 7.0, 9.0, 9.0, 9.5],
    "STAR-CCM+":            [9.0, 9.0, 10.0, 9.0, 9.0, 5.0, 2.0, 6.0],
    "ANSYS Fluent":         [8.0, 8.0, 10.0, 9.0, 8.0, 4.0, 1.0, 5.0],
    "OpenFOAM (vanilla)":   [3.0, 5.0, 9.0, 6.0, 5.0, 9.0, 0.0, 7.0],
}

COLORS = {
    "cfd-harness-unified": "#3b82f6",
    "STAR-CCM+":            "#ef4444",
    "ANSYS Fluent":         "#a855f7",
    "OpenFOAM (vanilla)":   "#10b981",
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
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(13, 11), subplot_kw=dict(polar=True), facecolor="#f8f9fb")
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

    fig.suptitle("CFD 工程能力雷达图 v3 · post-A8-widening 重画",
                 fontsize=18, fontweight="bold", y=0.97, color="#1f2937")
    fig.text(0.5, 0.92,
             "cfd-harness-unified · 2026-05-14 · A8 widening (V99+V100) post-land verification",
             ha="center", fontsize=11, color="#6b7280")

    fig.text(0.95, 0.02,
             "cfd-harness-unified v3 · 自我评估 · 见 COMMENTARY_V3.md",
             ha="right", fontsize=8, color="#9ca3af", style="italic")

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"✓ {OUT_PNG}")
    print(f"  size: {OUT_PNG.stat().st_size / 1024:.0f} KB")

    left = SCORES["cfd-harness-unified"][:5]
    right = SCORES["cfd-harness-unified"][5:]
    left_avg = sum(left)/len(left)
    right_avg = sum(right)/len(right)
    print(f"  left half average  (axes 1-5): {left_avg:.2f}")
    print(f"  right half average (axes 6-8): {right_avg:.2f}")
    print(f"  Done dim 5 (left ≥ 7.2): {'MET ✓' if left_avg >= 7.2 else f'NOT MET · gap {7.2-left_avg:.2f}'}")
    print(f"  Done dim 6 (right ≥ 8.7): {'MET ✓' if right_avg >= 8.7 else f'NOT MET · gap {8.7-right_avg:.2f}'}")


if __name__ == "__main__":
    main()
