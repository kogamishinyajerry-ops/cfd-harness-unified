#!/usr/bin/env python3
"""DEC → Notion Decisions DB sync (event-driven, NOT calendar-scheduled).

Per DEC-V61-087 §6 (Notion 单向同步契约) + 项目"禁用日期/调度门控"核心原则:
this script runs on DEMAND (event-triggered: DEC commit, Kogami review landing,
or explicit user invocation). It does NOT poll, schedule, or run on a timer.

Reads the DEC's frontmatter, parses the structured fields (decision_id, title,
status, etc.), maps them to the Notion Decisions DB schema (Name, Status,
Scope, Why, Decision, Impact, Alternatives, Canonical Follow-up), and either
creates a new page or updates an existing one (matched by decision_id).

After successful sync, backfills the DEC frontmatter `notion_sync_status` field
with the Notion page URL.

Auth: requires NOTION_TOKEN env var (in user's ~/.zshrc per MEMORY.md).
Endpoint: Notion REST API v1 (no MCP — this script is wrapper-callable, MCP isn't).

Usage:
    python3 scripts/governance/notion_sync_dec.py --dec <path-to-dec.md>

Exit codes:
    0 = synced (or no-op if frontmatter already has fresh sync URL)
    1 = error (no NOTION_TOKEN, dec not found, API failure, etc.)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"  # stable; matches Notion REST API v1 docs
DECISIONS_DB_ID = "fa55d3ed0a6d452f909d91a8c8d218a7"

# Mapping from DEC `status:` frontmatter pattern to Notion Status select option
STATUS_PATTERNS = [
    (re.compile(r"^Accepted", re.IGNORECASE), "Accepted"),
    (re.compile(r"^Proposed", re.IGNORECASE), "Proposed"),
    (re.compile(r"^Rejected", re.IGNORECASE), "Rejected"),
    (re.compile(r"^Superseded", re.IGNORECASE), "Superseded"),
    (re.compile(r"^Closed", re.IGNORECASE), "Closed"),
    (re.compile(r"^Done", re.IGNORECASE), "Done"),
    (re.compile(r"^Complete", re.IGNORECASE), "Completed"),
]


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-ish frontmatter block from a DEC markdown file."""
    if not text.startswith("---\n"):
        return {}
    try:
        end = text.index("\n---\n", 4)
    except ValueError:
        return {}
    fm_text = text[4:end]

    out: dict = {}
    cur_key = None
    cur_val_lines: list[str] = []

    def commit():
        nonlocal cur_key, cur_val_lines
        if cur_key is None:
            return
        joined = "\n".join(cur_val_lines).strip()
        out[cur_key] = joined
        cur_key = None
        cur_val_lines = []

    for line in fm_text.splitlines():
        if not line:
            cur_val_lines.append("")
            continue
        # Top-level key (no leading space)
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            commit()
            cur_key = m.group(1)
            v = m.group(2).strip()
            if v == "|" or v == ">":
                cur_val_lines = []
            else:
                cur_val_lines = [v]
        else:
            # Continuation (indented) line — keep as part of current value
            cur_val_lines.append(line.lstrip())

    commit()
    return out


def map_status(status_text: str) -> str:
    for pattern, mapped in STATUS_PATTERNS:
        if pattern.match(status_text.strip()):
            return mapped
    # Default fallback
    return "Proposed"


def extract_section(body: str, section_header: str, max_chars: int = 1500) -> str:
    """Extract the body of a markdown section by ## header, capped."""
    pattern = rf"^{re.escape(section_header)}\s*$(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    text = m.group(1).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text


def notion_api(method: str, path: str, body: dict | None = None) -> dict:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("FATAL: NOTION_TOKEN env var not set (expected in ~/.zshrc)")

    url = f"{NOTION_API}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        sys.exit(f"Notion API {method} {path} failed: HTTP {e.code}\n{body_text[:500]}")


