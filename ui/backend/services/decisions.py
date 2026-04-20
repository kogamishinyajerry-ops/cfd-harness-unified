"""Decisions Queue backing service (Phase 2).

Reads ``.planning/decisions/*.md`` YAML frontmatter and the external
gate queue to produce Kanban-column cards for the UI. Read-only in
Phase 2 — creating new decisions is a Phase 5 / external-Gate concern.

Column derivation rules:

    Accepted    → ``notion_sync_status`` starts with 'synced' AND
                  no ``superseded_by`` field.
    Closed      → filename matches `**_self_approve*` or the decision
                  record explicitly carries `status: CLOSED` /
                  `status: Closed` or a Notion mirror status
                  containing 'Closed'.
    Open        → no Notion sync or no synced prefix AND not closed.
    Superseded  → ``superseded_by`` is set (non-null).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from ui.backend.services.validation_report import REPO_ROOT

DECISIONS_DIR = REPO_ROOT / ".planning" / "decisions"
EXTERNAL_GATE_QUEUE = REPO_ROOT / ".planning" / "external_gate_queue.md"

DecisionColumn = Literal["Accepted", "Closed", "Open", "Superseded"]


@dataclass(slots=True)
class DecisionCard:
    decision_id: str
    title: str
    timestamp: str
    scope: str
    autonomous: bool
    reversibility: str
    notion_sync_status: str
    notion_url: str | None
    github_pr_url: str | None
    relative_path: str
    column: DecisionColumn
    superseded_by: str | None = None
    supersedes: str | None = None


@dataclass(slots=True)
class GateQueueItem:
    qid: str  # e.g. Q-1 / Q-2
    title: str
    state: Literal["OPEN", "CLOSED"]
    summary: str


@dataclass(slots=True)
class DecisionsQueueSnapshot:
    cards: list[DecisionCard] = field(default_factory=list)
    gate_queue: list[GateQueueItem] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_NOTION_URL_RE = re.compile(r"(https://www\.notion\.so/[A-Za-z0-9\-]+)")
_PR_URL_RE = re.compile(r"(https://github\.com/[\w\-./]+?/pull/\d+)")
_Q_HEADER_RE = re.compile(r"^##\s+(~~)?\s*(Q-\d+):?\s*(.*?)(~~)?$", re.MULTILINE)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    body = text[match.end():]
    return fm, body


def _extract_title(body: str) -> str:
    m = _TITLE_RE.search(body)
    if not m:
        return "(untitled)"
    return m.group(1).strip()


def _classify(fm: dict[str, Any], path: Path) -> DecisionColumn:
    if fm.get("superseded_by"):
        return "Superseded"
    status_hint = str(fm.get("status") or fm.get("notion_status") or "").lower()
    if "closed" in status_hint or "_self_approve" in path.name or "_fuse" in path.name:
        return "Closed"
    sync = str(fm.get("notion_sync_status", ""))
    if sync.strip().lower().startswith("synced"):
        return "Accepted"
    return "Open"


def _load_one(path: Path) -> DecisionCard | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fm, body = _parse_frontmatter(text)
    decision_id = str(fm.get("decision_id") or path.stem).strip()
    sync = str(fm.get("notion_sync_status", ""))
    notion_url = None
    m = _NOTION_URL_RE.search(sync)
    if m:
        notion_url = m.group(1)
    pr_url = None
    pr_search = _PR_URL_RE.search(f"{sync}\n{fm.get('github_pr_url','')}")
    if pr_search:
        pr_url = pr_search.group(1)
    relative = str(path.relative_to(REPO_ROOT))
    return DecisionCard(
        decision_id=decision_id,
        title=_extract_title(body),
        timestamp=str(fm.get("timestamp") or path.stem[:10]),
        scope=str(fm.get("scope") or ""),
        autonomous=bool(fm.get("autonomous_governance", False)),
        reversibility=(str(fm.get("reversibility") or "").splitlines() or [""])[0][:160],
        notion_sync_status=sync.splitlines()[0] if sync else "",
        notion_url=notion_url,
        github_pr_url=pr_url,
        relative_path=relative,
        column=_classify(fm, path),
        superseded_by=fm.get("superseded_by"),
        supersedes=fm.get("supersedes"),
    )


def _load_gate_queue() -> list[GateQueueItem]:
    if not EXTERNAL_GATE_QUEUE.exists():
        return []
    text = EXTERNAL_GATE_QUEUE.read_text(encoding="utf-8")
    matches = list(_Q_HEADER_RE.finditer(text))
    out: list[GateQueueItem] = []
    for idx, match in enumerate(matches):
        struck = bool(match.group(1))
        qid = match.group(2)
        header_title = (match.group(3) or "").strip().rstrip("—- ")
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = text[match.end():end].strip()
        summary_line = ""
        for line in block.splitlines():
            s = line.strip()
            if not s or s.startswith("-"):
                continue
            summary_line = s
            break
        if not summary_line:
            for line in block.splitlines():
                s = line.strip()
                if s.startswith("- **Summary**"):
                    summary_line = s.split("**Summary**:", 1)[-1].strip().lstrip(":").strip()
                    break
        state: Literal["OPEN", "CLOSED"] = "CLOSED" if struck else "OPEN"
        if qid == "Q-3":
            state = "CLOSED"  # Q-3 resolved 2026-04-19 / 2026-04-20
        out.append(
            GateQueueItem(
                qid=qid,
                title=header_title or qid,
                state=state,
                summary=(summary_line or "").splitlines()[0][:280],
            )
        )
    return out


def list_decisions() -> DecisionsQueueSnapshot:
    if not DECISIONS_DIR.exists():
        return DecisionsQueueSnapshot()
    cards: list[DecisionCard] = []
    for path in sorted(DECISIONS_DIR.glob("*.md")):
        card = _load_one(path)
        if card is not None:
            cards.append(card)
    gate_queue = _load_gate_queue()
    counts: dict[str, int] = {"Accepted": 0, "Closed": 0, "Open": 0, "Superseded": 0}
    for card in cards:
        counts[card.column] = counts.get(card.column, 0) + 1
    return DecisionsQueueSnapshot(cards=cards, gate_queue=gate_queue, counts=counts)
