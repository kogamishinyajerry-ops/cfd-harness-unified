"""DEC-V62-A-sub-M-DRIFT-V2 · Runtime V-series corpus drift guard.

Stack-level companion to **V61-198 M-DRIFT v1** (`scripts/governance/
check_corpus_sync.py` + pre-commit hook). v1 fails commits that stage the
methodology master copy without staging the runtime advisor copy in the
same commit — a *commit-time, static* invariant. v2 enforces the same
corpus-truth invariant **at the /api/ai-review route boundary**: every
``Finding`` returned by ``assemble_stack`` must cite ``evidence_v_rows``
that actually exist in the runtime corpus
(``docs/openfoam_corpus/industrial_solver_findings_v_series.md``). If a
Finding cites a V-row that has been deleted, renamed, or never existed
(stale advisor literal), the route either:

* **audit mode** (default · backward compatible): keeps the Finding and
  appends a ``v_series_drift_guard`` entry to ``advisor_calls`` flagging
  the missing V-rows. Existing callers see the same wire contract; a new
  ``advisor_calls`` entry is the only delta. This honors V133 "DEC scope-
  driven · don't break contracts to enforce a new invariant" discipline.
* **strict mode** (opt-in · ``?drift_mode=strict`` query param): drops
  every Finding whose ``evidence_v_rows`` contains at least one missing
  ID, *and* appends the same audit entry. ``advisor_count`` / ``advisor_
  calls`` are preserved (the drop is at the Finding tuple level).

Why a route-time check on top of v1's commit-time check? v1 only catches
the methodology + runtime delta within a *single commit*. If
``advisor_stack._V_ROWS_PER_ADVISOR`` is edited in a commit that doesn't
touch the methodology file, v1 passes — but the advisor will still
attach a V-row literal that may not exist in the runtime corpus
(post-renumber, post-deletion, typo). The /api/ai-review boundary is the
last enforceable hop before findings reach an external auditor / UI /
DEC trail; enforcing here closes the residual drift channel.

Four-question gate (V130 advisory-not-driver):

  1. **LLM offline OK?** Yes — module imports zero LLM providers.
  2. **Artifacts output?** Inherits from the route's audit JSON; this
     module only adds a structured ``AdvisorCall`` entry that the route
     serializes alongside everything else.
  3. **TrustGate?** Yes — every dropped (strict) or flagged (audit)
     Finding still carries ``source_advisor`` + the original
     ``evidence_v_rows``. The drift guard never re-authors evidence; it
     only attests to its existence (or absence) in the live corpus.
  4. **AI advisory only?** Yes — no writes to ``case_dir`` or anywhere
     else. The audit-trail entry is in-memory; only the route's existing
     ``_persist_audit`` writes to ``.planning/audits/``.

Inheritance / boundary with v1:

  * v1 (commit-time): methodology vs runtime *file-level* sync
  * v2 (route-time): runtime corpus vs *Finding-level* V-row claims
  * They are **complementary**, not overlapping. v1 catches the
    "engineer forgot to copy the master into the runtime file"
    failure; v2 catches the "advisor literal cites a V-row that the
    runtime file does not contain" failure.

Confidence: **med** (Opus self-graded). Net-new module, three pure
functions, no LLM deps, no security boundary — does not trip v2.3
1-sync-trigger.
"""
from __future__ import annotations

import dataclasses
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Literal

from ui.backend.services.advisor_stack import (
    AdvisorCall,
    AdvisorStackReport,
    Finding,
)


logger = logging.getLogger(__name__)


# Repo root: this file lives at .../ui/backend/services/v_series_drift_guard.py
# → three parents reach ``.../<repo>``.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CORPUS_PATH = (
    _REPO_ROOT / "docs" / "openfoam_corpus" / "industrial_solver_findings_v_series.md"
)

# V-row headings in the runtime corpus are ``### V<n>`` (e.g. ``### V42``).
# Anchored to start-of-line to avoid catching prose mentions like
# "see V42 above" inside body text.
_V_ROW_HEADING_RE = re.compile(r"^###\s+(V\d+)\b", re.MULTILINE)


_DriftMode = Literal["audit", "strict"]


@lru_cache(maxsize=4)
def _load_corpus_cached(corpus_path_str: str) -> frozenset[str]:
    """Parse the runtime corpus and return canonical V-row IDs.

    Cached by absolute path string so production calls (single canonical
    path) hit the cache while test fixtures (per-test tmp_path) get fresh
    parses. Bounded at 4 entries — far above the realistic working set.

    Returns ``frozenset[str]`` so callers can safely intersect / diff
    without aliasing concerns. An empty frozenset is returned on any
    load failure (missing file / unreadable bytes); a WARNING is logged
    so operators see the degradation even though the route stays up.
    """
    path = Path(corpus_path_str)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "v_series_drift_guard: corpus unreadable at %s (%s); "
            "drift checks will fail-open this request.",
            path,
            exc,
        )
        return frozenset()
    matches = _V_ROW_HEADING_RE.findall(text)
    return frozenset(matches)


