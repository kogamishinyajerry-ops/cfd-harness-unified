"""DEC-V61-155 (N5.4) · centerline CSV exporter.

Pure function rendering centerline samples as CSV. RFC 4180 quoting
for safety — field values containing commas, quotes, or newlines are
properly escaped.

Wire shape:

    CenterlineSample(position: float, fields: dict[str, float])
        position is a scalar (e.g. arc-length along centerline).
        fields is the per-field value at that position
        (e.g. {"U_x": 0.5, "U_y": 0.0, "p": 0.1}).

Header row is the union of all sample.fields keys, sorted
alphabetically for stability.

Byte-reproducibility: the writer guarantees stable column order
(sorted) + Unix line endings ('\\n') so two runs against the same
samples produce identical CSV bytes. Engineers diffing CSV output
across runs see only real value changes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CenterlineSample:
    position: float
    fields: dict[str, float]


def centerline_csv(samples: list[CenterlineSample]) -> str:
    """Render samples as RFC-4180 CSV. Returns a UTF-8 string.

    Empty input returns "position\\n" (header only).
    """
    if not samples:
        return "position\n"

    # Column order: position first, then fields sorted by name.
    field_keys = sorted({k for s in samples for k in s.fields})
    header = ["position", *field_keys]
    lines = [_csv_row(header)]
    for sample in samples:
        row = [_format_number(sample.position)]
        for key in field_keys:
            if key in sample.fields:
                row.append(_format_number(sample.fields[key]))
            else:
                row.append("")  # missing field for this sample
        lines.append(_csv_row(row))
    return "\n".join(lines) + "\n"


def _csv_row(fields: list[str]) -> str:
    return ",".join(_escape_csv_field(f) for f in fields)


def _escape_csv_field(value: str) -> str:
    """RFC 4180: wrap in quotes when value contains comma / quote /
    newline; double up internal quotes."""
    if any(c in value for c in (",", '"', "\n", "\r")):
        return '"' + value.replace('"', '""') + '"'
    return value


def _format_number(value: float) -> str:
    """Stable numeric formatting. Mirrors physics writer convention:
    fixed-point in [1e-4, 1e6); scientific otherwise. 0.0 special-
    cased to "0" (not "0.0") for consistency with engineering CSV
    convention."""
    if value == 0.0:
        return "0"
    abs_v = abs(value)
    if 1e-4 <= abs_v < 1e6:
        s = f"{value:.6f}".rstrip("0").rstrip(".")
        return s if s and s != "-" else "0"
    return f"{value:.6e}"


__all__ = ["CenterlineSample", "centerline_csv"]
