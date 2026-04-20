"""Tests for audit_package.serialize (Phase 5 · PR-5b · DEC-V61-013)."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from src.audit_package import (
    PdfBackendUnavailable,
    is_pdf_backend_available,
    render_html,
    serialize_pdf,
    serialize_zip,
    serialize_zip_bytes,
)
from src.audit_package.serialize import _canonical_json


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _synthetic_manifest() -> dict:
    """Minimal but realistic manifest for serialization tests."""
    return {
        "schema_version": 1,
        "manifest_id": "duct_flow-r1",
        "build_fingerprint": "2026-04-21T00:30:00Z",
        "git": {
            "repo_commit_sha": "b69fa34000000000000000000000000000000000",
            "whitelist_commit_sha": "947661ef00000000000000000000000000000000",
            "gold_standard_commit_sha": "947661ef00000000000000000000000000000000",
        },
        "case": {
            "id": "duct_flow",
            "legacy_ids": ["fully_developed_pipe", "fully_developed_turbulent_pipe_flow"],
            "whitelist_entry": {
                "id": "duct_flow",
                "name": "Fully Developed Turbulent Square-Duct Flow",
                "solver": "simpleFoam",
                "parameters": {"Re": 50000, "aspect_ratio": 1.0},
            },
            "gold_standard": {
                "case_id": "duct_flow",
                "source": "Jones 1976",
                "observables": [{"name": "friction_factor", "ref_value": 0.0185}],
            },
        },
        "run": {
            "run_id": "r1",
            "status": "output_present",
            "solver": "simpleFoam",
            "inputs": {
                "system/controlDict": "application simpleFoam;\nendTime 1000;\n",
                "system/blockMeshDict": "FoamFile { object blockMeshDict; }\n",
                "0/": {
                    "U": "dimensions [0 1 -1 0 0];\ninternalField uniform (1 0 0);\n",
                    "p": "dimensions [0 2 -2 0 0];\ninternalField uniform 0;\n",
                },
            },
            "outputs": {
                "solver_log_name": "log.simpleFoam",
                "solver_log_tail": "iter 199 Solving for Ux, Initial residual = 1.99e-04\nEnd\n",
                "postProcessing_sets_files": ["postProcessing/sets/1000/centerline_U.xy"],
            },
        },
        "measurement": {
            "key_quantities": {"friction_factor": 0.0183, "source": "sampleDict_direct"},
            "comparator_verdict": "PASS",
            "audit_concerns": [],
        },
        "decision_trail": [
            {
                "decision_id": "DEC-V61-011",
                "title": "Q-2 Path A — fully_developed_pipe → duct_flow rename",
                "relative_path": ".planning/decisions/2026-04-20_q2_r_a_relabel_path_a.md",
            },
            {
                "decision_id": "DEC-V61-012",
                "title": "Phase 5 PR-5a — Audit package manifest builder",
                "relative_path": ".planning/decisions/2026-04-21_phase5_5a_manifest_builder.md",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Canonical JSON
# ---------------------------------------------------------------------------

class TestCanonicalJson:
    def test_sorts_keys(self):
        b = _canonical_json({"b": 2, "a": 1})
        text = b.decode()
        assert text.index('"a"') < text.index('"b"')

    def test_trailing_newline(self):
        b = _canonical_json({"a": 1})
        assert b.endswith(b"\n")

    def test_utf8_preserved(self):
        b = _canonical_json({"name": "Rayleigh-Bénard"})
        assert "Bénard" in b.decode("utf-8")

    def test_byte_stable_across_calls(self):
        obj = {"x": [3, 1, 2], "y": {"b": 2, "a": 1}}
        assert _canonical_json(obj) == _canonical_json(obj)


# ---------------------------------------------------------------------------
# Zip determinism + content
# ---------------------------------------------------------------------------

class TestZipBytesDeterministic:
    def test_byte_identical_across_calls(self):
        m = _synthetic_manifest()
        b1 = serialize_zip_bytes(m)
        b2 = serialize_zip_bytes(m)
        assert b1 == b2
        # Hash as a second-line verification
        assert hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest()

    def test_zip_contains_manifest_json(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            assert "manifest.json" in zf.namelist()
            manifest_back = json.loads(zf.read("manifest.json"))
            assert manifest_back["manifest_id"] == "duct_flow-r1"

    def test_zip_includes_whitelist_and_gold(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            names = set(zf.namelist())
            assert "case/whitelist_entry.json" in names
            assert "case/gold_standard.json" in names

    def test_zip_includes_run_inputs(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            names = set(zf.namelist())
            assert "run/inputs/system/controlDict" in names
            assert "run/inputs/0/U" in names
            assert "run/inputs/0/p" in names

    def test_zip_includes_log_tail(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            log = zf.read("run/outputs/solver_log_tail.txt").decode()
            assert "End" in log

    def test_zip_includes_decision_trail_pointers(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            names = set(zf.namelist())
            assert "decisions/DEC-V61-011.txt" in names
            assert "decisions/DEC-V61-012.txt" in names

    def test_zip_entries_have_epoch_mtime(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            for info in zf.infolist():
                assert info.date_time == (1980, 1, 1, 0, 0, 0)

    def test_zip_entries_are_sorted(self):
        m = _synthetic_manifest()
        zbytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            names = zf.namelist()
            assert names == sorted(names)

    def test_minimal_manifest_still_zips(self):
        """Manifest with no run/ and no decisions still serializes."""
        minimal = {
            "schema_version": 1,
            "manifest_id": "x-y",
            "build_fingerprint": "2026-04-21T00:00:00Z",
            "git": {},
            "case": {"id": "x", "legacy_ids": [], "whitelist_entry": None, "gold_standard": None},
            "run": {"run_id": "y", "status": "no_run_output"},
            "measurement": {"key_quantities": {}, "comparator_verdict": None, "audit_concerns": []},
            "decision_trail": [],
        }
        zbytes = serialize_zip_bytes(minimal)
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            assert zf.namelist() == ["manifest.json"]


class TestSerializeZipWriter:
    def test_writes_to_path(self, tmp_path):
        m = _synthetic_manifest()
        out = tmp_path / "bundle.zip"
        serialize_zip(m, out)
        assert out.is_file()
        assert out.read_bytes() == serialize_zip_bytes(m)

    def test_creates_parent_dir(self, tmp_path):
        m = _synthetic_manifest()
        out = tmp_path / "a" / "b" / "bundle.zip"
        serialize_zip(m, out)
        assert out.is_file()


# ---------------------------------------------------------------------------
# HTML render
# ---------------------------------------------------------------------------

class TestRenderHtml:
    def test_contains_manifest_id(self):
        html = render_html(_synthetic_manifest())
        assert "duct_flow-r1" in html

    def test_contains_git_shas(self):
        html = render_html(_synthetic_manifest())
        assert "b69fa340" in html  # repo_commit_sha prefix
        assert "947661ef" in html  # whitelist + gold SHA prefix

    def test_verdict_styling(self):
        html = render_html(_synthetic_manifest())
        assert 'verdict-pass' in html
        assert 'PASS</span>' in html

    def test_fail_verdict_styled(self):
        m = _synthetic_manifest()
        m["measurement"]["comparator_verdict"] = "FAIL"
        html = render_html(m)
        assert 'verdict-fail' in html

    def test_hazard_verdict_styled(self):
        m = _synthetic_manifest()
        m["measurement"]["comparator_verdict"] = "HAZARD"
        html = render_html(m)
        assert 'verdict-hazard' in html

    def test_decision_trail_rendered(self):
        html = render_html(_synthetic_manifest())
        assert "DEC-V61-011" in html
        assert "DEC-V61-012" in html

    def test_legacy_ids_rendered(self):
        html = render_html(_synthetic_manifest())
        assert "fully_developed_pipe" in html

    def test_deterministic_across_calls(self):
        m = _synthetic_manifest()
        assert render_html(m) == render_html(m)

    def test_no_external_cdn_links(self):
        """Bundled CSS only — reviewer must be able to view offline."""
        html = render_html(_synthetic_manifest())
        assert "cdn." not in html
        assert "googleapis" not in html
        assert "unpkg" not in html

    def test_html_escapes_user_controlled_fields(self):
        m = _synthetic_manifest()
        m["case"]["id"] = "<script>alert(1)</script>"
        html = render_html(m)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_empty_measurement_graceful(self):
        m = _synthetic_manifest()
        m["measurement"]["key_quantities"] = {}
        m["measurement"]["audit_concerns"] = []
        html = render_html(m)
        assert "no measurement recorded" in html
        assert "no audit concerns flagged" in html

    def test_empty_decision_trail_graceful(self):
        m = _synthetic_manifest()
        m["decision_trail"] = []
        html = render_html(m)
        assert "no decision trail found" in html


# ---------------------------------------------------------------------------
# PDF (guarded — skip when weasyprint native libs missing)
# ---------------------------------------------------------------------------

class TestPdfBackendAvailability:
    def test_availability_probe_returns_bool(self):
        result = is_pdf_backend_available()
        assert isinstance(result, bool)

    @pytest.mark.skipif(is_pdf_backend_available(), reason="PDF backend is available; raise-path unreachable")
    def test_serialize_pdf_raises_when_unavailable(self, tmp_path):
        """When weasyprint native libs missing, error message is actionable."""
        with pytest.raises(PdfBackendUnavailable) as exc_info:
            serialize_pdf(_synthetic_manifest(), tmp_path / "out.pdf")
        # Error message should include an install hint
        msg = str(exc_info.value)
        assert any(hint in msg for hint in ("brew install", "pip install", "apt install", "installation"))

    @pytest.mark.skipif(not is_pdf_backend_available(), reason="PDF backend not available on this host (no weasyprint native libs)")
    def test_serialize_pdf_writes_file_when_available(self, tmp_path):
        """When weasyprint is installed, PDF renders to a non-empty file."""
        out = tmp_path / "audit.pdf"
        serialize_pdf(_synthetic_manifest(), out)
        assert out.is_file()
        assert out.stat().st_size > 0
        # PDF magic bytes
        assert out.read_bytes()[:4] == b"%PDF"
