"""TrustGate overall-verdict reducer · P1-T2.

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

Plane: Evaluation. Pure function over MetricReport values; no I/O,
no plane boundary crossing, no extractor delegate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .base import MetricReport, MetricStatus


@dataclass(frozen=True)
class TrustGateReport:
    """Aggregated trust-gate output for a set of metric evaluations.

    Attributes
    ----------
    overall
        Worst-wins verdict across all input reports. Empty input → PASS.
    reports
        Per-metric MetricReport list in the order provided to the reducer
        (defensive copy — consumers may mutate their original list safely).
    count_by_status
        Histogram keyed by MetricStatus. All three keys always present
        (zero-filled when absent) so consumers can index without KeyError.
    notes
        Aggregated non-PASS notes in report order, formatted
        `"{metric_name} [{status}]: {notes}"` for UI display. Reports
        with status=PASS or notes=None are skipped.
    """

    overall: MetricStatus
    reports: List[MetricReport]
    count_by_status: Dict[MetricStatus, int]
    notes: List[str] = field(default_factory=list)

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
    reports_list = list(reports)

    counts: Dict[MetricStatus, int] = {
        MetricStatus.PASS: 0,
        MetricStatus.WARN: 0,
        MetricStatus.FAIL: 0,
    }
    for rep in reports_list:
        counts[rep.status] = counts.get(rep.status, 0) + 1

    if counts[MetricStatus.FAIL] > 0:
        overall = MetricStatus.FAIL
    elif counts[MetricStatus.WARN] > 0:
        overall = MetricStatus.WARN
    else:
        overall = MetricStatus.PASS

    notes = [
        f"{rep.name} [{rep.status.value}]: {rep.notes}"
        for rep in reports_list
        if rep.status is not MetricStatus.PASS and rep.notes
    ]

    return TrustGateReport(
        overall=overall,
        reports=reports_list,
        count_by_status=counts,
        notes=notes,
    )
