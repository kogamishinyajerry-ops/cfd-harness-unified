"""MetricsRegistry · P1-T1 deliverable for METRICS_AND_TRUST_GATES v0.1 Draft.

Evaluation Plane per ADR-001 §2.1. Consumes CaseProfile.tolerance_policy
(delegated via VERSION_COMPATIBILITY_POLICY v1.0 §8.2 → this module per
METRICS_AND_TRUST_GATES §4 accepting clause).

Public API:
    MetricsRegistry  — global registry of Metric instances
    Metric           — ABC for all metrics
    MetricReport     — dataclass returned by Metric.evaluate()
    MetricClass      — enum (pointwise / integrated / spectral / residual)
    PointwiseMetric, IntegratedMetric, SpectralMetric, ResidualMetric
                     — 4 subclass skeletons; each has a delegate_to_module
                       pointer for the existing extractor it will wrap when
                       filled in by per-metric-class DECs.

Import direction (Evaluation Plane):
    metrics CAN import  : src.models (shared)
    metrics CANNOT import: src.foam_agent_adapter / src.cylinder_* / other
                          Execution modules (forbidden by .importlinter
                          evaluation-never-imports-execution contract)
"""

from __future__ import annotations

from .base import (
    Metric,
    MetricClass,
    MetricReport,
    MetricStatus,
)
from .registry import MetricsRegistry
from .pointwise import PointwiseMetric
from .integrated import IntegratedMetric
from .spectral import SpectralMetric
from .residual import ResidualMetric
from .trust_gate import TrustGateReport, reduce_reports
from .case_profile_loader import (
    CaseProfileError,
    load_case_profile,
    load_tolerance_policy,
)

__all__ = [
    "Metric",
    "MetricClass",
    "MetricReport",
    "MetricStatus",
    "MetricsRegistry",
    "PointwiseMetric",
    "IntegratedMetric",
    "SpectralMetric",
    "ResidualMetric",
    "TrustGateReport",
    "reduce_reports",
    "CaseProfileError",
    "load_case_profile",
    "load_tolerance_policy",
]
