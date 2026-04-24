"""SpectralMetric · P1-T1c · frequency-domain observable.

Semantic delegate: `src.cylinder_strouhal_fft` (which is classified
as Execution Plane in ADR-001 §2.1 because it is invoked from
`foam_agent_adapter` as part of the solver → post-process pipeline).

Implementation delegate (what this class actually calls): the shared
`_comparator_wrap.evaluate_via_result_comparator` helper — Evaluation
Plane. This preserves ADR-001 Contract 2 (Evaluation ↛ Execution):
SpectralMetric does NOT import the FFT extractor; it reads the
already-produced scalar from `ExecutionResult.key_quantities`.

WARN promotion: unlike Pointwise/Integrated which are strictly
PASS/FAIL from the comparator, SpectralMetric inspects a companion
key (default `"strouhal_low_confidence"`, overridable via the
`low_confidence_key` constructor arg). When True and the scalar
comparison would have passed, status is demoted PASS → WARN — the
value may still be within tolerance but we cannot strongly vouch
for it (<8 shedding periods resolved per DEC-V61-040 round-2).

FAIL is inherited from the comparator (quantity missing, reference
deviation exceeded). Low-confidence does NOT upgrade a FAIL to WARN
— a value outside tolerance is wrong even if confident.

Examples of spectral metrics in the 10-case whitelist:
- `cylinder_wake_strouhal_number` (circular_cylinder_wake · Re=100 → 0.164)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._comparator_wrap import evaluate_via_result_comparator
from .base import Metric, MetricClass, MetricReport, MetricStatus


class SpectralMetric(Metric):
    metric_class = MetricClass.SPECTRAL
    delegate_to_module = "src.cylinder_strouhal_fft"
    """Semantic delegate: the Execution-plane FFT extractor whose output
    this metric consumes via ExecutionResult.key_quantities. The actual
    Python call is to `src.result_comparator` via the shared wrapper."""

    def __init__(
        self,
        name: str,
        unit: str = "dimensionless",
        *,
        low_confidence_key: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, unit=unit)
        self._low_confidence_key = low_confidence_key

    def _resolve_low_confidence(
        self, artifacts: Any, quantity: Optional[str]
    ) -> bool:
        key_candidates = []
        if self._low_confidence_key:
            key_candidates.append(self._low_confidence_key)
        if quantity:
            key_candidates.append(f"{quantity}_low_confidence")
        # Default convention used by emit_strouhal for Strouhal-family.
        key_candidates.append("strouhal_low_confidence")

        if hasattr(artifacts, "key_quantities"):
            kq = artifacts.key_quantities
        elif isinstance(artifacts, dict):
            kq = artifacts.get("key_quantities", artifacts)
        else:
            return False

        for key in key_candidates:
            v = kq.get(key) if isinstance(kq, dict) else None
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
        return False

    def evaluate(
        self,
        artifacts: Any,
        observable_def: Dict[str, Any],
        tolerance_policy: Optional[Dict[str, Any]] = None,
    ) -> MetricReport:
        report = evaluate_via_result_comparator(
            self, artifacts, observable_def, tolerance_policy
        )

        low_confidence = self._resolve_low_confidence(
            artifacts, observable_def.get("quantity")
        )
        report.provenance["low_confidence"] = low_confidence

        if low_confidence and report.status is MetricStatus.PASS:
            report.status = MetricStatus.WARN
            note_suffix = (
                "extractor flagged low_confidence "
                "(<8 shedding periods resolved per DEC-V61-040)"
            )
            report.notes = (
                f"{report.notes}; {note_suffix}" if report.notes else note_suffix
            )

        return report
