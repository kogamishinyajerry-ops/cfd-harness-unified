#!/usr/bin/env python3
"""Evaluate the §2.4 Option A → B rollback trigger from the .jsonl log.

Reads ``reports/plane_guard/fixture_frame_confusion.jsonl`` and counts
incidents within a rolling 14-day window. If the count is ≥3 the
script exits with code 1 and prints a "ROLLBACK_TRIGGERED" summary;
otherwise it exits 0 with a "OK" summary.

Wired into CI via a weekly cron job (per ADR-002 §2.4 Draft-rev3
minor #2). The rollback itself does not auto-amend ADR-002 — a
human-driven follow-up DEC opens within 1 week of trigger fire,
per the same §2.4 text. This script is the **measurement plumbing**
that makes the trigger visible.

Usage:

    python scripts/plane_guard_rollback_eval.py
    python scripts/plane_guard_rollback_eval.py --window-days 14
    python scripts/plane_guard_rollback_eval.py --threshold 3
    python scripts/plane_guard_rollback_eval.py --log-path /custom/path.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = REPO_ROOT / "reports" / "plane_guard" / "fixture_frame_confusion.jsonl"
DEFAULT_WINDOW_DAYS = 14
DEFAULT_THRESHOLD = 3


def _parse_iso8601(value: str) -> datetime:
    """Parse the ``"%Y-%m-%dT%H:%M:%SZ"`` format the writer emits."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )


def _load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # Malformed line — skip rather than crash.
        if "timestamp" not in event:
            continue
        events.append(event)
    return events


def evaluate(
    *,
    log_path: Path = DEFAULT_LOG_PATH,
    window_days: int = DEFAULT_WINDOW_DAYS,
    threshold: int = DEFAULT_THRESHOLD,
    now: datetime | None = None,
) -> tuple[bool, int, list[dict]]:
    """Return ``(triggered, count, events_in_window)``.

    ``triggered`` is True when ``count >= threshold``. ``now``
    overrides the current time for testability.
    """
    events = _load_events(log_path)
    now_dt = now or datetime.now(timezone.utc)
    cutoff = now_dt - timedelta(days=window_days)
    in_window: list[dict] = []
    for event in events:
        try:
            ts = _parse_iso8601(event["timestamp"])
        except (ValueError, KeyError):
            continue
        if ts >= cutoff:
            in_window.append(event)
    return (len(in_window) >= threshold, len(in_window), in_window)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    parser.add_argument(
        "--log-path",
        default=str(DEFAULT_LOG_PATH),
        help="Path to fixture_frame_confusion.jsonl (default: repo path)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Rolling window length in days (default: {DEFAULT_WINDOW_DAYS})",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=f"Trigger threshold (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    triggered, count, events = evaluate(
        log_path=Path(args.log_path),
        window_days=args.window_days,
        threshold=args.threshold,
    )
    if triggered:
        print(
            f"ROLLBACK_TRIGGERED: {count} fixture-frame confusion incidents "
            f"in last {args.window_days}d ≥ threshold {args.threshold}"
        )
        for event in events:
            print(f"  - {event.get('timestamp')} {event.get('test_path')}")
        return 1
    print(
        f"OK: {count} fixture-frame confusion incidents in last "
        f"{args.window_days}d (threshold {args.threshold})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
