"""Tests for V198 4a · freecad_step_to_stl bridge."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from ui.backend.services.geometry_ingest.freecad_step_to_stl import (
    DEFAULT_FREECAD_CMD,
    STEPToSTLBackendUnavailable,
    STEPToSTLConversionFailed,
    combine_per_body_stls,
    sanitize_label,
    step_to_per_body_stl,
)


def test_sanitize_label_basic():
    assert sanitize_label("airframe_reference") == "airframe_reference"
    assert sanitize_label("Root Mount Pad") == "root_mount_pad"
    assert sanitize_label("farfield-outer/2") == "farfield_outer_2"


def test_sanitize_label_handles_empty_and_punctuation():
    assert sanitize_label("") == "body"
    assert sanitize_label("///") == "body"
    assert sanitize_label("  thin access plate  ") == "thin_access_plate"


def test_step_to_per_body_stl_raises_when_freecadcmd_missing(tmp_path):
    with pytest.raises(STEPToSTLBackendUnavailable, match="freecadcmd not at"):
        step_to_per_body_stl(
            step_path=tmp_path / "fake.step",
            out_dir=tmp_path / "out",
            freecad_cmd="/nonexistent/freecadcmd",
        )


def test_step_to_per_body_stl_raises_when_no_manifest(tmp_path, monkeypatch):
    fake_cmd = tmp_path / "fake_freecadcmd"
    fake_cmd.write_text("#!/bin/sh\nexit 1\n")
    fake_cmd.chmod(0o755)

    def _noop_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0] if args else [], returncode=1, stdout="", stderr="boom"
        )

    monkeypatch.setattr(subprocess, "run", _noop_run)
    with pytest.raises(STEPToSTLConversionFailed, match="no manifest"):
        step_to_per_body_stl(
            step_path=tmp_path / "in.step",
            out_dir=tmp_path / "out",
            freecad_cmd=str(fake_cmd),
        )


def test_step_to_per_body_stl_parses_manifest(tmp_path, monkeypatch):
    fake_cmd = tmp_path / "fake_freecadcmd"
    fake_cmd.write_text("#!/bin/sh\n")
    fake_cmd.chmod(0o755)
    out_dir = tmp_path / "out"

    def _fake_run(cmd, **kwargs):
        out_dir.mkdir(parents=True, exist_ok=True)
        for stem in ("airframe_reference", "inlet"):
            (out_dir / f"{stem}.stl").write_text("solid stub\nendsolid\n")
        (out_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "step_path": "x.step",
                    "n_bodies": 2,
                    "bodies": [
                        {"label": "airframe_reference", "stem": "airframe_reference",
                         "path": str(out_dir / "airframe_reference.stl"), "n_facets": 100},
                        {"label": "inlet", "stem": "inlet",
                         "path": str(out_dir / "inlet.stl"), "n_facets": 50},
                    ],
                }
            )
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = step_to_per_body_stl(
        step_path=tmp_path / "in.step",
        out_dir=out_dir,
        freecad_cmd=str(fake_cmd),
    )
    assert [p.name for p in result] == ["airframe_reference.stl", "inlet.stl"]
    assert all(p.exists() for p in result)


def test_combine_per_body_stls_rewrites_solid_headers_per_manifest(tmp_path):
    """Each body's `solid Mesh` header (FreeCAD generic) becomes `solid <stem>`.

    Verifies the F-NEW-10 round-trip: manifest stem → solid header →
    detect_patches recovers patch name downstream.
    """
    bodies = [
        ("inlet", b"solid Mesh\nfacet ...\nendsolid Mesh\n"),
        ("outlet", b"solid Mesh\nfacet ...\nendsolid Mesh\n"),
        ("airframe_reference", b"solid Mesh\nfacet ...\nendsolid Mesh\n"),
    ]
    body_records = []
    for stem, raw in bodies:
        p = tmp_path / f"{stem}.stl"
        p.write_bytes(raw)
        body_records.append({"label": stem, "stem": stem, "path": str(p), "n_facets": 1})
    (tmp_path / "manifest.json").write_text(
        json.dumps({"step_path": "x.step", "n_bodies": 3, "bodies": body_records})
    )

    out = combine_per_body_stls(stl_dir=tmp_path)

    assert out == tmp_path / "combined.stl"
    combined = out.read_bytes()
    # `solid <name>` matches as substring of `endsolid <name>`, so anchor
    # to start-of-line via regex when counting opening headers.
    import re as _re
    def _opening_count(name: str) -> int:
        pat = rb"(?:^|\n)solid " + _re.escape(name.encode()) + rb"\n"
        return len(_re.findall(pat, combined))

    assert _opening_count("inlet") == 1
    assert _opening_count("outlet") == 1
    assert _opening_count("airframe_reference") == 1
    assert combined.count(b"endsolid inlet\n") == 1
    assert combined.count(b"endsolid outlet\n") == 1
    assert combined.count(b"endsolid airframe_reference\n") == 1
    assert b"solid Mesh\n" not in combined  # all generic headers rewritten
    assert b"endsolid Mesh\n" not in combined


@pytest.mark.skipif(
    not os.path.exists(DEFAULT_FREECAD_CMD),
    reason="FreeCAD not installed at default path",
)
def test_step_to_per_body_stl_real_case_003_integration(tmp_path):
    """Integration: case_003 STEP must produce ≥10 named-body STLs."""
    repo_root = Path(__file__).resolve().parents[3]
    step_path = repo_root / (
        "ui/backend/user_drafts/imported/case_003_crm_hls/raw/cad.step"
    )
    if not step_path.exists():
        pytest.skip(f"case_003 STEP not at {step_path}")
    paths = step_to_per_body_stl(step_path=step_path, out_dir=tmp_path)
    assert len(paths) >= 10, f"expected ≥10 STLs, got {len(paths)}: {paths}"
    stems = {p.stem for p in paths}
    assert "airframe_reference" in stems
    assert "inlet" in stems
    assert "outlet" in stems
