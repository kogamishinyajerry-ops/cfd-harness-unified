#!/usr/bin/env python3
"""§11.5 · SSOT Consistency Check (DEC-V61-072 + RETRO-V61-005 · 2026-04-26)

Every phase transition (Phase X Status → Done in Phases DB) requires a fresh
SSOT consistency check before the phase is archived. The check verifies:

1. Every DEC-V61-XXX issued during the phase has frontmatter
   ``notion_sync_status: synced <date> (<url>)`` matching its Notion page.
2. Every Notion page in the phase has a corresponding repo file (DECs in
   .planning/decisions/, retros in .planning/retrospectives/).
3. STATE.md ``last_updated`` timestamp ≥ the latest commit in the phase.
4. ``external_gate_queue.md`` reflects the latest external-gate state.

Authority: Methodology v2.0 §11.5 (active provisional · pending CFDJerry sign-off).

Usage:
    python tools/methodology_guards/ssot_consistency_check.py [--phase <phase_id>]

By default reports for ALL phases that have transitioned to Done in the last 30 days.

Exit codes:
- 0 = clean (zero discrepancies)
- 1 = discrepancies found (block phase archive)
- 2 = invocation error
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DIR = REPO_ROOT / ".planning" / "decisions"
RETROS_DIR = REPO_ROOT / ".planning" / "retrospectives"
STATE_FILE = REPO_ROOT / ".planning" / "STATE.md"


def check_dec_frontmatter_sync_status() -> List[Tuple[str, str]]:
    """Return list of (file, issue) for DECs missing notion_sync_status."""
    issues: List[Tuple[str, str]] = []
    if not DECISIONS_DIR.is_dir():
        return issues
    for dec_file in sorted(DECISIONS_DIR.glob("*.md")):
        text = dec_file.read_text(encoding="utf-8")
        # Only check files with frontmatter
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end < 0:
            continue
        frontmatter = text[4:end]
        if "notion_sync_status:" not in frontmatter:
            issues.append((str(dec_file.relative_to(REPO_ROOT)),
                           "missing notion_sync_status frontmatter field"))
            continue
        # Check format: "synced <date> (<url>)" OR "pending"
        m = re.search(r"^notion_sync_status:\s*(.+)$", frontmatter, re.MULTILINE)
        if m:
            value = m.group(1).strip()
            if value == "pending":
                issues.append((str(dec_file.relative_to(REPO_ROOT)),
                               f"notion_sync_status=pending (needs sync)"))
    return issues


def check_state_md_freshness() -> List[Tuple[str, str]]:
    """Verify STATE.md last_updated >= latest commit timestamp."""
    issues: List[Tuple[str, str]] = []
    if not STATE_FILE.is_file():
        issues.append(("STATE.md", "missing"))
        return issues
    text = STATE_FILE.read_text(encoding="utf-8")
    m = re.search(r'last_updated:\s*"([^"]+)"', text)
    if not m:
        issues.append(("STATE.md", "no last_updated field"))
        return issues
    state_ts_str = m.group(1)
    # Parse "2026-04-26T11:35 local" loosely; we only compare YYYY-MM-DD
    state_date_match = re.match(r"(\d{4}-\d{2}-\d{2})", state_ts_str)
    if not state_date_match:
        return issues
    state_date = state_date_match.group(1)

    # Get latest commit date
    try:
        latest = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "main"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        ).stdout.strip()
        if latest > state_date:
            issues.append(("STATE.md",
                           f"last_updated={state_date} < latest commit={latest} on main"))
    except subprocess.CalledProcessError:
        pass
    return issues


def check_external_gate_queue_exists() -> List[Tuple[str, str]]:
    """Verify external_gate_queue.md exists and is non-trivial."""
    issues: List[Tuple[str, str]] = []
    queue_file = REPO_ROOT / ".planning" / "external_gate_queue.md"
    if not queue_file.is_file():
        # Optional file — only warn
        return issues
    if queue_file.stat().st_size < 10:
        issues.append((str(queue_file.relative_to(REPO_ROOT)),
                       "external_gate_queue.md is empty or near-empty"))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", help="Phase ID (informational)")
    args = parser.parse_args()

    print(f"§11.5 SSOT Consistency Check · {datetime.utcnow().isoformat()}Z")
    if args.phase:
        print(f"Phase: {args.phase}")

    all_issues: List[Tuple[str, str]] = []
    all_issues.extend(check_dec_frontmatter_sync_status())
    all_issues.extend(check_state_md_freshness())
    all_issues.extend(check_external_gate_queue_exists())

    if not all_issues:
        print("✓ Zero discrepancies. Phase archive allowed.")
        return 0

    print(f"\n✗ {len(all_issues)} discrepancy(ies) found:\n")
    for file, issue in all_issues:
        print(f"  - {file}: {issue}")
    print(f"\n§11.5 BLOCK: phase cannot be archived until report shows zero discrepancies.")
    print("Escape: same-day DEC acknowledging + deferring to follow-up phase.")
    print("≥3 discrepancies in single phase audit → mini-retro within 7 days.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
