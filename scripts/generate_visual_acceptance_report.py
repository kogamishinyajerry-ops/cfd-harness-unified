#!/usr/bin/env python3
"""Generate the single-file visual acceptance report."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.report_engine.visual_acceptance import (  # noqa: E402
    DEFAULT_CASE_IDS,
    DEFAULT_OUTPUT_PATH,
    VisualAcceptanceReportGenerator,
)


def main(argv: list[str]) -> int:
    requested = tuple(argv[1:]) if len(argv) > 1 else DEFAULT_CASE_IDS
    unknown = sorted(set(requested) - set(DEFAULT_CASE_IDS))
    if unknown:
        print(f"ERROR: unsupported visual case_ids: {unknown}", file=sys.stderr)
        print(f"supported: {list(DEFAULT_CASE_IDS)}", file=sys.stderr)
        return 2

    result = VisualAcceptanceReportGenerator().generate(case_ids=requested)
    print(
        "OK    visual_acceptance_report"
        f"  -> {result.output_path or DEFAULT_OUTPUT_PATH}"
        f"  cases={result.case_count}"
        f" charts={result.chart_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
