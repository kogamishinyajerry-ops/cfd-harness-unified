"""DEC-V61-059 Stage A.2 — tests for plane_channel_extractors.

Coverage:
    1. compute_friction_coefficient — formula correctness (Dean ref)
    2. compute_friction_coefficient — fail-closed on bad inputs
    3. ProfileSignalMetrics — SNR semantics (≥10× when profile is rich)
    4. compute_uplus_profile_signal_metrics — degenerate inputs report 0
    5. canonicalize_turbulence_model — model-name normalization
    6. enrich_emitted_profile — full path with C_f + SNR + canonical model
    7. enrich_emitted_profile — None / missing inputs degrade gracefully
    8. merge_secondary_into_key_quantities — dict mutation idempotent
    9. plane_channel_uplus_emitter integration — kwargs back-compat
"""

from __future__ import annotations

import math

import pytest

from src.plane_channel_extractors import (
    PlaneChannelExtractorError,
    ProfileSignalMetrics,
    SecondaryObservables,
    canonicalize_turbulence_model,
    compute_friction_coefficient,
    compute_uplus_profile_signal_metrics,
    enrich_emitted_profile,
    merge_secondary_into_key_quantities,
)


# ---------------------------------------------------------------------------
# friction coefficient
# ---------------------------------------------------------------------------

def test_compute_friction_coefficient_matches_dean_correlation_at_re_b_14000():
    """Re_τ ≈ 395 → u_τ ≈ 0.0099 m/s with h=1, ν=2.5e-5; U_b ≈ 0.35 m/s
    (Re_b ≈ 14000). C_f = 2·(0.0099/0.35)² ≈ 1.6e-3, in the right
    band for plane channel at this Re_b.
    """
    cf = compute_friction_coefficient(u_tau=0.0099, U_bulk=0.35)
    assert 1.4e-3 < cf < 1.8e-3


def test_compute_friction_coefficient_textbook_unit_case():
    """u_τ = U_b → C_f = 2; trivial sanity for the formula constants."""
    cf = compute_friction_coefficient(u_tau=1.0, U_bulk=1.0)
    assert cf == pytest.approx(2.0)


def test_compute_friction_coefficient_rejects_zero_u_tau():
    with pytest.raises(PlaneChannelExtractorError, match="positive"):
        compute_friction_coefficient(u_tau=0.0, U_bulk=1.0)


def test_compute_friction_coefficient_rejects_negative_u_tau():
    with pytest.raises(PlaneChannelExtractorError, match="positive"):
        compute_friction_coefficient(u_tau=-0.01, U_bulk=1.0)


def test_compute_friction_coefficient_rejects_zero_U_bulk():
    with pytest.raises(PlaneChannelExtractorError, match="too small"):
        compute_friction_coefficient(u_tau=0.01, U_bulk=0.0)


def test_compute_friction_coefficient_rejects_nan():
    with pytest.raises(PlaneChannelExtractorError, match="finite"):
        compute_friction_coefficient(u_tau=float("nan"), U_bulk=1.0)
    with pytest.raises(PlaneChannelExtractorError, match="finite"):
        compute_friction_coefficient(u_tau=1.0, U_bulk=float("inf"))


# ---------------------------------------------------------------------------
# SNR / signal metrics
# ---------------------------------------------------------------------------

def test_signal_metrics_high_snr_when_sampling_is_uniform_in_uplus():
    """A profile whose adjacent u+ samples are evenly spaced passes
    the RETRO-V61-050 SNR ≥ 10× threshold under the conservative
    worst-case floor (Codex round-2 F4: floor = max Δu+ between
    adjacent samples). The diagnostic is *intentionally pessimistic*
    — a profile that achieves SNR ≥ 10× has been sampled densely
    enough that worst-case interpolation error is <10% of profile
    amplitude. For a realistic Moser-shaped channel curve this
    requires sampling at ≥30 evenly-spaced u+ points.
    """
    n = 60  # 60 sample points over the half-channel
    u_plus = [i * (18.3 / (n - 1)) for i in range(n)]
    # y+ mapping is monotone but irrelevant to the SNR floor; the
    # floor is computed in u+ space.
    y_plus = [i * (150.0 / (n - 1)) for i in range(n)]
    sig = compute_uplus_profile_signal_metrics(y_plus, u_plus)
    assert sig.profile_amplitude == pytest.approx(18.3)
    # max Δu+ ≈ 18.3/59 ≈ 0.31 → snr ≈ 59 (well above 10×)
    assert sig.snr > 10.0


