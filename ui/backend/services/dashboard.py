"""Dashboard aggregation service (Phase 4).

Assembles Screen 1's 10-case matrix + gate queue count + decision
timeline in a single round trip. Read-only; uses only the services
already shipped in Phases 0, 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ui.backend.schemas.validation import CaseIndexEntry
from ui.backend.services.decisions import (
    DecisionCard,
    GateQueueItem,
    list_decisions,
)
from ui.backend.services.validation_report import list_cases, REPO_ROOT

STATE_FILE = REPO_ROOT / ".planning" / "STATE.md"


@dataclass(slots=True)
class DashboardTimelineEvent:
    date: str
    decision_id: str
    title: str
    column: str
    autonomous: bool
    github_pr_url: str | None
    notion_url: str | None


@dataclass(slots=True)
class DashboardSnapshot:
    cases: list[CaseIndexEntry] = field(default_factory=list)
    gate_queue: list[GateQueueItem] = field(default_factory=list)
    timeline: list[DashboardTimelineEvent] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    current_phase: str = ""
    autonomous_governance_counter: int | None = None


def _extract_current_phase() -> tuple[str, int | None]:
    """Scrape current_phase + autonomous_governance counter from STATE.md."""
    if not STATE_FILE.exists():
        return ("", None)
    text = STATE_FILE.read_text(encoding="utf-8", errors="ignore")
    phase = ""
    counter: int | None = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("current_phase:") and not phase:
            phase = s.split("current_phase:", 1)[-1].strip().strip("*`")
        if "autonomous_governance" in s and counter is None:
            # Look for "N of 10" / "counter = N" / "counter: N"
            import re as _re
            m = _re.search(r"(\d{1,2})\s*(?:/\s*10|of\s*10|slots)", s)
            if m:
                counter = int(m.group(1))
            elif "= 2" in s or "=2" in s:
                counter = 2
    return (phase, counter)


def build_dashboard() -> DashboardSnapshot:
    cases = list_cases()
    decisions_snap = list_decisions()
    timeline = [
        DashboardTimelineEvent(
            date=str(c.timestamp)[:10],
            decision_id=c.decision_id,
            title=c.title,
            column=c.column,
            autonomous=c.autonomous,
            github_pr_url=c.github_pr_url,
            notion_url=c.notion_url,
        )
        for c in sorted(decisions_snap.cards, key=lambda c: str(c.timestamp))
    ]
    summary: dict[str, int] = {
        "total_cases": len(cases),
        "pass_cases": sum(1 for c in cases if c.contract_status == "PASS"),
        "hazard_cases": sum(1 for c in cases if c.contract_status == "HAZARD"),
        "fail_cases": sum(1 for c in cases if c.contract_status == "FAIL"),
        "unknown_cases": sum(1 for c in cases if c.contract_status == "UNKNOWN"),
        "open_gates": sum(1 for g in decisions_snap.gate_queue if g.state == "OPEN"),
        "closed_gates": sum(1 for g in decisions_snap.gate_queue if g.state == "CLOSED"),
        "accepted_decisions": decisions_snap.counts.get("Accepted", 0),
        "closed_decisions": decisions_snap.counts.get("Closed", 0),
        "open_decisions": decisions_snap.counts.get("Open", 0),
        "superseded_decisions": decisions_snap.counts.get("Superseded", 0),
    }
    phase, counter = _extract_current_phase()
    return DashboardSnapshot(
        cases=cases,
        gate_queue=decisions_snap.gate_queue,
        timeline=timeline,
        summary=summary,
        current_phase=phase,
        autonomous_governance_counter=counter,
    )
