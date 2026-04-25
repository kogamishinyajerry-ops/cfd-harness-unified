"""DEC-V61-059 Stage A.2 — secondary observable extractors for plane channel.

Wraps `plane_channel_uplus_emitter.emit_uplus_profile` (DEC-V61-043) with
the additional gates DEC-V61-059 introduces:

  * friction_coefficient (C_f = 2 · (u_τ / U_b)²)
  * turbulence_model_used (consumed by comparator_gates.G2 to discriminate
    laminar canonical-band shortcuts from honest turbulence-resolving runs)
  * numerical_floor + signal_above_noise_ratio per RETRO-V61-050 noise
    contract — surfaces interpolation-noise-vs-physics ratio so the UI
    can flag SNR < 10× as a warning without hard-failing the gate.

Pattern follows src/wall_gradient.py: immutable dataclasses, an explicit
contract-violation exception, and small pure-function helpers. ADR-001:
this module lives in the Execution plane (read by the adapter's extractor
path) and does NOT import from comparator_gates / result_comparator /
auto_verifier (Evaluation plane).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple


class PlaneChannelExtractorError(Exception):
    """Raised when secondary-observable inputs are present but malformed.

    Distinct from "inputs absent" — absence allows the parent emitter to
    return None; malformed inputs fail loudly so fixture corruption is
    not silently masked (DEC-V61-040 round-2 pattern).
    """


# ---------------------------------------------------------------------------
# friction coefficient
# ---------------------------------------------------------------------------

def compute_friction_coefficient(
    u_tau: float,
    U_bulk: float,
) -> float:
    """C_f = 2 · (u_τ / U_b)² — channel-flow skin friction.

    Plane-channel definition is `tau_w = (1/2) ρ U_b² C_f`, so
    `tau_w/ρ = u_τ² = (1/2) U_b² C_f` → C_f = 2 (u_τ/U_b)². This is the
    convention Dean (1978) reports and is consistent with the Moser
    DNS framework (u_τ comes from wallShearStress FO; U_b from
    boundary-condition plumbing).

    Raises PlaneChannelExtractorError on malformed inputs (non-positive
    or non-finite values) so a divergent / mid-iteration extraction
    cannot produce a silently-wrong C_f.
    """
    if not isinstance(u_tau, (int, float)) or not math.isfinite(u_tau):
        raise PlaneChannelExtractorError(
            f"u_tau must be a finite float, got {u_tau!r}"
        )
    if not isinstance(U_bulk, (int, float)) or not math.isfinite(U_bulk):
        raise PlaneChannelExtractorError(
            f"U_bulk must be a finite float, got {U_bulk!r}"
        )
    if u_tau <= 0.0:
        raise PlaneChannelExtractorError(
            f"u_tau must be positive, got {u_tau}"
        )
    if abs(U_bulk) < 1e-12:
        raise PlaneChannelExtractorError(
            f"U_bulk too small for stable C_f reduction: {U_bulk}"
        )
    return 2.0 * (u_tau / U_bulk) ** 2


# ---------------------------------------------------------------------------
# numerical floor / SNR per RETRO-V61-050 contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProfileSignalMetrics:
    """RETRO-V61-050 noise-floor report for a sampled profile.

    sample_spacing_floor: the minimum |Δu+| separation between adjacent
        sample points in u+ space. Acts as a lower bound on what an
        interpolated u+(y+) value can resolve.
    profile_amplitude: max(u+) − min(u+) over the emitted profile.
        Used as the "signal" in the SNR ratio.
    snr: profile_amplitude / sample_spacing_floor. RETRO-V61-050 calls
        for SNR ≥ 10× before treating the profile as a validated
        measurement.
    """

    sample_spacing_floor: float
    profile_amplitude: float
    snr: float


def compute_uplus_profile_signal_metrics(
    y_plus: Sequence[float],
    u_plus: Sequence[float],
) -> ProfileSignalMetrics:
    """Compute the (numerical_floor, profile_amplitude, snr) triple
    for an emitted u+(y+) profile.

    The "noise floor" model is conservative: take the minimum spacing
    between adjacent u+ samples. Real interpolation noise is bounded
    above by this for any 1D linearly-interpolating extractor — a
    target value at y+ that falls between samples i and i+1 has
    interpolation error at most |u+_{i+1} − u+_i|.

    Returns a frozen dataclass so it can be safely cached / serialized.
    """
    pairs = sorted(
        (yp, up)
        for yp, up in zip(y_plus, u_plus)
        if isinstance(yp, (int, float))
        and isinstance(up, (int, float))
        and math.isfinite(yp)
        and math.isfinite(up)
    )
    if len(pairs) < 2:
        # Degenerate profile — report 0 SNR so downstream UI surfaces
        # this as below-threshold rather than infinite (which would
        # silently look great).
        return ProfileSignalMetrics(
            sample_spacing_floor=0.0,
            profile_amplitude=0.0,
            snr=0.0,
        )

    u_values = [up for _, up in pairs]
    profile_amplitude = max(u_values) - min(u_values)

    spacings = []
    for i in range(len(pairs) - 1):
        du = abs(pairs[i + 1][1] - pairs[i][1])
        if du > 0.0:
            spacings.append(du)
    if not spacings:
        # Constant profile — every adjacent diff is zero; SNR
        # undefined. Report 0 to surface as "no measurable signal".
        return ProfileSignalMetrics(
            sample_spacing_floor=0.0,
            profile_amplitude=profile_amplitude,
            snr=0.0,
        )

    sample_spacing_floor = min(spacings)
    if sample_spacing_floor < 1e-12:
        snr = 0.0
    else:
        snr = profile_amplitude / sample_spacing_floor
    return ProfileSignalMetrics(
        sample_spacing_floor=sample_spacing_floor,
        profile_amplitude=profile_amplitude,
        snr=snr,
    )


# ---------------------------------------------------------------------------
# turbulence-model declaration (G2 contract)
# ---------------------------------------------------------------------------

# Recognized model name normalization. Adapter generator emits e.g.
# `RAS kOmegaSST` in turbulenceProperties; we report a canonical short
# name in key_quantities so the comparator-gate G2 trusted-allowlist
# stays a fixed set rather than a regex pile.
_MODEL_CANONICAL = {
    "laminar":          "laminar",
    "komegasst":        "kOmegaSST",
    "komegasstlm":      "kOmegaSSTLM",
    "kepsilon":         "kEpsilon",
    "rngkepsilon":      "RNGkEpsilon",
    "realizableke":     "realizableKE",
    "realizablekepsilon": "realizableKE",
    "spalartallmaras":  "SpalartAllmaras",
    "smagorinsky":      "Smagorinsky",
    "keqn":             "kEqn",
    "wale":             "WALE",
    "dynamickeqn":      "dynamicKEqn",
    "dns":              "DNS",
}


def canonicalize_turbulence_model(declared: Optional[str]) -> str:
    """Normalize a generator-side turbulence model declaration into the
    canonical key string consumed by comparator_gates.G2.

    None or empty → "<not declared>" (G2 will treat as untrusted-by-default
    per fail-closed semantics).
    Unknown name → return the input verbatim (G2 will not match the
    trusted set; gate fires).
    """
    if not declared:
        return "<not declared>"
    if not isinstance(declared, str):
        return "<not declared>"
    key = declared.strip().lower()
    if not key:
        return "<not declared>"
    return _MODEL_CANONICAL.get(key, declared.strip())


# ---------------------------------------------------------------------------
# top-level enrich entrypoint
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecondaryObservables:
    """Fully-derived secondary scalars + signal metrics for plane channel.

    Field map → key_quantities entries written by `enrich_emitted_profile`:
        friction_coefficient        → "friction_coefficient"
        turbulence_model_used       → "turbulence_model_used"
        u_plus_profile_snr          → "u_plus_profile_snr"
        u_plus_profile_floor        → "u_plus_profile_numerical_floor"
        u_plus_profile_amplitude    → "u_plus_profile_amplitude"
    """

    friction_coefficient: Optional[float]
    turbulence_model_used: str
    u_plus_profile_snr: float
    u_plus_profile_floor: float
    u_plus_profile_amplitude: float
    diagnostics: Dict[str, Any] = field(default_factory=dict)


def enrich_emitted_profile(
    emitted: Dict[str, Any],
    *,
    U_bulk: Optional[float],
    turbulence_model_declared: Optional[str],
) -> SecondaryObservables:
    """Compute secondary observables from an emitter result.

    `emitted` is the dict returned by
    `plane_channel_uplus_emitter.emit_uplus_profile` — must contain
    `u_tau`, `u_mean_profile`, `u_mean_profile_y_plus`. This function
    is a pure transform: no I/O, no external state. Any malformed
    input that prevents a finite C_f propagates as None (rather than
    raising) so the existing emitter's None-return contract is
    preserved on partial failure.
    """
    u_tau = emitted.get("u_tau")
    u_plus = emitted.get("u_mean_profile") or []
    y_plus = emitted.get("u_mean_profile_y_plus") or []

    cf: Optional[float] = None
    cf_diag: Dict[str, Any] = {}
    if (
        isinstance(u_tau, (int, float))
        and isinstance(U_bulk, (int, float))
        and math.isfinite(u_tau)
        and math.isfinite(U_bulk)
        and u_tau > 0.0
        and abs(U_bulk) >= 1e-12
    ):
        try:
            cf = compute_friction_coefficient(float(u_tau), float(U_bulk))
        except PlaneChannelExtractorError as exc:
            cf_diag["c_f_error"] = str(exc)
    else:
        cf_diag["c_f_skip_reason"] = (
            f"u_tau={u_tau!r}, U_bulk={U_bulk!r} — at least one missing/non-positive"
        )

    sig = compute_uplus_profile_signal_metrics(y_plus, u_plus)
    canonical_model = canonicalize_turbulence_model(turbulence_model_declared)

    diagnostics: Dict[str, Any] = {}
    if cf_diag:
        diagnostics.update(cf_diag)

    return SecondaryObservables(
        friction_coefficient=cf,
        turbulence_model_used=canonical_model,
        u_plus_profile_snr=sig.snr,
        u_plus_profile_floor=sig.sample_spacing_floor,
        u_plus_profile_amplitude=sig.profile_amplitude,
        diagnostics=diagnostics,
    )


def merge_secondary_into_key_quantities(
    emitted: Dict[str, Any],
    secondary: SecondaryObservables,
) -> Dict[str, Any]:
    """Merge a SecondaryObservables block into the emitter's dict
    using the canonical key map.

    The returned dict is the same object as `emitted` (mutated in
    place) — caller can use either form. Returning the dict makes
    the emitter call sites readable (`return merge_secondary_into_kq(...)`).
    """
    if secondary.friction_coefficient is not None:
        emitted["friction_coefficient"] = secondary.friction_coefficient
    emitted["turbulence_model_used"] = secondary.turbulence_model_used
    emitted["u_plus_profile_snr"] = secondary.u_plus_profile_snr
    emitted["u_plus_profile_numerical_floor"] = secondary.u_plus_profile_floor
    emitted["u_plus_profile_amplitude"] = secondary.u_plus_profile_amplitude
    if secondary.diagnostics:
        emitted["plane_channel_extractor_diagnostics"] = secondary.diagnostics
    return emitted
