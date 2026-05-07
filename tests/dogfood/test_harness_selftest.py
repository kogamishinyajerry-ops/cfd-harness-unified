"""Tests for scripts/dogfood/harness.py --selftest path."""
from __future__ import annotations

from pathlib import Path

from scripts.dogfood.harness import main


def test_harness_selftest_returns_zero(capsys) -> None:
    rc = main(["--selftest"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Selftest run_id=" in captured.out


def test_harness_production_missing_args_returns_two() -> None:
    rc = main([])  # no --selftest, no --case
    assert rc == 2
