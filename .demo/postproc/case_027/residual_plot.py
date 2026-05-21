"""Generate residual_plot.png for case_027 Hagen-Poiseuille pipe.

Reads ../../../_sandboxes/case_027_hagen_poiseuille_pipe/case_v65/artifacts/residuals.csv
(produced by cfdtrust ingest from log_simpleFoam.txt) and plots all residual
columns on log-scale vs iteration.

Run:  python3 residual_plot.py
Output: residual_plot.png in this directory.
"""
from __future__ import annotations
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESID = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_027_hagen_poiseuille_pipe/case_v65/artifacts/residuals.csv"
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
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    for name, ys in cols.items():
        ax.semilogy(iters, ys, label=name, linewidth=1.2)
    ax.set_xlabel("simpleFoam iteration")
    ax.set_ylabel("Initial residual (log scale)")
    ax.set_title(
        "case_027 Hagen-Poiseuille  ·  6-gate ingest verified",
        fontsize=11,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
