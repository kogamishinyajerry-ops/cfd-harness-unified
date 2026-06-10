"""P4 V73.A · transonic airfoil (SBLI) QoI extractor (Execution Plane).

Extracts the RAE-2822-class transonic quantities from a solved compressible
case's raw artifacts:

    cl_fc / cd_fc        forceCoeffs coefficient.dat (name-based columns,
                         reusing the cylinder/airfoil parser chain)
    Cp(x/c) upper/lower  surfaces-FO raw file, COMPRESSIBLE normalization
                         Cp = (p - p_inf) / (0.5 * rho_inf * U_inf^2),
                         rho_inf = p_inf / (R * T_inf), p ABSOLUTE
    cn_p / ca_p / cl_p   contour pressure integration (independent
                         cross-check for the solver-reported Cl —
                         loop-auditor V73.A F2)
    shock_xc             upper-surface Cp* recompression crossing with
                         anti-wiggle guards (F3)
    freestream           MEASURED from an upstream probe FO (solved field)
                         + DECLARED from 0/ BCs — both returned so the
                         gate can do the three-way consistency check
                         (measured ~ declared ~ gold target, F1)

HONESTY
-------
The judged quantities are recomputed here from raw solver output; the shock
location is NEVER read from any solver-reported field, and the freestream
used for thresholds is the MEASURED one (a doctored 0/ file alone cannot
move the gates — wedge-gate precedent). Surface split is by CONTOUR
TRAVERSAL (nearest-neighbour chaining, split at LE), not z-sign — RAE 2822's
aft-loaded lower surface can cross z=0 (loop-auditor F6).

Fail-closed: missing/garbled files, nonuniform declared BCs, sparse upper
surface (< MIN_UPPER_POINTS), broken contour chain, non-positive absolute
pressure -> raise TransonicExtractionError. Never a fabricated QoI.

ADR-001: Execution Plane (stdlib + same-plane import of the coefficient.dat
parser; no Evaluation/Control imports — thresholds live in the gate).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .cylinder_strouhal_fft import parse_coefficient_dat, _latest_time_dir

# Minimum deduped points required on the upper surface for shock detection
# to be meaningful (F3: sparse-surface fail-closed).
MIN_UPPER_POINTS: int = 30
# Supersonic plateau guards (F3): >= N consecutive points below Cp* - margin.
PLATEAU_MIN_POINTS: int = 5
PLATEAU_MARGIN: float = 0.05
# Recompression jump must recover at least this fraction of the pocket depth.
JUMP_FRACTION: float = 0.3
# Max allowed Cp* crossings on the upper surface (down once, up once).
MAX_CROSSINGS: int = 2
# Contour chaining: a step longer than this multiple of the median step
# means the chain jumped across the profile (corrupt/duplicate points).
CHAIN_JUMP_FACTOR: float = 8.0


class TransonicExtractionError(ValueError):
    """Any extraction failure — the gate treats it as an honest BLOCK."""


@dataclass(frozen=True)
class FreestreamState:
    p_inf: float           # absolute static pressure [Pa]
    t_inf: float           # static temperature [K]
    u_vec: Tuple[float, float, float]
    mach: float
    alpha_deg: float       # atan2(Uz, Ux) in the x-z airfoil plane
    rho_inf: float


@dataclass(frozen=True)
class TransonicAirfoilMetrics:
    cl_fc: float                    # forceCoeffs lift coefficient (solver FO)
    cd_fc: float                    # forceCoeffs drag coefficient (solver FO)
    cl_p: float                     # pressure-integrated lift (independent)
    cn_p: float                     # normal-force coefficient from ∮Cp
    ca_p: float                     # chord-force coefficient from ∮Cp
    max_cp: float                   # over whole surface
    min_cp: float
    min_cp_upper: float
    shock_xc: Optional[float]       # None when detector declined (reason set)
    shock_decline_reason: Optional[str]
    n_upper: int
    n_lower: int
    measured: FreestreamState       # from the upstream probe (solved field)
    declared: FreestreamState       # from 0/ BC files
    reynolds_declared: float        # rho_inf*|U|*chord/mu from case transport
    upper_cp: Tuple[Tuple[float, float], ...]   # (x/c, Cp) ascending
    lower_cp: Tuple[Tuple[float, float], ...]


# --------------------------------------------------------------------------
# Raw parsing helpers (fail-closed)
# --------------------------------------------------------------------------

def _read_rows_xyzv(path: Path) -> List[Tuple[float, float, float, float]]:
    if not path.is_file():
        raise TransonicExtractionError(f"missing raw surface file: {path}")
    rows: List[Tuple[float, float, float, float]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 4:
            raise TransonicExtractionError(
                f"{path}:{lineno}: expected 4 columns (x y z p), got {len(parts)}"
            )
        try:
            rows.append(tuple(float(parts[i]) for i in range(4)))  # type: ignore[arg-type]
        except ValueError as exc:
            raise TransonicExtractionError(
                f"{path}:{lineno}: non-numeric field"
            ) from exc
    if not rows:
        raise TransonicExtractionError(f"{path}: no data rows")
    return rows


_UNIFORM_VEC_RE = re.compile(
    r"internalField\s+uniform\s+\(\s*([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s*\)\s*;"
)
_UNIFORM_SCA_RE = re.compile(r"internalField\s+uniform\s+([0-9eE+.\-]+)\s*;")


def _declared_uniform_scalar(path: Path) -> float:
    if not path.is_file():
        raise TransonicExtractionError(f"missing declared BC file: {path}")
    m = _UNIFORM_SCA_RE.search(path.read_text(encoding="utf-8"))
    if not m:
        raise TransonicExtractionError(
            f"{path}: no uniform scalar internalField (nonuniform declared "
            f"freestream is not supported — fail-closed)"
        )
    return float(m.group(1))


def _declared_uniform_vector(path: Path) -> Tuple[float, float, float]:
    if not path.is_file():
        raise TransonicExtractionError(f"missing declared BC file: {path}")
    m = _UNIFORM_VEC_RE.search(path.read_text(encoding="utf-8"))
    if not m:
        raise TransonicExtractionError(f"{path}: no uniform vector internalField")
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)))


_PROBE_VEC_RE = re.compile(r"\(\s*([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s+([0-9eE+.\-]+)\s*\)")


def _parse_freestream_probe(case_dir: Path) -> Tuple[float, float, Tuple[float, float, float]]:
    """Last row of postProcessing/freestreamProbe/<t>/surfaceFieldValue.dat.

    Contract (the V73.B case template emits exactly this): name-based header
    with areaAverage(p), areaAverage(T), areaAverage(U); U as '(ux uy uz)'.
    """
    parent = case_dir / "postProcessing" / "freestreamProbe"
    tdir = _latest_time_dir(parent)
    if tdir is None:
        raise TransonicExtractionError(
            f"no freestream probe output under {parent} (the measured-"
            f"freestream gate is mandatory — fail-closed, loop-auditor F1)"
        )
    dat = tdir / "surfaceFieldValue.dat"
    if not dat.is_file():
        raise TransonicExtractionError(f"missing {dat}")
    header_cols: List[str] = []
    last: Optional[str] = None
    for line in dat.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#"):
            cols = s.lstrip("#").split()
            if "areaAverage(p)" in cols:
                header_cols = cols
            continue
        if s:
            last = s
    if not header_cols or last is None:
        raise TransonicExtractionError(f"{dat}: missing header or data rows")
    i_p = header_cols.index("areaAverage(p)")
    i_t = header_cols.index("areaAverage(T)")
    i_u = header_cols.index("areaAverage(U)")
    vecs = _PROBE_VEC_RE.findall(last)
    scalars = re.sub(_PROBE_VEC_RE, "VEC", last).split()
    # scalars list now has 'VEC' placeholders where vectors were
    try:
        p = float(scalars[i_p])
        t = float(scalars[i_t])
        n_vec_before = sum(1 for c in scalars[:i_u] if c == "VEC")
        u = tuple(float(v) for v in vecs[n_vec_before])
    except (ValueError, IndexError) as exc:
        raise TransonicExtractionError(f"{dat}: cannot parse last row") from exc
    return p, t, u  # type: ignore[return-value]


def _freestream_state(p: float, t: float, u: Tuple[float, float, float],
                      gamma: float, r_specific: float, source: str) -> FreestreamState:
    if p <= 0 or t <= 0:
        raise TransonicExtractionError(
            f"non-physical {source} freestream: p={p}, T={t} (absolute "
            f"pressure/temperature required for a compressible case)"
        )
    umag = math.sqrt(sum(c * c for c in u))
    if umag <= 0:
        raise TransonicExtractionError(f"zero {source} freestream velocity")
    a = math.sqrt(gamma * r_specific * t)
    return FreestreamState(
        p_inf=p, t_inf=t, u_vec=u, mach=umag / a,
        alpha_deg=math.degrees(math.atan2(u[2], u[0])),
        rho_inf=p / (r_specific * t),
    )


def _declared_viscosity(case_dir: Path, t_inf: float) -> float:
    """mu from constant/thermophysicalProperties: const-mu or Sutherland."""
    path = case_dir / "constant" / "thermophysicalProperties"
    if not path.is_file():
        raise TransonicExtractionError(f"missing {path} (Re check needs mu)")
    text = path.read_text(encoding="utf-8")
    m_mu = re.search(r"\bmu\s+([0-9eE+.\-]+)\s*;", text)
    if m_mu:
        return float(m_mu.group(1))
    m_as = re.search(r"\bAs\s+([0-9eE+.\-]+)\s*;", text)
    m_ts = re.search(r"\bTs\s+([0-9eE+.\-]+)\s*;", text)
    if m_as and m_ts:
        As, Ts = float(m_as.group(1)), float(m_ts.group(1))
        return As * math.sqrt(t_inf) / (1.0 + Ts / t_inf)
    raise TransonicExtractionError(
        f"{path}: neither const mu nor Sutherland As/Ts found (fail-closed)"
    )


# --------------------------------------------------------------------------
# Contour ordering + surface split (loop-auditor F6: no z-sign split)
# --------------------------------------------------------------------------

def _dedup_span(rows: Sequence[Tuple[float, float, float, float]]
                ) -> List[Tuple[float, float, float]]:
    """Collapse thin-span duplicates (faces at y=±span) to one (x, z, p)."""
    seen: Dict[Tuple[float, float], Tuple[float, float, float]] = {}
    for x, _y, z, p in rows:
        seen[(round(x, 9), round(z, 9))] = (x, z, p)
    return list(seen.values())


def order_contour(points: List[Tuple[float, float, float]]
                  ) -> List[Tuple[float, float, float]]:
    """Nearest-neighbour chain over (x, z) — fail-closed on chain jumps."""
    if len(points) < 8:
        raise TransonicExtractionError(
            f"only {len(points)} surface points — too sparse to order a contour"
        )
    remaining = points[:]
    # start at the trailing edge (max x)
    current = max(remaining, key=lambda p: p[0])
    remaining.remove(current)
    chain = [current]
    steps: List[float] = []
    while remaining:
        nxt = min(remaining, key=lambda p: (p[0] - current[0]) ** 2 + (p[1] - current[1]) ** 2)
        steps.append(math.dist((current[0], current[1]), (nxt[0], nxt[1])))
        remaining.remove(nxt)
        chain.append(nxt)
        current = nxt
    med = sorted(steps)[len(steps) // 2]
    if med <= 0:
        raise TransonicExtractionError("degenerate contour (zero median step)")
    worst = max(steps)
    if worst > CHAIN_JUMP_FACTOR * med:
        raise TransonicExtractionError(
            f"contour chain jump {worst:.3g} > {CHAIN_JUMP_FACTOR}x median "
            f"{med:.3g} — surface points not a single clean profile (fail-closed)"
        )
    return chain


def split_surfaces(chain: List[Tuple[float, float, float]]
                   ) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Split the ordered closed contour at LE (min x) into two branches;
    upper = branch with the higher mean z. Returns (upper, lower) as
    (x, p) pairs? -- NO: returns (x, z, p) reduced to (x, p) later; here we
    keep (x, z, p) split, sorted by x ascending, as (x, p) pairs plus z used
    for the caller's geometry integration."""
    i_le = min(range(len(chain)), key=lambda i: chain[i][0])
    branch_a = chain[: i_le + 1]
    branch_b = chain[i_le:]
    mean_z_a = sum(p[1] for p in branch_a) / len(branch_a)
    mean_z_b = sum(p[1] for p in branch_b) / len(branch_b)
    upper3, lower3 = (branch_a, branch_b) if mean_z_a >= mean_z_b else (branch_b, branch_a)
    upper = sorted(((x, z, p) for x, z, p in upper3), key=lambda t: t[0])
    lower = sorted(((x, z, p) for x, z, p in lower3), key=lambda t: t[0])
    return upper, lower  # type: ignore[return-value]


