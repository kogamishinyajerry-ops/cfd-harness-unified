"""Coverage for scripts/generate_reports.py CLI (committed without direct tests)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "generate_reports.py"


def _load_module():
    """Import the script as a module without executing __main__."""
    spec = importlib.util.spec_from_file_location("generate_reports_cli", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cli():
    return _load_module()


class TestUnknownCaseId:
    def test_exits_2_on_unknown(self, cli):
        code = cli.main(["generate_reports.py", "definitely_not_a_case"])
        assert code == 2

    def test_exits_2_on_mixed_known_and_unknown(self, cli):
        code = cli.main([
            "generate_reports.py",
            "lid_driven_cavity_benchmark",
            "definitely_not_a_case",
        ])
        assert code == 2


class TestDefaultRun:
    def test_no_args_renders_all_available(self, cli, capsys):
        code = cli.main(["generate_reports.py"])
        captured = capsys.readouterr()
        assert "Rendered" in captured.out
        # At least one case must render for CLI to succeed (code 0)
        if "Rendered 0" in captured.out:
            assert code == 1
        else:
            assert code == 0

    def test_explicit_ldc_renders_ok(self, cli, capsys):
        code = cli.main(["generate_reports.py", "lid_driven_cavity_benchmark"])
        captured = capsys.readouterr()
        assert code == 0
        assert "OK    lid_driven_cavity_benchmark" in captured.out
        assert "sections=7" in captured.out


class TestSkipBehavior:
    def test_skips_case_without_auto_verify_report(self, cli, capsys):
        # fully_developed_turbulent_pipe_flow is in SUPPORTED_CASE_IDS
        # but has no reports/*/auto_verify_report.yaml — expected SKIP path.
        code = cli.main([
            "generate_reports.py",
            "fully_developed_turbulent_pipe_flow",
        ])
        captured = capsys.readouterr()
        # Zero rendered, one skipped → exit code 1 per main() contract
        assert code == 1
        assert "SKIP  fully_developed_turbulent_pipe_flow" in captured.out
        assert "Rendered 0 / 1" in captured.out


class TestShellInvocation:
    """Smoke test the actual subprocess entry point, not just main()."""

    def test_script_runs_as_subprocess(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "lid_driven_cavity_benchmark"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert "OK" in result.stdout
        assert "lid_driven_cavity_benchmark" in result.stdout

    def test_script_unknown_case_exits_2(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "bogus_case_id"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        assert result.returncode == 2
        assert "unsupported case_ids" in result.stderr


class TestSupportedCaseIdsExport:
    def test_supported_case_ids_is_non_empty(self, cli):
        assert len(cli.SUPPORTED_CASE_IDS) > 0

    def test_supported_case_ids_includes_ldc(self, cli):
        assert "lid_driven_cavity_benchmark" in cli.SUPPORTED_CASE_IDS
