"""Render the icoFoam residual history as a line chart PNG.

Parses ``log.icoFoam`` for the per-iteration "Initial residual" values
on Ux / Uy / Uz / p, then plots them on a log-scale y-axis vs
iteration index. Hand-rolled with Pillow — no matplotlib.
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class ResidualChartError(RuntimeError):
    """Raised when log.icoFoam is missing or has no parseable residual lines."""


_TIME_LINE = re.compile(r"^Time\s*=\s*([0-9.eE+-]+)s?\s*$", re.MULTILINE)
# Solver prefix is permissive ([A-Za-z]+) so we match icoFoam's
# default smoothSolver + DICPCG AND pimpleFoam's GAMG / PBiCGStab
# alternates. Codex af9579e round-3 P3 closure 2026-04-30 — kept
# in sync with solver_runner._RES_U_LINE / _RES_P_LINE.
_RES_U = re.compile(
    r"[A-Za-z]+:\s+Solving for U([xyz]),\s+Initial residual\s*=\s*"
    r"([0-9.eE+-]+),"
)
_RES_P = re.compile(
    r"[A-Za-z]+:\s+Solving for p,\s+Initial residual\s*=\s*([0-9.eE+-]+),"
)


_IMAGE_SIZE = (640, 360)
_PADDING_LEFT = 60
_PADDING_RIGHT = 130  # legend room
_PADDING_TOP = 30
_PADDING_BOTTOM = 40

_BG = (12, 14, 22)
_AXIS = (160, 165, 180)
_GRID = (40, 44, 56)
_TEXT = (220, 225, 235)
_COLOR_U = {
    "x": (96, 165, 250),  # blue
    "y": (250, 204, 21),  # amber
    "z": (167, 139, 250),  # violet
}
_COLOR_P = (52, 211, 153)  # emerald


def _parse_log(log_text: str) -> dict[str, list[tuple[int, float]]]:
    """Return {series_name: [(iteration_index, residual), ...]}.

    icoFoam emits residuals in time-step blocks. We iterate by time
    step (each ``Time = ...`` line increments the step counter) and
    capture the FIRST initial-residual per quantity within that block.
    PISO emits multiple p iterations per step (nCorrectors * nNonOrth
    + something); we pick the first as a representative for the
    timestep.
    """
    series: dict[str, list[tuple[int, float]]] = {
        "Ux": [],
        "Uy": [],
        "Uz": [],
        "p": [],
    }

    # Split log into per-time-step chunks.
    # Each "Time = T" begins a new chunk.
    chunks: list[str] = []
    last_pos = 0
    matches = list(_TIME_LINE.finditer(log_text))
    for i, m in enumerate(matches):
        chunks.append(
            log_text[m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(log_text)]
        )
        last_pos = m.end()
    if not chunks:
        return series

    for step_idx, chunk in enumerate(chunks, start=1):
        # Each U component has exactly one solve per timestep (icoFoam
        # uses smoothSolver which doesn't iterate). Capture the first
        # match per component.
        u_seen: set[str] = set()
        for m in _RES_U.finditer(chunk):
            comp = m.group(1)
            if comp in u_seen:
                continue
            u_seen.add(comp)
            series[f"U{comp}"].append((step_idx, float(m.group(2))))
            if u_seen >= {"x", "y", "z"}:
                break
        # PISO solves p multiple times per timestep: nCorrectors *
        # (1 + nNonOrthogonalCorrectors) outer×inner iterations. The
        # FIRST has the highest initial residual (gradient at the
        # current state); the LAST has the lowest (post-correction).
        # The convergence-tracking value is the LAST one — that's
        # what the user sees as "p has settled" at steady state.
        p_matches = list(_RES_P.finditer(chunk))
        if p_matches:
            series["p"].append((step_idx, float(p_matches[-1].group(1))))

    return series


def _log10_safe(v: float) -> float:
    """log10 with a floor to avoid -inf for zero residuals."""
    return math.log10(max(v, 1.0e-12))


def _draw_axes(draw: ImageDraw.ImageDraw, font, x_max: int, y_min_log: float, y_max_log: float) -> None:
    # Axis box
    box = (
        _PADDING_LEFT,
        _PADDING_TOP,
        _IMAGE_SIZE[0] - _PADDING_RIGHT,
        _IMAGE_SIZE[1] - _PADDING_BOTTOM,
    )
    draw.rectangle(box, outline=_AXIS, width=1)

    # Y gridlines + labels at integer log decades
    for log_y in range(int(math.ceil(y_min_log)), int(math.floor(y_max_log)) + 1):
        y_frac = (log_y - y_min_log) / (y_max_log - y_min_log)
        py = _PADDING_TOP + (1 - y_frac) * (_IMAGE_SIZE[1] - _PADDING_TOP - _PADDING_BOTTOM)
        draw.line(
            [(_PADDING_LEFT + 1, py), (_IMAGE_SIZE[0] - _PADDING_RIGHT - 1, py)],
            fill=_GRID,
        )
        draw.text(
            (8, py - 6),
            f"1e{log_y:+d}",
            fill=_TEXT,
            font=font,
        )

    # X gridlines at every ~80 iterations
    if x_max > 0:
        step = max(1, x_max // 5)
        for x_iter in range(0, x_max + 1, step):
            x_frac = x_iter / x_max if x_max > 0 else 0
            px = (
                _PADDING_LEFT
                + x_frac * (_IMAGE_SIZE[0] - _PADDING_LEFT - _PADDING_RIGHT)
            )
            draw.line(
                [(px, _PADDING_TOP + 1), (px, _IMAGE_SIZE[1] - _PADDING_BOTTOM - 1)],
                fill=_GRID,
            )
            draw.text(
                (px - 10, _IMAGE_SIZE[1] - _PADDING_BOTTOM + 4),
                str(x_iter),
                fill=_TEXT,
                font=font,
            )

    # Axis titles
    draw.text(
        (_IMAGE_SIZE[0] // 2 - 40, _IMAGE_SIZE[1] - 16),
        "iteration (timestep)",
        fill=_TEXT,
        font=font,
    )
    draw.text(
        (4, _PADDING_TOP - 16),
        "Initial residual (log scale)",
        fill=_TEXT,
        font=font,
    )


def _draw_series(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, float]],
    color: tuple[int, int, int],
    x_max: int,
    y_min_log: float,
    y_max_log: float,
) -> None:
    if not points:
        return
    plot_w = _IMAGE_SIZE[0] - _PADDING_LEFT - _PADDING_RIGHT
    plot_h = _IMAGE_SIZE[1] - _PADDING_TOP - _PADDING_BOTTOM

    pixels: list[tuple[float, float]] = []
    for it, val in points:
        x_frac = it / x_max if x_max > 0 else 0
        log_v = _log10_safe(val)
        y_frac = (log_v - y_min_log) / (y_max_log - y_min_log) if y_max_log > y_min_log else 0
        px = _PADDING_LEFT + x_frac * plot_w
        py = _PADDING_TOP + (1 - y_frac) * plot_h
        pixels.append((px, py))
    if len(pixels) >= 2:
        draw.line(pixels, fill=color, width=2)


def render_residual_chart_png(case_dir: Path) -> bytes:
    """Read ``log.icoFoam`` and render the residual history.

    Raises :class:`ResidualChartError` if the log is missing or has no
    parseable residual lines.
    """
    log_path = case_dir / "log.icoFoam"
    if not log_path.is_file():
        raise ResidualChartError(
            f"no log.icoFoam at {log_path} — run the solver first."
        )
    text = log_path.read_text(errors="replace")
    series = _parse_log(text)
    if not any(series.values()):
        raise ResidualChartError(
            "log.icoFoam has no parseable residual lines — solver may "
            "have crashed before the first time step."
        )

    img = Image.new("RGB", _IMAGE_SIZE, _BG)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = None

    # Find ranges
    all_vals = [v for s in series.values() for _, v in s]
    if not all_vals:
        raise ResidualChartError("no residual values in log")
    y_max_log = math.ceil(_log10_safe(max(all_vals)))
    y_min_log = math.floor(_log10_safe(min(all_vals)))
    if y_max_log == y_min_log:
        y_max_log += 1
    x_max = max(it for s in series.values() for it, _ in s)

    _draw_axes(draw, font, x_max, y_min_log, y_max_log)

    for comp, color in _COLOR_U.items():
        _draw_series(draw, series[f"U{comp}"], color, x_max, y_min_log, y_max_log)
    _draw_series(draw, series["p"], _COLOR_P, x_max, y_min_log, y_max_log)

    # Legend
    legend_x = _IMAGE_SIZE[0] - _PADDING_RIGHT + 10
    for i, (label, color) in enumerate(
        [
            ("Ux", _COLOR_U["x"]),
            ("Uy", _COLOR_U["y"]),
            ("Uz", _COLOR_U["z"]),
            ("p", _COLOR_P),
        ]
    ):
        ly = _PADDING_TOP + 14 + i * 18
        draw.line([(legend_x, ly), (legend_x + 22, ly)], fill=color, width=3)
        draw.text((legend_x + 28, ly - 6), label, fill=_TEXT, font=font)

    final_p = series["p"][-1] if series["p"] else (0, float("nan"))
    draw.text(
        (legend_x, _IMAGE_SIZE[1] - _PADDING_BOTTOM - 4),
        f"final p init: {final_p[1]:.2e}",
        fill=_TEXT,
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
