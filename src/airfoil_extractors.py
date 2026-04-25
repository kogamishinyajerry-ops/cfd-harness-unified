"""DEC-V61-058: airfoil multi-α extractors (Cl, Cd, dCl/dα, y+_max).

Reads OpenFOAM postProcessing artifacts emitted by the FOs that
``foam_agent_adapter._generate_airfoil_flow`` registered in
controlDict (B1.2 + B1.3):

  - ``postProcessing/forceCoeffs1/<t>/coefficient.dat`` (B1.2)
    timestep-by-timestep Cl(t), Cd(t), Cm(t) on the ``aerofoil``
    patch, with α-aware ``liftDir``/``dragDir``.
  - ``postProcessing/yPlus/<t>/yPlus.dat`` (B1.3)
    time-stamped per-patch (min, max, average) y+ rows.

Pipeline contract (matches Type II gate set per intake §3):

  Cl@α    via ``compute_cl_cd(case_dir, alpha_deg)`` final-time row
  Cd@α    via ``compute_cl_cd(case_dir, alpha_deg)`` final-time row
  dCl/dα  via ``compute_lift_slope([(α, Cl), …])`` 3-point linear fit
          + linearity check (|Cl(4°) - 0.5·(Cl(0°)+Cl(8°))|/|Cl(8°)| < 0.05)
  y+_max  via ``compute_y_plus_max(case_dir)`` final-time row

The ``coefficient.dat`` parser is delegated to the proven path in
``cylinder_strouhal_fft.parse_coefficient_dat`` (DEC-V61-041): same
OpenFOAM 10 column-name layout, ``#``-prefixed header. Reusing that
parser keeps the OF-version-drift risk in ONE module and frees the
airfoil pipeline from re-deriving it.

ADR-001 plane assignment: Execution Plane (reads OpenFOAM artifacts;
NO Evaluation imports — comparator wiring lives in Stage C).

DEC-V61-058 risk_flags addressed:

  numerical_noise_snr (intake §4): per-gate SNR documented below;
    HARD gates have SNR ≥ 8e3, well above 10× safety floor.
    Cl@α=0° EXCLUDED (gold = 0, ratio undefined → SANITY_CHECK only).
  python_version_parity: pure stdlib + math; py_compile clean under
    Python 3.9 (CI) + 3.12 (.venv).

Per-gate SNR table (intake §4 final values):

  | Gate                        | gold     | noise_floor      | ratio  |
  |-----------------------------|----------|------------------|--------|
  | Cl@α=8°  (HEADLINE_PRIMARY) |  0.815   | ≈ Δp_resid·Aref* | ≈ 8e5  |
  | Cl@α=4°  (HELPER_FOR_SLOPE) |  0.434   | same             | ≈ 4e5  |
  | Cd@α=0°  (SAME_RUN_CROSS)   |  0.0080  | same             | ≈ 8e3  |
  | Cp@x/c=0.5 (PROFILE_GATE)   | -0.40    | Δp/(0.5ρU²)≈2e-6 | ≈ 2e5  |
  | dCl/dα slope (QUALITATIVE)  |  0.105   | √(σ_Cl²+σ_Cl²)/8°| ≈ 2e4  |
  | y+_max (PROVISIONAL_ADV)    | [11,500] | sub-1.0          |   ≥ 11 |
  | Cl@α=0°  (SANITY_CHECK)     |  0.000   | undefined        |  ∞/0   |

  * Δp_resid·Aref / (0.5·ρ·U²·Aref) = Δp_resid/(0.5ρU²) ≈ 1e-6 / 0.5
    ≈ 2e-6 → Cl/Cd noise ≈ 2e-6 → ratios as above.

References:

  - Ladson 1988 NASA TM-4074 §3.2 Tab.1 Re=3e6 fixed-transition
    (gold values for Cl(α=4,8), Cd(α=0), dCl/dα slope).
  - OF airFoil2D tutorial (freestream-rotation convention).
  - intake YAML: .planning/intake/DEC-V61-058_naca0012_airfoil.yaml
  - gold YAML: knowledge/gold_standards/naca0012_airfoil.yaml
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Reuse the proven coefficient.dat parser from DEC-V61-041 (Execution
# plane → Execution plane import is allowed per ADR-001 §2.2 matrix).
from src.cylinder_strouhal_fft import (
    CylinderStrouhalError,
    parse_coefficient_dat,
)


class AirfoilExtractorError(Exception):
    """Raised when the airfoil postProcessing pipeline cannot produce a
    trustworthy Cl/Cd/y+ result. Covers:

    - Missing or malformed coefficient.dat / yPlus.dat
    - Empty post-trim window (zero data rows)
    - α-routing inconsistency (sign-convention assertion failure)
    """


@dataclass(frozen=True)
class CoeffsResult:
    """Single-α run's force-coefficient extraction."""

    alpha_deg: float
    Cl: float
    Cd: float
    final_time: float
    n_samples: int
    # Drift over last 100 samples — supports per-case attestor threshold
    # (intake §7 Batch C: cl_drift_pct < 1.0). 0.0 if < 100 samples.
    cl_drift_pct_last_100: float = 0.0
    cd_drift_pct_last_100: float = 0.0


