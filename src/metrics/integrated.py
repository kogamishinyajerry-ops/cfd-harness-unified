"""IntegratedMetric · P1-T1b extractor wrapper.

Domain / boundary integral quantity (CL, CD, Nu_mean, friction_factor,
reattachment_length). Delegates to `src.result_comparator` via the
shared `evaluate_via_result_comparator` wrapper. At this layer,
Pointwise and Integrated are identical (both are scalars produced by
the extractor); the `metric_class` label carries the semantic distinction
for tolerance-policy lookup per VCP §8.2 → METRICS §4 dispatch.

Examples of integrated metrics in the 10-case whitelist:
- `cd_mean` / `cl_rms` (circular_cylinder_wake via forceCoeffs integration)
- `Nu_mean` (impinging_jet, differential_heated_cavity)
- `friction_factor` (duct_flow · integrated wall shear)
- `reattachment_length_xr` (backward_facing_step · wall-shear integral τ_x=0)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._comparator_wrap import evaluate_via_result_comparator
from .base import Metric, MetricClass, MetricReport


class IntegratedMetric(Metric):
    metric_class = MetricClass.INTEGRATED
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
