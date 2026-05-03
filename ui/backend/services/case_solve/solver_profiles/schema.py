"""DEC-V61-112 Phase 1 · Solver-profile schema dataclasses.

A profile is the typed equivalent of an OpenFOAM solver-dict
template (controlDict + fvSchemes + fvSolution). Instead of
inlining template strings in ``bc_setup_from_stl_patches`` /
``bc_setup``, BC-setup call sites load a profile and render its
dicts. The schema is intentionally explicit — every OpenFOAM dict
field is a typed dataclass attribute; there is NO raw-string
passthrough. This eliminates the copy-paste-edit pattern that bit
V61-107.5 R14/R15 (forgot ``divDevReff`` in fvSchemes) and V61-111
R1 (mismatched PIMPLE/SIMPLE blocks).

The schema is render-only — profiles produce OpenFOAM dict text;
they do NOT parse existing dicts. Override semantics (V61-102
raw-dict editor) operate on the rendered output, not the profile.

Phase 1 includes only the fields used by simpleFoam (steady-state)
and pimpleFoam (transient) — this covers the V61-111 simpleFoam
extraction + Phase 2 pimpleFoam follow-up. icoFoam-only fields
(LDC ``setup_ldc_bc``) wait for Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# OpenFOAM dict syntax helpers. Profiles emit content that the
# BC-setup atomic-commit pipeline writes verbatim (with the FoamFile
# header prepended at write time, same as the inline templates).


def _render_dict_block(name: str, entries: dict[str, str]) -> str:
    """Render an OpenFOAM dict block: ``name { key value; ... }``."""
    body = " ".join(f"{k} {v};" for k, v in entries.items())
    return f"{name} {{ {body} }}"


@dataclass(frozen=True, slots=True)
class ControlDictBlock:
    """``system/controlDict`` template fields.

    DEC-V61-112: end_time and delta_t are caller-overridable at
    render time (per-case parameter); all other fields are
    profile-pinned. Engineers customize pinned fields via the
    V61-102 raw-dict editor, NOT by mutating the profile.

    For simpleFoam (steady-state SIMPLE), end_time is interpreted as
    iteration count; ``adjust_time_step`` / ``max_co`` / ``max_delta_t``
    are None (omitted from the rendered controlDict — no physical
    time coordinate). For pimpleFoam (transient PIMPLE) they are
    populated.
    """

    application: str
    start_from: str = "startTime"
    start_time: float = 0.0
    stop_at: str = "endTime"
    end_time_default: float = 200.0
    delta_t_default: float = 1.0
    write_control: str = "timeStep"
    write_interval: float = 50.0
    purge_write: int = 0
    write_format: str = "ascii"
    write_precision: int = 6
    write_compression: str = "off"
    time_format: str = "general"
    time_precision: int = 6
    run_time_modifiable: bool = True
    # Transient-only knobs. ``None`` means "omit from rendered
    # controlDict" (the simpleFoam case).
    adjust_time_step: bool | None = None
    max_co: float | None = None
    max_delta_t_follows_delta_t: bool = False  # pimpleFoam: maxDeltaT = caller delta_t
    # simpleFoam-only: floor on end_time when caller passes a small
    # value (smoke runners default to seconds-shaped values, which
    # would under-budget steady-state iteration count).
    iteration_floor: int | None = None

    def render(
        self,
        *,
        end_time: float | None = None,
        delta_t: float | None = None,
    ) -> str:
        """Return the controlDict body (FoamFile header is prepended
        by the BC-setup writer; the schema renders the post-header
        content only). Caller may override end_time / delta_t per
        case; all other fields are profile-pinned.
        """
        et = end_time if end_time is not None else self.end_time_default
        dt = delta_t if delta_t is not None else self.delta_t_default
        # simpleFoam iteration-count floor (V61-111 R0 + V61-112 P1).
        if self.iteration_floor is not None:
            et = max(int(et), self.iteration_floor)

        lines: list[str] = [
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object controlDict; }',
            f"application {self.application};",
            f"startFrom {self.start_from};",
            f"startTime {_format_number(self.start_time)};",
            f"stopAt {self.stop_at};",
            f"endTime {_format_endtime(et, self.iteration_floor is not None)};",
            f"deltaT {_format_number(dt)};",
            f"writeControl {self.write_control};",
            f"writeInterval {_format_number(self.write_interval)};",
            f"purgeWrite {self.purge_write};",
            f"writeFormat {self.write_format};",
            f"writePrecision {self.write_precision};",
            f"writeCompression {self.write_compression};",
            f"timeFormat {self.time_format};",
            f"timePrecision {self.time_precision};",
            f"runTimeModifiable {str(self.run_time_modifiable).lower()};",
        ]
        if self.adjust_time_step is not None:
            lines.append(
                f"adjustTimeStep {'yes' if self.adjust_time_step else 'no'};"
            )
        if self.max_co is not None:
            lines.append(f"maxCo {_format_number(self.max_co)};")
        if self.max_delta_t_follows_delta_t:
            lines.append(f"maxDeltaT {_format_number(dt)};")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, slots=True)
class FvSchemesBlock:
    """``system/fvSchemes`` template fields.

    DEC-V61-112: each scheme family is a dict of ``{key: value}``
    pairs that render to the OpenFOAM `family { key value; ... }`
    syntax. ``default`` is the most common key; non-default keys
    cover the explicit term schemes (``div(phi,U)`` vs the default,
    ``grad(U)`` cellLimited variants etc.).
    """

    ddt_schemes: dict[str, str] = field(default_factory=lambda: {"default": "Euler"})
    grad_schemes: dict[str, str] = field(
        default_factory=lambda: {"default": "Gauss linear"}
    )
    div_schemes: dict[str, str] = field(
        default_factory=lambda: {"default": "none"}
    )
    laplacian_schemes: dict[str, str] = field(
        default_factory=lambda: {"default": "Gauss linear corrected"}
    )
    interpolation_schemes: dict[str, str] = field(
        default_factory=lambda: {"default": "linear"}
    )
    sn_grad_schemes: dict[str, str] = field(
        default_factory=lambda: {"default": "corrected"}
    )

    def render(self) -> str:
        return (
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSchemes; }\n'
            + _render_dict_block("ddtSchemes ", self.ddt_schemes) + "\n"
            + _render_dict_block("gradSchemes", self.grad_schemes) + "\n"
            + _render_dict_block("divSchemes ", self.div_schemes) + "\n"
            + _render_dict_block("laplacianSchemes", self.laplacian_schemes) + "\n"
            + _render_dict_block("interpolationSchemes", self.interpolation_schemes) + "\n"
            + _render_dict_block("snGradSchemes", self.sn_grad_schemes) + "\n"
        )


@dataclass(frozen=True, slots=True)
class FvSolutionBlock:
    """``system/fvSolution`` template fields.

    DEC-V61-112: split into 3 layers — ``solvers`` (linear-solver
    choices per field), ``control_block`` (PIMPLE / SIMPLE / PISO
    block), ``relaxation_factors`` (steady-state SIMPLE relaxation
    only).

    ``control_block.name`` selects which control-block flavor
    renders. PIMPLE and SIMPLE have different sub-fields
    (residualControl is SIMPLE-only; nOuterCorrectors is
    PIMPLE-only); the schema captures BOTH and renders only the
    fields appropriate to ``control_block.name``.
    """

    # Linear-solver dict per field (p, U, pFinal, UFinal, etc.).
    # Each entry: {field_name: "PCG; preconditioner DIC; tolerance ..."}
    solvers: dict[str, str] = field(default_factory=dict)
    # control_block: name + nested-dict of fields. The nested dict
    # is rendered as `name { key value; ... }` with multi-line
    # support (residualControl is itself a sub-dict).
    control_block_name: str = "PIMPLE"
    control_block_fields: dict[str, object] = field(default_factory=dict)
    # SIMPLE-only relaxationFactors (None = omit).
    relaxation_factors_fields: dict[str, float] | None = None
    relaxation_factors_equations: dict[str, float] | None = None

    def render(self) -> str:
        lines: list[str] = [
            'FoamFile { version 2.0; format ascii; class dictionary; '
            'location "system"; object fvSolution; }',
            "solvers",
            "{",
        ]
        for field_name, body in self.solvers.items():
            lines.append(f"    {field_name}  {{ {body} }}")
        lines.append("}")

        # Control block (PIMPLE / SIMPLE / PISO).
        lines.append(self.control_block_name)
        lines.append("{")
        for k, v in self.control_block_fields.items():
            if isinstance(v, dict):
                # Nested dict (e.g. residualControl). Sub-values may
                # be int/float (rendered via _format_number) or str
                # (rendered verbatim — preserves V61-111's literal
                # scientific notation like "1e-3" that `:g` would
                # render as "0.001").
                lines.append(f"    {k}")
                lines.append("    {")
                for sk, sv in v.items():
                    sv_str = (
                        _format_number(sv)
                        if isinstance(sv, (int, float))
                        else str(sv)
                    )
                    lines.append(f"        {sk}   {sv_str};")
                lines.append("    }")
            else:
                lines.append(
                    f"    {k} "
                    f"{_format_number(v) if isinstance(v, (int, float)) else v};"
                )
        lines.append("}")

        # relaxationFactors (SIMPLE only — None = omit).
        if (
            self.relaxation_factors_fields is not None
            or self.relaxation_factors_equations is not None
        ):
            lines.append("relaxationFactors")
            lines.append("{")
            if self.relaxation_factors_fields is not None:
                lines.append("    fields")
                lines.append("    {")
                for k, v in self.relaxation_factors_fields.items():
                    lines.append(f"        {k}   {_format_number(v)};")
                lines.append("    }")
            if self.relaxation_factors_equations is not None:
                lines.append("    equations")
                lines.append("    {")
                for k, v in self.relaxation_factors_equations.items():
                    lines.append(f"        {k}   {_format_number(v)};")
                lines.append("    }")
            lines.append("}")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, slots=True)
class SolverProfile:
    """Top-level solver-profile schema. Carries the 3 dict templates
    plus solver metadata (name, family).
    """

    name: str
    family: Literal["steady", "transient"]
    control_dict: ControlDictBlock
    fv_schemes: FvSchemesBlock
    fv_solution: FvSolutionBlock

    def render_control_dict(
        self,
        *,
        end_time: float | None = None,
        delta_t: float | None = None,
    ) -> str:
        return self.control_dict.render(end_time=end_time, delta_t=delta_t)

    def render_fv_schemes(self) -> str:
        return self.fv_schemes.render()

    def render_fv_solution(self) -> str:
        return self.fv_solution.render()


def _format_number(value: float | int) -> str:
    """Format a numeric value for OpenFOAM dict syntax. Integers
    render without trailing ``.0``; floats render with up to 6
    significant digits, no scientific notation for typical
    relaxation/tolerance values, scientific for very small numbers
    (1e-06 etc.).
    """
    if isinstance(value, bool):
        # Should not reach here in numeric paths; defensive.
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    # Float. Match the V61-111 inline rendering convention:
    # - integer-valued floats render as "1" (deltaT 1) not "1.0"
    # - small numbers render as scientific: 1e-06 not 0.000001
    # - mid-range render as decimal: 0.5 not 5e-01
    if value == int(value):
        return str(int(value))
    if 0 < abs(value) < 1e-3 or abs(value) >= 1e6:
        return f"{value:g}"
    # Trim trailing zeros for compactness (0.05 not 0.050000).
    s = f"{value:.6g}"
    return s


def _format_endtime(value: float, is_iteration_count: bool) -> str:
    """For simpleFoam (iteration-count semantics), endTime renders as
    a plain integer. For transient solvers (seconds), use the
    standard numeric format.
    """
    if is_iteration_count:
        return str(int(value))
    return _format_number(value)