@dataclass(frozen=True)
class LiftSlopeResult:
    """Multi-α slope extraction (3-point linear fit).

    DEC-V61-058 Codex round 2 Q4(c) → C3-priority deferred:
    `linearity_check_applicable` flag added (round 3). The 2-point case
    (α∈{0,8}) cannot evaluate `|Cl(4°) - 0.5·(Cl(0°)+Cl(8°))|` because
    Cl(4°) is missing; pre-flag the result reported `linearity_ok=True`
    by default which was misleading. Now: `linearity_check_applicable`
    is True ONLY when α∈{0,4,8} are all present; downstream consumers
    must check this flag before trusting `linearity_ok`.
    """

    slope_per_deg: float        # dCl/dα
    intercept: float             # Cl at α=0
    linearity_check_applicable: bool  # True iff α∈{0,4,8} all present
    linearity_ok: bool           # |Cl(4) - 0.5·(Cl(0)+Cl(8))| / |Cl(8)| < 0.05; meaningful only when linearity_check_applicable
    linearity_residual: float    # LHS of the inequality; 0.0 if not applicable
    n_points: int                # 3 for α∈{0,4,8}; ≥2 for arbitrary fit
    points: Tuple[Tuple[float, float], ...] = ()  # ((α, Cl), …)


@dataclass(frozen=True)
class YPlusResult:
    """Wall-resolution diagnostic from yPlus FO."""

    y_plus_max: float
    y_plus_min: float
    y_plus_avg: float
    final_time: float
    advisory_status: str  # 'PASS' if in [11,500]; 'FLAG' if outside;
                          # 'BLOCK' if outside [5, 1000].


# --------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------


def _latest_time_dir(parent: Path) -> Optional[Path]:
    """Return the lexically-largest numeric subdirectory of ``parent``.

    OpenFOAM postProcessing creates ``<t>/`` directories per write
    interval; the canonical 'final-time' artifact is in the
    largest-numbered directory.

    Mirrors ``cylinder_strouhal_fft._latest_time_dir`` for symmetry.
    """
    if not parent.is_dir():
        return None
    candidates: List[Tuple[float, Path]] = []
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        try:
            candidates.append((float(child.name), child))
        except ValueError:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def _drift_pct(values: Sequence[float], window: int = 100) -> float:
    """Return percentage drift over the last ``window`` samples.

    Defined as ``100·|values[-1] - values[-window]| / max(|mean|, 1e-12)``
    where mean is over the same window. Returns 0.0 if fewer than
    ``window`` samples (insufficient data → assume no drift signal).
    """
    if len(values) < window:
        return 0.0
    last_window = list(values[-window:])
    delta = abs(last_window[-1] - last_window[0])
    mean_abs = abs(sum(last_window) / len(last_window))
    if mean_abs < 1e-12:
        return 0.0
    return 100.0 * delta / mean_abs


# --------------------------------------------------------------------
# Public extractors
# --------------------------------------------------------------------


