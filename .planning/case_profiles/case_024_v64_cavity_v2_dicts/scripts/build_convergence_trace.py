#!/usr/bin/env python3
"""Extract sparse convergence trace from simpleFoam log.

Reads log.simpleFoam, emits checkpoints at iter 10, 100, 500, 1000, 3000,
final-500, final. For each: Ux_init, Uy_init, p_init, continuity-sum-local.

Q1 LLM-offline: pure stdlib.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def parse_log(log_path: Path) -> list[dict]:
    iters: list[dict] = []
    current: dict = {}
    with log_path.open() as f:
        for line in f:
            m = re.match(r"^Time = (\d+)$", line)
            if m:
                if current.get("iter") is not None:
                    iters.append(current)
                current = {"iter": int(m.group(1))}
            else:
                m_ux = re.search(r"Solving for Ux, Initial residual = ([\d.eE+-]+),", line)
                if m_ux:
                    current["Ux_init"] = float(m_ux.group(1))
                m_uy = re.search(r"Solving for Uy, Initial residual = ([\d.eE+-]+),", line)
                if m_uy:
                    current["Uy_init"] = float(m_uy.group(1))
                m_p = re.search(r"Solving for p, Initial residual = ([\d.eE+-]+),", line)
                if m_p:
                    current["p_init"] = float(m_p.group(1))
                m_cont = re.search(r"sum local = ([\d.eE+-]+),", line)
                if m_cont:
                    current["cont_local"] = float(m_cont.group(1))
        if current.get("iter") is not None:
            iters.append(current)
    return iters


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    iters = parse_log(args.log)
    if not iters:
        print("no iterations parsed", file=sys.stderr)
        return 1

    final_iter = iters[-1]["iter"]
    checkpoint_iters = [10, 100, 500, 1000, 3000, 5000, max(1, final_iter - 500), final_iter]
    checkpoint_iters = sorted(set(c for c in checkpoint_iters if c <= final_iter))

    by_iter = {it["iter"]: it for it in iters}

    lines = [f"   iter   Ux_init    Uy_init    p_init     cont_local"]
    for ci in checkpoint_iters:
        # find nearest iter <= ci
        rec = by_iter.get(ci)
        if rec is None:
            cand = [k for k in by_iter if k <= ci]
            if cand:
                rec = by_iter[max(cand)]
            else:
                continue
        lines.append(
            f"  {rec['iter']:5d}  "
            f"{rec.get('Ux_init', float('nan')):.2e}  "
            f"{rec.get('Uy_init', float('nan')):.2e}  "
            f"{rec.get('p_init', float('nan')):.2e}  "
            f"{rec.get('cont_local', float('nan')):.2e}"
        )

    out = "\n".join(lines) + "\n"
    args.out.write_text(out)
    print(out)
    print(f"final iter = {final_iter}, wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
