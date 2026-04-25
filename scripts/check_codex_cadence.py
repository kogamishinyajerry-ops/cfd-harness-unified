#!/usr/bin/env python3
"""Codex-verified cadence + risk-class hook (pre-push).

Authority chain:
  - Opus 4.7 review 2026-04-25 (round 1) — original cadence floor (count-only)
  - Opus 4.7 review 2026-04-26 (round 2) Q5+Q14 — close bootstrap cliff
    + add risk-class trigger table (count-only floor was the same loophole
    that produced the 19-commit/0-Codex rollout, just delayed)

Two independent gates; failing either blocks the push:

  1. **Cadence floor**: count commits since the most recent canonical
     `Codex-verified:` trailer. Threshold {THRESHOLD}. Bootstrap iff the
     trailer has *never* existed in repo history (full `git log` scan,
     no `LOOKBACK` cliff — Q5 fix).

  2. **Risk-class trigger** (Q14 fix): the diff being pushed touches
     files / patterns that round-2 review classed as
     'Codex-required regardless of cadence count'. Examples:
       - new files under `routes/**`
       - new files under `pages/**`
       - LOC delta > {RISK_LOC_THRESHOLD}
       - any change to security-path globs (`_validate_*`, `_safe_*`)
       - new SSE / WebSocket route handlers
     If matched and HEAD does not already carry a canonical trailer,
     the push is blocked.

Override: `CODEX_CADENCE_OVERRIDE=1 git push`. Round-2 Q6 (override
audit trail) lands in PR-2 — for now the override is stderr-only.

Stdin contract: pre-push hooks receive `<local_ref> <local_sha>
<remote_ref> <remote_sha>` lines on stdin. We use `local_sha` to find
the diff range. If stdin is empty (manual invocation, tests), we fall
back to comparing HEAD against `origin/main` if reachable, else skip
the risk-class gate (cadence still runs).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

THRESHOLD = 10
RISK_LOC_THRESHOLD = 500

# Canonical trailer (Round-1 spec): four explicit verdicts only.
TRAILER_RE = (
    r"^Codex-verified: (APPROVE|APPROVE_WITH_COMMENTS|"
    r"CHANGES_REQUIRED|RESOLVED)\b"
)
TRAILER_GIT_GREP = (
    "Codex-verified: "
    "(APPROVE|APPROVE_WITH_COMMENTS|CHANGES_REQUIRED|RESOLVED)"
)


# Risk-class trigger globs (Q14): paths matching any of these in the
# pushed diff cause Codex to be REQUIRED even when cadence count < threshold.
# Curated to capture round-2's specific failure mode: new product surface
# + new HTTP route + new security boundary all slipped past count-only.
RISK_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^ui/backend/routes/[^/]+\.py$"),       # new HTTP route file
    re.compile(r"^ui/frontend/src/pages/[^/]+\.tsx$"),  # new top-level page
    re.compile(
        r"^ui/frontend/src/pages/[^/]+/[^/]+\.tsx$"     # nested pages (workbench/, learn/)
    ),
    re.compile(r"^scripts/check_[A-Za-z_]+\.py$"),      # new governance hook
    re.compile(r"^src/foam_agent_adapter\.py$"),        # solver-adapter contract
    re.compile(r"^\.importlinter$"),                    # import contract changes
    re.compile(r"^\.pre-commit-config\.yaml$"),         # hook config
]

# Names that look like security boundaries — match anywhere in the diff.
RISK_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b_validate_[A-Za-z_]+\b"),
    re.compile(r"\b_safe_[A-Za-z_]+\b"),
    re.compile(r"StreamingResponse\b"),  # SSE / streaming endpoints
    re.compile(r"\bEventSource\b"),
]


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def _try_run(cmd: list[str]) -> str | None:
    try:
        return _run(cmd)
    except subprocess.CalledProcessError:
        return None


def _find_last_verified_sha() -> str | None:
    """Q5: full-history scan. Returns the SHA of the most recent commit
    whose body carries a canonical Codex-verified trailer, or None if
    none has ever existed."""
    raw = _try_run([
        "git", "log",
        "-E", "--grep", TRAILER_GIT_GREP,
        "--pretty=%H%x00%B%x00%x00",
    ])
    if raw is None:
        return None
    pattern = re.compile(TRAILER_RE, re.MULTILINE)
    for entry in raw.split("\x00\x00"):
        entry = entry.strip("\n").lstrip("\x00")
        if not entry or "\x00" not in entry:
            continue
        sha, body = entry.split("\x00", 1)
        if pattern.search(body):
            return sha
    return None


def _head_carries_trailer() -> bool:
    body = _try_run(["git", "log", "-1", "--pretty=%B", "HEAD"])
    if body is None:
        return False
    return bool(re.search(TRAILER_RE, body, re.MULTILINE))


# --- Risk-class detection --------------------------------------------------

def _diff_range_from_stdin() -> tuple[str, str] | None:
    """pre-push protocol: lines `local_ref local_sha remote_ref remote_sha`
    on stdin. Returns (remote_sha, local_sha) for the FIRST non-deletion
    line, or None if stdin is empty / malformed.
    """
    if sys.stdin.isatty():
        return None
    try:
        data = sys.stdin.read()
    except Exception:
        return None
    if not data.strip():
        return None
    for line in data.strip().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local_sha, remote_sha = parts[1], parts[3]
        # Skip branch deletions (local_sha is all zeros)
        if set(local_sha) == {"0"}:
            continue
        return (remote_sha, local_sha)
    return None


def _diff_range_fallback() -> tuple[str, str] | None:
    """Fallback when stdin is empty (tests, manual invocation): use
    origin/main..HEAD if reachable. Returns None if origin/main is
    not configured (fresh repo) — caller skips the risk-class gate."""
    if _try_run(["git", "rev-parse", "--verify", "origin/main"]) is None:
        return None
    return ("origin/main", "HEAD")


def _changed_files(remote_sha: str, local_sha: str) -> list[str]:
    raw = _try_run(["git", "diff", "--name-only", f"{remote_sha}..{local_sha}"])
    if not raw:
        return []
    return [line for line in raw.splitlines() if line.strip()]


def _added_loc(remote_sha: str, local_sha: str) -> int:
    """Sum of insertions across the diff (additions only — deletions don't
    add risk surface)."""
    raw = _try_run(["git", "diff", "--shortstat", f"{remote_sha}..{local_sha}"])
    if not raw:
        return 0
    m = re.search(r"(\d+) insertions?\(\+\)", raw)
    return int(m.group(1)) if m else 0


def _diff_text(remote_sha: str, local_sha: str) -> str:
    return _try_run(["git", "diff", f"{remote_sha}..{local_sha}"]) or ""


def _new_files_in_diff(remote_sha: str, local_sha: str) -> list[str]:
    """Files added (not just modified) in the diff. New files are higher
    risk than mods because they introduce new surface entirely."""
    raw = _try_run([
        "git", "diff", "--name-status", "--diff-filter=A",
        f"{remote_sha}..{local_sha}",
    ])
    if not raw:
        return []
    out: list[str] = []
    for line in raw.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0].startswith("A"):
            out.append(parts[1].strip())
    return out


def _detect_risk_triggers() -> list[str]:
    """Returns a list of human-readable trigger reasons the diff matches.
    Empty list means no risk-class gate fires."""
    rng = _diff_range_from_stdin() or _diff_range_fallback()
    if rng is None:
        return []
    remote_sha, local_sha = rng

    triggers: list[str] = []

    new_files = _new_files_in_diff(remote_sha, local_sha)
    for path in new_files:
        for pat in RISK_PATH_PATTERNS:
            if pat.match(path):
                triggers.append(
                    f"new file matches risk path glob: {path} (pattern {pat.pattern})"
                )
                break  # one trigger per file is enough

    loc = _added_loc(remote_sha, local_sha)
    if loc > RISK_LOC_THRESHOLD:
        triggers.append(
            f"diff adds {loc} lines (>RISK_LOC_THRESHOLD={RISK_LOC_THRESHOLD})"
        )

    diff_text = _diff_text(remote_sha, local_sha)
    # Restrict to + lines so we don't trigger on existing code being
    # removed or just shown in context. Also strip the leading '+ '.
    added_lines = [
        line[1:] for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    added_blob = "\n".join(added_lines)
    for pat in RISK_NAME_PATTERNS:
        if pat.search(added_blob):
            triggers.append(
                f"diff introduces security/streaming pattern: {pat.pattern}"
            )

    return triggers


# --- Main ------------------------------------------------------------------

def main() -> int:
    if os.environ.get("CODEX_CADENCE_OVERRIDE") == "1":
        print(
            "[codex-cadence] OVERRIDE active (CODEX_CADENCE_OVERRIDE=1) — "
            "skipping cadence + risk-class gates",
            file=sys.stderr,
        )
        return 0

    last_verified = _find_last_verified_sha()
    head_verified = _head_carries_trailer()

    # --- Gate 1: cadence floor (Q5 fix: full-history, no LOOKBACK cliff) ---
    if last_verified is None:
        # Genuinely never verified — bootstrap mode. Cadence skipped.
        cadence_status = "bootstrap"
        cadence_count = 0
    else:
        try:
            cadence_count = int(_run([
                "git", "rev-list", f"{last_verified}..HEAD", "--count",
            ]))
        except (subprocess.CalledProcessError, ValueError):
            return 0
        if cadence_count >= THRESHOLD:
            print("", file=sys.stderr)
            print(
                f"[codex-cadence] CADENCE BLOCK · {cadence_count} commits "
                f"since last Codex-verified trailer (threshold={THRESHOLD})",
                file=sys.stderr,
            )
            print(
                f"   Last verified commit: {last_verified[:12]}",
                file=sys.stderr,
            )
            print(
                "   Required action: /codex-gpt54 review + add canonical "
                "'Codex-verified: APPROVE|APPROVE_WITH_COMMENTS|"
                "CHANGES_REQUIRED|RESOLVED <summary>' trailer.",
                file=sys.stderr,
            )
            print(
                "   Override (audited via env): "
                "CODEX_CADENCE_OVERRIDE=1 git push",
                file=sys.stderr,
            )
            print("", file=sys.stderr)
            return 1
        cadence_status = "ok"

    # --- Gate 2: risk-class trigger (Q14 fix) -------------------------------
    triggers = _detect_risk_triggers()
    if triggers and not head_verified:
        print("", file=sys.stderr)
        print(
            "[codex-cadence] RISK-CLASS BLOCK · push touches Codex-required "
            "surface area without a canonical trailer on HEAD:",
            file=sys.stderr,
        )
        for t in triggers:
            print(f"   · {t}", file=sys.stderr)
        print(
            "   Required action: /codex-gpt54 review this PR. Even if cadence "
            "count is OK, new routes/pages/governance scripts need Codex.",
            file=sys.stderr,
        )
        print(
            "   Override (audited via env): "
            "CODEX_CADENCE_OVERRIDE=1 git push",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        return 1

    # --- All gates pass -----------------------------------------------------
    if cadence_status == "bootstrap":
        msg_cadence = "bootstrap (no trailer in repo history)"
    else:
        msg_cadence = (
            f"{cadence_count}/{THRESHOLD} since {last_verified[:12]}"
        )
    risk_summary = (
        "no risk triggers" if not triggers
        else f"{len(triggers)} risk trigger(s) but HEAD carries trailer"
    )
    print(
        f"[codex-cadence] OK · cadence={msg_cadence} · risk={risk_summary}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