def compute_cl_cd(
    case_dir: Path,
    alpha_deg: float,
    *,
    fo_name: str = "forceCoeffs1",
) -> CoeffsResult:
    """Extract Cl, Cd at the final timestep from forceCoeffs FO output.

    Args:
        case_dir: OpenFOAM case directory (must contain
            ``postProcessing/<fo_name>/<t>/coefficient.dat``).
        alpha_deg: angle of attack used for this run; threaded into
            the result for downstream sign-convention assertion.
        fo_name: forceCoeffs FO name (matches B1.2 controlDict default).

    Raises:
        AirfoilExtractorError: missing/empty coefficient.dat, or zero
        data rows after parsing.

    Sign-convention precondition (intake §9 stage_e_close_checklist):
      α=+8° run MUST produce Cl > 0 strictly (asserted at the call site
      in Stage E smoke; this extractor returns the value unfiltered).
    """
    fo_dir = case_dir / "postProcessing" / fo_name
    time_dir = _latest_time_dir(fo_dir)
    if time_dir is None:
        raise AirfoilExtractorError(
            f"forceCoeffs FO output dir not found: {fo_dir} "
            f"(expected after running adapter B1.2 controlDict)"
        )

    # OpenFOAM 10 (foundation) emits `forceCoeffs.dat`; ESI/older versions
    # write `coefficient.dat`. Accept either — same column layout (header
    # is parsed by name in parse_coefficient_dat).
    coeff_dat = None
    for name in ("coefficient.dat", "forceCoeffs.dat"):
        candidate = time_dir / name
        if candidate.is_file():
            coeff_dat = candidate
            break
    if coeff_dat is None:
        raise AirfoilExtractorError(
            f"forceCoeffs output not found in {time_dir} "
            f"(checked coefficient.dat, forceCoeffs.dat)"
        )

    try:
        t_list, cd_list, cl_list = parse_coefficient_dat(coeff_dat)
    except CylinderStrouhalError as exc:
        # Re-raise under our own type so callers can catch one error class.
        raise AirfoilExtractorError(
            f"{coeff_dat.name} parse failed: {exc}"
        ) from exc

    if not t_list or not cl_list or not cd_list:
        raise AirfoilExtractorError(
            f"{coeff_dat} parsed zero rows (header malformed?)"
        )

    # Codex round 1 F2: fail closed on NaN/inf in the final-time row. A
    # diverged simpleFoam solve happily writes coefficient.dat with `nan`
    # or `inf` cells; the parser converts those to float('nan') /
    # float('inf') and they would otherwise propagate as "trustworthy"
    # gate values into the comparator.
    cl_final = float(cl_list[-1])
    cd_final = float(cd_list[-1])
    if not math.isfinite(cl_final) or not math.isfinite(cd_final):
        raise AirfoilExtractorError(
            f"non-finite final-time row in {coeff_dat}: "
            f"Cl={cl_final}, Cd={cd_final}. Solver likely diverged; "
            f"check residuals + run length."
        )

    return CoeffsResult(
        alpha_deg=float(alpha_deg),
        Cl=cl_final,
        Cd=cd_final,
        final_time=float(t_list[-1]),
        n_samples=len(t_list),
        cl_drift_pct_last_100=_drift_pct(cl_list, window=100),
        cd_drift_pct_last_100=_drift_pct(cd_list, window=100),
    )


