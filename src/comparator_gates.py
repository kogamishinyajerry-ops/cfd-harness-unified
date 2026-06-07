"""DEC-V61-036b/c: Hard comparator gates G2/G3/G4/G5 — post-extraction physics gates.

Trigger FAIL on:
  * G2 CANONICAL_BAND_SHORTCUT_LAMINAR_DNS — u+/y+ values land in Moser DNS
    canonical band while the solver path is declared laminar (or turbulence
    model is not declared at all). Laminar Poiseuille physics CANNOT produce
    DNS log-law u+ values; matching values imply a unit-mismatch shortcut
    (e.g. normalizing U/U_max and relabeling as u_plus, or emitting raw
    cell-centre values through a misnamed key). DEC-V61-059 closes the
    DEC-V61-036c G2 territory marker.
  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
    with log-based epsilon proxy fallback (epsilon ~ u^3/L).
  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
    OR max > 1e+10 (sanity overflow).
  * G5 CONTINUITY_DIVERGED — last-iter sum_local > 1e-2 OR |cumulative| > 1.

Operates on artifacts already written by the audit pipeline:
  * `reports/phase5_fields/{case_id}/{ts}/log.simpleFoam` (or .pimpleFoam,
    .icoFoam, .buoyantSimpleFoam)
  * `reports/phase5_fields/{case_id}/{ts}/VTK/*.vtk` (latest time step)
  * key_quantities dict from the case extractor (G2 reads u+/y+ profile
    + turbulence_model_used scalar)

See the accompanying DEC files for ground-truth evidence and expected
gate outcomes (DEC-V61-036b for G3/G4/G5; DEC-V61-059 for G2).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def _exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    """True when value is NaN, ±inf, OR finite-and-above threshold.

    Codex DEC-036b round-1 feedback: plain `value > threshold` returns False
    for NaN, which would silently pass the worst blowup mode. NaN and +inf
    must fire the gate unconditionally.
    """
    if value is None:
        return False
    if math.isnan(value) or math.isinf(value):
        return True
    return value > threshold


def _abs_exceeds_threshold(value: Optional[float], threshold: float) -> bool:
    """|value| > threshold with NaN/Inf guard (same semantics as above)."""
    if value is None:
        return False
    if math.isnan(value) or math.isinf(value):
        return True
    return abs(value) > threshold

# ---------------------------------------------------------------------------
# Thresholds (tunable via per-case override in future; seeded from Codex
# round-1 physics audit on DEC-V61-036).
# ---------------------------------------------------------------------------

G3_VELOCITY_RATIO_MAX = 100.0     # |U|_max / U_ref
G3_EPSILON_PROXY_MAX = 1.0e10     # fallback when VTK unavailable
G4_TURBULENCE_MAX_OVERFLOW = 1.0e10  # any k/eps/omega max above this = overflow
G5_SUM_LOCAL_MAX = 1.0e-2         # incompressible steady floor
G5_CUMULATIVE_ABS_MAX = 1.0       # hard divergence floor

# G2 — case-id pattern set this gate is responsible for. Uses both legacy
# alias (`plane_channel_flow`) and canonical id
# (`fully_developed_plane_channel_flow`) per knowledge/whitelist.yaml.
G2_PLANE_CHANNEL_CASE_IDS = frozenset({
    "plane_channel_flow",
    "fully_developed_plane_channel_flow",
})

# G2 — Moser 1999 / Kim 1987 canonical (y+, u+) reference points. Matches
# the gold YAML ref bands. The detector triggers when the emitted profile
# can be linearly interpolated to within G2_CANONICAL_BAND_TOLERANCE of
# at least G2_CANONICAL_BAND_MIN_HITS of these points.
#
# Selection criterion: at least one viscous-sublayer point (y+<=10 where
# DNS u+ ≈ y+ holds asymptotically) and at least one log-law point (y+>=30
# where the (1/0.41)·ln(y+)+5.2 law holds and lifts u+ above 13). Both
# regions must match for the shortcut to qualify as DNS-imitating — a
# laminar Poiseuille curve at any single (Re_b, h) cannot satisfy both.
G2_CANONICAL_REFERENCE_POINTS = (
    (5.0, 5.4),   # viscous sublayer (Kim 1987 DNS Re_τ=180)
    (30.0, 13.5), # log-law (Moser 1999, (1/0.41)·ln(30)+5.2 = 13.49)
    (100.0, 18.3),  # near-centerline (Moser 1999 Re_τ=395 DNS)
)
G2_CANONICAL_BAND_TOLERANCE = 0.20  # 20% relative envelope; wider than gold
                                     # 5-8% so gate fires only on
                                     # CLEAR-AND-PRESENT shortcuts, not
                                     # legitimate-but-borderline RANS runs.
G2_CANONICAL_BAND_MIN_HITS = 2       # both viscous + log-law region must
                                     # match before we conclude DNS-imitation
G2_TRUSTED_TURBULENCE_MODELS = frozenset({
    # Models that COULD legitimately produce DNS-band u+ via wall-resolved
    # RANS or DNS/LES. Anything outside this set is treated as "not declared
    # turbulent" → G2 evaluates the canonical-band shortcut.
    "kOmegaSST", "komegaSST", "kOmegaSSTLM",
    "kEpsilon", "RNGkEpsilon", "realizableKE",
    "SpalartAllmaras",
    "Smagorinsky", "kEqn", "WALE", "dynamicKEqn",  # LES family
    "DNS", "dns",                                   # explicit DNS marker
})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GateViolation:
    """A single post-extraction gate FAIL.

    The fixture writer forwards these to audit_concerns[] and the
    validation_report verdict engine hard-FAILs on any violation.
    """

    gate_id: str          # "G2" | "G3" | "G4" | "G5"
    concern_type: str     # "CANONICAL_BAND_SHORTCUT_LAMINAR_DNS" | "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
    summary: str
    detail: str
    evidence: dict = field(default_factory=dict)


@dataclass
class LogStats:
    """Parsed telemetry from an OpenFOAM solver log."""

    final_continuity_sum_local: Optional[float] = None
    final_continuity_cumulative: Optional[float] = None
    # Per-field (k/epsilon/omega) last-iter bounding stats.
    bounding_last: dict[str, dict[str, float]] = field(default_factory=dict)
    # Fatal errors (FOAM FATAL, floating exception).
    fatal_detected: bool = False
    fatal_lines: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

# Codex DEC-036b round-1 feedback: token classes below must also accept
# `nan` / `inf` (case-insensitive). When OpenFOAM's floating-point output
# overflows past double range it prints `nan` or `-inf`, and if the regex
# rejected those tokens, the worst blowup mode would silently bypass the
# gates. Each token class is `[\deE+.\-]+|nan|[+\-]?inf` (case-folded).
_NUM_TOKEN = r"(?:[\deE+.\-]+|[nN][aA][nN]|[+\-]?[iI][nN][fF])"

_CONTINUITY_RE = re.compile(
    r"time step continuity errors\s*:\s*sum local\s*=\s*(" + _NUM_TOKEN + r")\s*,"
    r"\s*global\s*=\s*" + _NUM_TOKEN + r"\s*,"
    r"\s*cumulative\s*=\s*(" + _NUM_TOKEN + r")"
)

# Matches "bounding k, min: -1.23 max: 4.56 average: 0.1" — the comma+space
# between min and max varies across OF versions; regex tolerates both.
_BOUNDING_RE = re.compile(
    r"bounding\s+(k|epsilon|omega|nuTilda|nut|nuSgs)\s*,\s*"
    r"min\s*:\s*(" + _NUM_TOKEN + r")\s*,?\s*"
    r"max\s*:\s*(" + _NUM_TOKEN + r")"
)


def _parse_foam_number(tok: str) -> Optional[float]:
    """Parse a numeric token that may be `nan`, `inf`, `-inf`, or a
    regular finite float. Returns float (nan/inf allowed — callers compare
    against thresholds and NaN/Inf naturally fail any comparison, which
    is the intended "this value is catastrophically bad" signal)."""
    try:
        return float(tok)
    except (ValueError, TypeError):
        return None

# Tightened to avoid false-positive on the benign startup line
# `sigFpe : Enabling floating point exception trapping (FOAM_SIGFPE)` which
# announces FPE trapping capability, not an actual exception. The real
# fatal markers are FOAM FATAL (IO )?ERROR + stack-trace frames.
_FATAL_RE = re.compile(
    r"FOAM FATAL (IO )?ERROR|"
    r"#\d+\s+Foam::error::printStack|"
    r"^Floating point exception",
    re.MULTILINE,
)


def parse_solver_log(log_path: Path) -> LogStats:
    """Parse continuity + bounding lines + fatal markers from a solver log.

    Extracts the LAST matching occurrence of each pattern (the end-of-run
    state is what matters for gate decisions). For bounding, keeps
    per-field last-iter min/max.
    """
    stats = LogStats()
    if not log_path.is_file():
        return stats

    last_continuity: Optional[tuple[float, float]] = None
    last_bounding: dict[str, dict[str, float]] = {}
    fatal_lines: list[str] = []

    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _CONTINUITY_RE.search(line)
            if m:
                sl = _parse_foam_number(m.group(1))
                cum = _parse_foam_number(m.group(2))
                if sl is not None and cum is not None:
                    last_continuity = (sl, cum)
                continue
            m = _BOUNDING_RE.search(line)
            if m:
                field_name = m.group(1)
                field_min = _parse_foam_number(m.group(2))
                field_max = _parse_foam_number(m.group(3))
                if field_min is not None and field_max is not None:
                    last_bounding[field_name] = {
                        "min": field_min,
                        "max": field_max,
                    }
                continue
            if _FATAL_RE.search(line):
                stats.fatal_detected = True
                if len(fatal_lines) < 5:
                    fatal_lines.append(line.strip()[:240])

    if last_continuity is not None:
        stats.final_continuity_sum_local = last_continuity[0]
        stats.final_continuity_cumulative = last_continuity[1]
    stats.bounding_last = last_bounding
    stats.fatal_lines = fatal_lines
    return stats


# ---------------------------------------------------------------------------
# VTK velocity magnitude
# ---------------------------------------------------------------------------

def read_final_velocity_max(vtk_dir: Path) -> Optional[float]:
    """Return the max |U| across all cells in the latest internal-field VTK.

    Uses pyvista when available. Returns None when VTK unavailable,
    unreadable, or pyvista is not installed — caller treats None as
    "skip G3 VTK branch, use log-epsilon proxy instead".
    """
    if not vtk_dir.is_dir():
        return None
    try:
        import numpy as np
        import pyvista as pv
    except ImportError:
        return None

    latest_internal: list[tuple[int, str, Path]] = []
    for vtk_path in vtk_dir.rglob("*.vtk"):
        if "allPatches" in vtk_path.parts:
            continue
        match = re.search(r"_(\d+)\.vtk$", vtk_path.name)
        if match is None:
            continue
        latest_internal.append((int(match.group(1)), str(vtk_path), vtk_path))

    if not latest_internal:
        return None

    latest_internal.sort(key=lambda item: (item[0], item[1]))
    vtk_path = latest_internal[-1][2]

    try:
        mesh = pv.read(str(vtk_path))
    except Exception:
        return None

    # Look for a vector field named U or velocity.
    point_fields = set(mesh.point_data.keys()) if hasattr(mesh, "point_data") else set()
    cell_fields = set(mesh.cell_data.keys()) if hasattr(mesh, "cell_data") else set()
    U_array = None
    for field_name in ("U", "velocity", "u"):
        if field_name in point_fields:
            U_array = np.asarray(mesh.point_data[field_name])
            break
        if field_name in cell_fields:
            U_array = np.asarray(mesh.cell_data[field_name])
            break
    if U_array is None or U_array.size == 0:
        return None
    # U is typically (N, 3); compute per-cell magnitude.
    if U_array.ndim == 2 and U_array.shape[1] >= 3:
        mags = np.linalg.norm(U_array[:, :3], axis=1)
    else:
        mags = np.abs(U_array.ravel())
    if mags.size == 0:
        return None
    return float(np.nanmax(mags))


# ---------------------------------------------------------------------------
# G2 — canonical-band shortcut detector (DEC-V61-059 / DEC-V61-036c closeout)
# ---------------------------------------------------------------------------

def _interp_uplus_at_yplus(
    y_plus_axis: list[float],
    u_plus_values: list[float],
    target_y_plus: float,
) -> Optional[float]:
    """Linearly interpolate u+(y+) at the target y+. Returns None when
    target is out of range or inputs are malformed.
    """
    if not y_plus_axis or not u_plus_values:
        return None
    if len(y_plus_axis) != len(u_plus_values):
        return None
    pairs = sorted(
        (yp, up)
        for yp, up in zip(y_plus_axis, u_plus_values)
        if isinstance(yp, (int, float))
        and isinstance(up, (int, float))
        and not (math.isnan(yp) or math.isnan(up))
    )
    if not pairs:
        return None
    if target_y_plus < pairs[0][0] or target_y_plus > pairs[-1][0]:
        return None
    for i in range(len(pairs) - 1):
        y0, u0 = pairs[i]
        y1, u1 = pairs[i + 1]
        if y0 <= target_y_plus <= y1:
            if y1 == y0:
                return u0
            t = (target_y_plus - y0) / (y1 - y0)
            return u0 + t * (u1 - u0)
    return None


def _check_g2_canonical_band_shortcut(
    case_id: Optional[str],
    key_quantities: Optional[dict[str, Any]],
) -> list[GateViolation]:
    """G2: u+/y+ canonical-band shortcut detector for plane channel.

    DEC-V61-059 closes the DEC-V61-036c G2 territory marker. The earlier
    DEC widened ResultComparator to read u_plus/y_plus from gold-side
    dicts; this gate adds the missing defense-in-depth check on the
    extracted side: when a plane-channel case emits u+ values that
    interpolate to the Moser/Kim DNS canonical band AT BOTH the viscous
    sublayer (y+≈5) AND the log-law region (y+≥30), AND the run is
    declared laminar (or no turbulence model is declared at all),
    fire a hard FAIL with concern_type=CANONICAL_BAND_SHORTCUT_LAMINAR_DNS.

    Why two-region match: laminar Poiseuille has u_centerline = 1.5 U_b
    and u_tau = sqrt(3 ν U_b / h); the resulting u+ at log-law y+ is
    determined entirely by Re_b and cannot simultaneously match DNS
    u+ at y+=5 (≈5.4) and DNS u+ at y+=30 (≈13.5) for any single
    Re_b. So a two-region hit is non-physical for laminar physics
    and necessarily implies the emitter is doing unit-mismatch work.

    Skips silently (returns []) when:
      - case_id not in G2_PLANE_CHANNEL_CASE_IDS (gate is case-scoped)
      - key_quantities is None (no extraction happened — G1 will catch)
      - u_plus / y_plus profile data is absent (G1 territory)
      - turbulence model is in G2_TRUSTED_TURBULENCE_MODELS (legitimate
        wall-resolved RANS or DNS — DNS-band match is honest)

    Reads:
      - key_quantities["u_mean_profile"] : list[float] — u+ profile
      - key_quantities["u_mean_profile_y_plus"] OR ["y_plus"] : list[float]
      - key_quantities["turbulence_model_used"] : str (laminar |
        kOmegaSST | ...) — populated by adapter post-DEC-V61-059 Stage A.4

    ADR-001: this function lives in the Evaluation plane and reads
    artifacts already-emitted by the Execution plane via the
    key_quantities dict. NO Execution-plane imports.
    """
    violations: list[GateViolation] = []
    if not case_id or case_id not in G2_PLANE_CHANNEL_CASE_IDS:
        return violations
    if not isinstance(key_quantities, dict):
        return violations

    turbulence_model = key_quantities.get("turbulence_model_used")
    if isinstance(turbulence_model, str) and turbulence_model in G2_TRUSTED_TURBULENCE_MODELS:
        return violations  # legitimate turbulent run; canonical match is honest

    u_plus = key_quantities.get("u_mean_profile")
    y_plus = (
        key_quantities.get("u_mean_profile_y_plus")
        or key_quantities.get("y_plus")
    )
    if not isinstance(u_plus, list) or not isinstance(y_plus, list):
        return violations  # G1 will surface MISSING_TARGET_QUANTITY
    if len(u_plus) < 2 or len(y_plus) < 2:
        return violations

    hits: list[tuple[float, float, float, float]] = []  # (y+, ref u+, sim u+, rel_err)
    for ref_y, ref_u in G2_CANONICAL_REFERENCE_POINTS:
        sim_u = _interp_uplus_at_yplus(y_plus, u_plus, ref_y)
        if sim_u is None:
            continue
        if abs(ref_u) < 1e-9:
            rel_err = abs(sim_u - ref_u)
        else:
            rel_err = abs(sim_u - ref_u) / abs(ref_u)
        if rel_err <= G2_CANONICAL_BAND_TOLERANCE:
            hits.append((ref_y, ref_u, sim_u, rel_err))

    if len(hits) < G2_CANONICAL_BAND_MIN_HITS:
        return violations  # not enough canonical points hit; honest miss

    # Need at least one viscous-sublayer hit AND one ACTUAL log-law-
    # region hit. Codex round-3 F5 (DEC-V61-059): the original
    # `has_loglaw = any(yp >= 30.0)` test counted the y+=100 centerline
    # reference as "log-law", which let a profile that hit only the
    # viscous (y+=5) + centerline (y+=100) anchors but MISSED the real
    # log-law band (y+≈30) trip the gate. Tighten the band so a hit
    # must land in the canonical log-law region (y+ ∈ (10, 60)) — the
    # range where (1/0.41)·ln(y+)+5.2 governs the velocity profile.
    # Centerline y+≥60 is its own asymptotic regime and cannot stand in
    # for log-law evidence.
    has_viscous = any(yp <= 10.0 for yp, *_ in hits)
    has_loglaw = any(10.0 < yp < 60.0 for yp, *_ in hits)
    if not (has_viscous and has_loglaw):
        return violations

    declared = (
        turbulence_model
        if isinstance(turbulence_model, str) and turbulence_model
        else "<not declared>"
    )
    summary = (
        f"u+/y+ matches Moser DNS at {len(hits)} canonical points "
        f"(turbulence_model={declared!r}) — laminar physics cannot "
        f"produce this; unit-mismatch shortcut suspected"
    )[:240]
    detail = (
        f"DEC-V61-059 G2 canonical-band shortcut detector fired on "
        f"case_id={case_id}. Emitted u+ profile interpolates to within "
        f"{G2_CANONICAL_BAND_TOLERANCE:.0%} of the Moser/Kim DNS canonical "
        f"reference at {len(hits)} of {len(G2_CANONICAL_REFERENCE_POINTS)} "
        f"points (viscous sublayer hit={has_viscous}, log-law region hit="
        f"{has_loglaw}), AND turbulence_model_used={declared!r} is not "
        f"in the trusted set {sorted(G2_TRUSTED_TURBULENCE_MODELS)}. "
        f"Laminar Poiseuille u+ saturates at u+_max = 1.5/u_τ where "
        f"u_τ = sqrt(3 ν U_b / h); for any single Re_b the laminar "
        f"profile cannot match DNS u+ at viscous sublayer (y+≈5) AND "
        f"log-law (y+≥30) simultaneously. A two-region match therefore "
        f"implies the emitter is doing unit-mismatch work — for "
        f"example normalizing U/U_max and relabeling as u_plus, or "
        f"emitting raw cell-centre values through a misnamed key. "
        f"Hits: {hits!r}. The PASS verdict is comparator-path artifact, "
        f"not honest physics; this gate hard-FAILs the case until the "
        f"adapter declares a turbulence-resolving solver path AND the "
        f"emitter computes u+ from a physically-realized u_τ."
    )[:2000]
    violations.append(
        GateViolation(
            gate_id="G2",
            concern_type="CANONICAL_BAND_SHORTCUT_LAMINAR_DNS",
            summary=summary,
            detail=detail,
            evidence={
                "case_id": case_id,
                "turbulence_model_used": declared,
                "hits": [
                    {
                        "y_plus": yp,
                        "u_plus_ref": uref,
                        "u_plus_sim": usim,
                        "rel_err": rel_err,
                    }
                    for yp, uref, usim, rel_err in hits
                ],
                "tolerance": G2_CANONICAL_BAND_TOLERANCE,
                "min_hits": G2_CANONICAL_BAND_MIN_HITS,
                "has_viscous": has_viscous,
                "has_loglaw": has_loglaw,
            },
        )
    )
    return violations


# ---------------------------------------------------------------------------
# Individual gate checks
# ---------------------------------------------------------------------------

def _check_g3_velocity_overflow(
    log_stats: Optional[LogStats],
    vtk_dir: Optional[Path],
    U_ref: float,
) -> list[GateViolation]:
    """G3: |U|_max > K * U_ref OR epsilon max > G3_EPSILON_PROXY_MAX."""
    violations: list[GateViolation] = []
    threshold = G3_VELOCITY_RATIO_MAX * max(U_ref, 1e-6)

    u_max: Optional[float] = None
    if vtk_dir is not None:
        u_max = read_final_velocity_max(vtk_dir)

    if u_max is not None and _exceeds_threshold(u_max, threshold):
        violations.append(
            GateViolation(
                gate_id="G3",
                concern_type="VELOCITY_OVERFLOW",
                summary=(
                    f"|U|_max={u_max:.3g} exceeds {G3_VELOCITY_RATIO_MAX:.0f}·U_ref "
                    f"({threshold:.3g})"
                )[:240],
                detail=(
                    f"DEC-V61-036b G3: reading latest-time VTK cell velocity "
                    f"found |U|_max={u_max:.6g}, which is above the "
                    f"{G3_VELOCITY_RATIO_MAX:.0f}·U_ref sanity ceiling "
                    f"({threshold:.6g}, U_ref={U_ref}). This indicates "
                    "solver divergence or runaway acceleration — the measurement "
                    "cannot be trusted regardless of whether it lies within "
                    "the gold tolerance band."
                )[:2000],
                evidence={"u_max": u_max, "U_ref": U_ref, "threshold": threshold},
            )
        )
        return violations

    # Log-epsilon proxy fallback when VTK unavailable.
    if log_stats is not None:
        eps_bound = log_stats.bounding_last.get("epsilon")
        if eps_bound is not None:
            eps_max = eps_bound.get("max")
            if _exceeds_threshold(eps_max, G3_EPSILON_PROXY_MAX):
                violations.append(
                    GateViolation(
                        gate_id="G3",
                        concern_type="VELOCITY_OVERFLOW",
                        summary=(
                            f"epsilon max={eps_max:.3g} implies "
                            f"|U|~{eps_max**(1/3):.2g} (VTK-proxy)"
                        )[:240],
                        detail=(
                            f"DEC-V61-036b G3 (VTK-unavailable fallback): "
                            f"log shows final epsilon max={eps_max:.6g}, "
                            f"above proxy threshold {G3_EPSILON_PROXY_MAX:.0g}. "
                            "Since ε~u³/L, this implies |U| is catastrophically "
                            "large. Velocity overflow flagged from log."
                        )[:2000],
                        evidence={
                            "epsilon_max": eps_max,
                            "proxy_threshold": G3_EPSILON_PROXY_MAX,
                            "inferred_u": eps_max ** (1.0 / 3.0),
                        },
                    )
                )
    return violations


def _check_g4_turbulence_negativity(
    log_stats: Optional[LogStats],
) -> list[GateViolation]:
    """G4: k/epsilon/omega min < 0 at last bounding line OR max > overflow."""
    violations: list[GateViolation] = []
    if log_stats is None:
        return violations

    for field_name, bounds in log_stats.bounding_last.items():
        f_min = bounds.get("min")
        f_max = bounds.get("max")
        # NaN → treat as "catastrophically wrong" → fire gate.
        if f_min is not None and (
            math.isnan(f_min) or math.isinf(f_min) or f_min < 0.0
        ):
            violations.append(
                GateViolation(
                    gate_id="G4",
                    concern_type="TURBULENCE_NEGATIVE",
                    summary=(
                        f"{field_name} min={f_min:.3g} is negative at last iter"
                    )[:240],
                    detail=(
                        f"DEC-V61-036b G4: final `bounding {field_name}` "
                        f"line shows min={f_min:.6g} (< 0), max={f_max}. "
                        "Turbulence fields cannot be physically negative; "
                        "this indicates solver inconsistency even if "
                        "OpenFOAM's internal bounding clipped the value "
                        "to a small positive before the next step."
                    )[:2000],
                    evidence={
                        "field": field_name,
                        "min": f_min,
                        "max": f_max,
                    },
                )
            )
            continue
        if _exceeds_threshold(f_max, G4_TURBULENCE_MAX_OVERFLOW):
            violations.append(
                GateViolation(
                    gate_id="G4",
                    concern_type="TURBULENCE_NEGATIVE",
                    summary=(
                        f"{field_name} max={f_max:.3g} overflow "
                        f"(> {G4_TURBULENCE_MAX_OVERFLOW:.0g})"
                    )[:240],
                    detail=(
                        f"DEC-V61-036b G4 (overflow branch): final `bounding "
                        f"{field_name}` shows max={f_max:.6g}, above "
                        f"{G4_TURBULENCE_MAX_OVERFLOW:.0g}. For realistic "
                        "industrial RANS cases this magnitude is non-physical; "
                        "likely a divergence signature bounded from below."
                    )[:2000],
                    evidence={
                        "field": field_name,
                        "min": f_min,
                        "max": f_max,
                        "threshold": G4_TURBULENCE_MAX_OVERFLOW,
                    },
                )
            )
    return violations


def _check_g5_continuity_divergence(
    log_stats: Optional[LogStats],
) -> list[GateViolation]:
    """G5: last-iter sum_local > 1e-2 OR |cumulative| > 1.0."""
    violations: list[GateViolation] = []
    if log_stats is None:
        return violations

    sum_local = log_stats.final_continuity_sum_local
    cumulative = log_stats.final_continuity_cumulative

    if _exceeds_threshold(sum_local, G5_SUM_LOCAL_MAX):
        violations.append(
            GateViolation(
                gate_id="G5",
                concern_type="CONTINUITY_DIVERGED",
                summary=(
                    f"continuity sum_local={sum_local:.3g} > "
                    f"{G5_SUM_LOCAL_MAX:.0e}"
                )[:240],
                detail=(
                    f"DEC-V61-036b G5: final-iteration continuity error "
                    f"sum_local={sum_local:.6g} exceeds the incompressible "
                    f"steady floor {G5_SUM_LOCAL_MAX:.0e}. SIMPLE/PISO "
                    "pressure-velocity coupling has not converged; any "
                    "extracted scalar is unreliable."
                )[:2000],
                evidence={
                    "sum_local": sum_local,
                    "cumulative": cumulative,
                    "threshold": G5_SUM_LOCAL_MAX,
                },
            )
        )
        return violations  # sum_local already FAILs; don't double-flag

    if _abs_exceeds_threshold(cumulative, G5_CUMULATIVE_ABS_MAX):
        violations.append(
            GateViolation(
                gate_id="G5",
                concern_type="CONTINUITY_DIVERGED",
                summary=(
                    f"continuity cumulative={cumulative:.3g}, "
                    f"|cum| > {G5_CUMULATIVE_ABS_MAX}"
                )[:240],
                detail=(
                    f"DEC-V61-036b G5: final-iteration cumulative continuity "
                    f"error {cumulative:.6g} exceeds sanity threshold "
                    f"{G5_CUMULATIVE_ABS_MAX}. This is hard divergence — "
                    "the solver state does not satisfy mass conservation."
                )[:2000],
                evidence={
                    "sum_local": sum_local,
                    "cumulative": cumulative,
                    "threshold": G5_CUMULATIVE_ABS_MAX,
                },
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_all_gates(
    log_path: Optional[Path] = None,
    vtk_dir: Optional[Path] = None,
    U_ref: float = 1.0,
    case_id: Optional[str] = None,
    key_quantities: Optional[dict[str, Any]] = None,
) -> list[GateViolation]:
    """Run G2 + G3 + G4 + G5 and return the aggregated list of violations.

    Called from `scripts/phase5_audit_run.py::_audit_fixture_doc` after
    G1 extraction. Each violation becomes an `audit_concerns[]` entry;
    `ui/backend/services/validation_report._derive_contract_status`
    hard-FAILs when any of the concern codes is present.

    DEC-V61-059 added G2 (canonical-band shortcut for plane channel u+/y+).
    G2 needs case_id + key_quantities to evaluate; both are optional for
    backward compatibility — when omitted G2 is a silent no-op (existing
    G3/G4/G5 callers retain identical behaviour).
    """
    log_stats: Optional[LogStats] = None
    if log_path is not None and log_path.is_file():
        log_stats = parse_solver_log(log_path)

    violations: list[GateViolation] = []
    violations.extend(_check_g2_canonical_band_shortcut(case_id, key_quantities))
    violations.extend(_check_g3_velocity_overflow(log_stats, vtk_dir, U_ref))
    violations.extend(_check_g4_turbulence_negativity(log_stats))
    violations.extend(_check_g5_continuity_divergence(log_stats))
    return violations


_GATE_DECISION_REFS = {
    "G2": "DEC-V61-059",
    "G3": "DEC-V61-036b",
    "G4": "DEC-V61-036b",
    "G5": "DEC-V61-036b",
}


def violation_to_audit_concern_dict(v: GateViolation) -> dict[str, Any]:
    """Serialize a GateViolation as an audit_concerns[] fixture entry."""
    return {
        "concern_type": v.concern_type,
        "summary": v.summary,
        "detail": v.detail,
        "decision_refs": [_GATE_DECISION_REFS.get(v.gate_id, "DEC-V61-036b")],
        "evidence": v.evidence,
    }
