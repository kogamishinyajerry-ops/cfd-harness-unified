"""Shared wrapper: ResultComparator → MetricReport.

Pointwise and Integrated metrics both delegate to `src.result_comparator`
(only the semantic label differs — scalar-at-a-point vs volume/surface
integral). To avoid duplicating the extractor-glue in both subclasses,
this module exposes a single helper that both call.

Plane: Evaluation. Imports only from `src.models` (contracts) and
`src.result_comparator` (same-plane delegate). ADR-001 contract 2
(Evaluation↛Execution) is honored by transitive import review.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import ExecutionResult
from ..result_comparator import REF_SCALAR_KEYS, ResultComparator
from .base import Metric, MetricReport, MetricStatus


def _coerce_execution_result(artifacts: Any) -> ExecutionResult:
    if isinstance(artifacts, ExecutionResult):
        return artifacts
    if isinstance(artifacts, dict):
        kq = artifacts.get("key_quantities", artifacts)
        return ExecutionResult(
            success=bool(artifacts.get("success", True)),
            is_mock=bool(artifacts.get("is_mock", False)),
            key_quantities=dict(kq),
        )
    raise TypeError(
        f"Metric evaluate() expects ExecutionResult or dict-like artifacts; "
        f"got {type(artifacts).__name__}"
    )


def _extract_first_reference_scalar(
    reference_values: Optional[list],
) -> Optional[float]:
    """Pick the same reference scalar `ResultComparator._compare_scalar` would.

    Iterates reference_values in order; for each entry, walks REF_SCALAR_KEYS
    and returns the first non-None numeric scalar. Agrees with comparator
    for the supported `knowledge/schemas/gold_standard_schema.json` shapes
    (numeric dict entries); divergence from comparator only occurs on
    out-of-contract shapes (non-dict entries, non-numeric recognized
    values) which comparator crashes on anyway (TypeError / AttributeError).
    Wrapper returns None defensively on those edge cases rather than raising
    — see Codex DEC-V61-054 R2 APPROVE_WITH_COMMENTS note.
    """
    if not reference_values:
        return None
    for entry in reference_values:
        if isinstance(entry, (int, float)):
            return float(entry)
        if isinstance(entry, dict):
            for key in REF_SCALAR_KEYS:
                v = entry.get(key)
                if isinstance(v, (int, float)):
                    return float(v)
    return None


def evaluate_via_result_comparator(
    metric: Metric,
    artifacts: Any,
    observable_def: Dict[str, Any],
    tolerance_policy: Optional[Dict[str, Any]] = None,
) -> MetricReport:
    """Shared evaluator for Pointwise + Integrated metrics.

    Produces MetricReport whose `status` mirrors ComparisonResult.passed
    (PASS when comparator accepted, FAIL otherwise). WARN is NOT emitted
    here — the underlying comparator is binary. WARN is reserved for
    spectral low-confidence and residual HAZARD verdicts (P1-T1c / P1-T1d).
    """
    exec_result = _coerce_execution_result(artifacts)

    gold = dict(observable_def)
    tol_override = None
    if tolerance_policy is not None:
        tol_override = tolerance_policy.get("tolerance")
        if tol_override is not None:
            gold["tolerance"] = tol_override

    comparator = ResultComparator()
    cmp_result = comparator.compare(exec_result, gold)

    quantity = gold.get("quantity")
    value: Optional[float] = None
    if quantity is not None:
        raw = exec_result.key_quantities.get(quantity)
        if isinstance(raw, (int, float)):
            value = float(raw)

    reference_value = _extract_first_reference_scalar(gold.get("reference_values"))
    tolerance_applied = gold.get("tolerance")

    deviation: Optional[float] = None
    if cmp_result.deviations:
        errs = [
            d.relative_error
            for d in cmp_result.deviations
            if d.relative_error is not None
        ]
        if errs:
            deviation = max(errs)
    elif value is not None and reference_value is not None:
        abs_err = abs(value - reference_value)
        if abs(reference_value) < 1e-6:
            deviation = abs_err
        else:
            deviation = abs_err / (abs(reference_value) + 1e-12)

    # Wrapper-level gate: when we have a value + reference + tolerance but
    # the comparator accepted anyway (e.g. its ref-scalar-key list doesn't
    # include our observable's key — `{"St": ...}` for Strouhal), apply
    # our own tolerance check so downstream TrustGate doesn't get bogus PASS.
    status = MetricStatus.PASS if cmp_result.passed else MetricStatus.FAIL
    if (
        status is MetricStatus.PASS
        and deviation is not None
        and tolerance_applied is not None
        and deviation > tolerance_applied
    ):
        status = MetricStatus.FAIL

    provenance: Dict[str, Any] = {
        "delegate_module": metric.delegate_to_module,
        "comparator_summary": cmp_result.summary,
    }
    if cmp_result.gold_standard_id:
        provenance["gold_standard_id"] = cmp_result.gold_standard_id
    if tol_override is not None:
        provenance["tolerance_source"] = "tolerance_policy"
    elif "tolerance" in observable_def:
        provenance["tolerance_source"] = "observable_def"
    else:
        provenance["tolerance_source"] = "comparator_default"

    if status is MetricStatus.FAIL:
        if not cmp_result.passed:
            notes = cmp_result.summary
        else:
            # Wrapper-level override: comparator said PASS but our deviation
            # gate disagreed (usually ref-dict key not in comparator's list).
            notes = (
                f"deviation {deviation:.4f} exceeds tolerance "
                f"{tolerance_applied:.4f} (wrapper-level gate)"
            )
    else:
        notes = None

    return MetricReport(
        name=metric.name,
        metric_class=metric.metric_class,
        value=value,
        unit=metric.unit,
        reference_value=reference_value,
        deviation=deviation,
        tolerance_applied=tolerance_applied,
        status=status,
        provenance=provenance,
        notes=notes,
    )
