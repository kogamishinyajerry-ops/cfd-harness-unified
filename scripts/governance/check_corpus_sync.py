#!/usr/bin/env python3
"""Corpus drift-prevention hook (commit-msg stage).

Fails the commit if the methodology master copy
(`.planning/methodology/industrial_case_solver_findings.md`) is staged
but the runtime advisor corpus copy
(`docs/openfoam_corpus/industrial_solver_findings_v_series.md`) is
NOT staged in the same commit.

Closes the gap that caused the V57→V84 (27-row) arrears surfaced by
Codex P2 on commit e56f160..e89a88f and synced 2026-05-13 in `a0effac`.
Recommended option 1 from methodology §"Corpus sync arrears".

Bypass paths:
  (a) Add trailer `Corpus-sync-defer: <reason>` to commit message
      (use for trailer-only / governance-only commits that don't
      modify V-rows or amendments).
  (b) Hard bypass via `git commit --no-verify` (audited).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

METHODOLOGY = ".planning/methodology/industrial_case_solver_findings.md"
RUNTIME_COPY = "docs/openfoam_corpus/industrial_solver_findings_v_series.md"
TRAILER_PREFIX = "Corpus-sync-defer:"


def staged_files() -> set[str]:
    """Return set of paths staged in the index."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return set()
    return {p for p in out.splitlines() if p}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        # Misuse: don't break the commit, just no-op.
        return 0

    msg_path = Path(argv[1])
    msg = msg_path.read_text() if msg_path.exists() else ""

    files = staged_files()
    if METHODOLOGY not in files:
        return 0  # nothing to check
    if RUNTIME_COPY in files:
        return 0  # synced in same commit
    if any(line.startswith(TRAILER_PREFIX) for line in msg.splitlines()):
        return 0  # explicit opt-out

    print(
        "\n✗ Corpus drift detected:\n"
        f"  staged:   {METHODOLOGY}\n"
        f"  missing:  {RUNTIME_COPY}\n\n"
        "The methodology file is changing without the runtime advisor copy.\n"
        "This is the gap that produced the V57→V84 (27-row) arrears\n"
        "(surfaced by Codex P2 on e56f160..e89a88f, closed 2026-05-13 in a0effac).\n\n"
        "Resolution options:\n"
        f"  (a) Stage the runtime copy too (preferred):\n"
        f"      git add {RUNTIME_COPY}\n"
        "  (b) If this commit is intentionally trailer-only (no new V-row /\n"
        "      no amendment), add to commit message:\n"
        "      Corpus-sync-defer: <reason>\n"
        "  (c) Hard bypass (audited):\n"
        "      git commit --no-verify\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
