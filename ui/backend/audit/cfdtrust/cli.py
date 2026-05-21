"""cfdtrust CLI — Phase 0.

Subcommands have distinct, non-overlapping semantics (Red Team F-05):

  validate-manifest <case_dir>    schema-check the manifest
  audit <case_dir>                run structural gates (geometry, mesh, bc).
                                  Read existing solver artifacts via read_artifacts;
                                  if missing, solver gate is BLOCKED. Audit NEVER
                                  invokes the solver.
  run <case_dir>                  execute the solver (mocked or real per
                                  manifest.solver_backend, F-04). Write solver.log
                                  + residuals.csv.
  report <case_dir>               read all artifacts produced by audit + run, run
                                  qoi + reference comparison, assemble trust_report.json.

All commands return non-zero exit codes when a gate FAILs / BLOCKs or when
overall_status is FAIL / BLOCKED (Red Team F-06). MOCKED still exits 0 — a
mocked run is not a failure of the harness, only an unfinished validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from .manifest import ManifestError, case_dir, validate_manifest, load_manifest
from .audit import boundary_conditions, geometry, mesh, qoi as qoi_mod, solver
from .audit.report import assemble


# ---------- printing helpers ----------


def _print_ok(msg: str) -> None:
    print(f"[cfdtrust] OK   {msg}")


def _print_warn(msg: str) -> None:
    print(f"[cfdtrust] WARN {msg}")


def _print_fail(msg: str) -> None:
    print(f"[cfdtrust] FAIL {msg}", file=sys.stderr)


# F-06: a "bad" gate status that should map to non-zero CLI exit.
_BAD_STATUSES = {"FAIL", "BLOCKED"}
_BAD_OVERALL = {"FAIL", "BLOCKED"}


def _gate_exit_code(gates: Dict[str, Dict[str, Any]]) -> int:
    """1 if any gate is FAIL / BLOCKED, else 0."""
    return 1 if any(g.get("status") in _BAD_STATUSES for g in gates.values()) else 0


# ---------- gate composition ----------


def _structural_gates(cd: Path, manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The gates `cfdtrust audit` is responsible for. NO solver execution."""
    return {
        "geometry_contract": geometry.run(cd, manifest),
        "mesh_contract":     mesh.run(cd, manifest),
        "bc_contract":       boundary_conditions.run(cd, manifest),
    }


