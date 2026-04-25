#!/usr/bin/env python3
"""Warn-not-block isolation guard for OPS-2026-04-25-001 dual-track development.

Authority: ``.planning/ops/2026-04-25_dual_track_plan.md`` §3 isolation
strength + Opus 4.7 audit recommendation (Notion page
34dc6894-2bed-81d8-8ef5-f8add0d01d0a). Active during dogfood window
2026-04-25 → 2026-05-19; auto-retires after expires date.

Detects commits that touch files from BOTH tracks (line A · ADR-002
governance · line B · 10-case simulation) and emits a stderr warning
if the commit message lacks an explicit ``[shared]`` or
``[cross-track-ack]`` acknowledgement tag. **Does not block** — false
positives on legitimate cross-track edits (e.g., line B adding a new
``src/<new>.py`` module requires editing
``src/_plane_assignment.py`` PLANE_OF dict per §4.1) would be more
costly than the warn fatigue.

Usage:
  python scripts/check_track_isolation.py                # check staged diff
  python scripts/check_track_isolation.py <commit-hash>  # check that commit
  python scripts/check_track_isolation.py --since=HEAD~3 # check last 3 commits

Exit codes:
  0 — no cross-track touches OR explicit ack tag present (clean)
  0 — cross-track touches detected, warning emitted to stderr (still 0)
  2 — invocation error (bad args, no git, etc.)

The pre-commit hook in ``.pre-commit-config.yaml`` runs this in
"commit message available" mode via ``commit-msg`` stage so the tag
detection is reliable.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import Iterable, List, Set, Tuple


# Ownership rules per OPS-2026-04-25-001 §2 + Opus 4.7 §2 audit amendments.
# Keep in sync with .planning/ops/2026-04-25_dual_track_plan.md.

LINE_A_PATTERNS = [
    r"^src/_plane_guard\.py$",
    r"^src/_plane_assignment\.py$",
    r"^src/__init__\.py$",
    r"^\.importlinter$",
    r"^scripts/gen_importlinter\.py$",
    r"^scripts/plane_guard_rollback_eval\.py$",
    r"^\.github/workflows/plane_guard_rollback_cron\.yml$",
    r"^docs/adr/ADR-002.*\.md$",
    r"^tests/test_plane_guard.*\.py$",
    r"^tests/test_plane_assignment_ssot\.py$",
    r"^tests/test_gen_importlinter\.py$",
]

LINE_B_PATTERNS = [
    r"^knowledge/gold_standards/.+\.yaml$",
    r"^src/foam_agent_adapter\.py$",
    r"^src/comparator_gates\.py$",
    r"^src/result_comparator\.py$",
    r"^src/(cylinder|airfoil|wall_gradient|plane_channel)_.*\.py$",
    r"^reports/(?!plane_guard|codex_tool_reports).*",
    r"^whitelist_cases/.*",
    r"^ui/frontend/public/flow-fields/.*",
    r"^tests/test_phase_e2e\.py$",
    r"^tests/test_foam_agent_adapter\.py$",
]

SHARED_PATTERNS = [
    r"^\.gitignore$",
    r"^pyproject\.toml$",
    r"^requirements.*\.txt$",
    r"^\.pre-commit-config\.yaml$",
    r"^\.planning/STATE\.md$",
    r"^tests/conftest\.py$",
]


ACK_TAG_RE = re.compile(
    r"\[(shared|cross-track-ack|deps|ops|line-a|line-b)\]", re.IGNORECASE
)


def _classify(path: str) -> str:
    """Return 'A', 'B', 'shared', or 'other' for a path."""
    for pat in LINE_A_PATTERNS:
        if re.match(pat, path):
            return "A"
    for pat in LINE_B_PATTERNS:
        if re.match(pat, path):
            return "B"
    for pat in SHARED_PATTERNS:
        if re.match(pat, path):
            return "shared"
    return "other"


def _git_diff_files(rev: str = "") -> List[str]:
    """Return paths changed in staged diff or specific commit."""
    if rev:
        cmd = ["git", "diff", "--name-only", f"{rev}~1..{rev}"]
    else:
        cmd = ["git", "diff", "--cached", "--name-only"]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _read_commit_msg(msg_file: str) -> str:
    if not msg_file or not os.path.exists(msg_file):
        return ""
    with open(msg_file, "r", encoding="utf-8") as f:
        return f.read()


def _check(files: Iterable[str], commit_msg: str) -> Tuple[Set[str], Set[str], Set[str], bool]:
    a_hits: Set[str] = set()
    b_hits: Set[str] = set()
    shared_hits: Set[str] = set()
    for path in files:
        cat = _classify(path)
        if cat == "A":
            a_hits.add(path)
        elif cat == "B":
            b_hits.add(path)
        elif cat == "shared":
            shared_hits.add(path)
    has_ack = bool(ACK_TAG_RE.search(commit_msg))
    return a_hits, b_hits, shared_hits, has_ack


def _format_warn(a: Set[str], b: Set[str], shared: Set[str], msg_file: str) -> str:
    lines = [
        "",
        "⚠️  OPS-2026-04-25-001 dual-track isolation WARN",
        "    Commit touches files from multiple tracks but commit message",
        "    lacks an explicit ack tag ([shared] / [cross-track-ack] /",
        "    [deps] / [ops] / [line-a] / [line-b]).",
        "",
    ]
    if a:
        lines.append("    Line A (ADR-002 governance) files:")
        lines.extend(f"      - {p}" for p in sorted(a))
    if b:
        lines.append("    Line B (10-case simulation) files:")
        lines.extend(f"      - {p}" for p in sorted(b))
    if shared:
        lines.append("    Shared files (require explicit ack):")
        lines.extend(f"      - {p}" for p in sorted(shared))
    lines.extend([
        "",
        "    Add one of [shared] / [cross-track-ack] / [deps] / [ops] /",
        "    [line-a] / [line-b] to your commit message subject to",
        "    silence this warning. The commit is NOT blocked — this is",
        "    a discipline reminder for dogfood window 2026-04-25 →",
        "    2026-05-19.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__ or "")
    p.add_argument("commit_msg_file", nargs="?", default="",
                   help="Path to .git/COMMIT_EDITMSG (commit-msg hook context)")
    p.add_argument("--rev", default="", help="Git rev to inspect (default: staged)")
    args = p.parse_args()

    files = _git_diff_files(rev=args.rev)
    if not files:
        return 0
    commit_msg = _read_commit_msg(args.commit_msg_file)

    a, b, shared, has_ack = _check(files, commit_msg)

    cross_track = bool(a and b)
    shared_touched = bool(shared)

    if not cross_track and not shared_touched:
        return 0
    if has_ack:
        return 0

    sys.stderr.write(_format_warn(a, b, shared, args.commit_msg_file))
    return 0  # warn-not-block per Opus 4.7 §3 audit recommendation


if __name__ == "__main__":
    raise SystemExit(main())
