"""Generate residual_plot.png for case_009 Sandia Flame D.

Hero plot for the demo: the engine declared 27 residual targets in the
case manifest (Ux/Uy/Uz/p/h/k/epsilon + 20 DRM-19 species). The
pre-TBD-17 solver_gate.json captured only 3 checked_fields (Ux/Uy/Uz)
and silently PASSed. After commit 3b5c43f the ingest path BLOCKS with
incomplete_residual_coverage + the explicit missing_target_fields list.

This script plots whatever columns the *current* residuals.csv contains
(typically 26 columns — DRM-19 species merged via CH2(S) -> CH2
collision per the TBD-19 patch) and annotates the historical bug.

Run:  python3 residual_plot.py
Output: residual_plot.png in this directory.
"""
from __future__ import annotations
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESID = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_009_sandia_flame_d/case/artifacts/residuals.csv"
)
OUT = HERE / "residual_plot.png"


def load_residuals(p: Path) -> tuple[list[int], dict[str, list[float]]]:
    with p.open() as f:
        rdr = csv.reader(f)
        header = next(rdr)
        iters: list[int] = []
        cols: dict[str, list[float]] = {h: [] for h in header[1:]}
        for row in rdr:
            iters.append(int(row[0]))
            for h, v in zip(header[1:], row[1:]):
                try:
                    cols[h].append(float(v))
                except ValueError:
                    cols[h].append(float("nan"))
        return iters, cols


def main() -> None:
    iters, cols = load_residuals(RESID)
    fig, ax = plt.subplots(figsize=(9.5, 5.0), dpi=140)
    for name, ys in cols.items():
        ax.semilogy(iters, ys, label=name, linewidth=0.9)
    ax.set_xlabel("reactingFoam iteration")
    ax.set_ylabel("Initial residual (log scale)")
    ax.set_title(
        "case_009 Sandia Flame D  ·  sub-gate honesty bug self-discovery",
        fontsize=11,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5),
              fontsize=7, ncol=2, frameon=False)
    ax.text(
        0.01, 0.97,
        ("MANIFEST DECLARED 27 FIELDS\n"
         f"PARSER FOUND {len(cols)}\n"
         "TBD-17 surface fixed in commit 3b5c43f"),
        transform=ax.transAxes, fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4",
                  facecolor="lightyellow", edgecolor="goldenrod"),
    )
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
