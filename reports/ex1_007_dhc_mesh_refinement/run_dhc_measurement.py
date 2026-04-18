"""EX-1-007 B1 post-commit: full DHC Ra=1e10 solver measurement.

Runs differential_heated_cavity case end-to-end (blockMesh + buoyantFoam +
postProcess + Nu extraction) via TaskRunner + FoamAgentExecutor and writes
measurement result to reports/ex1_007_dhc_mesh_refinement/measurement_result.yaml.

Expected wall-clock: 30-90 min on cfd-openfoam arm64 container (256^2 cells).
C5 predicted Nu band: [11, 21] (centre 16.1). Gold reference: 30.0.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ["EXECUTOR_MODE"] = "foam_agent"

from src.task_runner import TaskRunner

OUT = Path(__file__).parent / "measurement_result.yaml"


def _dump_yaml(data):
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def main() -> int:
    t0 = time.monotonic()
    started_at = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    runner = TaskRunner(correction_policy="suggest_only")
    batch = runner.run_batch(["differential_heated_cavity"])

    elapsed = time.monotonic() - t0
    ended_at = _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Extract observables
    obs = {}
    if batch.results and batch.results[0] is not None:
        cmp_ = batch.results[0]
        obs["passed"] = cmp_.passed
        obs["summary"] = cmp_.summary
        obs["deviations"] = [
            {
                "quantity": d.quantity,
                "expected": d.expected,
                "actual": d.actual,
                "relative_error": d.relative_error,
            }
            for d in (cmp_.deviations or [])
        ]

    attrib = None
    if batch.attribution_reports and batch.attribution_reports[0] is not None:
        ar = batch.attribution_reports[0]
        attrib = {
            "primary_cause": getattr(ar, "primary_cause", None),
            "confidence": getattr(ar, "confidence", None),
            "chain_complete": getattr(ar, "chain_complete", None),
            "audit_concern": getattr(ar, "audit_concern", None),
        }

    # Nu verdict band check (C5)
    nu_measured = None
    for dev in obs.get("deviations", []):
        if dev["quantity"] == "nusselt_number":
            nu_measured = dev["actual"]
            break
    # Passed case would not record deviation; but DHC gold=30, predicted 16 → always in deviation
    c5_band = {"low": 11.0, "centre": 16.1, "high": 21.0}
    c5_check = {"nu_measured": nu_measured, "band": c5_band}
    if nu_measured is not None:
        if nu_measured < c5_band["low"]:
            c5_check["verdict"] = "BELOW_BAND — re-Gate required"
        elif nu_measured > c5_band["high"]:
            c5_check["verdict"] = "ABOVE_BAND — investigate overshoot"
        else:
            c5_check["verdict"] = "IN_BAND — successful landing"
    else:
        c5_check["verdict"] = "NO_DATA — solver failed or Nu not extracted"

    payload = {
        "slice_id": "EX-1-007",
        "run_type": "post_commit_solver_measurement",
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "wall_clock_seconds": round(elapsed, 1),
        "batch_summary": {
            "total": batch.total,
            "passed": batch.passed,
            "failed": batch.failed,
            "errors": batch.errors,
        },
        "observables": obs,
        "attribution": attrib,
        "c5_band_check": c5_check,
    }

    OUT.write_text(_dump_yaml(payload))
    print(_dump_yaml(payload))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        OUT.write_text(
            _dump_yaml(
                {
                    "slice_id": "EX-1-007",
                    "run_type": "post_commit_solver_measurement",
                    "status": "EXCEPTION",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
        )
        sys.exit(1)