def test_signal_metrics_loglaw_profile_under_resolved_at_sublayer_boundary():
    """A 64-point UNIFORM-IN-Y+ Moser-like profile fails the 10× SNR
    threshold under conservative max(spacings) — the y+=5 sublayer-to-
    log-law transition produces a single Δu+ ≈ 5 jump that
    bounds interpolation error from below. This is exactly the
    under-resolution that RETRO-V61-050 SNR diagnostic should surface
    on real plane-channel emissions; the gate informs the user
    'sample more densely near y+=5' instead of silently passing.
    """
    import math as _m

    n = 64
    y_plus = [i * (150.0 / (n - 1)) for i in range(n)]
    u_plus = []
    for yp in y_plus:
        if yp <= 5.0:
            u_plus.append(yp)
        else:
            u_plus.append(min(19.0, (1 / 0.41) * _m.log(max(yp, 1.0)) + 5.2))
    sig = compute_uplus_profile_signal_metrics(y_plus, u_plus)
    # Max gap is the y+=2.38 → y+=4.76 → y+=7.14 region where
    # log-law jumps abruptly above the linear sublayer.
    assert sig.snr < 10.0
    assert sig.snr > 1.0  # not pathological


def test_signal_metrics_low_snr_for_sparse_non_uniform_profile():
    """Codex round-2 F4 regression: under the previous min(spacings)
    floor, a sparse non-uniform profile reported SNR > 10× even
    though the largest u+ gap was a meaningful fraction of the
    amplitude. Switching to max(spacings) collapses the false
    high-SNR for under-sampled curves — exactly what RETRO-V61-050
    asks the SNR diagnostic to surface.
    """
    # 10-point Moser-like profile (the OLD test fixture). Under
    # min(spacings)=0.7 the SNR was ~27×; under max(spacings)=4.0
    # it should drop to ~4.75×.
    y_plus = [0.0, 1.0, 5.0, 10.0, 20.0, 30.0, 50.0, 75.0, 100.0, 150.0]
    u_plus = [0.0, 1.0, 5.0, 8.5, 11.5, 13.5, 15.4, 16.7, 18.3, 19.0]
    sig = compute_uplus_profile_signal_metrics(y_plus, u_plus)
    assert sig.profile_amplitude == pytest.approx(19.0)
    # Worst-case Δu+ = 4.0 (the y+=5→y+=10 jump or y+=1→y+=5),
    # so SNR = 19 / 4 ≈ 4.75 — below the 10× threshold.
    assert sig.snr < 10.0
    assert sig.snr > 4.0
    assert sig.sample_spacing_floor == pytest.approx(4.0)


def test_signal_metrics_degenerate_constant_profile_reports_zero_snr():
    sig = compute_uplus_profile_signal_metrics([0.0, 1.0, 2.0], [5.0, 5.0, 5.0])
    assert sig.snr == 0.0
    assert sig.profile_amplitude == 0.0


def test_signal_metrics_handles_empty_input():
    sig = compute_uplus_profile_signal_metrics([], [])
    assert sig.snr == 0.0
    assert sig.sample_spacing_floor == 0.0
    assert sig.profile_amplitude == 0.0


def test_signal_metrics_filters_nan_and_inf_samples():
    y_plus = [0.0, 5.0, float("nan"), 30.0]
    u_plus = [0.0, 5.4, 11.0, 13.5]
    sig = compute_uplus_profile_signal_metrics(y_plus, u_plus)
    # NaN sample is dropped — remaining 3 points still produce a
    # meaningful amplitude.
    assert math.isfinite(sig.snr)
    assert sig.profile_amplitude == pytest.approx(13.5)


# ---------------------------------------------------------------------------
# turbulence model canonicalization
# ---------------------------------------------------------------------------

def test_canonicalize_turbulence_model_known_aliases():
    assert canonicalize_turbulence_model("kOmegaSST") == "kOmegaSST"
    assert canonicalize_turbulence_model("kOMEGAsst") == "kOmegaSST"
    assert canonicalize_turbulence_model("laminar") == "laminar"
    assert canonicalize_turbulence_model("LAMINAR") == "laminar"


def test_canonicalize_turbulence_model_hyphenated_repo_spellings():
    """Codex round-1 F2 regression: knowledge/whitelist.yaml uses
    'k-omega SST' and 'k-epsilon' for several cases (BFS at line 215,
    impinging_jet at 243, NACA at 137 etc.). Without strip-based
    normalization, those values fall through and G2 false-fires
    CANONICAL_BAND_SHORTCUT_LAMINAR_DNS on legitimate turbulent runs.
    Verify hyphens, spaces, and underscores all collapse to the same
    canonical camelCase identifier.
    """
    assert canonicalize_turbulence_model("k-omega SST") == "kOmegaSST"
    assert canonicalize_turbulence_model("k-omega sst") == "kOmegaSST"
    assert canonicalize_turbulence_model("k omega SST") == "kOmegaSST"
    assert canonicalize_turbulence_model("k_omega_sst") == "kOmegaSST"
    assert canonicalize_turbulence_model("k-epsilon") == "kEpsilon"
    assert canonicalize_turbulence_model("k epsilon") == "kEpsilon"
    assert canonicalize_turbulence_model("RNG k-epsilon") == "RNGkEpsilon"
    assert canonicalize_turbulence_model("spalart-allmaras") == "SpalartAllmaras"
    assert canonicalize_turbulence_model("realizable k-epsilon") == "realizableKE"


