"""B-ext-5.4 (DEC-V61-194) Step 6 isolation rehearsal driver.

Goal: isolate the verdict-formation chain (read-only routes +
submit_verdict) from the upstream Step 1-5 mechanics. Pre-stage a
backward_step case in a converged-or-not-converged state via a
fast curl path (~30s wall-time), then drive a persona with a
Step-6-specialized system prompt that explicitly forbids re-running
mesh/setup-bc/solve.

If the persona reaches submit_verdict (pass or fail outcome both
acceptable) within the budget, the verdict-formation chain WORKS in
isolation and the gap in B-ext-2/3/4 verdict pass = 0/3 was elsewhere
(persona budget exhaustion mid-Step-1-5, mesh-cycle pathology, /solve
502, DeepSeek timeout). If the persona burns its Step-6-only budget
without submitting a verdict, the prompt itself or the read-only
tools are the bottleneck.

Usage:
    .venv/bin/python -m scripts.dogfood.step6_rehearsal

Writes outputs to .planning/dogfood/runs/step6_rehearsal_<ts>/.
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

from scripts.dogfood.case_brief import CaseBrief, Reference
from scripts.dogfood.friction_log import FrictionLog
from scripts.dogfood.llm_clients import DeepSeekClient
from scripts.dogfood.persona_runner import PersonaConfig, run_persona
from scripts.dogfood.workbench_tools import WorkbenchToolExecutor

logger = logging.getLogger(__name__)

WB_BASE = "http://localhost:8000"
GEOMETRY_DIR = Path("scripts/dogfood/cases/geometry")

# Step 6 specialized prompt — replaces the full novice/experienced/debug
# prompt for this rehearsal. Frames the case as "already done; just
# fetch + verdict" so the persona doesn't waste budget on Steps 1-5.
STEP6_SYSTEM_PROMPT = """\
You are a CFD engineer at **Step 6** of a case workflow. Steps 1-5
(import → mesh → physics → BC → solve) are ALREADY DONE — the
workbench has staged the case, generated a mesh, authored boundary
conditions, and run the OpenFOAM solver. Your sole job is to:

1. Fetch the results via read-only routes
2. Compute the metric the case brief asks for
3. Call **submit_verdict** with your observed_value + rationale, OR
   call **submit_drop** if the result genuinely does not allow you to
   answer the brief's question

You have at most 30 steps total. Step 6 should be quick — most cases
need 5-15 calls to /results-summary, /run-history, and at most one
/results/{run_id}/field/{name} fetch.

## Read-only routes (use these only)

- `GET /api/cases/{case_id}/run-history` — returns
  `runs: [{run_id, started_at, duration_s, success, verdict_summary,
  ...}]`. Use the LATEST run's run_id for the field fetch below.
- `GET /api/cases/{case_id}/results-summary` — flow field stats:
  `cell_count`, `u_magnitude_{min,max,mean}`, `u_x_{min,mean,max}`,
  `is_recirculating`, `final_time`.
- `GET /api/cases/{case_id}/residual-history` — residual time series
  for the latest run. Use this to confirm convergence quality.
- `GET /api/cases/{case_id}/results/{run_id}/field/U` — raw cell-by-cell
  U vectors as bytes. ONLY fetch if the brief's metric needs it (e.g.
  reattachment length, centerline profile). Most metrics that
  results-summary covers do NOT need this.

## Hard prohibitions

- **DO NOT call POST /mesh, POST /setup-bc, or POST /solve.** The
  workflow is done. Re-running these is wasted budget and may break
  case state.
- **DO NOT modify case files via PUT/POST routes.** No
  /face-annotations, /patch-classification, /dicts mutations.
- **DO NOT call /openapi.json.** The four routes above are all you
  need.

## Reading results-summary

Even if the brief asks for a metric not directly in results-summary
(e.g. backward-step reattachment length L/h, NACA0012 lift coefficient),
the summary's `u_x_min`, `u_x_max`, `u_magnitude_max`, `cell_count`,
`is_recirculating` flags are diagnostic. If these numbers look
inconsistent with the brief's expected physics (e.g. `final_time=2.0`
when the brief asks for steady-state convergence at t→∞, or
`u_magnitude_max ≈ 1.0` on a case where inlet_speed should be 0.0758),
your verdict can legitimately report `passed=false` with an
observed_value that reflects whatever you can compute — and the
rationale should explain the inconsistency.

## Verdict shape

`submit_verdict(observed_value=<float>, rationale="<text>")` —
observed_value is a numeric scalar in the brief's reference units.
The runner separately compares it against `reference.value` ±
`reference.tolerance` to determine the actual pass/fail; you do not
set `passed` directly.