# --------------------------------------------------------------------------
# Shock detection (loop-auditor F3 guards)
# --------------------------------------------------------------------------

def detect_shock(upper_xc_cp: List[Tuple[float, float]], cp_star: float
                 ) -> Tuple[Optional[float], Optional[str]]:
    """Locate the supersonic-pocket recompression through Cp* on the upper
    surface. Returns (x/c, None) or (None, decline_reason)."""
    if len(upper_xc_cp) < MIN_UPPER_POINTS:
        raise TransonicExtractionError(
            f"upper surface has {len(upper_xc_cp)} points < {MIN_UPPER_POINTS} "
            f"— too sparse for shock detection (fail-closed)"
        )
    xs = [x for x, _ in upper_xc_cp]
    cps = [c for _, c in upper_xc_cp]
    # crossings of cp - cp_star
    signs = [c < cp_star for c in cps]
    crossings = sum(1 for a, b in zip(signs, signs[1:]) if a != b)
    if crossings > MAX_CROSSINGS:
        return None, f"{crossings} Cp* crossings > {MAX_CROSSINGS} (oscillatory field)"
    # longest supersonic plateau below cp_star - margin
    best_len, best_end, run = 0, -1, 0
    for i, c in enumerate(cps):
        run = run + 1 if c < cp_star - PLATEAU_MARGIN else 0
        if run > best_len:
            best_len, best_end = run, i
    if best_len < PLATEAU_MIN_POINTS:
        return None, (
            f"no supersonic plateau (longest run {best_len} < "
            f"{PLATEAU_MIN_POINTS} points below Cp*-{PLATEAU_MARGIN})"
        )
    # first recovery through cp_star after the plateau
    j = next((k for k in range(best_end + 1, len(cps)) if cps[k] >= cp_star), None)
    if j is None:
        return None, "supersonic pocket never recompresses through Cp*"
    plateau_start = best_end - best_len + 1
    min_cp_upper = min(cps)
    jump = cps[j] - min(cps[plateau_start: best_end + 1])
    if jump < JUMP_FRACTION * (cp_star - min_cp_upper):
        return None, (
            f"recompression jump {jump:.3f} < {JUMP_FRACTION} x pocket depth "
            f"{cp_star - min_cp_upper:.3f} (wiggle, not a shock)"
        )
    # steepest Cp rise within the crossing window
    window = range(max(best_end, 1), min(j + 1, len(cps) - 1) + 1)
    k_best = max(
        window,
        key=lambda k: (cps[k] - cps[k - 1]) / (xs[k] - xs[k - 1]) if xs[k] > xs[k - 1] else -math.inf,
    )
    return 0.5 * (xs[k_best] + xs[k_best - 1]), None


