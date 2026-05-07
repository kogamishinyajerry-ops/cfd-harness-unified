"""Live partial-run script: 3 DeepSeek personas only.

Per user authorization 2026-05-07: run the 3 DeepSeek-V4-Pro cells
from the charter table against the real workbench (localhost:8000).
Other 6 cells (Anthropic + gpt-5.4) deferred until those API keys
are staged.

Steps:
  1. Verify workbench /api/health
  2. Pre-stage 3 cases (multipart STL upload → workbench case_id)
  3. Build a per-cell CaseBrief replica with workbench case_id
  4. Run persona × case live with DeepSeekClient
  5. Write friction logs + results under
     .planning/dogfood/runs/live_2026_05_07/
"""
from __future__ import annotations

import dataclasses
import json
import logging
import sys
import time
import uuid
from pathlib import Path

import httpx

from scripts.dogfood.case_brief import CaseBrief
from scripts.dogfood.cases import brief_path, stl_path
from scripts.dogfood.friction_log import FrictionLog
from scripts.dogfood.llm_clients import DeepSeekClient
from scripts.dogfood.personas import get_assignment, get_persona
from scripts.dogfood.persona_runner import PersonaConfig, run_persona
from scripts.dogfood.workbench_tools import WorkbenchToolExecutor

logger = logging.getLogger(__name__)

WB_BASE = "http://localhost:8000"
RUNS_ROOT = Path(".planning/dogfood/runs/live_2026_05_07_r9")

DEEPSEEK_CELLS = [
    ("naca0012", "experienced_fluent"),
    ("backward_step", "novice"),
    ("pipe_expansion", "debug"),
]


def _verify_workbench() -> None:
    resp = httpx.get(f"{WB_BASE}/api/health", timeout=5.0)
    resp.raise_for_status()
    payload = resp.json()
    logger.info("workbench health: %s", payload)


def _stage_case(charter_case_id: str) -> str:
    """Upload STL via multipart; return workbench-assigned case_id."""
    stl_file = stl_path(charter_case_id)
    if not stl_file.exists():
        raise FileNotFoundError(f"STL fixture missing: {stl_file}")
    with stl_file.open("rb") as fh:
        files = {"file": (stl_file.name, fh, "model/stl")}
        resp = httpx.post(
            f"{WB_BASE}/api/import/stl",
            files=files,
            timeout=60.0,
        )
    if resp.status_code >= 400:
        logger.error("stage_case %s failed: %s %s",
                     charter_case_id, resp.status_code, resp.text[:500])
        raise RuntimeError(
            f"stage_case {charter_case_id} returned {resp.status_code}"
        )
    data = resp.json()
    wb_case_id = data["case_id"]
    logger.info(
        "staged %s → workbench case_id=%s",
        charter_case_id, wb_case_id,
    )
    return wb_case_id


def _build_case_brief(charter_case_id: str, wb_case_id: str) -> CaseBrief:
    """Load the charter brief and rewrite case_id to the workbench-assigned id."""
    raw = json.loads(brief_path(charter_case_id).read_text(encoding="utf-8"))
    from scripts.dogfood.case_brief import Reference

    ref_raw = raw["reference"]
    reference = Reference(
        metric=str(ref_raw["metric"]),
        value=float(ref_raw["value"]),
        tolerance=float(ref_raw["tolerance"]),
        tolerance_kind=ref_raw.get("tolerance_kind", "rel"),
        source=str(ref_raw.get("source", "")),
    )
    notes_aug = (
        f"{raw.get('notes', '')}\n\n"
        f"## Workbench-assigned case_id\n"
        f"This case has been imported into the workbench. Use case_id "
        f"`{wb_case_id}` in all your /api/cases/{{case_id}}/... calls. "
        f"The workbench import scaffolds the case skeleton — your job "
        f"is to drive the remaining workflow steps (mesh → physics → "
        f"BC → solver) and answer the question."
    ).strip()
    return CaseBrief(
        case_id=wb_case_id,
        title=str(raw["title"]),
        geometry=str(raw["geometry"]),
        physics=dict(raw.get("physics", {}) or {}),
        question=str(raw["question"]),
        reference=reference,
        notes=notes_aug,
    )