def compute_lift_slope(
    points: Sequence[Tuple[float, float]],
) -> LiftSlopeResult:
    """3-point linear fit of Cl(α) → dCl/dα slope + linearity check.

    Args:
        points: sequence of (alpha_deg, Cl) pairs. Expected exactly 3
            points at α∈{0°, 4°, 8°} per intake §3 extraction method;
            but the function tolerates any ordered sequence with ≥2
            points (returns the LSQ slope) and only the linearity
            check requires exactly the canonical α∈{0, 4, 8} layout.

    Returns:
        LiftSlopeResult with slope_per_deg, intercept (Cl at α=0),
        linearity_ok flag (gold YAML linearity_check criterion), and
        the residual value used.

    Raises:
        AirfoilExtractorError: fewer than 2 points, or non-finite Cl.
    """
    pts = [(float(a), float(c)) for a, c in points]
    if len(pts) < 2:
        raise AirfoilExtractorError(
            f"compute_lift_slope needs ≥2 points; got {len(pts)}"
        )
    for a, c in pts:
        if not math.isfinite(a) or not math.isfinite(c):
            raise AirfoilExtractorError(
                f"non-finite point in slope fit: ({a}, {c})"
            )

    # Least-squares slope + intercept (closed-form for 1D OLS).
    n = len(pts)
    sum_a = sum(a for a, _ in pts)
    sum_c = sum(c for _, c in pts)
    sum_a2 = sum(a * a for a, _ in pts)
    sum_ac = sum(a * c for a, c in pts)
    denom = n * sum_a2 - sum_a * sum_a
    if abs(denom) < 1e-18:
        raise AirfoilExtractorError(
            f"degenerate slope fit (all α equal): {pts}"
        )
    slope = (n * sum_ac - sum_a * sum_c) / denom
    intercept = (sum_c - slope * sum_a) / n

    # Linearity check per gold YAML extraction.linearity_check:
    #   |Cl(4°) - 0.5·(Cl(0°) + Cl(8°))| / |Cl(8°)| < 0.05
    # Only well-defined when α∈{0, 4, 8} are all present.
    # Codex round 2 Q4(c) → round 3 C3 fix: linearity_check_applicable flag
    # makes the not-applicable case explicit instead of silently reporting
    # linearity_ok=True.
    linearity_check_applicable = False
    linearity_ok = False
    linearity_residual = 0.0
    by_alpha = {round(a): c for a, c in pts}
    if all(a in by_alpha for a in (0, 4, 8)):
        cl_0 = by_alpha[0]
        cl_4 = by_alpha[4]
        cl_8 = by_alpha[8]
        midpoint = 0.5 * (cl_0 + cl_8)
        denom8 = abs(cl_8) + 1e-12
        linearity_residual = abs(cl_4 - midpoint) / denom8
        linearity_ok = linearity_residual < 0.05
        linearity_check_applicable = True

    return LiftSlopeResult(
        slope_per_deg=slope,
        intercept=intercept,
        linearity_check_applicable=linearity_check_applicable,
        linearity_ok=linearity_ok,
        linearity_residual=linearity_residual,
        n_points=n,
        points=tuple(pts),
    )


