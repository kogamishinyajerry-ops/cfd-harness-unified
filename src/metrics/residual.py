"""ResidualMetric · P1-T1 MVP skeleton.

Solver convergence residual or attestor-derived quality indicator.
Delegates to `src.convergence_attestor` when P1-T1d DEC lands the
extractor wrapper. Unlike the other 3 classes, residual metrics do NOT
have a gold-standard reference_value — they assert absolute thresholds
from attestor_thresholds.yaml + fail on divergence signs.

Examples of residual metrics in the 10-case whitelist:
- `final_p_residual` (all cases · sum_local from pimpleFoam/simpleFoam log)
- `final_U_residual` (same)
- `a1_continuity_attestation` through `a6_physical_sanity_attestation`
    (convergence_attestor A1..A6 per DEC-V61-038)
- `wall_y_plus_range` (near-wall mesh quality · all RANS cases)
"""

from __future__ import annotations

from .base import Metric, MetricClass


class ResidualMetric(Metric):
    metric_class = MetricClass.RESIDUAL
    delegate_to_module = "src.convergence_attestor"
