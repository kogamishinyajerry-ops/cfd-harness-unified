"""V91.3 · V9.D Audit-package commentary sidecar contract.

Asserts:
    - manifest adapter derives RunArtifactSlice correctly from manifest dict
    - commentary section attaches to manifest cleanly (additive · forward-compat)
    - ``_zip_entries_from_manifest`` writes ``commentary/matched.json`` when
      commentary section present
    - Byte-reproducibility (RS#36): same manifest dict → identical zip bytes
      across 3 calls (HMAC-signing depends on this)
    - Old bundles without commentary remain valid (purely additive)
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from typing import Any, Dict

import pytest

from src.audit_package.serialize import (
    _zip_entries_from_manifest,
    serialize_zip_bytes,
)
from ui.backend.services.v9_advisor.manifest_adapter import (
    commentary_section_for_manifest,
    derive_slice_from_manifest,
    matches_for_manifest,
)


def _baseline_manifest() -> Dict[str, Any]:
    """Minimal manifest dict shaped like real build_manifest output.

    V91 Codex P1 #3 disposition: uses the REAL audit-package schema
    (observables = list of records · key_quantities = singleton {quantity,
    value, solver_success, ...}). Older test fixtures used a dict-style
    shape which the adapter still supports as a fallback for ad-hoc tests.
    """
    return {
        "schema_version": "1",
        "manifest_id": "duct_flow-R-OK-1",
        "build_fingerprint": "abc123def456",
        "git": {"repo_commit_sha": "deadbeef", "whitelist_commit_sha": None, "gold_standard_commit_sha": None},
        "case": {
            "id": "duct_flow",
            "legacy_ids": [],
            "whitelist_entry": {"case_id": "duct_flow", "solver": "simpleFoam"},
            "gold_standard": {
                "case_id": "duct_flow",
                "observables": [
                    {
                        "name": "friction_factor",
                        "ref_value": 0.0185,
                        "tolerance": {"mode": "relative", "value": 0.10},
                        "unit": "dimensionless",
                    },
                ],
            },
        },
        "run": {
            "run_id": "R-OK-1",
            "status": "output_present",
            "outputs": {
                "solver_log_name": "log.simpleFoam",
                "solver_log_tail": (
                    "Time = 800s\n"  # V91 Codex P2 #4 fix: trailing "s" must parse
                    "DICPCG:  Solving for p, Initial residual = 5e-05\n"
                    "SIMPLE solution converged in 800 iterations\n"
                ),
            },
        },
        "measurement": {
            # V91 Codex P1 #3 fix: real singleton key_quantities record.
            "key_quantities": {
                "quantity": "friction_factor",
                "value": 0.0187,  # ~1% drift · within tolerance
                "solver_success": True,
                "comparator_passed": True,
                "unit": "dimensionless",
            },
            "comparator_verdict": "PASS",
            "audit_concerns": [],
        },
        "decision_trail": [],
    }


def _max_iters_manifest() -> Dict[str, Any]:
    """Run that hit maxIters AND drifted from gold — solver itself ran cleanly.

    V91 Codex P1 #2 disposition: this used to wrongly fire R3
    (RUN_FAILED_NONZERO_EXIT) because the old adapter equated comparator
    FAIL with a crashed solver. Real signal — comparator_verdict=FAIL +
    solver_success=True — is "physics drift in a clean run".
    """
    m = _baseline_manifest()
    m["run"]["outputs"]["solver_log_tail"] = (
        "Time = 5000s\n"  # trailing "s"
        "DILUPBiCGStab:  Solving for U, Initial residual = 0.02\n"
        "Maximum iterations reached but residuals still high\n"
    )
    # Force gold drift > 5%: friction_factor 0.0202 vs ref 0.0185 = 9.2% drift.
    m["measurement"]["key_quantities"] = {
        "quantity": "friction_factor",
        "value": 0.0202,
        "solver_success": True,  # solver ran cleanly · just off-spec output
        "comparator_passed": False,
    }
    m["measurement"]["comparator_verdict"] = "FAIL"
    return m


def _crashed_solver_manifest() -> Dict[str, Any]:
    """Run where the solver itself died — this IS the R3 case (V91 Codex P1 #2)."""
    m = _baseline_manifest()
    m["measurement"]["key_quantities"]["solver_success"] = False
    m["measurement"]["comparator_verdict"] = "FAIL"
    return m


class TestManifestAdapter:
    def test_derive_slice_pass_run(self):
        """V91 Codex P2 #4: log uses 'Time = 800s' (with s suffix) — must parse."""
        m = _baseline_manifest()
        s = derive_slice_from_manifest(m)
        assert s.success is True
        assert s.exit_code == 0
        assert s.case_id == "duct_flow"
        assert s.run_id == "R-OK-1"
        assert s.convergence_stats is not None
        assert s.convergence_stats.final_iter == 800  # parsed from "Time = 800s"
        assert s.convergence_stats.max_iters_reached is False
        assert s.convergence_stats.converged is True
        assert s.gold_delta is not None
        assert s.gold_delta.max_abs_pct < 1.5  # 0.0187 vs 0.0185 = ~1.1%

    def test_derive_slice_physics_drift_not_crash(self):
        """V91 Codex P1 #2: comparator FAIL + solver_success=True = clean run,
        physics drift. success stays True; R3 must NOT fire later."""
        m = _max_iters_manifest()
        s = derive_slice_from_manifest(m)
        # solver_success=True → success stays True even though verdict=FAIL
        assert s.success is True
        assert s.exit_code == 0
        assert s.convergence_stats is not None
        assert s.convergence_stats.max_iters_reached is True
        # converged = success AND NOT max_iters_reached → False
        assert s.convergence_stats.converged is False
        # gold_delta from real-schema observables list: 0.0202 vs 0.0185 ≈ 9.2%
        assert s.gold_delta is not None
        assert s.gold_delta.max_abs_pct > 5.0
        assert s.gold_delta.max_abs_pct < 12.0

    def test_derive_slice_crashed_solver(self):
        """V91 Codex P1 #2: solver_success=False = real crash → success=False,
        R3 SHOULD fire."""
        m = _crashed_solver_manifest()
        s = derive_slice_from_manifest(m)
        assert s.success is False
        assert s.exit_code == 1

    def test_derive_slice_missing_log_tail_graceful(self):
        m = _baseline_manifest()
        m["run"]["outputs"].pop("solver_log_tail")
        s = derive_slice_from_manifest(m)
        # No log → no convergence_stats; solver_success=True → success=True
        assert s.success is True
        assert s.convergence_stats is None

    def test_derive_slice_dict_observables_fallback(self):
        """Legacy/test-fiction dict-shape observables still supported."""
        m = _baseline_manifest()
        m["case"]["gold_standard"]["observables"] = {"friction_factor": 0.0185}
        m["measurement"]["key_quantities"] = {"friction_factor": 0.0187}
        s = derive_slice_from_manifest(m)
        assert s.gold_delta is not None
        assert s.gold_delta.max_abs_pct < 1.5


class TestMatchesForManifest:
    def test_baseline_run_no_false_positives(self):
        """Clean baseline (solver_success=True, comparator PASS, log converged,
        gold drift <5%) must NOT fire any negative-class rule."""
        m = _baseline_manifest()
        matches = matches_for_manifest(m)
        rule_ids = [x["rule_id"] for x in matches]
        # No max-iters, no crash, no gold drift, no forces history, no
        # residual history → only R8 healthy_convergence could potentially
        # fire IF residuals were present, but they're not. So expect 0.
        assert "MAX_ITERS_REACHED_V9_R2" not in rule_ids
        assert "RUN_FAILED_NONZERO_EXIT_V9_R3" not in rule_ids
        assert "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" not in rule_ids
        assert "FORCES_NOT_CONVERGED_V9_R5" not in rule_ids
        assert "RESIDUAL_PLATEAU_U_V9_R7" not in rule_ids

    def test_physics_drift_fires_r2_r4_not_r3(self):
        """V91 Codex P1 #2: max-iters + gold drift on a clean run fires R2 + R4,
        NOT R3 (which would falsely claim solver crashed)."""
        m = _max_iters_manifest()
        matches = matches_for_manifest(m)
        rule_ids = [x["rule_id"] for x in matches]
        assert "MAX_ITERS_REACHED_V9_R2" in rule_ids
        assert "GOLD_DELTA_EXCEEDS_5_PCT_V9_R4" in rule_ids
        # R3 must NOT fire — solver did not crash
        assert "RUN_FAILED_NONZERO_EXIT_V9_R3" not in rule_ids

    def test_crashed_solver_fires_r3(self):
        """V91 Codex P1 #2: actual crash (solver_success=False) DOES fire R3."""
        m = _crashed_solver_manifest()
        matches = matches_for_manifest(m)
        rule_ids = [x["rule_id"] for x in matches]
        assert "RUN_FAILED_NONZERO_EXIT_V9_R3" in rule_ids

    def test_matches_structure(self):
        m = _max_iters_manifest()
        matches = matches_for_manifest(m)
        assert len(matches) > 0
        for entry in matches:
            assert set(entry.keys()) == {
                "rule_id", "matched_at", "commentary_excerpt",
                "provenance", "severity",
            }


class TestCommentarySection:
    def test_section_schema(self):
        m = _baseline_manifest()
        section = commentary_section_for_manifest(m)
        assert section["version"]
        assert isinstance(section["matched"], list)


class TestSidecarSerialization:
    def test_zip_entry_present_when_commentary_attached(self):
        m = _baseline_manifest()
        m["commentary"] = commentary_section_for_manifest(m)
        entries = _zip_entries_from_manifest(m)
        assert "commentary/matched.json" in entries
        # Decode and verify shape
        body = json.loads(entries["commentary/matched.json"].decode("utf-8"))
        assert "version" in body
        assert "matched" in body

    def test_zip_entry_absent_when_commentary_not_attached(self):
        m = _baseline_manifest()
        # Don't attach commentary
        entries = _zip_entries_from_manifest(m)
        assert "commentary/matched.json" not in entries
        # Backward-compat: old bundles still valid

    def test_zip_sidecar_canonical_json(self):
        """RS#37 extension: sidecar JSON must be canonical inside the zip."""
        m = _baseline_manifest()
        m["commentary"] = commentary_section_for_manifest(m)
        entries = _zip_entries_from_manifest(m)
        raw = entries["commentary/matched.json"].decode("utf-8")
        loaded = json.loads(raw)
        canonical = json.dumps(loaded, sort_keys=True, ensure_ascii=False, indent=2)
        # _canonical_json appends \n (canonical UTF-8)
        assert raw == canonical + "\n" or raw == canonical

    def test_byte_reproducibility_rs36(self):
        """RS#36: serialize_zip_bytes × 3 on same manifest → identical bytes."""
        m = _baseline_manifest()
        m["commentary"] = commentary_section_for_manifest(m)
        a = serialize_zip_bytes(m)
        b = serialize_zip_bytes(m)
        c = serialize_zip_bytes(m)
        assert a == b == c
        # Cross-check via SHA-256 hash (HMAC signing relies on this)
        ha = hashlib.sha256(a).hexdigest()
        hb = hashlib.sha256(b).hexdigest()
        assert ha == hb

    def test_zip_contains_commentary_entry(self):
        """End-to-end: serialize zip, open it, verify commentary entry exists."""
        m = _baseline_manifest()
        m["commentary"] = commentary_section_for_manifest(m)
        zip_bytes = serialize_zip_bytes(m)
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "commentary/matched.json" in names
            body = json.loads(zf.read("commentary/matched.json").decode("utf-8"))
            assert "version" in body
            assert "matched" in body
