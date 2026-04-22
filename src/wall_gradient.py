"""Shared 3-point one-sided wall-gradient stencil.

DEC-V61-042: previously, each of the three Nu-emitting cases (DHC, RBC,
impinging_jet) used its own 1-point finite-difference between two
interior cells to approximate d(T)/d(normal) at the wall. That is
1st-order accurate at the midpoint of the two cells — NOT at the wall —
and systematically misreads the gradient by 30-50% for an
exponential-like thermal boundary layer on coarse meshes.

This module provides a single 2nd-order one-sided stencil that uses the
wall value from the BC itself plus the two nearest interior cell-centre
values. The stencil is the standard Fornberg non-uniform-spacing formula.

It also enforces a BC contract: if the wall BC is `fixedGradient`, the
helper returns the BC value directly (the gradient IS the BC — a stencil
over interior cells is a self-consistency mistake, not a measurement).
Any other BC type raises `BCContractViolation` so callers fail closed
rather than silently falling back to a wrong number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple


class BCContractViolation(Exception):
    """Raised when wall-gradient extraction is attempted under inputs
    that cannot yield a physically meaningful wall gradient.

    Examples:
      - `fixedGradient` BC with `bc_gradient` not provided (the BC IS
        the answer; a stencil over interior cells would shadow it).
      - Unknown BC type (callers must either extend the stencil's
        awareness or use a different extractor).
      - Fewer than 2 interior cells supplied.
      - Non-monotonic wall-normal ordering (wall not strictly below
        both interior coords).
    """


@dataclass(frozen=True)
class WallGradientStencil:
    """Non-uniform 3-point one-sided stencil for f'(wall).

    With wall at ``x_w`` and two interior cell-centres at ``x_1 < x_2``,
    spacing ``h_1 = x_1 - x_w`` and ``h_2 = x_2 - x_w``:

        f'(x_w) = -(h_1 + h_2)/(h_1 h_2)   * f(x_w)
                + h_2 / (h_1 (h_2 - h_1))  * f(x_1)
                - h_1 / (h_2 (h_2 - h_1))  * f(x_2)

    The formula is O(h^2) accurate for smooth f and reduces to the
    textbook uniform-spacing stencil (-3,4,-1)/(2h) when h_2 = 2*h_1.

    `bc_type` is advisory — the caller's extractor already knows what
    the wall BC is from the generator. Passing it here lets us fail
    closed if the contract is violated.
    """

    wall_coord: float
    wall_value: float
    coords: Tuple[float, float]  # cell-centre coords, sorted ascending
    values: Tuple[float, float]
    bc_type: Literal["fixedValue", "fixedGradient"]
    bc_gradient: Optional[float] = None

    def compute(self) -> float:
        if self.bc_type == "fixedGradient":
            if self.bc_gradient is None:
                raise BCContractViolation(
                    "fixedGradient BC declared but bc_gradient is None; the BC "
                    "itself is the source of truth for wall gradient — a stencil "
                    "over interior cells would silently shadow it."
                )
            return float(self.bc_gradient)

        if self.bc_type != "fixedValue":
            raise BCContractViolation(
                f"Unsupported wall BC type {self.bc_type!r}; "
                "extend WallGradientStencil or use a different extractor."
            )

        h1 = self.coords[0] - self.wall_coord
        h2 = self.coords[1] - self.wall_coord
        if h1 <= 0.0 or h2 <= h1:
            raise BCContractViolation(
                f"Non-monotonic wall-normal layout: wall_coord={self.wall_coord}, "
                f"coords={self.coords}; required wall < coords[0] < coords[1]."
            )
        c_w = -(h1 + h2) / (h1 * h2)
        c_1 = h2 / (h1 * (h2 - h1))
        c_2 = -h1 / (h2 * (h2 - h1))
        return (
            c_w * self.wall_value
            + c_1 * self.values[0]
            + c_2 * self.values[1]
        )


def extract_wall_gradient(
    wall_coord: float,
    wall_value: float,
    coords: Sequence[float],
    values: Sequence[float],
    *,
    bc_type: Literal["fixedValue", "fixedGradient"],
    bc_gradient: Optional[float] = None,
) -> float:
    """Compute f'(wall) from wall BC + two nearest interior cells.

    Picks the two interior cells nearest to `wall_coord` and applies
    `WallGradientStencil`. Callers pass all interior cells in the
    layer; this function handles selection + ordering.

    Raises `BCContractViolation` when the inputs cannot yield a
    physically meaningful gradient.
    """
    if len(coords) != len(values):
        raise BCContractViolation(
            f"coords/values length mismatch: {len(coords)} vs {len(values)}"
        )
    if len(coords) < 2:
        raise BCContractViolation(
            f"wall-gradient requires ≥2 interior cells, got {len(coords)}"
        )
    paired = sorted(zip(coords, values), key=lambda p: abs(p[0] - wall_coord))
    (c0, v0), (c1, v1) = paired[0], paired[1]
    ordered = sorted(((c0, v0), (c1, v1)), key=lambda p: p[0] - wall_coord)
    stencil = WallGradientStencil(
        wall_coord=wall_coord,
        wall_value=wall_value,
        coords=(ordered[0][0], ordered[1][0]),
        values=(ordered[0][1], ordered[1][1]),
        bc_type=bc_type,
        bc_gradient=bc_gradient,
    )
    return stencil.compute()
