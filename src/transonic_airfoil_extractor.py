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
# The raw file samples FACE CENTRES: the end centre sits at most HALF the
# local end-face length inboard of the true LE/TE vertex. We compensate by
# exactly that data-derived amount (vertex-recovered chord estimate) and
# then hold a TIGHT symmetric band — a genuinely clipped/mis-scaled surface
# shrinks far beyond its own end-face half-lengths, so it cannot hide
# inside the compensation (Codex R1 P2 + R2 P1/P2 joint resolution).
_CHORD_EST_RTOL: float = 0.02


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


def _snapshot_atol(t_snap: float) -> float:
    """Time-matching tolerance for snapshot alignment (Codex V73.A R0 P1)."""
    return max(1.0e-9, 1.0e-6 * max(1.0, abs(t_snap)))


def _parse_freestream_probe(case_dir: Path, t_snap: float
                            ) -> Tuple[float, float, Tuple[float, float, float]]:
    """Row of postProcessing/freestreamProbe/<t>/surfaceFieldValue.dat whose
    Time matches the SURFACE snapshot time (Codex V73.A R0 P1: every judged
    quantity must come from the same solver state — never "last row").

    Contract (the V73.B case template emits exactly this): name-based header
    with Time, areaAverage(p), areaAverage(T), areaAverage(U); U as '(ux uy uz)'.
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
    rows: List[str] = []
    for line in dat.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#"):
            cols = s.lstrip("#").split()
            if "areaAverage(p)" in cols:
                header_cols = cols
            continue
        if s:
            rows.append(s)
    if not header_cols or not rows:
        raise TransonicExtractionError(f"{dat}: missing header or data rows")
    if "Time" not in header_cols:
        raise TransonicExtractionError(f"{dat}: header has no Time column")
    i_time = header_cols.index("Time")
    i_p = header_cols.index("areaAverage(p)")
    i_t = header_cols.index("areaAverage(T)")
    i_u = header_cols.index("areaAverage(U)")

    best: Optional[Tuple[float, List[str], List[Tuple[str, str, str]]]] = None
    for row in rows:
        vecs = _PROBE_VEC_RE.findall(row)
        scalars = re.sub(_PROBE_VEC_RE, "VEC", row).split()
        try:
            t_row = float(scalars[i_time])
        except (ValueError, IndexError):
            continue
        dt = abs(t_row - t_snap)
        # <= so the LAST row wins ties: restarted runs append duplicate
        # Time rows and only the post-restart one matches the fresh surface
        # write (Codex V73.A R1 P1)
        if best is None or dt <= best[0]:
            best = (dt, scalars, vecs)
    if best is None or best[0] > _snapshot_atol(t_snap):
        raise TransonicExtractionError(
            f"{dat}: no probe row at the surface snapshot time t={t_snap:g} "
            f"(closest {'none' if best is None else f'{best[0]:.3g} away'}) — "
            f"refusing to mix solver states (fail-closed)"
        )
    _dt, scalars, vecs = best
    try:
        p = float(scalars[i_p])
        t = float(scalars[i_t])
        n_vec_before = sum(1 for c in scalars[:i_u] if c == "VEC")
        u = tuple(float(v) for v in vecs[n_vec_before])
    except (ValueError, IndexError) as exc:
        raise TransonicExtractionError(
            f"{dat}: cannot parse probe row at t={t_snap:g}"
        ) from exc
    return p, t, u  # type: ignore[return-value]


def _select_at_time(times: List[float], t_snap: float, what: str) -> int:
    """Index of the history row matching the snapshot time (fail-closed).

    Ties pick the LAST matching row: restarted runs append duplicate Time
    rows, and only the post-restart one belongs to the fresh surface write
    (Codex V73.A R1 P1).
    """
    if not times:
        raise TransonicExtractionError(f"{what}: empty history")
    idx, best = 0, math.inf
    for i, t in enumerate(times):
        dt = abs(t - t_snap)
        if dt <= best:
            best, idx = dt, i
    if best > _snapshot_atol(t_snap):
        raise TransonicExtractionError(
            f"{what}: no row at the surface snapshot time t={t_snap:g} "
            f"(closest {times[idx]:g}) — refusing to mix solver states"
        )
    return idx


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
                   ) -> Tuple[List[Tuple[float, float, float]], List[Tuple[float, float, float]]]:
    """Split the ordered closed contour at the LE (min x) into two branches,
    upper = branch with the higher MEAN z (never a per-point z-sign test —
    RAE 2822's aft-loaded lower surface crosses z=0, loop-auditor F6).

    Returns (upper, lower) as (x, z, value) triples sorted by x ascending;
    the third element is whatever the chain carried (p or Cp)."""
    i_le = min(range(len(chain)), key=lambda i: chain[i][0])
    branch_a = chain[: i_le + 1]
    branch_b = chain[i_le:]
    mean_z_a = sum(p[1] for p in branch_a) / len(branch_a)
    mean_z_b = sum(p[1] for p in branch_b) / len(branch_b)
    upper3, lower3 = (branch_a, branch_b) if mean_z_a >= mean_z_b else (branch_b, branch_a)
    upper = sorted(((x, z, p) for x, z, p in upper3), key=lambda t: t[0])
    lower = sorted(((x, z, p) for x, z, p in lower3), key=lambda t: t[0])
    return upper, lower  # type: ignore[return-value]


def _recover_vertex_chord(
    upper3: List[Tuple[float, float, float]],
    lower3: List[Tuple[float, float, float]],
) -> Tuple[float, float]:
    """Estimate the TRUE leading-edge x and chord from face-centre samples.

    A surface patch is written one row per FACE CENTRE, so the extreme
    sample sits at most half its own face length inboard of the true LE/TE
    vertex. The compensation is therefore data-derived and bounded: half the
    end gap of whichever branch owns the extreme point. A clipped or
    mis-scaled surface is missing far more than its own end-face
    half-lengths, so it cannot pass the tight chord check downstream.
    Returns (le_true_x, chord_estimate).
    """
    if len(upper3) < 2 or len(lower3) < 2:
        raise TransonicExtractionError(
            "a surface branch has fewer than 2 points — too sparse to "
            "recover the vertex chord (fail-closed)"
        )

    def _end_gap(branch: List[Tuple[float, float, float]], at_te: bool) -> float:
        # measure to the first STRICTLY different x — a blunt TE can put two
        # face centres at identical x in one branch (duplicate-x plateau)
        xs = [p[0] for p in branch]
        if at_te:
            x0 = xs[-1]
            nxt = next((x for x in reversed(xs) if x < x0), None)
        else:
            x0 = xs[0]
            nxt = next((x for x in xs if x > x0), None)
        if nxt is None:
            raise TransonicExtractionError(
                "degenerate end spacing on a surface branch (all points at "
                "one x — fail-closed)"
            )
        return abs(x0 - nxt)

    le_branch = upper3 if upper3[0][0] <= lower3[0][0] else lower3
    te_branch = upper3 if upper3[-1][0] >= lower3[-1][0] else lower3
    le_true = le_branch[0][0] - 0.5 * _end_gap(le_branch, at_te=False)
    te_true = te_branch[-1][0] + 0.5 * _end_gap(te_branch, at_te=True)
    return le_true, te_true - le_true


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

    # The SURFACE write defines the judged snapshot; probe + forceCoeffs rows
    # are then selected AT that time (Codex V73.A R0 P1: a forceCoeffs FO
    # writing every step must not contribute a later state than the Cp field).
    sdir = _latest_time_dir(case_dir / "postProcessing" / surface_dirname)
    if sdir is None:
        raise TransonicExtractionError(
            f"no surface output under postProcessing/{surface_dirname}"
        )
    try:
        t_snap = float(sdir.name)
    except ValueError as exc:
        raise TransonicExtractionError(
            f"surface time directory {sdir.name!r} is not numeric"
        ) from exc

    # freestream: measured (solved field, at t_snap) + declared (0/ BCs)
    p_m, t_m, u_m = _parse_freestream_probe(case_dir, t_snap)
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

    # forces from the solver FO at t_snap (cross-checked below by ∮Cp)
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
    i_fc = _select_at_time(times, t_snap, f"{dat}")
    cl_fc, cd_fc = cls[i_fc], cds[i_fc]
    if not all(math.isfinite(v) for v in (cl_fc, cd_fc)):
        raise TransonicExtractionError(
            f"{dat}: non-finite coefficients at t={t_snap:g}"
        )

    # surface Cp (compressible normalization off the MEASURED freestream)
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

    # x/c is normalized against the surface's OWN leading edge, not the
    # global origin (Codex V73.A R0 P2: a translated-but-correct mesh must
    # not shift the Cp profile / shock position). The x-extent must agree
    # with the declared chord — a scaled/partial surface is rejected.
    upper3, lower3 = split_surfaces(chain_cp)
    le_true, chord_est = _recover_vertex_chord(upper3, lower3)
    if abs(chord_est - chord) / chord > _CHORD_EST_RTOL:
        raise TransonicExtractionError(
            f"vertex-recovered chord {chord_est:.6g} disagrees with declared "
            f"chord {chord:g} by more than {_CHORD_EST_RTOL:.0%} — geometry/"
            f"chord mismatch (fail-closed; the face-centre compensation is "
            f"bounded by the surface's own end-face lengths, so a clipped or "
            f"mis-scaled surface cannot hide inside it)"
        )
    # x/c anchored at the RECOVERED leading edge and normalized by the
    # recovered chord — no systematic left-shift from the missing LE face
    # segment (Codex R2 P2), no origin dependence (Codex R0 P2)
    upper_cp = [((x - le_true) / chord_est, cp) for x, _z, cp in upper3]
    lower_cp = [((x - le_true) / chord_est, cp) for x, _z, cp in lower3]

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
