"""DEC-V61-146 (N4.1) · BC contract → 0.orig/{U, p} writer.

Renders OpenFOAM volVectorField (U) and volScalarField (p) dict files
from a :class:`BCContract`. Atomic writes via tempfile + os.replace.

Format matches what bc_setup.py's `_author_dicts` family has been
emitting since V61-097 — same dimensions header, same `boundaryField`
block layout. The behavioral contract: an engineer can `cat 0.orig/U`
after this writer runs and see legible OpenFOAM-10 syntax.

Dimension headers:
  U: [0 1 -1 0 0 0 0]  (m/s)
  p: [0 2 -2 0 0 0 0]  (m²/s² — kinematic-pressure form for
                        incompressible solvers; rho-multiplication
                        is solver-internal)

Internal fields (uniform initial guess):
  U: uniform (0 0 0)
  p: uniform 0
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ui.backend.schemas.bc_contract import (
    BCContract,
    CyclicBC,
    EmptyBC,
    InletOutletBC,
    MassFlowInletBC,
    MovingWallBC,
    NoSlipWallBC,
    PerPatchBC,
    PressureOutletBC,
    SymmetryBC,
    VelocityInletBC,
    VolumetricFlowInletBC,
)


_U_HEADER = (
    "FoamFile { version 2.0; format ascii; class volVectorField; "
    'location "0"; object U; }\n'
    "dimensions      [0 1 -1 0 0 0 0];\n"
    "internalField   uniform (0 0 0);\n"
)
_P_HEADER = (
    "FoamFile { version 2.0; format ascii; class volScalarField; "
    'location "0"; object p; }\n'
    "dimensions      [0 2 -2 0 0 0 0];\n"
    "internalField   uniform 0;\n"
)


class BCWriterError(RuntimeError):
    """Raised when the writer can't render dicts. ``failing_check``
    enumerates the structural problem so the route surfaces a stable
    detail."""

    def __init__(self, message: str, *, failing_check: str) -> None:
        super().__init__(message)
        self.failing_check = failing_check


def render_u_field(contract: BCContract) -> str:
    """Render `0.orig/U` dict text from the contract."""
    lines = [_U_HEADER, "boundaryField", "{"]
    for name, bc in contract.patches.items():
        lines.append(f"    {name}")
        lines.append("    {")
        for sub in _u_block_lines(bc):
            lines.append(f"        {sub}")
        lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_p_field(contract: BCContract) -> str:
    """Render `0.orig/p` dict text from the contract."""
    lines = [_P_HEADER, "boundaryField", "{"]
    for name, bc in contract.patches.items():
        lines.append(f"    {name}")
        lines.append("    {")
        for sub in _p_block_lines(bc):
            lines.append(f"        {sub}")
        lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class MassBalanceCheck:
    """DEC-V61-198 A4 advisory result. Never blocks; surfaces signal."""

    status: Literal["ok", "no_mass_flow", "no_relief_outlet"]
    total_inlet_kg_s: float
    has_relief_outlet: bool
    message: str


def check_mass_balance(contract: BCContract) -> MassBalanceCheck:
    """Pre-flight advisory adapted from APU bay 05_make_dicts.py:317-336.

    Main-repo schema has no mass_flow_outlet variant, so the check
    reduces to: when MassFlowInletBC patches are present, ensure at
    least one PressureOutletBC or InletOutletBC exists to absorb the
    imposed mdot. Advisory only — caller decides whether to surface.
    """
    total_in = sum(
        bc.mass_flow_rate
        for bc in contract.patches.values()
        if isinstance(bc, MassFlowInletBC)
    )
    has_relief = any(
        isinstance(bc, (PressureOutletBC, InletOutletBC))
        for bc in contract.patches.values()
    )
    if total_in == 0.0:
        return MassBalanceCheck(
            "no_mass_flow", 0.0, has_relief,
            "no MassFlowInletBC patches — pressure-driven case?",
        )
    if not has_relief:
        return MassBalanceCheck(
            "no_relief_outlet", total_in, False,
            f"Σmdot={total_in:.4f} kg/s with no PressureOutlet/InletOutlet "
            "— solver will likely diverge",
        )
    return MassBalanceCheck(
        "ok", total_in, True,
        f"Σmdot={total_in:.4f} kg/s + relief outlet present",
    )


def write_bc_dicts(
    case_dir: Path,
    *,
    contract: BCContract,
) -> dict[str, str]:
    """Write `0.orig/U` + `0.orig/p` atomically.

    Raises FileNotFoundError when ``case_dir`` is missing entirely.
    Creates `0.orig/` if it doesn't exist (matches the convention
    bc_setup.py establishes — initial-condition templates live in
    `0.orig/`, the solver runner copies them to `0/` at run time).
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(
            f"case_dir {case_dir!s} does not exist"
        )
    zero_orig = case_dir / "0.orig"
    zero_orig.mkdir(exist_ok=True)
    u_text = render_u_field(contract)
    p_text = render_p_field(contract)
    _atomic_write_text(zero_orig / "U", u_text)
    _atomic_write_text(zero_orig / "p", p_text)
    return {"0.orig/U": u_text, "0.orig/p": p_text}


