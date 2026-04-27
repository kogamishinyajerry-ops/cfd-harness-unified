"""TrustGate overall-verdict reducer · P1-T2 + P2-T1.b ExecutorMode routing.

Consumes `MetricsRegistry.evaluate_all()` output (List[MetricReport])
and produces a single `TrustGateReport` carrying the worst-wins
aggregated status plus per-metric breakdown and non-PASS notes.

Aggregation rule (three-state worst-wins per
METRICS_AND_TRUST_GATES §2 → TrustGate §5 accepting clause):
  - any FAIL   → FAIL
  - else any WARN → WARN
  - else       → PASS  (includes empty input = vacuously PASS)

MVP scope: no policy-driven escalation (e.g. "≥N WARNs = FAIL") —
that ships in a later DEC if case-profile data warrants it. The
reducer is policy-free; consumers can wrap additional logic around it.

DEC-V61-074 P2-T1.b adds :func:`apply_executor_mode_routing` that
applies EXECUTOR_ABSTRACTION.md §6.1 per-mode verdict ceilings on top
of the worst-wins reduction. Modes are compared as **strings** against
the manifest's ``executor.mode`` field — this module is in
``Plane.EVALUATION`` and may NOT import ``src.executor``
(``Plane.EXECUTION``) per ``.importlinter`` Contract 2. The string
values mirror ``src.executor.ExecutorMode`` StrEnum and are pinned in
lockstep when the spec adds a new mode.

Plane: Evaluation. Pure functions over MetricReport / dict values; no
I/O, no plane-boundary crossing, no extractor delegate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, List, Mapping, Optional, Tuple

from .base import MetricReport, MetricStatus

# ---------------------------------------------------------------------------
# DEC-V61-074 P2-T1.b · ExecutorMode string constants
#
# Mirror of src.executor.ExecutorMode StrEnum values. Re-defined here as
# bare strings because src.metrics (Plane.EVALUATION) MUST NOT import
# from src.executor (Plane.EXECUTION) per .importlinter Contract 2.
# Adding a new ExecutorMode requires: (a) row in EXECUTOR_ABSTRACTION.md
# §4 + §6.1, (b) StrEnum value in src.executor.base, (c) constant +
# routing branch here, all in the same DEC.
# ---------------------------------------------------------------------------
_EXECUTOR_MODE_DOCKER_OPENFOAM = "docker_openfoam"
_EXECUTOR_MODE_MOCK = "mock"
_EXECUTOR_MODE_HYBRID_INIT = "hybrid_init"
_EXECUTOR_MODE_FUTURE_REMOTE = "future_remote"

# Per-§6.1 routing notes (string literals — also mirror values used by
# src.executor.{mock,hybrid_init,future_remote} executors).
_NOTE_MOCK_NO_TRUTH_SOURCE = "mock_executor_no_truth_source"
_NOTE_HYBRID_INIT_INVARIANT_UNVERIFIED = "hybrid_init_invariant_unverified"
_NOTE_FUTURE_REMOTE_REFUSED = "future_remote_mode_not_yet_implemented"

# DEC-V61-091 M5.1 · source-origin routing constants.
#
# Workbench imported user cases have no literature ground truth, so the
# trust-gate verdict must be capped at WARN with a disclaimer note (the
# UI / audit-package layer renders WARN+this note as
# "PASS_WITH_DISCLAIMER" copy without requiring a new MetricStatus
# enum value). The string is duplicated from
# `ui.backend.services.case_scaffold.SOURCE_ORIGIN_IMPORTED_USER` rather
# than imported because src.metrics is in Plane.EVALUATION and may NOT
# import from ui.backend (Plane.UI) per .importlinter Contract 2 — the
# trust-core line-A boundary stays clean.
SOURCE_ORIGIN_IMPORTED_USER = "imported_user"
_NOTE_IMPORTED_USER_NO_LITERATURE_GROUND_TRUTH = (
    "imported_user_no_literature_ground_truth_pass_with_disclaimer"
)


@dataclass(frozen=True)
class TrustGateReport:
    """Aggregated trust-gate output for a set of metric evaluations.

    Fully immutable: the dataclass is frozen AND the container fields are
    wrapped so callers cannot mutate them post-reduction (Codex DEC-V61-055
    R1 APPROVE_WITH_COMMENTS — prior impl had mutable list/dict fields
    which meant `report.count_by_status[FAIL] = 999` silently invalidated
    `summary()` / `has_failures` / `has_warnings`).

    Attributes
    ----------
    overall
        Worst-wins verdict across all input reports. Empty input → PASS.
    reports
        Per-metric MetricReport tuple in the order provided to the
        reducer (input list defensively snapshotted as a tuple).
    count_by_status
        Histogram keyed by MetricStatus wrapped in MappingProxyType.
        All three keys always present (zero-filled when absent) so
        consumers can index without KeyError.
    notes
        Aggregated non-PASS notes in report order, formatted
        `"{metric_name} [{status}]: {notes}"` for UI display. Reports
        with status=PASS or notes=None are skipped. Wrapped as a tuple.
    """

    overall: MetricStatus
    reports: Tuple[MetricReport, ...]
    count_by_status: Mapping[MetricStatus, int]
    notes: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.overall is MetricStatus.PASS

    @property
    def has_failures(self) -> bool:
        return self.count_by_status.get(MetricStatus.FAIL, 0) > 0

    @property
    def has_warnings(self) -> bool:
        return self.count_by_status.get(MetricStatus.WARN, 0) > 0

    def summary(self) -> str:
        """Human-readable one-liner for logs / dashboards."""
        parts = [f"TrustGate: {self.overall.value.upper()}"]
        counts = [
            f"PASS={self.count_by_status.get(MetricStatus.PASS, 0)}",
            f"WARN={self.count_by_status.get(MetricStatus.WARN, 0)}",
            f"FAIL={self.count_by_status.get(MetricStatus.FAIL, 0)}",
        ]
        parts.append(" ".join(counts))
        parts.append(f"n={len(self.reports)}")
        return " | ".join(parts)


class ModeNotYetImplementedError(RuntimeError):
    """Raised by :func:`apply_executor_mode_routing` when the manifest's
    ``executor.mode`` is ``future_remote`` (per EXECUTOR_ABSTRACTION.md
    §6.1: "TrustGate refuses to score a future_remote manifest").

    Carries the offending mode string so the CLI / UI can surface
    ``mode_not_yet_implemented`` to the operator without parsing the
    message body. DEC-V61-078 will replace this refusal with a real
    HPC-mode contract.
    """

    def __init__(self, mode: str) -> None:
        super().__init__(
            f"TrustGate refuses to score executor mode {mode!r}: "
            "stub-only this milestone (EXECUTOR_ABSTRACTION.md §6.1)"
        )
        self.mode = mode


def _extract_mode(executor_section: Optional[Mapping[str, Any]]) -> str:
    """Pull the ``mode`` string from a manifest's ``executor`` section.

    Absent section / missing ``mode`` → ``docker_openfoam`` (legacy
    forward-compat per EXECUTOR_ABSTRACTION §3 + spike F-3 — pre-P2
    zips have no ``executor`` field and must be treated as the truth-
    source mode). Non-string mode values, non-mapping payloads (str /
    list / int — i.e. a malformed manifest where ``executor`` is not
    a dict at all), and ``None`` are all coerced to the legacy fallback
    so routing never raises ``AttributeError`` on a malformed input.
    Codex T1.b.3 post-commit LOW fix.
    """
    if not executor_section:
        return _EXECUTOR_MODE_DOCKER_OPENFOAM
    if not isinstance(executor_section, Mapping):
        return _EXECUTOR_MODE_DOCKER_OPENFOAM
    mode = executor_section.get("mode")
    if not isinstance(mode, str):
        return _EXECUTOR_MODE_DOCKER_OPENFOAM
    return mode


def _ceiling_to_warn(
    base: TrustGateReport, ceiling_note: str
) -> TrustGateReport:
    """Cap ``base.overall`` at ``WARN`` and append a synthetic note.

    A FAIL stays FAIL (worst-wins is monotone — capping never *raises*
    severity); PASS / WARN both become WARN. The original per-metric
    ``reports`` tuple is preserved so the audit trail still shows the
    underlying gold-comparison verdict.

    Codex T1.b.3 post-commit MED fix: when the ceiling promotes
    ``overall`` from PASS to WARN, ``count_by_status`` MUST also reflect
    the routing-imposed WARN — otherwise ``has_warnings`` /
    ``summary()`` would derive ``WARN=0`` from the unchanged histogram
    while ``overall=WARN``, which is a public-API correctness bug
    (consumers see "WARN with no warnings"). The fix bumps
    ``count_by_status[WARN]`` by 1 to represent the ceiling itself
    when the underlying histogram had no WARN entry, leaving
    ``count_by_status[PASS]`` and the ``reports`` tuple intact —
    the ceiling is a synthetic source of warning information separate
    from per-metric reports, and consumers querying the histogram now
    see ``PASS=N WARN=1 FAIL=0`` truthfully.
    """
    if base.overall is MetricStatus.FAIL:
        new_overall = MetricStatus.FAIL
    else:
        new_overall = MetricStatus.WARN

    new_counts = dict(base.count_by_status)
    if (
        new_overall is MetricStatus.WARN
        and new_counts.get(MetricStatus.WARN, 0) == 0
    ):
        new_counts[MetricStatus.WARN] = 1

    return TrustGateReport(
        overall=new_overall,
        reports=base.reports,
        count_by_status=MappingProxyType(new_counts),
        notes=base.notes + (ceiling_note,),
    )


def apply_executor_mode_routing(
    base_report: TrustGateReport,
    executor_section: Optional[Mapping[str, Any]],
    *,
    hybrid_init_reference_run_present: bool = False,
) -> TrustGateReport:
    """Apply EXECUTOR_ABSTRACTION.md §6.1 per-mode verdict ceilings.

    Parameters
    ----------
    base_report
        Output of :func:`reduce_reports` — the policy-free worst-wins
        aggregation across per-metric reports.
    executor_section
        The manifest's ``executor`` top-level section (a 3-key dict
        per §3: ``mode`` / ``version`` / ``contract_hash``). ``None``
        or a section missing the ``mode`` key falls back to
        ``docker_openfoam`` (legacy compat — pre-P2 zips never carried
        the field).
    hybrid_init_reference_run_present
        Per §6.3, when the manifest's mode is ``hybrid_init`` the gate
        verifies the §5.1 byte-equality invariant against a reference
        ``docker_openfoam`` run. The skeleton has no auditor wired in
        yet; callers (P2-T4 onward) inject this flag from the audit-
        package decision-trail. Default False so the skeleton falls
        through to the §6.3 first-ever-run WARN branch — which is the
        canonical refusal for the milestone.

    Returns
    -------
    TrustGateReport
        - ``docker_openfoam`` (or absent / unknown mode): ``base_report`` unchanged.
        - ``mock``: ceiling = ``WARN`` with note ``mock_executor_no_truth_source``.
        - ``hybrid_init`` + reference run present: ``base_report`` unchanged
          (full triad allowed on the OpenFOAM artifacts).
        - ``hybrid_init`` + no reference run: ceiling = ``WARN`` with note
          ``hybrid_init_invariant_unverified`` per §6.3.
        - ``future_remote``: raises :class:`ModeNotYetImplementedError`.

    Raises
    ------
    ModeNotYetImplementedError
        When the manifest's mode is ``future_remote`` — TrustGate
        refuses to score per §6.1 stub-only clause.
    """
    mode = _extract_mode(executor_section)

    if mode == _EXECUTOR_MODE_FUTURE_REMOTE:
        raise ModeNotYetImplementedError(mode)

    if mode == _EXECUTOR_MODE_MOCK:
        return _ceiling_to_warn(base_report, _NOTE_MOCK_NO_TRUTH_SOURCE)

    if mode == _EXECUTOR_MODE_HYBRID_INIT:
        if hybrid_init_reference_run_present:
            return base_report
        return _ceiling_to_warn(base_report, _NOTE_HYBRID_INIT_INVARIANT_UNVERIFIED)

    # `docker_openfoam` (canonical truth source) and any mode string
    # this module hasn't been taught about yet (forward-compat: an
    # older deployment reading a manifest from a newer producer)
    # both fall through to "no ceiling" — the worst-wins verdict from
    # the per-metric reports stands.
    return base_report


def apply_source_origin_routing(
    base_report: TrustGateReport,
    source_origin: Optional[str],
) -> TrustGateReport:
    """Apply DEC-V61-091 M5.1 source-origin verdict ceiling.

    Workbench imported user cases (per DEC-V61-089 two-track invariant)
    have no literature ground truth to validate against, so any
    underlying PASS verdict must be capped at WARN with the
    ``imported_user_no_literature_ground_truth_pass_with_disclaimer``
    note. WARN and FAIL stay where they are (worst-wins monotone — the
    cap can only lower severity, never raise it). The note still
    accumulates so the audit trail records why the cap fired.

    Parameters
    ----------
    base_report
        Output of :func:`reduce_reports`, optionally already routed
        through :func:`apply_executor_mode_routing`. Composition is
        worst-wins-preserving: both ceilings funnel through
        ``_ceiling_to_warn`` which is severity-idempotent and
        count-stable (PASS→WARN, WARN→WARN, FAIL→FAIL with the same
        ``count_by_status`` after the first application). The
        ``notes`` tuple still accumulates the ceiling note on every
        reapplication — that is by design so the audit trail records
        each cap event.
    source_origin
        Caller-supplied opaque tag identifying the case origin. The
        constant ``SOURCE_ORIGIN_IMPORTED_USER`` triggers the cap; any
        other string (including ``None``, ``"whitelist"``, ``"draft"``,
        or future origin tags this module hasn't been taught about
        yet) falls through unchanged so the worst-wins verdict stands.

    Returns
    -------
    TrustGateReport
        - ``imported_user``: ceiling = ``WARN`` with note appended.
        - any other origin (or ``None``): ``base_report`` unchanged.

    Notes
    -----
    The signal is opaque on purpose: the caller (typically
    ``task_runner``) derives the tag from upstream state (e.g.
    ``task_spec.mesh_already_provided`` per DEC-V61-090, which is
    exclusively set on imported user cases) and passes it as a string.
    This keeps the trust-core (Plane.EVALUATION) boundary clean — no
    direct read of ``case_manifest.yaml`` from inside the metrics
    module, no import from ``ui.backend`` (Plane.UI).
    """
    if source_origin == SOURCE_ORIGIN_IMPORTED_USER:
        return _ceiling_to_warn(
            base_report, _NOTE_IMPORTED_USER_NO_LITERATURE_GROUND_TRUTH
        )
    return base_report


def reduce_reports(reports: List[MetricReport]) -> TrustGateReport:
    """Worst-wins reduction of per-metric reports.

    Parameters
    ----------
    reports
        Iterable of MetricReport (typically from MetricsRegistry.evaluate_all).
        Empty list is valid → PASS (vacuously true, no metrics registered
        or no observable defs matched).

    Returns
    -------
    TrustGateReport
        Aggregated verdict + histogram + formatted notes.
    """
    reports_tuple: Tuple[MetricReport, ...] = tuple(reports)

    counts: dict = {
        MetricStatus.PASS: 0,
        MetricStatus.WARN: 0,
        MetricStatus.FAIL: 0,
    }
    for rep in reports_tuple:
        counts[rep.status] = counts.get(rep.status, 0) + 1

    if counts[MetricStatus.FAIL] > 0:
        overall = MetricStatus.FAIL
    elif counts[MetricStatus.WARN] > 0:
        overall = MetricStatus.WARN
    else:
        overall = MetricStatus.PASS

    notes_tuple: Tuple[str, ...] = tuple(
        f"{rep.name} [{rep.status.value}]: {rep.notes}"
        for rep in reports_tuple
        if rep.status is not MetricStatus.PASS and rep.notes
    )

    return TrustGateReport(
        overall=overall,
        reports=reports_tuple,
        count_by_status=MappingProxyType(counts),
        notes=notes_tuple,
    )
