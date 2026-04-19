from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from report_engine import VisualAcceptanceReportGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_visual_acceptance_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_visual_acceptance_report_cli", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_visual_acceptance_render_contains_delivery_sections():
    result = VisualAcceptanceReportGenerator().render()
    assert result.case_count == 5
    assert result.chart_count == 10
    assert "Visual Acceptance Report" in result.html
    assert "CAD Pre-Processing" in result.html
    assert "CFD Post-Processing" in result.html
    assert "NACA 0012 Airfoil External Flow" in result.html
    assert "Differential Heated Cavity" in result.html
    assert result.html.count("<svg") >= 10
    assert 'href="../lid_driven_cavity_benchmark/case_completion_report.md"' in result.html
    assert "reports/reports/" not in result.html


def test_visual_acceptance_generate_writes_output(tmp_path: Path):
    output = tmp_path / "visual_acceptance.html"
    result = VisualAcceptanceReportGenerator().generate(output_path=output)
    assert output.is_file()
    assert result.output_path == str(output)
    assert "wake-centerline deficit" in output.read_text(encoding="utf-8")


def test_visual_acceptance_cli_default(capsys):
    cli = _load_module()
    code = cli.main(["generate_visual_acceptance_report.py"])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK    visual_acceptance_report" in captured.out
    assert "cases=5" in captured.out


def test_visual_acceptance_cli_unknown_case(capsys):
    cli = _load_module()
    code = cli.main(["generate_visual_acceptance_report.py", "bogus_case"])
    captured = capsys.readouterr()
    assert code == 2
    assert "unsupported visual case_ids" in captured.err


def test_visual_acceptance_script_runs_as_subprocess():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "visual_acceptance_report" in result.stdout
