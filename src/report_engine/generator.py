"""Deterministic Markdown report generation using Jinja2."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .data_collector import REPORTS_ROOT, REPO_ROOT, ReportDataCollector
from .schemas import RenderResult, ReportContext

TEMPLATES_ROOT = REPO_ROOT / "templates"
MAIN_TEMPLATE = "case_report.md.j2"
SUPPORTED_CASE_IDS = {
    "lid_driven_cavity_benchmark",
    "backward_facing_step_steady",
    "cylinder_crossflow",
    "turbulent_flat_plate",
    "duct_flow",  # Q-2 Path A (DEC-V61-011) rename of fully_developed_turbulent_pipe_flow
    "rayleigh_benard_convection",
    "differential_heated_cavity",
    "naca0012_airfoil",
    "axisymmetric_impinging_jet",
    "fully_developed_plane_channel_flow",
}


class ReportGenerator:
    """Render case completion reports from collected structured inputs."""

    def __init__(
        self,
        collector: Optional[ReportDataCollector] = None,
        templates_root: Path = TEMPLATES_ROOT,
    ) -> None:
        self._collector = collector or ReportDataCollector()
        self._templates_root = templates_root
        self._env = Environment(
            loader=FileSystemLoader(str(templates_root)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False,
        )

    def render(self, case_id: str) -> RenderResult:
        if case_id not in SUPPORTED_CASE_IDS:
            return RenderResult(
                case_id=case_id,
                markdown="",
                section_count=0,
                status="noop",
                reason=(
                    "out_of_scope: report generation is frozen to "
                    "Phase 7 coverage anchors during Phase 8b-1"
                ),
                warnings=["out_of_scope"],
            )
        context = self._collector.collect(case_id)
        template = self._env.get_template(MAIN_TEMPLATE)
        markdown = template.render(**self._build_template_context(context)).strip() + "\n"
        section_count = markdown.count("\n## ")
        if markdown.startswith("## "):
            section_count += 1
        return RenderResult(
            case_id=case_id,
            markdown=markdown,
            section_count=section_count,
            warnings=self._warnings(context),
        )

    def generate(self, case_id: str, output_path: Optional[Path] = None) -> RenderResult:
        result = self.render(case_id)
        if result.status == "noop":
            return result
        output = output_path or REPORTS_ROOT / case_id / "report.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.markdown, encoding="utf-8")
        result.output_path = str(output)
        return result

    def generate_many(self, case_ids: Iterable[str]) -> List[RenderResult]:
        return [self.generate(case_id) for case_id in case_ids]

    @staticmethod
    def _build_template_context(context: ReportContext) -> dict:
        verify = context.auto_verify_report
        comparison = verify["gold_standard_comparison"]
        observables = comparison.get("observables", [])
        # DEC-V61-057 Codex round-4 F2-LOW: match_rate must exclude
        # PROVISIONAL_ADVISORY observables so the markdown report agrees
        # with the comparator's overall verdict (Stage C: advisory checks
        # don't degrade the pass-fraction). Backward compat: legacy
        # ObservableCheck.to_dict() omitting gate_status defaults to
        # HARD_GATED, so match_rate semantics are unchanged for cases
        # that haven't migrated to schema_v2.
        hard_observables = [
            o for o in observables
            if o.get("gate_status", "HARD_GATED") != "PROVISIONAL_ADVISORY"
        ]
        pass_count = sum(1 for observable in hard_observables if observable.get("within_tolerance"))
        total_count = len(hard_observables)
        match_rate = (pass_count / total_count) if total_count else 0.0
        return {
            "case_id": context.case_id,
            "case_meta": context.case_meta,
            "gold_standard": context.gold_standard,
            "auto_verify_report": verify,
            "attribution_report": context.attribution_report,
            "correction_spec": context.correction_spec,
            "project_progress": context.project_progress,
            "match_rate": match_rate,
            "deviation_direction": _deviation_direction,
            "format_value": _format_value,
        }

    @staticmethod
    def _warnings(context: ReportContext) -> List[str]:
        warnings = []
        if context.case_meta.get("meta_source") == "[DATA MISSING]":
            warnings.append("case_meta_missing")
        if context.attribution_report is None and context.auto_verify_report.get("verdict") == "FAIL":
            warnings.append("attribution_missing")
        if context.correction_spec is None and context.auto_verify_report.get("correction_spec_needed"):
            warnings.append("correction_spec_missing")
        return warnings


def _deviation_direction(ref_value, sim_value) -> str:  # noqa: ANN001
    try:
        delta = float(sim_value) - float(ref_value)
    except Exception:
        return "N/A"
    if delta > 0:
        return "Over"
    if delta < 0:
        return "Under"
    return "Match"


def _format_value(value):  # noqa: ANN001
    if isinstance(value, float):
        return f"{value:.6g}"
    return value
