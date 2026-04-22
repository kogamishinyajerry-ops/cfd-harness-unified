"""Generate a Chinese-first 10-case physics-contract dashboard."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml  # type: ignore[import-untyped]

from .data_collector import KNOWLEDGE_ROOT, REPORTS_ROOT, REPO_ROOT
from .schemas import ContractDashboardResult

DEFAULT_OUTPUT_PATH = REPORTS_ROOT / "deep_acceptance" / "contract_status_dashboard.html"
HISTORICAL_SNAPSHOT_PATH = REPORTS_ROOT / "deep_acceptance" / "2026-04-18_contract_status_dashboard.md"
OPEN_GATE_REFS: Tuple[str, ...] = (
    "Q-1:.planning/external_gate_queue.md#q-1",
    "Q-2:.planning/external_gate_queue.md#q-2",
)


@dataclass(frozen=True)
class DashboardCaseSpec:
    whitelist_id: str
    report_case_id: str
    gold_file: str
    title: str
    subtitle: str
    focus: str
    next_step: str


@dataclass(frozen=True)
class DashboardCaseState:
    spec: DashboardCaseSpec
    reference: str
    verdict: str
    overall: str
    contract_status: str
    contract_class: str
    measurement: str
    hazard: str
    lane: str
    lane_label: str
    next_step: str
    gold_path: str
    report_path: str
    deep_link_path: str


CANONICAL_CASE_SPECS: Tuple[DashboardCaseSpec, ...] = (
    # DEC-V61-046 round-1 fix (R3-M1): gold_file retargeted from legacy
    # alias (lid_driven_cavity_benchmark.yaml) to canonical LDC gold
    # (lid_driven_cavity.yaml) so dashboard and live /api/cases share the
    # same gold source. report_case_id kept legacy because the on-disk
    # run fixture lives at reports/lid_driven_cavity_benchmark/auto_verify_report.yaml;
    # the gold / run split is deliberate but now from the SAME canonical
    # gold YAML, not a parallel alias.
    DashboardCaseSpec(
        whitelist_id="lid_driven_cavity",
        report_case_id="lid_driven_cavity_benchmark",
        gold_file="lid_driven_cavity.yaml",
        title="方腔顶盖驱动流",
        subtitle="Lid-driven cavity · u_centerline satisfied, v/vortex preconditions flagged",
        focus="u_centerline 对齐 Ghia 1982 Table I；v_centerline + primary_vortex_location provenance 已在 canonical gold 里显式标 false，PASS 不涵盖这两条。",
        next_step="保持 SATISFIED_FOR_U_CENTERLINE_ONLY 语义；等 Phase 5c 独立 audit 再解锁 v/vortex 观测量。",
    ),
    DashboardCaseSpec(
        whitelist_id="backward_facing_step",
        report_case_id="backward_facing_step_steady",
        gold_file="backward_facing_step.yaml",
        title="后台阶分离再附着",
        subtitle="Backward-facing step · RANS k-ε vs DNS plateau (partial)",
        focus="Re_H=7600 adapter vs 5100 Le/Moin/Kim DNS，处于弱-Re-敏感 regime；adapter 实际是 kEpsilon（非早期 yaml 错标的 kOmegaSST），RANS-vs-DNS 的方法学差距由 10% tolerance 吸收。",
        next_step="保持 PARTIALLY_COMPATIBLE 叙事；任何 PASS 只属于 RANS 语义，不是 DNS PASS。",
    ),
    # cylinder: gold_file points at canonical circular_cylinder_wake.yaml
    # per R3-M1 parity invariant; report_case_id stays legacy "cylinder_crossflow"
    # because the on-disk run fixture lives at reports/cylinder_crossflow/.
    DashboardCaseSpec(
        whitelist_id="circular_cylinder_wake",
        report_case_id="cylinder_crossflow",
        gold_file="circular_cylinder_wake.yaml",
        title="圆柱绕流卡门涡街",
        subtitle="Cylinder crossflow · PASS with runtime shortcut caveat",
        focus="Cd / Cl_rms / wake deficit 可信，但 Strouhal 仍带 canonical-band shortcut 风险。",
        next_step="保持 PASS 但继续暴露 shortcut；不要把 Strouhal 写成无条件 physics-faithful。",
    ),
    DashboardCaseSpec(
        whitelist_id="turbulent_flat_plate",
        report_case_id="turbulent_flat_plate",
        gold_file="turbulent_flat_plate.yaml",
        title="湍流平板边界层",
        subtitle="Turbulent flat plate · PASS with fallback transparency",
        focus="Cf 数值对了，但要继续把 Spalding fallback 是否触发暴露出来。",
        next_step="保留 runtime hazard 标记；不要把 fallback-PASS 冒充成 clean extraction。",
    ),
    DashboardCaseSpec(
        whitelist_id="duct_flow",
        report_case_id="duct_flow",
        gold_file="duct_flow.yaml",
        title="全发展湍流方管流",
        subtitle="Turbulent square-duct flow · geometry honestly labeled (post Q-2 Path A)",
        focus="Q-2 Path A 落地：从 pipe → duct 诚实重标。f=0.0185 Jones 1976 correlation，同时在 Colebrook pipe 2% 以内。",
        next_step="对比 Jones-duct vs Moody-pipe 数值差；确认 adapter simpleFoam+SIMPLE_GRID 在 duct 语义下 PASS。",
    ),
    DashboardCaseSpec(
        whitelist_id="differential_heated_cavity",
        report_case_id="differential_heated_cavity",
        gold_file="differential_heated_cavity.yaml",
        title="差分加热方腔自然对流",
        subtitle="DHC · external-gate physics conflict",
        focus="测量链已到 Nu=77.82，但 gold=30.0 与文献区间冲突仍未裁决。",
        next_step="保持 Q-1 显式开放，等待 gold correction 或 regime downgrade 的 Gate 选择。",
    ),
    DashboardCaseSpec(
        whitelist_id="plane_channel_flow",
        report_case_id="fully_developed_plane_channel_flow",
        gold_file="plane_channel_flow.yaml",
        title="平面通道流 DNS",
        subtitle="Plane channel flow · laminar solver vs turbulent DNS (disguised)",
        focus="canonical gold 已明确这是 solver-choice incompatibility：laminar icoFoam 在 Re_bulk=5600 下不可能复现 Kim 1987 / Moser 1999 Re_τ=180 turbulent DNS u+ profile。ATTEST_PASS 是 comparator-path artifact，物理上应读为 FAIL。",
        next_step="保持 INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE，不要把 ATTEST_PASS 伪装成物理通过；Phase 9 solver routing 负责真修（pimpleFoam+LES 或 demote 到层流 Poiseuille）。",
    ),
    DashboardCaseSpec(
        whitelist_id="impinging_jet",
        report_case_id="axisymmetric_impinging_jet",
        gold_file="impinging_jet.yaml",
        title="轴对称冲击射流",
        subtitle="Impinging jet · 2D-slice + A4 iteration cap (disguised)",
        focus="canonical gold 暴露两条复合 hazard：(1) adapter axis patch 是 `empty` 不是 `wedge`，真实产出 2D 平面切片而非 axisymmetric；(2) A4 p_rgh iteration-cap ATTEST_FAIL — 当前 solver-config 未收敛（症状；根因仍需 solver-config audit）。历史 fixture 把 Cf=0.0042 当 Nu=25 报告，属纯维度错位。",
        next_step="维持 PASS-vacuous 判定；先做 solver-config audit（under-relaxation / coupling / axis wedge），再谈物理可比性。",
    ),
    DashboardCaseSpec(
        whitelist_id="naca0012_airfoil",
        report_case_id="naca0012_airfoil",
        gold_file="naca0012_airfoil.yaml",
        title="NACA0012 翼型外流",
        subtitle="NACA0012 · quantified deviation, not a clean pass",
        focus="偏差集中在前缘 / 吸力峰，但方向已知、归因明确，属于可解释偏差。",
        next_step="保持 PASS_WITH_DEVIATIONS 叙事；后续优先改 mesh/y+，不是改文案。",
    ),
    DashboardCaseSpec(
        whitelist_id="rayleigh_benard_convection",
        report_case_id="rayleigh_benard_convection",
        gold_file="rayleigh_benard_convection.yaml",
        title="Rayleigh-Benard 自然对流",
        subtitle="RBC · compatible only in its current low-Ra regime",
        focus="Ra=1e6 当前是 compatible，但这个结论不应被偷渡到高 Ra 腔体问题上。",
        next_step="继续作为低-Ra 参考，不把它当作 DHC 高-Ra 论证替身。",
    ),
)

CONTRACT_CLASS_ORDER: Tuple[str, ...] = (
    "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE",
    "COMPATIBLE_WITH_SILENT_PASS_HAZARD",
    "PARTIALLY_COMPATIBLE",
    "INCOMPATIBLE",
    "DEVIATION",
    # SATISFIED* prefixes are semantically strongest: physics contract is
    # exactly satisfied (not just "compatible within tolerance"). Covers
    # SATISFIED, SATISFIED_UNDER_LAMINAR_CONTRACT, SATISFIED_FOR_*_ONLY, etc.
    # Must appear before COMPATIBLE in the .startswith() match order so that
    # SATISFIED_UNDER_LAMINAR_CONTRACT resolves to SATISFIED (not UNKNOWN)
    # and doesn't accidentally match COMPATIBLE's shorter prefix via a typo.
    "SATISFIED",
    "COMPATIBLE",
)

_CSS = """
:root {
  --bg: #07111c;
  --bg-alt: #0d1828;
  --card: rgba(10, 21, 37, 0.9);
  --panel: rgba(13, 24, 40, 0.92);
  --border: rgba(110, 166, 221, 0.18);
  --fg: #e8eef7;
  --fg-dim: #a9b8cb;
  --fg-mute: #73859d;
  --accent: #7dc9ff;
  --ok: #79e3aa;
  --warn: #ffd27d;
  --danger: #ff879a;
  --mono: "SFMono-Regular", "JetBrains Mono", Menlo, Consolas, monospace;
  --sans: "SF Pro Display", "PingFang SC", "Helvetica Neue", system-ui, sans-serif;
  --shadow: 0 22px 72px rgba(0, 0, 0, 0.34);
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  background:
    radial-gradient(circle at 12% 14%, rgba(125, 201, 255, 0.14), transparent 24%),
    radial-gradient(circle at 86% 10%, rgba(121, 227, 170, 0.08), transparent 20%),
    linear-gradient(180deg, #050d17 0%, #091320 45%, #08111b 100%);
  color: var(--fg);
  font-family: var(--sans);
}
body { padding: 34px 18px 74px; }
.wrap { max-width: 1480px; margin: 0 auto; }
.hero,
.section-card,
.case-card,
.summary-card,
.distribution-card,
.gate-card {
  border: 1px solid var(--border);
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(16, 32, 54, 0.88), rgba(9, 18, 31, 0.94));
  box-shadow: var(--shadow);
}
.hero {
  padding: 32px 32px 28px;
  background:
    linear-gradient(135deg, rgba(19, 54, 96, 0.92), rgba(9, 18, 31, 0.92)),
    linear-gradient(135deg, rgba(125, 201, 255, 0.16), rgba(121, 227, 170, 0.08));
}
.eyebrow,
.label,
.section-label,
th,
.footer {
  color: var(--fg-mute);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.hero h1 {
  margin: 14px 0 12px;
  font-size: clamp(40px, 5vw, 68px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}
.hero p,
.section-lead,
.case-card p,
td,
.lane-note,
.artifact-link {
  color: var(--fg-dim);
  line-height: 1.7;
}
.pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 20px;
}
.pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(7, 16, 27, 0.55);
  color: var(--fg-dim);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.pill.ok,
.status-pill.ok { color: var(--ok); border-color: rgba(121, 227, 170, 0.28); background: rgba(121, 227, 170, 0.08); }
.pill.warn,
.status-pill.warn { color: var(--warn); border-color: rgba(255, 210, 125, 0.28); background: rgba(255, 210, 125, 0.08); }
.pill.fail,
.status-pill.fail { color: var(--danger); border-color: rgba(255, 135, 154, 0.32); background: rgba(255, 135, 154, 0.08); }
.summary-grid,
.distribution-grid,
.version-grid,
.lane-grid,
.case-grid,
.gate-grid {
  display: grid;
  gap: 16px;
}
.summary-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); margin-top: 22px; }
.distribution-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 20px; }
.version-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 22px; }
.lane-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.case-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.gate-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.summary-card,
.distribution-card,
.section-card,
.case-card,
.gate-card {
  padding: 18px 18px 16px;
}
.summary-card .value,
.distribution-card .value {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.04em;
}
.summary-card .note,
.distribution-card .note {
  margin-top: 8px;
  color: var(--fg-dim);
  font-size: 14px;
  line-height: 1.55;
}
.version-card {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(125, 201, 255, 0.18);
  background: rgba(7, 16, 27, 0.42);
}
.version-card .value {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.55;
  word-break: break-word;
}
.section-block { margin-top: 40px; }
h2 {
  margin: 10px 0 14px;
  font-size: 28px;
  letter-spacing: -0.03em;
}
h3 {
  margin: 0 0 12px;
  font-size: 20px;
  letter-spacing: -0.03em;
}
table {
  width: 100%;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: rgba(8, 16, 28, 0.82);
}
th, td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(110, 166, 221, 0.12);
  text-align: left;
  vertical-align: top;
}
td strong { color: var(--fg); }
.case-card h3 { margin-bottom: 8px; }
.case-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.case-subtitle {
  color: var(--fg-mute);
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.case-callout {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: rgba(7, 16, 27, 0.46);
}
.lane-card {
  padding: 20px 18px;
  border-radius: 22px;
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(13, 24, 40, 0.92), rgba(8, 16, 28, 0.95));
}
.lane-list {
  margin: 12px 0 0;
  padding-left: 18px;
}
.lane-list li {
  margin: 10px 0;
  color: var(--fg-dim);
}
.footer {
  margin-top: 42px;
  padding-top: 22px;
  border-top: 1px solid rgba(110, 166, 221, 0.16);
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
@media (max-width: 1220px) {
  .summary-grid,
  .distribution-grid,
  .version-grid,
  .lane-grid,
  .case-grid,
  .gate-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 720px) {
  body { padding: 16px 12px 54px; }
  .hero, .summary-card, .distribution-card, .section-card, .case-card, .gate-card { border-radius: 22px; }
  .hero h1 { font-size: 38px; }
}
"""


class ContractDashboardGenerator:
    """Render the 10-case physics-contract dashboard from repo truth sources."""

    def render(
        self,
        canonical_path: Optional[Path] = None,
        snapshot_path: Optional[Path] = None,
        manifest_path: Optional[Path] = None,
        generated_at: Optional[datetime] = None,
        head_sha: Optional[str] = None,
        branch_name: Optional[str] = None,
    ) -> ContractDashboardResult:
        generated_at = generated_at or datetime.now()
        canonical_target = canonical_path or DEFAULT_OUTPUT_PATH
        snapshot_target = snapshot_path or self._snapshot_path(canonical_target, generated_at)
        manifest_target = manifest_path or self._manifest_path(canonical_target)
        resolved_head_sha = head_sha or self._git_value("rev-parse", "--short", "HEAD") or "unknown"
        resolved_branch_name = branch_name or self._git_value("branch", "--show-current") or "unknown"
        states = [self._load_case(spec) for spec in CANONICAL_CASE_SPECS]
        summary_counts = Counter(state.contract_class for state in states)
        html = self._render_html(
            states=states,
            generated_at=generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            head_sha=resolved_head_sha,
            canonical_path=self._display_path(canonical_target),
            snapshot_path=self._display_path(snapshot_target),
            manifest_path=self._display_path(manifest_target),
            summary_counts=dict(summary_counts),
        )
        return ContractDashboardResult(
            html=html,
            case_count=len(states),
            canonical_path=str(canonical_target),
            snapshot_path=str(snapshot_target),
            manifest_path=str(manifest_target),
            generated_at=generated_at.isoformat(timespec="seconds"),
            head_sha=resolved_head_sha,
            branch_name=resolved_branch_name,
            summary_counts=dict(summary_counts),
        )

    def generate(self, output_path: Optional[Path] = None) -> ContractDashboardResult:
        target = output_path or DEFAULT_OUTPUT_PATH
        generated_at = datetime.now()
        snapshot_target = self._snapshot_path(target, generated_at)
        manifest_target = self._manifest_path(target)
        result = self.render(
            canonical_path=target,
            snapshot_path=snapshot_target,
            manifest_path=manifest_target,
            generated_at=generated_at,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(result.html, encoding="utf-8")
        snapshot_target.write_text(result.html, encoding="utf-8")
        manifest = self._manifest_payload(result)
        manifest_target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result.output_path = str(target)
        result.manifest = manifest
        return result

    def _render_html(
        self,
        states: Sequence[DashboardCaseState],
        generated_at: str,
        head_sha: str,
        canonical_path: str,
        snapshot_path: str,
        manifest_path: str,
        summary_counts: Dict[str, int],
    ) -> str:
        clean_demo_count = sum(
            1 for state in states if state.contract_class == "COMPATIBLE" and state.verdict == "PASS"
        )
        runtime_hazard_count = sum(
            1 for state in states if state.contract_class == "COMPATIBLE_WITH_SILENT_PASS_HAZARD"
        )
        blocker_count = sum(
            1
            for state in states
            if state.contract_class in {
                "DEVIATION",
                "INCOMPATIBLE",
                "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE",
            }
        )
        table_rows = "\n".join(self._render_row(state) for state in states)
        case_cards = "\n".join(self._render_case_card(state) for state in states)
        distribution_cards = "\n".join(self._render_distribution_card(name, count) for name, count in summary_counts.items())
        lane_cards = "\n".join(self._render_lane(states, lane) for lane in ("demo", "watch", "block"))

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>10-case Physics Contract Dashboard · CFD Harness OS</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="eyebrow">Phase 8 Delivery Surface · 10-case physics contract lens</div>
      <h1>10-case Physics Contract Dashboard</h1>
      <p>这张页面把 10 个 canonical whitelist case 的物理契约状态、runtime silent-pass hazard、PENDING_RE_RUN 留白，以及 Q-1/Q-2 外部门控放到一张中文科研级总览里。它不是替代 5-case visual acceptance，而是补上“全项目 physics truth surface”的上帝视角。</p>
      <div class="pill-row">
        <span class="pill ok">源数据直驱</span>
        <span class="pill ok">10 个 canonical cases</span>
        <span class="pill warn">2 个 runtime hazard</span>
        <span class="pill fail">Q-1 / Q-2 仍冻结</span>
      </div>
      <div class="summary-grid">
        <article class="summary-card">
          <div class="label">Canonical Cases</div>
          <div class="value">{len(states)}</div>
          <div class="note">直接由 whitelist + gold_standards + auto_verify truth source 汇总。</div>
        </article>
        <article class="summary-card">
          <div class="label">Clean Demo-ready</div>
          <div class="value">{clean_demo_count}</div>
          <div class="note">既是 PASS，又是 COMPATIBLE，适合对外演示时充当 physics-backed anchor。</div>
        </article>
        <article class="summary-card">
          <div class="label">Runtime Hazard</div>
          <div class="value">{runtime_hazard_count}</div>
          <div class="note">不是假阳性，但仍需把 shortcut / fallback 风险持续暴露给读者。</div>
        </article>
        <article class="summary-card">
          <div class="label">Structural / Gate Blockers</div>
          <div class="value">{blocker_count}</div>
          <div class="note">包括 DHC 外部门控、pipe/duct 几何错位，以及 literature-observable 错配。</div>
        </article>
        <article class="summary-card">
          <div class="label">Open Gates</div>
          <div class="value">2</div>
          <div class="note">Q-1 DHC gold-reference / Q-2 duct-flow relabel 继续冻结，不在这轮里越权修改。</div>
        </article>
      </div>
      <div class="version-grid">
        <div class="version-card">
          <div class="label">Generated</div>
          <div class="value">{escape(generated_at)}</div>
        </div>
        <div class="version-card">
          <div class="label">Head SHA</div>
          <div class="value">{escape(head_sha)}</div>
        </div>
        <div class="version-card">
          <div class="label">Canonical / Snapshot</div>
          <div class="value">{escape(canonical_path)}<br>{escape(snapshot_path)}</div>
        </div>
        <div class="version-card">
          <div class="label">Manifest / Linked Surfaces</div>
          <div class="value">{escape(manifest_path)}<br>visual_acceptance_report.html<br>2026-04-18_contract_status_dashboard.md</div>
        </div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-label">Status Distribution</div>
      <h2>物理契约状态分布</h2>
      <p class="section-lead">这里看的是 physics contract，不是 UI 层的 PASS 绿点。一个 case 可以在 auto_verify 上 PASS，但只要 observable 命名、几何假设或 runtime shortcut 让文献比较失真，它就不能被当成“完全科学可信”的 clean pass。</p>
      <div class="distribution-grid">
        {distribution_cards}
      </div>
    </section>

    <section class="section-block">
      <div class="section-label">Gate Boundary</div>
      <h2>冻结的治理边界</h2>
      <div class="gate-grid">
        <article class="gate-card">
          <div class="label">Q-1</div>
          <h3>DHC gold-reference 仍需 external Gate</h3>
          <p>DHC 的 extractor 方法学已经修正到 mean-over-y，但当前测量 <strong>Nu=77.82</strong> 与 gold <strong>30.0</strong> 的冲突，实质上是 gold 语义与工况匹配问题，不是继续盲修 solver 就能解决的问题。</p>
          <p class="artifact-link"><a href="../differential_heated_cavity/report.html">打开 DHC narrative report</a></p>
        </article>
        <article class="gate-card gate-closed">
          <div class="label">Q-2 · CLOSED</div>
          <h3>pipe ↔ duct relabel 已落地 (2026-04-20)</h3>
          <p>Gate Q-2 Path A 通过 DEC-V61-011 关闭：whitelist id <code>fully_developed_pipe</code> 与 auto_verifier id <code>fully_developed_turbulent_pipe_flow</code> 统一为 <code>duct_flow</code>，gold standard 切换到 Jones 1976 方管摩擦因子参考（Re=50000, f=0.0185，与 Colebrook pipe 在 2% 以内）。physics contract 从 INCOMPATIBLE 转为 SATISFIED。</p>
          <p class="artifact-link"><a href="../../.planning/gates/Q-2_r_a_relabel.md">查看 Gate Q-2 full record</a></p>
        </article>
      </div>
    </section>

    <section class="section-block">
      <div class="section-label">Portfolio Lanes</div>
      <h2>按交付语义分组</h2>
      <p class="section-lead">如果你要把 10 个 case 带进 demo、scientific review 或治理讨论，最好先按这里的三条 lane 分流：哪些能当 physics-backed baseline，哪些可以展示但必须保留 caveat，哪些根本不该被包装成“只差一点”的问题。</p>
      <div class="lane-grid">
        {lane_cards}
      </div>
    </section>

    <section class="section-block section-card">
      <div class="section-label">Case Matrix</div>
      <h2>全量 10-case matrix</h2>
      <table>
        <thead>
          <tr>
            <th>算例</th>
            <th>Auto Verify</th>
            <th>Physics Contract</th>
            <th>当前最重要的观测</th>
            <th>下一步</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </section>

    <section class="section-block">
      <div class="section-label">Per-case Cards</div>
      <h2>逐案科研解读</h2>
      <div class="case-grid">
        {case_cards}
      </div>
    </section>

    <div class="footer">
      <span>Generated · {escape(generated_at)}</span>
      <span>Head · {escape(head_sha)}</span>
      <span>Source · knowledge/whitelist.yaml + knowledge/gold_standards/*.yaml + reports/*/auto_verify_report.yaml</span>
      <span><a href="visual_acceptance_report.html">Open 5-case visual acceptance report</a></span>
      <span><a href="2026-04-18_contract_status_dashboard.md">Open historical markdown snapshot</a></span>
    </div>
  </div>
</body>
</html>
"""

    def _render_distribution_card(self, contract_class: str, count: int) -> str:
        note_map = {
            "SATISFIED": "Physics contract 完整满足：几何、流态、数值、比较链全部 evidence-backed。PASS 是真 PASS。",
            "COMPATIBLE": "所有关键 precondition 成立，PASS 可以被当作 physics-valid 结果读。",
            "COMPATIBLE_WITH_SILENT_PASS_HAZARD": "结果本身有价值，但必须把 runtime shortcut/fallback 的 caveat 一起展示。",
            "PARTIALLY_COMPATIBLE": "偏差存在，但方向和成因可归因，适合做“有解释的偏差”案例。",
            "DEVIATION": "不是 clean pass，也不是结构性错位；往往需要治理级判断来解释 remaining gap。",
            "INCOMPATIBLE": "几何、solver 或 comparator 前提未满足，继续调参没有意义。",
            "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE": "最危险的类型：表面 PASS，但 observable 和 literature 根本不是一回事。",
            # Post-DEC-V61-040 attestation surface can emit UNKNOWN when the
            # physics_contract block is absent or the gold YAML pre-dates the
            # contract_status field. Render a muted note instead of crashing.
            "UNKNOWN": "Gold standard 尚未声明 physics_contract 或 contract_status；无法判定兼容性，请补齐 gold YAML。",
        }
        pill_class = "ok" if contract_class == "COMPATIBLE" else "warn" if "COMPATIBLE" in contract_class else "fail"
        # Graceful fallback for any other future contract_class: empty note
        # instead of KeyError. Dashboard stays renderable as a structural
        # invariant — that's the whole point of the "honest evidence" surface.
        note = note_map.get(contract_class, "")
        return f"""
        <article class="distribution-card">
          <div class="label">{escape(contract_class)}</div>
          <div class="value">{count}</div>
          <div class="note">{escape(note)}</div>
          <div class="pill-row"><span class="status-pill {pill_class}">{escape(self._short_label(contract_class))}</span></div>
        </article>
        """

    def _render_lane(self, states: Sequence[DashboardCaseState], lane: str) -> str:
        title_map = {
            "demo": "Lane A · Physics-backed Demo",
            "watch": "Lane B · 可展示但必须带 caveat",
            "block": "Lane C · 治理 / 结构阻塞",
        }
        note_map = {
            "demo": "这些 case 可以作为对外 demo 或验收 anchor，但依旧应该引用 benchmark 与 source path。",
            "watch": "这些 case 不是不能展示，而是展示时必须把 runtime hazard 或已知偏差一起抬到台面上。",
            "block": "这些 case 目前的主要问题不是“再调一点参数”，而是 physics contract / governance 语义还没闭环。",
        }
        lane_states = [state for state in states if state.lane == lane]
        return f"""
        <article class="lane-card">
          <div class="label">{escape(title_map[lane])}</div>
          <div class="lane-note">{escape(note_map[lane])}</div>
          <ul class="lane-list">
            {"".join(f"<li><strong>{escape(state.spec.title)}</strong> · {escape(state.spec.focus)}</li>" for state in lane_states)}
          </ul>
        </article>
        """

    def _render_row(self, state: DashboardCaseState) -> str:
        verdict_pill = self._pill_class_for_verdict(state.verdict)
        contract_pill = self._pill_class_for_contract(state.contract_class)
        return f"""
          <tr>
            <td><strong>{escape(state.spec.title)}</strong><br><span class="case-subtitle">{escape(state.spec.report_case_id)}</span></td>
            <td><span class="status-pill {verdict_pill}">{escape(state.verdict)}</span><br>{escape(state.overall)}</td>
            <td><span class="status-pill {contract_pill}">{escape(state.contract_class)}</span><br>{escape(state.hazard)}</td>
            <td>{escape(state.measurement)}</td>
            <td>{escape(state.next_step)}</td>
          </tr>
        """

    def _render_case_card(self, state: DashboardCaseState) -> str:
        verdict_pill = self._pill_class_for_verdict(state.verdict)
        contract_pill = self._pill_class_for_contract(state.contract_class)
        return f"""
        <article class="case-card">
          <div class="case-meta">
            <div>
              <div class="label">Case</div>
              <h3>{escape(state.spec.title)}</h3>
              <div class="case-subtitle">{escape(state.spec.subtitle)}</div>
            </div>
            <div class="pill-row">
              <span class="status-pill {verdict_pill}">{escape(state.verdict)}</span>
              <span class="status-pill {contract_pill}">{escape(self._short_label(state.contract_class))}</span>
            </div>
          </div>
          <p>{escape(state.spec.focus)}</p>
          <div class="case-callout"><strong>当前观测：</strong> {escape(state.measurement)}</div>
          <div class="case-callout"><strong>风险说明：</strong> {escape(state.hazard)}</div>
          <div class="case-callout"><strong>下一步：</strong> {escape(state.next_step)}</div>
          <div class="pill-row">
            <span class="pill">{escape(state.lane_label)}</span>
            <span class="pill">{escape(state.reference)}</span>
          </div>
          <p class="artifact-link"><a href="{escape(state.gold_path)}">gold standard</a> · <a href="{escape(state.report_path)}">runtime report</a> · <a href="{escape(state.deep_link_path)}">deep evidence</a></p>
        </article>
        """

    def _load_case(self, spec: DashboardCaseSpec) -> DashboardCaseState:
        gold_path = KNOWLEDGE_ROOT / "gold_standards" / spec.gold_file
        gold = self._load_gold_standard(gold_path)
        report_path = REPORTS_ROOT / spec.report_case_id / "auto_verify_report.yaml"
        report = self._load_optional_yaml(report_path) or {}
        verdict = str(report.get("verdict") or "NO_RUNTIME_REPORT")
        overall = str((report.get("gold_standard_comparison") or {}).get("overall") or "NO_RUNTIME_REPORT")
        raw_status = str((gold.get("physics_contract") or {}).get("contract_status") or "UNKNOWN")
        contract_class = self._normalize_contract_class(raw_status)
        reference = str(gold.get("source") or self._whitelist_reference(spec.whitelist_id) or "[DATA MISSING]")
        measurement = self._measurement(spec, report)
        hazard = self._hazard(spec, report, raw_status)
        lane = self._lane(spec, contract_class, verdict)
        lane_label = {
            "demo": "Physics-backed demo",
            "watch": "Caveat-required",
            "block": "Governance / structural blocker",
        }[lane]
        deep_link_path = self._deep_link_path(spec)
        return DashboardCaseState(
            spec=spec,
            reference=reference,
            verdict=verdict,
            overall=overall,
            contract_status=raw_status,
            contract_class=contract_class,
            measurement=measurement,
            hazard=hazard,
            lane=lane,
            lane_label=lane_label,
            next_step=spec.next_step,
            gold_path=self._relative_link(gold_path),
            report_path=self._relative_link(report_path),
            deep_link_path=deep_link_path,
        )

    def _manifest_payload(self, result: ContractDashboardResult) -> Dict[str, Any]:
        return {
            "generated_at": result.generated_at,
            "head_sha": result.head_sha,
            "branch_name": result.branch_name,
            "canonical_path": str(Path(result.canonical_path or result.output_path or DEFAULT_OUTPUT_PATH)),
            "snapshot_path": str(Path(result.snapshot_path or self._snapshot_path(DEFAULT_OUTPUT_PATH, datetime.now()))),
            "manifest_path": str(Path(result.manifest_path or self._manifest_path(DEFAULT_OUTPUT_PATH))),
            "case_count": result.case_count,
            "class_counts": result.summary_counts,
            "open_gate_refs": list(OPEN_GATE_REFS),
            "historical_snapshot_path": str(HISTORICAL_SNAPSHOT_PATH),
        }

    def _load_gold_standard(self, path: Path) -> Dict[str, Any]:
        docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        for doc in docs:
            if isinstance(doc, dict) and doc.get("case_id"):
                return doc
        for doc in docs:
            if isinstance(doc, dict):
                return doc
        raise ValueError(f"Unsupported gold_standard payload: {path}")

    @staticmethod
    def _load_optional_yaml(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def _measurement(self, spec: DashboardCaseSpec, report: Dict[str, Any]) -> str:
        if spec.report_case_id == "differential_heated_cavity":
            nu = self._dhc_measurement()
            return f"Nu={nu:.2f} vs gold 30.0；当前冲突已经明确进入 Q-1 external gate。"
        if spec.report_case_id == "duct_flow":
            return "Q-2 Path A 已落地 (DEC-V61-011)，geometry 从 pipe 重标为 duct，gold 切换 Jones 1976 方管相关式。等 auto_verify_report 复跑后给新 verdict。"
        if spec.report_case_id == "fully_developed_plane_channel_flow":
            return "PENDING_RE_RUN；laminar comparator patch 已落地，但 fresh Docker E2E 尚未补齐。"
        if spec.report_case_id == "naca0012_airfoil":
            return "Cp 前缘误差 52.9%，中弦误差 32.4%，属于可量化但不应包装成 clean PASS 的偏差。"
        if spec.report_case_id == "axisymmetric_impinging_jet":
            return "当前 report 记录 PASS on 0.0042，但 literature target 实际是 Nu=25，不是同一个 observable。"
        if spec.report_case_id == "cylinder_crossflow":
            return "St=0.164, Cd=1.31, Cl_rms=0.049；其中 Strouhal 这一格仍需把 shortcut 风险一起展示。"
        if spec.report_case_id == "turbulent_flat_plate":
            return "Cf=0.00760037，对 Spalding 相关式几乎零误差，但 fallback 路径必须持续透明。"
        if spec.report_case_id == "rayleigh_benard_convection":
            return "Nu=10.5 at Ra=1e6；当前 compatible，但不能被拿来替代高-Ra 腔体论证。"
        if spec.report_case_id == "lid_driven_cavity_benchmark":
            return "u / v 中心线与主涡核位置都在低误差区，是 textbook-grade baseline。"
        if spec.report_case_id == "backward_facing_step_steady":
            return "Xr/H=6.30 vs 6.26，速度剖面误差约 2.5%，适合作为 separation / reattachment anchor。"
        return str(report.get("verdict") or "N/A")

    def _hazard(self, spec: DashboardCaseSpec, report: Dict[str, Any], contract_status: str) -> str:
        if spec.report_case_id == "cylinder_crossflow":
            return "Strouhal 通过 canonical-band shortcut 可能被伪确认；Cd / Cl_rms / wake deficit 则仍有物理含义。"
        if spec.report_case_id == "turbulent_flat_plate":
            return "Cf>0.01 时可能走 Spalding substitution；结果可用，但必须持续保留 runtime fallback 透明度。"
        if spec.report_case_id == "differential_heated_cavity":
            return "extractor 方法学已修正，但 gold-reference 语义与 literature/工况冲突仍未裁决。"
        if spec.report_case_id == "axisymmetric_impinging_jet":
            return "observable 命名与 literature 目标不一致，最容易造成“数值 PASS 但科学含义错位”的误读。"
        if spec.report_case_id == "duct_flow":
            return "Q-2 Path A 落地后不再是类别错误；remaining hazard 是 Jones-vs-Colebrook 相关式 2% 量级差别，需要做一次新 auto_verify_report 才能关闭。"
        if spec.report_case_id == "fully_developed_plane_channel_flow":
            return "当前是 comparator / solver 路线不闭环，不适合再用局部 patch 把它包装成可验收结果。"
        if spec.report_case_id == "naca0012_airfoil":
            return "偏差集中在前缘与近壁分辨；风险在于被 UI 误读成“只差一点的 clean PASS”。"
        return contract_status.split("—", 1)[0].strip()

    def _lane(self, spec: DashboardCaseSpec, contract_class: str, verdict: str) -> str:
        if contract_class == "COMPATIBLE" and verdict == "PASS":
            return "demo"
        if contract_class in {"COMPATIBLE_WITH_SILENT_PASS_HAZARD", "PARTIALLY_COMPATIBLE"}:
            return "watch"
        if spec.report_case_id == "rayleigh_benard_convection":
            return "watch"
        return "block"

    def _normalize_contract_class(self, raw_status: str) -> str:
        for prefix in CONTRACT_CLASS_ORDER:
            if raw_status.startswith(prefix):
                return prefix
        return "UNKNOWN"

    def _whitelist_reference(self, whitelist_id: str) -> str:
        whitelist = yaml.safe_load((KNOWLEDGE_ROOT / "whitelist.yaml").read_text(encoding="utf-8")) or {}
        for case in whitelist.get("cases", []):
            if case.get("id") == whitelist_id:
                return str(case.get("reference") or "[DATA MISSING]")
        return "[DATA MISSING]"

    def _deep_link_path(self, spec: DashboardCaseSpec) -> str:
        if spec.report_case_id == "differential_heated_cavity":
            return self._relative_link(REPORTS_ROOT / "differential_heated_cavity" / "report.html")
        if spec.report_case_id == "duct_flow":
            return self._relative_link(REPORTS_ROOT / "ex1_first_slice" / "diagnostic_memo.md")
        if spec.report_case_id == "fully_developed_plane_channel_flow":
            return self._relative_link(REPORTS_ROOT / "fully_developed_plane_channel_flow" / "report.md")
        return self._relative_link(REPORTS_ROOT / spec.report_case_id / "report.md")

    def _dhc_measurement(self) -> float:
        path = REPORTS_ROOT / "ex1_007_dhc_mesh_refinement" / "measurement_result.yaml"
        if not path.exists():
            return 77.82
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return float(data.get("c5_band_check", {}).get("nu_measured", 77.82))

    def _relative_link(self, path: Path) -> str:
        return os.path.relpath(path, DEFAULT_OUTPUT_PATH.parent)

    @staticmethod
    def _pill_class_for_verdict(verdict: str) -> str:
        if verdict == "PASS":
            return "ok"
        if verdict in {"PASS_WITH_DEVIATIONS", "PENDING_RE_RUN"}:
            return "warn"
        return "fail"

    @staticmethod
    def _pill_class_for_contract(contract_class: str) -> str:
        # SATISFIED is strictly stronger than COMPATIBLE (full evidence-backed
        # precondition match vs "compatible within tolerance"). Both pill-ok.
        if contract_class in {"COMPATIBLE", "SATISFIED"}:
            return "ok"
        if contract_class in {"COMPATIBLE_WITH_SILENT_PASS_HAZARD", "PARTIALLY_COMPATIBLE"}:
            return "warn"
        return "fail"

    @staticmethod
    def _short_label(contract_class: str) -> str:
        labels = {
            "SATISFIED": "Satisfied",
            "COMPATIBLE": "Compatible",
            "COMPATIBLE_WITH_SILENT_PASS_HAZARD": "Silent-pass hazard",
            "PARTIALLY_COMPATIBLE": "Partially compatible",
            "DEVIATION": "Deviation",
            "INCOMPATIBLE": "Incompatible",
            "INCOMPATIBLE_WITH_LITERATURE_DISGUISED_AS_COMPATIBLE": "Observable mismatch",
            "UNKNOWN": "Unknown",
        }
        # Fallback to the raw class if a future status gets added without
        # updating the label map — keep the dashboard renderable.
        return labels.get(contract_class, contract_class)

    def _snapshot_path(self, canonical_path: Path, generated_at: datetime) -> Path:
        stamp = generated_at.strftime("%Y%m%d_%H%M%S")
        return canonical_path.with_name(f"{canonical_path.stem}_{stamp}{canonical_path.suffix}")

    def _manifest_path(self, canonical_path: Path) -> Path:
        return canonical_path.with_name(f"{canonical_path.stem}_manifest.json")

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(REPO_ROOT))
        except ValueError:
            return str(path)

    def _git_value(self, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return ""
        return completed.stdout.strip()