`submit_drop(reason="<text>")` — call this only if you genuinely
cannot extract any usable observation from the converged case (e.g.
field is entirely NaN; results-summary returns 422). A drop is
acceptable when the upstream workflow produced unusable data.

## Voice

You are a competent engineer triaging an already-completed run. Be
terse. State what the numbers show, compute the metric, submit the
verdict. No re-discovery, no exploration of other routes.
"""


def _prestage_converged_case(charter_case_id: str) -> str:
    """Drive Steps 1-5 via direct curl-equivalent calls. Returns the
    workbench case_id ready for Step 6."""
    stl_file = GEOMETRY_DIR / f"{charter_case_id}.stl"
    if not stl_file.exists():
        raise FileNotFoundError(f"STL fixture missing: {stl_file}")

    with httpx.Client(timeout=120.0) as wb:
        # Step 1: import STL
        with stl_file.open("rb") as fh:
            resp = wb.post(
                f"{WB_BASE}/api/import/stl",
                files={"file": (stl_file.name, fh, "model/stl")},
            )
        resp.raise_for_status()
        case_id = resp.json()["case_id"]
        logger.info("prestage staged %s → %s", charter_case_id, case_id)

        # Step 2: mesh
        resp = wb.post(
            f"{WB_BASE}/api/import/{case_id}/mesh",
            json={},
        )
        resp.raise_for_status()
        cells = resp.json()["mesh_summary"]["cell_count"]
        logger.info("prestage meshed %s (%d cells)", case_id, cells)

        # Step 3+4: setup-bc with LDC defaults (from_stl_patches=0).
        # This produces a "ran_but_not_converged" case rather than a
        # physically-correct backward-step run, but the rehearsal
        # tests verdict-formation mechanics, not physics correctness.
        # The persona's verdict will (correctly) report a non-passing
        # observed_value with rationale explaining the inconsistency.
        resp = wb.post(f"{WB_BASE}/api/import/{case_id}/setup-bc")
        resp.raise_for_status()
        logger.info("prestage setup-bc applied (LDC defaults)")

        # Step 5: solve
        resp = wb.post(f"{WB_BASE}/api/import/{case_id}/solve")
        if resp.status_code != 200:
            raise RuntimeError(
                f"prestage /solve failed: {resp.status_code} {resp.text[:300]}"
            )
        summary = resp.json()
        logger.info(
            "prestage /solve %s → run_id=%s converged=%s",
            case_id, summary.get("run_id"), summary.get("converged"),
        )

    return case_id


def _build_step6_brief(charter_case_id: str, wb_case_id: str) -> CaseBrief:
    """Same brief as the regular live run, but with Step 6 framing in
    the notes section so the persona doesn't try to drive Steps 1-5."""
    raw = json.loads(
        (Path("scripts/dogfood/cases/briefs") / f"{charter_case_id}.json")
        .read_text(encoding="utf-8")
    )
    ref_raw = raw["reference"]
    reference = Reference(
        metric=str(ref_raw["metric"]),
        value=float(ref_raw["value"]),
        tolerance=float(ref_raw["tolerance"]),
        tolerance_kind=ref_raw.get("tolerance_kind", "rel"),
        source=str(ref_raw.get("source", "")),
    )
    notes = (
        f"{raw.get('notes', '')}\n\n"
        f"## Step 6 framing — case is already converged\n"
        f"Workbench case_id `{wb_case_id}` has been pre-staged. Mesh "
        f"is done; setup-bc has been applied; /solve has run to "
        f"completion. Your task is Step 6 only: fetch results and "
        f"submit a verdict. The system prompt's hard prohibitions "
        f"apply — DO NOT re-run mesh / setup-bc / solve."
    ).strip()
    return CaseBrief(
        case_id=wb_case_id,
        title=str(raw["title"]),
        geometry=str(raw["geometry"]),
        physics=dict(raw.get("physics", {}) or {}),
        question=str(raw["question"]),
        reference=reference,
        notes=notes,
    )