def test_canonicalize_turbulence_model_none_or_empty():
    assert canonicalize_turbulence_model(None) == "<not declared>"
    assert canonicalize_turbulence_model("") == "<not declared>"
    assert canonicalize_turbulence_model("   ") == "<not declared>"


def test_canonicalize_turbulence_model_unknown_passthrough():
    """Unknown model names pass through unchanged so the gate can
    recognize them as 'declared but unrecognized' and treat as untrusted.
    """
    assert canonicalize_turbulence_model("frobnozzle") == "frobnozzle"


# ---------------------------------------------------------------------------
# enrich_emitted_profile — full path
# ---------------------------------------------------------------------------

def _moser_emitted_dict() -> dict:
    return {
        "u_mean_profile":         [0.0, 1.0, 5.4, 11.5, 13.5, 18.3],
        "u_mean_profile_y_plus":  [0.0, 1.0, 5.0, 20.0, 30.0, 100.0],
        "u_tau":                  0.0099,
        "Re_tau":                 395.0,
        "wall_shear_stress":      9.8e-5,
        "u_mean_profile_source":  "wallShearStress_fo_v1",
    }


def test_enrich_emitted_profile_full_kOmegaSST_run():
    emitted = _moser_emitted_dict()
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared="kOmegaSST",
    )
    assert isinstance(secondary, SecondaryObservables)
    assert secondary.friction_coefficient is not None
    assert 1.4e-3 < secondary.friction_coefficient < 1.8e-3
    assert secondary.turbulence_model_used == "kOmegaSST"
    assert secondary.u_plus_profile_amplitude == pytest.approx(18.3)
    assert secondary.u_plus_profile_snr > 0.0


def test_enrich_emitted_profile_laminar_run():
    """Laminar declaration → canonical 'laminar' string emitted; G2
    will fire when this combines with canonical-band match.
    """
    emitted = _moser_emitted_dict()
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared="laminar",
    )
    assert secondary.turbulence_model_used == "laminar"
    assert secondary.friction_coefficient is not None  # still computed


def test_enrich_emitted_profile_missing_U_bulk_no_cf():
    emitted = _moser_emitted_dict()
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=None,
        turbulence_model_declared="kOmegaSST",
    )
    assert secondary.friction_coefficient is None
    assert "c_f_skip_reason" in secondary.diagnostics


def test_enrich_emitted_profile_missing_u_tau_no_cf():
    emitted = _moser_emitted_dict()
    emitted["u_tau"] = None  # type: ignore[assignment]
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared="kOmegaSST",
    )
    assert secondary.friction_coefficient is None


def test_enrich_emitted_profile_no_turbulence_declaration():
    emitted = _moser_emitted_dict()
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared=None,
    )
    assert secondary.turbulence_model_used == "<not declared>"


# ---------------------------------------------------------------------------
# merge_secondary_into_key_quantities
# ---------------------------------------------------------------------------

def test_merge_writes_canonical_keys():
    emitted = _moser_emitted_dict()
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared="kOmegaSST",
    )
    out = merge_secondary_into_key_quantities(emitted, secondary)
    assert out is emitted  # mutates in place
    assert out["friction_coefficient"] == secondary.friction_coefficient
    assert out["turbulence_model_used"] == "kOmegaSST"
    assert out["u_plus_profile_snr"] == secondary.u_plus_profile_snr
    assert out["u_plus_profile_numerical_floor"] == secondary.u_plus_profile_floor
    assert out["u_plus_profile_amplitude"] == secondary.u_plus_profile_amplitude


def test_merge_skips_friction_coefficient_when_none():
    emitted = _moser_emitted_dict()
    emitted.pop("u_tau")  # forces C_f = None
    secondary = enrich_emitted_profile(
        emitted,
        U_bulk=0.35,
        turbulence_model_declared="kOmegaSST",
    )
    out = merge_secondary_into_key_quantities(emitted, secondary)
    assert "friction_coefficient" not in out  # don't surface a None
    assert "plane_channel_extractor_diagnostics" in out
    assert "c_f_skip_reason" in out["plane_channel_extractor_diagnostics"]


# ---------------------------------------------------------------------------
# emitter integration — kwargs backward compatibility
# ---------------------------------------------------------------------------

def test_emit_uplus_profile_signature_accepts_optional_secondary_kwargs():
    """Smoke-test: the emitter signature accepts U_bulk +
    turbulence_model_declared, and pre-DEC-V61-059 callers without
    those kwargs still call cleanly. Actual emit logic requires real
    postProcessing inputs and is covered by integration tests; here
    we only need the signature.
    """
    import inspect

    from src.plane_channel_uplus_emitter import emit_uplus_profile

    sig = inspect.signature(emit_uplus_profile)
    assert "nu" in sig.parameters
    assert "half_height" in sig.parameters
    assert "U_bulk" in sig.parameters
    assert "turbulence_model_declared" in sig.parameters
    # New params must be optional (default None) for backward compat.
    assert sig.parameters["U_bulk"].default is None
    assert sig.parameters["turbulence_model_declared"].default is None
