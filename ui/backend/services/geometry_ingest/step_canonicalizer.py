"""STEP file canonicalizer — byte-determinism for Codex-generated CAD.

The OCP STEP exporter (cadquery 2.7.0+) writes a wall-clock timestamp
into the ``FILE_NAME(...)`` header of every STEP file. Two byte-
identical-geometry runs therefore produce different SHA-256 hashes
even when the build is deterministic, which breaks the byte-
determinism contract the Codex case-design protocol expects.

This module strips just the timestamp argument, leaving every other
FILE_NAME field (author, organization, preprocessor_version,
originating_system, authorisation) intact. Geometry is never touched.

V130 / V132: read-only metadata, no mutating routes. Caller decides
``inplace=True`` (file overwrite) vs writing to a sibling
``.canonical.step``.

References:
- V51 in ``industrial_case_solver_findings.md`` (case_012 cross-cut,
  4 sediment cases observed: case_002a / case_005 / case_011 / case_012)
- sub-DEC V61-198-sub-A7 · 2026-05-12
- Reference implementation precursor: ``~/Desktop/case_012_hvac_supply_diffuser/scripts/build_cad.py::canonicalize_step``
  (case-local; this module is the productized main-project form)
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SENTINEL_TIMESTAMP = "1970-01-01T00:00:00"

# OCP STEP writes FILE_NAME on a single line; the timestamp is the
# 2nd quoted argument. This pattern captures the prefix up to and
# including the comma+whitespace before the timestamp, then the
# timestamp itself, then the trailing comma so we can splice the
# sentinel without touching neighbours.
_FILE_NAME_TIMESTAMP_RE = re.compile(
    r"(FILE_NAME\(\s*'[^']*'\s*,\s*)'[^']*'(\s*,)"
)


@dataclass(frozen=True)
class StepCanonicalizationReport:
    """Outcome of ``canonicalize_step_file`` / ``canonicalize_step_text``."""
    path: Path | None
    replaced_lines: int
    original_sha256: str
    canonical_sha256: str
    is_already_canonical: bool


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonicalize_step_text(
    text: str,
    *,
    sentinel_timestamp: str = DEFAULT_SENTINEL_TIMESTAMP,
) -> tuple[str, int]:
    """Replace the FILE_NAME timestamp with a sentinel.

    Returns ``(canonical_text, replaced_count)``. The replacement is
    surgical — only the 2nd quoted argument of ``FILE_NAME(...)`` is
    touched. Returns ``replaced_count == 0`` when no FILE_NAME line
    is found (binary STEP or non-OCP exporter).
    """
    replaced = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal replaced
        replaced += 1
        return f"{match.group(1)}'{sentinel_timestamp}'{match.group(2)}"

    canonical = _FILE_NAME_TIMESTAMP_RE.sub(_sub, text)
    return canonical, replaced


def canonicalize_step_file(
    path: str | Path,
    *,
    inplace: bool = True,
    sentinel_timestamp: str = DEFAULT_SENTINEL_TIMESTAMP,
) -> StepCanonicalizationReport:
    """Canonicalize a STEP file's FILE_NAME timestamp for byte-determinism.

    With ``inplace=True``: overwrites the file at ``path``. With
    ``inplace=False``: writes a sibling ``<stem>.canonical.step`` and
    leaves the original untouched. Returns the report.

    Idempotent: a file already at the sentinel is detected via
    ``is_already_canonical=True`` and is rewritten as a no-op (the
    written bytes equal the read bytes).
    """
    p = Path(path)
    original_bytes = p.read_bytes()
    original_text = original_bytes.decode("utf-8")
    canonical_text, replaced = canonicalize_step_text(
        original_text, sentinel_timestamp=sentinel_timestamp
    )
    canonical_bytes = canonical_text.encode("utf-8")

    if inplace:
        out_path = p
    else:
        out_path = p.with_suffix(".canonical.step")

    is_already_canonical = canonical_bytes == original_bytes
    if not is_already_canonical or not inplace:
        out_path.write_bytes(canonical_bytes)

    return StepCanonicalizationReport(
        path=out_path,
        replaced_lines=replaced,
        original_sha256=_sha256(original_bytes),
        canonical_sha256=_sha256(canonical_bytes),
        is_already_canonical=is_already_canonical,
    )
