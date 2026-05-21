"""Assemble trust_report.json from individual gate outputs."""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft7Validator

from ..status import ensure_artifacts_dir, utc_now_iso

SCHEMA_PACKAGE = "cfdtrust.schemas"
SCHEMA_FILENAME = "trust_report.schema.json"


def _load_schema() -> Dict[str, Any]:
    with resources.files(SCHEMA_PACKAGE).joinpath(SCHEMA_FILENAME).open("r") as f:
        return json.load(f)


def _overall_status(gates: Dict[str, Dict[str, Any]]) -> str:
    statuses = {g.get("status", "FAIL") for g in gates.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if "MOCKED" in statuses:
        return "MOCKED"
    if "WARN" in statuses:
        return "WARN"
    if statuses == {"PASS"}:
        return "PASS"
    return "WARN"


def assemble(case_dir: Path, manifest: Dict[str, Any], gates: Dict[str, Dict[str, Any]]) -> Path:
    art = ensure_artifacts_dir(case_dir)
    report_path = art / "trust_report.json"

    solver_gate = gates.get("solver_execution", {})
    solver_execution = solver_gate.get("details", {}).get("execution", "mocked")

    # Sub-commit 2d: validation_status now reflects the reference_comparison
    # gate's real outcome instead of always landing on "unknown" for real
    # runs. Honesty rule: a real solver run whose Cf curve deviated from
    # NASA TMR by 67% is NOT validated — that's `not_validated`, not
    # `unknown`. Pre-2d the harness would have called it "unknown" even
    # though we have concrete evidence of failed validation.
    #
    # M9.1 fix (R24-F-01): pre-fix, `validation_status` only checked that
    # the solver ran (`execution=real`), not that the solver_execution
    # GATE itself PASSed. A case that ran to max_iter without converging
    # but happened to produce a Cf within tolerance of NASA reference
    # would land "validated" — a coincidental match is NOT validation.
    # Surfaced by M9.1 channel_flow live run: solver_execution FAIL +
    # reference_comparison PASS would have incorrectly claimed
    # validation. Now we additionally require the solver gate to PASS.
    solver_status = solver_gate.get("status", "MOCKED")
    ref_gate = gates.get("reference_comparison", {})
    ref_status = ref_gate.get("status", "MOCKED")
    ref_real = ref_gate.get("details", {}).get("real_comparison_performed", False)

    if solver_execution != "real":
        validation_status = "not_validated"
    elif solver_status != "PASS":
        # Solver executed but didn't pass its own contract (residual
        # targets not met, timed out, etc.) — cannot claim validation
        # even if the reference comparison happens to PASS.
        validation_status = "not_validated"
    elif not ref_real:
        validation_status = "unknown"   # solver real + PASS, but reference path not exercised
    elif ref_status == "PASS":
        validation_status = "validated"
    elif ref_status == "FAIL":
        validation_status = "not_validated"
    else:  # BLOCKED / MOCKED / WARN / anything else
        validation_status = "unknown"

    overall = _overall_status(gates)

    limitations = []
    if solver_execution == "mocked":
        limitations.append(
            "No real CFD solver was executed. This run does not constitute validation."
        )
    ref_gate = gates.get("reference_comparison", {})
    if not ref_gate.get("details", {}).get("real_comparison_performed", False):
        limitations.append(
            "Reference comparison is a placeholder. No published data was compared against."
        )
    if not limitations:
        limitations.append("Phase 0 scaffold — limitations not exhaustively enumerated.")

    next_actions = [
        "Implement real OpenFOAM adapter (Phase 1).",
        "Finalize reference dataset for flat_plate_rans_sst.",
        "Add seeded negative-test fixtures.",
        "Run Red Team review on this trust loop.",
    ]

    artifacts_index = {
        "geometry_report": str((art / "geometry_report.json").relative_to(case_dir)),
        "mesh_report": str((art / "mesh_report.json").relative_to(case_dir)),
        "bc_audit": str((art / "bc_audit.json").relative_to(case_dir)),
        "solver_log": str((art / "solver.log").relative_to(case_dir)),
        "residuals_csv": str((art / "residuals.csv").relative_to(case_dir)),
        "qoi_csv": str((art / "qoi.csv").relative_to(case_dir)),
        "reference_comparison_csv": str((art / "reference_comparison.csv").relative_to(case_dir)),
        "trust_report": str(report_path.relative_to(case_dir)),
    }

    report = {
        "case_id": manifest.get("case_id"),
        "generated_at": utc_now_iso(),
        "overall_status": overall,
        "solver_execution": solver_execution,
        "validation_status": validation_status,
        "gates": gates,
        "artifacts": artifacts_index,
        "limitations": limitations,
        "next_actions": next_actions,
    }

    # validate before writing — fail loudly if our own writer drifts from schema
    Draft7Validator(_load_schema()).validate(report)

    report_path.write_text(json.dumps(report, indent=2))
    return report_path
