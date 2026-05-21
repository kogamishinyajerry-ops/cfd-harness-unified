"""Generate residual_plot.png for case_021 NASA TMR flat plate.

Reads ../../../_sandboxes/case_021_nasa_tmr_flat_plate/case_v65/artifacts/residuals.csv
and plots all parsed residual columns on log scale vs iteration.

Run:  python3 residual_plot.py
Output: residual_plot.png in this directory.

Caveat: at the time of capture, the parsed residuals.csv contains only `p`.
This is itself a parser-coverage discussion point in the demo — manifest
declares Ux/Uy/Uz/p but the simpleFoam log emitted via the v65 dataset path
appears to surface only `p` to the regex. Honesty fence at work.
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
    "case_021_nasa_tmr_flat_plate/case_v65/artifacts/residuals.csv"
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
        "case_021 NASA TMR flat plate  ·  RANS k-ω SST",
        fontsize=11,
    )
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right", fontsize=9)
    ax.text(
        0.02, 0.04,
        "parser surfaced fields = " + ", ".join(cols.keys()),
        transform=ax.transAxes, fontsize=8, color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
