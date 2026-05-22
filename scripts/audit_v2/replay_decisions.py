"""DEC-V61-202-SUB-M30-CYCLE6 · replay decide() provenance log.

Reads a case's `decisions.jsonl` and prints a chronological table of
what the workbench surfaced. Use this to retro "engineer Y saw the
workbench tell them X at time T — was that right?"

Usage:
    python3 scripts/audit_v2/replay_decisions.py <case_id> [--limit N]
    python3 scripts/audit_v2/replay_decisions.py <case_id> --field rail_primary.title

If --field is omitted, prints a default compact view: timestamp |
step | focus_patch | rail.kind | rail.title | topbar.kind | cards.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ui.backend.services.workbench_decide_provenance import (
    AUDIT_V2_DIR,
    _safe_case_id,
)


def _get_field(obj: dict, dotted: str):
    """Walk a dotted path through a nested dict; return None on miss."""
    cur = obj
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_id", help="Case ID (will be sanitized)")
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Only show the last N entries (0 = all)",
    )
    parser.add_argument(
        "--field", type=str, default=None,
        help="Dotted field path to extract per line (e.g. rail_primary.title)",
    )
    parser.add_argument(
        "--audit-dir", type=Path, default=AUDIT_V2_DIR,
        help="Override audit_v2 root (default: ui/backend/user_drafts/audit_v2)",
    )
    args = parser.parse_args()

    case_dir = args.audit_dir / _safe_case_id(args.case_id)
    log_path = case_dir / "decisions.jsonl"
    if not log_path.exists():
        print(f"No log at {log_path}", file=sys.stderr)
        return 1

    lines = []
    for raw in log_path.read_text().splitlines():
        if not raw.strip():
            continue
        try:
            lines.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            print(f"# WARNING: skipped invalid JSON line: {exc}", file=sys.stderr)

    if args.limit > 0:
        lines = lines[-args.limit :]

    if args.field:
        for rec in lines:
            ts = rec.get("timestamp", "?")
            val = _get_field(rec, args.field)
            print(f"{ts}  {args.field}={val!r}")
    else:
        # Default compact view.
        header = (
            "TIMESTAMP                      | STEP | FOCUS    | RAIL.KIND     | "
            "RAIL.TITLE                                    | TOPBAR.KIND   | CARDS"
        )
        print(header)
        print("-" * len(header))
        for rec in lines:
            ts = rec.get("timestamp", "?")[:30]
            step = rec.get("step", "?")
            focus = (rec.get("focus_patch") or "-")[:8]
            rail = rec.get("rail_primary") or {}
            r_kind = (rail.get("kind") or "-")[:13]
            r_title = (rail.get("title") or "-")[:44]
            topbar = rec.get("topbar_cta") or {}
            t_kind = (topbar.get("kind") or "-")[:13]
            cards = rec.get("bottom_card_count", 0)
            print(
                f"{ts:<30} | {step:<4} | {focus:<8} | {r_kind:<13} | "
                f"{r_title:<44} | {t_kind:<13} | {cards}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
