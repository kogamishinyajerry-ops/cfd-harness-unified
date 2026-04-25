"""Preflight service · Stage 4 GuardedRun MVP.

Aggregates ≥5 categories of preflight checks per case, surfaced as
the JSON payload powering the `<RunRail>` UI primitive. Categories:

  1. physics       — physics_precondition rows from gold YAML
  2. schema        — workbench_basics YAML present + patch_id consistency
  3. mesh          — mesh sweep fixtures present, Richardson computable
  4. gold_standard — gold YAML has ref_value + tolerance + citation
  5. adapter       — case_id is in the canonical whitelist (has generator)

Reuses existing services (gold loader, grid_convergence, workbench_basics
schema) so this module is a thin aggregator rather than re-implementing
data access.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ui.backend.schemas.preflight import (
    PreflightCheck,
    PreflightCounts,
    PreflightSummary,
)
from ui.backend.schemas.workbench_basics import validate_patch_consistency
from ui.backend.services.grid_convergence import (
    compute_gci_from_fixtures,
    load_mesh_solutions_from_fixtures,
)
from ui.backend.services.validation_report import _load_gold_standard

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WHITELIST_PATH = _REPO_ROOT / "knowledge" / "whitelist.yaml"
_BASICS_DIR = _REPO_ROOT / "knowledge" / "workbench_basics"


def _load_whitelist_ids() -> set[str]:
    if not _WHITELIST_PATH.is_file():
        return set()
    try:
        doc = yaml.safe_load(_WHITELIST_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return set()
    cases = (doc or {}).get("cases") or []
    return {c.get("id") for c in cases if isinstance(c, dict) and c.get("id")}


def _normalize_satisfied(value: Any) -> str:
    """Map physics_precondition.satisfied_by_current_adapter to status."""
    if isinstance(value, bool):
        return "pass" if value else "fail"
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1"):
            return "pass"
        if low in ("false", "no", "0"):
            return "fail"
        if low == "partial":
            return "partial"
    return "fail"


def _physics_checks(gs: dict[str, Any] | None) -> list[PreflightCheck]:
    if not gs:
        return [
            PreflightCheck(
                category="physics",
                id="physics_no_gold",
                label_zh="物理前置（无金标准）",
                label_en="Physics preconditions (no gold YAML)",
                status="skip",
                evidence="knowledge/gold_standards/<case_id>.yaml 缺失",
            )
        ]
    rows = ((gs.get("physics_contract") or {}).get("physics_precondition") or [])
    if not rows:
        return [
            PreflightCheck(
                category="physics",
                id="physics_no_rows",
                label_zh="物理前置（contract 未声明）",
                label_en="Physics preconditions (none declared)",
                status="skip",
                evidence="physics_contract.physics_precondition 为空",
            )
        ]
    out: list[PreflightCheck] = []
    for i, row in enumerate(rows):
        out.append(
            PreflightCheck(
                category="physics",
                id=f"physics_{i}",
                label_zh=row.get("condition", "")[:80],
                status=_normalize_satisfied(row.get("satisfied_by_current_adapter")),
                evidence=row.get("evidence_ref"),
                consequence=row.get("consequence_if_unsatisfied"),
            )
        )
    return out


def _schema_check(case_id: str) -> PreflightCheck:
    yaml_path = _BASICS_DIR / f"{case_id}.yaml"
    if not yaml_path.is_file():
        return PreflightCheck(
            category="schema",
            id="schema_basics_present",
            label_zh="工作台首屏数据已编排",
            label_en="workbench_basics YAML present",
            status="fail",
            evidence=f"缺失 knowledge/workbench_basics/{case_id}.yaml",
            consequence="CaseFrame 首屏渲染会回退到旧 hero illustration",
        )
    try:
        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return PreflightCheck(
            category="schema",
            id="schema_basics_present",
            label_zh="工作台首屏数据已编排",
            status="fail",
            evidence=f"YAML 解析错误：{e}",
            consequence="endpoint 返回 500",
        )
    drift = (
        validate_patch_consistency(payload) if isinstance(payload, dict) else None
    )
    if drift:
        return PreflightCheck(
            category="schema",
            id="schema_basics_present",
            label_zh="BC patch 引用与 patches[] 一致",
            label_en="BC per_patch keys consistent with patches[].id",
            status="partial",
            evidence=drift,
            consequence="CaseFrame 顶部会出现 amber drift 提示，但仍渲染",
        )
    return PreflightCheck(
        category="schema",
        id="schema_basics_present",
        label_zh="工作台首屏数据 + patch 引用一致",
        label_en="workbench_basics authored + patches[] ↔ BC consistent",
        status="pass",
        evidence=f"knowledge/workbench_basics/{case_id}.yaml",
    )


def _mesh_checks(case_id: str) -> list[PreflightCheck]:
    sols = load_mesh_solutions_from_fixtures(case_id)
    out: list[PreflightCheck] = []
    if len(sols) >= 4:
        levels_status = "pass"
        evid = f"4 fixture: {', '.join(s.label for s in sols)}"
    elif len(sols) >= 3:
        levels_status = "partial"
        evid = f"仅 {len(sols)} 个 fixture，Richardson 可算但 sweep 不完整"
    elif len(sols) >= 1:
        levels_status = "fail"
        evid = f"仅 {len(sols)} 个 fixture，无法计算 Richardson"
    else:
        levels_status = "fail"
        evid = "无任何 mesh_*_measurement.yaml fixture"
    out.append(
        PreflightCheck(
            category="mesh",
            id="mesh_fixtures",
            label_zh=f"网格 sweep fixture 完整 ({len(sols)}/4)",
            label_en=f"Mesh sweep fixtures ({len(sols)}/4)",
            status=levels_status,
            evidence=evid,
            consequence=("Stage 3 GCI 不可计算" if levels_status == "fail" else None),
        )
    )

    if len(sols) >= 3:
        gci = compute_gci_from_fixtures(case_id)
        if gci is None:
            out.append(
                PreflightCheck(
                    category="mesh",
                    id="mesh_gci_computable",
                    label_zh="Richardson/GCI 可计算",
                    status="fail",
                    evidence="compute_gci_from_fixtures 返回 None",
                )
            )
        elif gci.p_obs is None:
            out.append(
                PreflightCheck(
                    category="mesh",
                    id="mesh_gci_computable",
                    label_zh="Richardson/GCI 可计算",
                    status="partial",
                    evidence=f"oscillating convergence — {gci.note}",
                    consequence="MeshQC 验证条退化为 gray",
                )
            )
        else:
            out.append(
                PreflightCheck(
                    category="mesh",
                    id="mesh_gci_computable",
                    label_zh="Richardson/GCI 可计算",
                    status="pass",
                    evidence=f"p_obs={gci.p_obs:.2f}, GCI₃₂={(gci.gci_32 or 0)*100:.2f}%",
                )
            )
    return out


def _gold_check(gs: dict[str, Any] | None) -> PreflightCheck:
    if not gs:
        return PreflightCheck(
            category="gold_standard",
            id="gold_present",
            label_zh="金标准 YAML 存在",
            status="fail",
            evidence="knowledge/gold_standards/<case_id>.yaml 缺失",
            consequence="comparator 无对照基准",
        )
    obs = gs.get("observables") or []
    has_ref = any(
        isinstance(o, dict) and o.get("ref_value") is not None
        for o in obs
    )
    has_tol = any(
        isinstance(o, dict)
        and isinstance(o.get("tolerance"), dict)
        and o["tolerance"].get("value") is not None
        for o in obs
    )
    citation_keys = ("source", "literature_doi", "reference")
    has_citation = bool(gs.get("source") or gs.get("literature_doi"))
    has_citation = has_citation or any(
        isinstance(o, dict) and any(k in o for k in citation_keys)
        for o in obs
    )

    parts: list[str] = []
    if has_ref:
        parts.append("ref_value ✓")
    else:
        parts.append("ref_value ✗")
    if has_tol:
        parts.append("tolerance ✓")
    else:
        parts.append("tolerance ✗")
    if has_citation:
        parts.append("citation ✓")
    else:
        parts.append("citation ✗")

    if has_ref and has_tol and has_citation:
        status = "pass"
        consequence = None
    elif has_ref:
        status = "partial"
        consequence = "comparator 可跑但缺少容差或引文，审计可疑"
    else:
        status = "fail"
        consequence = "comparator 无对照基准"

    return PreflightCheck(
        category="gold_standard",
        id="gold_completeness",
        label_zh="金标准三件套（ref_value / tolerance / citation）",
        status=status,
        evidence=" · ".join(parts),
        consequence=consequence,
    )


def _adapter_check(case_id: str, whitelist_ids: set[str]) -> PreflightCheck:
    if case_id in whitelist_ids:
        return PreflightCheck(
            category="adapter",
            id="adapter_whitelisted",
            label_zh="案例在 canonical whitelist",
            label_en="case_id in knowledge/whitelist.yaml",
            status="pass",
            evidence=f"knowledge/whitelist.yaml cases[].id 命中 {case_id!r}",
        )
    return PreflightCheck(
        category="adapter",
        id="adapter_whitelisted",
        label_zh="案例未在 canonical whitelist",
        status="fail",
        evidence=f"{case_id!r} 不在 knowledge/whitelist.yaml",
        consequence="无对应生成器；FoamAgentExecutor 无法 spec 出 case",
    )


def _aggregate_overall(checks: list[PreflightCheck]) -> str:
    if not checks:
        return "skip"
    if any(c.status == "fail" for c in checks):
        return "fail"
    if any(c.status == "partial" for c in checks):
        return "partial"
    if all(c.status == "skip" for c in checks):
        return "skip"
    return "pass"


def build_preflight(case_id: str) -> PreflightSummary:
    """Run all preflight categories for a case, return composite summary."""
    gs = _load_gold_standard(case_id)
    whitelist_ids = _load_whitelist_ids()

    checks: list[PreflightCheck] = []
    checks.append(_adapter_check(case_id, whitelist_ids))
    checks.append(_gold_check(gs))
    checks.extend(_physics_checks(gs))
    checks.append(_schema_check(case_id))
    checks.extend(_mesh_checks(case_id))

    counts = PreflightCounts()
    for c in checks:
        if c.status == "pass":
            counts.pass_ += 1
        elif c.status == "fail":
            counts.fail += 1
        elif c.status == "partial":
            counts.partial += 1
        elif c.status == "skip":
            counts.skip += 1
    counts.total = len(checks)

    n_categories = len({c.category for c in checks})

    return PreflightSummary(
        case_id=case_id,
        checks=checks,
        counts=counts,
        n_categories=n_categories,
        overall=_aggregate_overall(checks),
    )
