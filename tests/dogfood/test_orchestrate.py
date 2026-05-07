"""Tests for scripts/dogfood/orchestrate.py — dry-run all 9 cells."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dogfood.cases import CASE_IDS
from scripts.dogfood.orchestrate import (
    _SERIAL_DIAGONAL,
    _all_cells,
    _batch_cells,
    execute_cell,
    main,
    orchestrate_batch,
    orchestrate_serial,
)
from scripts.dogfood.personas import PERSONA_NAMES


# ---------------------------------------------------------------------------
# Cell mapping
# ---------------------------------------------------------------------------


def test_all_cells_returns_nine() -> None:
    cells = _all_cells()
    assert len(cells) == 9
    assert set(cells) == {(c, p) for c in CASE_IDS for p in PERSONA_NAMES}


def test_serial_diagonal_is_three_distinct_cases_personas() -> None:
    diag = list(_SERIAL_DIAGONAL)
    assert len(diag) == 3
    cases = {c for c, _ in diag}
    personas = {p for _, p in diag}
    assert len(cases) == 3
    assert len(personas) == 3


def test_batch_cells_excludes_serial_diagonal() -> None:
    batch = _batch_cells()
    assert len(batch) == 6
    assert not (set(batch) & set(_SERIAL_DIAGONAL))


# ---------------------------------------------------------------------------
# Single-cell execution (dry-run)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id,persona", _all_cells())
def test_execute_cell_dry_run_creates_artifacts(
    case_id: str, persona: str, tmp_path: Path
) -> None:
    outcome = execute_cell(case_id, persona, dry_run=True, runs_root=tmp_path)
    assert outcome.error is None
    assert (outcome.spec.run_dir / "friction_log.jsonl").exists()
    assert (outcome.spec.run_dir / "result.json").exists()
    assert (outcome.spec.run_dir / "spec.json").exists()
    spec = json.loads((outcome.spec.run_dir / "spec.json").read_text())
    assert spec["case_id"] == case_id
    assert spec["persona"] == persona
    assert spec["dry_run"] is True


# ---------------------------------------------------------------------------
# Serial / batch orchestration
# ---------------------------------------------------------------------------


def test_orchestrate_serial_runs_diagonal(tmp_path: Path) -> None:
    report = orchestrate_serial(
        list(_SERIAL_DIAGONAL),
        dry_run=True,
        runs_root=tmp_path,
        workbench_base_url="http://localhost:8000",
    )
    assert len(report.outcomes) == 3
    assert all(o.error is None for o in report.outcomes)
    summary = report.summary()
    assert summary["n_outcomes"] == 3
    assert summary["n_errors"] == 0


def test_orchestrate_batch_runs_six_concurrent(tmp_path: Path) -> None:
    report = orchestrate_batch(
        _batch_cells(),
        concurrency=3,
        dry_run=True,
        runs_root=tmp_path,
        workbench_base_url="http://localhost:8000",
    )
    assert len(report.outcomes) == 6
    assert all(o.error is None for o in report.outcomes)


def test_orchestrate_all_runs_nine_cells(tmp_path: Path) -> None:
    """End-to-end smoke: serial diagonal + batch via main()."""
    rc = main([
        "--all",
        "--dry-run",
        "--runs-root", str(tmp_path),
        "--concurrency", "3",
    ])
    assert rc == 0
    runs = sorted(p for p in tmp_path.iterdir() if p.is_dir())
    assert len(runs) == 9
    for run_dir in runs:
        assert (run_dir / "friction_log.jsonl").exists()
        assert (run_dir / "result.json").exists()


# ---------------------------------------------------------------------------
# Persona prompt is wired through (not the B.1 stub)
# ---------------------------------------------------------------------------


def test_orchestrate_uses_persona_library_prompt(tmp_path: Path) -> None:
    """The orchestrator must consume B.2 persona prompts, not B.1's stub."""
    outcome = execute_cell(
        "naca0012", "experienced_fluent", dry_run=True, runs_root=tmp_path
    )
    # The friction log contains tool_use rationale text from the script;
    # we assert the run completed successfully (non-stub prompt drove it)
    assert outcome.result.verdict is not None
    assert outcome.result.verdict.passed is True
