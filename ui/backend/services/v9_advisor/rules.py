"""V91.1 + V91.2 · V9.C ruleset Python binding.

Loads the JSON SSOT at ``ui/frontend/src/data/v9_advisor_rules.json`` and
joins commentary + provenance + severity with Python predicate functions
by rule id. The TS binding at ``ui/frontend/src/data/v9_advisor_rules.ts``
does the analogous join.

V130: this module reads ONE file — the JSON SSOT — at import time. No
network · no subprocess · no other filesystem reads. The predicate
functions are pure (no side effects).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .pattern_matcher import (
    AdvisorRule,
    MatchSite,
    RunArtifactSlice,
    js_to_exponential,
    js_to_fixed,
)

# JSON SSOT location · repo-rooted, both TS and Python read this file.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_JSON_PATH = _REPO_ROOT / "ui" / "frontend" / "src" / "data" / "v9_advisor_rules.json"

# NASA-convention reference_comparison tolerance per DEC-V61-209 ADDENDUM 4
# (lines 304-339) — mirrored verbatim in `flat_plate_cf.py::station_rel`
# gate (`station_rel <= tolerance`). Used by BOTH R10 (station-pass
# precondition) and R12 (PASS/FAIL XOR boundary) so the literal cannot
# drift between the two rules. Per Codex CRS R0 W2.1 R1 fix.
_NASA_TOL_PCT = 10.0


# ---------------------------------------------------------------------------
# Predicate helpers (mirror v9_advisor_rules.ts helpers exactly)
# ---------------------------------------------------------------------------

def _recent_residuals(
    slice_: RunArtifactSlice, quantity: str, count: int
) -> List[float]:
    if slice_.residuals is None:
        return []
    history = slice_.residuals.get(quantity)
    if history is None or len(history) < count:
        return []
    return list(history[-count:])


def _is_monotonically_decreasing(values: List[float]) -> bool:
    if len(values) < 2:
        return False
    for i in range(1, len(values)):
        if values[i] >= values[i - 1]:
            return False
    return True


def _is_monotonically_increasing(values: List[float]) -> bool:
    if len(values) < 2:
        return False
    for i in range(1, len(values)):
        if values[i] <= values[i - 1]:
            return False
    return True


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _is_oscillating(values: List[float], threshold_ratio: float) -> bool:
    if len(values) < 4:
        return False
    mean = sum(values) / len(values)
    mean_mag = abs(mean)
    if mean_mag == 0:
        return False

    sign_flips = 0
    max_amplitude_ratio = 0.0
    for i in range(1, len(values)):
        prev = values[i - 1] - mean
        curr = values[i] - mean
        # Mirror TS: Math.sign(prev) !== Math.sign(curr) && Math.sign(curr) !== 0
        if _sign(prev) != _sign(curr) and _sign(curr) != 0:
            sign_flips += 1
        max_amplitude_ratio = max(
            max_amplitude_ratio,
            abs(values[i] - mean) / mean_mag,
        )
    return sign_flips >= 2 and max_amplitude_ratio > threshold_ratio


# ---------------------------------------------------------------------------
# Predicates (id-keyed · 1:1 with TS PREDICATES_BY_ID)
# ---------------------------------------------------------------------------

def _pred_residual_oscillation_p(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    last8 = _recent_residuals(slice_, "p", 8)
    if len(last8) < 8:
        return None
    if not _is_oscillating(last8, 0.3):
        return None
    final_iter = (
        slice_.convergence_stats.final_iter
        if slice_.convergence_stats is not None
        else len(last8)
    )
    return MatchSite(matched_at=f"iter_{final_iter}_p_residual")


def _pred_max_iters_reached(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None or not slice_.convergence_stats.max_iters_reached:
        return None
    return MatchSite(matched_at="convergence_stats")


def _pred_run_failed_nonzero_exit(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.success is not False:
        return None
    if slice_.exit_code == 0:
        return None
    return MatchSite(matched_at=f"exit_code_{slice_.exit_code}")


def _pred_gold_delta_exceeds_5_pct(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.gold_delta is None:
        return None
    pct = slice_.gold_delta.max_abs_pct
    if pct is None or pct <= 5:
        return None
    return MatchSite(matched_at=f"gold_delta_{js_to_fixed(pct, 2)}pct")


def _pred_forces_not_converged(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    forces = slice_.forces
    if forces is None or len(forces) < 10:
        return None
    last10 = forces[-10:]
    cds = [f.Cd for f in last10]
    cd_mean = sum(cds) / len(cds)
    if abs(cd_mean) < 1e-9:
        return None
    max_drift_pct = max(abs((cd - cd_mean) / cd_mean) for cd in cds) * 100
    if max_drift_pct <= 1:
        return None
    return MatchSite(matched_at=f"forces_drift_{js_to_fixed(max_drift_pct, 2)}pct")


def _pred_slow_convergence(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None:
        return None
    if not slice_.convergence_stats.converged:
        return None
    final = slice_.convergence_stats.final_iter
    if final < 5000:
        return None
    return MatchSite(matched_at=f"iter_{final}_slow_converge")


def _pred_residual_plateau_u(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    last20 = _recent_residuals(slice_, "U", 20)
    if len(last20) < 20:
        return None
    mean = sum(last20) / len(last20)
    mean_mag = abs(mean)
    if mean_mag < 1e-12:
        return None
    variance = sum((v - mean) ** 2 for v in last20) / len(last20)
    std_dev = math.sqrt(variance)
    variation_pct = (std_dev / mean_mag) * 100
    if variation_pct >= 2 or mean_mag < 1e-4:
        return None
    return MatchSite(matched_at=f"U_plateau_{js_to_exponential(mean_mag, 2)}")


def _pred_healthy_convergence(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    if slice_.convergence_stats is None or not slice_.convergence_stats.converged:
        return None
    last8 = _recent_residuals(slice_, "p", 8)
    if len(last8) < 8:
        return None
    if not _is_monotonically_decreasing(last8):
        return None
    return MatchSite(matched_at="healthy_convergence_p")


def _pred_known_deviation_pattern_near_le(
    slice_: RunArtifactSlice,
) -> Optional[MatchSite]:
    # W2.1 · DEC-V61-209 ADDENDUM 5 #2 distillation (DEC-V61-216).
    #
    # R10: HONEST KNOWN KNOWN. Fires only when the scalar gold-delta drift
    # (R4 amplitude floor crossed) is fully explained by the cataloged
    # near-LE OpenFOAM-kΩSST-vs-CFL3D formulation discrepancy:
    #
    #   (1) gold_delta.max_abs_pct > 5%        (R4 would fire in isolation)
    #   (2) developed_region_gold_delta.n_failures == 0
    #                                          (structurally clean past LE)
    #   (3) integrated_drag_pct.within_tolerance is True
    #                                          (NASA dual-metric PASSES)
    #   (4) reference_comparison_band_summary.n_near_le_deviations > 0
    #                                          (≥1 cataloged near-LE row)
    #   (5) reference_comparison_band_summary.x_floor_m is not None
    #                                          (band scope is KNOWN)
    #
    # ALL five conditions must hold; absence of any one silently skips.
    # This is the inverse-polarity discriminator paired with R11.
    #
    # Honest None handling (DEC-V61-213/214/215 R1 carry-forward): any
    # required source field == None → return None. NEVER equate None
    # with 0, False, or empty. The Optional[float] x_floor_m guard
    # mirrors DEC-V61-215 R1 (test_derive_slice_band_summary_x_floor_
    # absent_stays_none_not_zero) — if the cutoff is unknown, the rule
    # CANNOT claim the deviation lives in the documented near-LE band
    # without fabricating "cutoff at the leading edge" (truth-chain
    # violation).
    #
    # KNOWN-GAP (signal-vs-noise discipline · DEC-V61-216 R10 negative
    # contract): R10 is INFORMATIONAL — its absence on a high-gold-delta
    # slice does NOT mean clean. It means R11 or R4 owns the verdict.
    # R10 will NOT fire when:
    #   (a) x_floor_m is None — cutoff unknown; refusing to fabricate.
    #   (b) any of the 4 W2.0.6/legacy fields is None — per_point gate
    #       and legacy V91-era manifests legitimately carry no regional
    #       payload (DEC-215 graceful-skip contract).
    #   (c) developed_region_gold_delta.n_failures > 0 — developed-region
    #       carries genuine failures → R11 territory, not R10.
    #   (d) integrated_drag_pct.within_tolerance is False — NASA gate is
    #       failing → not the demoted-near-LE pattern.
    gd = slice_.gold_delta
    dr = slice_.developed_region_gold_delta
    idp = slice_.integrated_drag_pct
    rcs = slice_.reference_comparison_band_summary
    if gd is None or dr is None or idp is None or rcs is None:
        return None

    # (1) R4 amplitude floor.
    if gd.max_abs_pct is None or gd.max_abs_pct <= 5.0:
        return None
    # (2) Developed region structurally clean.
    if dr.n_failures != 0:
        return None
    # (3) NASA dual-metric gate PASSES — Codex CRS R0 P2 R1 fix:
    #     BOTH the integrated drag tolerance check AND the verification
    #     station tolerance check must pass. The NASA gate is a paired
    #     PASS/PASS contract (DEC-V61-209 ADDENDUM 4 lines 304-339); a
    #     run with integrated within tolerance but station > NASA_TOL_PCT
    #     or station_pct missing is NOT a "demoted near-LE known
    #     deviation" — it's an R12-class discrepancy that R10 must NOT
    #     mask. The boundary uses the same canonical NASA tolerance as
    #     R12 (NASA_TOL_PCT=10.0, inclusive — matches flat_plate_cf.py
    #     `station_rel <= tolerance`).
    if idp.within_tolerance is not True:
        return None
    if idp.station_pct is None:
        return None
    if idp.station_pct > _NASA_TOL_PCT:
        return None
    # (4) ≥1 cataloged near-LE deviation.
    if rcs.n_near_le_deviations <= 0:
        return None
    # (5) Cutoff known (DEC-V61-215 R1 carry-forward — never 0.0 sentinel).
    if rcs.x_floor_m is None:
        return None

    n = rcs.n_near_le_deviations
    worst = rcs.worst_near_le_pct if rcs.worst_near_le_pct is not None else 0.0
    return MatchSite(
        matched_at=f"near_le_known_dev_n{n}_worst{js_to_fixed(worst, 2)}pct"
    )


def _pred_developed_region_shape_mismatch(
    slice_: RunArtifactSlice,
) -> Optional[MatchSite]:
    # W2.1 · DEC-V61-209 ADDENDUM 5 #1 distillation (DEC-V61-216).
    #
    # R11: developed-region per-point FAILURE is qualitatively different
    # from scalar amplitude drift (R4). DEC-V61-209 ADDENDUM 5 #1 added
    # developed_region_min_m = 0.1 m as a THIRD-PASS condition in the
    # NASA-convention gate precisely because integral-drag + a single
    # verification station cannot, on their own, reject a curve whose
    # +/- area errors cancel in the integral AND happens to match at the
    # one station. A per-point failure past x ≥ 0.1 m is a real FAIL,
    # NOT a `known_deviation` laundering candidate.
    #
    # Firing predicate:
    #   (1) developed_region_gold_delta is not None (W2.0.6 populated)
    #   (2) n_failures > 0                          (real per-point fail)
    #   (3) max_abs_pct > 5.0                       (amplitude floor —
    #       discriminator matches R4 scalar; single-point grazing the
    #       gate tolerance at 0.05% is NOT a solver-bug signal worth
    #       surfacing at warn severity)
    #
    # Polarity-paired with R10: when R10 short-circuits at `n_failures
    # != 0`, R11 picks up the same slice (n_failures > 0 + amplitude
    # past the discriminator floor).
    #
    # Honest None handling: developed_region_gold_delta is None → silent
    # skip (per_point gate-mode + legacy manifests legitimately carry
    # no developed-region payload; DEC-V61-215 graceful-skip contract).
    #
    # KNOWN-GAP (signal-vs-noise discipline · DEC-V61-216 R11 negative
    # contract): R11 will NOT fire when:
    #   (a) developed_region_gold_delta is None — per_point gate cases
    #       legitimately carry no developed-region payload (matches
    #       dec209_developed_region_clean_per_point_mode fixture).
    #   (b) n_failures == 0 even when max_abs_pct is high — no per-point
    #       failure → max_abs_pct came from a within-tolerance worst
    #       case → not a shape mismatch.
    #   (c) max_abs_pct ≤ 5.0 — single-point grazing the gate tolerance
    #       (e.g. 5.00%) is not a solver-bug signal worth surfacing at
    #       warn severity. Discriminator floor matches R4 scalar.
    # Rule purposefully ignores n_points (small n_points like 10 is
    # still a valid developed-region grid; not a sample-size gap).
    dr = slice_.developed_region_gold_delta
    if dr is None:
        return None
    if dr.n_failures <= 0:
        return None
    if dr.max_abs_pct is None or dr.max_abs_pct <= 5.0:
        return None
    return MatchSite(
        matched_at=(
            f"developed_region_failures_{dr.n_failures}of{dr.n_points}_"
            f"max{js_to_fixed(dr.max_abs_pct, 2)}pct"
        )
    )


def _pred_integrated_vs_station_discrepancy(
    slice_: RunArtifactSlice,
) -> Optional[MatchSite]:
    # W2.1 · DEC-V61-209 ADDENDUM 4 distillation (DEC-V61-216).
    #
    # R12: NASA-convention dual-metric XOR. DEC-V61-209 ADDENDUM 4
    # (lines 304-339) defines the NASA-canonical gate as integrated-Cf
    # drag + Cf@x=0.97008 station, BOTH within 10% tolerance — paired
    # by physical convention because either alone is gameable. When
    # the two metrics DISAGREE (one PASSES, one FAILS at the same
    # 10% boundary), the divergence itself is a citable finding
    # pattern — typically a post-processing / integration-pipeline bug
    # rather than a CFD issue.
    #
    # DEC-V61-209 lines 226-231 document the canonical incident:
    # cfdtrust extractor pulling a stale time directory → station
    # readout right, integration arithmetic wrong (integration ran
    # over the wrong field). R12 surfaces this incident class.
    #
    # Predicate is a strict PASS/FAIL XOR at NASA_TOL_PCT=10.0 — the
    # canonical NASA tolerance, hard-coded as a literal (no config-file
    # indirection; same literal mirrored in TS predicate for parity).
    # Does NOT match R4's 5% scalar floor by design; ADDENDUM 4
    # explicitly sets 10% as the NASA reference_comparison tolerance.
    #
    # KNOWN-GAP (signal-vs-noise discipline · DEC-V61-216 R12 negative
    # contract): R12 will NOT fire when:
    #   (a) integrated_drag_pct is None — legacy V91-era manifests +
    #       per_point gate-mode cases have no NASA-convention pair
    #       (graceful-skip contract).
    #   (b) integrated_drag_pct.station_pct is None — verification_
    #       station block absent (NASA dual-metric pair incomplete;
    #       refusing to fire on half-data is the truth-chain discipline,
    #       mirrors DEC-V61-215 honest scope-out).
    #   (c) BOTH metrics agree (both pass OR both fail — agreement is
    #       the expected NASA-convention outcome, no discrepancy to
    #       surface).
    # Rule does NOT inspect |pct - station_pct| magnitude — the
    # discriminator is PASS/FAIL boundary-crossing, not absolute
    # delta (would be a separate R13 candidate requiring a future
    # slice extension).
    idp = slice_.integrated_drag_pct
    if idp is None:
        return None
    if idp.station_pct is None:
        return None

    # Codex CRS R0 P3 R1 fix: NASA gate convention is `<=` not `<`. The
    # source gate in `flat_plate_cf.py` uses `station_rel <= tolerance`
    # so a slice with station_pct == 10.0 is IN tolerance (PASSES). The
    # previous strict `<` falsely flagged exact-boundary slices as
    # PASS/FAIL XOR even when both metrics were canonically in
    # tolerance. R10 shares the same boundary (now imported from the
    # module-level `_NASA_TOL_PCT` so the literal cannot drift
    # between R10 and R12).
    integrated_passes = bool(idp.within_tolerance)
    station_passes = idp.station_pct <= _NASA_TOL_PCT

    # XOR — exactly one metric passes.
    if integrated_passes == station_passes:
        return None

    return MatchSite(
        matched_at=(
            f"integrated_drag_{js_to_fixed(idp.pct, 2)}pct_"
            f"vs_station_{js_to_fixed(idp.station_pct, 2)}pct"
        )
    )


def _pred_residual_divergence(slice_: RunArtifactSlice) -> Optional[MatchSite]:
    # Divergence (blow-up): the p residual climbing monotonically AND crossing
    # O(1). OpenFOAM residuals are normalized (initial ~1.0, converging ones
    # fall to <<1), so a residual that increases past 1.0 is unambiguously
    # diverging — distinct from R1 (oscillation), R7 (plateau), R2 (max-iters)
    # and R3 (nonzero-exit crash; divergence can occur WITHOUT a crash, e.g. a
    # run that hits maxIters with climbing residuals or whose blow-up is mid-
    # flight).
    #
    # Window: opportunistic up to 4 samples — fires as soon as ≥2 consecutive
    # samples exist and the pattern holds. Cadence Codex review 2026-05-29
    # (CRS gpt-5.4 high) caught that the prior strict-4 requirement missed the
    # V3-class fast blow-up the rule's own docstring claimed to cover (V3 iter-3
    # = 3 samples; the strict-4 rule never fired on its own target). Relaxed to
    # ≥2 + monotonic + final>1.0. The >1.0 floor keeps an early transient bump
    # in an otherwise-converging run from false-firing — same guard.
    #
    # KNOWN-GAP (honest scope-out): V6 first-iter mass-flow-zero-IC blow-up
    # produces only 1 residual sample. A single residual at O(1) cannot be
    # distinguished from a normal startup transient without a much higher
    # single-sample threshold that would shadow the >1.0 floor's false-positive
    # guard for typical first-iter values. R3 (nonzero-exit) catches V6 when
    # the case dies; if V6 leaves a clean exit with no recovery, that gap is
    # tracked for a future slice-extension rule (see retro 2026-05-29
    # cadence_codex_r1).
    #
    # Provenance: V3 / V7 + Ferziger & Perić §8.7 (V6 is the known-gap above).
    if slice_.residuals is None:
        return None
    p_history = slice_.residuals.get("p")
    if p_history is None:
        return None
    recent = list(p_history[-4:])  # opportunistic — take what's available
    if len(recent) < 2:
        return None
    if not _is_monotonically_increasing(recent):
        return None
    if recent[-1] <= 1.0:
        return None
    final_iter = (
        slice_.convergence_stats.final_iter
        if slice_.convergence_stats is not None
        else len(recent)
    )
    return MatchSite(matched_at=f"iter_{final_iter}_p_divergence")


_PREDICATES_BY_ID: Dict[str, Callable[[RunArtifactSlice], Optional[MatchSite]]] = {
    "RESIDUAL_OSCILLATION_P_V9_R1": _pred_residual_oscillation_p,
    "MAX_ITERS_REACHED_V9_R2": _pred_max_iters_reached,
    "RUN_FAILED_NONZERO_EXIT_V9_R3": _pred_run_failed_nonzero_exit,
    "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4": _pred_gold_delta_exceeds_5_pct,
    "FORCES_NOT_CONVERGED_V9_R5": _pred_forces_not_converged,
    "SLOW_CONVERGENCE_V9_R6": _pred_slow_convergence,
    "RESIDUAL_PLATEAU_U_V9_R7": _pred_residual_plateau_u,
    "HEALTHY_CONVERGENCE_V9_R8": _pred_healthy_convergence,
    "RESIDUAL_DIVERGENCE_V9_R9": _pred_residual_divergence,
    "KNOWN_DEVIATION_PATTERN_NEAR_LE_V9_R10": _pred_known_deviation_pattern_near_le,
    "DEVELOPED_REGION_SHAPE_MISMATCH_V9_R11": _pred_developed_region_shape_mismatch,
    "INTEGRATED_VS_STATION_DRAG_DISCREPANCY_V9_R12": _pred_integrated_vs_station_discrepancy,
}


# ---------------------------------------------------------------------------
# Rule loader — joins JSON SSOT data with predicates
# ---------------------------------------------------------------------------

def _load_corpus() -> Tuple[str, List[AdvisorRule]]:
    text = _JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(text)
    version = data["version"]
    rules: List[AdvisorRule] = []
    for r in data["rules"]:
        pid = r["id"]
        predicate = _PREDICATES_BY_ID.get(pid)
        if predicate is None:
            raise RuntimeError(
                f"V91.1 join error: JSON rule id {pid!r} has no matching Python predicate"
            )
        if not r["provenance"]:
            raise RuntimeError(f"V90 RS#32: rule {pid!r} has empty provenance")
        rules.append(
            AdvisorRule(
                id=pid,
                severity=r["severity"],
                commentary=r["commentary"],
                provenance=r["provenance"],
                predicate=predicate,
            )
        )
    return version, rules


V9_RULESET_VERSION, V9_ADVISOR_RULES = _load_corpus()
