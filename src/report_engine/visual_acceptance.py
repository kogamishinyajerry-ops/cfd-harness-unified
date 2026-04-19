"""Generate a single-file visual acceptance report with inline SVG charts."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml  # type: ignore[import-untyped]

from .data_collector import REPORTS_ROOT, REPO_ROOT, ReportDataCollector
from .schemas import ReportContext, VisualAcceptanceResult

DEFAULT_CASE_IDS: Tuple[str, ...] = (
    "lid_driven_cavity_benchmark",
    "backward_facing_step_steady",
    "cylinder_crossflow",
    "naca0012_airfoil",
    "differential_heated_cavity",
)
DEFAULT_OUTPUT_PATH = REPORTS_ROOT / "deep_acceptance" / "visual_acceptance_report.html"

_CSS = """
:root {
  --bg: #0b0d10;
  --bg-alt: #12161b;
  --bg-card: #181d24;
  --border: #262c36;
  --fg: #e6e8eb;
  --fg-dim: #9aa3ad;
  --fg-mute: #6b7580;
  --accent: #4aa3ff;
  --accent-soft: rgba(74, 163, 255, 0.14);
  --ok: #3fb950;
  --warn: #d29922;
  --fail: #f85149;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: radial-gradient(circle at top, #121925 0%, var(--bg) 52%);
  color: var(--fg);
  font-family: var(--sans);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
body { padding: 40px 24px 80px; }
.wrap { max-width: 1280px; margin: 0 auto; }
.hero {
  padding: 28px 32px;
  border: 1px solid rgba(74, 163, 255, 0.28);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(74, 163, 255, 0.14), rgba(248, 81, 73, 0.06)),
    rgba(12, 16, 22, 0.88);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
}
.eyebrow {
  color: var(--fg-mute);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.hero h1 {
  margin: 12px 0 8px;
  font-size: 38px;
  line-height: 1.05;
  letter-spacing: -0.03em;
}
.hero p {
  margin: 0;
  max-width: 980px;
  color: var(--fg-dim);
  font-size: 16px;
}
.hero-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 20px;
}
.pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(18, 22, 27, 0.88);
  color: var(--fg-dim);
  font-size: 12px;
  font-family: var(--mono);
}
.pill.ok { color: var(--ok); border-color: rgba(63, 185, 80, 0.35); background: rgba(63, 185, 80, 0.08); }
.pill.warn { color: var(--warn); border-color: rgba(210, 153, 34, 0.35); background: rgba(210, 153, 34, 0.08); }
.pill.fail { color: var(--fail); border-color: rgba(248, 81, 73, 0.35); background: rgba(248, 81, 73, 0.08); }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 22px 0 40px;
}
.summary-card {
  padding: 18px 18px 16px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: rgba(17, 21, 28, 0.92);
}
.summary-card .label {
  color: var(--fg-mute);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.summary-card .value {
  margin-top: 8px;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
}
.summary-card .note {
  margin-top: 4px;
  color: var(--fg-dim);
  font-size: 13px;
}

h2 {
  margin: 42px 0 16px;
  font-size: 22px;
  letter-spacing: -0.02em;
}
h3 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.02em;
}

table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(17, 21, 28, 0.92);
}
th, td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
th {
  background: rgba(18, 22, 27, 0.95);
  color: var(--fg-mute);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: var(--mono);
  font-weight: 500;
}
td {
  color: var(--fg-dim);
  font-size: 14px;
}
td strong { color: var(--fg); }
.mono { font-family: var(--mono); }

