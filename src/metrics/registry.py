"""MetricsRegistry · P1-T1 MVP · Evaluation Plane.

Per METRICS_AND_TRUST_GATES v0.1 Draft. Registry holds Metric instances
keyed by name; lookup by name or filter by metric_class. Used by
TrustGate + Attribution downstream (both future P1-T1b+ deliverables).
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .base import Metric, MetricClass, MetricReport


class MetricsRegistry:
    """Registry of Metric instances for a given project / case scope.

    MVP behavior:
      - `register(metric)`: add by name; raises KeyError on name collision
      - `lookup(name)`: return Metric or None
      - `filter_by_class(metric_class)`: subset by MetricClass enum
      - `evaluate_all(artifacts, observable_defs, tolerance_policy)`:
          iterate all registered metrics, each gets its matching observable
          def (by name). Returns list of MetricReport.

    MVP caveats:
      - No persistence. Future P4 KNOWLEDGE_OBJECT_MODEL Active will add
        serialization to `knowledge/metrics_registry.yaml`.
      - No version drift check on ExecutionArtifacts (VCP §3 DESIGN_ONLY
        until P1-T1 TaskRunner pre-check hook).
      - Metric.evaluate() currently raises NotImplementedError; registry
        is the contract surface, concrete metrics land via subsequent DECs.
    """

    def __init__(self) -> None:
        self._metrics: Dict[str, Metric] = {}

    def register(self, metric: Metric) -> None:
        """Add metric to registry.

        Raises:
            KeyError: if a metric with the same name is already registered.
                Callers can catch and call `unregister()` first if intentional.
        """
        if metric.name in self._metrics:
            raise KeyError(
                f"Metric {metric.name!r} already registered as "
                f"{type(self._metrics[metric.name]).__name__}. "
                f"Use unregister() first for intentional replacement."
            )
        self._metrics[metric.name] = metric

    def unregister(self, name: str) -> Optional[Metric]:
        """Remove by name. Returns the removed Metric or None if absent."""
        return self._metrics.pop(name, None)

    def lookup(self, name: str) -> Optional[Metric]:
        return self._metrics.get(name)

    def filter_by_class(self, metric_class: MetricClass) -> List[Metric]:
        return [m for m in self._metrics.values() if m.metric_class is metric_class]

    def __contains__(self, name: str) -> bool:
        return name in self._metrics

    def __len__(self) -> int:
        return len(self._metrics)

    def __iter__(self) -> Iterable[Metric]:
        return iter(self._metrics.values())

    def names(self) -> List[str]:
        return sorted(self._metrics.keys())

    def evaluate_all(
        self,
        artifacts: Dict[str, Any],
        observable_defs: Dict[str, Dict[str, Any]],
        tolerance_policy: Optional[Dict[str, Any]] = None,
    ) -> List[MetricReport]:
        """Evaluate every registered metric that has a matching observable def.

        Args:
            artifacts: ExecutionArtifacts bundle (file paths / in-memory data).
                Read-only from the Metric's perspective (Evaluation ↛ Execution
                per ADR-001).
            observable_defs: mapping from metric name → observable definition
                (per KNOWLEDGE §1 draft; typically loaded from gold YAML).
            tolerance_policy: CaseProfile.tolerance_policy per VCP §8.2 →
                METRICS §4 accepting clause. May override
                observable_def.tolerance on a per-name basis.

        Returns:
            List of MetricReport in registered-name sort order. Metrics
            lacking a matching observable_def are skipped silently (not an
            error — registry can be broader than a given case's expected
            observables).
        """
        reports: List[MetricReport] = []
        for name in self.names():
            metric = self._metrics[name]
            obs_def = observable_defs.get(name)
            if obs_def is None:
                continue
            # Per-metric dispatch: only the named entry (observable name key)
            # applies. Do NOT fall back to the whole policy dict — that would
            # leak a top-level `tolerance` override into unrelated metrics
            # (Codex DEC-V61-054 R1 finding #2). Documented semantics per
            # METRICS_AND_TRUST_GATES §4: `tolerance_policy[<observable_name>]`.
            per_metric_tol = (
                tolerance_policy.get(name) if tolerance_policy is not None else None
            )
            reports.append(metric.evaluate(artifacts, obs_def, per_metric_tol))
        return reports
