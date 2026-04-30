"""DEC-V61-102 Phase 1.2 · light-weight raw-dict content validation.

We do NOT parse the full OpenFOAM dict grammar (libFOAM's parser is the
authoritative source; reimplementing it in Python would be a tar pit).
Instead we sanity-check the bare minimum that prevents file-corrupting
paste mistakes:

* ``FoamFile { ... }`` header present
* curly-brace balance
* basic structural sanity per-file (e.g. controlDict must have an
  ``application`` key, otherwise solver dispatch would silently fail)

The ``?force=1`` query flag in the route bypasses validation entirely
for the "I know what I'm doing" path. That flag still records the edit
in manifest history (so if the run later fails, the audit log shows
the user opted to bypass).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One concern raised about the dict text. ``severity`` controls
    whether the route layer treats it as 422 (error) or 200-with-warnings
    (advisory)."""

    severity: str  # "error" | "warning"
    message: str


_FOAM_FILE_HEADER = re.compile(r"\bFoamFile\s*\{", re.MULTILINE)
_APPLICATION_LINE = re.compile(r"^\s*application\s+\S+\s*;", re.MULTILINE)


def _check_brace_balance(text: str) -> int:
    """Return (open_count - close_count). Zero means balanced. We
    deliberately ignore string-literal escapes — OpenFOAM dicts rarely
    contain quoted braces, and false positives there are louder than
    silently passing a corrupt file."""
    return text.count("{") - text.count("}")


def validate_raw_dict(
    *, relative_path: str, content: str
) -> list[ValidationIssue]:
    """Run every applicable check for ``relative_path`` against
    ``content``. Returns the list of issues (empty = clean).

    The check set is minimal by design: each rule corresponds to a
    failure mode that has been observed to crash OpenFOAM with a
    cryptic error if missed. Adding more checks here is fine, but each
    new rule needs a regression test.
    """
    issues: list[ValidationIssue] = []

    # All OpenFOAM dict files start with a FoamFile header. Missing it
    # leads to "FoamFile not found" cryptic errors at runtime.
    if not _FOAM_FILE_HEADER.search(content):
        issues.append(
            ValidationIssue(
                severity="error",
                message="missing FoamFile header — every OpenFOAM dict must "
                "start with `FoamFile { ... }`",
            )
        )

    # Brace balance: catches paste mistakes that would otherwise produce
    # a syntax error 50 lines into the file.
    delta = _check_brace_balance(content)
    if delta != 0:
        sign = "extra opening" if delta > 0 else "extra closing"
        issues.append(
            ValidationIssue(
                severity="error",
                message=f"unbalanced braces ({sign} {abs(delta)})",
            )
        )

    # Per-file sanity checks.
    if relative_path == "system/controlDict":
        if not _APPLICATION_LINE.search(content):
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="controlDict missing `application <solver>;` "
                    "line — solver dispatch reads this field",
                )
            )

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    """Convenience predicate for the route's 422 decision."""
    return any(i.severity == "error" for i in issues)


__all__ = ["ValidationIssue", "validate_raw_dict", "has_errors"]
