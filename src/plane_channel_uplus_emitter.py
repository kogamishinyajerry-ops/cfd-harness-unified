"""DEC-V61-043: plane channel u+/y+ emitter.

Reads the plane_channel case's postProcessing output:
- wallShearStress FO → τ_w/ρ (kinematic; icoFoam operates in kinematic ν)
- uLine sets FO → U(y) profile along a y-line at mid-length

Computes:
- u_τ = sqrt(|τ_w/ρ|)
- y_wall = min(|y - y_bottom|, |y - y_top|)  (half-channel fold)
- y+ = y_wall · u_τ / ν
- u+ = U_x / u_τ

Emits key_quantities aligned with the comparator's G2 schema
(DEC-V61-036c):
- u_mean_profile:        list of u+ values
- u_mean_profile_y_plus: list of matching y+ values
- u_tau:                 scalar
- Re_tau:                u_τ · h / ν
- wall_shear_stress:     scalar kinematic τ_w/ρ

Fail-closed: if the FO output directories are absent (MOCK mode,
legacy runs, case not regenerated) or malformed, the emitter
returns None so the caller's existing fallback path is not shadowed
silently. A returned dict is ALWAYS a complete measurement set.

Reference: Moser 1999 DNS u+/y+ at Re_τ=180, 395, 590. Gold
currently pinned at Re_τ≈180 with points at y+={5, 30, 100}.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


class PlaneChannelEmitterError(Exception):
    """Raised when postProcessing input is present but malformed.

    Distinct from 'inputs absent' — absence is signalled by the emitter
    returning None (caller's decision whether to fall back). Malformed
    inputs fail loudly so fixture corruption is not silently hidden
    (Codex DEC-V61-040 round-2 pattern).
    """


@dataclass(frozen=True)
class PlaneChannelNormalizedProfile:
    u_tau: float
    Re_tau: float
    wall_shear_stress: float  # kinematic τ_w/ρ (m²/s²)
    y_plus: Tuple[float, ...]
    u_plus: Tuple[float, ...]


def _latest_time_dir(parent: Path) -> Optional[Path]:
    """Pick the lexically largest numeric subdirectory (OpenFOAM time
    directories are numeric strings like '0', '10', '50')."""
    if not parent.is_dir():
        return None
    candidates = [p for p in parent.iterdir() if p.is_dir()]
    numeric: List[Tuple[float, Path]] = []
    for p in candidates:
        try:
            numeric.append((float(p.name), p))
        except ValueError:
            continue
    if not numeric:
        return None
    numeric.sort(key=lambda pair: pair[0])
    return numeric[-1][1]


def _read_wall_shear_stress(case_dir: Path) -> Optional[float]:
    """Parse postProcessing/wallShearStress/<t>/wallShearStress.dat.

    OpenFOAM 10 format is a single-row-per-time-step aggregate per
    patch, e.g.:
        # Time          patch      min(Wss)      max(Wss)      ...
        50              walls      (... ... ...) (... ... ...)
    We take the last row (latest time), patch=walls, and use the
    magnitude of the min/max/average 3-vector. Returns the mean of
    |min| and |max| as a patch-representative scalar |τ_w/ρ|.

    Returns None when the file is absent; raises when malformed (key
    CFD evidence path must not fail silently).
    """
    root = case_dir / "postProcessing" / "wallShearStress"
    latest = _latest_time_dir(root)
    if latest is None:
        return None
    dat = latest / "wallShearStress.dat"
    if not dat.is_file():
        return None
    try:
        text = dat.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise PlaneChannelEmitterError(f"cannot read {dat}: {exc}") from exc
    data_rows: List[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        data_rows.append(s)
    if not data_rows:
        raise PlaneChannelEmitterError(
            f"{dat} has no data rows (only comments/blanks)"
        )
    # Take last row — final converged time step.
    last = data_rows[-1]
    # Extract all parenthesized 3-vectors in the row; we want |vec|
    # magnitudes and return their mean as a scalar.
    vecs = _parse_parenthesized_vectors(last)
    if not vecs:
        raise PlaneChannelEmitterError(
            f"{dat} last row has no (x y z) vector tokens: {last!r}"
        )
    mags = [math.sqrt(vx * vx + vy * vy + vz * vz) for vx, vy, vz in vecs]
    # Return the mean magnitude — for a homogeneous channel, min/max/
    # average vectors differ only in shear magnitude; their mean is
    # a robust representative value.
    return sum(mags) / len(mags)


def _parse_parenthesized_vectors(
    line: str,
) -> List[Tuple[float, float, float]]:
    """Find all '(x y z)' 3-vectors in a line."""
    out: List[Tuple[float, float, float]] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "(":
            j = line.find(")", i + 1)
            if j < 0:
                break
            inner = line[i + 1 : j].strip().split()
            if len(inner) == 3:
                try:
                    vx, vy, vz = (float(x) for x in inner)
                    out.append((vx, vy, vz))
                except ValueError:
                    pass
            i = j + 1
        else:
            i += 1
    return out


def _read_uline_profile(
    case_dir: Path,
    set_name: str = "channelCenter",
    field: str = "U",
) -> Optional[List[Tuple[float, float]]]:
    """Parse postProcessing/uLine/<t>/<set_name>_<field>.xy.

    OpenFOAM raw-format line samples for a vector field write:
        y_value  Ux  Uy  Uz
    one row per sample point. We return [(y, Ux)] sorted by y.

    Returns None when the directory/file is absent; raises on malformed
    file contents.
    """
    root = case_dir / "postProcessing" / "uLine"
    latest = _latest_time_dir(root)
    if latest is None:
        return None
    xy = latest / f"{set_name}_{field}.xy"
    if not xy.is_file():
        return None
    try:
        text = xy.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise PlaneChannelEmitterError(f"cannot read {xy}: {exc}") from exc
    rows: List[Tuple[float, float]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        # Vector field: y Ux Uy Uz → 4 columns
        if len(parts) < 2:
            continue
        try:
            y = float(parts[0])
            ux = float(parts[1])
        except ValueError as exc:
            raise PlaneChannelEmitterError(
                f"{xy}: row {s!r} has non-numeric y or Ux"
            ) from exc
        rows.append((y, ux))
    # Codex DEC-V61-043 round-1 FLAG: generator emits nPoints=129 on
    # the line-uniform sampler; accepting <64 rows would silently let
    # a truncated run PASS the sparse-input check. Threshold at 64 is
    # half the default, which allows for any future down-sampled
    # generator variant but rejects gross truncation / corruption.
    MIN_SAMPLES = 64
    if len(rows) < MIN_SAMPLES:
        raise PlaneChannelEmitterError(
            f"{xy} has {len(rows)} sample rows; expected ≥{MIN_SAMPLES} "
            f"(DEC-V61-043 generator emits 129). Truncated / corrupt "
            f"postProcessing output."
        )
    rows.sort(key=lambda r: r[0])
    return rows


def compute_normalized_profile(
    wall_shear_stress: float,  # kinematic τ_w/ρ (m²/s²)
    u_line: Sequence[Tuple[float, float]],  # [(y, Ux)] sorted by y
    *,
    nu: float,
    half_height: float,  # h = D/2 for channel bracketed at y=±h
    y_bottom: Optional[float] = None,
    y_top: Optional[float] = None,
) -> PlaneChannelNormalizedProfile:
    """Convert raw τ_w and U(y) into a u+/y+ profile.

    wall_shear_stress is the kinematic stress τ_w/ρ — icoFoam returns
    this directly. u_tau = sqrt(|τ_w/ρ|); dividing by ρ would be a
    double-normalization (documented here so a future buoyantFoam
    port doesn't accidentally repeat the fix).

    Half-channel fold: for a channel at y ∈ [y_bottom, y_top], each
    cell's wall-distance is the smaller of its distance to either wall.
    We then keep only cells whose y+ ≤ Re_tau (past centerline is
    the reflected half; keeping both would double-count).

    Returns a frozen dataclass with tuples so it can be safely cached.
    """
    if wall_shear_stress <= 0.0:
        raise PlaneChannelEmitterError(
            f"wall_shear_stress must be positive (kinematic τ_w/ρ), "
            f"got {wall_shear_stress}"
        )
    if nu <= 0.0:
        raise PlaneChannelEmitterError(f"nu must be positive, got {nu}")
    if half_height <= 0.0:
        raise PlaneChannelEmitterError(
            f"half_height must be positive, got {half_height}"
        )
    u_tau = math.sqrt(wall_shear_stress)
    Re_tau = u_tau * half_height / nu

    if y_bottom is None:
        y_bottom = min(y for y, _ in u_line)
    if y_top is None:
        y_top = max(y for y, _ in u_line)
    y_center = 0.5 * (y_bottom + y_top)

    # Codex DEC-V61-043 round-1 FLAG: "half-channel fold" means FOLD —
    # map both halves to the same [0, h] space AND either drop one
    # half or average duplicates. Previously we just folded y_wall
    # without deduplicating, so each y_plus value appeared twice
    # (once from the lower half, once from the upper). For a
    # converged run the two halves are symmetric and the duplicates
    # are benign, but a subtly-asymmetric run (upstream effects,
    # mesh asymmetry) would silently let the comparator pick one
    # arbitrary branch. Fix: keep only the LOWER half (y ≤ center),
    # which is standard Moser convention. Upper-half statistics are
    # available via the mirror; if a case ever develops real
    # asymmetry it should emit two separate profiles, not merge.
    y_plus_list: List[float] = []
    u_plus_list: List[float] = []
    for y, ux in u_line:
        # Keep lower half only (y ≤ center). Include the center
        # point exactly once (y_wall = half_height at y = center).
        if y > y_center + 1e-9:
            continue
        y_wall = abs(y - y_bottom)
        if y_wall > half_height * 1.0000001:
            continue
        yp = y_wall * u_tau / nu
        up = ux / u_tau
        y_plus_list.append(yp)
        u_plus_list.append(up)

    # Sort by y+ ascending for predictable comparator alignment.
    pairs = sorted(zip(y_plus_list, u_plus_list), key=lambda p: p[0])
    y_plus_tuple = tuple(p[0] for p in pairs)
    u_plus_tuple = tuple(p[1] for p in pairs)
    return PlaneChannelNormalizedProfile(
        u_tau=u_tau,
        Re_tau=Re_tau,
        wall_shear_stress=wall_shear_stress,
        y_plus=y_plus_tuple,
        u_plus=u_plus_tuple,
    )


def emit_uplus_profile(
    case_dir: Path,
    *,
    nu: float,
    half_height: float,
) -> Optional[Dict[str, object]]:
    """End-to-end: read FO output, normalize, emit key_quantities.

    Returns a dict ready to merge into key_quantities, or None when
    FO output is absent (so caller can fall back to scalar U_max path).
    Malformed FO output raises PlaneChannelEmitterError — corruption
    must surface, not silently degrade.
    """
    tau_w = _read_wall_shear_stress(case_dir)
    u_line = _read_uline_profile(case_dir)
    # Codex DEC-V61-043 round-1 BLOCKER: treat partial FO output as
    # corruption, not absence. If *both* inputs are missing (MOCK run,
    # legacy fixture, case not regenerated), return None so the caller
    # can fall back cleanly. If only one is missing, the run emitted
    # half the required evidence — fail loud so the comparator sees
    # MISSING_TARGET_QUANTITY instead of a silent cell-centre fallback.
    if tau_w is None and u_line is None:
        return None
    if tau_w is None:
        raise PlaneChannelEmitterError(
            "plane_channel postProcessing corruption: uLine output "
            "present but wallShearStress output absent — expected both "
            "from the DEC-V61-043 controlDict functions{} block."
        )
    if u_line is None:
        raise PlaneChannelEmitterError(
            "plane_channel postProcessing corruption: wallShearStress "
            "output present but uLine output absent — expected both "
            "from the DEC-V61-043 controlDict functions{} block."
        )

    profile = compute_normalized_profile(
        wall_shear_stress=tau_w,
        u_line=u_line,
        nu=nu,
        half_height=half_height,
    )

    return {
        "u_mean_profile": list(profile.u_plus),
        "u_mean_profile_y_plus": list(profile.y_plus),
        "u_tau": profile.u_tau,
        "Re_tau": profile.Re_tau,
        "wall_shear_stress": profile.wall_shear_stress,
        "u_mean_profile_source": "wallShearStress_fo_v1",
    }
