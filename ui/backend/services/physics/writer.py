"""DEC-V61-142 (N3.3) · physics dict writer.

Translates :class:`MaterialContract` → ``constant/physicalProperties``
and :class:`RegimeContract` → ``constant/momentumTransport`` (or
successor `turbulenceProperties`).

Matches the byte-format of the existing hand-crafted writers in
``services/case_solve/bc_setup.py`` (Newtonian + nu in OpenFOAM SI
dimensions). Engineer-typed `kind=custom` contracts and
preset-shorthand `kind=preset` contracts produce byte-identical
output when their `fluid`/`thermal` numbers match — the discriminator
is audit-only metadata.

Atomic write via tempfile + rename so concurrent reads (engineer's
editor, AI advisor's GET, or the route's read-back GET) never observe
partial dict files.

V130 Principle B / V132 contract: this writer IS a mutator. It
appears in KNOWN_MUTATION_FUNCTIONS so AI dispatch paths cannot call
it. The route layer (route_physics.py) calls it from the user-driven
POST handler only.

LES-stub regime emits a TODO comment in the dict (charter §"LES-stub
forward-compat placeholder"); the case is still loadable but the
engineer must edit the dict by hand for an actual LES sub-grid model.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ui.backend.schemas.material_contract import MaterialContract
from ui.backend.schemas.regime_contract import RegimeContract


_PHYS_HEADER = (
    "FoamFile { version 2.0; format ascii; class dictionary; "
    'location "constant"; object physicalProperties; }\n'
)
_MOMENTUM_HEADER = (
    "FoamFile { version 2.0; format ascii; class dictionary; "
    'location "constant"; object momentumTransport; }\n'
)


def render_physical_properties(material: MaterialContract) -> str:
    """Render OpenFOAM ``constant/physicalProperties`` text from the
    contract.

    Format matches what bc_setup.py has been writing since V61-097.
    Density is emitted only when thermal block present (the legacy
    incompressible path didn't write density; downstream solvers
    derive ρ from `nu` + reference cases). When thermal is set, the
    case is presumed buoyant / energy-equation, and density is
    written explicitly.
    """
    lines = [_PHYS_HEADER, "transportModel  Newtonian;"]
    nu = material.fluid.kinematic_viscosity
    lines.append(f"nu              [0 2 -1 0 0 0 0] {_render_float(nu)};")
    if material.thermal is not None:
        # Thermal block: emit ρ + cp + k explicitly. Solver dict
        # editors (N4.2) will consume these.
        rho = material.fluid.density
        lines.append(
            f"rho             [1 -3 0 0 0 0 0] {_render_float(rho)};"
        )
        lines.append(
            f"Cp              [0 2 -2 -1 0 0 0] "
            f"{_render_float(material.thermal.specific_heat)};"
        )
        lines.append(
            f"kappa           [1 1 -3 -1 0 0 0] "
            f"{_render_float(material.thermal.thermal_conductivity)};"
        )
        if material.fluid.prandtl is not None:
            lines.append(
                f"Pr              [0 0 0 0 0 0 0] "
                f"{_render_float(material.fluid.prandtl)};"
            )
    return "\n".join(lines) + "\n"


def render_momentum_transport(regime: RegimeContract) -> str:
    """Render OpenFOAM ``constant/momentumTransport`` text from the
    contract.

    Maps RegimeKind literal → simulationType + RAS/LES sub-block:
      * laminar          → simulationType laminar;
      * RANS-RAS         → simulationType RAS; RAS { RASModel kEpsilon; ... }
      * RANS-kOmegaSST   → simulationType RAS; RAS { RASModel kOmegaSST; ... }
      * LES-stub         → simulationType laminar; with TODO comment
                           directing engineer to edit by hand for LES
    """
    lines = [_MOMENTUM_HEADER]
    if regime.regime == "laminar":
        lines.append("simulationType laminar;")
    elif regime.regime == "RANS-RAS":
        lines.append("simulationType RAS;")
        lines.append("RAS")
        lines.append("{")
        lines.append("    RASModel        kEpsilon;")
        lines.append("    turbulence      on;")
        lines.append("    printCoeffs     on;")
        lines.append("}")
    elif regime.regime == "RANS-kOmegaSST":
        lines.append("simulationType RAS;")
        lines.append("RAS")
        lines.append("{")
        lines.append("    RASModel        kOmegaSST;")
        lines.append("    turbulence      on;")
        lines.append("    printCoeffs     on;")
        lines.append("}")
    elif regime.regime == "LES-stub":
        # Forward-compat placeholder — N3.3 emits a laminar dict with
        # a TODO. Engineer hand-edits to add LES { LESModel ... } block.
        lines.append("// TODO(N3-extend): LES sub-grid model selection deferred.")
        lines.append("//   Replace this block with `simulationType LES;` + LES{...}")
        lines.append("//   when M3-extend lands sub-grid model picking.")
        lines.append("simulationType laminar;")
    else:
        # Defensive: schema literal matches one of the above; this
        # branch only fires if RegimeKind grew without the writer
        # being updated.
        raise ValueError(f"unknown regime literal: {regime.regime!r}")
    return "\n".join(lines) + "\n"


def write_physics_dicts(
    case_dir: Path,
    *,
    material: MaterialContract,
    regime: RegimeContract,
) -> dict[str, str]:
    """Write `constant/physicalProperties` + `constant/momentumTransport`.

    Returns a dict ``{rel_path: dict_text}`` of what was written —
    useful for the route layer's response body so the engineer can
    confirm the dict text without re-reading from disk.

    Atomic writes via tempfile + rename; concurrent readers either see
    the prior dict in full or the new dict in full, never a partial
    file.

    Raises FileNotFoundError when ``case_dir/constant/`` doesn't
    exist (the case wasn't scaffolded yet — engineer must complete
    Step 1 import first).
    """
    constant_dir = case_dir / "constant"
    if not constant_dir.is_dir():
        raise FileNotFoundError(
            f"constant/ directory missing for case at {case_dir!s}; "
            "the case has not been scaffolded yet"
        )
    phys_text = render_physical_properties(material)
    momentum_text = render_momentum_transport(regime)
    _atomic_write_text(constant_dir / "physicalProperties", phys_text)
    _atomic_write_text(constant_dir / "momentumTransport", momentum_text)
    return {
        "constant/physicalProperties": phys_text,
        "constant/momentumTransport": momentum_text,
    }


def _atomic_write_text(target: Path, text: str) -> None:
    """Write `text` to `target` atomically. tmp file in the same
    directory + os.rename ensures a concurrent reader sees either the
    prior file or the new file in full."""
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
        # Best-effort cleanup; raise the original.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _render_float(value: float) -> str:
    """Render a float for OpenFOAM dict syntax. Use fixed-point for
    values in the readable [1e-4, 1e6) range; scientific otherwise.

    Matches the existing bc_setup.py byte format conventions where
    ν=1e-5 / 2e-4 are emitted as fixed-point; very small or very
    large values switch to scientific.
    """
    abs_v = abs(value)
    if 1e-4 <= abs_v < 1e6:
        # Strip trailing zeros after decimal but keep at least one digit.
        s = f"{value:.6f}".rstrip("0").rstrip(".")
        return s if "." in s or "e" in s else f"{s}.0"
    return f"{value:.6e}"
