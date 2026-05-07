"""DEC-V61-155 (N5.4) · centerline CSV + 2x2 grid SVG exporter tests.

Coverage:
  * CSV header row reflects sorted union of field keys
  * CSV value formatting (fixed-point, scientific, 0.0 → "0")
  * CSV RFC-4180 quoting helper handles commas/quotes/newlines
  * CSV missing field for some samples → empty cell
  * CSV byte-reproducibility
  * SVG header + viewBox + 2x2 layout
  * SVG truncates extra panels (>4); missing cells emit placeholder
  * SVG embeds PNG via data: URL when png_bytes provided
  * SVG raises on non-positive width/height
  * SVG XML escapes title content
  * SVG byte-reproducibility
  * V130 advisory-only contract
"""
from __future__ import annotations

import base64

import pytest

from ui.backend.services.case_export import (
    CenterlineSample,
    GridPanel,
    centerline_csv,
    grid_svg,
)


# ────────── CSV ──────────


def test_csv_empty_input_returns_header_only():
    assert centerline_csv([]) == "position\n"


def test_csv_header_is_sorted_union_of_field_keys():
    samples = [
        CenterlineSample(position=0.0, fields={"U_x": 1.0, "p": 0.5}),
        CenterlineSample(position=1.0, fields={"U_y": 0.0}),
    ]
    out = centerline_csv(samples)
    header = out.splitlines()[0]
    assert header == "position,U_x,U_y,p"


def test_csv_missing_field_renders_empty_cell():
    samples = [
        CenterlineSample(position=0.0, fields={"U_x": 1.0}),
        CenterlineSample(position=1.0, fields={"U_y": 0.5}),
    ]
    out = centerline_csv(samples)
    rows = out.splitlines()
    # Header: position,U_x,U_y (sorted union)
    assert rows[0] == "position,U_x,U_y"
    # First row has U_x but no U_y → trailing empty cell
    assert rows[1] == "0,1,"
    # Second row has U_y but no U_x → empty in middle
    assert rows[2] == "1,,0.5"


def test_csv_value_formatting_fixed_and_scientific():
    samples = [
        CenterlineSample(position=0.5, fields={"x": 0.001}),
        CenterlineSample(position=2.0, fields={"x": 1e-8}),
    ]
    out = centerline_csv(samples)
    assert "0.001" in out
    assert "1.000000e-08" in out


def test_csv_zero_renders_as_short_zero():
    samples = [CenterlineSample(position=0.0, fields={"u": 0.0})]
    out = centerline_csv(samples)
    assert out.splitlines()[1] == "0,0"


def test_csv_rfc4180_escape_helper():
    from ui.backend.services.case_export.csv_exporter import (
        _escape_csv_field,
    )

    assert _escape_csv_field("plain") == "plain"
    assert _escape_csv_field("a,b") == '"a,b"'
    assert _escape_csv_field('a"b') == '"a""b"'
    assert _escape_csv_field("a\nb") == '"a\nb"'


def test_csv_byte_reproducibility():
    samples = [
        CenterlineSample(position=0.0, fields={"U": 1.0, "p": 0.0}),
        CenterlineSample(position=1.0, fields={"p": 0.5, "U": 0.0}),
    ]
    assert centerline_csv(samples) == centerline_csv(samples)


# ────────── SVG ──────────


def test_svg_emits_xmlns_and_viewbox():
    out = grid_svg([], width=1200, height=900)
    assert 'xmlns="http://www.w3.org/2000/svg"' in out
    assert 'viewBox="0 0 1200 900"' in out


def test_svg_2x2_layout_at_default_size():
    panels = [GridPanel(title=f"P{i}", png_bytes=None) for i in range(4)]
    out = grid_svg(panels)
    assert out.count("<g transform=") == 4
    assert 'transform="translate(0 0)"' in out
    assert 'transform="translate(600 0)"' in out
    assert 'transform="translate(0 450)"' in out
    assert 'transform="translate(600 450)"' in out


def test_svg_truncates_extra_panels_above_four():
    panels = [GridPanel(title=f"P{i}", png_bytes=None) for i in range(7)]
    out = grid_svg(panels)
    assert out.count("<g transform=") == 4


def test_svg_missing_cells_get_no_figure_placeholder():
    out = grid_svg([GridPanel(title="A", png_bytes=None)])
    assert "(no figure)" in out


def test_svg_embeds_png_via_data_url():
    panels = [GridPanel(title="A", png_bytes=b"PNG_BYTES_RAW")]
    out = grid_svg(panels)
    assert "data:image/png;base64," in out
    expected_b64 = base64.b64encode(b"PNG_BYTES_RAW").decode("ascii")
    assert expected_b64 in out


def test_svg_raises_on_non_positive_dimensions():
    with pytest.raises(ValueError):
        grid_svg([], width=0, height=900)
    with pytest.raises(ValueError):
        grid_svg([], width=1200, height=-1)


def test_svg_xml_escapes_title():
    panels = [GridPanel(title="A & <B>", png_bytes=None)]
    out = grid_svg(panels)
    assert "A &amp; &lt;B&gt;" in out
    assert "<B>" not in out


def test_svg_byte_reproducibility():
    panels = [
        GridPanel(title="A", png_bytes=b"x"),
        GridPanel(title="B", png_bytes=None),
    ]
    assert grid_svg(panels) == grid_svg(panels)


# ────────── V130 advisory-only ──────────


def test_case_export_not_in_known_mutation_functions():
    from ui.backend.services.ai_actions.mutating_routes import (
        KNOWN_MUTATION_FUNCTIONS,
    )

    for module, _ in KNOWN_MUTATION_FUNCTIONS:
        assert "case_export" not in module
