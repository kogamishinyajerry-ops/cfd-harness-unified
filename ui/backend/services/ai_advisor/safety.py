"""DEC-V61-158/159 (N6.2/N6.3) · server-side advisory-only enforcement.

Shared text-pattern sanitizer used by both AI 审查 (review) and AI
诊断 (diagnose). The V130 contract says no AI surface emits route
descriptors / button labels / shell mutations; the prompt asks the
LLM to follow it, and this module enforces it server-side before
text reaches the wire.

Per Codex N6.2 R1 P1: the matcher is type-safe — non-string inputs
return False rather than raising TypeError. That keeps a malformed
sibling finding from poisoning the rest of the LLM batch.

Per Codex N6.2 R1 P2: the regex set must stay aligned with the
prompt's FORBIDDEN list. Any new label added to the prompt must
also extend the regex here, and vice versa.
"""
from __future__ import annotations

import re

# Action-text patterns that signal the LLM ignored the advisory-only
# contract. Any finding whose ``message`` or ``recommended_change`` /
# ``suggested_fix`` matches is dropped before reaching the wire.
#
# False positives (legitimate text mentioning HTTP / api / curl as
# diagnostic context) are acceptable: the rule-based fallback covers
# the underlying issue, and the LLM can phrase the same advice
# without action language.
ACTION_TEXT_PATTERNS: tuple[re.Pattern, ...] = (
    # HTTP method + path: "POST /api/...", "PUT /cases/..."
    re.compile(r"\b(POST|PUT|PATCH|DELETE)\s+/", re.IGNORECASE),
    # Bare API path: "/api/cases/{id}/..." — implies route invocation
    re.compile(r"/api/[a-z][a-z0-9_\-/{}]+", re.IGNORECASE),
    # Button-style labels — must stay aligned with the system-prompt
    # FORBIDDEN list authored in each route's prompt builder.
    re.compile(
        r"\[\s*(apply|submit|confirm|commit|save|"
        r"应用|提交|执行|保存)\s*\]",
        re.IGNORECASE,
    ),
    # Shell commands that would mutate the case
    re.compile(
        r"\b(curl|wget|http|httpie)\s+-X\s*(POST|PUT|PATCH|DELETE)",
        re.IGNORECASE,
    ),
    # Direct dispatcher tool invocation phrasing
    re.compile(r"\bdispatch\s*\(\s*tool\s*=", re.IGNORECASE),
)


def has_action_text(text: object) -> bool:
    """Return True iff ``text`` is a string matching any action-text
    pattern.

    None / empty / non-string → False (no risk).

    The non-string branch is load-bearing (Codex N6.2 R1 P1): the
    LLM may emit malformed JSON like ``{"message": [...]}`` or
    ``{"suggested_fix": {"text": ...}}``; if we tried
    ``pattern.search()`` on those, ``re`` would raise TypeError,
    escape the per-finding parser, and the route handler would
    treat it as a whole-LLM failure — discarding any valid sibling
    findings in the same batch. Returning False here lets the
    per-finding Pydantic validation drop the malformed record while
    keeping siblings intact.
    """
    if not isinstance(text, str) or not text:
        return False
    for pattern in ACTION_TEXT_PATTERNS:
        if pattern.search(text):
            return True
    return False


__all__ = ["ACTION_TEXT_PATTERNS", "has_action_text"]