def _build_synthetic_uxmin_brief(wb_case_id: str) -> CaseBrief:
    """Variant B: synthetic brief asking for u_x_min — directly
    available in /results-summary. Proves the submit_verdict (pass)
    path works in addition to submit_drop. Tolerance is generous (50%)
    because the absolute scale of LDC-on-backward-step is irrelevant —
    we want any valid scalar back from the persona."""
    return CaseBrief(
        case_id=wb_case_id,
        title="Synthetic Step 6 rehearsal · u_x_min from results-summary",
        geometry="(rehearsal — geometry irrelevant)",
        physics={"regime": "rehearsal_only"},
        question=(
            "What is the minimum streamwise velocity u_x_min in the "
            "domain, as reported by the workbench /results-summary "
            "route? Report u_x_min directly."
        ),
        reference=Reference(
            metric="u_x_min",
            value=-0.0711501,
            tolerance=0.5,
            tolerance_kind="rel",
            source="(rehearsal · pre-measured from prestage on identical case)",
        ),
        notes=(
            f"## Step 6 rehearsal — Variant B (submit_verdict pass path)\n"
            f"Workbench case_id `{wb_case_id}`. Case has run; results "
            f"are in /results-summary. The metric is the literal "
            f"`u_x_min` field from that response — no field-level "
            f"computation needed. Submit_verdict with observed_value "
            f"set to whatever /results-summary returns for u_x_min."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    run_dir = Path(f".planning/dogfood/runs/step6_rehearsal_{ts}")
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Step 6 rehearsal · output: {run_dir}")
    print("=" * 60)

    # 1. Prestage
    charter_case = "backward_step"
    persona = "novice"
    print("Prestaging converged case via Steps 1-5 ...")
    started = time.monotonic()
    try:
        wb_case_id = _prestage_converged_case(charter_case)
    except Exception as exc:
        print(f"prestage failed: {exc}", file=sys.stderr)
        return 2
    prestage_s = time.monotonic() - started
    print(f"  → wb_case_id={wb_case_id}  ({prestage_s:.1f}s)")

    # 2. Pick variant — A: real brief (likely submit_drop, F15 blocks
    # field fetch); B: synthetic u_x_min brief (submit_verdict path).
    variant = (argv or sys.argv[1:])
    variant = variant[0] if variant else "A"
    if variant not in ("A", "B"):
        print(f"unknown variant: {variant!r}; expected A or B", file=sys.stderr)
        return 2
    if variant == "A":
        brief = _build_step6_brief(charter_case, wb_case_id)
        print("Variant A — real backward_step brief (L/h reattachment)")
    else:
        brief = _build_synthetic_uxmin_brief(wb_case_id)
        print("Variant B — synthetic u_x_min brief (submit_verdict path)")

    # 3. Configure persona — Step 6 specialized prompt, small budget
    cell_id = f"{charter_case}__{persona}__step6_{variant}"
    run_id = f"{cell_id}__{uuid.uuid4().hex[:8]}"
    log_path = run_dir / "friction_log.jsonl"

    config = PersonaConfig(
        persona_name=persona,
        family="deepseek",
        model_id="deepseek-chat",
        system_prompt=STEP6_SYSTEM_PROMPT,
        max_steps=30,  # Step 6 should be quick
        max_input_tokens=400_000,  # tight; force succinct flow
        max_output_tokens=2048,
        prune_keep_full=3,
        prune_min_turns_before_active=4,
    )

    client = DeepSeekClient(model_id="deepseek-chat")
    executor = WorkbenchToolExecutor(base_url=WB_BASE)

    # 4. Drive persona
    print(f"Running persona {persona}/deepseek-chat (max_steps=30) ...")
    started = time.monotonic()
    error = None
    result = None
    try:
        with FrictionLog(
            path=log_path,
            run_id=run_id,
            case_id=brief.case_id,
            persona=persona,
            model_id="deepseek-chat",
        ) as flog:
            flog.emit(
                "decision",
                step=0,
                detail=(
                    f"step6 rehearsal · charter_case={charter_case} · "
                    f"wb_case_id={wb_case_id}"
                ),
            )
            result = run_persona(
                config=config, brief=brief, client=client,
                log=flog, executor=executor,
            )
    except Exception as exc:
        error = f"persona_run_error: {exc!s}"
        logger.exception("persona run failed")
    finally:
        executor.close()
        client.close()

    elapsed = time.monotonic() - started

    # 5. Write outputs
    spec = {
        "charter_case_id": charter_case,
        "workbench_case_id": wb_case_id,
        "variant": variant,
        "persona": persona,
        "family": "deepseek",
        "model_id": "deepseek-chat",
        "run_id": run_id,
        "max_steps": config.max_steps,
        "max_input_tokens": config.max_input_tokens,
        "prestage_s": prestage_s,
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
        v = result.verdict
        verdict_str = (
            f"VERDICT pass={v.passed} observed={v.observed} ref={v.reference}±{v.tolerance}{v.tolerance_kind}"
            if v
            else f"DROPPED ({result.drop_reason})" if result.dropped
            else f"INCOMPLETE ({result.error or 'no terminal call'})"
        )
        print(f"  → {verdict_str}  steps={result.steps}  "
              f"in_tok={result.total_input_tokens}  "
              f"elapsed={elapsed:.1f}s")
    else:
        (run_dir / "result.json").write_text(
            json.dumps({"error": error or "no result"}, ensure_ascii=False,
                       indent=2),
            encoding="utf-8",
        )
        print(f"  → ERROR  elapsed={elapsed:.1f}s  {error}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
