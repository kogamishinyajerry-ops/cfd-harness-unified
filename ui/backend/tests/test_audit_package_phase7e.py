"""Phase 7e (DEC-V61-033, L4) — audit-package Phase 7 artifact embedding tests.

Guards:
- When Phase 7 artifacts exist, manifest.phase7 is populated and the signed
  zip contains them at phase7/* paths with byte-identical content.
- When Phase 7 artifacts are absent, manifest.phase7 is omitted; signed zip
  is unchanged (backward-compatible with pre-L4 audit packages).
- Byte-reproducibility: two calls to build_manifest + serialize_zip with the
  same inputs produce identical bytes (HMAC-stable).
- Tampered Phase 7 manifest (invalid timestamp) → phase7 key absent, not 500.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Tuple

import pytest

from src.audit_package.manifest import (
    _PHASE7_TIMESTAMP_RE,
    _collect_phase7_artifacts,
    build_manifest,
)
from src.audit_package.serialize import (
    _zip_entries_from_manifest,
    serialize_zip_bytes,
)  # noqa: F401 — _zip_entries_from_manifest retained for legacy imports


# ---------- Test fixture helpers --------------------------------------------

def _setup_phase7_tree(
    tmp_path: Path, case_id: str = "lid_driven_cavity", run_id: str = "audit_real_run",
    timestamp: str = "20260421T000000Z",
) -> Tuple[Path, str]:
    """Build a minimal Phase 7 artifact tree under tmp_path/reports/."""
    fields = tmp_path / "reports" / "phase5_fields" / case_id
    renders = tmp_path / "reports" / "phase5_renders" / case_id
    reports = tmp_path / "reports" / "phase5_reports" / case_id
    (fields / timestamp / "sample" / "1000").mkdir(parents=True)
    (fields / timestamp / "sample" / "1000" / "uCenterline.xy").write_text(
        "# y Ux Uy Uz p\n0 0 0 0 0\n0.5 -0.2 0 0 0\n1.0 1.0 0 0 0\n",
        encoding="utf-8",
    )
    (fields / timestamp / "residuals.csv").write_text(
        "Time,Ux,Uy,p\n1,1,1,1\n2,0.1,0.1,0.1\n", encoding="utf-8",
    )
    (fields / "runs").mkdir(parents=True)
    (fields / "runs" / f"{run_id}.json").write_text(
        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id}),
        encoding="utf-8",
    )
    (renders / timestamp).mkdir(parents=True)
    for n in ("profile_u_centerline.png", "residuals.png"):
        (renders / timestamp / n).write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (renders / "runs").mkdir(parents=True)
    (renders / "runs" / f"{run_id}.json").write_text(
        json.dumps({"timestamp": timestamp, "case_id": case_id, "run_label": run_id,
                    "outputs": {}}),
        encoding="utf-8",
    )
    (reports / timestamp).mkdir(parents=True)
    (reports / timestamp / f"{run_id}_comparison_report.pdf").write_bytes(
        b"%PDF-1.7\n%fake pdf for test\n%%EOF\n",
    )
    return tmp_path, timestamp


# ---------- _collect_phase7_artifacts unit tests ----------------------------

def test_collect_phase7_happy_path(tmp_path) -> None:
    _setup_phase7_tree(tmp_path)
    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
    assert phase7 is not None
    assert phase7["schema_level"] == "L4"
    zip_paths = [e["zip_path"] for e in phase7["entries"]]
    # Sorted alphabetically.
    assert zip_paths == sorted(zip_paths)
    # Contains field artifacts + renders + PDF.
    assert any(z.startswith("phase7/field_artifacts/") for z in zip_paths)
    assert any(z.startswith("phase7/renders/") for z in zip_paths)
    assert "phase7/comparison_report.pdf" in zip_paths
    # Every entry has a valid sha256.
    for e in phase7["entries"]:
        assert isinstance(e["sha256"], str)
        assert len(e["sha256"]) == 64


def test_collect_phase7_no_artifacts_returns_none(tmp_path) -> None:
    result = _collect_phase7_artifacts("nonexistent_case", "nonexistent_run", tmp_path)
    assert result is None


def test_collect_phase7_rejects_tampered_timestamp(tmp_path) -> None:
    """Malicious runs/{run}.json with timestamp='../../outside' must not leak files."""
    _setup_phase7_tree(tmp_path)
    # Overwrite the 7a manifest with a traversal attempt.
    m = tmp_path / "reports" / "phase5_fields" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    m.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
    # Plant a would-be leak target (shouldn't be included).
    leak = tmp_path / "etc" / "passwd_fake"
    leak.parent.mkdir(parents=True)
    leak.write_text("root:x:0:0\n", encoding="utf-8")
    # Also invalidate the 7b manifest to test both paths.
    mr = tmp_path / "reports" / "phase5_renders" / "lid_driven_cavity" / "runs" / "audit_real_run.json"
    mr.write_text(json.dumps({"timestamp": "../../etc"}), encoding="utf-8")
    phase7 = _collect_phase7_artifacts("lid_driven_cavity", "audit_real_run", tmp_path)
    # Every entry (if any) must have zip_path under phase7/ — no leaks.
    if phase7 is not None:
        for e in phase7["entries"]:
            assert e["zip_path"].startswith("phase7/"), e
            assert "passwd" not in e["disk_path_rel"]
            assert "/etc/" not in e["disk_path_rel"]


def test_timestamp_regex_shape_gate() -> None:
    for ok in ("20260421T000000Z", "20991231T235959Z"):
        assert _PHASE7_TIMESTAMP_RE.match(ok)
    for bad in ("2026-04-21", "../../evil", "", "abc", "20260421",
                "20260421T000000z", "20260421T000000", "20260421 000000Z"):
        assert _PHASE7_TIMESTAMP_RE.match(bad) is None


# ---------- Integration: build_manifest + serialize_zip ----------------------

def test_build_manifest_embeds_phase7(tmp_path) -> None:
    _setup_phase7_tree(tmp_path)
    manifest = build_manifest(
        case_id="lid_driven_cavity",
        run_id="audit_real_run",
        repo_root=tmp_path,
        include_phase7=True,
    )
    assert "phase7" in manifest
    assert manifest["phase7"]["schema_level"] == "L4"


def test_build_manifest_opt_out_phase7(tmp_path) -> None:
    """Backward compat: include_phase7=False suppresses the key entirely."""
    _setup_phase7_tree(tmp_path)
    manifest = build_manifest(
        case_id="lid_driven_cavity",
        run_id="audit_real_run",
        repo_root=tmp_path,
        include_phase7=False,
    )
    assert "phase7" not in manifest


def test_zip_contains_phase7_entries(tmp_path) -> None:
    """serialize_zip_bytes(manifest, repo_root=tmp_path) picks up phase7
    entries and embeds them at the declared zip_path with byte-identical
    content. Exercises the REAL serialize path — no monkeypatch — so a
    drift between build_manifest's repo_root and serialize's repo_root
    will surface here (Codex round 1 finding #1, DEC-V61-033)."""
    _setup_phase7_tree(tmp_path)
    manifest = build_manifest(
        case_id="lid_driven_cavity",
        run_id="audit_real_run",
        repo_root=tmp_path,
    )
    zip_bytes = serialize_zip_bytes(manifest, repo_root=tmp_path)

    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        phase7_names = [n for n in names if n.startswith("phase7/")]
        assert len(phase7_names) >= 3  # at least PDF + 1 render + 1 field artifact
        assert "phase7/comparison_report.pdf" in names
        # Manifest-declared phase7 entry count must match zip-present count.
        manifest_phase7 = manifest["phase7"]["entries"]
        assert len(manifest_phase7) == len(phase7_names), (
            "manifest advertises phase7 files the zip does not contain "
            "— repo_root drift between build_manifest and serialize"
        )
        # Verify byte-identical embedded content.
        pdf_bytes = zf.read("phase7/comparison_report.pdf")
        assert pdf_bytes == (tmp_path / "reports" / "phase5_reports" /
                             "lid_driven_cavity" / "20260421T000000Z" /
                             "audit_real_run_comparison_report.pdf").read_bytes()


def test_zip_omits_phase7_on_repo_root_mismatch(tmp_path) -> None:
    """If callers forget to pass ``repo_root=`` to serialize_zip_bytes but
    did pass it to build_manifest, phase7 entries fail containment and
    drop silently — BUT the manifest still advertises them. This test
    documents that hazard so consumers know the two calls must agree.

    Prefer ``repo_root=`` on BOTH sides (or None on both sides).
    """
    _setup_phase7_tree(tmp_path)
    manifest = build_manifest(
        case_id="lid_driven_cavity",
        run_id="audit_real_run",
        repo_root=tmp_path,  # tmp_path manifest…
    )
    # …but serialize without repo_root → falls back to real repo root,
    # where tmp_path's disk_path_rel values don't resolve.
    zip_bytes = serialize_zip_bytes(manifest)
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        phase7_names = [n for n in zf.namelist() if n.startswith("phase7/")]
    # The drop is silent (containment check fails) — zero phase7 entries.
    assert phase7_names == []


def test_byte_reproducibility_with_phase7(tmp_path) -> None:
    """Two consecutive build_manifest + serialize_zip_bytes calls with the
    same Phase 7 artifacts must produce byte-identical zips."""
    _setup_phase7_tree(tmp_path)
    m1 = build_manifest(
        case_id="lid_driven_cavity", run_id="audit_real_run",
        build_fingerprint="deadbeefdeadbeef",
        repo_root=tmp_path,
    )
    m2 = build_manifest(
        case_id="lid_driven_cavity", run_id="audit_real_run",
        build_fingerprint="deadbeefdeadbeef",
        repo_root=tmp_path,
    )
    # manifest dicts equal → canonical JSON equal.
    assert m1 == m2
    # phase7 SHA256s identical.
    sha1 = [e["sha256"] for e in m1["phase7"]["entries"]]
    sha2 = [e["sha256"] for e in m2["phase7"]["entries"]]
    assert sha1 == sha2
    # Zip bytes identical (real serialize path, with repo_root plumbed through).
    z1 = serialize_zip_bytes(m1, repo_root=tmp_path)
    z2 = serialize_zip_bytes(m2, repo_root=tmp_path)
    assert z1 == z2
    # Sanity: phase7 embed count matches manifest advertisement.
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(z1)) as zf:
        phase7_names = [n for n in zf.namelist() if n.startswith("phase7/")]
    assert len(phase7_names) == len(m1["phase7"]["entries"])