# --------------------------------------------------------------------------
# Pressure-integration cross-check (loop-auditor F2)
# --------------------------------------------------------------------------

def integrate_cn_ca(chain_xzcp: List[Tuple[float, float, float]], chord: float
                    ) -> Tuple[float, float]:
    """Cn, Ca from the closed Cp contour (pressure forces only).

    For COUNTER-CLOCKWISE traversal the outward normal is (dz, -dx)/ds, so
    dF_z = -p n_z ds = +p dx and dF_x = -p n_x ds = -p dz, giving
        Cn = +(1/c) ∮ Cp dx        Ca = -(1/c) ∮ Cp dz
    (the freestream-pressure term integrates to zero around a closed loop).
    Traversal direction is normalized via the signed area so the sign
    convention is independent of chaining direction.
    """
    pts = chain_xzcp + [chain_xzcp[0]]
    area2 = sum(
        (pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1])
        for i in range(len(pts) - 1)
    )
    if abs(area2) < 1e-12:
        raise TransonicExtractionError("degenerate contour (zero enclosed area)")
    # counter-clockwise (positive area) traversal yields the sign convention
    # below; flip if the chain came out clockwise.
    orient = 1.0 if area2 > 0 else -1.0
    cn = 0.0
    ca = 0.0
    for i in range(len(pts) - 1):
        x0, z0, c0 = pts[i]
        x1, z1, c1 = pts[i + 1]
        cp_mid = 0.5 * (c0 + c1)
        cn += cp_mid * (x1 - x0) / chord * orient
        ca += -cp_mid * (z1 - z0) / chord * orient
    return cn, ca


