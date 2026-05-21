"""cfdtrust ingest — DEC-V61-201-SUB-INGEST.

Import an externally-run OpenFOAM case into the audit subsystem without
re-invoking the solver. Mirrors the printing contract of `cfdtrust run`
(in cli.py) so the CLI surface is uniform.

Honesty fence reminder (enforced in audit/report.py + schema): an
ingested case can never reach `overall_status=PASS` or
`validation_status=validated`; the harness did not witness the solver
run. The most an ingested case can achieve is `overall_status=WARN`
with every individual gate at PASS.
"""
from __future__ import annotations

import sys
from typing import Any, Dict

from .manifest import ManifestError, case_dir, validate_manifest
from .audit import solver

# Codex R1-P2 fix: ONLY BLOCKED exits non-zero. FAIL on the solver gate
# means "evidence was imported successfully but residuals didn't meet
# the manifest target" — a valid trust outcome that downstream `cfdtrust
# report` consumes. Returning 1 here breaks the `ingest && report`
# chained workflow on exactly the cases users most need to inspect:
# external runs that landed but did not converge.
_INGEST_ENV_BLOCKED = {"BLOCKED"}


def _print_ok(msg: str) -> None:
    print(f"[cfdtrust] OK   {msg}")


def _print_warn(msg: str) -> None:
    print(f"[cfdtrust] WARN {msg}")


def _print_fail(msg: str) -> None:
    print(f"[cfdtrust] FAIL {msg}", file=sys.stderr)


def cmd_ingest(case_path: str) -> int:
    """Ingest an externally-run case. Mirrors `cmd_run` shape from cli.py.

    Exit codes (Codex R1-P2 clarification):
      0  — ingest step succeeded; gate status may be PASS / WARN / FAIL.
           A FAIL gate means evidence was imported and the solver did
           not meet residual targets — this is a valid trust outcome
           and the downstream `cfdtrust report` exit code carries the
           overall trust verdict. Scripted `ingest && report` flows
           rely on this.
      1  — ingest itself was BLOCKED by an environment / case-shape
           issue (Docker unavailable, no time directory, no log file,
           etc.). No artifacts were imported; rerunning `report` won't
           help.
      2  — manifest could not be loaded.
    """
    try:
        cd = case_dir(case_path)
        manifest = validate_manifest(cd)
    except ManifestError as e:
        _print_fail(str(e))
        return 2

    gate: Dict[str, Any] = solver.ingest(cd, manifest)
    status = gate.get("status", "BLOCKED")

    if status in _INGEST_ENV_BLOCKED:
        _print_fail(f"ingest {status}: {gate.get('summary')}")
        details = gate.get("details", {}) or {}
        reason = details.get("reason")
        if reason:
            _print_fail(f"  reason: {reason}")
        next_step = details.get("next_step")
        if next_step:
            _print_warn(f"  next step: {next_step}")
        return 1

    # PASS / WARN / FAIL all mean "ingest itself succeeded; here is the
    # gate verdict on the imported evidence". Exit 0 so the standard
    # `cfdtrust ingest <case> && cfdtrust report <case>` chain keeps
    # working on non-converged external runs.
    if status == "FAIL":
        _print_warn(f"ingest {status}: {gate.get('summary')}")
        _print_warn(
            "  Solver gate FAILed on imported residuals — evidence was "
            "still ingested. Run `cfdtrust report` to assemble the full "
            "trust_report.json."
        )
    else:
        _print_ok(f"ingest {status}: {gate.get('summary')}")

    details = gate.get("details", {}) or {}
    src = details.get("external_log_source")
    if src:
        _print_ok(f"  external_log_source = {src}")
    image = details.get("image")
    if image:
        _print_ok(f"  checkmesh_image     = {image}")
    _print_warn(
        "Ingested run: harness did NOT witness the solver execution. "
        "trust_report will cap overall_status at WARN; validation_status "
        "cannot reach `validated`."
    )
    return 0
