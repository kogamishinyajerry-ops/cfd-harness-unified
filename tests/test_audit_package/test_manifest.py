"""Tests for audit_package.manifest (Phase 5 · PR-5a · DEC-V61-012)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.audit_package import SCHEMA_VERSION, build_manifest
from src.audit_package.manifest import (
    _extract_first_heading,
    _extract_frontmatter_field,
    _load_decision_trail,
    _load_gold_standard,
    _load_run_inputs,
    _load_run_outputs,
    _load_whitelist_entry,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic repo layout inside tmp_path
# ---------------------------------------------------------------------------

def _synth_repo(tmp_path: Path) -> Path:
    """Minimal repo-root layout with knowledge/ + .planning/ populated."""
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "knowledge" / "gold_standards").mkdir()
    (tmp_path / ".planning").mkdir()
    (tmp_path / ".planning" / "decisions").mkdir()
    (tmp_path / "knowledge" / "whitelist.yaml").write_text(
        "cases:\n"
        "  - id: duct_flow\n"
        "    name: Fully Developed Turbulent Square-Duct Flow\n"
        "    reference: Jones 1976\n"
        "    solver: simpleFoam\n"
        "    turbulence_model: k-epsilon\n"
        "    parameters:\n"
        "      Re: 50000\n"
        "    gold_standard:\n"
        "      reference_values:\n"
        "        - {Re: 50000, f: 0.0185}\n"
        "      tolerance: 0.10\n",
        encoding="utf-8",
    )
    (tmp_path / "knowledge" / "gold_standards" / "duct_flow.yaml").write_text(
        "case_id: duct_flow\n"
        "source: Jones 1976\n"
        "legacy_case_ids:\n"
        "  - fully_developed_pipe\n"
        "  - fully_developed_turbulent_pipe_flow\n"
        "observables:\n"
        "  - name: friction_factor\n"
        "    ref_value: 0.0185\n",
        encoding="utf-8",
    )
    return tmp_path


def _synth_run_output(run_dir: Path) -> Path:
    """Populate a fake OpenFOAM case dir with the input/output files build_manifest reads."""
    (run_dir / "system").mkdir(parents=True)
    (run_dir / "system" / "controlDict").write_text("application simpleFoam;\nendTime 1000;\n")
    (run_dir / "system" / "blockMeshDict").write_text("FoamFile { object blockMeshDict; }\n")
    (run_dir / "system" / "fvSchemes").write_text("ddtSchemes { default steadyState; }\n")
    (run_dir / "system" / "fvSolution").write_text("solvers { p { solver GAMG; } }\n")
    (run_dir / "constant").mkdir()
    (run_dir / "constant" / "physicalProperties").write_text("nu [0 2 -1 0 0] 2e-6;\n")
    (run_dir / "0").mkdir()
    (run_dir / "0" / "U").write_text("dimensions [0 1 -1 0 0];\ninternalField uniform (1 0 0);\n")
    (run_dir / "0" / "p").write_text("dimensions [0 2 -2 0 0];\ninternalField uniform 0;\n")
    (run_dir / "log.simpleFoam").write_text(
        "\n".join(f"iter {i} Solving for Ux, Initial residual = {1e-6*i:.2e}" for i in range(200))
        + "\nEnd\n"
    )
    pp = run_dir / "postProcessing" / "sets" / "1000"
    pp.mkdir(parents=True)
    (pp / "centerline_U.xy").write_text("0.5 0 0 -0.037 0 0\n0.5 0.5 0 0.025 0 0\n")
    return run_dir


# ---------------------------------------------------------------------------
# Low-level helper tests
# ---------------------------------------------------------------------------

class TestLoadWhitelistEntry:
    def test_returns_case_by_id(self, tmp_path):
        repo = _synth_repo(tmp_path)
        entry = _load_whitelist_entry("duct_flow", repo / "knowledge" / "whitelist.yaml")
        assert entry is not None
        assert entry["id"] == "duct_flow"
        assert entry["parameters"]["Re"] == 50000

    def test_returns_none_for_unknown_id(self, tmp_path):
        repo = _synth_repo(tmp_path)
        entry = _load_whitelist_entry("nonexistent", repo / "knowledge" / "whitelist.yaml")
        assert entry is None

    def test_matches_legacy_alias(self, tmp_path):
        repo = _synth_repo(tmp_path)
        entry = _load_whitelist_entry(
            "fully_developed_pipe",
            repo / "knowledge" / "whitelist.yaml",
            legacy_aliases=("duct_flow",),
        )
        assert entry is not None
        assert entry["id"] == "duct_flow"

    def test_returns_none_when_whitelist_missing(self, tmp_path):
        assert _load_whitelist_entry("x", tmp_path / "nope.yaml") is None


class TestLoadGoldStandard:
    def test_returns_gold_for_canonical(self, tmp_path):
        repo = _synth_repo(tmp_path)
        gold = _load_gold_standard("duct_flow", repo / "knowledge" / "gold_standards")
        assert gold is not None
        assert gold["case_id"] == "duct_flow"

    def test_falls_back_to_legacy_alias(self, tmp_path):
        repo = _synth_repo(tmp_path)
        # Gold file named duct_flow.yaml, asked for by legacy id → alias fallback
        gold = _load_gold_standard(
            "fully_developed_pipe",
            repo / "knowledge" / "gold_standards",
            legacy_aliases=("duct_flow",),
        )
        assert gold is not None
        assert gold["case_id"] == "duct_flow"

    def test_returns_none_when_missing(self, tmp_path):
        repo = _synth_repo(tmp_path)
        assert _load_gold_standard("nonexistent", repo / "knowledge" / "gold_standards") is None


class TestLoadRunInputs:
    def test_collects_system_files(self, tmp_path):
        run = _synth_run_output(tmp_path / "run")
        inputs = _load_run_inputs(run)
        assert "system/controlDict" in inputs
        assert "system/blockMeshDict" in inputs
        assert "application simpleFoam" in inputs["system/controlDict"]

    def test_collects_initial_fields(self, tmp_path):
        run = _synth_run_output(tmp_path / "run")
        inputs = _load_run_inputs(run)
        assert "0/" in inputs
        assert "U" in inputs["0/"]
        assert "p" in inputs["0/"]

    def test_empty_when_no_inputs(self, tmp_path):
        (tmp_path / "empty_run").mkdir()
        assert _load_run_inputs(tmp_path / "empty_run") == {}


class TestLoadRunOutputs:
    def test_solver_log_tail_captured(self, tmp_path):
        run = _synth_run_output(tmp_path / "run")
        outputs = _load_run_outputs(run)
        assert outputs["solver_log_name"] == "log.simpleFoam"
        # Tail should include final lines
        assert "End" in outputs["solver_log_tail"]

    def test_postprocessing_listing(self, tmp_path):
        run = _synth_run_output(tmp_path / "run")
        outputs = _load_run_outputs(run)
        assert "postProcessing_sets_files" in outputs
        assert any("centerline_U.xy" in f for f in outputs["postProcessing_sets_files"])

    def test_empty_when_no_outputs(self, tmp_path):
        (tmp_path / "empty_run").mkdir()
        assert _load_run_outputs(tmp_path / "empty_run") == {}


class TestDecisionTrailAndFrontmatter:
    def test_extract_frontmatter_field_basic(self):
        text = "---\ndecision_id: DEC-V61-011\nfoo: bar\n---\n# Title\n"
        assert _extract_frontmatter_field(text, "decision_id") == "DEC-V61-011"
        assert _extract_frontmatter_field(text, "foo") == "bar"
        assert _extract_frontmatter_field(text, "missing") is None

    def test_extract_first_heading(self):
        text = "---\nfoo: bar\n---\n\n# DEC-V61-011: Path A\n\nBody."
        assert _extract_first_heading(text) == "DEC-V61-011: Path A"

    def test_extract_first_heading_none_when_absent(self):
        assert _extract_first_heading("no headings here") is None

    def test_decision_trail_grep_matches_case_id(self, tmp_path):
        repo = _synth_repo(tmp_path)
        dec = repo / ".planning" / "decisions" / "2026-04-20_foo.md"
        dec.write_text(
            "---\ndecision_id: DEC-V61-011\n---\n# Q-2 Path A\nRenames fully_developed_pipe → duct_flow\n",
            encoding="utf-8",
        )
        trail = _load_decision_trail("duct_flow", repo / ".planning" / "decisions")
        assert len(trail) == 1
        assert trail[0]["decision_id"] == "DEC-V61-011"
        assert trail[0]["title"].startswith("Q-2")

    def test_decision_trail_matches_legacy_alias(self, tmp_path):
        repo = _synth_repo(tmp_path)
        dec = repo / ".planning" / "decisions" / "old_dec.md"
        dec.write_text(
            "---\ndecision_id: DEC-ADWM-001\n---\n# Legacy\nRefers to fully_developed_pipe.\n",
            encoding="utf-8",
        )
        trail = _load_decision_trail(
            "duct_flow",
            repo / ".planning" / "decisions",
            legacy_aliases=("fully_developed_pipe",),
        )
        assert len(trail) == 1
        assert trail[0]["decision_id"] == "DEC-ADWM-001"

    def test_decision_trail_stable_sort_by_id(self, tmp_path):
        repo = _synth_repo(tmp_path)
        for i, did in enumerate(["DEC-V61-011", "DEC-V61-004", "DEC-V61-010"]):
            (repo / ".planning" / "decisions" / f"dec_{i}.md").write_text(
                f"---\ndecision_id: {did}\n---\n# {did}\nduct_flow\n",
                encoding="utf-8",
            )
        trail = _load_decision_trail("duct_flow", repo / ".planning" / "decisions")
        ids = [entry["decision_id"] for entry in trail]
        assert ids == sorted(ids) == ["DEC-V61-004", "DEC-V61-010", "DEC-V61-011"]


# ---------------------------------------------------------------------------
# build_manifest integration
# ---------------------------------------------------------------------------

class TestBuildManifestIntegration:
    def test_minimal_mock_manifest_without_run_output(self, tmp_path, monkeypatch):
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        manifest = build_manifest(
            case_id="duct_flow",
            run_id="abc123",
            build_fingerprint="2026-04-20T23:55:00Z",
            solver_name="simpleFoam",
        )
        assert manifest["schema_version"] == SCHEMA_VERSION
        assert manifest["manifest_id"] == "duct_flow-abc123"
        assert manifest["build_fingerprint"] == "2026-04-20T23:55:00Z"
        assert manifest["case"]["id"] == "duct_flow"
        assert manifest["case"]["whitelist_entry"]["parameters"]["Re"] == 50000
        assert manifest["case"]["gold_standard"]["case_id"] == "duct_flow"
        assert manifest["run"]["status"] == "no_run_output"
        assert manifest["run"]["solver"] == "simpleFoam"
        assert manifest["measurement"]["key_quantities"] == {}
        assert manifest["measurement"]["comparator_verdict"] is None
        # L3 rename drift detection (Codex round 9 Note #2): the renamed
        # field must be present AND the legacy key must be absent from the
        # manifest dict itself. This catches a future regression that
        # reintroduces `generated_at` into manifest.json while the route
        # response stays clean.
        assert "generated_at" not in manifest

    def test_manifest_with_run_output_has_inputs_and_outputs(self, tmp_path, monkeypatch):
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        run_dir = _synth_run_output(tmp_path / "run_xyz")
        manifest = build_manifest(
            case_id="duct_flow",
            run_id="run_xyz",
            run_output_dir=run_dir,
            build_fingerprint="2026-04-20T23:55:00Z",
        )
        assert manifest["run"]["status"] == "output_present"
        assert "inputs" in manifest["run"]
        assert "outputs" in manifest["run"]
        assert "system/controlDict" in manifest["run"]["inputs"]
        assert manifest["run"]["outputs"]["solver_log_name"] == "log.simpleFoam"

    def test_measurement_and_audit_concerns_passthrough(self, tmp_path, monkeypatch):
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        manifest = build_manifest(
            case_id="duct_flow",
            run_id="m1",
            measurement={"friction_factor": 0.0183, "source": "sampleDict_direct"},
            comparator_verdict="PASS",
            audit_concerns=[{"code": "FB-SPALDING", "severity": "INFO"}],
            build_fingerprint="2026-04-20T23:55:00Z",
        )
        assert manifest["measurement"]["key_quantities"]["friction_factor"] == 0.0183
        assert manifest["measurement"]["comparator_verdict"] == "PASS"
        assert manifest["measurement"]["audit_concerns"][0]["code"] == "FB-SPALDING"

    def test_byte_stable_across_two_invocations(self, tmp_path, monkeypatch):
        """Two identical calls with same build_fingerprint → byte-identical JSON."""
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        kwargs = dict(
            case_id="duct_flow",
            run_id="stable",
            build_fingerprint="2026-04-20T23:55:00Z",
            measurement={"friction_factor": 0.0185},
            comparator_verdict="PASS",
        )
        m1 = build_manifest(**kwargs)
        m2 = build_manifest(**kwargs)
        s1 = json.dumps(m1, sort_keys=True, ensure_ascii=False)
        s2 = json.dumps(m2, sort_keys=True, ensure_ascii=False)
        assert s1 == s2

    def test_decision_trail_picks_up_matching_decs(self, tmp_path, monkeypatch):
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        # Two DECs: one matches canonical id, one matches legacy via gold.legacy_case_ids
        (repo / ".planning" / "decisions" / "dec_011.md").write_text(
            "---\ndecision_id: DEC-V61-011\n---\n# Q-2 Path A\nRenames duct_flow.\n",
            encoding="utf-8",
        )
        (repo / ".planning" / "decisions" / "dec_legacy.md").write_text(
            "---\ndecision_id: DEC-ADWM-004\n---\n# Legacy\nfully_developed_pipe FUSE record.\n",
            encoding="utf-8",
        )
        manifest = build_manifest(
            case_id="duct_flow",
            run_id="dt",
            build_fingerprint="2026-04-20T23:55:00Z",
        )
        ids = [entry["decision_id"] for entry in manifest["decision_trail"]]
        # gold.legacy_case_ids triggers pickup of the fully_developed_pipe DEC too
        assert "DEC-V61-011" in ids
        assert "DEC-ADWM-004" in ids

    def test_missing_whitelist_entry_sets_none_not_raises(self, tmp_path, monkeypatch):
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        manifest = build_manifest(
            case_id="totally_unknown_case",
            run_id="r1",
            build_fingerprint="2026-04-20T23:55:00Z",
        )
        assert manifest["case"]["whitelist_entry"] is None
        assert manifest["case"]["gold_standard"] is None
        assert manifest["decision_trail"] == []

    def test_legacy_case_ids_flow_from_gold_file(self, tmp_path, monkeypatch):
        """When gold.legacy_case_ids is populated, decision-trail grep expands."""
        repo = _synth_repo(tmp_path)
        monkeypatch.setattr("src.audit_package.manifest._REPO_ROOT", repo)
        monkeypatch.setattr("src.audit_package.manifest._WHITELIST_PATH", repo / "knowledge" / "whitelist.yaml")
        monkeypatch.setattr("src.audit_package.manifest._GOLD_STANDARDS_ROOT", repo / "knowledge" / "gold_standards")
        monkeypatch.setattr("src.audit_package.manifest._DECISIONS_ROOT", repo / ".planning" / "decisions")
        manifest = build_manifest(
            case_id="duct_flow",
            run_id="r1",
            build_fingerprint="2026-04-20T23:55:00Z",
        )
        assert "fully_developed_pipe" in manifest["case"]["legacy_ids"]
        assert "fully_developed_turbulent_pipe_flow" in manifest["case"]["legacy_ids"]
