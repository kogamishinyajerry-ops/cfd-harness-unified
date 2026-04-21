"""Monotonicity regression for grid-convergence fixture sweeps.

Every case registered as a `grid_convergence` sweep (mesh_20 / mesh_40
/ mesh_80 / mesh_160) must show |measurement - gold| decreasing
monotonically from the coarsest to the finest mesh. This is the
pedagogical contract the `/learn` Mesh-tab slider teaches: as h → 0,
the measured quantity should approach the literature anchor — not
oscillate around it.

Asymptotic noise at the finest mesh CAN produce raw-value dips (e.g.
80² gives 10.80 then 160² gives 10.75 around gold=10.5), but the
|deviation| must still be monotone. Any raw-value dip is acceptable
as long as the dip lands closer to gold than the previous point.

Recommended by Codex round 13 (post-merge review of commit `13b96ca` /
PR #36).
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from ui.backend.services.validation_report import (
    _load_gold_standard,  # noqa: SLF001 — read-only fixture helper
    _load_whitelist,  # noqa: SLF001
    _make_gold_reference,  # noqa: SLF001
)

FIXTURES_ROOT = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "runs"
)

# Every `grid_convergence` sweep in the catalog. Keep in sync with
# ui/frontend/src/pages/learn/LearnCaseDetailPage.tsx::GRID_CONVERGENCE_CASES.
GRID_CONVERGENCE_CASES = [
    "lid_driven_cavity",
    "backward_facing_step",
    "circular_cylinder_wake",
    "turbulent_flat_plate",
    "duct_flow",
    "differential_heated_cavity",
    "plane_channel_flow",
    "impinging_jet",
    "naca0012_airfoil",
    "rayleigh_benard_convection",
]

MESH_RUN_IDS = ["mesh_20", "mesh_40", "mesh_80", "mesh_160"]


def _load_measurement(case_id: str, run_id: str) -> float:
    path = FIXTURES_ROOT / case_id / f"{run_id}_measurement.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return float(doc["measurement"]["value"])


def _resolve_gold_scalar(case_id: str) -> float:
    """Use the live engine's gold-resolution path so this test stays in sync
    with the contract engine. If the engine picks u_plus=5.4 for channel,
    that's what we anchor against; if it picks Cp=1.0 for NACA, same."""
    whitelist = _load_whitelist()
    case = whitelist[case_id]
    gs = _load_gold_standard(case_id)
    gr = _make_gold_reference(case, gs)
    assert gr is not None, f"no gold reference resolved for {case_id}"
    return gr.ref_value


@pytest.mark.parametrize("case_id", GRID_CONVERGENCE_CASES)
def test_grid_convergence_sweep_is_monotone(case_id: str) -> None:
    """|measurement - gold| must decrease monotonically across mesh_20 → mesh_160.

    Raw-value non-monotonicity is allowed as long as each successive
    point lands closer to the gold anchor than the previous one.
    """
    gold = _resolve_gold_scalar(case_id)
    values = [_load_measurement(case_id, rid) for rid in MESH_RUN_IDS]
    deviations = [abs(v - gold) for v in values]

    for prev, curr, prev_id, curr_id in zip(
        deviations,
        deviations[1:],
        MESH_RUN_IDS,
        MESH_RUN_IDS[1:],
    ):
        assert curr <= prev, (
            f"{case_id}: {prev_id} deviation {prev:.6g} < "
            f"{curr_id} deviation {curr:.6g} (gold={gold}, "
            f"values={values}) — sweep must converge toward gold, "
            f"not diverge at the asymptotic end. Either tighten the "
            f"final mesh fixture so |deviation| keeps shrinking, or "
            f"document an explicit exception here."
        )
