"""DEC-V61-042: tests for src/wall_gradient.py (3-point one-sided stencil).

Coverage:
- Analytic linear field → stencil is exact (machine precision).
- Analytic quadratic field → stencil is exact to machine precision
  (3-point one-sided is designed for quadratic exactness).
- Exponential BL profile on coarse mesh → 3-point error <10%; the
  baseline 1-point midpoint method errors ~21% — demonstrates the
  accuracy win motivating the DEC.
- fixedGradient BC returns the BC value verbatim, raises if value
  missing (fail-closed contract).
- Unknown BC type raises.
- <2 interior cells raises.
- Non-monotonic wall-normal layout raises.
"""

from __future__ import annotations

import math

import pytest

from src.wall_gradient import (
    BCContractViolation,
    WallGradientStencil,
    extract_wall_gradient,
)


def test_linear_profile_is_exact() -> None:
    # f(x) = 5 + 3x, f'(x_w=0) = 3 everywhere.
    grad = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=5.0,
        coords=[0.1, 0.3],
        values=[5.3, 5.9],
        bc_type="fixedValue",
    )
    assert grad == pytest.approx(3.0, abs=1e-12)


def test_quadratic_profile_is_exact() -> None:
    # f(x) = 1 + 2x + x^2, f'(0) = 2. 3-point one-sided must nail this
    # because the stencil is exact for quadratic functions on non-uniform
    # spacing.
    grad = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=1.0,
        coords=[0.1, 0.2],
        values=[1.0 + 2 * 0.1 + 0.1 ** 2, 1.0 + 2 * 0.2 + 0.2 ** 2],
        bc_type="fixedValue",
    )
    assert grad == pytest.approx(2.0, abs=1e-12)


def test_exponential_bl_3point_beats_1point() -> None:
    """Motivation test: on an exponential-like BL with only 2-3 cells
    resolving it, the 3-point one-sided stencil is <10% off while the
    1-point midpoint method (what the old extractors used) is ~20% off.
    """
    # T(y) = 1 - exp(-y/delta), delta=0.01. True gradient at y=0 is 1/delta = 100.
    delta = 0.01

    def T(y: float) -> float:
        return 1.0 - math.exp(-y / delta)

    # Coarse wall-packed mesh: y_cell1 = 0.005, y_cell2 = 0.015
    coords = [0.005, 0.015]
    values = [T(0.005), T(0.015)]
    grad_3pt = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=T(0.0),
        coords=coords,
        values=values,
        bc_type="fixedValue",
    )
    # 3-point: within 10% of the true 100.
    assert abs(grad_3pt - 100.0) / 100.0 < 0.10, (
        f"3-point stencil {grad_3pt:.3f} vs true 100.0 (err="
        f"{abs(grad_3pt - 100.0):.3f})"
    )
    # Cross-check: the old 1-point midpoint method is much worse.
    grad_1pt = (values[1] - values[0]) / (coords[1] - coords[0])
    assert abs(grad_1pt - 100.0) / 100.0 > 0.15, (
        "1-point midpoint should be meaningfully worse — "
        "if this asserts fires, the motivating case has drifted"
    )


def test_fixed_gradient_returns_bc_value() -> None:
    grad = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=300.0,
        coords=[0.01, 0.02],
        values=[300.1, 300.3],  # intentionally inconsistent with BC
        bc_type="fixedGradient",
        bc_gradient=15.0,
    )
    assert grad == 15.0  # BC wins — interior values ignored.


def test_fixed_gradient_missing_value_raises() -> None:
    with pytest.raises(BCContractViolation, match="bc_gradient is None"):
        extract_wall_gradient(
            wall_coord=0.0,
            wall_value=300.0,
            coords=[0.01, 0.02],
            values=[300.1, 300.3],
            bc_type="fixedGradient",
        )


def test_unknown_bc_type_raises() -> None:
    with pytest.raises(BCContractViolation, match="Unsupported wall BC type"):
        WallGradientStencil(
            wall_coord=0.0,
            wall_value=300.0,
            coords=(0.01, 0.02),
            values=(300.1, 300.3),
            bc_type="mixedMagic",  # type: ignore[arg-type]
        ).compute()


def test_fewer_than_two_cells_raises() -> None:
    with pytest.raises(BCContractViolation, match="requires ≥2 interior cells"):
        extract_wall_gradient(
            wall_coord=0.0,
            wall_value=300.0,
            coords=[0.01],
            values=[300.1],
            bc_type="fixedValue",
        )


def test_coords_values_length_mismatch_raises() -> None:
    with pytest.raises(BCContractViolation, match="length mismatch"):
        extract_wall_gradient(
            wall_coord=0.0,
            wall_value=300.0,
            coords=[0.01, 0.02, 0.03],
            values=[300.1, 300.3],
            bc_type="fixedValue",
        )


def test_wall_inside_cells_raises() -> None:
    # Wall coord between the two cells — non-monotonic.
    with pytest.raises(BCContractViolation, match="Non-monotonic wall-normal"):
        extract_wall_gradient(
            wall_coord=0.15,
            wall_value=300.0,
            coords=[0.1, 0.2],
            values=[300.1, 300.3],
            bc_type="fixedValue",
        )


def test_wall_above_cells_raises() -> None:
    # Both cells are below the wall — impossible for a wall-normal layout.
    with pytest.raises(BCContractViolation, match="Non-monotonic wall-normal"):
        extract_wall_gradient(
            wall_coord=0.5,
            wall_value=300.0,
            coords=[0.1, 0.2],
            values=[300.1, 300.3],
            bc_type="fixedValue",
        )


def test_stencil_handles_descending_coord_input() -> None:
    # Caller passes coords in descending order; helper sorts internally.
    grad_asc = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=0.0,
        coords=[0.1, 0.3],
        values=[1.0, 3.0],
        bc_type="fixedValue",
    )
    grad_desc = extract_wall_gradient(
        wall_coord=0.0,
        wall_value=0.0,
        coords=[0.3, 0.1],
        values=[3.0, 1.0],
        bc_type="fixedValue",
    )
    assert grad_asc == pytest.approx(grad_desc, abs=1e-12)
