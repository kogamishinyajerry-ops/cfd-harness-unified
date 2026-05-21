#!/usr/bin/env python3
"""Render docs/status/COCKPIT.md and COCKPIT.html from project_status.json.

Per Red Team finding F-01: every narrative section MUST be derived from repo
state. This module is a presenter, never a source.
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml

# Import the shared path-safety contract. tools/ live as flat scripts, not a
# package, so we load the sibling module by path to keep this script runnable
# without sys.path tweaks.
_PATHS_SPEC = importlib.util.spec_from_file_location(
    "cwos_paths", str(Path(__file__).resolve().parent / "cwos_paths.py")
)
cwos_paths = importlib.util.module_from_spec(_PATHS_SPEC)
_PATHS_SPEC.loader.exec_module(cwos_paths)

# R8-F-02 fix: agent enumeration must share the same safety guards as
# cwos_event.py. Load the sibling module by file path (same pattern used
# above for cwos_paths) and route derive_agent_matrix through it.
_AGENTS_SPEC = importlib.util.spec_from_file_location(
    "cwos_agents", str(Path(__file__).resolve().parent / "cwos_agents.py")
)
cwos_agents = importlib.util.module_from_spec(_AGENTS_SPEC)
_AGENTS_SPEC.loader.exec_module(cwos_agents)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_STATUS = REPO_ROOT / "docs" / "status"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"
OPEN_QUESTIONS = REPO_ROOT / "docs" / "project-memory" / "OPEN_QUESTIONS.md"
NEXT_ACTIONS = REPO_ROOT / "docs" / "project-memory" / "NEXT_ACTIONS.md"
EVENTS_LOG = REPO_ROOT / ".cwos" / "agent_events.jsonl"


# ---------- helpers ----------

def _load_status() -> Dict[str, Any]:
    p = DOCS_STATUS / "project_status.json"
    if not p.exists():
        raise SystemExit("project_status.json missing — run tools/cwos_status.py first.")
    return json.loads(p.read_text())


def _status_emoji(s: str) -> str:
    return {
        "PASS": "🟢", "GREEN": "🟢",
        "WARN": "🟡", "AMBER": "🟡", "MOCKED": "🟡",
        "FAIL": "🔴", "RED": "🔴", "BLOCKED": "🔴",
    }.get(s, "⚪")


# ---------- data-derived sections (F-01 fix) ----------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """
    Red Team T1-F-02 fix: use yaml.safe_load instead of a hand-rolled
    `line.partition(":")` parser. Handles block scalars (`description: |`),
    colons inside quoted strings, and standard YAML constructs.

    Graceful degradation: returns {} on missing/empty/malformed frontmatter.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    # Coerce values to strings for cockpit display (yaml may return ints/lists).
    return {str(k): (v if isinstance(v, str) else str(v)) for k, v in data.items()}


def derive_agent_matrix(
    agents_dir: Path | None = None,
    repo_root: Path | None = None,
) -> List[Tuple[str, str, str]]:
    """Return [(name, description, relative_path)] from `.claude/agents/*.md`.

    Round-8 R8-F-02 fix: this function now delegates agent enumeration to
    `cwos_agents.declared_agents()` so the cockpit, the event writer, and
    the test suite all observe the same allowlist. The symlink-class
    guards (`is_symlink` on the directory and on each `.md`) live in
    `cwos_agents._safe_md_files`; this function only renders the rows.

    Both args default to module-level constants so the production caller
    stays parameter-free; tests inject tmp dirs.
    """
    a = agents_dir if agents_dir is not None else AGENTS_DIR
    r = repo_root if repo_root is not None else REPO_ROOT
    rows: List[Tuple[str, str, str]] = []
    for entry in cwos_agents.declared_agents(a):
        p = entry["path"]
        try:
            rel = str(p.relative_to(r))
        except ValueError:
            rel = str(p)  # path outside repo_root; show absolute (test paths)
        rows.append((entry["name"], entry["description"], rel))
    return rows


_OQ_HEADER_RE = re.compile(r"^##\s+(OQ-\d+)\s+—\s+(.+?)\s*$")


def derive_decisions_needed(limit: int = 3) -> List[Tuple[str, str]]:
    """Return [(oq_id, title)] for open questions whose status is 'open'."""
    if not OPEN_QUESTIONS.exists():
        return []
    text = OPEN_QUESTIONS.read_text()
    out: List[Tuple[str, str]] = []
    current_id: str | None = None
    current_title: str | None = None
    open_flag = False
    for line in text.splitlines():
        m = _OQ_HEADER_RE.match(line)
        if m:
            # flush previous block
            if current_id and open_flag:
                out.append((current_id, current_title or ""))
            current_id, current_title = m.group(1), m.group(2).strip()
            open_flag = False
            continue
        if current_id and re.search(r"\*\*Status:\*\*\s*open", line, re.IGNORECASE):
            open_flag = True
    if current_id and open_flag:
        out.append((current_id, current_title or ""))
    return out[:limit]


