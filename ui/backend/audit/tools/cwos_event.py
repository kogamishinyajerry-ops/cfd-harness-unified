#!/usr/bin/env python3
"""Append a structured event to .cwos/agent_events.jsonl.

Usage:

    python tools/cwos_event.py \\
        --agent backend-engineer \\
        --task-id PH0-CLI-001 \\
        --status PASS \\
        --summary "Implemented cfdtrust CLI skeleton" \\
        --evidence src/cfdtrust/cli.py tests/test_manifest.py \\
        --tests "pytest -q"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_PATH = REPO_ROOT / ".cwos" / "agent_events.jsonl"
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

ALLOWED_STATUSES = {
    "QUEUED", "RUNNING", "PASS", "FAIL", "BLOCKED",
    "NEEDS_DECISION", "DEFERRED", "MOCKED",
}


def _load_sibling(name: str):
    """Load a sibling tools/ module by file path (the round-4 pattern)."""
    spec = importlib.util.spec_from_file_location(
        name, str(Path(__file__).resolve().parent / f"{name}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cwos_paths = _load_sibling("cwos_paths")
cwos_agents = _load_sibling("cwos_agents")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(args: argparse.Namespace) -> Dict[str, Any]:
    if args.status not in ALLOWED_STATUSES:
        raise SystemExit(
            f"invalid status '{args.status}'. Allowed: {sorted(ALLOWED_STATUSES)}"
        )

    # F-07 fix: --agent must match a declared agent in .claude/agents/*.md.
    # The audit trail is no longer forgeable just by picking any string.
    #
    # R6-F-01 fix: an empty allowlist is a hard BLOCKED, NOT a free pass.
    # The previous form `if known and args.agent not in known` failed open
    # when .claude/agents/ was missing or empty — any string was accepted
    # as --agent. The allowlist source disappearing is exactly when the
    # gate matters most, so we treat it as a configuration error.
    known = cwos_agents.known_agent_names(AGENTS_DIR)
    if not known:
        raise SystemExit(
            f"agent allowlist is empty: no agents declared under {AGENTS_DIR}. "
            f"At least one .claude/agents/<name>.md with YAML frontmatter "
            f"`name: <name>` must exist before events can be written. "
            f"The allowlist cannot fail open."
        )
    if args.agent not in known:
        raise SystemExit(
            f"unknown agent '{args.agent}'. Declared agents: {sorted(known)}.\n"
            f"To add a new agent, create .claude/agents/<name>.md with YAML "
            f"frontmatter `name: <name>` first."
        )

    evidence = list(args.evidence or [])
    if args.status == "PASS" and not evidence:
        raise SystemExit(
            "PASS events require at least one --evidence path. "
            "If you have no evidence, your task is not PASS."
        )

    # F-08 fix: PASS events must cite safe-relative-and-existing evidence
    # paths at write time. Mirrors the read-time check in cockpit. Closes
    # the loophole that let `cwos_event ... --evidence does/not/exist.py`
    # land successfully.
    if args.status == "PASS":
        for rel in evidence:
            ok, reason = cwos_paths.path_is_safe_relative(rel, REPO_ROOT)
            if not ok:
                raise SystemExit(
                    f"invalid evidence path '{rel}' for PASS event: {reason}.\n"
                    f"Evidence must be a relative path to a file inside the repo."
                )

    return {
        "time": utc_now_iso(),
        "agent": args.agent,
        "task_id": args.task_id,
        "status": args.status,
        "summary": args.summary,
        "evidence": evidence,
        "tests": args.tests,
        "blockers": list(args.blockers or []),
        "decision_required": bool(args.decision_required),
        "next_action": args.next_action,
    }


def append(event: Dict[str, Any], path: Path = EVENTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Append a CWOS event to .cwos/agent_events.jsonl")
    p.add_argument("--agent", required=True)
    p.add_argument("--task-id", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--evidence", nargs="*", default=[])
    p.add_argument("--tests", default=None)
    p.add_argument("--blockers", nargs="*", default=[])
    p.add_argument("--decision-required", action="store_true")
    p.add_argument("--next-action", default=None)
    args = p.parse_args(argv)
    event = build_event(args)
    append(event)
    print(json.dumps(event, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
