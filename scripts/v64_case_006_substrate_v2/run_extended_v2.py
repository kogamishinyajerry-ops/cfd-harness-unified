"""Path (b) extended v2 · assemble_stack on case_006 with the v1 substrate
PLUS the newly-landed ``solver_block_inputs.yaml`` (V27 + V28 capture).

DEC-V64-A-sub-M-V64A-CASE-006-SUBSTRATE-V2 (V63-A carry-over #6). Mirrors
``scripts/v63_case_006_substrate/run_extended.py`` (B42) and adds one
substrate-side input file newly landed under ``case_006/inputs/``:

  - ``solver_block_inputs.yaml`` -> ``solver_block_advisor`` dispatch
    (V27 + V28 evidence rows · case_006 v1 2026-05-08 pre-fix snapshot)

Goal: push V-row truth-capture rate from 3/9 firm (V29 + V30 + D1 · B42
substrate v1) to 5/9 firm (+ V27 + V28 via solver_block_advisor LANDED
2026-05-15) on case_006.

Run from repo root::

    .venv/bin/python -m scripts.v64_case_006_substrate_v2.run_extended_v2
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 4Q gate Q1: drop LLM keys BEFORE any backend import.
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.pop(_k, None)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from scripts.stack_track_c_session_3_rerun.build_inputs import (  # noqa: E402
    BC_FORK_DEFAULT,
    CASE_DIR,
    build_parts_manifest,
    build_shm_dict,
    build_thermo_dict,
    step_path,
)
from scripts.v63_case_006_substrate.run_extended import (  # noqa: E402
    load_interface_bodies,
    load_interface_specs,
    load_thin_wall_inputs,
)
from ui.backend.services.advisor_stack import assemble_stack  # noqa: E402
from ui.backend.services.geometry_ingest import solver_block_advisor  # noqa: E402

INPUTS = CASE_DIR / "inputs"


def load_solver_block_snapshot() -> solver_block_advisor.SolverBlockSnapshot:
    """Load case_006/inputs/solver_block_inputs.yaml -> SolverBlockSnapshot."""
    raw = yaml.safe_load((INPUTS / "solver_block_inputs.yaml").read_text())
    return solver_block_advisor.SolverBlockSnapshot(
        solver=str(raw["solver"]),
        adjust_time_step=raw.get("adjust_time_step"),
        delta_t=raw.get("delta_t"),
        preconditioners=dict(raw.get("preconditioners") or {}),
    )


def main() -> dict:
    parts = build_parts_manifest()
    shm = build_shm_dict()
    thermo = build_thermo_dict()
    step = step_path()

    interface_bodies = load_interface_bodies()
    interface_specs = load_interface_specs()
    thin_wall_inputs = load_thin_wall_inputs()
    solver_block_snapshot = load_solver_block_snapshot()

    report = assemble_stack(
        parts_manifest=parts,
        shm_dict=shm,
        thermo_dict=thermo,
        step_path=step,
        bc_fork=BC_FORK_DEFAULT,
        interface_bodies=interface_bodies,
        interface_specs=interface_specs,
        thin_wall_inputs=thin_wall_inputs,
        solver_block_snapshot=solver_block_snapshot,
    )

    out = {
        "advisor_count": report.advisor_count,
        "finding_count": len(report.findings),
        "critical_count": report.critical_count,
        "warning_count": report.warning_count,
        "failed_advisor_count": report.failed_advisor_count,
        "advisors_dispatched": sorted({c.advisor_name for c in report.advisor_calls}),
        "evidence_refs": sorted(report.evidence_refs),
        "findings": [
            {
                "code": f.code,
                "severity": f.severity,
                "source_advisor": f.source_advisor,
                "evidence_v_rows": list(f.evidence_v_rows),
                "message": f.message,
                "location": f.location,
            }
            for f in report.findings
        ],
        "advisor_calls": [
            {
                "advisor_name": c.advisor_name,
                "status": c.status,
                "duration_ms": c.duration_ms,
                "input_summary": c.input_summary,
                "version": c.version,
                "output_summary": (
                    c.output
                    if isinstance(c.output, dict)
                    else type(c.output).__name__
                ),
            }
            for c in report.advisor_calls
        ],
        "env_keys_present": {
            k: bool(os.environ.get(k))
            for k in (
                "ANTHROPIC_API_KEY",
                "OPENAI_API_KEY",
                "GOOGLE_API_KEY",
                "DEEPSEEK_API_KEY",
            )
        },
    }

    out_path = Path(__file__).parent / "stack_report_python_extended_v2.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    out = main()
    print(
        json.dumps(
            {
                "advisor_count": out["advisor_count"],
                "finding_count": out["finding_count"],
                "critical_count": out["critical_count"],
                "warning_count": out["warning_count"],
                "failed_advisor_count": out["failed_advisor_count"],
                "advisors_dispatched": out["advisors_dispatched"],
                "evidence_refs": out["evidence_refs"],
                "env_keys_present": out["env_keys_present"],
            },
            indent=2,
        )
    )
