"""Metric ABC + MetricReport dataclass.

Per METRICS_AND_TRUST_GATES v0.1 Draft (Notion) + accepting clause
for VERSION_COMPATIBILITY_POLICY v1.0 §8.2.

MVP scope (P1-T1): ABC + dataclass + enum. Individual metric classes
ship with NotImplementedError placeholders; per-metric DECs (P1-T1a,
P1-T1b, ...) will fill in concrete evaluation logic by wrapping
existing extractors (result_comparator / cylinder_strouhal_fft /
convergence_attestor / wall_gradient).
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class MetricClass(str, Enum):
    """4 categories per METRICS_AND_TRUST_GATES §1 (Notion Draft v0.1)."""

    POINTWISE = "pointwise"
    """Single-point scalar extracted at a specific location / time."""

    INTEGRATED = "integrated"
    """Domain / boundary integral quantity (CL, CD, Nu, bulk temperature)."""

    SPECTRAL = "spectral"
    """Frequency-domain quantity derived via FFT (Strouhal, dominant modes)."""

    RESIDUAL = "residual"
    """Solver convergence residual or attestor-derived quality indicator."""


class MetricStatus(str, Enum):
    """Three-state TrustGate verdict per METRICS_AND_TRUST_GATES §2."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class MetricReport:
    """Result of a single Metric.evaluate() call.

    Per METRICS_AND_TRUST_GATES §3 output schema. TrustGate consumes
    `status` (three-state) + `deviation` to produce overall verdict;
    version_metadata per VERSION_COMPATIBILITY_POLICY §2 provides the
    four-tuple for drift check (aspirational until P1-T1 TaskRunner
    pre-check hook lands, see VCP §3 DESIGN_ONLY note).
    """

    name: str
    """Metric identifier, unique within MetricsRegistry."""

    metric_class: MetricClass
    """Category for dispatch + tolerance-policy lookup."""

    value: Optional[float] = None
    """Measured scalar (None when extraction failed; see `status`)."""

    unit: str = "dimensionless"

    reference_value: Optional[float] = None
    """Gold standard reference (when applicable; None for residual metrics)."""

    deviation: Optional[float] = None
    """Relative deviation |value - reference| / |reference| (fraction, not %).
    None when reference unavailable."""

    tolerance_applied: Optional[float] = None
    """The tolerance the Trust-Gate compared against (from CaseProfile
    .tolerance_policy per VCP §8.2 → METRICS §4 delegation)."""

    status: MetricStatus = MetricStatus.PASS
    """PASS / WARN / FAIL per METRICS §2 three-state decision."""

    provenance: Dict[str, Any] = field(default_factory=dict)
    """Extraction provenance: source artifact paths, extractor version,
    resampling grid, etc. Per KNOWLEDGE_OBJECT_MODEL §1 Provenance object
    (when KNOWLEDGE v1.0 Active, will align with canonical schema)."""

    version_metadata: Dict[str, str] = field(default_factory=dict)
    """VCP v1.0 §2.1 four-tuple: solver_version / case_compatibility /
    extractor_compatibility / schema_version. Populated by P2 executor when
    ExecutionArtifacts carry it; placeholder empty-dict on today's MVP."""

    notes: Optional[str] = None
    """Free-form. Used by WARN / FAIL to surface the root cause to the UI."""


class Metric(ABC):
    """Base class for all metrics.

    Subclasses (PointwiseMetric / IntegratedMetric / SpectralMetric /
    ResidualMetric) declare `metric_class` + `delegate_to_module` and
    implement `evaluate()`. MVP skeletons raise NotImplementedError until
    per-metric DECs fill in the extractor wrappers.
    """

    metric_class: MetricClass
    """Subclass-level attribute — set in each concrete subclass."""

    delegate_to_module: Optional[str] = None
    """Dot-path of the existing extractor this metric will wrap (for
    traceability during the P1-T1 → per-metric DEC transition).
    e.g. 'src.result_comparator' for point/integrated, 'src.cylinder_strouhal_fft'
    for SpectralMetric, 'src.convergence_attestor' for ResidualMetric."""

    def __init__(self, name: str, unit: str = "dimensionless") -> None:
        self.name = name
        self.unit = unit

    def evaluate(
        self,
        artifacts: Dict[str, Any],
        observable_def: Dict[str, Any],
        tolerance_policy: Optional[Dict[str, Any]] = None,
    ) -> MetricReport:
        """Compute the metric value from artifacts + observable definition.

        Args:
            artifacts: ExecutionArtifacts (paths / in-memory handles) from
                Execution Plane. The MVP does NOT import execution modules;
                it only reads file-system artifacts per the plane contract.
            observable_def: GoldStandard observable entry (per KNOWLEDGE
                §1 draft): `{quantity, reference_values, tolerance, source, ...}`.
            tolerance_policy: CaseProfile.tolerance_policy per VCP §8.2 →
                METRICS §4 accepting clause. Overrides observable_def.tolerance
                when present.

        Returns:
            MetricReport with status / deviation / provenance populated.

        Raises:
            NotImplementedError: Placeholder in P1-T1 MVP. Concrete
                implementations land via per-metric-class DECs.
        """
        raise NotImplementedError(
            f"Metric subclass {type(self).__name__} has no evaluate() "
            f"implementation yet. Per-metric DECs (P1-T1a/b/c/d) will "
            f"land the extractor wrappers."
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"class={self.metric_class.value}, "
            f"delegates={self.delegate_to_module})"
        )