def _run_one(charter_case_id: str, persona: str) -> dict:
    assignment = get_assignment(charter_case_id, persona)
    assert assignment.family == "deepseek", (
        f"live_partial_run is DeepSeek-only; got family={assignment.family}"
    )
    persona_obj = get_persona(persona)
    wb_case_id = _stage_case(charter_case_id)
    brief = _build_case_brief(charter_case_id, wb_case_id)

    cell_id = f"{charter_case_id}__{persona}__deepseek"
    run_id = f"{cell_id}__{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "friction_log.jsonl"

    config = PersonaConfig(
        persona_name=persona,
        family="deepseek",
        model_id=assignment.model_id,
        system_prompt=persona_obj.system_prompt,
        max_steps=120,  # R9: +40 over R5/R8 — backward_step R8 hit /solve at step ~70, ran out of headroom for Step 6 verdict flow
        max_input_tokens=4_000_000,  # R9: +1M to absorb extended Step 6 budget
        max_output_tokens=2048,
        prune_keep_full=3,  # tighter than default 6 — keep per-turn input small
        prune_min_turns_before_active=4,
    )

    client = DeepSeekClient(model_id=assignment.model_id)
    executor = WorkbenchToolExecutor(base_url=WB_BASE)

    started = time.monotonic()
    error: str | None = None
    try:
        with FrictionLog(
            path=log_path,
            run_id=run_id,
            case_id=brief.case_id,
            persona=persona,
            model_id=assignment.model_id,
        ) as flog:
            flog.emit(
                "decision",
                step=0,
                detail=(
                    f"live partial run · charter_case={charter_case_id} · "
                    f"workbench_case_id={wb_case_id} · model={assignment.model_id}"
                ),
            )
            result = run_persona(
                config=config,
                brief=brief,
                client=client,
                log=flog,
                executor=executor,
            )
    except Exception as exc:
        error = f"persona_run_error: {exc!s}"
        logger.exception("persona run failed")
        result = None  # type: ignore[assignment]
    finally:
        executor.close()
        client.close()

    elapsed = time.monotonic() - started
    spec = {
        "charter_case_id": charter_case_id,
        "workbench_case_id": wb_case_id,
        "persona": persona,
        "family": "deepseek",
        "model_id": assignment.model_id,
        "run_id": run_id,
        "dry_run": False,
        "stl_path": str(stl_path(charter_case_id)),
        "elapsed_s": elapsed,
        "error": error,
    }
    (run_dir / "spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if result is not None:
        (run_dir / "result.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        verdict_str = "PASS" if (result.verdict and result.verdict.passed) else (
            "FAIL" if result.verdict else "—"
        )
        drop_str = "yes" if result.dropped else "—"
        steps = result.steps
        in_tokens = result.total_input_tokens
        out_tokens = result.total_output_tokens
    else:
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "case_id": brief.case_id,
                    "persona": persona,
                    "model_id": assignment.model_id,
                    "verdict": None,
                    "dropped": True,
                    "drop_reason": error,
                    "error": error,
                    "steps": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        verdict_str = "ERROR"
        drop_str = "yes"
        steps = 0
        in_tokens = out_tokens = 0
    print(
        f"  {charter_case_id:>16s} / {persona:<20s} → {verdict_str:<6s} "
        f"drop={drop_str:<3s} steps={steps:>2} tokens=in:{in_tokens}/out:{out_tokens} "
        f"elapsed={elapsed:.1f}s"
    )
    return spec


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)

    print(f"Live partial run · 3 DeepSeek cells · {WB_BASE}")
    print(f"Output: {RUNS_ROOT}")
    print("=" * 60)

    try:
        _verify_workbench()
    except Exception as exc:
        print(f"workbench health check failed: {exc}", file=sys.stderr)
        return 2

    summary: list[dict] = []
    for case_id, persona in DEEPSEEK_CELLS:
        try:
            spec = _run_one(case_id, persona)
            summary.append(spec)
        except Exception as exc:
            logger.exception("cell %s/%s failed", case_id, persona)
            summary.append(
                {
                    "charter_case_id": case_id,
                    "persona": persona,
                    "error": str(exc),
                }
            )

    print("=" * 60)
    (RUNS_ROOT / "LIVE_PARTIAL_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
