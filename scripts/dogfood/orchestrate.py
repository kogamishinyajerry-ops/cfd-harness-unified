"""B-arc dogfood orchestrator (DEC-V61-166).

Wires B.1 harness + B.2 personas + B.3 cases into an executable arc.

Modes:
    --dry-run --all     : run all 9 cells with scripted mock LLM
                           against mock workbench transport; produces
                           real artifacts under .planning/dogfood/
    --serial            : 3 checkered cells (one per case, persona,
                           model — diagonal of the 3×3 table) to
                           validate harness orchestration
    --batch             : remaining 6 cells, 3 concurrent
    --all               : full 9-cell arc (serial then batch)
    --live              : real LLM + real workbench (requires
                           ANTHROPIC_API_KEY + DEEPSEEK_API_KEY +
                           CODEX_RELAY_API_KEY env vars + workbench
                           dev server up at localhost:8000)

Live mode is gated on user authorization; --dry-run is the default.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from scripts.dogfood.case_brief import CaseBrief, load_brief
from scripts.dogfood.cases import (
    CASE_IDS,
    brief_path,
    stl_path,
)
from scripts.dogfood.friction_log import FrictionLog
from scripts.dogfood.harness import _ScriptedMockClient
from scripts.dogfood.llm_clients import LLMClient, build_client
from scripts.dogfood.persona_runner import PersonaConfig, RunResult, run_persona
from scripts.dogfood.personas import (
    PERSONA_NAMES,
    get_assignment,
    get_persona,
)
from scripts.dogfood.scripted_runs import get_script
from scripts.dogfood.workbench_tools import WorkbenchToolExecutor

logger = logging.getLogger(__name__)

DEFAULT_RUNS_ROOT = Path(".planning/dogfood/runs")


# ---------------------------------------------------------------------------
# Cell mapping (charter §rationale 3×3 table; checkered diagonal first)
# ---------------------------------------------------------------------------


_SERIAL_DIAGONAL: tuple[tuple[str, str], ...] = (
    # Charter 3×3 has a "checkered" property — pick one cell per case +
    # one per persona + one per model family
    ("naca0012", "novice"),  # anthropic / Sonnet
    ("backward_step", "experienced_fluent"),  # openai_compat / gpt-5.4
    ("pipe_expansion", "debug"),  # deepseek
)


def _all_cells() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for case_id in CASE_IDS:
        for persona in PERSONA_NAMES:
            out.append((case_id, persona))
    return out


def _batch_cells() -> list[tuple[str, str]]:
    serial_set = set(_SERIAL_DIAGONAL)
    return [c for c in _all_cells() if c not in serial_set]


# ---------------------------------------------------------------------------
# Mock workbench transport for dry-run
# ---------------------------------------------------------------------------


def _build_mock_workbench_transport() -> httpx.MockTransport:
    """Returns canned responses simulating workbench routes the personas hit.

    Real workbench responses would carry real case state; for dry-run we
    just need 200 OK with plausibly-shaped JSON.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/state"):
            return httpx.Response(
                200,
                json={
                    "case_id": path.split("/")[-2],
                    "step": "geometry",
                    "completeness": 0.0,
                    "llm_available": True,
                },
            )
        if path.endswith("/ai-review"):
            return httpx.Response(
                200,
                json={
                    "case_id": path.split("/")[-2],
                    "findings": [
                        {
                            "id": "f1",
                            "severity": "info",
                            "area": "mesh_quality",
                            "source": "rule_based",
                            "message": "(dry-run mock) mesh appears nominal",
                            "citation": {
                                "chunk_id": "mesh_quality_checkmesh.md:0:abcd1234",
                                "path": "mesh_quality_checkmesh.md",
                                "section_anchor": "checkMesh",
                                "sha16": "abcd1234",
                            },
                        }
                    ],
                    "corpus_sha": "dryrun_corpus_sha",
                    "llm_available": True,
                    "degradation_note": None,
                    "generated_at": "2026-05-07T13:00:00Z",
                },
            )
        if "/ai-diagnose" in path:
            return httpx.Response(
                200,
                json={
                    "case_id": path.split("/")[-2],
                    "hypotheses": [
                        {
                            "id": "h1",
                            "likelihood": "medium",
                            "failure_mode": "stalled_residuals",
                            "source": "rule_based",
                            "summary": "(dry-run mock) residuals appear stable",
                            "evidence": {"residual_trend": "stable"},
                            "citation": {
                                "chunk_id": "residual_diagnostics.md:0:efgh5678",
                                "path": "residual_diagnostics.md",
                                "section_anchor": "interpretation",
                                "sha16": "efgh5678",
                            },
                            "suggested_fix": "(dry-run mock) no action recommended",
                        }
                    ],
                    "corpus_sha": "dryrun_corpus_sha",
                    "problem_hint": None,
                    "llm_available": True,
                    "degradation_note": None,
                    "generated_at": "2026-05-07T13:00:00Z",
                },
            )
        return httpx.Response(404, json={"error": f"not found: {path}"})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# RunSpec + execution