# ────────── Per-BC-type dispatch ──────────


def _u_block_lines(bc: PerPatchBC) -> list[str]:
    """Return the lines that go inside the `<patch> { ... }` block
    of `0.orig/U` for this BC type. Each line is sub-indented by
    the caller."""
    if isinstance(bc, VelocityInletBC):
        return [
            "type            fixedValue;",
            f"value           uniform {_render_vec(bc.velocity)};",
        ]
    if isinstance(bc, VolumetricFlowInletBC):
        return [
            "type            flowRateInletVelocity;",
            f"volumetricFlowRate {_render_float(bc.volumetric_flow_rate)};",
            "extrapolateProfile yes;",
            "value           uniform (0 0 0);",
        ]
    if isinstance(bc, MassFlowInletBC):
        return [
            "type            flowRateInletVelocity;",
            f"massFlowRate    {_render_float(bc.mass_flow_rate)};",
            "rho             rho;",
            "extrapolateProfile yes;",
            "value           uniform (0 0 0);",
        ]
    if isinstance(bc, PressureOutletBC):
        return ["type            zeroGradient;"]
    if isinstance(bc, InletOutletBC):
        return [
            "type            pressureInletOutletVelocity;",
            "value           uniform (0 0 0);",
        ]
    if isinstance(bc, NoSlipWallBC):
        return [
            "type            fixedValue;",
            "value           uniform (0 0 0);",
        ]
    if isinstance(bc, MovingWallBC):
        return [
            "type            fixedValue;",
            f"value           uniform {_render_vec(bc.velocity)};",
        ]
    if isinstance(bc, SymmetryBC):
        return ["type            symmetry;"]
    if isinstance(bc, CyclicBC):
        return ["type            cyclic;"]
    if isinstance(bc, EmptyBC):
        return ["type            empty;"]
    raise BCWriterError(
        f"unknown BC type {type(bc).__name__!r} for U field",
        failing_check="bc_type_unknown",
    )


def _p_block_lines(bc: PerPatchBC) -> list[str]:
    if isinstance(
        bc,
        (
            VelocityInletBC,
            VolumetricFlowInletBC,
            MassFlowInletBC,
            NoSlipWallBC,
            MovingWallBC,
        ),
    ):
        return ["type            zeroGradient;"]
    if isinstance(bc, PressureOutletBC):
        return [
            "type            fixedValue;",
            f"value           uniform {_render_float(bc.gauge_pressure)};",
        ]
    if isinstance(bc, InletOutletBC):
        return [
            "type            fixedValue;",
            f"value           uniform {_render_float(bc.gauge_pressure)};",
        ]
    if isinstance(bc, SymmetryBC):
        return ["type            symmetry;"]
    if isinstance(bc, CyclicBC):
        return ["type            cyclic;"]
    if isinstance(bc, EmptyBC):
        return ["type            empty;"]
    raise BCWriterError(
        f"unknown BC type {type(bc).__name__!r} for p field",
        failing_check="bc_type_unknown",
    )


# ────────── Helpers ──────────


def _atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _render_vec(vec: tuple[float, float, float]) -> str:
    return f"({_render_float(vec[0])} {_render_float(vec[1])} {_render_float(vec[2])})"


def _render_float(value: float) -> str:
    """Same readable-form picker as physics writer — fixed-point in
    the [1e-4, 1e6) range, scientific otherwise."""
    abs_v = abs(value)
    if abs_v == 0.0:
        return "0"
    if 1e-4 <= abs_v < 1e6:
        s = f"{value:.6f}".rstrip("0").rstrip(".")
        return s if "." in s or "e" in s else f"{s}.0"
    return f"{value:.6e}"
