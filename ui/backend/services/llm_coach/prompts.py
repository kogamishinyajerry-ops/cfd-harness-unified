"""DEC-V61-119 · governance-aware system prompt composition.

Pure function — no I/O, no LLM tool registry, no orchestration. Given
a :class:`CaseCompletenessReport` snapshot and the project rules text,
return the system message string the route handler will prepend to
the user's history before opening the LLM stream.

Design constraints (per DEC-V61-119 §risk register):
  * ``max_missing_to_inline`` caps the inlined missing-field list so
    the prompt stays bounded as completeness reports grow large
    (Risk-5).
  * ``suggested_default`` values are skipped when they look like
    secrets — operator-authored data is the source, but defensive
    heuristics protect against accidental token leakage (Risk-6).
  * The role preamble explicitly names the LLM as a *read-only
    adviser* — no autonomous actions, must point engineer at
    ``field_path`` coordinates rather than fabricate data (Risk-4).
"""
from __future__ import annotations

import re
from typing import Iterable

from ui.backend.services.case_completeness import (
    CaseCompletenessReport,
    MissingField,
)

# Role + governance preamble. Kept compact; the bulk of token budget
# goes to the inlined case state below.
DEFAULT_PROJECT_RULES = """\
You are the CFD Harness AI coach. Your role is to help an engineer \
complete and validate a CFD case under the project's governance rules.

Hard constraints:
  * Read-only adviser. You MUST NOT claim to perform autonomous \
actions — the UI applies edits, not you.
  * Point the engineer at the exact ``field_path`` coordinates the \
case-completeness analyzer reported. DO NOT invent field paths or \
fabricate values you weren't told.
  * "Critical" severity blocks ``ready_for_archive``. "Warning" and \
"info" are surfaced for awareness but do NOT block.
  * If the engineer asks for a value you don't see in the snapshot, \
say so plainly and suggest where to look (the manifest schema, the \
gold-standard physics_contract, or operator override) — do not \
guess.
  * Respect the engineer's language preference. The completeness \
analyzer may have authored ``why`` strings in zh-CN; reply in the \
same language unless the engineer switches.
"""


# Heuristic: a suggested_default value of >40 chars matching common
# token shapes is probably a secret slipped in by mistake. Skip it
# from the prompt (the missing-field entry is still surfaced; just
# without the suspect value).
_SECRET_SHAPE_RE = re.compile(
    r"^("
    r"sk-[A-Za-z0-9_-]{20,}"          # OpenAI/DeepSeek-style API keys
    r"|ey[A-Za-z0-9_-]{20,}"          # JWT
    r"|[A-Fa-f0-9]{40,}"              # sha1+/sha256 hex
    r"|[A-Za-z0-9_-]{60,}"            # generic long opaque token
    r")$"
)


def _looks_like_secret(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) <= 40:
        return False
    return bool(_SECRET_SHAPE_RE.match(value))


def _format_missing_entry(entry: MissingField) -> str:
    """Render one missing-field row for the inlined snapshot.

    ``suggested_default`` is dropped if it looks like a secret;
    otherwise it's included so the LLM can offer it in its reply.
    """
    bullet = (
        f"- [{entry.severity.upper()}] field_path={entry.field_path} · "
        f"why={entry.why}"
    )
    if entry.suggested_default is not None and not _looks_like_secret(
        entry.suggested_default
    ):
        bullet += f" · suggested_default={entry.suggested_default!r}"
    return bullet


def _select_top_missing(
    missing: Iterable[MissingField],
    limit: int,
) -> tuple[list[MissingField], int]:
    """Pick up to ``limit`` entries, prioritizing critical > warning > info.

    Returns ``(picked, remainder_count)`` where ``remainder_count``
    counts how many entries did NOT make the cut (so the prompt can
    summarize "+ N more entries — ask to expand").
    """
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    sorted_entries = sorted(
        missing, key=lambda e: severity_rank.get(e.severity, 99)
    )
    picked = sorted_entries[:limit]
    remainder = max(0, len(sorted_entries) - limit)
    return picked, remainder


def build_coach_system_prompt(
    report: CaseCompletenessReport,
    project_rules: str = DEFAULT_PROJECT_RULES,
    *,
    max_missing_to_inline: int = 8,
) -> str:
    """Compose the coach system prompt from a completeness snapshot.

    Layers (in order):
      1. Project rules / role preamble (governance constraints).
      2. Case state line (case_id, kind, percentage, ready_for_archive,
         blocked_by_critical).
      3. Top-N missing fields, severity-ranked.
      4. Notes from the analyzer (if any) — surfaced verbatim so the
         LLM can quote the analyzer's own reasoning.

    Pure: no provider calls, no env reads, no logging side-effects.
    """
    if max_missing_to_inline < 0:
        raise ValueError("max_missing_to_inline must be non-negative")

    parts: list[str] = [project_rules.rstrip()]

    parts.append("")  # blank separator
    parts.append("=== Current case snapshot ===")
    parts.append(
        f"case_id={report.case_id} · case_kind={report.case_kind} · "
        f"completeness={report.percentage}% "
        f"({report.present_count}/{report.total_count} fields present) · "
        f"ready_for_archive={report.ready_for_archive} · "
        f"blocked_by_critical={report.blocked_by_critical}"
    )

    if report.missing:
        picked, remainder = _select_top_missing(
            report.missing, max_missing_to_inline
        )
        parts.append("")
        parts.append("=== Missing-field snapshot (top "
                     f"{len(picked)} of {len(report.missing)}, "
                     "severity-ranked) ===")
        parts.extend(_format_missing_entry(entry) for entry in picked)
        if remainder > 0:
            parts.append(
                f"... + {remainder} more missing entries (lower severity); "
                "ask the engineer if they want the full list."
            )
    else:
        parts.append("")
        parts.append(
            "=== Missing-field snapshot ===\n"
            "(none — all expected fields are present)"
        )

    if report.notes:
        parts.append("")
        parts.append("=== Analyzer notes ===")
        parts.extend(f"- {note}" for note in report.notes)

    return "\n".join(parts)
