"""P4 V73.A · transonic airfoil SBLI gate (``rae2822_case9``, Control Plane).

Two-tier oracle for the RAE 2822 Case 9 transonic anchor (M=0.734, alpha=2.79
deg corrected, Re_c=6.5e6 — AGARD AR-138; civil-aircraft cruise aerodynamics).

Tier 1 — SANITY gates (closed-form, re-derived in tests, ALWAYS enforced)
-------------------------------------------------------------------------
  C0a freestream Mach     three-way: |M_meas - M_decl| <= atol AND
                          |M_meas - M_gold| <= atol. M_meas comes from an
                          upstream PROBE of the SOLVED field — a doctored 0/
                          file alone cannot satisfy this (loop-auditor F1;
                          wedge-gate measured-freestream precedent).
  C0b incidence           |alpha_meas - alpha_gold| <= atol_deg AND
                          |alpha_meas - alpha_decl| <= atol_deg
  C0c Reynolds (rough)    |Re_decl - Re_gold| / Re_gold <= rtol, with
                          Re_decl = rho_inf |U| c / mu(T_inf) from the case's
                          own transport dict (catches a wrong-fluid setup)
  C1  stagnation          1.0 <= max Cp <= Cp_stag(M_meas) + margin
                          (isentropic pitot ceiling; Cp_stag(0.734) ~ 1.142)
  (no vacuum-floor gate: with the measured-freestream normalization,
   p_inf/q_inf == 2/(gamma M^2) is an algebraic identity, so
   Cp >= Cp_vacuum <=> p_abs >= 0 — ALREADY enforced fail-closed by the
   extractor's positive-absolute-pressure check. A gate that cannot
   independently fire is a tautology gate; cp_vacuum() is kept as a
   documented closed form only.)
  C3  supersonic pocket   min Cp_upper < Cp*(M_meas) ~ -0.647 — Case 9 is
                          ABOVE shock-formation threshold; an attached
                          fully-subcritical solution is the wrong flow
  C4  shock position      detector fired (plateau/jump/crossing guards, F3)
                          AND x/c in (0.2, 0.9)
  C5  force ranges        0 < Cl < 2 ; 0 < Cd < 0.1
  C6  Cl cross-check      |Cl_p - Cl_fc| / Cl_fc <= rtol, Cl_p independently
                          contour-integrated from the surface Cp (F2: the
                          solver's forceCoeffs FO is never trusted alone)

A tier-1 pass is reported as **SANITY-PASS** — gas-dynamic plausibility only.
It is NOT experimental validation, NOT runnable-coverage evidence, and tier 1
carries no run-provenance (V72.A F3/F4 inheritance; live-run provenance is
the V73.B/C evidence chain's job).

Tier 2 — AGARD AR-138 experimental anchor (role-aware, consumer-side enforced)
------------------------------------------------------------------------------
Candidates are keyed by QoI with an explicit role:
  ENFORCED  cl (band rel_tol), shock_xc (band atol)  — the judged set
  ADVISORY  cd — viscous-drag credibility differs by turbulence model;
            compared + reported, NEVER part of tier2_passed (loop-auditor F5)
  (Cp(x/c) profile band: PROFILE-PENDING — future QoI, not judged here)
The anchor is consumed ONLY when ALL of: status enum == "VERIFIED"
(fail-closed on anything else) + non-empty provenance + every candidate value
non-null + ANCHOR META-GATE (each candidate's full tolerance band must lie
inside its own tier-1 sanity range — an anchor outside the physics it is
supposed to certify marks the gold corrupt) + the ENFORCED role set exactly
== {cl, shock_xc} (role completeness pin: gold alone can neither shrink nor
grow the judged set without a code change).

COVERAGE HONESTY (this anchor is BREADTH, not a new compute type)
-----------------------------------------------------------------
kOmegaSST COMP-STEADY is already runnable-covered (wedge V71 arc). V73 adds
transonic-SBLI depth on that covered cell — closing capability-matrix §6
gap#2 ("just below shock-formation threshold") — so this gate exposes
``coverage_impact`` (always the explanatory string, never a boolean) and NO
coverage_eligible field: nothing downstream can flip runnable-coverage 3 -> 4
off this verdict.

ADR-001 plane assignment: **Control Plane** (imports the Execution-plane
extractor; thresholds live here + in the gold, never in the extractor).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .transonic_airfoil_extractor import (
    TransonicAirfoilMetrics,
    TransonicExtractionError,
    extract_transonic_airfoil,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_GOLD = _REPO_ROOT / "knowledge" / "gold_standards" / "rae2822_case9.yaml"

_TIER2_VERIFIED = "VERIFIED"          # the ONLY status that enables enforcement
_ENFORCED_QOI_SET = {"cl", "shock_xc"}  # role completeness pin (F5)

COVERAGE_IMPACT = (
    "none — breadth anchor: transonic-SBLI depth on the already-covered "
    "kOmegaSST COMP-STEADY cell (wedge V71); runnable-coverage stays 3"
)


class TransonicGoldError(ValueError):
    """Raised when the gold standard itself is malformed (fail-closed BLOCK)."""


@dataclass(frozen=True)
class TransonicGateResult:
    """Outcome of gating a transonic-airfoil case. tier-1 PASS == SANITY only."""

    sanity_passed: bool                 # ALL of C0a..C6 (no C2 — see docstring)
    freestream_mach_ok: bool            # C0a
    alpha_ok: bool                      # C0b
    reynolds_ok: bool                   # C0c
    stagnation_ok: bool                 # C1
    supersonic_pocket_ok: bool          # C3
    shock_ok: bool                      # C4
    ranges_ok: bool                     # C5
    cl_crosscheck_ok: bool              # C6
    tier2_mode: str                     # ENFORCED | PROVISIONAL | REJECTED_ANCHOR
    tier2_passed: Optional[bool]        # None unless ENFORCED; ENFORCED QoIs only
    coverage_impact: str                # always COVERAGE_IMPACT (breadth honesty)
    metrics: TransonicAirfoilMetrics
    summary: str


# --------------------------------------------------------------------------
# Closed forms (re-derived in tests against hand values)
# --------------------------------------------------------------------------

def cp_stagnation(mach: float, gamma: float = 1.4) -> float:
    """Isentropic stagnation Cp: 2/(g M^2) [(1 + (g-1)/2 M^2)^(g/(g-1)) - 1]."""
    m2 = mach * mach
    return (2.0 / (gamma * m2)) * (
        (1.0 + 0.5 * (gamma - 1.0) * m2) ** (gamma / (gamma - 1.0)) - 1.0
    )


def cp_critical(mach: float, gamma: float = 1.4) -> float:
    """Cp* (sonic): 2/(g M^2) [((2 + (g-1) M^2)/(g+1))^(g/(g-1)) - 1]."""
    m2 = mach * mach
    return (2.0 / (gamma * m2)) * (
        ((2.0 + (gamma - 1.0) * m2) / (gamma + 1.0)) ** (gamma / (gamma - 1.0)) - 1.0
    )


def cp_vacuum(mach: float, gamma: float = 1.4) -> float:
    """Vacuum-pressure floor: Cp = -2/(g M^2) at p -> 0 absolute."""
    return -2.0 / (gamma * mach * mach)


# --------------------------------------------------------------------------
# Gold loading (fail-closed)
# --------------------------------------------------------------------------

def _load_gold(gold_path: Path) -> Dict[str, Any]:
    docs = [d for d in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")) if d]
    if not docs:
        raise TransonicGoldError(f"empty / unparseable gold standard: {gold_path}")
    for doc in docs:
        if doc.get("quantity") == "transonic_airfoil_sbli":
            return doc
    raise TransonicGoldError(
        f"no transonic_airfoil_sbli document in {gold_path} (fail-closed)"
    )


def _operating_point(doc: Dict[str, Any]) -> Dict[str, float]:
    op = doc.get("operating_point") or {}
    try:
        return {
            "mach": float(op["mach"]),
            "alpha_deg": float(op["alpha_deg"]),
            "reynolds": float(op["reynolds"]),
            "chord_m": float(op["chord_m"]),
            "gamma": float(op["gamma"]),
            "r_specific": float(op["r_specific_J_kgK"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise TransonicGoldError(f"gold operating_point malformed: {exc}") from exc


def _tolerances(doc: Dict[str, Any]) -> Dict[str, Any]:
    tol = doc.get("tolerances") or {}
    try:
        out = {
            "mach_atol": float(tol["mach_atol"]),
            "alpha_atol_deg": float(tol["alpha_atol_deg"]),
            "reynolds_rtol": float(tol["reynolds_rtol"]),
            "stagnation_margin": float(tol["stagnation_margin"]),
            "shock_band": [float(v) for v in tol["shock_band"]],
            "cl_range": [float(v) for v in tol["cl_range"]],
            "cd_range": [float(v) for v in tol["cd_range"]],
            "cl_crosscheck_rtol": float(tol["cl_crosscheck_rtol"]),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise TransonicGoldError(f"gold tolerances malformed: {exc}") from exc
    if len(out["shock_band"]) != 2 or not out["shock_band"][0] < out["shock_band"][1]:
        raise TransonicGoldError(f"gold shock_band malformed: {out['shock_band']}")
    return out


# --------------------------------------------------------------------------
# Tier-2 consumption rules (V72.A triad, role-aware per loop-auditor F5)
# --------------------------------------------------------------------------

def _candidate_meta_gate(qoi: str, value: float, band: float, is_rel: bool,
                         tol: Dict[str, Any]) -> Optional[str]:
    """Return a corruption note if a candidate's tolerance band escapes its
    own tier-1 sanity range (ANCHOR META-GATE), else None."""
    lo_band = value * (1.0 - band) if is_rel else value - band
    hi_band = value * (1.0 + band) if is_rel else value + band
    sanity = {
        "cl": tol["cl_range"],
        "cd": tol["cd_range"],
        "shock_xc": tol["shock_band"],
    }.get(qoi)
    if sanity is None:
        return f"unknown tier-2 QoI {qoi!r}"
    lo, hi = sanity
    if not (lo < lo_band and hi_band < hi):
        return (
            f"candidate {qoi}={value} band [{lo_band:.4g}, {hi_band:.4g}] escapes "
            f"its tier-1 sanity range ({lo}, {hi})"
        )
    return None


def _tier2_mode(doc: Dict[str, Any], tol: Dict[str, Any]) -> Tuple[str, List[str]]:
    notes: List[str] = []
    tier2 = doc.get("tier2_anchor") or {}
    candidates = tier2.get("candidates") or []

    # role completeness pin runs FIRST — a gold that tries to enforce a
    # different QoI set is corrupt regardless of verification status (F5)
    roles = {c.get("qoi"): c.get("role") for c in candidates}
    enforced = {q for q, r in roles.items() if r == "ENFORCED"}
    if candidates and enforced != _ENFORCED_QOI_SET:
        raise TransonicGoldError(
            f"tier-2 ENFORCED role set {sorted(enforced)} != required "
            f"{sorted(_ENFORCED_QOI_SET)} — the judged set is pinned in code "
            f"(role completeness pin); a gold cannot grow/shrink it alone"
        )

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
            "(VERIFIED without provenance is refused)"
        )
        return "PROVISIONAL", notes
    if not candidates:
        notes.append("tier-2 VERIFIED but no candidates -> PROVISIONAL")
        return "PROVISIONAL", notes
    for cand in candidates:
        qoi, value = cand.get("qoi"), cand.get("value")
        if qoi is None or value is None:
            notes.append(f"tier-2 candidate {cand!r} has null qoi/value -> PROVISIONAL")
            return "PROVISIONAL", notes
        is_rel = "rel_tol" in cand
        band = float(cand.get("rel_tol") if is_rel else cand.get("atol", 0.0))
        if band <= 0:
            notes.append(f"tier-2 candidate {qoi} has no positive tolerance -> PROVISIONAL")
            return "PROVISIONAL", notes
        corrupt = _candidate_meta_gate(qoi, float(value), band, is_rel, tol)
        if corrupt:
            notes.append(f"ANCHOR META-GATE: {corrupt} -> REJECTED_ANCHOR (gold corrupt)")
            return "REJECTED_ANCHOR", notes
    return "ENFORCED", notes


def _tier2_judge(metrics: TransonicAirfoilMetrics, candidates: List[Dict[str, Any]],
                 notes: List[str]) -> bool:
    measured = {
        "cl": metrics.cl_fc,
        "cd": metrics.cd_fc,
        "shock_xc": metrics.shock_xc,
    }
    enforced_ok: List[bool] = []
    for cand in candidates:
        qoi, ref = cand["qoi"], float(cand["value"])
        got = measured[qoi]
        if got is None:
            ok = False
            notes.append(f"tier-2 {qoi}: no measured value -> FAIL")
        elif "rel_tol" in cand:
            ok = abs(got - ref) / abs(ref) <= float(cand["rel_tol"])
            notes.append(f"tier-2 {qoi}: {got:.4f} vs {ref:.4f} rel_tol={cand['rel_tol']} -> {'PASS' if ok else 'FAIL'}")
        else:
            ok = abs(got - ref) <= float(cand["atol"])
            notes.append(f"tier-2 {qoi}: {got:.4f} vs {ref:.4f} atol={cand['atol']} -> {'PASS' if ok else 'FAIL'}")
        if cand["role"] == "ENFORCED":
            enforced_ok.append(ok)
        else:
            notes[-1] += " (ADVISORY — not judged)"
    return all(enforced_ok)


# --------------------------------------------------------------------------
# Gate
# --------------------------------------------------------------------------

def gate_transonic_airfoil_against_gold(
    case_dir: Path,
    gold_path: Path = _DEFAULT_GOLD,
) -> TransonicGateResult:
    """Run the rae2822_case9 gate (fail-closed).

    Any extraction failure propagates as ``TransonicExtractionError`` (an
    honest BLOCK upstream); a malformed gold raises ``TransonicGoldError`` —
    never a fabricated verdict.
    """
    doc = _load_gold(Path(gold_path))
    op = _operating_point(doc)
    tol = _tolerances(doc)

    metrics = extract_transonic_airfoil(
        Path(case_dir),
        chord=op["chord_m"],
        gamma=op["gamma"],
        r_specific=op["r_specific"],
    )
    m_meas = metrics.measured.mach
    m_decl = metrics.declared.mach

    # --- tier-1 sanity gates -------------------------------------------------
    freestream_mach_ok = (
        abs(m_meas - m_decl) <= tol["mach_atol"]
        and abs(m_meas - op["mach"]) <= tol["mach_atol"]
    )
    alpha_ok = (
        abs(metrics.measured.alpha_deg - op["alpha_deg"]) <= tol["alpha_atol_deg"]
        and abs(metrics.measured.alpha_deg - metrics.declared.alpha_deg) <= tol["alpha_atol_deg"]
    )
    reynolds_ok = (
        abs(metrics.reynolds_declared - op["reynolds"]) / op["reynolds"]
        <= tol["reynolds_rtol"]
    )
    cp_stag = cp_stagnation(m_meas, op["gamma"])
    cp_star = cp_critical(m_meas, op["gamma"])
    stagnation_ok = 1.0 <= metrics.max_cp <= cp_stag + tol["stagnation_margin"]
    supersonic_pocket_ok = metrics.min_cp_upper < cp_star
    shock_lo, shock_hi = tol["shock_band"]
    shock_ok = metrics.shock_xc is not None and shock_lo < metrics.shock_xc < shock_hi
    cl_lo, cl_hi = tol["cl_range"]
    cd_lo, cd_hi = tol["cd_range"]
    ranges_ok = cl_lo < metrics.cl_fc < cl_hi and cd_lo < metrics.cd_fc < cd_hi
    cl_crosscheck_ok = (
        metrics.cl_fc > 0
        and abs(metrics.cl_p - metrics.cl_fc) / metrics.cl_fc <= tol["cl_crosscheck_rtol"]
    )
    sanity_passed = (
        freestream_mach_ok and alpha_ok and reynolds_ok and stagnation_ok
        and supersonic_pocket_ok and shock_ok and ranges_ok and cl_crosscheck_ok
    )

    # --- tier-2 (consumer-side enforced, role-aware) --------------------------
    tier2_mode, tier2_notes = _tier2_mode(doc, tol)
    tier2_passed: Optional[bool] = None
    if tier2_mode == "ENFORCED":
        tier2_passed = _tier2_judge(
            metrics, doc["tier2_anchor"]["candidates"], tier2_notes
        )

    gate_parts = [
        f"freestream_mach={'PASS' if freestream_mach_ok else 'FAIL'}",
        f"alpha={'PASS' if alpha_ok else 'FAIL'}",
        f"reynolds={'PASS' if reynolds_ok else 'FAIL'}",
        f"stagnation={'PASS' if stagnation_ok else 'FAIL'}",
        f"supersonic_pocket={'PASS' if supersonic_pocket_ok else 'FAIL'}",
        f"shock={'PASS' if shock_ok else 'FAIL'}",
        f"ranges={'PASS' if ranges_ok else 'FAIL'}",
        f"cl_crosscheck={'PASS' if cl_crosscheck_ok else 'FAIL'}",
    ]
    shock_str = (
        f"shock_xc={metrics.shock_xc:.4f}" if metrics.shock_xc is not None
        else f"shock_xc=None ({metrics.shock_decline_reason})"
    )
    summary = (
        f"rae2822_case9 tier-1 {'SANITY-PASS' if sanity_passed else 'SANITY-FAIL'} "
        f"(M_meas={m_meas:.4f}, alpha={metrics.measured.alpha_deg:.3f}deg, "
        f"Cl_fc={metrics.cl_fc:.4f}, Cl_p={metrics.cl_p:.4f}, "
        f"Cd_fc={metrics.cd_fc:.5f}, {shock_str}, "
        f"Cp*={cp_star:.4f}, Cp_stag={cp_stag:.4f}) | "
        + ", ".join(gate_parts)
        + f" | tier-2 {tier2_mode}"
        + (f" {'PASS' if tier2_passed else 'FAIL'}" if tier2_passed is not None else "")
        + f" | coverage_impact: {COVERAGE_IMPACT}"
        + (" | " + " ; ".join(tier2_notes) if tier2_notes else "")
    )
    return TransonicGateResult(
        sanity_passed=sanity_passed,
        freestream_mach_ok=freestream_mach_ok,
        alpha_ok=alpha_ok,
        reynolds_ok=reynolds_ok,
        stagnation_ok=stagnation_ok,
        supersonic_pocket_ok=supersonic_pocket_ok,
        shock_ok=shock_ok,
        ranges_ok=ranges_ok,
        cl_crosscheck_ok=cl_crosscheck_ok,
        tier2_mode=tier2_mode,
        tier2_passed=tier2_passed,
        coverage_impact=COVERAGE_IMPACT,
        metrics=metrics,
        summary=summary,
    )
