"""P3 W3.0.3 (DEC-V61-217 charter) — solver_block_extractor CHT regression.

**SPIKE-class · ZERO extractor code change.** The DEC-V61-211
``solver_block_extractor`` is region-agnostic by construction: the ``controlDict``
lives at top-level ``system/controlDict`` in BOTH single- and multi-region cases
(chtMultiRegionSimpleFoam has a master controlDict at the top level; only
``fvSchemes`` / ``fvSolution`` are per-region). The same generic
``application <name>;`` capture (``_APPLICATION_RE``) therefore reports
``chtMultiRegionSimpleFoam`` / ``chtMultiRegionFoam`` unchanged.

These tests pin that behaviour against a case_002b / case_011-shaped CHT master
controlDict (the corpus ships no real CHT case yet — same synthetic-fixture
approach as W3.0/W3.0.1/W3.0.2). They serve as the charter's canonical example
that "not every P2 extractor needs rewriting" for multi-region.

They also document the W3.0.3 ↔ W3.2 seam: the solver name is *parsed* today, but
the ``case_family_registry`` does NOT yet enumerate a CHT family
(``helper_candidate_applies`` → ``False``). W3.2 is the workstream that registers
``cht_steady_laminar_multi_region``; when it lands, the registry assertion below
flips and must be updated (an intentional cross-workstream tripwire).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ui.backend.services.case_extractors import extract_solver_block_snapshot
from ui.backend.services.case_extractors.solver_block_extractor import (
    _DENSITY_BASED_AT_RISK_SOLVERS as _AT_RISK,
)
from ui.backend.services.case_family_registry import helper_candidate_applies


def _write_cht_master_controldict(case_dir: Path, application: str) -> None:
    """Write a CHT master ``system/controlDict`` with the given application."""
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system" / "controlDict").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }\n"
        f"application     {application};\n"
        "startFrom       startTime;\n"
        "startTime       0;\n"
        "endTime         1000;\n"
        "deltaT          1;\n"
        "writeControl    timeStep;\n"
        "writeInterval   100;\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "cht_solver",
    ["chtMultiRegionSimpleFoam", "chtMultiRegionFoam"],
)
def test_cht_master_controldict_reports_solver(tmp_path: Path, cht_solver: str) -> None:
    """case_002b/case_011-shaped CHT master controlDict → solver reported verbatim.

    Zero extractor code change: the generic application capture handles the CHT
    solver names as-is. delta_t is read from the master controlDict.
    """
    _write_cht_master_controldict(tmp_path, cht_solver)
    snap = extract_solver_block_snapshot(tmp_path)

    assert snap is not None, f"{cht_solver} master controlDict must yield a snapshot"
    assert snap.solver == cht_solver
    assert snap.delta_t == 1.0


@pytest.mark.parametrize(
    "cht_solver",
    ["chtMultiRegionSimpleFoam", "chtMultiRegionFoam"],
)
def test_cht_solver_not_density_based_at_risk(tmp_path: Path, cht_solver: str) -> None:
    """A CHT solver must NOT be treated as density-based-at-risk.

    The V27 density-based path makes a *missing* ``adjustTimeStep`` carry advisor
    meaning. CHT multi-region solvers are not density-based, so a controlDict
    without ``adjustTimeStep`` must keep ``adjust_time_step`` an honest ``None``
    (no fabricated V27 semantics).
    """
    assert cht_solver not in _AT_RISK
    _write_cht_master_controldict(tmp_path, cht_solver)
    snap = extract_solver_block_snapshot(tmp_path)
    assert snap is not None
    assert snap.adjust_time_step is None


def test_cht_steady_family_registered_by_w32a() -> None:
    """W3.0.3 ↔ W3.2a seam (FLIPPED by DEC-V61-223): W3.2a registered the
    ``cht_steady_laminar_multi_region`` family, so the STEADY solver now unlocks
    its helper for the laminar target regime. The TRANSIENT ``chtMultiRegionFoam``
    stays UNregistered per charter Q4 (steady + laminar first; transient deferred)
    — this asymmetry is the intentional tripwire: a future transient sub-DEC
    flips the second assertion.
    """
    # Steady variant: registered by W3.2a → laminar (target regime) applies.
    assert helper_candidate_applies("chtMultiRegionSimpleFoam", "laminar") is True
    # Transient variant: still unregistered (charter Q4 deferral).
    assert helper_candidate_applies("chtMultiRegionFoam", "laminar") is False
