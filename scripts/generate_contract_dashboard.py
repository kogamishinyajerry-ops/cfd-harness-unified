#!/usr/bin/env python3
"""Generate the single-file 10-case contract dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.report_engine.contract_dashboard import (  # noqa: E402
    DEFAULT_OUTPUT_PATH,
    ContractDashboardGenerator,
)


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        print("ERROR: contract dashboard CLI does not accept case_ids; it always renders the 10-case canonical view.", file=sys.stderr)
        return 2

    result = ContractDashboardGenerator().generate()
    print(
        "OK    contract_dashboard"
        f"  canonical={result.output_path or DEFAULT_OUTPUT_PATH}"
        f"  snapshot={result.snapshot_path}"
        f"  manifest={result.manifest_path}"
        f"  head={result.head_sha}"
        f"  cases={result.case_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
