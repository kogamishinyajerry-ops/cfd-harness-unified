#!/usr/bin/env python3
"""Batch-generate case reports via Report Engine.

Usage:
    python scripts/generate_reports.py               # all supported cases with evidence
    python scripts/generate_reports.py CASE_ID ...   # specific cases

Skips cases whose auto_verify_report.yaml is missing (prints WARN line).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.report_engine.generator import REPORTS_ROOT, SUPPORTED_CASE_IDS, ReportGenerator


def main(argv: list[str]) -> int:
    requested = argv[1:] if len(argv) > 1 else sorted(SUPPORTED_CASE_IDS)
    unknown = [cid for cid in requested if cid not in SUPPORTED_CASE_IDS]
    if unknown:
        print(f"ERROR: unsupported case_ids: {unknown}", file=sys.stderr)
        print(f"supported: {sorted(SUPPORTED_CASE_IDS)}", file=sys.stderr)
        return 2

    generator = ReportGenerator()
    rendered = skipped = 0
    for case_id in requested:
        verify_path = REPORTS_ROOT / case_id / "auto_verify_report.yaml"
        if not verify_path.exists():
            print(f"SKIP  {case_id}  (missing {verify_path.relative_to(REPO_ROOT)})")
            skipped += 1
            continue
        try:
            result = generator.generate(case_id)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {case_id}  ({type(exc).__name__}: {exc})")
            skipped += 1
            continue
        output = result.output_path or "-"
        warnings = f" warnings={result.warnings}" if result.warnings else ""
        print(f"OK    {case_id}  -> {output}  sections={result.section_count}{warnings}")
        rendered += 1

    print(f"\nRendered {rendered} / {len(requested)} (skipped {skipped})")
    return 0 if rendered > 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
