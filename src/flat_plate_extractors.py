"""DEC-V61-063 Stage A.1 · turbulent_flat_plate secondary observable extractors.

Pure-helper extractors operating on the per-x Cf list and raw u(y) line
samples produced by ``foam_agent_adapter._extract_flat_plate_cf``. Designed
for the LAMINAR Blasius regime declared by V61-006 (Re=50000,
plate_length=1.0m, Re_x ≤ 5e4 — well below transition):

  - ``compute_blasius_invariant(cf_x_pairs)``  → mean / std / per-x of
        K_x = Cf · √Re_x. Per the Blasius similarity solution K = 0.664,
        independent of x. Tight invariant: ≤5% std/mean catches non-similar
        flow patterns the per-point Cf check (10% relative) would miss.

  - ``compute_delta_99_at_x(u_line, U_inf, x, nu)``  → δ_99(x), the
        wall-normal distance at which u_x = 0.99 · U_∞. Compared to the
        Blasius analytical δ_99(x) = 5 · √(ν · x / U_∞).

  - ``canonicalize_turbulence_model(declared)``  → strip-based
        normalization mirroring V61-059 plane_channel_extractors so
        ``"k-omega SST"``, ``"kOmegaSST"``, and ``"k_omega_SST"`` all map
        to the same canonical key. Trust gate: only laminar / known-RANS
        names produce non-None.

  - ``profile_signal_metrics(cf_x_pairs)``  → numerical_floor / amplitude
        / SNR diagnostic for the Cf(x) profile. Conservative SNR uses
        ``max(spacings)`` per V61-059 R2 F4 (worst-case interpolation
        error bound).

Each extractor:
  - takes an explicit data list/dict (no hidden adapter coupling),
  - returns a frozen dataclass / dict so the comparator can decide
    HARD_FAIL vs ADVISORY based on diagnostics,
  - fails LOUD on degenerate inputs (raises ``FlatPlateExtractorError``)
    so a corrupt or under-resolved input becomes a MISSING_TARGET_QUANTITY
    at the gate rather than a silent ATTEST_PASS-via-extractor-bug
    (the very class of failure DEC-V61-036c warned about).

Module is Execution-plane (registered in ``src._plane_assignment``) — it
must not import from ``src.auto_verifier``, ``src.metrics``,
``src.report_engine``, or any other Evaluation-plane module per ADR-001.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Errors & dataclasses
# ---------------------------------------------------------------------------


class FlatPlateExtractorError(Exception):
    """Raised when input is malformed (empty, NaN, degenerate spacing).

    Distinct from "input absent" — absence is signalled by the adapter
    skipping the extraction call, not by raising here. Malformed inputs
    fail loudly so fixture corruption is not silently hidden, mirroring
    the V61-059 PlaneChannelEmitterError contract.
    """


@dataclass(frozen=True)
class BlasiusInvariant:
    """K_x = Cf · √Re_x diagnostics for the laminar Blasius similarity check.

    Attributes:
        mean_K: arithmetic mean of K across sampled x.
        std_K: sample std (n-1) of K across sampled x.
        rel_spread: std_K / mean_K — the dimensionless tightness number
            the comparator gate compares against the 5% invariant tolerance.
        per_x_K: ordered map x → K_x for audit-package transparency.
        n_samples: count contributing to mean/std.
        canonical_K: 0.664 (Blasius constant) — included so reports can
            display the gold value next to the measured mean without a
            second magic-number reach-through.
    """

    mean_K: float
    std_K: float
    rel_spread: float
    per_x_K: Tuple[Tuple[float, float], ...]
    n_samples: int
    canonical_K: float = 0.664


@dataclass(frozen=True)
class ProfileSignalMetrics:
    """SNR-style diagnostics for the Cf(x) profile.

    Used by the comparator to attach an ADVISORY note when the Cf profile
    is technically within tolerance but lacks meaningful dynamic range
    (e.g., all 4 sampled x's returned ~0.005, masking whether the
    extractor is responding to x at all).

    Attributes:
        numerical_floor: smallest absolute Cf value across the profile
            (max(|Cf|.min(), 1e-12) to avoid log(0) downstream).
        amplitude: max(Cf) - min(Cf) across the profile.
        snr_ratio: amplitude / numerical_floor — dimensionless dynamic
            range. Higher is better. Anything < 1.5 means the profile
            is essentially flat and the gate should be ADVISORY.
        sample_spacing_floor: ``max(spacing(Cf_pairs by x))`` — the
            worst-case x-spacing used as a conservative interpolation
            error bound (V61-059 R2 F4 fix).
    """

    numerical_floor: float
    amplitude: float
    snr_ratio: float
    sample_spacing_floor: float


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Blasius similarity invariant: K_x ≡ Cf · √Re_x = 0.664 for the laminar
# zero-pressure-gradient flat plate. Schlichting BL theory 7th ed. §7.3
# eq. (7.50). Source-of-truth: knowledge/gold_standards/turbulent_flat_plate.yaml
# physics_contract block. Hardcoded here so the extractor doesn't have a
# YAML-loading side effect (Execution-plane purity).
BLASIUS_INVARIANT_K: float = 0.664

# Blasius δ_99 prefactor: δ_99(x) = BLASIUS_DELTA99_PREFACTOR · √(ν · x / U_∞).
# Schlichting eq. (7.52). Same provenance as BLASIUS_INVARIANT_K.
BLASIUS_DELTA99_PREFACTOR: float = 5.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_finite(name: str, value: float) -> float:
    """Reject NaN / Inf inputs at the boundary; preserves invariant
    that all downstream arithmetic stays finite."""
    if not math.isfinite(value):
        raise FlatPlateExtractorError(
            f"{name} must be finite, got {value!r}"
        )
    return float(value)


def _validate_positive(name: str, value: float) -> float:
    v = _validate_finite(name, value)
    if v <= 0.0:
        raise FlatPlateExtractorError(
            f"{name} must be > 0, got {v}"
        )
    return v


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_blasius_invariant(
    cf_x_pairs: Sequence[Tuple[float, float]],
    *,
    U_inf: float,
    nu: float,
    x_min: float = 0.25,
) -> BlasiusInvariant:
    """Compute K_x = Cf · √Re_x diagnostics across the sampled profile.

    Skips x < ``x_min`` to avoid the inlet-sensitive region where the
    Blasius similarity assumption is most fragile (intake §6 risk
    ``blasius_invariant_extreme_sensitivity_to_inlet_drift``).

    Args:
        cf_x_pairs: sequence of (x, Cf) pairs from the multi-x extractor.
        U_inf: free-stream velocity (m/s).
        nu: kinematic viscosity (m²/s).
        x_min: minimum x to include in the invariant (m). Default 0.25 m
            is documented in the intake.

    Returns:
        BlasiusInvariant with mean / std / per-x K + sample count.

    Raises:
        FlatPlateExtractorError: empty profile / non-finite values /
            non-positive U_inf or nu / fewer than 2 samples after
            x_min filter (cannot compute std).
    """
    if not cf_x_pairs:
        raise FlatPlateExtractorError("cf_x_pairs is empty")
    U_inf = _validate_positive("U_inf", U_inf)
    nu = _validate_positive("nu", nu)
    x_min = _validate_finite("x_min", x_min)

    per_x_K_list: list[Tuple[float, float]] = []
    for raw in cf_x_pairs:
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            raise FlatPlateExtractorError(
                f"cf_x_pairs entries must be (x, Cf) tuples, got {raw!r}"
            )
        x = _validate_finite("x", float(raw[0]))
        Cf = _validate_finite("Cf", float(raw[1]))
        if x < x_min:
            continue
        if Cf <= 0.0:
            # Cf should always be positive on a flat plate (drag, not thrust).
            # A non-positive value means an upstream extractor sign error,
            # not a physics regime. Fail loud.
            raise FlatPlateExtractorError(
                f"Cf must be > 0 at x={x}, got {Cf}"
            )
        Re_x = U_inf * x / nu
        if Re_x <= 0.0:
            raise FlatPlateExtractorError(
                f"Re_x must be > 0 at x={x} (U_inf={U_inf}, nu={nu})"
            )
        K = Cf * math.sqrt(Re_x)
        per_x_K_list.append((x, K))

    n = len(per_x_K_list)
    if n < 2:
        raise FlatPlateExtractorError(
            f"need ≥2 samples with x ≥ {x_min} m for invariant, got {n} "
            f"({len(cf_x_pairs)} input pairs total)"
        )

    Ks = [K for _, K in per_x_K_list]
    mean_K = sum(Ks) / n
    # Sample variance (n-1 denominator).
    var = sum((K - mean_K) ** 2 for K in Ks) / (n - 1)
    std_K = math.sqrt(var)
    # rel_spread guard: if mean is near-zero we'd divide by ~0 — an upstream
    # sign-flipped Cf would have raised already, but be defensive.
    if mean_K <= 0.0:
        raise FlatPlateExtractorError(
            f"mean K is non-positive ({mean_K}); cf_x_pairs likely corrupt"
        )
    rel_spread = std_K / mean_K
    return BlasiusInvariant(
        mean_K=mean_K,
        std_K=std_K,
        rel_spread=rel_spread,
        per_x_K=tuple(per_x_K_list),
        n_samples=n,
    )


def compute_delta_99_at_x(
    u_line: Sequence[Tuple[float, float]],
    *,
    U_inf: float,
    x: float,
    nu: float,
) -> Dict[str, float]:
    """Extract δ_99(x) from a wall-normal velocity profile.

    ``u_line`` is the raw cell-center (y, u_x) pairs at a single x slice,
    sorted ascending by y starting at the wall. Computes:
      - ``delta_99``: linear-interpolated y where u_x / U_∞ first reaches 0.99
      - ``delta_99_blasius``: 5 · √(ν · x / U_∞) reference
      - ``rel_error``: (delta_99 - delta_99_blasius) / delta_99_blasius

    Returns a plain dict (not a frozen dataclass) so caller can merge
    directly into ``key_quantities``.

    Args:
        u_line: sequence of (y, u_x) pairs from the wall-normal sampling
            (typically 20-80 points spanning 0 ≤ y ≤ H/2).
        U_inf: free-stream velocity (m/s). Used to normalize u_x and to
            compute the Blasius reference.
        x: streamwise position of this slice (m). Used only for the
            Blasius reference; not for u_line interpretation.
        nu: kinematic viscosity (m²/s).

    Raises:
        FlatPlateExtractorError: degenerate input (≤2 samples, all u_x ≤ 0,
            non-positive U_inf/nu/x, profile never reaches 0.99·U_∞).
    """
    U_inf = _validate_positive("U_inf", U_inf)
    nu = _validate_positive("nu", nu)
    x = _validate_positive("x", x)

    rows: list[Tuple[float, float]] = []
    for raw in u_line:
        if not isinstance(raw, (tuple, list)) or len(raw) != 2:
            raise FlatPlateExtractorError(
                f"u_line entries must be (y, u_x) tuples, got {raw!r}"
            )
        y = _validate_finite("y", float(raw[0]))
        u = _validate_finite("u_x", float(raw[1]))
        rows.append((y, u))
    if len(rows) < 3:
        raise FlatPlateExtractorError(
            f"need ≥3 (y, u_x) samples, got {len(rows)}"
        )
    rows.sort(key=lambda r: r[0])
    threshold = 0.99 * U_inf

    # Linear interpolation: find the first interval [y_i, y_{i+1}] across
    # which u_x crosses 0.99·U_∞ from below. Using monotonic-up assumption
    # for the BL profile (valid pre-separation; flat plate ZPG is far from
    # separation).
    delta_99: Optional[float] = None
    for (y0, u0), (y1, u1) in zip(rows[:-1], rows[1:]):
        if u0 < threshold <= u1:
            # Monotonic crossing — interpolate linearly.
            denom = u1 - u0
            if denom <= 0.0:
                continue  # not a true crossing
            alpha = (threshold - u0) / denom
            delta_99 = y0 + alpha * (y1 - y0)
            break

    if delta_99 is None:
        raise FlatPlateExtractorError(
            f"profile at x={x} m never reaches 0.99·U_∞ ({threshold} m/s); "
            f"BL likely under-resolved or U_∞ value is wrong "
            f"(max sampled u={max(u for _, u in rows):.6f})"
        )

    delta_99_blasius = BLASIUS_DELTA99_PREFACTOR * math.sqrt(nu * x / U_inf)
    rel_error = (delta_99 - delta_99_blasius) / delta_99_blasius
    return {
        "delta_99": delta_99,
        "delta_99_blasius": delta_99_blasius,
        "rel_error": rel_error,
        "x": x,
    }


def profile_signal_metrics(
    cf_x_pairs: Sequence[Tuple[float, float]],
) -> ProfileSignalMetrics:
    """Compute SNR-style diagnostics for the Cf(x) profile.

    Mirrors V61-059 plane_channel_extractors.compute_uplus_profile_signal_metrics
    but operates on the (x, Cf) sequence instead of (y+, u+). Same
    conservative ``max(spacings)`` floor (V61-059 R2 F4).

    Returns ProfileSignalMetrics. Raises on degenerate input (empty, all
    Cf identical, NaN values).
    """
    if not cf_x_pairs:
        raise FlatPlateExtractorError("cf_x_pairs is empty")
    pairs: list[Tuple[float, float]] = []
    for raw in cf_x_pairs:
        x = _validate_finite("x", float(raw[0]))
        Cf = _validate_finite("Cf", float(raw[1]))
        pairs.append((x, Cf))
    if len(pairs) < 2:
        raise FlatPlateExtractorError(
            f"need ≥2 (x, Cf) samples for SNR, got {len(pairs)}"
        )
    pairs.sort(key=lambda r: r[0])
    Cfs = [Cf for _, Cf in pairs]
    abs_min = min(abs(c) for c in Cfs)
    numerical_floor = max(abs_min, 1e-12)
    amplitude = max(Cfs) - min(Cfs)
    snr_ratio = amplitude / numerical_floor

    # Conservative interpolation-error bound: max(spacings) per V61-059
    # R2 F4. min(spacings) was optimistic and pretended SNR ≈ ∞ on any
    # flat segment (e.g., adapter dropping all samples but two adjacent x).
    spacings = [pairs[i + 1][0] - pairs[i][0] for i in range(len(pairs) - 1)]
    sample_spacing_floor = max(spacings) if spacings else 0.0

    return ProfileSignalMetrics(
        numerical_floor=numerical_floor,
        amplitude=amplitude,
        snr_ratio=snr_ratio,
        sample_spacing_floor=sample_spacing_floor,
    )


def canonicalize_turbulence_model(declared: Optional[str]) -> Optional[str]:
    """Normalize a turbulence-model declaration to a canonical key.

    Strip-based normalization (V61-059 plane_channel_extractors pattern):
    every space, hyphen, and underscore is removed before case-folding,
    so ``"k-omega SST"``, ``"kOmegaSST"``, ``"k_omega_SST"``, and
    ``"K-Omega-SST"`` all collapse to the same lookup key.

    Returns the canonical name (camelCase) on a recognized declaration,
    ``"laminar"`` on the literal laminar input, or ``None`` on any
    unrecognized / empty input. The None signal lets the comparator gate
    treat unrecognized declarations as untrusted (fail-closed pessimistic
    default).

    Recognized RANS keys mirror knowledge/whitelist.yaml turbulence_model
    spellings: kOmegaSST, kEpsilon, RealizableKE, SpalartAllmaras.
    """
    if declared is None:
        return None
    if not isinstance(declared, str):
        return None
    raw = declared.strip()
    if not raw:
        return None
    # Strip whitespace / hyphens / underscores; case-fold to lower.
    key = re.sub(r"[\s\-_]+", "", raw).lower()
    if key == "laminar":
        return "laminar"
    canonical_table: Dict[str, str] = {
        "komegasst": "kOmegaSST",
        "kepsilon": "kEpsilon",
        "realizablekepsilon": "RealizableKE",
        "realizableke": "RealizableKE",
        "spalartallmaras": "SpalartAllmaras",
    }
    return canonical_table.get(key)


# ---------------------------------------------------------------------------
# Aggregator (called by the adapter post-extraction)
# ---------------------------------------------------------------------------


def enrich_cf_profile(
    cf_x_pairs: Sequence[Tuple[float, float]],
    u_line_at_x_for_delta_99: Dict[float, Sequence[Tuple[float, float]]],
    *,
    U_inf: float,
    nu: float,
) -> Dict[str, object]:
    """One-call enrichment: returns the dict to merge into key_quantities.

    Computes the Blasius invariant + the Cf profile signal metrics in
    one shot, plus a δ_99 entry per (x, u_line_at_x) entry the caller
    supplies.

    Caller is responsible for providing:
      - ``cf_x_pairs``: the multi-x Cf result from
        ``foam_agent_adapter._extract_flat_plate_cf`` (post Stage A.2
        generalization).
      - ``u_line_at_x_for_delta_99``: ``{x: [(y, u_x), ...]}`` for the
        x's where δ_99 should be computed (typically 0.5 and 1.0).
      - ``U_inf`` and ``nu``: reference free-stream conditions.

    Returns a dict ready to ``key_quantities.update(...)`` with:
      - ``cf_blasius_invariant_mean_K``
      - ``cf_blasius_invariant_std_K``
      - ``cf_blasius_invariant_rel_spread``
      - ``cf_blasius_invariant_per_x_K``
      - ``cf_blasius_invariant_n_samples``
      - ``cf_profile_numerical_floor``
      - ``cf_profile_amplitude``
      - ``cf_profile_snr_ratio``
      - ``cf_profile_sample_spacing_floor``
      - ``delta_99_at_x_<x_str>``  (one per supplied x)
      - ``delta_99_blasius_at_x_<x_str>``
      - ``delta_99_rel_error_at_x_<x_str>``

    Errors propagate (FlatPlateExtractorError); caller (adapter) decides
    whether to swallow them into a missing-target-quantity flag or
    propagate further.
    """
    invariant = compute_blasius_invariant(cf_x_pairs, U_inf=U_inf, nu=nu)
    snr = profile_signal_metrics(cf_x_pairs)
    out: Dict[str, object] = {
        "cf_blasius_invariant_mean_K": invariant.mean_K,
        "cf_blasius_invariant_std_K": invariant.std_K,
        "cf_blasius_invariant_rel_spread": invariant.rel_spread,
        "cf_blasius_invariant_per_x_K": list(invariant.per_x_K),
        "cf_blasius_invariant_n_samples": invariant.n_samples,
        "cf_blasius_invariant_canonical_K": invariant.canonical_K,
        "cf_profile_numerical_floor": snr.numerical_floor,
        "cf_profile_amplitude": snr.amplitude,
        "cf_profile_snr_ratio": snr.snr_ratio,
        "cf_profile_sample_spacing_floor": snr.sample_spacing_floor,
    }
    for x_pos, u_line in u_line_at_x_for_delta_99.items():
        d = compute_delta_99_at_x(u_line, U_inf=U_inf, x=x_pos, nu=nu)
        # Use a stable string key for the x position — formatted with
        # one decimal so 0.5 → "0p5" stays canonical regardless of float
        # repr drift.
        x_key = f"{x_pos:.4f}".rstrip("0").rstrip(".").replace(".", "p")
        out[f"delta_99_at_x_{x_key}"] = d["delta_99"]
        out[f"delta_99_blasius_at_x_{x_key}"] = d["delta_99_blasius"]
        out[f"delta_99_rel_error_at_x_{x_key}"] = d["rel_error"]
    return out