# --------------------------------------------------------------------------
# Top-level extraction
# --------------------------------------------------------------------------

def extract_transonic_airfoil(
    case_dir: Path,
    chord: float,
    gamma: float = 1.4,
    r_specific: float = 287.058,
    surface_dirname: str = "airfoilSurface",
    raw_filename: str = "p_aerofoil.raw",
) -> TransonicAirfoilMetrics:
    case_dir = Path(case_dir)
    if chord <= 0:
        raise TransonicExtractionError(f"non-physical chord {chord}")

    # freestream: measured (solved field) + declared (0/ BCs)
    p_m, t_m, u_m = _parse_freestream_probe(case_dir)
    measured = _freestream_state(p_m, t_m, u_m, gamma, r_specific, "measured")
    declared = _freestream_state(
        _declared_uniform_scalar(case_dir / "0" / "p"),
        _declared_uniform_scalar(case_dir / "0" / "T"),
        _declared_uniform_vector(case_dir / "0" / "U"),
        gamma, r_specific, "declared",
    )
    mu = _declared_viscosity(case_dir, declared.t_inf)
    umag_d = math.sqrt(sum(c * c for c in declared.u_vec))
    reynolds = declared.rho_inf * umag_d * chord / mu

    # forces from the solver FO (cross-checked below by ∮Cp)
    fc_parent = case_dir / "postProcessing" / "forceCoeffs1"
    tdir = _latest_time_dir(fc_parent)
    if tdir is None:
        raise TransonicExtractionError(f"no forceCoeffs output under {fc_parent}")
    dat = tdir / "coefficient.dat"
    if not dat.is_file():
        dat = tdir / "forceCoeffs.dat"
    try:
        times, cds, cls = parse_coefficient_dat(dat)
    except TransonicExtractionError:
        raise
    except Exception as exc:  # CylinderStrouhalError etc. -> our fail-closed type
        raise TransonicExtractionError(f"forceCoeffs parse failed: {exc}") from exc
    if not times:
        raise TransonicExtractionError(f"{dat}: empty coefficient history")
    cl_fc, cd_fc = cls[-1], cds[-1]
    if not all(math.isfinite(v) for v in (cl_fc, cd_fc)):
        raise TransonicExtractionError(f"{dat}: non-finite final coefficients")

    # surface Cp (compressible normalization off the MEASURED freestream)
    sdir = _latest_time_dir(case_dir / "postProcessing" / surface_dirname)
    if sdir is None:
        raise TransonicExtractionError(
            f"no surface output under postProcessing/{surface_dirname}"
        )
    rows = _read_rows_xyzv(sdir / raw_filename)
    if any(r[3] <= 0 for r in rows):
        raise TransonicExtractionError(
            "non-positive absolute pressure on surface (compressible case "
            "must carry absolute p — gauge-pressure setups are rejected)"
        )
    q_inf = 0.5 * measured.rho_inf * sum(c * c for c in measured.u_vec)
    dedup = _dedup_span(rows)
    chain = order_contour(dedup)
    chain_cp = [(x, z, (p - measured.p_inf) / q_inf) for x, z, p in chain]
    upper3, lower3 = split_surfaces(chain_cp)
    upper_cp = [(x / chord, cp) for x, _z, cp in upper3]
    lower_cp = [(x / chord, cp) for x, _z, cp in lower3]

    all_cp = [cp for _x, _z, cp in chain_cp]
    min_cp_upper = min(cp for _x, cp in upper_cp)

    # closed-form Cp* for the detector comes from the MEASURED Mach
    m2 = measured.mach * measured.mach
    cp_star = (2.0 / (gamma * m2)) * (
        ((2.0 + (gamma - 1.0) * m2) / (gamma + 1.0)) ** (gamma / (gamma - 1.0)) - 1.0
    )
    shock_xc, decline = detect_shock(upper_cp, cp_star)

    cn_p, ca_p = integrate_cn_ca(chain_cp, chord)
    a_rad = math.radians(measured.alpha_deg)
    cl_p = cn_p * math.cos(a_rad) - ca_p * math.sin(a_rad)

    return TransonicAirfoilMetrics(
        cl_fc=cl_fc, cd_fc=cd_fc, cl_p=cl_p, cn_p=cn_p, ca_p=ca_p,
        max_cp=max(all_cp), min_cp=min(all_cp), min_cp_upper=min_cp_upper,
        shock_xc=shock_xc, shock_decline_reason=decline,
        n_upper=len(upper_cp), n_lower=len(lower_cp),
        measured=measured, declared=declared, reynolds_declared=reynolds,
        upper_cp=tuple(upper_cp), lower_cp=tuple(lower_cp),
    )
