"""PointwiseMetric · P1-T1a extractor wrapper.

Single-point scalar extracted at a specific (x, y, z) / time. Delegates
to `src.result_comparator` (same-plane Evaluation helper) via the shared
`evaluate_via_result_comparator` wrapper — IntegratedMetric uses the same
path because the extractor-level semantic is identical (scalar float +
optional profile list with axis coords).

Examples of pointwise metrics in the 10-case whitelist:
- `u_centerline_y=0.5` (LDC)
- `cp_at_x_over_c=0.3` (NACA0012)
- `T_at_wall_x=0.5` (differential_heated_cavity)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._comparator_wrap import evaluate_via_result_comparator
from .base import Metric, MetricClass, MetricReport


class PointwiseMetric(Metric):
    metric_class = MetricClass.POINTWISE
    delegate_to_module = "src.result_comparator"

    def evaluate(
        self,
        artifacts: Any,
        observable_def: Dict[str, Any],
        tolerance_policy: Optional[Dict[str, Any]] = None,
    ) -> MetricReport:
        return evaluate_via_result_comparator(
            self, artifacts, observable_def, tolerance_policy
        )
