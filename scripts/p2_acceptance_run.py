"""§5d Part-2 acceptance driver — runs 5 whitelist cases via FoamAgentExecutor
and emits Screen-4 measurement fixtures from solver output.

Usage (from repo root):
    EXECUTOR_MODE=foam_agent \\
    .venv/bin/python scripts/p2_acceptance_run.py

Output:
    ui/backend/tests/fixtures/{case_id}_measurement.yaml  (one per case)
    reports/post_phase5_acceptance/2026-04-21_part2_raw_results.json

Context:
    DEC-V61-019 PR-5d.1 closed. RETRO-V61-001 ratified. Running Option C
    from the acceptance plan to populate Screens 4/5 with real-solver
    measurements for the 5 PASS/FAIL/HAZARD-diverse cases.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.foam_agent_adapter import FoamAgentExecutor  # noqa: E402
from src.task_runner import TaskRunner  # noqa: E402

TARGET_CASES = [
    "lid_driven_cavity",
    "backward_facing_step",
    "plane_channel_flow",
    "turbulent_flat_plate",
    "duct_flow",
]

FIXTURE_DIR = REPO_ROOT / "ui" / "backend" / "tests" / "fixtures"
RAW_RESULTS_PATH = (
    REPO_ROOT / "reports" / "post_phase5_acceptance" / "2026-04-21_part2_raw_results.json"
)


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], timeout=5
        )
        return out.decode().strip()[:7]
    except Exception:
        return "unknown"


def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_primary_measurement(report) -> tuple[str | None, float | None, str]:
    """Return (quantity_name, value, source_note).

    Precedence: comparison.deviations[0] if present → key_quantities first
    numeric entry → None.
    """
    comp = report.comparison_result
    if comp is not None and comp.deviations:
        first = comp.deviations[0]
        actual = first.actual
        # actual may be float or dict like {"value": ..., "note": ...}
        if isinstance(actual, dict) and "value" in actual:
            return first.quantity, float(actual["value"]), "comparator_deviation"
        if isinstance(actual, (int, float)):
            return first.quantity, float(actual), "comparator_deviation"

    kq = report.execution_result.key_quantities or {}
    for k, v in kq.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k, float(v), "key_quantities_fallback"
        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
            return k, float(v["value"]), "key_quantities_fallback"
    return None, None, "no_numeric_quantity"


def _write_fixture(case_id: str, report, commit_sha: str) -> Path:
    """Emit minimal Screen-4 fixture from the run report."""
    quantity, value, source_note = _extract_primary_measurement(report)
    comp = report.comparison_result
    passed = comp.passed if comp else False
    unit = "dimensionless"  # conservative default; gold_standard has unit but we don't
    # cross-reference here — the comparator already used the correct gold unit.

    doc = {
        "case_id": case_id,
        "source": "p2_acceptance_solver_run",
        "measurement": {
            "value": value if value is not None else 0.0,
            "unit": unit,
            "run_id": f"p2_acc_{case_id}_{commit_sha}",
            "commit_sha": commit_sha,
            "measured_at": _iso_now(),
            "quantity": quantity,
            "extraction_source": source_note,
            "solver_success": report.execution_result.success,
            "comparator_passed": passed,
        },
        "audit_concerns": [
            {
                "concern_type": "CONTRACT_STATUS",
                "summary": (comp.summary if comp else "No comparator result")[:240],
                "detail": (comp.summary if comp else "")[:2000],
                "decision_refs": ["DEC-V61-019", "RETRO-V61-001"],
            }
        ] if comp else [],
        "decisions_trail": [
            {
                "decision_id": "DEC-V61-019",
                "date": "2026-04-21",
                "title": "PR-5d.1 Codex closure (HIGH+MED)",
                "autonomous": True,
            },
            {
                "decision_id": "RETRO-V61-001",
                "date": "2026-04-21",
                "title": "v6.1 governance retrospective (bundle D)",
                "autonomous": True,
            },
        ],
    }
    path = FIXTURE_DIR / f"{case_id}_measurement.yaml"
    with path.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Phase 5 §5d Part-2 acceptance fixture (2026-04-21).\n"
            "# Auto-generated from FoamAgentExecutor + ResultComparator run by\n"
            "# scripts/p2_acceptance_run.py. DEC-V61-019 + RETRO-V61-001 context.\n"
            "# NOT a curated fixture — regenerate by re-running the driver.\n\n"
        )
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False)
    return path


def main() -> int:
    if os.environ.get("EXECUTOR_MODE", "").lower() != "foam_agent":
        print(
            "ERROR: set EXECUTOR_MODE=foam_agent before running this driver.",
            file=sys.stderr,
        )
        return 2

    commit_sha = _git_head_sha()
    print(f"[p2] main SHA: {commit_sha}")
    print(f"[p2] cases: {TARGET_CASES}")
    print(f"[p2] fixture dir: {FIXTURE_DIR}")
    RAW_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    runner = TaskRunner(executor=FoamAgentExecutor())

    raw_log: list[dict] = []
    for idx, case_id in enumerate(TARGET_CASES, 1):
        t0 = time.monotonic()
        print(f"\n[p2] case {idx}/{len(TARGET_CASES)} — {case_id} → start")
        try:
            task_spec = runner._task_spec_from_case_id(case_id)
            report = runner.run_task(task_spec)
        except Exception as e:  # noqa: BLE001
            print(f"[p2] case {case_id} EXCEPTION: {e!r}")
            raw_log.append({"case_id": case_id, "exception": repr(e)})
            continue

        dt = time.monotonic() - t0
        comp = report.comparison_result
        verdict = "UNKNOWN"
        if comp is not None:
            verdict = "PASS" if comp.passed else "FAIL"

        quantity, value, source_note = _extract_primary_measurement(report)
        print(
            f"[p2] case {case_id} done in {dt:.1f}s — "
            f"success={report.execution_result.success} "
            f"verdict={verdict} "
            f"{quantity}={value} ({source_note})"
        )

        fixture_path = _write_fixture(case_id, report, commit_sha)
        print(f"[p2] fixture written: {fixture_path.relative_to(REPO_ROOT)}")

        raw_log.append(
            {
                "case_id": case_id,
                "elapsed_s": dt,
                "exec_success": report.execution_result.success,
                "is_mock": report.execution_result.is_mock,
                "verdict": verdict,
                "quantity": quantity,
                "value": value,
                "source_note": source_note,
                "error_message": report.execution_result.error_message,
                "residuals_keys": list(report.execution_result.residuals.keys()),
            }
        )

        with RAW_RESULTS_PATH.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "main_sha": commit_sha,
                    "started_at": _iso_now(),
                    "cases": raw_log,
                },
                fh,
                indent=2,
                default=str,
            )

    print("\n[p2] batch complete.")
    print(f"[p2] raw results: {RAW_RESULTS_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
