"""Structured friction log for B-arc dogfood runs.

Writes one JSONL file per run (`friction_log.jsonl`). Each line is a
typed event documenting one observable step of the persona's run:
HTTP call, advisor query, decision/rationale, drop (skipped step),
verdict, error, tool_use, budget_check.

Schema is flat-object intentionally — easy to parse, easy to grep
(B.4 retro greps for V130 violation patterns).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

EVENT_TYPES = (
    "api_call",
    "advisor_query",
    "decision",
    "drop",
    "verdict",
    "error",
    "tool_use",
    "budget_check",
)


@dataclass
class FrictionLog:
    """JSONL friction log writer.

    Open a writer for the duration of one run; flush after each event
    so a crash leaves a partial-but-valid log on disk.
    """

    path: Path
    run_id: str
    case_id: str
    persona: str
    model_id: str
    _fh: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")
        self._emit(
            "run_start",
            run_id=self.run_id,
            case_id=self.case_id,
            persona=self.persona,
            model_id=self.model_id,
        )

    def emit(self, event_type: str, **payload: Any) -> None:
        if event_type not in EVENT_TYPES and event_type not in {"run_start", "run_end"}:
            raise ValueError(
                f"Unknown event_type {event_type!r}; allowed: {EVENT_TYPES}"
            )
        self._emit(event_type, **payload)

    def _emit(self, event_type: str, **payload: Any) -> None:
        record = {
            "ts": time.time(),
            "event_type": event_type,
            "run_id": self.run_id,
            **payload,
        }
        self._fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        self._fh.write("\n")
        self._fh.flush()
        try:
            os.fsync(self._fh.fileno())
        except OSError:
            pass

    def close(self, *, final_status: str = "complete") -> None:
        if self._fh is None:
            return
        self._emit("run_end", final_status=final_status)
        self._fh.close()
        self._fh = None

    def __enter__(self) -> "FrictionLog":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        status = "complete" if exc is None else f"error:{exc_type.__name__}"
        self.close(final_status=status)


def read_log(path: Path) -> list[dict[str, Any]]:
    """Replay helper for tests + B.4 retro analysis."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def grep_events(events: Iterable[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event_type") == event_type]


__all__ = ["EVENT_TYPES", "FrictionLog", "grep_events", "read_log"]
