"""Shared path-safety contract for CWOS.

Single source of truth for "is this evidence path safe to display as proof
that work was done?". Used by:

  - tools/cwos_render_dashboard.py  (Bright Spots filter + phantom counter)
  - tools/cwos_status.py             (project_status.json metrics + overall_status)
  - tests/test_red_team_safety.py    (event-log integrity check)

Red Team R3-F-01 / R3-F-05 fix: before this module, two places implemented
`(repo_root / rel).exists()` independently. pathlib drops the left operand
when the right is absolute, so both checks were bypassed by absolute paths
and `..`-traversal. Centralizing the rule prevents the pattern from drifting
back in.

A path is "safe and exists" only if ALL of:
  - it is not absolute
  - it does not escape `repo_root` after symlink resolution
  - it resolves to a file/dir that exists on disk
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def path_is_safe_relative(rel: str, repo_root: Path) -> Tuple[bool, str]:
    """
    Return (is_safe_and_exists, reason).

    `is_safe_and_exists` is True only when `rel` is a relative path that
    resolves (with symlinks followed) to a real filesystem object contained
    within `repo_root`.

    `reason` is empty when safe, otherwise a short diagnostic.
    """
    if not isinstance(rel, str) or not rel:
        return False, "empty or non-string evidence entry"
    if Path(rel).is_absolute():
        return False, f"absolute path rejected: {rel}"
    candidate = repo_root / rel
    try:
        resolved = candidate.resolve()
        resolved_root = repo_root.resolve()
    except (OSError, ValueError) as e:
        # R5-F-01 fix: Path.resolve()'s lstat raises ValueError on null-byte
        # filenames. Catch it alongside OSError so a malformed path cleanly
        # rejects instead of crashing the cockpit refresh pipeline.
        return False, f"resolve failed: {e}"
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return False, f"path escapes repo_root: {rel} -> {resolved}"
    if not resolved.exists():
        return False, f"path does not exist: {rel}"
    # R5-F-02 fix: evidence must be a regular file, not a directory and not
    # the repo root itself. Closes:
    #   - evidence=["."] (resolves to repo_root, a directory)
    #   - evidence=["some_dir/"] (resolves to a directory)
    #   - string-as-list tamper `"evidence": "."` (single-char iter → ".")
    if not resolved.is_file():
        return False, f"evidence must be a regular file, not directory or special: {rel}"
    return True, ""


def evidence_paths_all_safe_and_exist(
    evidence: List[str], repo_root: Path
) -> bool:
    """True iff every evidence path is safe-relative and exists."""
    return all(path_is_safe_relative(p, repo_root)[0] for p in evidence)


def first_unsafe_evidence_reason(
    evidence: List[str], repo_root: Path
) -> str | None:
    """Diagnostic helper for tests. Return the first failure reason, or None."""
    for p in evidence:
        ok, reason = path_is_safe_relative(p, repo_root)
        if not ok:
            return reason
    return None


# ---------- event-log utilities ----------


def iter_pass_events_with_evidence(events_log: Path) -> List[Dict[str, Any]]:
    """Yield PASS events that declare a non-empty evidence list. No path check."""
    if not events_log.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in events_log.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("status") == "PASS" and e.get("evidence"):
            out.append(e)
    return out


def count_phantom_pass_events(events_log: Path, repo_root: Path) -> int:
    """
    Number of PASS events with at least one evidence entry that is NOT
    safe-relative-and-existing. This is the canonical phantom counter.
    """
    return sum(
        1
        for e in iter_pass_events_with_evidence(events_log)
        if not evidence_paths_all_safe_and_exist(e.get("evidence", []), repo_root)
    )
