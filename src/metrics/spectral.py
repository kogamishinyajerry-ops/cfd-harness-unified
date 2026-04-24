"""SpectralMetric · P1-T1 MVP skeleton.

Frequency-domain quantity derived via FFT. Delegates to
`src.cylinder_strouhal_fft` when P1-T1c DEC lands the extractor wrapper.
Typically consumes forceCoeffs time series + applies windowed FFT +
peak-finding under an SNR floor.

Examples of spectral metrics in the 10-case whitelist:
- `strouhal_number` (circular_cylinder_wake · St = f D / U)
- `shedding_frequency_hz` (same case, raw frequency)
- `dominant_mode_wavelength` (future DECs if POD / DMD added)
"""

from __future__ import annotations

from .base import Metric, MetricClass


class SpectralMetric(Metric):
    metric_class = MetricClass.SPECTRAL
    delegate_to_module = "src.cylinder_strouhal_fft"
