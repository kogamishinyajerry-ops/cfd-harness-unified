#!/usr/bin/env python3
"""Codex-verified cadence hook (pre-push).

Opus 4.7 review 2026-04-25 governance amendment. The workbench rollout
shipped 19 commits with 0 Codex-review calls — RETRO-V61-001 had made
Codex-per-risky-PR a baseline rule, but "risky" is judgment-dependent
and the rollout slipped through. This hook adds a cadence floor: if
you've gone THRESHOLD commits without a `Codex-verified:` trailer,
push is blocked until you either

  (a) run /codex-gpt54 review on a recent risky PR and add the trailer
      to a follow-up commit (or amend the verified commit), or
  (b) override with `CODEX_CADENCE_OVERRIDE=1 git push` (audited).

Trailer pattern: lines starting with `Codex-verified:` in the commit
message body. Status text after the colon is freeform (typically
APPROVE / APPROVE_WITH_COMMENTS / CHANGES_REQUIRED → RESOLVED).

The hook is intentionally permissive on bootstrap (no trailer found in
the last 50 commits) — first-time installs in older repos shouldn't
brick the dev shell. Once the project has at least one verified commit,
the cadence rule activates.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

THRESHOLD = 10
# Match real Codex verdicts only — "Codex-verified: pending" / "tbd" / etc.
# do NOT count toward cadence. The verdict must be one of the four canonical
# review outcomes from /codex-gpt54.
TRAILER_RE = (
    r"^Codex-verified: (APPROVE|APPROVE_WITH_COMMENTS|"
    r"CHANGES_REQUIRED|RESOLVED)\b"
)
LOOKBACK = 50


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def main() -> int:
    if os.environ.get("CODEX_CADENCE_OVERRIDE") == "1":
        print(
            "[codex-cadence] OVERRIDE active (CODEX_CADENCE_OVERRIDE=1) — skipping",
            file=sys.stderr,
        )
        return 0

    try:
        # Two-step: grep loosely with git (POSIX ERE — no `^` line anchor
        # since git --grep operates on the full message text, no `\b` word
        # boundary since POSIX ERE doesn't recognize it), then filter to
        # true line-anchored matches in Python with re.MULTILINE. This
        # rejects accidental body mentions like
        # "(see Codex-verified: APPROVE in #123)".
        loose_re = (
            "Codex-verified: "
            "(APPROVE|APPROVE_WITH_COMMENTS|CHANGES_REQUIRED|RESOLVED)"
        )
        commits = _run(
            [
                "git", "log", f"-{LOOKBACK}",
                "-E", "--grep", loose_re, "--pretty=%H%x00%B%x00%x00",
            ]
        )
    except subprocess.CalledProcessError:
        # If git itself misbehaves, don't block — fail open
        return 0

    log: list[str] = []
    pattern = re.compile(TRAILER_RE, re.MULTILINE)
    for entry in commits.split("\x00\x00"):
        entry = entry.strip("\n").lstrip("\x00")
        if not entry or "\x00" not in entry:
            continue
        sha, body = entry.split("\x00", 1)
        if pattern.search(body):
            log.append(sha)

    if not log:
        print(
            f"[codex-cadence] no canonical Codex-verified trailer in last "
            f"{LOOKBACK} commits — bootstrap mode, not blocking. The trailer "
            "must match: 'Codex-verified: APPROVE|APPROVE_WITH_COMMENTS|"
            "CHANGES_REQUIRED|RESOLVED'. Once the first real verdict lands, "
            "the cadence rule activates.",
            file=sys.stderr,
        )
        return 0

    last_verified = log[0]
    try:
        count = int(_run(["git", "rev-list", f"{last_verified}..HEAD", "--count"]))
    except (subprocess.CalledProcessError, ValueError):
        return 0

    if count >= THRESHOLD:
        print("", file=sys.stderr)
        print(
            f"[codex-cadence] {count} commits since last Codex-verified "
            f"trailer (threshold={THRESHOLD})",
            file=sys.stderr,
        )
        print(f"   Last verified commit: {last_verified[:12]}", file=sys.stderr)
        print(
            "   Required action: run /codex-gpt54 review on a recent risky PR,",
            file=sys.stderr,
        )
        print(
            "   then add a 'Codex-verified: APPROVE|APPROVE_WITH_COMMENTS|"
            "CHANGES_REQUIRED|RESOLVED <summary>' trailer (new commit or amend).",
            file=sys.stderr,
        )
        print(
            "   Override (audited via env var): "
            "CODEX_CADENCE_OVERRIDE=1 git push",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        return 1

    print(
        f"[codex-cadence] {count} commits since last Codex-verified "
        f"({last_verified[:12]}) — within threshold {THRESHOLD}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
