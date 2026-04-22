"""DEC-V61-036b: Hard comparator gates G3/G4/G5 — post-extraction physics gates.

Trigger FAIL on:
  * G3 VELOCITY_OVERFLOW  — |U|_max > K * U_ref (K=100 default). VTK-based,
    with log-based epsilon proxy fallback (epsilon ~ u^3/L).
  * G4 TURBULENCE_NEGATIVE — k/epsilon/omega min < 0 at last bounding line
    OR max > 1e+10 (sanity overflow).
  * G5 CONTINUITY_DIVERGED — last-iter sum_local > 1e-2 OR |cumulative| > 1.

Operates on artifacts already written by the audit pipeline:
  * `reports/phase5_fields/{case_id}/{ts}/log.simpleFoam` (or .pimpleFoam,
    .icoFoam, .buoyantSimpleFoam)
  * `reports/phase5_fields/{case_id}/{ts}/VTK/*.vtk` (latest time step)

See the accompanying DEC file for ground-truth evidence from the BFS run
(cumulative=-1434.64, k min=-6.41e+30) and expected gate outcomes.
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


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GateViolation:
    """A single post-extraction gate FAIL.

    The fixture writer forwards these to audit_concerns[] and the
    validation_report verdict engine hard-FAILs on any violation.
    """

    gate_id: str          # "G3" | "G4" | "G5"
    concern_type: str     # "VELOCITY_OVERFLOW" | "TURBULENCE_NEGATIVE" | "CONTINUITY_DIVERGED"
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
    """Return the max |U| across all cells in the latest-time VTK.

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

    # Find the latest-time VTK file. OpenFOAM foamToVTK lays files as
    # {case}_{timestep}.vtk or allPatches/{case}_{timestep}.vtk. We scan
    # the whole tree under vtk_dir.
    candidates = sorted(vtk_dir.rglob("*.vtk"))
    if not candidates:
        return None

    u_max_overall: Optional[float] = None
    for vtk_path in candidates:
        try:
            mesh = pv.read(str(vtk_path))
        except Exception:
            continue
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
            continue
        # U is typically (N, 3); compute per-cell magnitude.
        if U_array.ndim == 2 and U_array.shape[1] >= 3:
            mags = np.linalg.norm(U_array[:, :3], axis=1)
        else:
            mags = np.abs(U_array.ravel())
        if mags.size == 0:
            continue
        candidate_max = float(np.nanmax(mags))
        if u_max_overall is None or candidate_max > u_max_overall:
            u_max_overall = candidate_max
    return u_max_overall


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
) -> list[GateViolation]:
    """Run G3 + G4 + G5 and return the aggregated list of violations.

    Called from `scripts/phase5_audit_run.py::_audit_fixture_doc` after
    G1 extraction. Each violation becomes an `audit_concerns[]` entry;
    `ui/backend/services/validation_report._derive_contract_status`
    hard-FAILs when any of the concern codes is present.
    """
    log_stats: Optional[LogStats] = None
    if log_path is not None and log_path.is_file():
        log_stats = parse_solver_log(log_path)

    violations: list[GateViolation] = []
    violations.extend(_check_g3_velocity_overflow(log_stats, vtk_dir, U_ref))
    violations.extend(_check_g4_turbulence_negativity(log_stats))
    violations.extend(_check_g5_continuity_divergence(log_stats))
    return violations


def violation_to_audit_concern_dict(v: GateViolation) -> dict[str, Any]:
    """Serialize a GateViolation as an audit_concerns[] fixture entry."""
    return {
        "concern_type": v.concern_type,
        "summary": v.summary,
        "detail": v.detail,
        "decision_refs": ["DEC-V61-036b"],
        "evidence": v.evidence,
    }
