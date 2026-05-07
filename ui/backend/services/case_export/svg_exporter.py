"""DEC-V61-155 (N5.4) · 2×2 figure grid SVG exporter.

Pure function rendering a 2×2 grid of figures as a minimal SVG
document. v0 emits a layout SVG with embedded PNG images via
`<image href="data:image/png;base64,...">`. This satisfies the
charter §4-question-gate Q4 ("format converters") for cases where
the engineer wants a vector-wrapper for screenshots.

Wire shape:

    GridPanel(title: str, png_bytes: bytes | None, alt_text: str)
        title is the panel header (rendered as <text>).
        png_bytes is the embedded raster (None = empty placeholder).
        alt_text is the SVG <desc> for accessibility.

Out of scope for N5.4 v0:
  * True vector rendering (path-based field plots) — requires
    matplotlib SVG backend integration; defer to N5-extend.
  * Custom panel arrangement beyond 2×2 — defer.
  * Theme / styling beyond default sans-serif — defer.

Byte-reproducibility: panel order is the input list order; no
wall-clock timestamps; base64 encoding of png_bytes is deterministic.
Same input → identical SVG bytes.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass(frozen=True)
class GridPanel:
    title: str
    png_bytes: bytes | None
    alt_text: str = ""


def grid_svg(
    panels: list[GridPanel],
    *,
    width: int = 1200,
    height: int = 900,
) -> str:
    """Render a 2×2 grid SVG. Accepts up to 4 panels — extras are
    truncated; fewer panels leave the missing cells empty."""
    if width <= 0 or height <= 0:
        raise ValueError(
            f"width and height must be positive (got {width}x{height})"
        )
    panels = list(panels)[:4]
    half_w = width // 2
    half_h = height // 2
    title_band = 30  # px reserved for panel title
    image_y_offset = title_band

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        'font-family="sans-serif">'
    )
    lines.append(
        '  <desc>2x2 figure grid · DEC-V61-155 N5.4 export</desc>'
    )
    # 4 cells: (0,0), (1,0), (0,1), (1,1) — row-major fill order so
    # caller's panel[0] lands top-left.
    cell_indices = [
        (0, 0), (1, 0), (0, 1), (1, 1),
    ]
    for idx, (col, row) in enumerate(cell_indices):
        if idx >= len(panels):
            break
        panel = panels[idx]
        x = col * half_w
        y = row * half_h
        lines.append(
            f'  <g transform="translate({x} {y})">'
        )
        lines.append(
            f'    <rect width="{half_w}" height="{half_h}" '
            'fill="none" stroke="#666" stroke-width="1"/>'
        )
        # Title band.
        lines.append(
            f'    <text x="{half_w // 2}" y="20" text-anchor="middle" '
            f'font-size="14" fill="#222">{_escape_xml(panel.title)}</text>'
        )
        # Embedded image (when png_bytes provided).
        if panel.png_bytes:
            b64 = base64.b64encode(panel.png_bytes).decode("ascii")
            lines.append(
                f'    <image x="0" y="{image_y_offset}" '
                f'width="{half_w}" height="{half_h - image_y_offset}" '
                f'href="data:image/png;base64,{b64}" '
                f'><title>{_escape_xml(panel.alt_text)}</title></image>'
            )
        else:
            # Empty placeholder text.
            lines.append(
                f'    <text x="{half_w // 2}" y="{half_h // 2}" '
                'text-anchor="middle" font-size="12" fill="#999">'
                '(no figure)</text>'
            )
        lines.append('  </g>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def _escape_xml(value: str) -> str:
    """Minimal XML escaping for SVG text + title content."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


__all__ = ["GridPanel", "grid_svg"]