def find_existing_page(decision_id: str) -> str | None:
    """Search Decisions DB for a page whose Name property starts with `decision_id`."""
    res = notion_api(
        "POST",
        f"/databases/{DECISIONS_DB_ID}/query",
        {
            "filter": {
                "property": "Name",
                "title": {"starts_with": decision_id},
            },
            "page_size": 5,
        },
    )
    for page in res.get("results", []):
        title_prop = page.get("properties", {}).get("Name", {}).get("title", [])
        title_text = "".join(t.get("plain_text", "") for t in title_prop)
        if title_text.startswith(decision_id):
            return page["id"]
    return None


def page_props_from_frontmatter(fm: dict, body: str) -> dict:
    """Build Notion properties dict from DEC frontmatter + body sections."""
    title_raw = fm.get("title", fm.get("decision_id", "untitled DEC"))
    decision_id = fm.get("decision_id", "")
    full_title = f"{decision_id} · {title_raw}" if decision_id and not title_raw.startswith(decision_id) else title_raw

    why = extract_section(body, "## Why")
    decision_section = extract_section(body, "## Decision")
    impact = extract_section(body, "## Impact") or extract_section(body, "## Acceptance Criteria")
    alternatives = extract_section(body, "## Alternatives") or extract_section(body, "## Open Questions", 1200)
    follow_up = extract_section(body, "## Process Note") or extract_section(body, "## Implementation Plan", 1200)

    props = {
        "Name": {"title": [{"text": {"content": full_title[:2000]}}]},
        "Status": {"select": {"name": map_status(fm.get("status", ""))}},
        "Scope": {"select": {"name": "Architecture"}},
    }
    # Optional rich-text fields — only set if non-empty
    for prop_name, value in [
        ("Why", why),
        ("Decision", decision_section),
        ("Impact", impact),
        ("Alternatives", alternatives),
        ("Canonical Follow-up", follow_up),
    ]:
        if value:
            # Notion text property limit ~2000 chars/block
            props[prop_name] = {"rich_text": [{"text": {"content": value[:1900]}}]}
    return props


def create_or_update(decision_id: str, props: dict, dec_path: Path) -> tuple[str, str]:
    existing_id = find_existing_page(decision_id)
    if existing_id:
        notion_api("PATCH", f"/pages/{existing_id}", {"properties": props})
        url = f"https://www.notion.so/{existing_id.replace('-', '')}"
        return existing_id, url
    res = notion_api(
        "POST",
        "/pages",
        {
            "parent": {"database_id": DECISIONS_DB_ID},
            "properties": props,
        },
    )
    page_id = res["id"]
    url = res.get("url") or f"https://www.notion.so/{page_id.replace('-', '')}"
    return page_id, url


def backfill_sync_status(dec_path: Path, notion_url: str) -> None:
    """Update notion_sync_status frontmatter field in the DEC file."""
    text = dec_path.read_text()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_value = f"synced {today} ({notion_url})"

    pattern = re.compile(r"^notion_sync_status:.*$", re.MULTILINE)
    if pattern.search(text):
        new_text = pattern.sub(f"notion_sync_status: {new_value}", text, count=1)
    else:
        # Insert after frontmatter opener
        new_text = text.replace("---\n", f"---\nnotion_sync_status: {new_value}\n", 1)

    dec_path.write_text(new_text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dec", type=Path, required=True, help="path to DEC markdown")
    ap.add_argument("--no-backfill", action="store_true", help="skip writing notion_sync_status to DEC frontmatter")
    args = ap.parse_args()

    if not args.dec.exists():
        sys.exit(f"FATAL: DEC not found: {args.dec}")

    text = args.dec.read_text()
    fm = parse_frontmatter(text)
    decision_id = fm.get("decision_id", "")
    if not decision_id:
        sys.exit(f"FATAL: DEC has no `decision_id` frontmatter field: {args.dec}")

    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    props = page_props_from_frontmatter(fm, body)

    page_id, notion_url = create_or_update(decision_id, props, args.dec)
    print(f"[notion-sync] {decision_id}: {notion_url}")

    if not args.no_backfill:
        backfill_sync_status(args.dec, notion_url)
        print(f"[notion-sync] backfilled notion_sync_status in {args.dec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
