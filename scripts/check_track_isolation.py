#!/usr/bin/env python3
"""Pre-commit-stage block-with-env-escape isolation guard for OPS-2026-04-25-001.

v2 (2026-04-25T21:50 · Opus 4.7 §3 v2 supersede): graduated severity
model. This script is the **pre-commit stage** half (looks at
``git diff --cached`` only, NEVER at commit message). The commit-msg
stage half is ``scripts/check_track_isolation_msg.py``.

Authority: ``.planning/ops/2026-04-25_dual_track_plan.md`` §3 v2 +
Notion Opus 4.7 audit on OPS page block 31
(id 29c8696d-84e9-4484-94db-1391f43d0df4) · 2026-04-25T15:10 +0800.
Active during dogfood window 2026-04-25 → 2026-05-19; the script
itself auto-retires after expires date (header docstring of OPS).

# Severity model

- **CORE line A files** (LINE_A_SOLE_PATTERNS below): the 7 strict
  line A authority files. Touching these from a commit that ALSO
  touches LINE_B files triggers a HARD BLOCK at pre-commit stage.
  Escape: per-invocation env var ``CROSS_TRACK_ACK=1``.
- **Soft line A files / SHARED files**: handled by the commit-msg
  stage hook (block with [cross-track-ack: <reason>] / [shared] tag
  escape). Pre-commit stage ignores these.

# Usage

```
python scripts/check_track_isolation.py
```

(Pre-commit framework invokes this with no args at pre-commit stage.)

Exit codes:
- 0 = no cross-track touch OR ``CROSS_TRACK_ACK=1`` set (clean)
- 1 = cross-track touch detected without env escape (BLOCK)
- 2 = invocation error (no git, etc.)

# Why no commit message access here

The commit message file (`.git/COMMIT_EDITMSG`) does not exist yet at
pre-commit stage — it is created later, before commit-msg stage. This
script intentionally does not try to read it; tag-based escape lives
in the sibling commit-msg hook.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import List, Set


# CORE line A authority files — pre-commit-stage hard-block scope.
# These are the 7 files Opus 4.7 §3 v2 enumerates as "line A SOLE".
LINE_A_SOLE_PATTERNS = [
    r"^src/_plane_guard\.py$",
    r"^src/_plane_assignment\.py$",
    r"^src/__init__\.py$",
    r"^\.importlinter$",
    r"^scripts/gen_importlinter\.py$",
    r"^scripts/plane_guard_rollback_eval\.py$",
    r"^\.github/workflows/plane_guard_rollback_cron\.yml$",
]

# Line B file path prefixes (case simulation arc).
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


def _is_line_a_sole(path: str) -> bool:
    return any(re.match(pat, path) for pat in LINE_A_SOLE_PATTERNS)


def _is_line_b(path: str) -> bool:
    if path.startswith(LINE_B_PREFIXES):
        return True
    # Per-case extractors and adapters (line B Execution + Evaluation planes)
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


def main() -> int:
    files = _staged_files()
    if not files:
        return 0

    a_sole_hits: Set[str] = set()
    b_hits: Set[str] = set()
    for path in files:
        if _is_line_a_sole(path):
            a_sole_hits.add(path)
        if _is_line_b(path):
            b_hits.add(path)

    if not (a_sole_hits and b_hits):
        return 0  # No cross-track between CORE line A and line B.

    if os.environ.get("CROSS_TRACK_ACK") == "1":
        # Explicit per-invocation escape — caller has acknowledged.
        return 0

    sys.stderr.write(
        "\n"
        "🛑  OPS-2026-04-25-001 §3 v2 dual-track isolation BLOCK (pre-commit stage)\n"
        "    Commit touches CORE line A authority files AND line B files\n"
        "    in the same index. This is the most likely path to silent\n"
        "    cross-track absorption (e.g., `git add -A` / `git add .`\n"
        "    sweeping both lines into one commit · 2x occurred 2026-04-25).\n"
        "\n"
        "    Line A SOLE files staged:\n"
    )
    for p in sorted(a_sole_hits):
        sys.stderr.write(f"      - {p}\n")
    sys.stderr.write("\n    Line B files staged:\n")
    for p in sorted(b_hits):
        sys.stderr.write(f"      - {p}\n")
    sys.stderr.write(
        "\n"
        "    To proceed (legitimate cross-track edit, e.g. §4.1 PLANE_OF\n"
        "    dict update for a new src.* module added by line B):\n"
        "        CROSS_TRACK_ACK=1 git commit ...\n"
        "\n"
        "    OR un-stage either line A or line B files and commit each\n"
        "    track separately (recommended for non-§4.1 cases).\n"
        "\n"
        "    The commit-msg stage hook ALSO requires either a\n"
        "    [cross-track-ack: <reason>] or [shared] tag in the message\n"
        "    once you proceed past this block (block-with-tag-escape).\n"
        "\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