def compute_y_plus_max(
    case_dir: Path,
    *,
    fo_name: str = "yPlus",
    patch_name: str = "aerofoil",
) -> YPlusResult:
    """Read y+_max on the airfoil patch from yPlus FO output (final-time row).

    yPlus FO writes ``postProcessing/yPlus/<t>/yPlus.dat`` with header
    ``# Time  patch  min  max  average`` (OpenFOAM 10 default; column
    layout may drift slightly across versions — we look up by header
    name where present, else fall back to positional layout
    ``[time, patch, min, max, avg]``).

    Args:
        case_dir: OpenFOAM case directory.
        fo_name: yPlus FO name (matches B1.3 controlDict default).
        patch_name: patch to extract (matches blockMesh boundary
            name; B1 keeps the British spelling 'aerofoil').

    Raises:
        AirfoilExtractorError: missing yPlus.dat, no rows for the
        requested patch, or non-numeric values.

    Returns:
        YPlusResult with min/max/avg + advisory_status:
          'PASS'  if y+_max in [11, 500]   (PROVISIONAL band per Codex F5)
          'FLAG'  if y+_max outside [11, 500] but inside [5, 1000]
          'BLOCK' if y+_max outside [5, 1000]
    """
    fo_dir = case_dir / "postProcessing" / fo_name
    time_dir = _latest_time_dir(fo_dir)
    if time_dir is None:
        raise AirfoilExtractorError(
            f"yPlus FO output dir not found: {fo_dir}"
        )

    yplus_dat = time_dir / "yPlus.dat"
    if not yplus_dat.is_file():
        raise AirfoilExtractorError(
            f"yPlus.dat not found at {yplus_dat}"
        )

    text = yplus_dat.read_text(encoding="utf-8", errors="replace")
    header_idx_map: Dict[str, int] = {}
    rows: List[Tuple[float, str, float, float, float]] = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            tokens = line.lstrip("#").split()
            if tokens and tokens[0].lower() == "time":
                # OF10 yPlus header: # Time   patch   min   max   average
                for i, tok in enumerate(tokens):
                    header_idx_map[tok.lower()] = i
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        # Resolve column indices by name where header present, else positional.
        time_idx = header_idx_map.get("time", 0)
        patch_idx = header_idx_map.get("patch", 1)
        min_idx = header_idx_map.get("min", 2)
        max_idx = header_idx_map.get("max", 3)
        avg_idx = header_idx_map.get("average", header_idx_map.get("avg", 4))
        try:
            t_val = float(parts[time_idx])
            patch_val = parts[patch_idx]
            min_val = float(parts[min_idx])
            max_val = float(parts[max_idx])
            avg_val = float(parts[avg_idx])
        except (ValueError, IndexError):
            continue
        rows.append((t_val, patch_val, min_val, max_val, avg_val))

    if not rows:
        raise AirfoilExtractorError(
            f"yPlus.dat parsed zero numeric rows: {yplus_dat}"
        )

    # Find rows for the requested patch; final-time row wins.
    patch_rows = [r for r in rows if r[1] == patch_name]
    if not patch_rows:
        raise AirfoilExtractorError(
            f"yPlus.dat has no rows for patch={patch_name!r}; "
            f"patches present: {sorted({r[1] for r in rows})}"
        )
    final = patch_rows[-1]
    t_val, _, ymin, ymax, yavg = final

    # Codex round 1 F2: fail closed on NaN/inf in the final-time row.
    # yPlus FO emits NaN if wallDist is mal-resolved (zero-thickness face,
    # singularity at trailing edge, etc.). Propagating those would
    # produce a meaningless ADVISORY_BLOCK that masks the real cause.
    if not (math.isfinite(ymin) and math.isfinite(ymax) and math.isfinite(yavg)):
        raise AirfoilExtractorError(
            f"non-finite y+ values in {yplus_dat} for patch={patch_name!r}: "
            f"min={ymin}, max={ymax}, avg={yavg}. Likely wallDist failure on "
            f"degenerate face."
        )

    # Threshold band per Codex F5 (PROVISIONAL_ADVISORY).
    if 11.0 <= ymax <= 500.0:
        status = "PASS"
    elif 5.0 <= ymax <= 1000.0:
        status = "FLAG"
    else:
        status = "BLOCK"

    return YPlusResult(
        y_plus_max=ymax,
        y_plus_min=ymin,
        y_plus_avg=yavg,
        final_time=t_val,
        advisory_status=status,
    )


def assert_sign_convention(result: CoeffsResult) -> None:
    """Stage E smoke test helper: assert α=+8° → Cl > 0 strictly.

    Per intake §9 stage_e_close_checklist sign-convention smoke item.
    Also enforces the SANITY_CHECK: |Cl| < 0.005 at α=0°.

    Raises:
        AirfoilExtractorError: assertion failure with diagnostic context.
    """
    a = result.alpha_deg
    if abs(a - 8.0) < 1e-3:
        if not (result.Cl > 0.0):
            raise AirfoilExtractorError(
                f"sign-convention violation: α=+8° produced Cl={result.Cl} "
                f"(expected > 0). liftDir/freestream rotation may be wrong "
                f"(see foam_agent_adapter._generate_airfoil_flow Codex F2 "
                f"comment block)."
            )
    elif abs(a) < 1e-3:
        # SANITY_CHECK band per gold YAML sanity_checks block.
        if abs(result.Cl) >= 0.005:
            raise AirfoilExtractorError(
                f"sanity_check violation at α=0°: |Cl|={abs(result.Cl)} "
                f"(expected < 0.005 for symmetric airfoil). Mesh asymmetry "
                f"or numerical noise above floor."
            )
