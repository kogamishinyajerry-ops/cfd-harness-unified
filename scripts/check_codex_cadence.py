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

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

THRESHOLD = 10
RISK_LOC_THRESHOLD = 500
# Round-3 F4: full-history scan safety valve. On a 100k-commit repo the
# unbounded `git log` would pay full O(N) IO every push. 2000 is well
# beyond practical workbench arc length while still bounding the worst
# case. Tunable.
FULL_HISTORY_CAP = 2000
# Round-3 F5: when a risk-class FILE is modified (not just newly added),
# we need a per-file LOC threshold — every typo PR shouldn't ring the
# governance bell, only material changes should. 150 lines is the empirical
# floor between "minor patch" (Codex review unnecessary) and "feature"
# (review warranted). Tunable.
RISK_MOD_LOC_THRESHOLD = 150
OVERRIDE_LOG_PATH = Path(".governance/codex_cadence_overrides.log")
OVERRIDE_REASON_RE = re.compile(r"^Override-reason:\s*(.+)$", re.MULTILINE)

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
    none has ever existed.

    Round-3 F4 safety valve: cap the scan at FULL_HISTORY_CAP commits
    so a 100k-commit repo doesn't pay full O(N) IO on every push. If
    no trailer is found within the cap, treat as "no recent verified
    commit" — same outcome as bootstrap mode for cadence-floor purposes.
    The honesty trade-off: a verified commit older than the cap is
    invisible to the hook. That's acceptable because the cadence rule
    is about RECENT review, not "ever-reviewed in repo history".
    """
    raw = _try_run([
        "git", "log", f"-{FULL_HISTORY_CAP}",
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


def _is_ci_environment() -> bool:
    """Round-3 F10: detect CI/runner context via standard env vars.

    Most CI providers (GitHub Actions, GitLab CI, CircleCI, Travis, Jenkins,
    Buildkite) set `CI=true`. Anyone setting these in a dev shell on
    purpose either knows what they're doing or is exactly the workflow
    we want to audit. Only check `CI` (which is the de-facto standard);
    avoid matching any container env that just happens to set CI=1.
    """
    return os.environ.get("CI", "").lower() in ("1", "true", "yes")


def _head_carries_trailer() -> bool:
    body = _try_run(["git", "log", "-1", "--pretty=%B", "HEAD"])
    if body is None:
        return False
    return bool(re.search(TRAILER_RE, body, re.MULTILINE))


def _head_override_reason() -> str | None:
    """Round-2 Q6: read `Override-reason:` trailer from HEAD commit body.

    The override env var alone is insufficient for audit (round-2 review:
    'stderr OVERRIDE active 不留痕，违反 RETRO-V61-001 governance bar').
    Now the user must ALSO put a reason in the commit message body or set
    `CODEX_OVERRIDE_REASON` env var. Either form is logged.
    """
    body = _try_run(["git", "log", "-1", "--pretty=%B", "HEAD"])
    if body is None:
        return None
    m = OVERRIDE_REASON_RE.search(body)
    if m:
        return m.group(1).strip()
    return None


def _append_override_log(
    reason: str,
    head_sha: str,
    triggers: list[str],
    extra: dict[str, object] | None = None,
) -> None:
    """Round-2 Q6 + round-3 F8: persistent JSONL audit trail.

    Format change (round-3): TSV → JSONL. Round-2 used 5-field TSV which
    breaks if `reason` contains a literal `\\t` (round-3 finding #8). JSONL
    via `json.dumps` escapes tabs / quotes / newlines automatically and
    is the standard append-only audit log format (jq-friendly).

    One JSON object per line:
        {"ts": "...", "sha": "...", "reason": "...",
         "n_triggers": N, "triggers": [...], ...extra}

    `extra` carries optional fields (e.g. `{"backfill": true}` for the
    round-3 F18 PR-1 backfill entry).
    """
    try:
        OVERRIDE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="seconds"
        )
        record: dict[str, object] = {
            "ts": ts,
            "sha": head_sha[:12],
            "reason": reason,
            "n_triggers": len(triggers),
            "triggers": triggers,
        }
        if extra:
            record.update(extra)
        with OVERRIDE_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        # Audit log failure must not block the developer's work, but it
        # should be loud — print to stderr so the failure is visible.
        print(
            f"[codex-cadence] WARNING: could not append override log at "
            f"{OVERRIDE_LOG_PATH}",
            file=sys.stderr,
        )


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


def _changed_risk_files(
    remote_sha: str, local_sha: str
) -> list[tuple[str, str]]:
    """Round-3 F5: extends the risk-class detector to ALSO catch large
    modifications of existing risk-class files (not just additions).

    Returns a list of (status, path) pairs where status is "A" (added)
    or "M" (modified). Renames and deletions are out of scope here —
    rename targets show as A in the second commit anyway, and deletions
    don't add new surface.

    Caller decides per-status policy: A → trigger on any path-glob match;
    M → trigger only if also above RISK_MOD_LOC_THRESHOLD added LOC for
    that specific file.
    """
    raw = _try_run([
        "git", "diff", "--name-status", "--diff-filter=AM",
        f"{remote_sha}..{local_sha}",
    ])
    if not raw:
        return []
    out: list[tuple[str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0][0] in ("A", "M"):
            out.append((parts[0][0], parts[1].strip()))
    return out


def _added_loc_per_file(
    remote_sha: str, local_sha: str, path: str
) -> int:
    """Insertions for a single file via `git diff --numstat`. Used by
    the round-3 F5 mod-threshold check."""
    raw = _try_run([
        "git", "diff", "--numstat",
        f"{remote_sha}..{local_sha}", "--", path,
    ])
    if not raw:
        return 0
    # numstat format: "<added>\t<deleted>\t<path>"; use first column
    first = raw.splitlines()[0]
    parts = first.split("\t")
    if len(parts) < 1 or not parts[0].isdigit():
        return 0
    return int(parts[0])


def _detect_risk_triggers() -> list[str]:
    """Returns a list of human-readable trigger reasons the diff matches.
    Empty list means no risk-class gate fires."""
    rng = _diff_range_from_stdin() or _diff_range_fallback()
    if rng is None:
        return []
    remote_sha, local_sha = rng

    triggers: list[str] = []

    # Round-3 F5: walk both A (added) and M (modified) files. Added files
    # trigger on any path-glob match; modified files require a per-file
    # ≥RISK_MOD_LOC_THRESHOLD added-LOC threshold so typo-fix PRs to
    # routes/wizard.py don't ring the governance bell.
    for status, path in _changed_risk_files(remote_sha, local_sha):
        for pat in RISK_PATH_PATTERNS:
            if not pat.match(path):
                continue
            if status == "A":
                triggers.append(
                    f"new file matches risk path glob: {path} (pattern {pat.pattern})"
                )
                break
            # status == "M"
            file_loc = _added_loc_per_file(remote_sha, local_sha, path)
            if file_loc >= RISK_MOD_LOC_THRESHOLD:
                triggers.append(
                    f"large modification of risk-class file: {path} "
                    f"(+{file_loc} LOC ≥ {RISK_MOD_LOC_THRESHOLD}; "
                    f"pattern {pat.pattern})"
                )
                break

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
    override_active = os.environ.get("CODEX_CADENCE_OVERRIDE") == "1"
    last_verified = _find_last_verified_sha()
    head_verified = _head_carries_trailer()

    if override_active:
        # Round-3 F10: refuse override entirely in CI contexts. CI runners
        # are ephemeral and the audit log is gitignored — overrides done
        # in CI leave no trace. Policy: humans-only override; CI must use
        # a properly-trailered Codex-verified commit instead.
        if _is_ci_environment():
            print("", file=sys.stderr)
            print(
                "[codex-cadence] CI OVERRIDE REFUSED · CI=true detected; "
                "overrides are not permitted in CI/runner contexts.",
                file=sys.stderr,
            )
            print(
                "   Reason: ephemeral runners discard the audit log; bypass "
                "would be undetectable in post-hoc review.",
                file=sys.stderr,
            )
            print(
                "   Required: land a Codex-verified trailer on HEAD before "
                "the CI push, or push from a developer machine.",
                file=sys.stderr,
            )
            print("", file=sys.stderr)
            return 1

        # Round-2 Q6 + round-3 F11: override requires an audit-grade
        # reason. Either an `Override-reason:` trailer on HEAD (preferred —
        # durable in git history) or a CODEX_OVERRIDE_REASON env var
        # (emergency hot-fix path). Both forms strip whitespace and reject
        # empty results explicitly — round-3 #11 flagged the implicit
        # `or None` chain as not obviously rejecting whitespace-only reasons.
        reason_raw = _head_override_reason() or os.environ.get(
            "CODEX_OVERRIDE_REASON", ""
        )
        reason = reason_raw.strip() if reason_raw else ""
        if not reason:
            print("", file=sys.stderr)
            print(
                "[codex-cadence] OVERRIDE BLOCKED · CODEX_CADENCE_OVERRIDE=1 "
                "is set but no audit reason was provided.",
                file=sys.stderr,
            )
            print(
                "   Required (either form):",
                file=sys.stderr,
            )
            print(
                "     (a) add 'Override-reason: <text>' line to HEAD commit body",
                file=sys.stderr,
            )
            print(
                "     (b) set CODEX_OVERRIDE_REASON='<text>' alongside the env var",
                file=sys.stderr,
            )
            print("", file=sys.stderr)
            return 1
        # Compute trigger list so the audit log captures what was bypassed.
        triggers = _detect_risk_triggers()
        head_sha = _try_run(["git", "rev-parse", "HEAD"]) or "(unknown)"
        _append_override_log(reason, head_sha, triggers)
        print(
            f"[codex-cadence] OVERRIDE active (reason: {reason!r}) — bypass "
            f"logged to {OVERRIDE_LOG_PATH}",
            file=sys.stderr,
        )
        return 0

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
                "   Override (audited): set CODEX_CADENCE_OVERRIDE=1 AND provide a reason via",
                file=sys.stderr,
            )
            print(
                "     'Override-reason: <text>' commit trailer or "
                "CODEX_OVERRIDE_REASON='<text>' env var.",
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
