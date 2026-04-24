"""IntegratedMetric · P1-T1 MVP skeleton.

Domain / boundary integral quantity. Delegates to `src.result_comparator`
+ integration helpers when P1-T1b DEC lands the extractor wrapper.

Examples of integrated metrics in the 10-case whitelist:
- `cd_mean` / `cl_rms` (circular_cylinder_wake via forceCoeffs integration)
- `Nu_mean` (impinging_jet, differential_heated_cavity)
- `friction_factor` (duct_flow · integrated wall shear)
- `reattachment_length_xr` (backward_facing_step · wall-shear integral τ_x=0)
"""

from __future__ import annotations

from .base import Metric, MetricClass


class IntegratedMetric(Metric):
    metric_class = MetricClass.INTEGRATED
    delegate_to_module = "src.result_comparator"