_NA_HEADER_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")


def derive_next_best_actions(limit: int = 5) -> List[Tuple[str, str]]:
    """Return [(number, title)] from NEXT_ACTIONS.md, in document order."""
    if not NEXT_ACTIONS.exists():
        return []
    out: List[Tuple[str, str]] = []
    for line in NEXT_ACTIONS.read_text().splitlines():
        m = _NA_HEADER_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out[:limit]


def derive_bright_spots(
    limit: int = 5,
    events_log: Path | None = None,
    repo_root: Path | None = None,
) -> List[Dict[str, Any]]:
    """
    Bright Spots = recent PASS events whose evidence paths are ALL
    safe-relative-and-existing. Phantom-evidence events are filtered.

    Red Team T1-F-01 + R3-F-01 fix: uses `cwos_paths.evidence_paths_all_safe_and_exist`
    which rejects absolute paths AND paths that escape `repo_root` after symlink
    resolution. Centralized in `cwos_paths.py` so this check cannot drift.
    """
    log = events_log if events_log is not None else EVENTS_LOG
    root = repo_root if repo_root is not None else REPO_ROOT
    events = cwos_paths.iter_pass_events_with_evidence(log)
    valid = [
        e for e in events
        if cwos_paths.evidence_paths_all_safe_and_exist(e.get("evidence", []), root)
    ]
    return list(reversed(valid))[:limit]


def count_phantom_evidence_pass_events(
    events_log: Path | None = None,
    repo_root: Path | None = None,
) -> int:
    """Thin re-export of the shared phantom counter for back-compat."""
    log = events_log if events_log is not None else EVENTS_LOG
    root = repo_root if repo_root is not None else REPO_ROOT
    return cwos_paths.count_phantom_pass_events(log, root)


# ---------- markdown table cell sanitization (R3-F-02 + R3-F-03 fix) ----------


def sanitize_table_cell(value: str) -> str:
    """
    Make a string safe to drop into a markdown table cell:
      - escape `|` so it cannot inject extra columns
      - flatten any newlines / carriage returns into single spaces
      - collapse adjacent whitespace
      - trim
    """
    if value is None:
        return ""
    s = str(value).replace("\r", " ").replace("\n", " ").replace("|", r"\|")
    return re.sub(r"\s+", " ", s).strip()


# ---------- markdown ----------

