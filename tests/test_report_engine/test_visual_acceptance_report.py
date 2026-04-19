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
    assert result.chart_count == 15
    assert "可视化验收报告" in result.html
    assert "验收基线与未决事项" in result.html
    assert "Q-1" in result.html
    assert "Q-2" in result.html
    assert "试用验收路径" in result.html
    assert "真实 CAD / 前处理渲染" in result.html
    assert "科研级 CFD 后处理" in result.html
    assert "文献 / Benchmark 对比" in result.html
    assert "NACA0012 翼型外流" in result.html
    assert "差分加热方腔自然对流" in result.html
    assert "DHC gold-reference 准确性仍待裁决" in result.html
    assert result.html.count("<img") >= 15
    assert "<svg" not in result.html
    assert "data:image/png;base64" in result.html
    assert 'href="../lid_driven_cavity_benchmark/case_completion_report.md"' in result.html
    assert 'id="case-naca0012_airfoil"' in result.html
    assert "reports/reports/" not in result.html


def test_visual_acceptance_generate_writes_output(tmp_path: Path):
    output = tmp_path / "visual_acceptance.html"
    result = VisualAcceptanceReportGenerator().generate(output_path=output)
    assert output.is_file()
    assert result.output_path == str(output)
    html = output.read_text(encoding="utf-8")
    assert "圆柱绕流卡门涡街" in html
    assert "真实 PNG 图板" in html
    assert "Nu = 77.82" in html


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
