"""DEC-V61-042: integration tests for the extractor edits.

Validates that:
- _extract_nc_nusselt fails closed when the generator didn't plumb
  wall_coord_hot / T_hot_wall / wall_bc_type.
- _extract_nc_nusselt computes Nu via src.wall_gradient.extract_wall_gradient
  when metadata is present.
- _extract_jet_nusselt fails closed when impinging-jet BC metadata is
  missing (previously it would silently emit a radial-gradient result
  of ≈0).
- _extract_jet_nusselt uses the wall-normal stencil instead of the old
  dT/dr path.

These sit alongside tests/test_wall_gradient.py (which covers the
stencil math itself). The point of this file is the WIRING: did the
generator's BC plumbing actually reach the extractor, and does the
extractor correctly refuse to guess when it didn't?
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pytest

from src.foam_agent_adapter import FoamAgentExecutor


@dataclass
class _StubTaskSpec:
    """Minimal TaskSpec stand-in — _extract_* methods only read
    task_spec.boundary_conditions."""
    boundary_conditions: Optional[Dict[str, Any]] = field(default_factory=dict)


def test_nc_extractor_fails_closed_without_bc_metadata() -> None:
    """Without wall_coord_hot / T_hot_wall / wall_bc_type plumbed through,
    the extractor must NOT emit nusselt_number — DEC-V61-036 G1's
    MISSING_TARGET_QUANTITY concern should fire at the comparator."""
    key_quantities: Dict[str, Any] = {}
    result = FoamAgentExecutor._extract_nc_nusselt(
        cxs=[0.005, 0.01, 0.02, 0.03],
        cys=[0.1, 0.1, 0.1, 0.1],
        t_vals=[303.0, 301.0, 300.5, 300.1],
        task_spec=_StubTaskSpec(boundary_conditions={"dT": 10.0, "L": 1.0}),
        key_quantities=key_quantities,
    )
    assert "nusselt_number" not in result
    assert result.get("_nc_wall_gradient_missing_bc_metadata") is True


def test_nc_extractor_uses_3point_stencil_with_metadata() -> None:
    """With BC metadata present, extractor should compute Nu via the
    helper. Construct a linear T profile where the wall-normal gradient
    is known exactly."""
    # Linear temperature: T(x) = T_hot + slope·x, slope=-100/m
    # → gradient = -100; |grad| = 100; dT=10, L=1; Nu = 100·1/10 = 10.0
    T_hot = 305.0
    slope = -100.0
    # Single y-layer, 4 cells in x.
    xs = [0.01, 0.02, 0.03, 0.04]
    ys = [0.5, 0.5, 0.5, 0.5]
    ts = [T_hot + slope * x for x in xs]

    key_quantities: Dict[str, Any] = {}
    bc = {
        "wall_coord_hot": 0.0,
        "T_hot_wall": T_hot,
        "wall_bc_type": "fixedValue",
        "dT": 10.0,
        "L": 1.0,
    }
    result = FoamAgentExecutor._extract_nc_nusselt(
        cxs=xs,
        cys=ys,
        t_vals=ts,
        task_spec=_StubTaskSpec(boundary_conditions=bc),
        key_quantities=key_quantities,
    )
    assert "nusselt_number" in result
    assert result["nusselt_number_source"] == "wall_gradient_stencil_3pt"
    # Linear profile → stencil is exact → Nu = 10.0.
    assert result["nusselt_number"] == pytest.approx(10.0, abs=1e-6)


def test_ij_extractor_fails_closed_without_bc_metadata() -> None:
    """Impinging-jet extractor must emit no nusselt_number when the
    generator didn't plumb plate/inlet temperatures and wall coord.
    Previously it would silently emit 0.00417 via radial differencing."""
    key_quantities: Dict[str, Any] = {}
    result = FoamAgentExecutor._extract_jet_nusselt(
        cxs=[0.0, 0.01, 0.02, 0.03],
        cys=[0.09, 0.09, 0.09, 0.09],
        t_vals=[290.01, 290.01, 290.01, 290.01],
        task_spec=_StubTaskSpec(boundary_conditions={}),
        key_quantities=key_quantities,
    )
    assert "nusselt_number" not in result
    assert result.get("_ij_wall_gradient_missing_bc_metadata") is True


def test_ij_extractor_wall_normal_stencil_recovers_known_gradient() -> None:
    """Wall-normal stencil on a known exponential BL at a single radial
    bin. Verifies the extractor correctly uses the helper on a column of
    cy cells below the plate, keyed by radial position |cx|."""
    # Plate at cy=0.1 (wall_coord_plate). T_plate=290, T_inlet=310 → ΔT=20.
    # T(cy) = 290 + 20·(1 − exp((cy−0.1)/δ_T)), δ_T = 0.005
    # At cy = 0.1: T = 290 (matches BC). Gradient at wall:
    #   dT/d(cy) |_{cy=0.1} = −20/δ_T = −4000  (T decreases into interior)
    # Wait: define T(cy) = T_plate + (T_inlet - T_plate) · (1 − exp((cy − plate)/δ))
    # At cy=plate (0.1): T=T_plate. At cy → −∞: T → T_inlet.
    # dT/d(cy) at plate = (T_inlet - T_plate) · (−1/δ) · exp(0) = -20/δ = -4000
    # |grad| = 4000; Nu = D_nozzle · 4000 / ΔT = 0.05 · 4000 / 20 = 10
    plate = 0.1
    delta = 0.005
    T_plate = 290.0
    T_inlet = 310.0

    def T(cy: float) -> float:
        return T_plate + (T_inlet - T_plate) * (1.0 - math.exp((cy - plate) / delta))

    # Cells at a single radial bin r=0 (cx=0), at cy = 0.099, 0.098, 0.097
    # (interior cells below the plate).
    xs = [0.0, 0.0, 0.0]
    ys = [0.099, 0.098, 0.097]
    ts = [T(cy) for cy in ys]

    bc = {
        "wall_coord_plate": plate,
        "T_plate": T_plate,
        "T_inlet": T_inlet,
        "wall_bc_type": "fixedValue",
        "D_nozzle": 0.05,
    }
    result = FoamAgentExecutor._extract_jet_nusselt(
        cxs=xs,
        cys=ys,
        t_vals=ts,
        task_spec=_StubTaskSpec(boundary_conditions=bc),
        key_quantities={},
    )
    assert "nusselt_number" in result
    assert result["nusselt_number_source"] == "wall_gradient_stencil_3pt"
    # Stencil on a mildly-curved exponential at dy=0.001 spacing should
    # recover |grad|≈4000 within ~15%; Nu = 10 ± 1.5.
    Nu = result["nusselt_number"]
    assert 8.0 < Nu < 12.5, f"expected Nu ≈ 10, got {Nu}"


def test_ij_extractor_skips_radial_bins_with_fewer_than_2_cells() -> None:
    """Radial bins with only 1 interior cell must be skipped without
    raising. Only bins with ≥2 cells contribute to the Nu profile."""
    bc = {
        "wall_coord_plate": 0.1,
        "T_plate": 290.0,
        "T_inlet": 310.0,
        "wall_bc_type": "fixedValue",
        "D_nozzle": 0.05,
    }
    # Single isolated cell at r=0, two cells at r=0.01.
    result = FoamAgentExecutor._extract_jet_nusselt(
        cxs=[0.0, 0.01, 0.01],
        cys=[0.095, 0.095, 0.090],
        t_vals=[295.0, 295.0, 296.0],
        task_spec=_StubTaskSpec(boundary_conditions=bc),
        key_quantities={},
    )
    # r=0 skipped (1 cell); r=0.01 has 2 cells → Nu emitted from that bin.
    assert "nusselt_number" in result
    assert len(result.get("nusselt_number_profile", [])) == 1
    assert result["nusselt_number_profile_r"] == [0.01]
