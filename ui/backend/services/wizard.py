"""Onboarding-wizard service · Stage 8a.

Three hand-written starter templates + a YAML renderer that turns
(template_id, params) into a self-contained case YAML, then writes it
to the existing user_drafts store.

The templates are intentionally minimal: no gold_standard block (the
user is creating a NEW case — they don't have benchmark data yet),
realistic OpenFOAM solver/turbulence_model assignments so the YAML
would actually be runnable when Stage 8b wires the real solver, and
a small param schema so the form fields stay glanceable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import yaml

from ui.backend.schemas.wizard import (
    DraftCreateResponse,
    TemplateParam,
    TemplateSummary,
)
from ui.backend.services.case_drafts import lint_case_yaml, put_case_yaml


@dataclass(slots=True)
class _Template:
    summary: TemplateSummary
    render_fn: Callable[[str, str, dict[str, float]], dict]


def _square_cavity_render(
    case_id: str, name_display: str, params: dict[str, float]
) -> dict:
    Re = params.get("Re", 100.0)
    U_lid = params.get("lid_velocity", 1.0)
    return {
        "id": case_id,
        "name": name_display,
        "reference": "Patterned on Ghia 1982 lid-driven cavity",
        "flow_type": "INTERNAL",
        "geometry_type": "SIMPLE_GRID",
        "compressibility": "INCOMPRESSIBLE",
        "steady_state": "STEADY",
        "solver": "icoFoam" if Re <= 1000 else "simpleFoam",
        "turbulence_model": "laminar" if Re <= 1000 else "kEpsilon",
        "parameters": {"Re": Re},
        "boundary_conditions": {
            "top_wall_u": U_lid,
            "other_walls_u": 0.0,
        },
    }


def _backward_step_render(
    case_id: str, name_display: str, params: dict[str, float]
) -> dict:
    Re = params.get("Re", 800.0)
    U_inlet = params.get("inlet_velocity", 1.0)
    expansion = params.get("expansion_ratio", 2.0)
    return {
        "id": case_id,
        "name": name_display,
        "reference": "Patterned on Armaly 1983 backward-facing step",
        "flow_type": "INTERNAL",
        "geometry_type": "SIMPLE_GRID",
        "compressibility": "INCOMPRESSIBLE",
        "steady_state": "STEADY",
        "solver": "simpleFoam",
        "turbulence_model": "laminar" if Re <= 1000 else "kOmegaSST",
        "parameters": {"Re": Re, "expansion_ratio": expansion},
        "boundary_conditions": {
            "inlet_u": U_inlet,
            "outlet_p": 0.0,
            "walls_u": 0.0,
        },
    }


def _pipe_flow_render(
    case_id: str, name_display: str, params: dict[str, float]
) -> dict:
    Re = params.get("Re", 200.0)
    U_inlet = params.get("inlet_velocity", 0.1)
    L = params.get("length", 1.0)
    D = params.get("diameter", 0.05)
    return {
        "id": case_id,
        "name": name_display,
        "reference": "Hagen-Poiseuille laminar pipe flow (analytical reference)",
        "flow_type": "INTERNAL",
        "geometry_type": "AXISYMMETRIC",
        "compressibility": "INCOMPRESSIBLE",
        "steady_state": "STEADY",
        "solver": "simpleFoam",
        "turbulence_model": "laminar" if Re <= 2300 else "kOmegaSST",
        "parameters": {
            "Re": Re,
            "length": L,
            "diameter": D,
        },
        "boundary_conditions": {
            "inlet_u": U_inlet,
            "outlet_p": 0.0,
            "wall_u": 0.0,
        },
    }


_TEMPLATES: dict[str, _Template] = {
    "square_cavity": _Template(
        summary=TemplateSummary(
            template_id="square_cavity",
            name_zh="方腔顶盖驱动",
            name_en="Square lid-driven cavity",
            description_zh="经典 Ghia 1982 基准 — 一个单位正方形腔，顶盖匀速驱动流体，其余三面无滑移。Re ≤ 1000 走层流，更高 Re 自动切换到 kEpsilon。",
            geometry_type="SIMPLE_GRID",
            flow_type="INTERNAL",
            solver="icoFoam",
            canonical_ref="Ghia, Ghia & Shin 1982 (J. Comput. Phys. 47:387)",
            params=[
                TemplateParam(
                    key="Re",
                    label_zh="雷诺数",
                    label_en="Reynolds number",
                    type="float",
                    default=100.0,
                    min=10.0,
                    max=10000.0,
                    unit="dimensionless",
                    help_zh="Re=ρUL/μ。100 对应原始 Ghia 案例；>1000 自动切换到湍流求解器。",
                ),
                TemplateParam(
                    key="lid_velocity",
                    label_zh="顶盖速度",
                    label_en="Lid velocity",
                    type="float",
                    default=1.0,
                    min=0.01,
                    max=10.0,
                    unit="m/s",
                ),
            ],
        ),
        render_fn=_square_cavity_render,
    ),
    "backward_facing_step": _Template(
        summary=TemplateSummary(
            template_id="backward_facing_step",
            name_zh="后台阶突扩",
            name_en="Backward-facing step",
            description_zh="经典 Armaly 1983 几何 — 入口沟道在某处突然扩张为台阶下游通道，再附长度是关键观测量。Re ≤ 1000 层流，更高 Re 走 k-ω SST。",
            geometry_type="SIMPLE_GRID",
            flow_type="INTERNAL",
            solver="simpleFoam",
            canonical_ref="Armaly, Durst, Pereira & Schönung 1983",
            params=[
                TemplateParam(
                    key="Re",
                    label_zh="雷诺数",
                    label_en="Reynolds number",
                    type="float",
                    default=800.0,
                    min=100.0,
                    max=20000.0,
                    unit="dimensionless",
                ),
                TemplateParam(
                    key="inlet_velocity",
                    label_zh="入口速度",
                    label_en="Inlet velocity",
                    type="float",
                    default=1.0,
                    min=0.01,
                    max=10.0,
                    unit="m/s",
                ),
                TemplateParam(
                    key="expansion_ratio",
                    label_zh="扩张比",
                    label_en="Expansion ratio",
                    type="float",
                    default=2.0,
                    min=1.5,
                    max=5.0,
                    unit="dimensionless",
                    help_zh="下游高度 / 入口高度。Armaly 原始论文为 1.94。",
                ),
            ],
        ),
        render_fn=_backward_step_render,
    ),
    "pipe_flow": _Template(
        summary=TemplateSummary(
            template_id="pipe_flow",
            name_zh="层流圆管",
            name_en="Laminar pipe flow",
            description_zh="Hagen-Poiseuille 层流圆管 — 完全发展段的速度分布有解析解（抛物线型），可作为新手验证管道求解器收敛性的入门案例。",
            geometry_type="AXISYMMETRIC",
            flow_type="INTERNAL",
            solver="simpleFoam",
            canonical_ref="Hagen-Poiseuille 解析解",
            params=[
                TemplateParam(
                    key="Re",
                    label_zh="雷诺数",
                    label_en="Reynolds number",
                    type="float",
                    default=200.0,
                    min=10.0,
                    max=10000.0,
                    unit="dimensionless",
                    help_zh="Re ≤ 2300 走层流；以上自动切到 k-ω SST。",
                ),
                TemplateParam(
                    key="inlet_velocity",
                    label_zh="入口平均速度",
                    label_en="Inlet mean velocity",
                    type="float",
                    default=0.1,
                    min=0.001,
                    max=10.0,
                    unit="m/s",
                ),
                TemplateParam(
                    key="length",
                    label_zh="管长",
                    label_en="Pipe length",
                    type="float",
                    default=1.0,
                    min=0.1,
                    max=10.0,
                    unit="m",
                ),
                TemplateParam(
                    key="diameter",
                    label_zh="管径",
                    label_en="Pipe diameter",
                    type="float",
                    default=0.05,
                    min=0.001,
                    max=1.0,
                    unit="m",
                ),
            ],
        ),
        render_fn=_pipe_flow_render,
    ),
}


def list_templates() -> list[TemplateSummary]:
    return [t.summary for t in _TEMPLATES.values()]


def render_yaml(
    template_id: str, case_id: str, name_display: str | None, params: dict[str, float]
) -> str:
    template = _TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"unknown template_id: {template_id!r}")
    display = name_display or f"{template.summary.name_zh} · {case_id}"
    body = template.render_fn(case_id, display, params or {})
    return yaml.safe_dump(body, sort_keys=False, allow_unicode=True)


def create_draft(
    template_id: str,
    case_id: str,
    name_display: str | None,
    params: dict[str, float],
) -> DraftCreateResponse:
    """Render YAML from template + write to user_drafts via existing
    case_drafts.put_case_yaml. Returns the lint result so the wizard
    UI can surface warnings (missing fields are warnings, not errors —
    the user has not yet authored a gold_standard block, expected)."""
    yaml_text = render_yaml(template_id, case_id, name_display, params)
    # Pre-lint so we can surface the result on creation (put_case_yaml
    # also lints internally and short-circuits on parse-fail; here we
    # want both fields whether the parse succeeds or not).
    lint = lint_case_yaml(yaml_text)
    draft_path, _ = put_case_yaml(case_id, yaml_text)
    return DraftCreateResponse(
        case_id=case_id,
        draft_path=draft_path or "",
        yaml_text=yaml_text,
        lint_ok=lint.ok,
        lint_errors=lint.errors,
        lint_warnings=lint.warnings,
    )
