from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from report_engine import ContractDashboardGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_contract_dashboard.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_contract_dashboard_cli", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_dashboard_render_contains_core_sections():
    result = ContractDashboardGenerator().render()
    assert result.case_count == 10
    assert "10-case Physics Contract Dashboard" in result.html
    assert "物理契约状态分布" in result.html
    assert "冻结的治理边界" in result.html
    assert "Q-1" in result.html
    assert "Q-2" in result.html
    assert "方腔顶盖驱动流" in result.html
    # DEC-V61-011 (Gate Q-2 Path A, 2026-04-20): pipe → square-duct rename.
    # The canonical title is now "全发展湍流方管流" (Jones 1976 square-duct
    # correlation). "全发展湍流管流" was a physics-mislabel for a circular pipe.
    assert "全发展湍流方管流" in result.html
    assert "轴对称冲击射流" in result.html
    assert "Observable mismatch" in result.html
    assert "visual_acceptance_report.html" in result.html
    # Contract-class distribution drifts case-by-case as gold YAMLs are
    # reclassified (DEC-V61-011 duct rename, Q-new Case 4 TFP laminar
    # promotion, DEC-V61-040 UNKNOWN surface, demo-first round 2026-04-22
    # SATISFIED recognition). Pin current distribution so accidental
    # re-classification is caught. After the 2026-04-22 backfill there
    # should be NO UNKNOWN cases — every whitelist entry has an explicit
    # physics_contract block.
    assert result.summary_counts["SATISFIED"] == 3
    assert result.summary_counts["COMPATIBLE"] == 3
    assert result.summary_counts["COMPATIBLE_WITH_SILENT_PASS_HAZARD"] == 1
    assert result.summary_counts["INCOMPATIBLE"] == 1
    assert result.summary_counts.get("UNKNOWN", 0) == 0  # all 10 cases contract-labelled


def test_contract_dashboard_generate_writes_output(tmp_path: Path):
    output = tmp_path / "contract_status_dashboard.html"
    result = ContractDashboardGenerator().generate(output_path=output)
    assert output.is_file()
    assert result.output_path == str(output)
    assert result.snapshot_path
    assert Path(result.snapshot_path).is_file()
    assert result.manifest_path
    manifest_path = Path(result.manifest_path)
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["canonical_path"] == str(output)
    assert manifest["snapshot_path"] == str(Path(result.snapshot_path))
    assert manifest["manifest_path"] == str(manifest_path)
    assert manifest["case_count"] == 10
    assert manifest["class_counts"]["COMPATIBLE"] == 3
    assert any(ref.startswith("Q-1") for ref in manifest["open_gate_refs"])
    assert any(ref.startswith("Q-2") for ref in manifest["open_gate_refs"])
    html = output.read_text(encoding="utf-8")
    assert "PENDING_RE_RUN" in html
    # Post-DEC-V61-011 the "materialized auto_verify_report" shibboleth was
    # removed; pin the lasting invariant instead — dashboard must surface
    # its auto_verify_report.yaml provenance.
    assert "auto_verify_report.yaml" in html


def test_contract_dashboard_cli_default(capsys):
    cli = _load_module()
    code = cli.main(["generate_contract_dashboard.py"])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK    contract_dashboard" in captured.out
    assert "snapshot=" in captured.out
    assert "manifest=" in captured.out
    assert "cases=10" in captured.out


def test_contract_dashboard_cli_rejects_extra_args(capsys):
    cli = _load_module()
    code = cli.main(["generate_contract_dashboard.py", "bogus"])
    captured = capsys.readouterr()
    assert code == 2
    assert "does not accept case_ids" in captured.err


def test_contract_dashboard_script_runs_as_subprocess():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "contract_dashboard" in result.stdout
