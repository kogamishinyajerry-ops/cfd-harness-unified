#!/usr/bin/env python3
"""Cycle-2 residual plot for case_011 plate-fin CHT.

Reads the real residuals.csv produced by the cycle-2 re-dogfood of
case_011 (TBD-15 + TBD-20 + multi-region parser + streaming parser all
landed).  The cycle-1 run produced 1 field (p_rgh only) because the
DILUPBiCGStab regex was blind to Ux/Uy/Uz and the text-path parser
couldn't keep up with multi-region log line shapes.  Cycle-2 lights up
all five solved fields.

Real data source:
  ~/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/
      case/artifacts/residuals.csv   (13714 bytes · 5 fields × 200 iter)

Output: .demo/postproc/case_011/residual_plot_cycle2.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

CSV_PATH = Path(
    "/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/"
    "case_011_plate_fin_compact_hx/case/artifacts/residuals.csv"
)
OUT_PATH = Path(__file__).with_name("residual_plot_cycle2.png")

assert CSV_PATH.exists(), f"missing real residual data: {CSV_PATH}"

with CSV_PATH.open() as f:
    rd = csv.reader(f)
    header = next(rd)
    rows = [list(map(float, r)) for r in rd]

cols = {name: [r[i] for r in rows] for i, name in enumerate(header)}
iters = cols["iter"]
fields = [c for c in header if c != "iter"]
assert fields, "no residual fields found"

fig, ax = plt.subplots(figsize=(10, 5.2), dpi=160)
fig.patch.set_facecolor("#0a1428")
ax.set_facecolor("#0a1428")

colors = {
    "Ux": "#6ec1e4",
    "Uy": "#8fd3c7",
    "Uz": "#a5c882",
    "h":  "#f0c674",
    "p_rgh": "#ff6b6b",
}
for field in fields:
    ax.semilogy(iters, cols[field], label=field,
                color=colors.get(field, "#cccccc"),
                linewidth=1.8, alpha=0.95)

# residual target band (the manifest target for chtMultiRegionSimpleFoam)
ax.axhspan(0, 1e-3, alpha=0.08, color="#a5c882",
           label="residual target (1e-3)")
ax.axhline(1e-3, color="#a5c882", linestyle="--", linewidth=0.8,
           alpha=0.7)

ax.set_xlabel("iteration", color="#cccccc", fontsize=11)
ax.set_ylabel("normalized residual (log)", color="#cccccc", fontsize=11)
ax.set_title(
    "case_011 plate-fin CHT · cycle-2 · "
    "chtMultiRegionSimpleFoam · 5 fields tracked",
    color="#f0c674", fontsize=13, pad=10, weight="bold",
)
ax.tick_params(colors="#cccccc")
for spine in ax.spines.values():
    spine.set_color("#3a4a60")
ax.grid(True, which="both", linestyle=":", color="#2a3a50", alpha=0.6)
leg = ax.legend(loc="upper right", facecolor="#0a1428",
                edgecolor="#3a4a60", labelcolor="#e0e0e0",
                fontsize=10)
for txt in leg.get_texts():
    txt.set_color("#e0e0e0")

# annotation: cycle-1 vs cycle-2 payoff
ax.annotate(
    "cycle-1: 1/1 field tracked\n"
    "cycle-2: 5/5 fields tracked\n"
    "(TBD-15 reacting log fallback + TBD-20 streaming\n"
    "+ DILUPBiCGStab regex coverage)",
    xy=(140, 8e-2),
    xycoords="data",
    color="#f0c674",
    fontsize=9.5,
    ha="left",
    bbox=dict(boxstyle="round,pad=0.5", fc="#16223a", ec="#f0c674",
              lw=1.0, alpha=0.92),
)

# header strap with source provenance
fig.text(0.01, 0.97,
         f"source: {CSV_PATH.name}  "
         f"({CSV_PATH.stat().st_size} bytes · {len(rows)} iter · "
         f"{len(fields)} fields)",
         color="#888a99", fontsize=8.5, family="monospace")
fig.text(0.99, 0.97,
         "ingested · honest BLOCKED on multi-region verdict layer",
         color="#888a99", fontsize=8.5, family="monospace",
         ha="right")

plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(OUT_PATH, facecolor=fig.get_facecolor(),
            edgecolor="none", bbox_inches="tight")
print(f"[postproc] wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
