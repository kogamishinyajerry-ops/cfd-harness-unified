"""Friction log aggregator → DOGFOOD_REPORT.md.

Reads all `friction_log.jsonl` files under a runs root, classifies
events by severity (critical / warning / info), and produces a
structured markdown report with a backlog table.

Severity rules (from DEC-V61-166 §severity-classification):

- **critical** — V130 violation patterns in rationale text · workbench
  5xx · max_steps_reached · transport errors · drop reason
  "no_tool_call"
- **warning** — verdict failed (off-tolerance) · >10 advisor queries
  per run · token budget exceeded · explicit drop · truncated
  workbench responses
- **info** — clean run (verdict passed, ≤10 advisor queries, no errors)
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.dogfood.friction_log import grep_events, read_log

# Patterns that indicate a V130 violation in persona rationale text
_V130_VIOLATION_PATTERNS = (
    re.compile(r"\bAI told me\b", re.IGNORECASE),
    re.compile(r"\badvisor said so\b", re.IGNORECASE),
    re.compile(r"\bauto[- ]apply\b", re.IGNORECASE),
    re.compile(r"\bbecause the AI\b", re.IGNORECASE),
    re.compile(r"\bbecause the advisor\b", re.IGNORECASE),
)


@dataclass
class BacklogItem:
    severity: str  # "critical" | "warning" | "info"
    category: str
    run_id: str
    case_id: str
    persona: str
    detail: str
    evidence: str = ""  # JSON-stringified pointer to friction_log line(s)


@dataclass
class RunSummary:
    run_id: str
    case_id: str
    persona: str
    model_id: str
    n_steps: int
    n_advisor_queries: int
    n_tool_uses: int
    verdict_passed: bool | None
    dropped: bool
    drop_reason: str | None
    error: str | None
    elapsed_s: float | None
    backlog: list[BacklogItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-run analysis
# ---------------------------------------------------------------------------


def _scan_v130_violations(events: list[dict[str, Any]]) -> list[BacklogItem]:
    out: list[BacklogItem] = []
    for ev in events:
        rationale = str(ev.get("rationale", "")) if ev.get("rationale") else ""
        if not rationale:
            continue
        for pat in _V130_VIOLATION_PATTERNS:
            if pat.search(rationale):
                out.append(
                    BacklogItem(
                        severity="critical",
                        category="v130_violation",
                        run_id=str(ev.get("run_id", "")),
                        case_id="",
                        persona="",
                        detail=f"persona rationale matched V130 violation pattern {pat.pattern!r}",
                        evidence=json.dumps(
                            {
                                "ts": ev.get("ts"),
                                "event_type": ev.get("event_type"),
                                "rationale": rationale[:200],
                                "url": ev.get("url"),
                                "tool_name": ev.get("tool_name"),
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
                break
    return out


def _classify_run(events: list[dict[str, Any]], result_dict: dict[str, Any], spec_dict: dict[str, Any]) -> RunSummary:
    run_id = str(result_dict.get("run_id") or spec_dict.get("run_id") or "")
    case_id = str(result_dict.get("case_id") or spec_dict.get("case_id") or "")
    persona = str(result_dict.get("persona") or spec_dict.get("persona") or "")
    model_id = str(result_dict.get("model_id") or spec_dict.get("model_id") or "")

    api_calls = grep_events(events, "api_call")
    advisor_calls = [
        c for c in api_calls
        if "/ai-review" in str(c.get("url", "")) or "/ai-diagnose" in str(c.get("url", ""))
    ]
    tool_uses = grep_events(events, "tool_use")
    errors = grep_events(events, "error")
    budget_checks = grep_events(events, "budget_check")
    truncated = [c for c in api_calls if c.get("truncated_at_bytes")]
    server_5xx = [
        c for c in api_calls
        if isinstance(c.get("status"), int) and 500 <= int(c["status"]) < 600
    ]

    verdict = result_dict.get("verdict")
    verdict_passed = bool(verdict.get("passed")) if isinstance(verdict, dict) else None
    dropped = bool(result_dict.get("dropped", False))
    drop_reason = result_dict.get("drop_reason")
    error = result_dict.get("error")
    elapsed_s = spec_dict.get("elapsed_s")

    backlog: list[BacklogItem] = []

    # critical
    backlog.extend(_scan_v130_violations(events))
    for e in errors:
        backlog.append(
            BacklogItem(
                severity="critical",
                category="run_error",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"error event: phase={e.get('phase')} detail={e.get('detail')}",
                evidence=json.dumps(e, ensure_ascii=False),
            )
        )
    for s in server_5xx:
        backlog.append(
            BacklogItem(
                severity="critical",
                category="workbench_5xx",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"workbench 5xx on {s.get('url')}",
                evidence=json.dumps(s, ensure_ascii=False),
            )
        )
    if drop_reason == "no_tool_call":
        backlog.append(
            BacklogItem(
                severity="critical",
                category="dropped_no_tool_call",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail="persona returned text with no tool_call; treated as drop",
                evidence=json.dumps({"drop_reason": drop_reason}, ensure_ascii=False),
            )
        )
    if error == "max_steps_reached":
        backlog.append(
            BacklogItem(
                severity="critical",
                category="max_steps_reached",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"persona did not converge within max_steps; n_steps={result_dict.get('steps')}",
                evidence=json.dumps({"error": error}, ensure_ascii=False),
            )
        )

    # warning
    if verdict_passed is False:
        backlog.append(
            BacklogItem(
                severity="warning",
                category="verdict_failed",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=(
                    f"observed={verdict.get('observed')} outside reference="
                    f"{verdict.get('reference')} ± {verdict.get('tolerance')}"
                ),
                evidence=json.dumps(verdict, ensure_ascii=False) if isinstance(verdict, dict) else "",
            )
        )
    if len(advisor_calls) > 10:
        backlog.append(
            BacklogItem(
                severity="warning",
                category="advisor_overuse",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"persona called advisor {len(advisor_calls)} times (>10)",
            )
        )
    for b in budget_checks:
        if b.get("exceeded"):
            backlog.append(
                BacklogItem(
                    severity="warning",
                    category="budget_exceeded",
                    run_id=run_id,
                    case_id=case_id,
                    persona=persona,
                    detail=f"budget_check phase={b.get('phase')} exceeded",
                    evidence=json.dumps(b, ensure_ascii=False),
                )
            )
    if dropped and drop_reason and drop_reason != "no_tool_call":
        backlog.append(
            BacklogItem(
                severity="warning",
                category="explicit_drop",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"persona explicitly dropped: {drop_reason!r}",
            )
        )
    if truncated:
        backlog.append(
            BacklogItem(
                severity="warning",
                category="response_truncated",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=f"{len(truncated)} workbench responses exceeded bytes-cap and were truncated",
            )
        )

    # info — only if zero higher-severity items
    has_critical = any(i.severity == "critical" for i in backlog)
    has_warning = any(i.severity == "warning" for i in backlog)
    if not has_critical and not has_warning and verdict_passed is True:
        backlog.append(
            BacklogItem(
                severity="info",
                category="clean_run",
                run_id=run_id,
                case_id=case_id,
                persona=persona,
                detail=(
                    f"verdict passed; {len(advisor_calls)} advisor queries, "
                    f"{len(tool_uses)} tool uses, {result_dict.get('steps')} steps"
                ),
            )
        )

    return RunSummary(
        run_id=run_id,
        case_id=case_id,
        persona=persona,
        model_id=model_id,
        n_steps=int(result_dict.get("steps") or 0),
        n_advisor_queries=len(advisor_calls),
        n_tool_uses=len(tool_uses),
        verdict_passed=verdict_passed,
        dropped=dropped,
        drop_reason=drop_reason,
        error=error,
        elapsed_s=elapsed_s if isinstance(elapsed_s, (int, float)) else None,
        backlog=backlog,
    )


def aggregate(runs_root: Path) -> list[RunSummary]:
    """Discover and classify every run under `runs_root`."""
    summaries: list[RunSummary] = []
    if not runs_root.exists():
        return summaries
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        log_path = run_dir / "friction_log.jsonl"
        result_path = run_dir / "result.json"
        spec_path = run_dir / "spec.json"
        if not log_path.exists() or not result_path.exists():
            continue
        events = read_log(log_path)
        result_dict = json.loads(result_path.read_text(encoding="utf-8"))
        spec_dict = (
            json.loads(spec_path.read_text(encoding="utf-8"))
            if spec_path.exists() else {}
        )
        summaries.append(_classify_run(events, result_dict, spec_dict))
    return summaries


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _format_summary_table(summaries: list[RunSummary]) -> str:
    lines = [
        "| Case | Persona | Model | Verdict | Drop | Steps | Advisor calls | Tool uses | Elapsed |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        if s.verdict_passed is True:
            v = "PASS"
        elif s.verdict_passed is False:
            v = "FAIL"
        else:
            v = "—"
        elapsed = f"{s.elapsed_s:.2f}s" if s.elapsed_s is not None else "—"
        lines.append(
            f"| `{s.case_id}` | `{s.persona}` | `{s.model_id}` | {v} | "
            f"{('yes' if s.dropped else '—')} | {s.n_steps} | "
            f"{s.n_advisor_queries} | {s.n_tool_uses} | {elapsed} |"
        )
    return "\n".join(lines)


def _format_backlog_section(summaries: list[RunSummary], severity: str) -> str:
    items: list[BacklogItem] = []
    for s in summaries:
        items.extend(i for i in s.backlog if i.severity == severity)
    if not items:
        return f"_No {severity} items._\n"
    lines = ["| # | Run | Case | Persona | Category | Detail |", "|---|---|---|---|---|---|"]
    for i, it in enumerate(items, start=1):
        detail = it.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {i} | `{it.run_id[:24]}…` | `{it.case_id}` | `{it.persona}` | "
            f"`{it.category}` | {detail} |"
        )
    return "\n".join(lines) + "\n"


def render_report(
    summaries: list[RunSummary],
    *,
    title: str = "DOGFOOD REPORT",
    dry_run: bool = False,
) -> str:
    n_total = len(summaries)
    n_passed = sum(1 for s in summaries if s.verdict_passed is True)
    n_failed = sum(1 for s in summaries if s.verdict_passed is False)
    n_dropped = sum(1 for s in summaries if s.dropped)
    n_critical = sum(
        sum(1 for i in s.backlog if i.severity == "critical")
        for s in summaries
    )
    n_warning = sum(
        sum(1 for i in s.backlog if i.severity == "warning")
        for s in summaries
    )
    n_info = sum(
        sum(1 for i in s.backlog if i.severity == "info")
        for s in summaries
    )

    out: list[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    out.append(f"**Mode**: {'DRY RUN (scripted mock LLM + mock workbench)' if dry_run else 'LIVE'}")
    out.append("")
    out.append("## Run roster")
    out.append("")
    out.append(_format_summary_table(summaries))
    out.append("")
    out.append("## Aggregate counts")
    out.append("")
    out.append(f"- runs: **{n_total}**")
    out.append(f"- verdict pass: **{n_passed}**")
    out.append(f"- verdict fail: **{n_failed}**")
    out.append(f"- dropped: **{n_dropped}**")
    out.append(f"- critical findings: **{n_critical}**")
    out.append(f"- warning findings: **{n_warning}**")
    out.append(f"- info entries: **{n_info}**")
    out.append("")
    out.append("## Critical backlog")
    out.append("")
    out.append(_format_backlog_section(summaries, "critical"))
    out.append("")
    out.append("## Warning backlog")
    out.append("")
    out.append(_format_backlog_section(summaries, "warning"))
    out.append("")
    out.append("## Info entries (clean runs)")
    out.append("")
    out.append(_format_backlog_section(summaries, "info"))
    out.append("")
    if dry_run:
        out.append("## Dry-run caveat")
        out.append("")
        out.append(
            "This report is generated from SCRIPTED mock-LLM responses against a "
            "MOCK workbench transport. Backlog items reflect the script + "
            "deterministic verdict comparison; they do NOT capture real "
            "engineer-LLM friction. A live run (with `ANTHROPIC_API_KEY`, "
            "`DEEPSEEK_API_KEY`, `CODEX_RELAY_API_KEY` set and the workbench "
            "dev server up at `localhost:8000`) is required to surface real "
            "advisor signal-to-noise findings, mesh-import failures, "
            "convergence behavior, and persona-vs-workbench UX gaps."
        )
        out.append("")
    out.append("## References")
    out.append("")
    out.append("- DEC-V61-162 · B-arc charter")
    out.append("- DEC-V61-163 · B.1 harness")
    out.append("- DEC-V61-164 · B.2 personas")
    out.append("- DEC-V61-165 · B.3 case pool")
    out.append("- DEC-V61-166 · B.4 orchestration + this aggregator")
    return "\n".join(out)


__all__ = [
    "BacklogItem",
    "RunSummary",
    "aggregate",
    "render_report",
]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Dogfood friction log aggregator")
    parser.add_argument("--runs-root", type=str, default=".planning/dogfood/runs")
    parser.add_argument("--out", type=str, default=".planning/dogfood/DOGFOOD_REPORT.md")
    parser.add_argument("--title", type=str, default="DOGFOOD REPORT")
    parser.add_argument("--dry-run-mode", action="store_true",
                        help="mark report as dry-run derived")
    args = parser.parse_args(argv)
    summaries = aggregate(Path(args.runs_root))
    text = render_report(summaries, title=args.title, dry_run=args.dry_run_mode)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Wrote {out_path} ({len(summaries)} runs analyzed)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
