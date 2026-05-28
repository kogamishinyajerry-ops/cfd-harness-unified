"""Solver-block extractor · case_dir → SolverBlockSnapshot | None (v0.1).

Per DEC-V61-211. Reads `<case_dir>/system/controlDict` and pulls three
fields used by `geometry_ingest.solver_block_advisor.check_solver_block`:

  - `solver`           ← `application <name>;`        (required; None ⇒ skip)
  - `adjust_time_step` ← `adjustTimeStep <bool>;`     (optional; None if absent)
  - `delta_t`          ← `deltaT <float>;`            (optional; None if absent)

The fourth `SolverBlockSnapshot` field — `preconditioners` — is
**intentionally NOT extracted** in v0.1 (DEC-211 §"Out (deferred to v0.2)"):
it requires walking `fvSolution.solvers.<field>` blocks, including
OpenFOAM regex-pattern keys like `"(U|k|omega)"` that expand to multiple
fields. v0.1 returns an empty preconditioners mapping. A downstream
advisor that needs preconditioner data will silently see "no
preconditioner info" — never "wrong preconditioner info" — preserving
truth-chain (omission, not fabrication).

## Scope-locked NON-features (extractor will NOT parse correctly)

  - Preconditioner data (v0.2 / follow-on sub-DEC; intentional omission).
  - `#include`d sub-dicts: a `controlDict` that pulls `application` from
    a separate file via `#includeFunc` is not followed; returns None.
  - Macro substitution: `application $solverChoice;` — the `$solverChoice`
    literal would be captured as the solver name (garbage in / garbage out).
    No real case in `.planning/case_profiles/*_dicts/` uses this pattern
    today (verified 2026-05-28), and a follow-on sub-DEC can add macro
    resolution if a real case needs it.
  - Multi-line/computed `deltaT` (e.g. `#calc "1e-3 * 5"`): the regex
    matches only a single-token value; a `#calc` expression won't match
    and `delta_t` will be left None (honest omission, not wrong number).

## Why line-anchored regex (not a generic OF-dict parser)

A general OpenFOAM-dict parser is multi-hour, edge-case-heavy
infrastructure (regex keys, includes, macros, embedded code). This
extractor's three keys (`application`, `adjustTimeStep`, `deltaT`) appear
as `key value;` at the top level of `controlDict` and not anywhere else
in standard `controlDict`s — so a line-anchored regex over a
comment-stripped buffer is correct and bounded for the in-repo case
profiles (verified by `tests/test_solver_block_extractor.py`).
"""
from __future__ import annotations

import re
from pathlib import Path

from ui.backend.services.geometry_ingest.solver_block_advisor import (
    SolverBlockSnapshot,
)

__all__ = ["extract"]


# Strip C++ line comments (`// …` to EOL) and block comments (`/* … */`,
# possibly spanning lines). Done before key regexes so a key buried inside
# a comment cannot false-match.
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")

# Line-anchored, single-key matchers. `^\s*` requires the key to start the
# line (after optional indentation) — `someOtherKey adjustTimeStep yes;` on
# one line cannot false-match. `\s*;` allows trailing whitespace before the
# terminator. \w+ for solver / bool tokens; \S+ for deltaT to allow `1e-3`,
# `0.001`, `2.5e-05` etc. (parsing to float is gated below).
_APPLICATION_RE = re.compile(r"^\s*application\s+(\w+)\s*;", re.MULTILINE)
_ADJUST_DT_RE = re.compile(r"^\s*adjustTimeStep\s+(\w+)\s*;", re.MULTILINE)
_DELTA_T_RE = re.compile(r"^\s*deltaT\s+(\S+?)\s*;", re.MULTILINE)

# OpenFOAM bool tokens (OF accepts these case-sensitively per the dict
# grammar). Anything else (e.g. a `$macro`, a typo, a comment artifact)
# yields None — treated as "key not honestly determinable", never guessed.
_TRUE_TOKENS = frozenset({"yes", "true", "on"})
_FALSE_TOKENS = frozenset({"no", "false", "off"})


def _strip_comments(text: str) -> str:
    """Remove `/* ... */` blocks and `// ...` line tails before key matching."""
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


def _parse_bool(token: str) -> bool | None:
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return None


def _parse_float(token: str) -> float | None:
    try:
        return float(token)
    except (TypeError, ValueError):
        return None


def extract(case_dir: Path) -> SolverBlockSnapshot | None:
    """Read `<case_dir>/system/controlDict` → `SolverBlockSnapshot`.

    Returns `None` (the honest "cannot construct a valid snapshot" signal)
    when:
      - `system/controlDict` is missing,
      - the file is unreadable (OSError),
      - the `application` key is absent or unparseable — `solver` is the
        snapshot's only required field; without it the snapshot has no
        meaning to the downstream advisor.

    `adjust_time_step` and `delta_t` are populated when present and
    parseable; left at `SolverBlockSnapshot`'s defaults (None) otherwise.
    `preconditioners` is left at its default (empty dict) — this v0.1
    extractor does not parse `fvSolution.solvers` blocks (DEC-V61-211).

    Per DEC-V61-130/132, this function is **read-only** — `Path.read_text`
    is the only I/O; no writes, no route, no mutation.
    """
    control_dict_path = case_dir / "system" / "controlDict"
    if not control_dict_path.is_file():
        return None
    try:
        raw = control_dict_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    body = _strip_comments(raw)

    app_match = _APPLICATION_RE.search(body)
    if not app_match:
        return None
    solver = app_match.group(1)

    adjust_token = _ADJUST_DT_RE.search(body)
    adjust_time_step = (
        _parse_bool(adjust_token.group(1)) if adjust_token else None
    )

    delta_token = _DELTA_T_RE.search(body)
    delta_t = _parse_float(delta_token.group(1)) if delta_token else None

    return SolverBlockSnapshot(
        solver=solver,
        adjust_time_step=adjust_time_step,
        delta_t=delta_t,
        # preconditioners intentionally empty in v0.1 (DEC-V61-211).
    )