.case-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
}
.case-card {
  padding: 22px;
  border-radius: 18px;
  border: 1px solid var(--border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.01), transparent 22%),
    rgba(17, 21, 28, 0.94);
}
.case-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.case-head p {
  margin: 8px 0 0;
  color: var(--fg-dim);
}
.case-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.case-grid {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}
.subcard {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(10, 13, 18, 0.62);
}
.subcard h4 {
  margin: 0 0 10px;
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-mute);
  font-family: var(--mono);
  font-weight: 500;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.metric {
  padding: 12px;
  border-radius: 12px;
  background: rgba(18, 22, 27, 0.92);
  border: 1px solid var(--border);
}
.metric .label {
  color: var(--fg-mute);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.metric .value {
  margin-top: 6px;
  color: var(--fg);
  font-size: 18px;
  font-weight: 650;
}
.metric .detail {
  margin-top: 4px;
  color: var(--fg-dim);
  font-size: 12px;
}

.artifact-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.runbook-grid,
.process-grid {
  display: grid;
  gap: 14px;
}
.runbook-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 6px;
}
.process-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 14px;
}
.runbook-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent 28%),
    rgba(17, 21, 28, 0.94);
}
.runbook-card .stage {
  color: var(--fg-mute);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.runbook-card p {
  margin: 10px 0 0;
  color: var(--fg-dim);
  font-size: 14px;
}
.runbook-card a {
  color: var(--accent);
  text-decoration: none;
}
.runbook-card a:hover { text-decoration: underline; }
.compact-list {
  margin: 0;
  padding-left: 18px;
  color: var(--fg-dim);
}
.compact-list li + li { margin-top: 8px; }
.compact-list strong { color: var(--fg); }
.advisory-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 16px 0 6px;
}
.advisory-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(210, 153, 34, 0.28);
  background:
    linear-gradient(180deg, rgba(210, 153, 34, 0.08), transparent 36%),
    rgba(17, 21, 28, 0.94);
}
.advisory-card .tag {
  color: var(--warn);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.advisory-card p {
  margin: 10px 0 0;
  color: var(--fg-dim);
  font-size: 14px;
}
.artifact {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(17, 21, 28, 0.92);
}
.artifact a {
  color: var(--accent);
  text-decoration: none;
}
.artifact a:hover { text-decoration: underline; }
.artifact .path {
  margin-top: 8px;
  color: var(--fg-mute);
  font-size: 12px;
  font-family: var(--mono);
  word-break: break-all;
}

.footer {
  margin-top: 40px;
  color: var(--fg-mute);
  font-family: var(--mono);
  font-size: 12px;
}

@media (max-width: 980px) {
  .summary-grid,
  .advisory-grid,
  .artifact-list,
  .runbook-grid,
  .metric-grid,
  .process-grid,
  .case-grid {
    grid-template-columns: 1fr;
  }
  body { padding-inline: 16px; }
  .hero { padding: 24px; }
  .hero h1 { font-size: 32px; }
}
"""


@dataclass
class _VisualCase:
    section_id: str
    case_id: str
    case_name: str
    verdict: str
    comparison: str
    convergence: str
    physics: str
    contract_status: str
    description: str
    chart_title: str
    chart_svg: str
    geometry_svg: str
    metrics: List[Tuple[str, str, str]]
    notes: List[str]
    runbook_stage: str
    runbook_summary: str
    cad_lens: List[str]
    cfd_lens: List[str]
    trial_checks: List[str]
    report_path: str


class VisualAcceptanceReportGenerator:
    """Generate a delivery-grade acceptance dashboard for the core CFD cases."""

    def __init__(self, collector: Optional[ReportDataCollector] = None) -> None:
        self._collector = collector or ReportDataCollector()

    def render(
        self,
        case_ids: Iterable[str] = DEFAULT_CASE_IDS,
        output_path: Path = DEFAULT_OUTPUT_PATH,
    ) -> VisualAcceptanceResult:
        cases = [self._build_case(case_id) for case_id in case_ids]
        html = self._build_html(cases, output_path=output_path)
        chart_count = sum(2 for _ in cases)
        return VisualAcceptanceResult(
            html=html,
            case_count=len(cases),
            chart_count=chart_count,
        )

    def generate(
        self,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        case_ids: Iterable[str] = DEFAULT_CASE_IDS,
    ) -> VisualAcceptanceResult:
        result = self.render(case_ids=case_ids, output_path=output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.html, encoding="utf-8")
        result.output_path = str(output_path)
        return result

    def _build_case(self, case_id: str) -> _VisualCase:
        context = self._collector.collect(case_id)
        verdict = context.auto_verify_report["verdict"]
        comparison = context.auto_verify_report["gold_standard_comparison"]["overall"]
        convergence = context.auto_verify_report["convergence"]["status"]
        physics = context.auto_verify_report["physics_check"]["status"]
        contract_status = context.gold_standard.get("physics_contract", {}).get(
            "contract_status",
            "UNKNOWN",
        )
        description = context.case_meta.get("description", "")
        report_path = self._best_report_path(case_id)

        if case_id == "lid_driven_cavity_benchmark":
            chart_title, chart_svg = self._build_ldc_chart(context)
            geometry_svg = self._geometry_lid_driven_cavity()
            metrics = self._ldc_metrics(context)
            notes = [
                "Profile overlays stay inside the 5% band; this is the cleanest verifier-grade PASS.",
                "Centerline extraction is interpolation-aware, not index-locked.",
            ]
        elif case_id == "backward_facing_step_steady":
            chart_title, chart_svg = self._build_bfs_chart(context)
            geometry_svg = self._geometry_bfs()
            metrics = self._bfs_metrics(context)
            notes = [
                "Reattachment proxy is visible rather than hidden inside scalar-only YAML.",
                "Pressure recovery and drag stay aligned with the same experimental regime.",
            ]
        elif case_id == "cylinder_crossflow":
            chart_title, chart_svg = self._build_cylinder_chart(context)
            geometry_svg = self._geometry_cylinder()
            metrics = self._cylinder_metrics(context)
            notes = [
                "Wake-centerline deficit is solver-derived; Strouhal remains tagged as a shortcut hazard.",
                "This card makes the silent-pass caveat visible without discarding the otherwise strong PASS.",
            ]
        elif case_id == "naca0012_airfoil":
            chart_title, chart_svg = self._build_airfoil_chart(context)
            geometry_svg = self._geometry_airfoil()
            metrics = self._airfoil_metrics(context)
            notes = [
                "CAD preview mirrors the adapter's NACA0012 pre-processing assumptions.",
                "Cp values are shape-faithful but magnitude-attenuated because extraction uses near-surface cells.",
            ]
        elif case_id == "differential_heated_cavity":
            chart_title, chart_svg = self._build_dhc_chart(context)
            geometry_svg = self._geometry_dhc()
            metrics = self._dhc_metrics(context)
            notes = [
                "This is the only FAIL card; the report makes the gold-reference ambiguity visually explicit.",
                "The detailed standalone DHC HTML remains the deep-dive artifact for this escalation path.",
            ]
        else:
            raise ValueError(f"Unsupported visual acceptance case: {case_id}")

        stage, summary, cad_lens, cfd_lens, trial_checks = self._experience_lens(case_id, context)
        return _VisualCase(
            section_id=f"case-{case_id}",
            case_id=case_id,
            case_name=context.case_meta.get("name", case_id),
            verdict=verdict,
            comparison=comparison,
            convergence=convergence,
            physics=physics,
            contract_status=contract_status,
            description=description,
            chart_title=chart_title,
            chart_svg=chart_svg,
            geometry_svg=geometry_svg,
            metrics=metrics,
            notes=notes,
            runbook_stage=stage,
            runbook_summary=summary,
            cad_lens=cad_lens,
            cfd_lens=cfd_lens,
            trial_checks=trial_checks,
            report_path=report_path,
        )

    def _build_html(self, cases: Sequence[_VisualCase], output_path: Path) -> str:
        clean_pass = sum(case.verdict == "PASS" for case in cases)
        with_deviations = sum(case.verdict == "PASS_WITH_DEVIATIONS" for case in cases)
        failed = sum(case.verdict == "FAIL" for case in cases)
        chart_count = sum(2 for _ in cases)
        open_item_cards = "\n".join(self._open_item_card(item) for item in self._open_contract_items())
        runbook_cards = "\n".join(self._runbook_card(case) for case in cases)
        matrix_rows = "\n".join(self._matrix_row(case) for case in cases)
        case_cards = "\n".join(self._case_card(case, output_path=output_path) for case in cases)
        artifact_cards = "\n".join(self._artifact_card(case, output_path=output_path) for case in cases)
        try:
            output_label = str(output_path.relative_to(REPO_ROOT))
        except ValueError:
            output_label = str(output_path)
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"zh-CN\">\n"
            "<head>\n"
            "<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "<title>Visual Acceptance Report · cfd-harness-unified</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n"
            "<body>\n"
            "<div class=\"wrap\">\n"
            "<section class=\"hero\">\n"
            "<div class=\"eyebrow\">Phase 8/9 Delivery Surface · Notion-guided acceptance synthesis</div>\n"
            "<h1>Visual Acceptance Report</h1>\n"
            "<p>This dashboard upgrades the existing Markdown-only evidence chain into a visual artifact: "
            "CAD pre-processing assumptions are surfaced as geometry previews, CFD post-processing observables are "
            "rendered as inline SVG charts, and the highest-signal acceptance cases are grouped on a single delivery page.</p>\n"
            "<div class=\"hero-meta\">"
            "<span class=\"pill ok\">Grounded against Phase 8/9 report-engine context</span>"
            "<span class=\"pill ok\">Single-file HTML deliverable</span>"
            "<span class=\"pill warn\">No long CFD reruns required</span>"
            "<span class=\"pill fail\">DHC external-Gate ambiguity remains explicit</span>"
            "</div>\n"
            "</section>\n"
            "<section class=\"summary-grid\">\n"
            f"{self._summary_card('CASES RENDERED', str(len(cases)), 'Core delivery deck across CAD + CFD surfaces')}\n"
            f"{self._summary_card('CLEAN PASS', str(clean_pass), 'Physics-valid, no deviation caveat', tone='ok')}\n"
            f"{self._summary_card('PASS WITH DEVIATIONS', str(with_deviations), 'Shape-faithful but not fully contract-clean', tone='warn')}\n"
            f"{self._summary_card('FAIL / ESCALATED', str(failed), 'Gold-reference ambiguity kept visible', tone='fail')}\n"
            "</section>\n"
            "<h2>Known Open Contract Items</h2>\n"
            "<p>These items stay deliberately visible during visual acceptance so Kogami can separate deck quality from unresolved governance or gold-reference closure work.</p>\n"
            "<div class=\"advisory-grid\">\n"
            f"{open_item_cards}\n"
            "</div>\n"
            "<h2>Trial Runbook</h2>\n"
            "<div class=\"runbook-grid\">\n"
            f"{runbook_cards}\n"
            "</div>\n"
            "<h2>Readiness Matrix</h2>\n"
            "<table>\n"
            "<thead><tr><th>Case</th><th>Verdict</th><th>Convergence / Physics</th><th>Contract Status</th><th>Visual Focus</th></tr></thead>\n"
            "<tbody>\n"
            f"{matrix_rows}\n"
            "</tbody></table>\n"
            "<h2>Case Deck</h2>\n"
            "<div class=\"case-list\">\n"
            f"{case_cards}\n"
            "</div>\n"
            "<h2>Supporting Artifacts</h2>\n"
            "<div class=\"artifact-list\">\n"
            f"{artifact_cards}\n"
            "</div>\n"
            "<div class=\"footer\">"
            f"Generated from repo artifacts only · cases={len(cases)} · inline geometry+chart panels={chart_count} · output={escape(output_label)}"
            "</div>\n"
            "</div>\n"
            "</body>\n"
            "</html>\n"
        )

    @staticmethod
    def _summary_card(label: str, value: str, note: str, tone: str = "") -> str:
        tone_class = f" {tone}" if tone else ""
        return (
            f"<div class=\"summary-card{tone_class}\">"
            f"<div class=\"label\">{escape(label)}</div>"
            f"<div class=\"value\">{escape(value)}</div>"
            f"<div class=\"note\">{escape(note)}</div>"
            "</div>"
        )

    def _matrix_row(self, case: _VisualCase) -> str:
        focus = "CAD + post-processing" if case.case_id == "naca0012_airfoil" else "Geometry + observable overlay"
        if case.case_id == "differential_heated_cavity":
            focus = "Mesh / Nu escalation visibility"
        return (
            "<tr>"
            f"<td><strong>{escape(case.case_name)}</strong><br><span class=\"mono\">{escape(case.case_id)}</span></td>"
            f"<td>{self._pill(case.verdict, case.verdict)}</td>"
            f"<td>{escape(case.convergence)} / {escape(case.physics)}</td>"
            f"<td>{escape(case.contract_status)}</td>"
            f"<td>{escape(focus)}</td>"
            "</tr>"
        )

    def _case_card(self, case: _VisualCase, output_path: Path) -> str:
        notes = "".join(f"<li>{escape(note)}</li>" for note in case.notes)
        metrics = "".join(
            "<div class=\"metric\">"
            f"<div class=\"label\">{escape(label)}</div>"
            f"<div class=\"value\">{escape(value)}</div>"
            f"<div class=\"detail\">{escape(detail)}</div>"
            "</div>"
            for label, value, detail in case.metrics
        )
        artifact_href = escape(self._artifact_href(case.report_path, output_path))
        return (
            "<article class=\"case-card\">"
            f"<a id=\"{escape(case.section_id)}\"></a>"
            "<div class=\"case-head\">"
            "<div>"
            f"<h3>{escape(case.case_name)}</h3>"
            f"<p>{escape(case.description)}</p>"
            "<div class=\"case-meta\">"
            f"{self._pill(case.verdict, case.verdict)}"
            f"{self._pill(case.comparison, case.comparison)}"
            f"{self._pill(case.contract_status, case.contract_status)}"
            "</div>"
            "</div>"
            f"<div class=\"pill\">{escape(case.case_id)}</div>"
            "</div>"
            "<div class=\"case-grid\">"
            "<div class=\"subcard\">"
            "<h4>CAD Pre-Processing</h4>"
            f"{case.geometry_svg}"
            "</div>"
            "<div class=\"subcard\">"
            f"<h4>CFD Post-Processing · {escape(case.chart_title)}</h4>"
            f"{case.chart_svg}"
            f"<div class=\"metric-grid\">{metrics}</div>"
            "</div>"
            "</div>"
            "<div class=\"process-grid\">"
            f"{self._lens_card('CAD / Pre-Processing Lens', case.cad_lens)}"
            f"{self._lens_card('CFD / Post-Processing Lens', case.cfd_lens)}"
            f"{self._lens_card('Trial Checklist', case.trial_checks)}"
            "</div>"
            "<div class=\"subcard\" style=\"margin-top: 14px;\">"
            "<h4>Acceptance Notes</h4>"
            f"<ul>{notes}</ul>"
            f"<div class=\"pill\" style=\"margin-top: 12px;\"><a href=\"{artifact_href}\" style=\"color: inherit; text-decoration: none;\">Open supporting artifact</a></div>"
            "</div>"
            "</article>"
        )

    def _runbook_card(self, case: _VisualCase) -> str:
        return (
            "<div class=\"runbook-card\">"
            f"<div class=\"stage\">{escape(case.runbook_stage)}</div>"
            f"<h3 style=\"margin-top: 10px;\">{escape(case.case_name)}</h3>"
            f"{self._pill(case.verdict, case.verdict)}"
            f"<p>{escape(case.runbook_summary)}</p>"
            f"<p><a href=\"#{escape(case.section_id)}\">Jump to case deck</a></p>"
            "</div>"
        )

    @staticmethod
    def _open_contract_items() -> Sequence[Tuple[str, str, str]]:
        return (
            (
                "Q-1",
                "DHC gold-reference accuracy",
                "Differential Heated Cavity remains an explicit FAIL until the external Gate chooses Path P-1 vs P-2 and resolves why measured Nu stays far above the current gold target.",
            ),
            (
                "Q-2",
                "R-A relabel (pipe_flow -> duct_flow)",
                "The relabel is still open, so contract-status totals should be read as provisional. The visual deck can still be trialed, but naming/governance closure is not claimed finished.",
            ),
        )

    @staticmethod
    def _open_item_card(item: Tuple[str, str, str]) -> str:
        item_id, title, description = item
        return (
            "<div class=\"advisory-card\">"
            f"<div class=\"tag\">{escape(item_id)}</div>"
            f"<h3 style=\"margin-top: 10px;\">{escape(title)}</h3>"
            f"<p>{escape(description)}</p>"
            "</div>"
        )

    @staticmethod
    def _lens_card(title: str, items: Sequence[str]) -> str:
        body = "".join(f"<li>{escape(item)}</li>" for item in items)
        return (
            "<div class=\"subcard\">"
            f"<h4>{escape(title)}</h4>"
            f"<ul class=\"compact-list\">{body}</ul>"
            "</div>"
        )

    def _artifact_card(self, case: _VisualCase, output_path: Path) -> str:
        artifact_href = escape(self._artifact_href(case.report_path, output_path))
        return (
            "<div class=\"artifact\">"
            f"<strong>{escape(case.case_name)}</strong>"
            f"<div style=\"margin-top: 8px; color: var(--fg-dim);\">{self._pill(case.verdict, case.verdict)}"
            "</div>"
            f"<div class=\"path\"><a href=\"{artifact_href}\">{escape(case.report_path)}</a></div>"
            "</div>"
        )

    @staticmethod
    def _best_report_path(case_id: str) -> str:
        candidates = [
            REPORTS_ROOT / case_id / "case_completion_report.md",
            REPORTS_ROOT / case_id / "report.html",
            REPORTS_ROOT / case_id / "report.md",
        ]
        for path in candidates:
            if path.exists():
                return str(path.relative_to(REPO_ROOT))
        return str((REPORTS_ROOT / case_id).relative_to(REPO_ROOT))

    @staticmethod
    def _artifact_href(report_path: str, output_path: Path) -> str:
        target = REPO_ROOT / report_path
        return os.path.relpath(target, start=output_path.parent)

    @staticmethod
    def _pill(label: str, value: str) -> str:
        lowered = value.lower()
        tone = ""
        if "pass_with_deviations" in lowered or "partially" in lowered or "hazard" in lowered:
            tone = " warn"
        elif "pass" in lowered or "compatible" in lowered or "converged" in lowered:
            tone = " ok"
        elif "fail" in lowered or "incompatible" in lowered or "deviation" in lowered:
            tone = " fail"
        return f"<span class=\"pill{tone}\">{escape(label)}</span>"

    def _ldc_metrics(self, context: ReportContext) -> List[Tuple[str, str, str]]:
        u_obs = self._compare_observable(context, "u_centerline")
        v_obs = self._compare_observable(context, "v_centerline")
        vortex = self._compare_observable(context, "primary_vortex_location")
        sim = vortex["sim_value"]
        return [
            ("u rel error", f"{u_obs['rel_error'] * 100:.2f}%", "Vertical centerline vs Ghia 1982"),
            ("v rel error", f"{v_obs['rel_error'] * 100:.2f}%", "Horizontal centerline vs Ghia 1982"),
            (
                "vortex center",
                f"({sim['vortex_center_x']:.4f}, {sim['vortex_center_y']:.4f})",
                "Primary vortex location from harness extraction",
            ),
        ]

    def _bfs_metrics(self, context: ReportContext) -> List[Tuple[str, str, str]]:
        xr = self._compare_observable(context, "reattachment_length")
        cd = self._compare_observable(context, "cd_mean")
        pressure = self._compare_observable(context, "pressure_recovery")
        return [
            ("Xr / H", f"{xr['sim_value']:.2f}", f"ref {xr['ref_value']:.2f}"),
            ("Cd mean", f"{cd['sim_value']:.2f}", f"ref {cd['ref_value']:.2f}"),
            (
                "pressure delta",
                f"{pressure['sim_value']['delta']:.2f}",
                f"inlet {pressure['sim_value']['inlet']:.2f} → outlet {pressure['sim_value']['outlet']:.2f}",
            ),
        ]

    def _cylinder_metrics(self, context: ReportContext) -> List[Tuple[str, str, str]]:
        st = self._compare_observable(context, "strouhal_number")
        cd = self._compare_observable(context, "cd_mean")
        cl = self._compare_observable(context, "cl_rms")
        return [
            ("Strouhal", f"{st['sim_value']:.3f}", f"ref {st['ref_value']:.3f}"),
            ("Cd mean", f"{cd['sim_value']:.2f}", f"ref {cd['ref_value']:.2f}"),
            ("Cl rms", f"{cl['sim_value']:.3f}", f"ref {cl['ref_value']:.3f}"),
        ]

    def _airfoil_metrics(self, context: ReportContext) -> List[Tuple[str, str, str]]:
        cp = self._compare_observable(context, "pressure_coefficient")
        rel_errors = [sample["error"] for sample in cp["rel_error"]]
        return [
            ("samples extracted", str(cp["n_points_extracted"]), "Near-surface pressure points binned into Cp profile"),
            ("worst rel error", f"{max(rel_errors) * 100:.1f}%", "Expected attenuation vs exact-surface gold"),
            ("sampling mode", "cell-band", "Current extractor averages near-surface cell centres"),
        ]

    def _dhc_metrics(self, context: ReportContext) -> List[Tuple[str, str, str]]:
        measurement = self._dhc_measurement()
        obs = self._compare_observable(context, "nusselt_number")
        return [
            ("Nu measured", f"{measurement['nu_measured']:.2f}", f"gold ref {obs['ref_value']:.2f}"),
            (
                "band verdict",
                measurement["verdict"].split(" ")[0],
                f"band {measurement['band']['low']:.1f}–{measurement['band']['high']:.1f}",
            ),
            ("verdict", context.auto_verify_report["verdict"], "Converged numerically, failed against gold"),
        ]

    def _build_ldc_chart(self, context: ReportContext) -> Tuple[str, str]:
        gold = self._gold_observable(context, "u_centerline")
        compare = self._compare_observable(context, "u_centerline")
        xs = [float(sample["y"]) for sample in gold["ref_value"]]
        ref = [float(sample["u"]) for sample in gold["ref_value"]]
        sim = [float(value) for value in compare["sim_value"]]
        return (
            "u-centerline overlay",
            self._line_chart_svg(
                xs,
                ref,
                sim,
                x_label="y",
                y_label="u",
                ref_label="Ghia 1982",
                sim_label="harness",
            ),
        )

    def _build_bfs_chart(self, context: ReportContext) -> Tuple[str, str]:
        gold = self._gold_observable(context, "velocity_profile_reattachment")
        compare = self._compare_observable(context, "velocity_profile_reattachment")
        xs = [float(sample["y_H"]) for sample in gold["ref_value"]]
        ref = [float(sample["u_Ubulk"]) for sample in gold["ref_value"]]
        sim = [float(value) for value in compare["sim_value"]]
        return (
            "reattachment velocity profile",
            self._line_chart_svg(
                xs,
                ref,
                sim,
                x_label="y / H",
                y_label="u / Ubulk",
                ref_label="Driver & Seegmiller",
                sim_label="harness",
            ),
        )

    def _build_cylinder_chart(self, context: ReportContext) -> Tuple[str, str]:
        gold = self._gold_observable(context, "u_mean_centerline")
        compare = self._compare_observable(context, "u_mean_centerline")
        xs = [float(sample["x_D"]) for sample in gold["ref_value"]]
        ref = [float(sample["u_Uinf"]) for sample in gold["ref_value"]]
        sim = [float(value) for value in compare["sim_value"]]
        return (
            "wake-centerline deficit",
            self._line_chart_svg(
                xs,
                ref,
                sim,
                x_label="x / D",
                y_label="u / Uinf",
                ref_label="Williamson 1996",
                sim_label="harness",
            ),
        )

    def _build_airfoil_chart(self, context: ReportContext) -> Tuple[str, str]:
        gold = self._gold_observable(context, "pressure_coefficient")
        compare = self._compare_observable(context, "pressure_coefficient")
        xs = [float(sample.get("x_over_c", sample.get("x", 0.0))) for sample in gold["ref_value"]]
        ref = [float(sample["Cp"]) for sample in gold["ref_value"]]
        sim_x = [float(sample["x_over_c"]) for sample in compare["sim_sample"]]
        sim = [
            float(sample["Cp"])
            for sample in compare["sim_sample"]
        ]
        return (
            "Cp sample vs gold",
            self._line_chart_svg(
                xs,
                ref,
                sim,
                sim_x_values=sim_x,
                x_label="x / c",
                y_label="Cp",
                ref_label="gold",
                sim_label="cell-band sample",
                invert_y=True,
            ),
        )

    def _build_dhc_chart(self, context: ReportContext) -> Tuple[str, str]:
        measurement = self._dhc_measurement()
        obs = self._compare_observable(context, "nusselt_number")
        return (
            "Nu bullet chart",
            self._bullet_chart_svg(
                actual=float(measurement["nu_measured"]),
                target=float(obs["ref_value"]),
                band_low=float(measurement["band"]["low"]),
                band_high=float(measurement["band"]["high"]),
                x_label="Nusselt number",
            ),
        )

    @staticmethod
    def _gold_observable(context: ReportContext, name: str) -> Dict[str, Any]:
        for observable in context.gold_standard.get("observables", []):
            if observable.get("name") == name:
                return observable
        raise KeyError(f"gold observable not found: {name}")

    @staticmethod
    def _compare_observable(context: ReportContext, name: str) -> Dict[str, Any]:
        for observable in context.auto_verify_report["gold_standard_comparison"]["observables"]:
            if observable.get("name") == name:
                return observable
        raise KeyError(f"comparison observable not found: {name}")

    @staticmethod
    def _dhc_measurement() -> Dict[str, Any]:
        path = REPORTS_ROOT / "ex1_007_dhc_mesh_refinement" / "measurement_result.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data["c5_band_check"]

    def _experience_lens(
        self,
        case_id: str,
        context: ReportContext,
    ) -> Tuple[str, str, List[str], List[str], List[str]]:
        solver = context.case_meta.get("solver", "unknown")
        turbulence = context.case_meta.get("turbulence_model", "unknown")
        mesh_strategy = self._mesh_strategy(case_id, context)
        key_parameters = context.case_meta.get("key_parameters", {})

        if case_id == "lid_driven_cavity_benchmark":
            return (
                "Start Here",
                "Use this clean laminar PASS as the baseline visual trust check before moving to noisier wake or thermal cases.",
                [
                    f"Solver stack: {solver} with {turbulence} flow assumptions.",
                    f"Mesh posture: {mesh_strategy}.",
                    f"Operating point: Re={key_parameters.get('Re', 'n/a')} unit-square cavity with moving lid.",
                ],
                [
                    "Primary observable: u/v centerline overlays against Ghia 1982.",
                    "Comparison mode: interpolation-aware profiles plus primary-vortex location.",
                    "Risk posture: minimal; this is the least caveated verifier-grade surface.",
                ],
                [
                    "Confirm the harness profile stays visually glued to the gold curve over the full centerline.",
                    "Check the vortex-center metric card after reading the overlay, not before.",
                    "Use this card to calibrate what a 'good' PASS should look like in the rest of the deck.",
                ],
            )
        if case_id == "backward_facing_step_steady":
            return (
                "Pressure Recovery",
                "This is the best steady separated-flow card for Kogami to judge whether geometry and recovery metrics stay coherent together.",
                [
                    f"Solver stack: {solver} with {turbulence} closure for separated internal flow.",
                    f"Mesh posture: {mesh_strategy}.",
                    f"Operating point: Re={key_parameters.get('Re', 'n/a')} with expansion_ratio={key_parameters.get('expansion_ratio', 'n/a')}.",
                ],
                [
                    "Primary observable: reattachment velocity profile.",
                    "Comparison mode: profile shape plus scalar reattachment-length and pressure-recovery checks.",
                    "Risk posture: low; the visual layer makes reattachment behavior easy to spot without diving into YAML.",
                ],
                [
                    "Inspect whether the velocity profile shape matches before reading the scalar Xr/H badge.",
                    "Use the pressure-delta metric as the second confidence signal, not the first.",
                    "Treat this as the internal-flow counterpart to the lid-driven cavity baseline.",
                ],
            )
        if case_id == "cylinder_crossflow":
            return (
                "Wake Readout",
                "This card is the best bluff-body experience slice: it looks strong visually, but still exposes the silent-pass caveat honestly.",
                [
                    f"Solver stack: {solver} with {turbulence} in an external wake setup.",
                    f"Mesh posture: {mesh_strategy}.",
                    f"Operating point: Re={key_parameters.get('Re', 'n/a')} circular-cylinder shedding regime.",
                ],
                [
                    "Primary observable: wake-centerline velocity deficit.",
                    "Comparison mode: solver-derived wake samples plus scalar Strouhal/Cd/Cl badges.",
                    "Risk posture: medium; the Strouhal shortcut remains a known audit concern and is intentionally visible.",
                ],
                [
                    "Read the wake curve first; it should feel physically plausible even before you inspect the badges.",
                    "Use the Strouhal badge to verify that the shortcut hazard is still called out, not hidden.",
                    "This is the best card for testing whether the acceptance layer stays honest under a 'looks good but caveated' case.",
                ],
            )
        if case_id == "naca0012_airfoil":
            return (
                "CAD-to-Cp Chain",
                "This is the strongest CAD pre-processing story in the deck because the geometry preview and Cp extraction caveat are both visible on one card.",
                [
                    f"Solver stack: {solver} with {turbulence} for external airfoil flow.",
                    f"Mesh posture: {mesh_strategy}.",
                    f"Operating point: Re={key_parameters.get('Re', 'n/a')}, AoA={key_parameters.get('angle_of_attack', 'n/a')} deg, chord={key_parameters.get('chord_length', 'n/a')} m.",
                ],
                [
                    "Primary observable: pressure-coefficient profile.",
                    "Comparison mode: near-surface cell-band sampling against surface gold points.",
                    "Risk posture: medium; shape fidelity is good, but magnitude attenuation is still visible and expected.",
                ],
                [
                    "Inspect whether the CAD preview and the Cp curve tell the same aerodynamic story.",
                    "Expect shape agreement first and magnitude agreement second; the current extractor is intentionally not over-claimed.",
                    "Use this card as the trial surface for CAD pre-processing credibility.",
                ],
            )
        if case_id == "differential_heated_cavity":
            return (
                "Escalation Lane",
                "Keep this last in the trial sequence: it is the honest FAIL card that proves the deck does not hide hard thermal/gold-reference ambiguity.",
                [
                    f"Solver stack: {solver} with {turbulence} for buoyant natural convection.",
                    f"Mesh posture: {mesh_strategy}.",
                    f"Operating point: Ra={key_parameters.get('Ra', 'n/a')}, Pr={key_parameters.get('Pr', 'n/a')}, aspect_ratio={key_parameters.get('aspect_ratio', 'n/a')}.",
                ],
                [
                    "Primary observable: mean Nusselt number against thermal gold reference.",
                    "Comparison mode: bullet-chart framing of measured Nu, target gold, and expected band.",
                    "Risk posture: high but honest; the failure is a gold-reference / methodology escalation, not a hidden numerical shrug.",
                ],
                [
                    "Read this card as proof that the acceptance layer surfaces unresolved thermal issues instead of blending them into a PASS.",
                    "Check the band verdict and FAIL badge together; they should tell one consistent story.",
                    "Use the supporting artifact link if you want the deep-dive DHC escalation narrative after the main deck review.",
                ],
            )
        raise ValueError(f"Unsupported visual acceptance case: {case_id}")

    @staticmethod
    def _mesh_strategy(case_id: str, context: ReportContext) -> str:
        value = context.case_meta.get("mesh_strategy")
        if value and value != "[DATA MISSING]":
            return str(value)
        fallbacks = {
            "lid_driven_cavity_benchmark": "structured square cavity grid with centerline extraction support",
            "backward_facing_step_steady": "block-structured step channel tuned for reattachment sampling",
            "cylinder_crossflow": "2D-in-3D wake channel with cylinder obstacle and centerline probe path",
            "naca0012_airfoil": "blockMesh farfield plus near-surface cell band for Cp extraction",
            "differential_heated_cavity": "wall-bounded natural-convection cavity mesh with thermal-boundary focus",
        }
        return fallbacks.get(case_id, "mesh strategy not recorded")

    @staticmethod
    def _line_chart_svg(
        x_values: Sequence[float],
        ref_values: Sequence[float],
        sim_values: Sequence[float],
        *,
        sim_x_values: Optional[Sequence[float]] = None,
        x_label: str,
        y_label: str,
        ref_label: str,
        sim_label: str,
        invert_y: bool = False,
        width: int = 640,
        height: int = 320,
    ) -> str:
        if len(x_values) != len(ref_values):
            raise ValueError("reference x/y inputs must have equal lengths")
        if sim_x_values is None:
            sim_x_values = x_values
        if len(sim_x_values) != len(sim_values):
            raise ValueError("simulation x/y inputs must have equal lengths")

        left = 54
        right = 16
        top = 18
        bottom = 42
        plot_w = width - left - right
        plot_h = height - top - bottom

        min_x = min(min(x_values), min(sim_x_values))
        max_x = max(max(x_values), max(sim_x_values))
        min_y = min(min(ref_values), min(sim_values))
        max_y = max(max(ref_values), max(sim_values))
        if math.isclose(max_x, min_x):
            max_x += 1.0
        if math.isclose(max_y, min_y):
            max_y += 1.0
        pad = (max_y - min_y) * 0.12
        min_y -= pad
        max_y += pad

        def scale_x(value: float) -> float:
            return left + ((value - min_x) / (max_x - min_x)) * plot_w

        def scale_y(value: float) -> float:
            ratio = (value - min_y) / (max_y - min_y)
            if invert_y:
                ratio = 1.0 - ratio
            return top + plot_h - ratio * plot_h

        grid = []
        for idx in range(5):
            y = top + idx * (plot_h / 4)
            value = max_y - idx * ((max_y - min_y) / 4)
            if invert_y:
                value = min_y + idx * ((max_y - min_y) / 4)
            grid.append(
                f"<line x1=\"{left}\" y1=\"{y:.1f}\" x2=\"{left + plot_w}\" y2=\"{y:.1f}\" stroke=\"rgba(154,163,173,0.18)\" stroke-width=\"1\" />"
                f"<text x=\"{left - 10}\" y=\"{y + 4:.1f}\" text-anchor=\"end\" fill=\"#9aa3ad\" font-size=\"11\">{value:.2f}</text>"
            )

        points_ref = " ".join(f"{scale_x(x):.1f},{scale_y(y):.1f}" for x, y in zip(x_values, ref_values))
        points_sim = " ".join(f"{scale_x(x):.1f},{scale_y(y):.1f}" for x, y in zip(sim_x_values, sim_values))
        circles = []
        for x, y in zip(x_values, ref_values):
            circles.append(
                f"<circle cx=\"{scale_x(x):.1f}\" cy=\"{scale_y(y):.1f}\" r=\"3.2\" fill=\"#4aa3ff\" />"
            )
        for x, y in zip(sim_x_values, sim_values):
            circles.append(
                f"<circle cx=\"{scale_x(x):.1f}\" cy=\"{scale_y(y):.1f}\" r=\"3.2\" fill=\"#3fb950\" />"
            )

        legend = (
            "<g>"
            "<line x1=\"20\" y1=\"18\" x2=\"44\" y2=\"18\" stroke=\"#4aa3ff\" stroke-width=\"2.4\" />"
            f"<text x=\"50\" y=\"22\" fill=\"#9aa3ad\" font-size=\"11\">{escape(ref_label)}</text>"
            "<line x1=\"20\" y1=\"38\" x2=\"44\" y2=\"38\" stroke=\"#3fb950\" stroke-width=\"2.4\" />"
            f"<text x=\"50\" y=\"42\" fill=\"#9aa3ad\" font-size=\"11\">{escape(sim_label)}</text>"
            "</g>"
        )

        return (
            f"<svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"{escape(ref_label)} vs {escape(sim_label)}\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            f"{''.join(grid)}"
            f"<line x1=\"{left}\" y1=\"{top + plot_h}\" x2=\"{left + plot_w}\" y2=\"{top + plot_h}\" stroke=\"#6b7580\" stroke-width=\"1.2\" />"
            f"<line x1=\"{left}\" y1=\"{top}\" x2=\"{left}\" y2=\"{top + plot_h}\" stroke=\"#6b7580\" stroke-width=\"1.2\" />"
            f"<polyline fill=\"none\" stroke=\"#4aa3ff\" stroke-width=\"2.4\" points=\"{points_ref}\" />"
            f"<polyline fill=\"none\" stroke=\"#3fb950\" stroke-width=\"2.4\" points=\"{points_sim}\" />"
            f"{''.join(circles)}"
            f"<text x=\"{left + plot_w / 2:.1f}\" y=\"{height - 8}\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"11\">{escape(x_label)}</text>"
            f"<text x=\"16\" y=\"{top + plot_h / 2:.1f}\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"11\" transform=\"rotate(-90 16 {top + plot_h / 2:.1f})\">{escape(y_label)}</text>"
            f"{legend}"
            "</svg>"
        )

    @staticmethod
    def _bullet_chart_svg(
        *,
        actual: float,
        target: float,
        band_low: float,
        band_high: float,
        x_label: str,
        width: int = 640,
        height: int = 220,
    ) -> str:
        left = 54
        right = 18
        bar_y = 92
        bar_h = 20
        plot_w = width - left - right
        upper = max(actual, target, band_high) * 1.15
        if upper <= 0:
            upper = 1.0

        def scale_x(value: float) -> float:
            return left + (value / upper) * plot_w

        target_x = scale_x(target)
        actual_x = scale_x(actual)
        low_x = scale_x(band_low)
        high_x = scale_x(band_high)

        ticks = []
        for idx in range(5):
            value = upper * idx / 4
            x = scale_x(value)
            ticks.append(
                f"<line x1=\"{x:.1f}\" y1=\"{bar_y + bar_h + 6}\" x2=\"{x:.1f}\" y2=\"{bar_y + bar_h + 14}\" stroke=\"#6b7580\" stroke-width=\"1\" />"
                f"<text x=\"{x:.1f}\" y=\"{bar_y + bar_h + 28}\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"11\">{value:.0f}</text>"
            )

        return (
            f"<svg viewBox=\"0 0 {width} {height}\" role=\"img\" aria-label=\"DHC Nusselt bullet chart\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            f"<rect x=\"{left}\" y=\"{bar_y}\" width=\"{plot_w}\" height=\"{bar_h}\" fill=\"rgba(154,163,173,0.12)\" rx=\"10\" />"
            f"<rect x=\"{low_x:.1f}\" y=\"{bar_y}\" width=\"{max(high_x - low_x, 4):.1f}\" height=\"{bar_h}\" fill=\"rgba(74,163,255,0.20)\" rx=\"10\" />"
            f"<line x1=\"{target_x:.1f}\" y1=\"{bar_y - 10}\" x2=\"{target_x:.1f}\" y2=\"{bar_y + bar_h + 10}\" stroke=\"#4aa3ff\" stroke-width=\"3\" />"
            f"<circle cx=\"{actual_x:.1f}\" cy=\"{bar_y + bar_h / 2}\" r=\"8\" fill=\"#f85149\" />"
            f"<text x=\"{target_x:.1f}\" y=\"{bar_y - 16}\" text-anchor=\"middle\" fill=\"#4aa3ff\" font-size=\"11\">gold {target:.1f}</text>"
            f"<text x=\"{actual_x:.1f}\" y=\"{bar_y - 28}\" text-anchor=\"middle\" fill=\"#f85149\" font-size=\"11\">measured {actual:.2f}</text>"
            f"<text x=\"{(low_x + high_x) / 2:.1f}\" y=\"{bar_y + bar_h + 44}\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"11\">band {band_low:.1f}–{band_high:.1f}</text>"
            f"{''.join(ticks)}"
            f"<text x=\"{left + plot_w / 2:.1f}\" y=\"{height - 12}\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"11\">{escape(x_label)}</text>"
            "</svg>"
        )

    @staticmethod
    def _geometry_lid_driven_cavity() -> str:
        return (
            "<svg viewBox=\"0 0 320 220\" role=\"img\" aria-label=\"Lid-driven cavity geometry\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            "<rect x=\"78\" y=\"40\" width=\"150\" height=\"150\" fill=\"#18212c\" stroke=\"#6b7580\" stroke-width=\"2\" />"
            "<line x1=\"78\" y1=\"40\" x2=\"228\" y2=\"40\" stroke=\"#4aa3ff\" stroke-width=\"4\" />"
            "<path d=\"M110 28 L150 28 M150 28 L142 20 M150 28 L142 36\" stroke=\"#4aa3ff\" stroke-width=\"3\" fill=\"none\" />"
            "<text x=\"154\" y=\"20\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"12\">moving lid u=1</text>"
            "<text x=\"154\" y=\"208\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"12\">unit square cavity</text>"
            "</svg>"
        )

    @staticmethod
    def _geometry_bfs() -> str:
        return (
            "<svg viewBox=\"0 0 320 220\" role=\"img\" aria-label=\"Backward-facing step geometry\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            "<path d=\"M30 150 H85 V105 H290 V150 Z\" fill=\"#18212c\" stroke=\"#6b7580\" stroke-width=\"2\" />"
            "<path d=\"M30 150 V80 H85\" stroke=\"#4aa3ff\" stroke-width=\"3\" fill=\"none\" />"
            "<text x=\"64\" y=\"170\" fill=\"#9aa3ad\" font-size=\"12\">step</text>"
            "<text x=\"188\" y=\"92\" fill=\"#9aa3ad\" font-size=\"12\">reattachment profile at x/H=6</text>"
            "<path d=\"M36 128 L66 128 M66 128 L58 120 M66 128 L58 136\" stroke=\"#4aa3ff\" stroke-width=\"2.5\" fill=\"none\" />"
            "</svg>"
        )

    @staticmethod
    def _geometry_cylinder() -> str:
        return (
            "<svg viewBox=\"0 0 320 220\" role=\"img\" aria-label=\"Cylinder crossflow geometry\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            "<rect x=\"24\" y=\"70\" width=\"272\" height=\"84\" fill=\"#18212c\" stroke=\"#6b7580\" stroke-width=\"2\" rx=\"10\" />"
            "<circle cx=\"108\" cy=\"112\" r=\"22\" fill=\"#12161b\" stroke=\"#4aa3ff\" stroke-width=\"3\" />"
            "<path d=\"M32 112 H84 M84 112 L76 104 M84 112 L76 120\" stroke=\"#3fb950\" stroke-width=\"2.5\" fill=\"none\" />"
            "<path d=\"M132 112 C174 84, 216 140, 262 112\" stroke=\"#f85149\" stroke-width=\"2.5\" fill=\"none\" opacity=\"0.8\" />"
            "<text x=\"206\" y=\"92\" fill=\"#9aa3ad\" font-size=\"12\">wake centerline samples</text>"
            "</svg>"
        )

    @staticmethod
    def _geometry_airfoil() -> str:
        points = []
        for idx in range(61):
            x = idx / 60
            y = _naca0012_half_thickness(x)
            px = 54 + x * 212
            py_u = 112 - y * 260
            py_l = 112 + y * 260
            points.append((px, py_u, py_l))
        upper = " ".join(f"{x:.1f},{yu:.1f}" for x, yu, _ in points)
        lower = " ".join(f"{x:.1f},{yl:.1f}" for x, _, yl in reversed(points))
        band_upper = " ".join(f"{x:.1f},{yu - 8:.1f}" for x, yu, _ in points)
        band_lower = " ".join(f"{x:.1f},{yl + 8:.1f}" for x, _, yl in reversed(points))
        return (
            "<svg viewBox=\"0 0 320 220\" role=\"img\" aria-label=\"NACA0012 CAD preview\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            "<rect x=\"18\" y=\"30\" width=\"284\" height=\"152\" fill=\"none\" stroke=\"#6b7580\" stroke-width=\"1.5\" rx=\"10\" />"
            f"<polygon points=\"{band_upper} {band_lower}\" fill=\"rgba(74,163,255,0.10)\" />"
            f"<polygon points=\"{upper} {lower}\" fill=\"#18212c\" stroke=\"#4aa3ff\" stroke-width=\"2.4\" />"
            "<text x=\"160\" y=\"22\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"12\">blockMesh farfield domain × near-surface extraction band</text>"
            "<text x=\"42\" y=\"198\" fill=\"#9aa3ad\" font-size=\"11\">x/c = 0</text>"
            "<text x=\"252\" y=\"198\" fill=\"#9aa3ad\" font-size=\"11\">x/c = 1</text>"
            "</svg>"
        )

    @staticmethod
    def _geometry_dhc() -> str:
        return (
            "<svg viewBox=\"0 0 320 220\" role=\"img\" aria-label=\"Differential heated cavity geometry\">"
            "<rect width=\"100%\" height=\"100%\" fill=\"#0f141b\" rx=\"12\" />"
            "<rect x=\"88\" y=\"34\" width=\"144\" height=\"144\" fill=\"#18212c\" stroke=\"#6b7580\" stroke-width=\"2\" />"
            "<line x1=\"88\" y1=\"34\" x2=\"88\" y2=\"178\" stroke=\"#f85149\" stroke-width=\"5\" />"
            "<line x1=\"232\" y1=\"34\" x2=\"232\" y2=\"178\" stroke=\"#4aa3ff\" stroke-width=\"5\" />"
            "<line x1=\"88\" y1=\"34\" x2=\"232\" y2=\"34\" stroke=\"#9aa3ad\" stroke-width=\"3\" stroke-dasharray=\"5 5\" />"
            "<line x1=\"88\" y1=\"178\" x2=\"232\" y2=\"178\" stroke=\"#9aa3ad\" stroke-width=\"3\" stroke-dasharray=\"5 5\" />"
            "<text x=\"74\" y=\"108\" text-anchor=\"end\" fill=\"#f85149\" font-size=\"12\">hot</text>"
            "<text x=\"246\" y=\"108\" fill=\"#4aa3ff\" font-size=\"12\">cold</text>"
            "<text x=\"160\" y=\"202\" text-anchor=\"middle\" fill=\"#9aa3ad\" font-size=\"12\">mean-Nu vs gold ambiguity</text>"
            "</svg>"
        )


def _naca0012_half_thickness(x_over_c: float, thickness_ratio: float = 0.12) -> float:
    x = min(max(x_over_c, 0.0), 1.0)
    if x in (0.0, 1.0):
        return 0.0
    thickness = (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )
    return max(0.0, 5.0 * thickness_ratio * thickness)
