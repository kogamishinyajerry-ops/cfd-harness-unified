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


def _dedup_key(event: dict) -> tuple:
    """4-tuple dedup key for a fixture-frame confusion incident.

    Authority: Notion Opus 4.7 OPS audit 2026-04-25T16:30 (verdict
    ACCEPT_WITH_COMMENTS direction 4 P0). Without dedup, a single
    real plane-crossing incident can be written 2-3 times per CI
    run via finder re-entry across pytest collection: same forbidden
    transition triggers ``record_fixture_frame_confusion()`` once
    per ``find_spec()`` invocation, which is invoked once per
    ``import`` statement evaluation, which can repeat across test
    files importing overlapping modules. The 14-day rolling-window
    threshold ≥3 (§2.4) would then fire on what is actually 1 real
    incident replayed 3 times — false-positive rollback trigger
    builds the rollback decision on noise, not signal.

    Group key is ``(test_path, source_module, target_module,
    contract_name)`` — the smallest tuple that uniquely identifies
    a kind of forbidden plane transition from a particular test
    context. Stack snippets / incident_id / timestamps differ
    between repeats; the 4-tuple is the stable identity.
    """
    return (
        event.get("test_path", ""),
        event.get("source_module", ""),
        event.get("target_module", ""),
        event.get("contract_name", ""),
    )


def _dedup_events(events: list[dict]) -> list[dict]:
    """Keep the earliest event per 4-tuple key (stable order preserved)."""
    seen: dict[tuple, dict] = {}
    for event in events:
        key = _dedup_key(event)
        if key not in seen:
            seen[key] = event
    return list(seen.values())


def evaluate(
    *,
    log_path: Path = DEFAULT_LOG_PATH,
    window_days: int = DEFAULT_WINDOW_DAYS,
    threshold: int = DEFAULT_THRESHOLD,
    now: datetime | None = None,
    dedup: bool = True,
) -> tuple[bool, int, list[dict], int]:
    """Return ``(triggered, count, events_in_window, raw_count)``.

    ``triggered`` is True when ``count >= threshold``. ``count`` is
    the post-dedup count (i.e., unique 4-tuples) when ``dedup=True``
    (default), or the raw line count otherwise. ``raw_count`` is
    always the pre-dedup line count for diagnostic visibility.
    ``now`` overrides the current time for testability.
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
    raw_count = len(in_window)
    if dedup:
        in_window = _dedup_events(in_window)
    return (len(in_window) >= threshold, len(in_window), in_window, raw_count)


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
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help=(
            "Disable 4-tuple dedup (test_path, source_module, target_module, "
            "contract_name). Default is dedup=ON per Opus 4.7 §3 v2 ACCEPT_"
            "WITH_COMMENTS direction 4 — finder re-entry across pytest "
            "collection inflates the same incident 2-3x and would trip the "
            "§2.4 ≥3 threshold on noise. --no-dedup retained for diagnostic "
            "purposes (e.g., comparing raw vs deduped counts)."
        ),
    )
    args = parser.parse_args()

    triggered, count, events, raw_count = evaluate(
        log_path=Path(args.log_path),
        window_days=args.window_days,
        threshold=args.threshold,
        dedup=not args.no_dedup,
    )
    mode = "raw (--no-dedup)" if args.no_dedup else "dedup-by-4-tuple"
    if triggered:
        print(
            f"ROLLBACK_TRIGGERED: {count} fixture-frame confusion incidents "
            f"in last {args.window_days}d ≥ threshold {args.threshold} "
            f"[{mode}; raw lines={raw_count}]"
        )
        for event in events:
            print(
                f"  - {event.get('timestamp')} test={event.get('test_path')} "
                f"src={event.get('source_module')} → "
                f"tgt={event.get('target_module')} "
                f"contract={event.get('contract_name')}"
            )
        return 1
    print(
        f"OK: {count} fixture-frame confusion incidents in last "
        f"{args.window_days}d (threshold {args.threshold}) "
        f"[{mode}; raw lines={raw_count}]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