def load_v_series_index(corpus_path: Path | None = None) -> set[str]:
    """Return canonical V-row IDs present in the runtime corpus.

    ``corpus_path`` defaults to ``docs/openfoam_corpus/industrial_solver_
    findings_v_series.md`` resolved from the repo root. Test callers may
    pass a tmp_path-rooted alternative.

    Public surface returns ``set[str]`` for ergonomic difference ops on
    the caller side; internally we cache a ``frozenset`` and copy out on
    each call so mutation by callers cannot poison the cache.
    """
    p = (corpus_path or _DEFAULT_CORPUS_PATH).resolve()
    return set(_load_corpus_cached(str(p)))


def check_finding_drift(
    finding: Finding,
    index: Iterable[str] | None = None,
    *,
    corpus_path: Path | None = None,
) -> tuple[bool, list[str]]:
    """Cross-check a single Finding's ``evidence_v_rows`` against the index.

    Args:
        finding: A normalized ``Finding`` from ``assemble_stack``.
        index: Optional pre-loaded V-row ID set. Skipping repeated index
            loads is the common case (route loads once per request, then
            iterates findings). When ``None``, the corpus is (re)loaded.
        corpus_path: Forwarded to ``load_v_series_index`` when ``index``
            is omitted. Test-only knob.

    Returns:
        ``(ok, missing)`` where ``ok`` is True iff every cited V-row is
        present in the index, and ``missing`` is the sorted list of IDs
        absent from the index. A Finding citing zero V-rows is treated
        as ``ok=True`` (the advisor explicitly waived TrustGate; the
        drift guard cannot opine on what isn't claimed).
    """
    if index is None:
        index = load_v_series_index(corpus_path=corpus_path)
    index_set = index if isinstance(index, (set, frozenset)) else set(index)
    cited = set(finding.evidence_v_rows)
    if not cited:
        return True, []
    missing = sorted(cited - index_set, key=_v_row_sort_key)
    return (not missing), missing


def _v_row_sort_key(v_row: str) -> tuple[int, str]:
    """Sort key for V-row IDs: numeric order, falling back to lexical."""
    m = re.fullmatch(r"V(\d+)", v_row)
    if m:
        return (int(m.group(1)), v_row)
    return (10**9, v_row)


def enforce_at_route_boundary(
    report: AdvisorStackReport,
    mode: _DriftMode = "audit",
    *,
    corpus_path: Path | None = None,
) -> AdvisorStackReport:
    """Apply v_series drift enforcement to ``report`` and return a new one.

    Behavior matrix:

    +---------+-------------------------------+--------------------------------+
    | mode    | findings tuple                | advisor_calls tuple            |
    +---------+-------------------------------+--------------------------------+
    | audit   | unchanged                     | +1 ``v_series_drift_guard``    |
    | strict  | drift findings removed        | +1 ``v_series_drift_guard``    |
    +---------+-------------------------------+--------------------------------+

    The appended ``AdvisorCall`` carries ``status="ok"`` (the check
    itself succeeded) and an ``output`` dict that the route serializes
    verbatim:

    .. code-block:: python

        {
            "check_status":      "clean" | "drift_detected",
            "mode":              "audit" | "strict",
            "missing_v_rows":    ["V101", ...],
            "findings_flagged":  int,   # how many Findings cited ≥1 missing row
            "findings_dropped":  int,   # strict mode only; 0 in audit mode
            "corpus_size":       int,   # V-row count in the loaded index
        }

    Calling with ``mode`` outside ``{"audit","strict"}`` raises
    ``ValueError`` — the caller is expected to validate the query param
    before reaching this function.
    """
    if mode not in ("audit", "strict"):
        raise ValueError(
            f"v_series_drift_guard: unsupported mode {mode!r}; expected 'audit'|'strict'"
        )

    index = load_v_series_index(corpus_path=corpus_path)
    findings_flagged = 0
    findings_kept: list[Finding] = []
    missing_union: set[str] = set()

    for f in report.findings:
        ok, missing = check_finding_drift(f, index=index)
        if ok:
            findings_kept.append(f)
            continue
        findings_flagged += 1
        missing_union.update(missing)
        if mode == "audit":
            findings_kept.append(f)  # audit mode never drops
        # strict mode: do not append → finding is dropped

    findings_dropped = findings_flagged if mode == "strict" else 0
    check_status = "drift_detected" if findings_flagged else "clean"

    guard_call = AdvisorCall(
        advisor_name="v_series_drift_guard",
        status="ok",
        input_summary=(
            f"findings={len(report.findings)} mode={mode} "
            f"corpus={len(index)}"
        )[:200],
        output={
            "check_status": check_status,
            "mode": mode,
            "missing_v_rows": sorted(missing_union, key=_v_row_sort_key),
            "findings_flagged": findings_flagged,
            "findings_dropped": findings_dropped,
            "corpus_size": len(index),
        },
        duration_ms=0.0,
        version="ui.backend.services.v_series_drift_guard",
    )

    return dataclasses.replace(
        report,
        findings=tuple(findings_kept),
        advisor_calls=report.advisor_calls + (guard_call,),
    )


__all__ = [
    "load_v_series_index",
    "check_finding_drift",
    "enforce_at_route_boundary",
]