def render_md(status: Dict[str, Any]) -> str:
    overall = status.get("overall_status", "AMBER")
    tasks = status.get("tasks", {})
    by_status = tasks.get("by_status", {})
    reports = status.get("trust_reports", [])
    blockers = status.get("blockers", [])
    events = status.get("events", {})
    pass_no_evidence = events.get("pass_without_evidence", [])
    metrics = status.get("metrics", {})

    agent_rows = derive_agent_matrix()
    decisions = derive_decisions_needed(limit=3)
    next_actions = derive_next_best_actions(limit=5)
    bright = derive_bright_spots(limit=5)
    phantom_evidence_count = count_phantom_evidence_pass_events()

    lines: List[str] = [
        "# AI-CFD-V2 — Project Cockpit",
        "",
        f"> Generated: `{status.get('generated_at')}`  |  Phase: **{status.get('phase')}**",
        "> All sections below are derived from repo state. No hand-written narrative lives here.",
        "",
        f"## Overall Status: {_status_emoji(overall)} {overall}",
        "",
        "## Phase Progress",
        "",
        f"- Total tasks: **{tasks.get('total', 0)}**",
    ]
    for s in ("PASS", "RUNNING", "QUEUED", "BLOCKED", "FAIL", "NEEDS_DECISION", "MOCKED", "DEFERRED"):
        n = by_status.get(s, 0)
        if n:
            lines.append(f"  - {s}: {n}")

    lines += ["", "## Trust Loop Status", ""]
    if not reports:
        lines.append("_No trust_report.json found yet. Run `make trust-loop`._")
    else:
        lines.append("| case_id | overall | solver | validation | path |")
        lines.append("|---|---|---|---|---|")
        for r in reports:
            lines.append(
                f"| `{r.get('case_id')}` | {_status_emoji(r.get('overall_status',''))} {r.get('overall_status')} "
                f"| {r.get('solver_execution')} | {r.get('validation_status')} | `{r.get('path')}` |"
            )

    lines += ["", "## Agent Matrix", ""]
    if not agent_rows:
        lines.append("_No agent files found under `.claude/agents/`._")
    else:
        lines.append("| agent | description | declared in |")
        lines.append("|---|---|---|")
        for name, desc, rel in agent_rows:
            # R3-F-02 + R3-F-03 fix: sanitize before truncation so escaped
            # `|` and flattened newlines don't sneak into the cell.
            name_cell = sanitize_table_cell(name)
            desc_cell = sanitize_table_cell(desc)
            rel_cell = sanitize_table_cell(rel)
            short = desc_cell if len(desc_cell) <= 140 else desc_cell[:137].rstrip() + "..."
            lines.append(f"| `{name_cell}` | {short} | `{rel_cell}` |")

    lines += ["", "## Blockers", ""]
    if not blockers:
        lines.append("_None._")
    else:
        for b in blockers:
            lines.append(
                f"- **{b.get('blocker_id')}** [{b.get('severity')}] {b.get('title')} — owner: `{b.get('owner_agent')}`"
            )

    lines += ["", "## Bright Spots", ""]
    if not bright:
        lines.append("_No evidenced PASS events yet._")
    else:
        for e in bright:
            tid = e.get("task_id", "?")
            agent = e.get("agent", "?")
            summary = e.get("summary", "")
            ev_count = len(e.get("evidence") or [])
            lines.append(f"- `{tid}` — {agent} — {summary}  _(evidence files: {ev_count})_")

    lines += ["", "## Decisions Needed", ""]
    if not decisions:
        lines.append("_No open questions._")
    else:
        for i, (oq_id, title) in enumerate(decisions, 1):
            lines.append(f"{i}. **{oq_id}** — {title}  _(see `docs/project-memory/OPEN_QUESTIONS.md`)_")

    lines += [
        "",
        "## Integrity Checks",
        "",
        f"- PASS events without evidence: **{len(pass_no_evidence)}** (must be 0)",
        f"- PASS events with phantom evidence (paths do not resolve): **{phantom_evidence_count}** (must be 0)",
        f"- mocked solver reports: {metrics.get('mocked_solver_reports', 0)}",
        f"- real solver reports:   {metrics.get('real_solver_reports', 0)}",
        f"- agents declared: {len(agent_rows)}",
        f"- open questions: {len(decisions)} surfaced (top 3)",
        "",
        "## Next Best Actions",
        "",
    ]
    if not next_actions:
        lines.append("_No next actions declared in `docs/project-memory/NEXT_ACTIONS.md`._")
    else:
        for num, title in next_actions:
            lines.append(f"{num}. {title}  _(see `docs/project-memory/NEXT_ACTIONS.md`)_")

    lines += [
        "",
        "---",
        "_Cockpit is generated by `tools/cwos_render_dashboard.py`. "
        "Do not hand-edit. To change narrative content, edit the source documents "
        "(`.claude/agents/*.md`, `OPEN_QUESTIONS.md`, `NEXT_ACTIONS.md`, "
        "`agent_events.jsonl`) and re-run `make cockpit`._",
    ]
    return "\n".join(lines) + "\n"


# ---------- html ----------

def render_html(md: str, status: Dict[str, Any]) -> str:
    overall = status.get("overall_status", "AMBER")
    body = html.escape(md)
    return (
        "<!doctype html>\n<html><head><meta charset='utf-8'>"
        "<title>AI-CFD-V2 Cockpit</title>"
        "<style>"
        "body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:920px;margin:24px auto;padding:0 16px;color:#111}"
        "pre{white-space:pre-wrap;background:#0b1020;color:#dbe6ff;padding:16px;border-radius:8px;overflow-x:auto;font-size:13px;line-height:1.5}"
        "h1{font-size:22px}"
        ".badge{display:inline-block;padding:2px 10px;border-radius:999px;font-weight:600;font-size:13px;margin-left:8px}"
        ".green{background:#d2f5dd;color:#0a6b2c}"
        ".amber{background:#fff1c2;color:#7a5300}"
        ".red{background:#ffd6d6;color:#8a0d0d}"
        "</style></head><body>"
        f"<h1>AI-CFD-V2 Cockpit"
        f"<span class='badge {overall.lower()}'>{overall}</span></h1>"
        f"<pre>{body}</pre>"
        "</body></html>\n"
    )


def main(argv: List[str] | None = None) -> int:
    status = _load_status()
    DOCS_STATUS.mkdir(parents=True, exist_ok=True)
    md = render_md(status)
    (DOCS_STATUS / "COCKPIT.md").write_text(md)
    (DOCS_STATUS / "COCKPIT.html").write_text(render_html(md, status))
    print(f"[cwos_dashboard] wrote COCKPIT.md and COCKPIT.html (overall={status.get('overall_status')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