def _full_gates_for_report(cd: Path, manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """All six gates for trust_report assembly. Solver gate is OBSERVED, not executed."""
    structural = _structural_gates(cd, manifest)
    solver_gate = solver.read_artifacts(cd, manifest)
    qoi_out = qoi_mod.run(cd, manifest)
    return {
        **structural,
        "solver_execution":     solver_gate,
        "qoi_extraction":       qoi_out["qoi_gate"],
        "reference_comparison": qoi_out["reference_gate"],
    }


# ---------- subcommands ----------


def cmd_validate(case_path: str) -> int:
    try:
        manifest = validate_manifest(case_path)
    except ManifestError as e:
        _print_fail(str(e))
        return 2
    _print_ok(f"manifest valid: case_id={manifest['case_id']}")
    return 0


def cmd_audit(case_path: str) -> int:
    """
    Structural inspection only — geometry, mesh, bc.

    Audit does NOT observe the solver gate. That belongs in `cfdtrust report`,
    which composes structural gates with the solver observation. This keeps
    `make trust-loop` ordering simple: `validate audit run report` — audit
    can run on a case that has not been executed yet without falsely BLOCKING
    the pipeline.
    """
    try:
        cd = case_dir(case_path)
        manifest = validate_manifest(cd)
    except ManifestError as e:
        _print_fail(str(e))
        return 2
    gates = _structural_gates(cd, manifest)
    for name, gate in gates.items():
        _print_ok(f"audit gate {name}: {gate.get('status')}")
    _print_warn("solver state and qoi/reference gates are reported by `cfdtrust report`.")
    return _gate_exit_code(gates)


def cmd_run(case_path: str) -> int:
    """Execute the solver. The only command that calls solver.execute."""
    try:
        cd = case_dir(case_path)
        manifest = validate_manifest(cd)
    except ManifestError as e:
        _print_fail(str(e))
        return 2
    gate = solver.execute(cd, manifest)
    status = gate.get("status")
    if status == "MOCKED":
        _print_warn(f"solver execution MOCKED — no CFD was performed (status={status}).")
        return 0
    if status in _BAD_STATUSES:
        _print_fail(f"solver execution {status}: {gate.get('summary')}")
        return 1
    _print_ok(f"solver execution {status}: {gate.get('summary')}")
    return 0


def cmd_report(case_path: str) -> int:
    try:
        cd = case_dir(case_path)
        manifest = validate_manifest(cd)
    except ManifestError as e:
        _print_fail(str(e))
        return 2
    gates = _full_gates_for_report(cd, manifest)
    report_path = assemble(cd, manifest, gates)
    report = json.loads(Path(report_path).read_text())
    _print_ok(f"trust_report written: {report_path}")
    print(f"        overall_status   = {report['overall_status']}")
    print(f"        solver_execution = {report['solver_execution']}")
    print(f"        validation_status= {report['validation_status']}")
    if report["solver_execution"] != "real":
        _print_warn("This trust_report does NOT constitute real CFD validation.")
    return 1 if report["overall_status"] in _BAD_OVERALL else 0


# ---------- argparse ----------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cfdtrust", description="AI-CFD-V2 Phase 0 trust harness CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name: str, help_text: str):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("case_dir", help="path to a CFD case directory containing case_manifest.yaml")
        return sp

    add("validate-manifest", "Validate case_manifest.yaml against the schema.")
    add("audit", "Run structural gates (geometry/mesh/bc); observe solver artifacts if present.")
    add("run", "Execute the solver (mocked or real per manifest.solver_backend).")
    add("report", "Assemble trust_report.json from existing audit + solver artifacts.")

    # M3.1: `init` doesn't take an existing case_dir; it CREATES one.
    sp_init = sub.add_parser("init", help="Scaffold a new case dir from an existing template case.")
    sp_init.add_argument("new_case_id", help="case_id for the new case (alphanumeric + underscore)")
    sp_init.add_argument(
        "--template", "-t", default="flat_plate_rans_sst",
        help="case_id of the template to clone from (default: flat_plate_rans_sst)",
    )
    sp_init.add_argument(
        "--cases-root", default=None,
        help="cases/ directory (default: ./cases/ under CWD)",
    )

    # M3.2: `verify-reference` operates on a case_dir but its semantics
    # are check-or-fix not run-or-report.
    sp_vr = sub.add_parser(
        "verify-reference",
        help="Verify or update manifest.reference_comparison.reference_csv_sha256.",
    )
    sp_vr.add_argument("case_dir", help="path to a CFD case directory containing case_manifest.yaml")
    sp_vr.add_argument(
        "--fix", action="store_true",
        help="rewrite manifest.reference_csv_sha256 to match the on-disk file (default: check-only)",
    )

    # M3.3: `doctor` performs a static audit without running the solver.
    add("doctor", "Static audit of a case dir (no solver run). Surfaces common configuration issues.")

    # M10: `explain` renders a Markdown advisor explanation from trust_report.json.
    sp_explain = sub.add_parser(
        "explain",
        help="Render a Markdown explanation of trust_report.json with per-gate WHY + recommendations.",
    )
    sp_explain.add_argument("case_dir", help="path to a CFD case directory containing case_manifest.yaml")
    sp_explain.add_argument(
        "--out", default=None,
        help="write Markdown to this file instead of stdout",
    )

    args = p.parse_args(argv)
    if args.cmd == "validate-manifest":
        return cmd_validate(args.case_dir)
    if args.cmd == "audit":
        return cmd_audit(args.case_dir)
    if args.cmd == "run":
        return cmd_run(args.case_dir)
    if args.cmd == "report":
        return cmd_report(args.case_dir)
    if args.cmd == "init":
        from pathlib import Path as _P
        from .cli_init import cmd_init
        return cmd_init(
            args.new_case_id,
            template_case_id=args.template,
            cases_root=_P(args.cases_root) if args.cases_root else None,
        )
    if args.cmd == "verify-reference":
        from .cli_verify import cmd_verify_reference
        return cmd_verify_reference(args.case_dir, fix=args.fix)
    if args.cmd == "doctor":
        from .cli_doctor import cmd_doctor
        return cmd_doctor(args.case_dir)
    if args.cmd == "explain":
        from .cli_explain import cmd_explain
        return cmd_explain(args.case_dir, out=args.out)
    p.error(f"unknown subcommand: {args.cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
