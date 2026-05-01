"""Read the final time directory's U field, compute summary statistics.

Phase-1A scope: numerical summary (cell count, |U| min/max/mean, mean
Ux for recirculation sanity). Future Phase-1C will add a midplane
slice glb so the UI viewport can render the velocity field.

Not using OpenFOAM's ``postProcess`` utility because the parsed-on-
host approach (a) avoids a second container round-trip, (b) gives us
direct numpy-style access to the field array for the UI's plot, and
(c) doesn't require staging back into the container.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


class ResultsExtractError(RuntimeError):
    """Raised when the final time directory is missing or U file is
    malformed."""


@dataclass(frozen=True, slots=True)
class ResultsSummary:
    case_id: str
    final_time: float
    cell_count: int
    u_magnitude_min: float
    u_magnitude_max: float
    u_magnitude_mean: float
    u_x_mean: float
    u_x_min: float
    u_x_max: float
    is_recirculating: bool


def _list_time_directories(case_dir: Path) -> list[float]:
    """Return all numeric subdirectories sorted ascending. Excludes
    '0' if there are higher-numbered ones (we want the SOLUTION time,
    not the initial condition)."""
    out: list[float] = []
    for entry in case_dir.iterdir():
        if not entry.is_dir():
            continue
        try:
            out.append(float(entry.name))
        except ValueError:
            continue
    return sorted(out)


def _parse_internal_field(u_path: Path) -> list[tuple[float, float, float]]:
    """Parse a volVectorField's nonuniform internalField list.

    Format:
        internalField   nonuniform List<vector>
        N
        (
        (ux uy uz)
        (ux uy uz)
        ...
        )
        ;
    """
    text = u_path.read_text()
    m = re.search(
        r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\n\(\s*\n",
        text,
    )
    if not m:
        # Could be a uniform field (rare for icoFoam output but possible
        # at t=0). Handle: ``internalField  uniform (a b c);``
        m_uni = re.search(
            r"internalField\s+uniform\s+\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+"
            r"([-0-9.eE+]+)\)\s*;",
            text,
        )
        if m_uni:
            return [
                (
                    float(m_uni.group(1)),
                    float(m_uni.group(2)),
                    float(m_uni.group(3)),
                )
            ]
        raise ResultsExtractError(
            f"internalField in {u_path} is neither nonuniform List<vector> "
            "nor uniform (a b c) — unrecognized format."
        )
    n = int(m.group(1))
    body_start = m.end()
    body_end = text.index("\n)", body_start)
    body = text[body_start:body_end]

    # Detect divergence-to-NaN explicitly so callers can distinguish
    # "solver wrote a corrupt file" from "solver diverged". OpenFOAM
    # writes ``(nan nan -nan)`` (or ``(inf inf -inf)``) per cell when
    # the residuals blow up; the float-only regex below would silently
    # discard these lines and the count check would then fire with a
    # confusing "0 entries but declared N" message that hides the real
    # cause. Surface the divergence directly.
    nan_inf_count = sum(
        1 for line in body.splitlines()
        if line.strip() and re.search(r"\b(?:nan|-nan|inf|-inf)\b", line.lower())
    )
    if nan_inf_count > 0:
        raise ResultsExtractError(
            f"U field at {u_path} contains {nan_inf_count} NaN/Inf entries — "
            "solver diverged to non-finite values. Re-run with smaller dt, "
            "tighter relaxation factors, or different initial conditions."
        )

    vels: list[tuple[float, float, float]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        mm = re.match(
            r"\(([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\)", line
        )
        if mm:
            vels.append(
                (
                    float(mm.group(1)),
                    float(mm.group(2)),
                    float(mm.group(3)),
                )
            )
    if len(vels) != n:
        raise ResultsExtractError(
            f"U field has {len(vels)} entries but declared {n} in {u_path}"
        )
    return vels


def extract_results_summary(
    case_dir: Path, *, case_id: str
) -> ResultsSummary:
    """Read the U field from the highest-numbered time directory and
    compute summary statistics.

    Raises :class:`ResultsExtractError` if no solution time directory
    exists (only ``0/``) or the U field is malformed.
    """
    if not case_dir.is_dir():
        raise ResultsExtractError(f"case dir not found: {case_dir}")

    times = _list_time_directories(case_dir)
    if len(times) <= 1:
        raise ResultsExtractError(
            f"only initial condition (0/) exists in {case_dir} — "
            "icoFoam hasn't run yet."
        )
    # Highest non-zero time directory.
    final_time = max(t for t in times if t > 0)
    final_dir = case_dir / (
        f"{int(final_time)}" if final_time == int(final_time) else f"{final_time}"
    )
    # OpenFOAM writes time-directory names with the same precision as
    # ``timePrecision`` in controlDict (default 6, but the integer
    # cases drop to "1", "2", etc.). Try both forms.
    if not final_dir.is_dir():
        candidates = [
            d for d in case_dir.iterdir()
            if d.is_dir() and d.name not in ("0", "constant", "system")
        ]
        if not candidates:
            raise ResultsExtractError(
                f"no solution time directory under {case_dir}"
            )
        final_dir = max(candidates, key=lambda p: float(p.name))
        final_time = float(final_dir.name)

    u_path = final_dir / "U"
    if not u_path.is_file():
        raise ResultsExtractError(
            f"U field not found at {u_path} — solver may have failed mid-run."
        )

    vels = _parse_internal_field(u_path)
    n = len(vels)
    mags = [math.sqrt(u * u + v * v + w * w) for u, v, w in vels]
    uxs = [v[0] for v in vels]

    u_mag_min = min(mags)
    u_mag_max = max(mags)
    u_mag_mean = sum(mags) / n
    u_x_mean = sum(uxs) / n
    u_x_min = min(uxs)
    u_x_max = max(uxs)

    # LDC sanity: a converged steady state has near-zero mean Ux
    # (recirculating vortex balances itself). We accept anything within
    # 5% of the lid speed as "recirculating" (vs. e.g. plug flow which
    # would have Ux ≈ U_lid throughout).
    is_recirculating = abs(u_x_mean) < 0.05 and u_x_min < -0.05 < u_x_max

    return ResultsSummary(
        case_id=case_id,
        final_time=final_time,
        cell_count=n,
        u_magnitude_min=u_mag_min,
        u_magnitude_max=u_mag_max,
        u_magnitude_mean=u_mag_mean,
        u_x_mean=u_x_mean,
        u_x_min=u_x_min,
        u_x_max=u_x_max,
        is_recirculating=is_recirculating,
    )
