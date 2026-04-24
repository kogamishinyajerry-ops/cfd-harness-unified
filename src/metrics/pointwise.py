"""PointwiseMetric · P1-T1 MVP skeleton.

Single-point scalar extracted at a specific (x, y, z) / time. Delegates to
`src.result_comparator` for the actual comparator logic when P1-T1a DEC
lands the extractor wrapper.

Examples of pointwise metrics in the 10-case whitelist:
- `u_centerline_y=0.5` (LDC)
- `cp_at_x_over_c=0.3` (NACA0012)
- `T_at_wall_x=0.5` (differential_heated_cavity)
"""

from __future__ import annotations

from .base import Metric, MetricClass


class PointwiseMetric(Metric):
    metric_class = MetricClass.POINTWISE
    delegate_to_module = "src.result_comparator"

    # evaluate() inherits NotImplementedError from Metric.evaluate until
    # P1-T1a DEC lands the concrete wrapper around result_comparator.
