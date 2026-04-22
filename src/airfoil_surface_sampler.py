"""DEC-V61-044: NACA airfoil surface Cp sampler.

Reads postProcessing/airfoilSurface/<t>/p_aerofoil.raw (emitted by the
`surfaces` FO with `type patch; patches (aerofoil)`), which contains one
row per face of the aerofoil patch:

    # x y z p
    0.001  0.001  0.006  -0.02
    0.001 -0.001  0.006  -0.02
    ...

Normalizes to Cp = (p - p_inf) / (0.5·rho·U_inf²) and splits into upper
(z > 0) and lower (z < 0) surfaces. Deduplicates y-axis spanwise
duplicates introduced by the thin 2D mesh (y=±0.001 produces two faces
with identical (x, z, p)) by rounding y to zero.

Critical: the patch name is British spelling `aerofoil` — matches the
blockMesh boundary block at foam_agent_adapter.py:~5923. Any file
lookup must use this exact spelling or the surfaces FO output goes to
a different filename and this parser sees nothing.

Trailing-edge degeneracy: NACA0012 half-thickness collapses to zero at
x/c=1. Faces there have z≈0 → `side` labeling becomes ambiguous. We
tag x/c > 0.995 as side="trailing_edge" (merged), keeping genuine
upper/lower distinction only in the aerodynamically-meaningful range.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AirfoilSurfaceSamplerError(Exception):
    """Raised when postProcessing input is present but malformed.

    Absence is signalled by returning None so the caller can fall back
    to the legacy volume-cell band-averaging path. Corruption fails
    loudly so fixture drift is not silently hidden (Codex DEC-V61-040
    round-2 pattern).
    """


@dataclass(frozen=True)
class CpPoint:
    x_over_c: float
    Cp: float
    side: str  # "upper" | "lower" | "trailing_edge"


def _latest_time_dir(parent: Path) -> Optional[Path]:
    if not parent.is_dir():
        return None
    numeric: List[Tuple[float, Path]] = []
    for p in parent.iterdir():
        if not p.is_dir():
            continue
        try:
            numeric.append((float(p.name), p))
        except ValueError:
            continue
    if not numeric:
        return None
    numeric.sort(key=lambda pair: pair[0])
    return numeric[-1][1]


def read_patch_raw(
    case_dir: Path,
    fo_name: str = "airfoilSurface",
    surface_name: str = "aerofoil",
    field: str = "p",
) -> Optional[List[Tuple[float, float, float, float]]]:
    """Parse postProcessing/<fo_name>/<t>/<field>_<surface_name>.raw.

    OpenFOAM 10 `surfaceFormat raw` writes:
        # x y z <field>
        0.001 0.001 0.0062 -0.02
        ...

    Returns list of (x, y, z, field_value) rows, or None when the
    expected directory/file is absent (MOCK run, legacy fixture, case
    not regenerated). Raises AirfoilSurfaceSamplerError on malformed
    file contents — we do not want silent corruption in the audit path.
    """
    root = case_dir / "postProcessing" / fo_name
    latest = _latest_time_dir(root)
    if latest is None:
        return None
    # OpenFOAM 10 surfaces FO output filename is <field>_<surface>.raw.
    raw = latest / f"{field}_{surface_name}.raw"
    if not raw.is_file():
        return None
    try:
        text = raw.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise AirfoilSurfaceSamplerError(
            f"cannot read {raw}: {exc}"
        ) from exc
    rows: List[Tuple[float, float, float, float]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 4:
            raise AirfoilSurfaceSamplerError(
                f"{raw}:{lineno}: expected 4 columns (x y z {field}), "
                f"got {len(parts)}: {s!r}"
            )
        try:
            x, y, z, fv = (float(parts[i]) for i in range(4))
        except ValueError as exc:
            raise AirfoilSurfaceSamplerError(
                f"{raw}:{lineno}: non-numeric field in {s!r}"
            ) from exc
        rows.append((x, y, z, fv))
    if not rows:
        raise AirfoilSurfaceSamplerError(
            f"{raw} has no data rows (only comments/blanks)"
        )
    return rows


def compute_cp(
    points: List[Tuple[float, float, float, float]],
    *,
    chord: float,
    U_inf: float,
    rho: float = 1.0,
    p_inf: float = 0.0,
    trailing_edge_x_over_c: float = 0.995,
    y_dedup_round: int = 6,
) -> List[CpPoint]:
    """Convert raw (x, y, z, p) face samples into a Cp(x/c) profile.

    Steps:
    1. Normalize: x_over_c = x / chord; Cp = (p - p_inf) / (0.5·rho·U_inf²).
    2. Deduplicate spanwise (thin-2D mesh has faces at y=±0.001 with
       identical (x, z, p) — by rounding y to 0, duplicates collapse to
       a single (x_over_c, Cp) pair via a dict keyed on (x, z_sign)).
    3. Split by z: upper (z>0), lower (z<0), trailing_edge (x/c > 0.995).

    Returns a list of CpPoint sorted by (side, x_over_c) ascending.

    Raises AirfoilSurfaceSamplerError on invalid params (zero chord /
    U_inf / negative rho). Empty points list returns [].
    """
    if chord <= 0.0:
        raise AirfoilSurfaceSamplerError(f"chord must be positive, got {chord}")
    if U_inf == 0.0:
        raise AirfoilSurfaceSamplerError(f"U_inf must be nonzero, got {U_inf}")
    if rho <= 0.0:
        raise AirfoilSurfaceSamplerError(f"rho must be positive, got {rho}")

    q_ref = 0.5 * rho * U_inf * U_inf
    # Dedup map: key = (round(x, 6), round(z, 6)) → average p over span.
    # Using a dict keeps the first-seen, averaging avoids bias if the
    # spanwise faces disagree (they shouldn't for 2D steady, but this is
    # cheap insurance).
    bucket: Dict[Tuple[float, float], List[float]] = {}
    for x, y, z, p in points:
        key = (round(x, y_dedup_round), round(z, y_dedup_round))
        bucket.setdefault(key, []).append(p)

    cp_points: List[CpPoint] = []
    for (x, z), ps in bucket.items():
        p_mean = sum(ps) / len(ps)
        x_over_c = x / chord
        Cp = (p_mean - p_inf) / q_ref
        if x_over_c > trailing_edge_x_over_c:
            side = "trailing_edge"
        elif z > 0.0:
            side = "upper"
        elif z < 0.0:
            side = "lower"
        else:
            # z == 0 exactly (leading edge cap on projected OBJ) — treat
            # as a shared point, emit once labelled "trailing_edge" only
            # if also at x/c≈1; otherwise "upper" (arbitrary choice for
            # the leading-edge stagnation point — Cp there is ≈1 on both
            # sides by symmetry so the label is cosmetic).
            side = "upper"
        cp_points.append(CpPoint(x_over_c=x_over_c, Cp=Cp, side=side))

    # Sort deterministically: side priority upper → lower → trailing_edge,
    # then by x_over_c ascending.
    side_rank = {"upper": 0, "lower": 1, "trailing_edge": 2}
    cp_points.sort(key=lambda p: (side_rank.get(p.side, 99), p.x_over_c))
    return cp_points


def emit_cp_profile(
    case_dir: Path,
    *,
    chord: float,
    U_inf: float,
    rho: float = 1.0,
    p_inf: float = 0.0,
) -> Optional[Dict[str, object]]:
    """End-to-end: read postProcessing output, compute Cp, emit
    key_quantities aligned with the comparator's profile schema.

    Returns a dict ready to merge into key_quantities with keys:
    - pressure_coefficient:         list of Cp floats (upper surface
                                    only, sorted by x/c — matches gold
                                    reference_values shape at AoA=0)
    - pressure_coefficient_x:       matching x/c values (axis column)
    - pressure_coefficient_profile: full [{x_over_c, Cp, side}] list
                                    for audit package / plots
    - pressure_coefficient_source:  "surface_fo_direct"

    Returns None when postProcessing/airfoilSurface is absent; raises
    on malformed input. Upper-surface-only primary profile matches
    the gold schema (AoA=0 symmetric) but the full profile is
    preserved for downstream consumers.
    """
    rows = read_patch_raw(case_dir)
    if rows is None:
        return None
    cp_points = compute_cp(
        rows,
        chord=chord,
        U_inf=U_inf,
        rho=rho,
        p_inf=p_inf,
    )
    if not cp_points:
        raise AirfoilSurfaceSamplerError(
            "surface sampler parsed postProcessing but produced zero Cp "
            "points — likely aerofoil patch emitted no faces. Verify "
            "blockMesh patch naming (British spelling `aerofoil`)."
        )
    # Build the gold-aligned scalar list (upper surface only, AoA=0 gold
    # assumes symmetric so upper ≈ lower; keeping upper preserves the
    # stagnation Cp=1 anchor). Downstream comparator uses
    # pressure_coefficient_x as the axis column.
    upper = [p for p in cp_points if p.side == "upper"]
    upper.sort(key=lambda p: p.x_over_c)
    return {
        "pressure_coefficient": [p.Cp for p in upper],
        "pressure_coefficient_x": [p.x_over_c for p in upper],
        "pressure_coefficient_profile": [
            {"x_over_c": p.x_over_c, "Cp": p.Cp, "side": p.side}
            for p in cp_points
        ],
        "pressure_coefficient_source": "surface_fo_direct",
    }