# ---------------------------------------------------------------------------


@dataclass
class RunSpec:
    case_id: str
    persona: str
    family: str
    model_id: str
    run_id: str
    run_dir: Path
    brief: CaseBrief
    dry_run: bool


@dataclass
class CellOutcome:
    spec: RunSpec
    result: RunResult
    elapsed_s: float
    error: str | None = None


def _load_run_spec(case_id: str, persona: str, *, dry_run: bool, runs_root: Path) -> RunSpec:
    assignment = get_assignment(case_id, persona)
    brief = load_brief(brief_path(case_id))
    cell_id = f"{case_id}__{persona}__{assignment.family}"
    run_id = f"{cell_id}__{uuid.uuid4().hex[:8]}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return RunSpec(
        case_id=case_id,
        persona=persona,
        family=assignment.family,
        model_id=assignment.model_id,
        run_id=run_id,
        run_dir=run_dir,
        brief=brief,
        dry_run=dry_run,
    )


def _build_client_for(spec: RunSpec) -> LLMClient:
    if spec.dry_run:
        return _ScriptedMockClient(
            model_id=f"dryrun-{spec.model_id}",
            scripted=get_script(spec.case_id, spec.persona),
        )
    return build_client(spec.family, spec.model_id)


def _build_executor_for(spec: RunSpec, *, workbench_base_url: str) -> WorkbenchToolExecutor:
    if spec.dry_run:
        client = httpx.Client(
            transport=_build_mock_workbench_transport(),
            base_url="http://localhost:8000",
        )
        return WorkbenchToolExecutor(client=client)
    return WorkbenchToolExecutor(base_url=workbench_base_url)


def execute_cell(
    case_id: str,
    persona: str,
    *,
    dry_run: bool = True,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    workbench_base_url: str = "http://localhost:8000",
    max_steps: int = 30,
) -> CellOutcome:
    """Run one (case, persona) cell end-to-end."""
    spec = _load_run_spec(case_id, persona, dry_run=dry_run, runs_root=runs_root)
    persona_obj = get_persona(persona)
    config = PersonaConfig(
        persona_name=persona,
        family=spec.family,
        model_id=spec.model_id,
        system_prompt=persona_obj.system_prompt,
        max_steps=max_steps,
    )
    log_path = spec.run_dir / "friction_log.jsonl"

    client = _build_client_for(spec)
    executor = _build_executor_for(spec, workbench_base_url=workbench_base_url)

    started = time.monotonic()
    error: str | None = None
    try:
        with FrictionLog(
            path=log_path,
            run_id=spec.run_id,
            case_id=spec.case_id,
            persona=spec.persona,
            model_id=spec.model_id,
        ) as log:
            log.emit(
                "decision",
                step=0,
                detail=f"orchestrator dispatch · dry_run={spec.dry_run} · model={spec.model_id}",
            )
            result = run_persona(
                config=config,
                brief=spec.brief,
                client=client,
                log=log,
                executor=executor,
            )
    except Exception as exc:  # pragma: no cover - defensive
        error = f"orchestrator_failure: {exc!s}"
        result = RunResult(
            run_id=spec.run_id,
            case_id=spec.case_id,
            persona=spec.persona,
            model_id=spec.model_id,
            steps=0,
            verdict=None,
            dropped=True,
            drop_reason=error,
            total_input_tokens=0,
            total_output_tokens=0,
            error=error,
        )
    finally:
        executor.close()
        if hasattr(client, "close"):
            try:
                client.close()  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                pass

    elapsed = time.monotonic() - started
    (spec.run_dir / "result.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (spec.run_dir / "spec.json").write_text(
        json.dumps(
            {
                "case_id": spec.case_id,
                "persona": spec.persona,
                "family": spec.family,
                "model_id": spec.model_id,
                "run_id": spec.run_id,
                "dry_run": spec.dry_run,
                "stl_path": str(stl_path(spec.case_id)),
                "elapsed_s": elapsed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return CellOutcome(spec=spec, result=result, elapsed_s=elapsed, error=error)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class OrchestrationReport:
    runs_root: Path
    outcomes: list[CellOutcome] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "runs_root": str(self.runs_root),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "n_outcomes": len(self.outcomes),
            "n_passed": sum(
                1 for o in self.outcomes if o.result.verdict and o.result.verdict.passed
            ),
            "n_dropped": sum(1 for o in self.outcomes if o.result.dropped),
            "n_errors": sum(1 for o in self.outcomes if o.error or o.result.error),
        }


def orchestrate_serial(
    cells: list[tuple[str, str]],
    *,
    dry_run: bool,
    runs_root: Path,
    workbench_base_url: str,
    max_steps: int = 30,
) -> OrchestrationReport:
    report = OrchestrationReport(runs_root=runs_root)
    for case_id, persona in cells:
        outcome = execute_cell(
            case_id,
            persona,
            dry_run=dry_run,
            runs_root=runs_root,
            workbench_base_url=workbench_base_url,
            max_steps=max_steps,
        )
        report.outcomes.append(outcome)
        logger.info(
            "cell complete: %s/%s passed=%s dropped=%s elapsed=%.2fs",
            case_id,
            persona,
            outcome.result.verdict.passed if outcome.result.verdict else None,
            outcome.result.dropped,
            outcome.elapsed_s,
        )
    report.finished_at = time.time()
    return report


def orchestrate_batch(
    cells: list[tuple[str, str]],
    *,
    concurrency: int,
    dry_run: bool,
    runs_root: Path,
    workbench_base_url: str,
    max_steps: int = 30,
) -> OrchestrationReport:
    report = OrchestrationReport(runs_root=runs_root)
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(
                execute_cell,
                case_id,
                persona,
                dry_run=dry_run,
                runs_root=runs_root,
                workbench_base_url=workbench_base_url,
                max_steps=max_steps,
            )
            for case_id, persona in cells
        ]
        for fut in concurrent.futures.as_completed(futures):
            outcome = fut.result()
            report.outcomes.append(outcome)
    report.finished_at = time.time()
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )


