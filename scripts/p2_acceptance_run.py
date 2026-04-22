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
from src.result_comparator import _lookup_with_alias  # noqa: E402

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


def _gold_expected_quantity(case_id: str) -> str | None:
    """Same helper as phase5_audit_run._gold_expected_quantity.

    Loads `quantity` from knowledge/gold_standards/{case_id}.yaml. Returns
    None if the file is absent or unparseable — caller then falls back to
    the legacy first-numeric path (shouldn't happen for whitelist cases).
    """
    gold_path = REPO_ROOT / "knowledge" / "gold_standards" / f"{case_id}.yaml"
    if not gold_path.is_file():
        return None
    try:
        with gold_path.open("r", encoding="utf-8") as fh:
            docs = list(yaml.safe_load_all(fh))
    except Exception:
        return None
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        q = doc.get("quantity")
        if isinstance(q, str) and q.strip():
            return q.strip()
        obs = doc.get("observables")
        if isinstance(obs, list) and obs:
            first = obs[0]
            if isinstance(first, dict):
                name = first.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
    return None


def _extract_primary_measurement(
    report, expected_quantity: str | None = None
) -> tuple[str | None, float | None, str]:
    """Return (quantity_name, value, source_note).

    DEC-V61-036 G1: when `expected_quantity` is provided (derived from the
    gold standard), require the run to emit that exact quantity via direct
    match or result_comparator alias. NO first-numeric fallback — the prior
    fallback silently substituted any scalar and drove PASS-washing.

    Precedence with expected_quantity:
      1. comparator.deviations entry matching expected_quantity
      2. key_quantities direct/alias lookup on expected_quantity
      3. (expected_quantity, None, "no_numeric_quantity") — gate miss

    Legacy path (expected_quantity=None) preserves first-numeric for
    backwards-compat with any ad-hoc caller.
    """
    comp = report.comparison_result
    kq = report.execution_result.key_quantities or {}

    if expected_quantity is not None:
        # DEC-V61-036 G1 round 2: profile-quantity support — see
        # phase5_audit_run._primary_scalar for full discussion.
        def _quantity_matches(dev_quantity: str) -> bool:
            if dev_quantity == expected_quantity:
                return True
            return dev_quantity.split("[", 1)[0] == expected_quantity

        if comp is not None and comp.deviations:
            for dev in comp.deviations:
                if _quantity_matches(dev.quantity):
                    actual = dev.actual
                    if isinstance(actual, dict) and "value" in actual:
                        return dev.quantity, float(actual["value"]), "comparator_deviation"
                    if isinstance(actual, (int, float)):
                        return dev.quantity, float(actual), "comparator_deviation"
        value, resolved_key = _lookup_with_alias(kq, expected_quantity)
        if value is not None:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                src = (
                    "key_quantities_direct"
                    if resolved_key == expected_quantity
                    else f"key_quantities_alias:{resolved_key}"
                )
                return expected_quantity, float(value), src
            if isinstance(value, dict) and "value" in value and isinstance(
                value["value"], (int, float)
            ):
                return expected_quantity, float(value["value"]), "key_quantities_alias_dict"
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, (int, float)) and not isinstance(first, bool):
                    return (
                        f"{expected_quantity}[0]",
                        float(first),
                        "key_quantities_profile_sample",
                    )
                if isinstance(first, dict) and "value" in first and isinstance(
                    first["value"], (int, float)
                ):
                    return (
                        f"{expected_quantity}[0]",
                        float(first["value"]),
                        "key_quantities_profile_sample_dict",
                    )
        return expected_quantity, None, "no_numeric_quantity"

    # Legacy path (no expected_quantity): preserved for backward compat.
    if comp is not None and comp.deviations:
        first = comp.deviations[0]
        actual = first.actual
        if isinstance(actual, dict) and "value" in actual:
            return first.quantity, float(actual["value"]), "comparator_deviation"
        if isinstance(actual, (int, float)):
            return first.quantity, float(actual), "comparator_deviation"
    for k, v in kq.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k, float(v), "key_quantities_fallback_legacy"
        if isinstance(v, dict) and "value" in v and isinstance(v["value"], (int, float)):
            return k, float(v["value"]), "key_quantities_fallback_legacy"
    return None, None, "no_numeric_quantity"


def _write_fixture(case_id: str, report, commit_sha: str) -> Path:
    """Emit minimal Screen-4 fixture from the run report.

    DEC-V61-036 G1: extractor must match the gold's canonical quantity
    (with alias resolution). No numeric match → measurement.value: null,
    which forces hard-FAIL in validation_report._derive_contract_status.
    """
    expected_quantity = _gold_expected_quantity(case_id)
    quantity, value, source_note = _extract_primary_measurement(report, expected_quantity)
    comp = report.comparison_result
    passed = comp.passed if comp else False
    unit = "dimensionless"  # conservative default; gold_standard has unit but we don't
    # cross-reference here — the comparator already used the correct gold unit.

    # DEC-V61-036 G1: null (None) preserved in YAML as explicit missing.
    measurement_value: float | None = value

    audit_concerns: list[dict] = []
    if comp is not None:
        audit_concerns.append(
            {
                "concern_type": "CONTRACT_STATUS",
                "summary": (comp.summary or "No summary")[:240],
                "detail": (comp.summary or "")[:2000],
                "decision_refs": ["DEC-V61-019", "RETRO-V61-001"],
            }
        )
    if source_note == "no_numeric_quantity":
        audit_concerns.append(
            {
                "concern_type": "MISSING_TARGET_QUANTITY",
                "summary": (
                    f"Extractor could not locate gold quantity "
                    f"{quantity!r} in run key_quantities."
                )[:240],
                "detail": (
                    "DEC-V61-036 G1: prior PASS-washing fallback (first "
                    "numeric) closed. Adapter needs a case-specific "
                    "extractor for this quantity; verdict is hard-FAIL."
                )[:2000],
                "decision_refs": ["DEC-V61-036"],
            }
        )

    doc = {
        "case_id": case_id,
        "source": "p2_acceptance_solver_run",
        "measurement": {
            "value": measurement_value,
            "unit": unit,
            "run_id": f"p2_acc_{case_id}_{commit_sha}",
            "commit_sha": commit_sha,
            "measured_at": _iso_now(),
            "quantity": quantity,
            "extraction_source": source_note,
            "solver_success": report.execution_result.success,
            "comparator_passed": passed,
        },
        "audit_concerns": audit_concerns,
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
            {
                "decision_id": "DEC-V61-036",
                "date": "2026-04-22",
                "title": "Hard comparator gate G1 (missing-target-quantity)",
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
