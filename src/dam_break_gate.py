"""P4 V72.A · VOF dam-break gate (``dam_break_collapse``, Control Plane).

Two-tier oracle for the collapsing-water-column anchor (Martin & Moyce 1952
n^2=2 geometry, OpenFOAM-tutorial column a=0.1461 m without the obstacle).

Tier 1 — SANITY gates (closed-form, re-derived in tests, ALWAYS enforced)
-------------------------------------------------------------------------
  G0 initial column intact   |Z(T=0) - 1| <= 0.1 (wrong setFields init dies here)
  G1 Ritter strict bound     Z(T) < 2T for every sampled T > 0
                             (Ritter 1892 dry-bed front x = 2 t sqrt(g h0);
                             in Martin & Moyce variables Z_Ritter(T) = 2T exactly,
                             for ANY aspect ratio — derivation in the gold header.
                             Experiment runs ~15% slower, so this is a one-sided
                             upper bound ONLY, never a band target.)
  G2 monotone collapse       Z strictly increases across all sampled times
  G3 collapse floor          Z(T_last) > 1.5 (an unrun/frozen case sits at Z = 1.0;
                             anti-tautology — kills "didn't run, still passed")
  G4 volume conservation     max pairwise drift of sum(alpha*V) <= 1% (MULES)
  G5 alpha boundedness       -1e-6 <= alpha <= 1 + 1e-6 globally

A tier-1 pass is reported as **SANITY-PASS** — kinematic plausibility +
conservation + boundedness. It is NOT experimental validation and NOT
runnable-coverage evidence (loop-auditor V72.A F3: verdict naming capped; F4:
tier 1 carries no run-provenance — a fabricated conservation-satisfying field
could pass tier 1; the live-run provenance is established by the V72.B/C
evidence chain, not by this gate).

Tier 2 — Martin & Moyce experimental band (consumer-side enforced, F2 pins)
---------------------------------------------------------------------------
The gold's tier-2 anchor is consumed ONLY when ALL of:
  (a) ``anchor_verification == "VERIFIED"`` — any other value, including a
      missing field or a typo, is treated as NOT verified (enum fail-closed);
  (b) a non-empty ``provenance`` block exists (primary/secondary source +
      digitization detail) — VERIFIED without provenance is refused;
  (c) every candidate has a non-null Z and passes the ANCHOR META-GATE
      ``Z * (1 + tol) < 2T`` — an anchor whose band crosses its own Ritter
      bound is physically impossible and marks the gold corrupt
      (loop-auditor V72.A F1: the candidate Z~2.0@T=1.0 that motivated this
      meta-gate violated the bound — a time-normalization convention clash).
Otherwise tier 2 reports PROVISIONAL (or REJECTED_ANCHOR for (c)) and
``coverage_eligible`` is False: this verdict can NEVER flip runnable-coverage.

ADR-001 plane assignment: **Control Plane** (imports the Execution-plane
extractor; thresholds live here + in the gold, never in the extractor).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .dam_break_extractor import (
    DamBreakExtractionError,
    DamBreakMetrics,
    extract_dam_break,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = _REPO_ROOT / "knowledge" / "gold_standards" / "dam_break_collapse.yaml"

# --- tier-1 thresholds (documented in the gold header; SSOT here) -----------
_INITIAL_COLUMN_TOL: float = 0.10   # G0: |Z(0) - 1| tolerance (half-cell bias)
_COLLAPSE_FLOOR_Z: float = 1.5      # G3: Z(T_last) must exceed this
_VOLUME_DRIFT_MAX: float = 0.01     # G4: max relative pairwise volume drift
_ALPHA_BOUND_TOL: float = 1.0e-6    # G5: numerical over/undershoot allowance
_FLOOR_BAND_FRAC: float = 0.10      # front measured in band y <= 0.1 * a
_MIN_WET_CELLS: int = 3             # F6 splash guard (extractor enforces)

_TIER2_VERIFIED = "VERIFIED"        # the ONLY status that enables enforcement


class DamBreakGoldError(ValueError):
    """Raised when the gold standard itself is malformed (fail-closed BLOCK)."""


@dataclass(frozen=True)
class DamBreakGateResult:
    """Outcome of gating a dam-break case. tier-1 PASS == SANITY only."""

    sanity_passed: bool                 # ALL of G0..G5
    initial_column_ok: bool             # G0
    ritter_bound_ok: bool               # G1
    monotone_ok: bool                   # G2
    collapse_floor_ok: bool             # G3
    volume_conservation_ok: bool        # G4
    alpha_bounded_ok: bool              # G5
    tier2_mode: str                     # ENFORCED | PROVISIONAL | REJECTED_ANCHOR
    tier2_passed: Optional[bool]        # None unless ENFORCED
    coverage_eligible: bool             # sanity AND tier2 ENFORCED AND tier2 pass
    z_by_T: Dict[float, float]          # measured Z keyed by dimensionless T
    metrics: DamBreakMetrics
    summary: str


# --------------------------------------------------------------------------
# Gold loading + derivations (closed-form, re-derived in tests)
# --------------------------------------------------------------------------

def _load_gold(gold_path: Path) -> Dict[str, Any]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise DamBreakGoldError(f"empty / unparseable gold standard: {gold_path}")
    for doc in docs:
        if doc.get("quantity") == "surge_front_position":
            return doc
    raise DamBreakGoldError(
        f"no surge_front_position document in {gold_path} (fail-closed)"
    )


def derive_sample_time(T: float, a: float, g: float) -> float:
    """t = T * sqrt(a / (2 g)) — inverse of Martin & Moyce T = n t sqrt(g/a), n^2=2."""
    return T * math.sqrt(a / (2.0 * g))


def ritter_bound(T: float) -> float:
    """Ritter front in M&M variables: Z_Ritter(T) = 2T (any aspect ratio)."""
    return 2.0 * T


def _geometry(doc: Dict[str, Any]) -> Tuple[float, float, List[float]]:
    geo = doc.get("case_info", {}).get("geometry", {})
    try:
        a = float(geo["column_width_a_m"])
        h0 = float(geo["column_height_m"])
        g = float(geo["gravity_m_s2"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DamBreakGoldError(f"gold geometry block malformed: {exc}") from exc
    if not math.isclose(h0 / a, 2.0, rel_tol=1e-6):
        raise DamBreakGoldError(
            f"gold aspect ratio h0/a = {h0 / a:.6f} != 2 — the Martin & Moyce n^2=2 "
            f"variables and the T<->t conversion in this gate assume n^2=2 exactly"
        )
    sample_T = doc.get("sample_T")
    if not isinstance(sample_T, list) or not sample_T or 0.0 not in sample_T:
        raise DamBreakGoldError(
            "gold sample_T must be a list containing T=0.0 (G0 needs the initial field)"
        )
    return a, g, [float(T) for T in sample_T]


# --------------------------------------------------------------------------
# Tier-2 consumption rules (loop-auditor F2: three pins, fail-closed)
# --------------------------------------------------------------------------

def _tier2_mode(doc: Dict[str, Any], tolerance: float) -> Tuple[str, List[str]]:
    notes: List[str] = []
    tier2 = doc.get("tier2_anchor") or {}
    status = tier2.get("anchor_verification")
    if status != _TIER2_VERIFIED:
        notes.append(
            f"tier-2 anchor_verification={status!r} != 'VERIFIED' -> PROVISIONAL "
            f"(enum fail-closed: missing/typo/new values all refuse enforcement)"
        )
        return "PROVISIONAL", notes
    provenance = tier2.get("provenance")
    if not isinstance(provenance, dict) or not provenance.get("source") or not provenance.get("digitization"):
        notes.append(
            "tier-2 VERIFIED but provenance block missing/empty -> PROVISIONAL "
            "(VERIFIED without provenance is refused; F2 pin 3)"
        )
        return "PROVISIONAL", notes
    candidates = tier2.get("candidates") or []
    if not candidates:
        notes.append("tier-2 VERIFIED but no candidates -> PROVISIONAL")
        return "PROVISIONAL", notes
    for cand in candidates:
        T, Z = cand.get("T"), cand.get("Z")
        if T is None or Z is None:
            notes.append(f"tier-2 candidate {cand!r} has null T/Z -> PROVISIONAL")
            return "PROVISIONAL", notes
        if float(Z) * (1.0 + tolerance) >= ritter_bound(float(T)):
            notes.append(
                f"ANCHOR META-GATE: candidate Z={Z}@T={T} with tol={tolerance} "
                f"crosses its own Ritter bound 2T={ritter_bound(float(T))} -> "
                f"REJECTED_ANCHOR (gold corrupt; loop-auditor F1)"
            )
            return "REJECTED_ANCHOR", notes
    return "ENFORCED", notes


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------

def gate_dam_break_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> DamBreakGateResult:
    """Run the dam_break_collapse gate (fail-closed).

    Any extraction failure propagates as ``DamBreakExtractionError`` (an honest
    BLOCK upstream); a malformed gold raises ``DamBreakGoldError`` — never a
    fabricated verdict.
    """
    doc = _load_gold(Path(gold_path))
    tolerance = float(doc.get("tolerance", 0.10))
    a, g, sample_T = _geometry(doc)
    times = [derive_sample_time(T, a, g) for T in sample_T]

    metrics = extract_dam_break(
        Path(case_dir),
        sample_times=times,
        column_width_a=a,
        floor_band_y=_FLOOR_BAND_FRAC * a,
        min_wet_cells=_MIN_WET_CELLS,
    )
    # map measured snapshots back to dimensionless T (same order, both sorted)
    pairs = sorted(zip(sorted(sample_T), metrics.snapshots), key=lambda p: p[0])
    z_by_T = {T: snap.z_front for T, snap in pairs}
    positive_T = [T for T in z_by_T if T > 0.0]

    # --- tier-1 sanity gates -------------------------------------------------
    initial_column_ok = abs(z_by_T[0.0] - 1.0) <= _INITIAL_COLUMN_TOL
    ritter_bound_ok = all(z_by_T[T] < ritter_bound(T) for T in positive_T)
    zs_in_time_order = [snap.z_front for _, snap in pairs]
    monotone_ok = all(b > a_ for a_, b in zip(zs_in_time_order, zs_in_time_order[1:]))
    collapse_floor_ok = z_by_T[max(positive_T)] > _COLLAPSE_FLOOR_Z
    volumes = [snap.water_volume for _, snap in pairs]
    vmax, vmin = max(volumes), min(volumes)
    volume_conservation_ok = vmax > 0 and (vmax - vmin) / vmax <= _VOLUME_DRIFT_MAX
    alpha_bounded_ok = all(
        snap.alpha_min >= -_ALPHA_BOUND_TOL and snap.alpha_max <= 1.0 + _ALPHA_BOUND_TOL
        for _, snap in pairs
    )
    sanity_passed = (
        initial_column_ok and ritter_bound_ok and monotone_ok
        and collapse_floor_ok and volume_conservation_ok and alpha_bounded_ok
    )

    # --- tier-2 (consumer-side enforced) --------------------------------------
    tier2_mode, tier2_notes = _tier2_mode(doc, tolerance)
    tier2_passed: Optional[bool] = None
    if tier2_mode == "ENFORCED":
        checks = []
        for cand in doc["tier2_anchor"]["candidates"]:
            T, Z_ref = float(cand["T"]), float(cand["Z"])
            if T not in z_by_T:
                raise DamBreakGoldError(
                    f"tier-2 candidate T={T} not in sample_T {sample_T} (gold inconsistent)"
                )
            checks.append(abs(z_by_T[T] - Z_ref) / Z_ref <= tolerance)
        tier2_passed = all(checks)

    coverage_eligible = bool(sanity_passed and tier2_mode == "ENFORCED" and tier2_passed)

    gate_parts = [
        f"initial_column={'PASS' if initial_column_ok else 'FAIL'}",
        f"ritter_bound={'PASS' if ritter_bound_ok else 'FAIL'}",
        f"monotone={'PASS' if monotone_ok else 'FAIL'}",
        f"collapse_floor={'PASS' if collapse_floor_ok else 'FAIL'}",
        f"volume_conservation={'PASS' if volume_conservation_ok else 'FAIL'}",
        f"alpha_bounded={'PASS' if alpha_bounded_ok else 'FAIL'}",
    ]
    z_str = ", ".join(f"Z(T={T:g})={z_by_T[T]:.4f}" for T in sorted(z_by_T))
    summary = (
        f"dam_break_collapse tier-1 {'SANITY-PASS' if sanity_passed else 'SANITY-FAIL'} "
        f"({z_str}) | " + ", ".join(gate_parts)
        + f" | tier-2 {tier2_mode}"
        + (f" {'PASS' if tier2_passed else 'FAIL'}" if tier2_passed is not None else "")
        + f" | coverage_eligible={coverage_eligible}"
        + (" | " + " ; ".join(tier2_notes) if tier2_notes else "")
    )
    return DamBreakGateResult(
        sanity_passed=sanity_passed,
        initial_column_ok=initial_column_ok,
        ritter_bound_ok=ritter_bound_ok,
        monotone_ok=monotone_ok,
        collapse_floor_ok=collapse_floor_ok,
        volume_conservation_ok=volume_conservation_ok,
        alpha_bounded_ok=alpha_bounded_ok,
        tier2_mode=tier2_mode,
        tier2_passed=tier2_passed,
        coverage_eligible=coverage_eligible,
        z_by_T=z_by_T,
        metrics=metrics,
        summary=summary,
    )