def _resolve_cells(args: argparse.Namespace) -> list[tuple[str, str]]:
    if args.all:
        return _all_cells()
    if args.serial:
        return list(_SERIAL_DIAGONAL)
    if args.batch:
        return _batch_cells()
    return list(_SERIAL_DIAGONAL)


def _summarize(report: OrchestrationReport) -> str:
    lines = ["", "=" * 60, "Orchestration summary", "=" * 60]
    s = report.summary()
    lines.append(f"runs_root: {s['runs_root']}")
    lines.append(f"cells: {s['n_outcomes']}, passed: {s['n_passed']}, "
                 f"dropped: {s['n_dropped']}, errors: {s['n_errors']}")
    lines.append("")
    for o in report.outcomes:
        verdict = "—"
        if o.result.verdict:
            verdict = "pass" if o.result.verdict.passed else f"fail({o.result.verdict.observed})"
        marker = "drop" if o.result.dropped else verdict
        lines.append(
            f"  {o.spec.case_id:>16s} / {o.spec.persona:<20s} "
            f"({o.spec.family:<14s}) → {marker:<14s} "
            f"steps={o.result.steps:>2} elapsed={o.elapsed_s:.2f}s"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B-arc dogfood orchestrator")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="all 9 cells")
    mode.add_argument("--serial", action="store_true", help="3 diagonal cells (default)")
    mode.add_argument("--batch", action="store_true", help="remaining 6 cells, 3 concurrent")

    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="default; uses scripted mock LLM + mock workbench")
    parser.add_argument("--live", dest="dry_run", action="store_false",
                        help="real LLM + real workbench (requires API keys)")

    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--runs-root", type=str, default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--workbench-base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    cells = _resolve_cells(args)
    runs_root = Path(args.runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    logger.info(
        "orchestrating %d cells · dry_run=%s · runs_root=%s",
        len(cells),
        args.dry_run,
        runs_root,
    )

    if args.serial or (not args.all and not args.batch):
        report = orchestrate_serial(
            cells,
            dry_run=args.dry_run,
            runs_root=runs_root,
            workbench_base_url=args.workbench_base_url,
            max_steps=args.max_steps,
        )
    elif args.batch:
        report = orchestrate_batch(
            cells,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            runs_root=runs_root,
            workbench_base_url=args.workbench_base_url,
            max_steps=args.max_steps,
        )
    elif args.all:
        # serial diagonal first to validate harness, then concurrent batch
        serial_cells = list(_SERIAL_DIAGONAL)
        serial_report = orchestrate_serial(
            serial_cells,
            dry_run=args.dry_run,
            runs_root=runs_root,
            workbench_base_url=args.workbench_base_url,
            max_steps=args.max_steps,
        )
        batch_report = orchestrate_batch(
            _batch_cells(),
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            runs_root=runs_root,
            workbench_base_url=args.workbench_base_url,
            max_steps=args.max_steps,
        )
        report = OrchestrationReport(
            runs_root=runs_root,
            outcomes=serial_report.outcomes + batch_report.outcomes,
            started_at=serial_report.started_at,
            finished_at=batch_report.finished_at,
        )
    else:  # pragma: no cover
        report = orchestrate_serial(
            cells,
            dry_run=args.dry_run,
            runs_root=runs_root,
            workbench_base_url=args.workbench_base_url,
            max_steps=args.max_steps,
        )

    print(_summarize(report))
    (runs_root.parent / "ORCHESTRATION_SUMMARY.json").write_text(
        json.dumps(report.summary(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = report.summary()
    return 0 if summary["n_errors"] == 0 else 1


__all__ = [
    "CellOutcome",
    "OrchestrationReport",
    "RunSpec",
    "execute_cell",
    "main",
    "orchestrate_batch",
    "orchestrate_serial",
]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
