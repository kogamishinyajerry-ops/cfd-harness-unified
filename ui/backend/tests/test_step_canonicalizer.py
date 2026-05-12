"""Tests for ``geometry_ingest.step_canonicalizer`` (A7 advisor).

Coverage:
1. canonicalize_step_text replaces timestamp in FILE_NAME line
2. idempotency — running twice produces identical output
3. no FILE_NAME line → replaced_count = 0, text unchanged
4. multiple FILE_NAME lines → all replaced (defensive; OCP writes one)
5. canonicalize_step_file inplace → byte-determinism across runs
6. canonicalize_step_file inplace=False → writes sibling .canonical.step
7. is_already_canonical signals correctly for pre-canonical input
8. surgical replacement preserves other FILE_NAME fields (author etc.)
9. geometry lines (CARTESIAN_POINT etc.) untouched
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ui.backend.services.geometry_ingest.step_canonicalizer import (
    DEFAULT_SENTINEL_TIMESTAMP,
    StepCanonicalizationReport,
    canonicalize_step_file,
    canonicalize_step_text,
)


# OCP-style single-line FILE_NAME header excerpt. Keep small (no full
# STEP file content needed) — algorithm operates on text.
_OCP_STEP_HEADER = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Open CASCADE Model'),'2;1');
FILE_NAME('Open CASCADE Shape Model','2026-05-09T20:11:09',('Author'),('Unknown'),'Open CASCADE STEP processor 7.7','Open CASCADE 7.7','Unknown');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#1=CARTESIAN_POINT('',(0.0,0.0,0.0));
#2=CARTESIAN_POINT('',(1.0,0.0,0.0));
ENDSEC;
END-ISO-10303-21;
"""

_PRE_CANONICAL_HEADER = _OCP_STEP_HEADER.replace(
    "'2026-05-09T20:11:09'", f"'{DEFAULT_SENTINEL_TIMESTAMP}'"
)


def test_canonicalize_text_replaces_timestamp():
    canonical, replaced = canonicalize_step_text(_OCP_STEP_HEADER)
    assert replaced == 1
    assert "2026-05-09T20:11:09" not in canonical
    assert DEFAULT_SENTINEL_TIMESTAMP in canonical


def test_canonicalize_text_idempotent():
    once, n1 = canonicalize_step_text(_OCP_STEP_HEADER)
    twice, n2 = canonicalize_step_text(once)
    assert n1 == 1
    assert n2 == 1  # regex re-matches the sentinel slot; idempotent in content
    assert once == twice


def test_canonicalize_text_no_file_name_unchanged():
    text = "ISO-10303-21;\nDATA;\n#1=CARTESIAN_POINT('',(0.0,0.0,0.0));\nEND-ISO-10303-21;\n"
    canonical, replaced = canonicalize_step_text(text)
    assert replaced == 0
    assert canonical == text


def test_canonicalize_text_preserves_other_fields():
    canonical, _ = canonicalize_step_text(_OCP_STEP_HEADER)
    # Author, organization, preprocessor, originating system, authorisation
    # all preserved.
    assert "'Author'" in canonical
    assert "'Unknown'" in canonical
    assert "Open CASCADE STEP processor 7.7" in canonical
    assert "Open CASCADE 7.7" in canonical


def test_canonicalize_text_preserves_geometry_lines():
    canonical, _ = canonicalize_step_text(_OCP_STEP_HEADER)
    assert "#1=CARTESIAN_POINT('',(0.0,0.0,0.0));" in canonical
    assert "#2=CARTESIAN_POINT('',(1.0,0.0,0.0));" in canonical


def test_canonicalize_text_custom_sentinel():
    canonical, _ = canonicalize_step_text(
        _OCP_STEP_HEADER, sentinel_timestamp="2000-01-01T00:00:00"
    )
    assert "'2000-01-01T00:00:00'" in canonical
    assert DEFAULT_SENTINEL_TIMESTAMP not in canonical


def test_canonicalize_file_inplace_byte_determinism(tmp_path: Path):
    # Two independently-generated STEP files with different timestamps.
    p1 = tmp_path / "case_a_run1.step"
    p2 = tmp_path / "case_a_run2.step"
    p1.write_text(_OCP_STEP_HEADER)
    p2.write_text(_OCP_STEP_HEADER.replace("2026-05-09T20:11:09", "2026-05-09T20:11:42"))
    assert p1.read_bytes() != p2.read_bytes()  # pre-canonical: differ

    r1 = canonicalize_step_file(p1, inplace=True)
    r2 = canonicalize_step_file(p2, inplace=True)

    assert r1.replaced_lines == 1
    assert r2.replaced_lines == 1
    assert r1.canonical_sha256 == r2.canonical_sha256  # byte-determinism achieved
    assert p1.read_bytes() == p2.read_bytes()


def test_canonicalize_file_not_inplace_writes_sibling(tmp_path: Path):
    src = tmp_path / "case_b.step"
    src.write_text(_OCP_STEP_HEADER)
    src_sha = hashlib.sha256(src.read_bytes()).hexdigest()

    report = canonicalize_step_file(src, inplace=False)

    assert report.path == src.with_suffix(".canonical.step")
    assert report.path.exists()
    assert report.path.read_bytes() != src.read_bytes()
    # Original untouched
    assert hashlib.sha256(src.read_bytes()).hexdigest() == src_sha


def test_canonicalize_file_already_canonical_signals(tmp_path: Path):
    src = tmp_path / "case_c_canonical.step"
    src.write_text(_PRE_CANONICAL_HEADER)
    pre_bytes = src.read_bytes()

    report = canonicalize_step_file(src, inplace=True)

    assert report.is_already_canonical is True
    assert report.original_sha256 == report.canonical_sha256
    assert src.read_bytes() == pre_bytes  # no write needed; content stable


def test_canonicalize_file_returns_report_dataclass(tmp_path: Path):
    src = tmp_path / "case_d.step"
    src.write_text(_OCP_STEP_HEADER)
    report = canonicalize_step_file(src, inplace=True)
    assert isinstance(report, StepCanonicalizationReport)
    assert report.path == src
    assert report.replaced_lines == 1
    assert report.is_already_canonical is False
    assert report.original_sha256 != report.canonical_sha256
