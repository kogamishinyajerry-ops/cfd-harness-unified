#!/usr/bin/env python3
"""Commit-msg-stage block-with-tag-escape isolation guard for OPS-2026-04-25-001.

v2 (2026-04-25T21:50 · Opus 4.7 §3 v2 supersede): graduated severity
model. This script is the **commit-msg stage** half (looks at the
prepared commit message file PLUS ``git diff --cached``). The pre-commit
stage half is ``scripts/check_track_isolation.py``.

Authority: ``.planning/ops/2026-04-25_dual_track_plan.md`` §3 v2 +
Notion Opus 4.7 audit on OPS page block 31
(id 29c8696d-84e9-4484-94db-1391f43d0df4) · 2026-04-25T15:10 +0800.
Active during dogfood window 2026-04-25 → 2026-05-19; the script
itself auto-retires after expires date.

# Severity model (commit-msg stage scope)

The pre-commit stage already hard-blocks the most dangerous case
(CORE line A SOLE ∧ line B in the same index). This stage covers
the **softer** boundary:

- **SOFT line A files / SHARED files** ∧ **line B files** in the
  same commit → BLOCK unless the commit message has one of the
  legitimizing tags below.

# Legitimizing tags (block-with-tag-escape)

Any of these tags in the commit message body unblocks the commit:

- ``[cross-track-ack: <reason>]`` — author explicitly acknowledges a
  legitimate cross-track edit (e.g., §4.1 PLANE_OF dict update for a
  new src.* module added by line B).
- ``[shared]`` — commit is intentionally cross-track infrastructure
  (e.g., editing both ``CLAUDE.md`` line A section and a line B
  reference simultaneously).
- ``[deps]`` — pure dependency / lockfile / pyproject.toml-only
  bump that crosses tracks by nature.
- ``[ops]`` — touching governance docs that span both tracks
  (OPS-2026-04-25-001, RETRO files referencing both lines, etc.).
- ``[line-a]`` or ``[line-b]`` alone DO NOT unblock — those are
  single-track tags; using one while staging the other track is
  exactly the cross-track-absorption mistake we are catching.

# Usage

```
python scripts/check_track_isolation_msg.py <commit-msg-file>
```

(Pre-commit framework invokes this at commit-msg stage with the
prepared message path as argv[1].)

Exit codes:
- 0 = no cross-track touch OR appropriate tag present (clean)
- 1 = cross-track touch detected without tag escape (BLOCK)
- 2 = invocation error (no git, no msg file, etc.)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import List, Set


# Soft line A files / SHARED files — commit-msg-stage block-with-tag-escape
# scope. These are line A files that the pre-commit stage does NOT
# hard-block (because they legitimately get co-edited via [shared] /
# [cross-track-ack] flows), but should still trip a block when paired
# with line B unless tagged.
LINE_A_SHARED_PATTERNS = [
    r"^docs/adr/ADR-002-.*\.md$",
    r"^\.github/workflows/ci\.yml$",
    r"^\.planning/ops/.*\.md$",
    r"^\.planning/retrospectives/.*\.md$",
    r"^docs/methodology/.*\.md$",
    r"^scripts/check_track_isolation.*\.py$",
    r"^\.pre-commit-config\.yaml$",
    r"^bin/dev-session-init$",
    r"^\.gitmessage$",
    r"^CLAUDE\.md$",
    r"^pyproject\.toml$",
    r"^tests/conftest\.py$",
]

# Line B file path prefixes (case simulation arc) — same as pre-commit stage.
LINE_B_PREFIXES = (
    "knowledge/gold_standards/",
    "reports/phase5_audit/",
    "reports/phase5_fields/",
    "reports/cylinder_crossflow/",
    "reports/differential_heated_cavity/",
    "reports/rayleigh_benard_convection/",
    "reports/turbulent_flat_plate/",
    "reports/deep_acceptance/",
    "whitelist_cases/",
    "ui/frontend/public/flow-fields/",
    ".planning/intake/DEC-V61-",
    ".planning/decisions/",
)


def _is_line_a_shared(path: str) -> bool:
    return any(re.match(pat, path) for pat in LINE_A_SHARED_PATTERNS)


def _is_line_b(path: str) -> bool:
    if path.startswith(LINE_B_PREFIXES):
        return True
    if re.match(r"^src/(foam_agent_adapter|comparator_gates|result_comparator)\.py$", path):
        return True
    if re.match(r"^src/(cylinder|airfoil|wall_gradient|plane_channel)_.*\.py$", path):
        return True
    if re.match(r"^tests/test_(phase_e2e|foam_agent_adapter|cylinder|airfoil|naca|rayleigh|differential_heated|turbulent_flat|backward_facing|axisymmetric)", path):
        return True
    return False


def _staged_files() -> List[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


# Regex for legitimizing tags. Each is matched on the message body
# (anywhere — header or body). The [cross-track-ack: ...] form
# requires a non-empty reason.
TAG_PATTERNS = [
    re.compile(r"\[cross-track-ack:\s*[^\]\s][^\]]*\]"),
    re.compile(r"\[shared\]"),
    re.compile(r"\[deps\]"),
    re.compile(r"\[ops\]"),
]


def _has_legitimizing_tag(msg: str) -> bool:
    return any(p.search(msg) for p in TAG_PATTERNS)


def _read_msg(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        sys.stderr.write(
            "check_track_isolation_msg.py: missing commit-msg file argument\n"
        )
        return 2

    msg_path = argv[1]
    msg = _read_msg(msg_path)
    # Strip comment lines (lines starting with '#') — those are
    # template / instructional content, not author commitment.
    msg_body = "\n".join(
        line for line in msg.splitlines() if not line.lstrip().startswith("#")
    )

    files = _staged_files()
    if not files:
        return 0

    a_shared_hits: Set[str] = set()
    b_hits: Set[str] = set()
    for path in files:
        if _is_line_a_shared(path):
            a_shared_hits.add(path)
        if _is_line_b(path):
            b_hits.add(path)

    if not (a_shared_hits and b_hits):
        return 0  # No cross-track between SHARED line A and line B.

    if _has_legitimizing_tag(msg_body):
        return 0  # Author tagged the commit explicitly; let it through.

    sys.stderr.write(
        "\n"
        "🛑  OPS-2026-04-25-001 §3 v2 dual-track isolation BLOCK (commit-msg stage)\n"
        "    Commit touches SHARED line A files AND line B files in the\n"
        "    same index, but the commit message has no legitimizing tag.\n"
        "\n"
        "    Line A SHARED files staged:\n"
    )
    for p in sorted(a_shared_hits):
        sys.stderr.write(f"      - {p}\n")
    sys.stderr.write("\n    Line B files staged:\n")
    for p in sorted(b_hits):
        sys.stderr.write(f"      - {p}\n")
    sys.stderr.write(
        "\n"
        "    To proceed, add ONE of these tags to the commit message:\n"
        "      [cross-track-ack: <one-line reason>]   (legitimate cross-track edit)\n"
        "      [shared]                                (intentional shared infra)\n"
        "      [deps]                                  (pure dep/lockfile bump)\n"
        "      [ops]                                   (governance doc touching both)\n"
        "\n"
        "    Note: [line-a] or [line-b] alone are NOT escapes — those are\n"
        "    single-track markers; using one while staging the other track\n"
        "    is exactly the cross-track-absorption mistake this hook catches.\n"
        "\n"
        "    Alternatively, un-stage one track and split into two commits.\n"
        "\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
