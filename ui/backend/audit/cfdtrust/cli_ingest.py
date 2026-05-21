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

_BAD_STATUSES = {"FAIL", "BLOCKED"}


def _print_ok(msg: str) -> None:
    print(f"[cfdtrust] OK   {msg}")


def _print_warn(msg: str) -> None:
    print(f"[cfdtrust] WARN {msg}")


def _print_fail(msg: str) -> None:
    print(f"[cfdtrust] FAIL {msg}", file=sys.stderr)


def cmd_ingest(case_path: str) -> int:
    """Ingest an externally-run case. Mirrors `cmd_run` shape from cli.py.

    Exit codes:
      0  — ingest produced a non-BLOCKED gate (PASS / WARN / FAIL all exit 0
           because the ingest step itself succeeded; downstream `cfdtrust
           report` exit code carries the trust verdict).
      1  — ingest gate status is FAIL or BLOCKED.
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

    if status in _BAD_STATUSES:
        _print_fail(f"ingest {status}: {gate.get('summary')}")
        details = gate.get("details", {}) or {}
        reason = details.get("reason")
        if reason:
            _print_fail(f"  reason: {reason}")
        next_step = details.get("next_step")
        if next_step:
            _print_warn(f"  next step: {next_step}")
        return 1

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
