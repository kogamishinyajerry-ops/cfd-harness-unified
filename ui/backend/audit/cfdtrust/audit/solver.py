"""Solver gate — Phase 0.

Two responsibilities, deliberately separated (Red Team F-05):

  - `execute(case_dir, manifest)`    invoked only by `cfdtrust run`. Honors
                                     `manifest.solver_backend` and either runs
                                     the mocked synthetic solver or returns a
                                     BLOCKED gate when the manifest declares an
                                     openfoam backend that the harness does not
                                     yet implement (Red Team F-04).
  - `read_artifacts(case_dir, ...)`  invoked by `cfdtrust audit` and `cfdtrust
                                     report`. Reads previously-written solver.log
                                     and residuals.csv. Reports BLOCKED if
                                     no artifacts exist. Never invokes the solver.

Before this round, all three CLI commands invoked `solver.run` as a side-effect,
which conflated observation with execution and forced trust-loop runs to
re-execute the solver 3×.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Dict

from ..status import ensure_artifacts_dir, utc_now_iso


# M2.3a fix: persist the execute-gate JSON to disk so `read_artifacts` reads
# the SAME truth `execute` recorded. Pre-fix, the two functions disagreed:
# `execute` could return FAIL (e.g. residual targets not met) but
# `read_artifacts` only checked file existence and would silently return PASS,
# letting a FAILed solver propagate into trust_report.json as a healthy gate.
# Flat-plate converged cleanly and the two paths happened to agree, hiding
# the drift. Backward-facing step does not — and surfaced this on M2.3.
_GATE_FILENAME = "solver_gate.json"


def _write_gate(case_dir: Path, gate: Dict[str, Any]) -> Dict[str, Any]:
    """Persist `gate` to artifacts/solver_gate.json.

    R17-F-02 fix: if the write fails (disk full, permissions, transient I/O),
    surface that as a BLOCKED augmentation of the returned gate AND continue.
    Pre-fix, an OSError here would propagate up and the caller would lose
    the gate result entirely. A persistence failure is worth reporting but
    must not silently obliterate the just-computed gate.
    """
    try:
        art = ensure_artifacts_dir(case_dir)
        (art / _GATE_FILENAME).write_text(json.dumps(gate, indent=2, default=str))
        return gate
    except OSError as e:
        # Don't recurse — return an augmented version without persistence.
        augmented = dict(gate)
        details = dict(augmented.get("details", {}) or {})
        details["gate_persistence_failed"] = str(e)
        details["next_step"] = (
            "Original gate result preserved in memory; subsequent "
            "`cfdtrust report` will fall back to file-existence detection. "
            "Fix the underlying disk/permission issue and re-run."
        )
        augmented["details"] = details
        return augmented


def _read_persisted_gate(case_dir: Path) -> Dict[str, Any] | None:
    p = case_dir / "artifacts" / _GATE_FILENAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


MOCK_BANNER = (
    "# AI-CFD-V2 Phase 0 mocked solver log\n"
    "# WARNING: No real CFD solver was executed.\n"
    "# Residuals below are synthetic placeholders.\n"
)

# Codex R5-P1 fix: an ingested case must remain identifiable as
# `execution="ingested"` even if `artifacts/solver_gate.json` is
# missing or unreadable. `_write_gate()` already documents OSError as
# a supported failure mode (returning the gate with a
# `gate_persistence_failed` augmentation), so the fallback in
# `read_artifacts()` is a live code path — without an in-log marker,
# the fallback used to upgrade any non-mocked artifact to
# `execution="real"`, silently bypassing the
# DEC-V61-201-SUB-INGEST honesty fences (cap overall_status at WARN,
# cap validation_status at `partial`).
#
# `cfdtrust ingest` prepends this banner to the transcribed
# `artifacts/solver.log`. `read_artifacts()` checks for it in the
# fallback branch and classifies the case as `execution="ingested"`
# instead of `"real"`. Mirror of the MOCK_BANNER pattern.
INGEST_BANNER = (
    "# AI-CFD-V2 ingested external solver log\n"
    "# WARNING: The trust harness did NOT witness this execution.\n"
    "# overall_status caps at WARN, validation_status caps at `partial`.\n"
    "# See DEC-V61-201-SUB-INGEST. Original log content follows below.\n"
)


# ---------- execution: solver.execute ----------


def execute(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Run the solver per `manifest.solver_backend`. Write artifacts to disk.

    Red Team F-04 fix: this function does NOT silently substitute mocked output
    when the manifest declares an openfoam backend. Each backend has a separate
    path; an undeclared / unimplemented backend returns BLOCKED.

    M2.3a fix: persist the resulting gate JSON to
    `artifacts/solver_gate.json` so `read_artifacts` reads the SAME truth.
    """
    backend = manifest.get("solver_backend")
    if backend == "mocked":
        gate = _execute_mocked(case_dir, manifest)
    elif backend == "openfoam":
        gate = _execute_openfoam(case_dir, manifest)
    else:
        gate = {
            "status": "BLOCKED",
            "summary": f"unknown solver_backend in manifest: {backend!r}",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "unknown_backend",
            },
        }
    return _write_gate(case_dir, gate)


def _execute_mocked(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Synthetic solver: writes a clearly-labeled log + decaying residuals."""
    art = ensure_artifacts_dir(case_dir)
    log_path = art / "solver.log"
    residuals_path = art / "residuals.csv"

    contract = manifest.get("solver_contract", {})
    targets = contract.get("residual_targets", {"Ux": 1e-5, "p": 1e-5})
    max_iter = int(contract.get("max_iterations", 500))

    log_lines = [MOCK_BANNER]
    with residuals_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["iteration"] + list(targets.keys()))
        for i in range(1, max_iter + 1):
            row = [i]
            line_parts = [f"Time = {i}"]
            for name, target in targets.items():
                val = max(target * 0.1, math.exp(-i / 80.0))
                row.append(f"{val:.3e}")
                line_parts.append(f"residual({name})={val:.3e}")
            writer.writerow(row)
            log_lines.append("  ".join(line_parts))
    log_path.write_text("\n".join(log_lines) + "\n")

    return {
        "status": "MOCKED",
        "summary": (
            f"Synthetic solver log with {max_iter} pseudo-iterations. "
            f"No real CFD executed."
        ),
        "artifact": str(log_path.relative_to(case_dir)),
        "details": {
            "execution": "mocked",
            "log": str(log_path.relative_to(case_dir)),
            "residuals_csv": str(residuals_path.relative_to(case_dir)),
            "iterations": max_iter,
            "generated_at": utc_now_iso(),
            "real_solver_invoked": False,
            "warning": "No CFD solver was executed. This does not constitute validation.",
        },
    }


def _execute_openfoam(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """OpenFOAM backend dispatch. Phase 0: not yet wired → BLOCKED."""
    try:
        # Future Phase 1 adapter lives here:
        from ..backends.openfoam import run as _run  # noqa: F401
        # If the import succeeds, the adapter is available — call it.
        return _run(case_dir, manifest)  # type: ignore[name-defined]
    except ImportError:
        return {
            "status": "BLOCKED",
            "summary": (
                "manifest declares solver_backend=openfoam but the OpenFOAM "
                "adapter is not implemented yet (Phase 1)."
            ),
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "openfoam_adapter_not_implemented",
                "next_step": "Either implement src/cfdtrust/backends/openfoam.py, "
                              "or change manifest.solver_backend to 'mocked' for Phase 0.",
            },
        }


# ---------- observation: solver.read_artifacts ----------


def read_artifacts(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inspect existing solver artifacts on disk; report the gate without
    re-running anything. If artifacts are missing, gate is BLOCKED.

    Red Team F-05 fix: separates observation from execution. `cfdtrust audit`
    and `cfdtrust report` call this; `cfdtrust run` calls `execute()`.

    M2.3a fix: prefer the persisted `solver_gate.json` (written by
    `execute`) so a FAILed execute can never silently become PASS in the
    persisted trust_report. The file-existence-only fallback remains for
    legacy case dirs that ran before this fix landed.
    """
    art = case_dir / "artifacts"
    log_path = art / "solver.log"
    residuals_path = art / "residuals.csv"

    # M2.3a: prefer the persisted gate; it is the SAME truth `execute` saw.
    persisted = _read_persisted_gate(case_dir)
    if persisted is not None:
        return persisted

    if not log_path.exists() or not residuals_path.exists():
        return {
            "status": "BLOCKED",
            "summary": "solver artifacts missing — run `cfdtrust run <case>` first.",
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "no_solver_artifacts",
                "expected_log": str(log_path.relative_to(case_dir)),
                "expected_residuals": str(residuals_path.relative_to(case_dir)),
            },
        }

    # Codex R5-P1 fix: widen the head scan from 3 lines to 5 so the
    # 4-line INGEST_BANNER is fully covered. MOCK_BANNER detection
    # (3 lines, scanned via "mocked" keyword) still works.
    log_head = log_path.read_text().splitlines()[:5]
    is_mocked = any("mocked" in line.lower() for line in log_head)
    # Detect the ingest banner literally — looking for the marker line
    # "AI-CFD-V2 ingested external solver log" so we don't false-trip
    # on user logs that happen to contain the word "ingested".
    is_ingested = any(
        "ingested external solver log" in line.lower() for line in log_head
    )
    iterations = max(0, sum(1 for _ in residuals_path.read_text().splitlines()) - 1)

    if is_mocked:
        return {
            "status": "MOCKED",
            "summary": f"Mocked solver artifacts present ({iterations} iterations).",
            "artifact": str(log_path.relative_to(case_dir)),
            "details": {
                "execution": "mocked",
                "log": str(log_path.relative_to(case_dir)),
                "residuals_csv": str(residuals_path.relative_to(case_dir)),
                "iterations": iterations,
                "real_solver_invoked": False,
                "warning": "No CFD solver was executed. This does not constitute validation.",
            },
        }
    if is_ingested:
        # DEC-V61-201-SUB-INGEST-P2-FOLLOWUP: don't hard-code WARN. The
        # pre-fix branch collapsed every banner-detected outcome to WARN,
        # which (a) silently upgraded a FAIL ingested run (residuals
        # didn't meet targets) to WARN, and (b) prevented the
        # PASS+ingested → partial-validation branch in `assemble()`
        # from firing after gate-JSON loss. Re-parse the solver log via
        # the same pure functions that produced the original gate and
        # overlay the ingest provenance.
        from ..backends.openfoam import (
            _compute_gate_from_residuals,
            _parse_simplefoam_log,
        )
        parsed = _parse_simplefoam_log(log_path.read_text())
        recovered = _compute_gate_from_residuals(parsed, manifest)
        details = dict(recovered.get("details", {}) or {})
        # Preserve ingest provenance regardless of recomputed status —
        # the honesty fences in `assemble()` key off `execution=="ingested"`.
        details["execution"] = "ingested"
        details["real_solver_invoked"] = False
        details["log"] = str(log_path.relative_to(case_dir))
        details["residuals_csv"] = str(residuals_path.relative_to(case_dir))
        details["recovered_from_log_banner"] = True
        details["warning"] = (
            "solver_gate.json was missing or unreadable; the gate was "
            "recovered by re-parsing solver.log + recomputing against "
            "manifest residual_targets. Re-run `cfdtrust ingest` to "
            "refresh the persisted gate JSON."
        )
        recovered["details"] = details
        recovered["artifact"] = str(log_path.relative_to(case_dir))
        return recovered
    # Legacy real-artifact fallback. CAUTION: a real run that FAILed but
    # didn't persist solver_gate.json would land here as PASS. Post-M2.3a
    # this branch should be reachable only for pre-fix case dirs.
    return {
        "status": "PASS",
        "summary": f"Real solver artifacts present ({iterations} iterations).",
        "artifact": str(log_path.relative_to(case_dir)),
        "details": {
            "execution": "real",
            "log": str(log_path.relative_to(case_dir)),
            "residuals_csv": str(residuals_path.relative_to(case_dir)),
            "iterations": iterations,
            "real_solver_invoked": True,
            "warning": "Legacy file-existence fallback; no persisted gate.json found. "
                       "Re-run `cfdtrust run` to refresh.",
        },
    }


# Backward-compatible alias — keep until callers migrate.
def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Deprecated alias for `execute`. Kept for compatibility with older CLI code."""
    return execute(case_dir, manifest)


# ---------- DEC-V61-201-SUB-INGEST: external-run ingest entry point ----------


def ingest(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest evidence from an externally-run case (DEC-V61-201-SUB-INGEST).

    Refuses non-openfoam backends — there is nothing to ingest from a
    mocked backend, and "unknown" backends shouldn't have produced any
    real evidence in the first place. The backend-level ingest helper
    then validates env, runs checkMesh, persists *_quality.json, and
    transcribes the existing solver log + residuals.

    Mirrors `execute()`'s persistence pattern WHEN the ingest actually
    runs: the resulting gate is written to `artifacts/solver_gate.json`
    so `read_artifacts` (and therefore `cfdtrust report`) reads the
    SAME truth — preventing the pre-M2.3a drift where execute and
    read_artifacts could disagree.

    Codex R2-P2 fix: when the dispatcher REFUSES (unsupported backend),
    do NOT persist the BLOCKED gate. Persisting would poison
    `artifacts/solver_gate.json` so every subsequent `cfdtrust report`
    sees a BLOCKED solver gate even though the user later does the
    right thing (`cfdtrust run`). A rejected subcommand must not modify
    the persisted trust state.
    """
    backend = manifest.get("solver_backend")
    if backend != "openfoam":
        # Return-only, no _write_gate — refusal must not mutate state.
        return {
            "status": "BLOCKED",
            "summary": (
                f"`cfdtrust ingest` only supports solver_backend=openfoam; "
                f"manifest declares {backend!r}."
            ),
            "details": {
                "execution": "skipped",
                "real_solver_invoked": False,
                "reason": "ingest_backend_unsupported",
                "next_step": (
                    "Ingest is for cases run by an external OpenFOAM build "
                    "(any fork). For mocked-backend cases there is no real "
                    "evidence to import — use `cfdtrust run` instead."
                ),
            },
        }

    from ..backends.openfoam import ingest as _backend_ingest
    gate = _backend_ingest(case_dir, manifest)
    # Codex R6-P1 fix (tightened by R7-P1 follow-up
    # DEC-V61-201-SUB-INGEST-P1-GUARD-DISCRIMINATE): BLOCKED gates
    # from ingest *preconditions* (no_solver_log_found,
    # case_decomposed_not_reconstructed, solver_log_unreadable,
    # docker_not_available, ...) MUST NOT overwrite
    # `artifacts/solver_gate.json` — every precondition refusal in
    # the backend carries `details.execution == "skipped"`, so we
    # gate on that discriminator instead of bare status==BLOCKED.
    # Otherwise pointing `cfdtrust ingest` at a case that already
    # had a successful `cfdtrust run` would destroy the last good
    # gate and force the next `cfdtrust report` to read the stale
    # ingest-BLOCKED state.
    #
    # Post-residual BLOCKED gates (e.g., no_iterations_in_log,
    # fields_missing_in_log from `_compute_gate_from_residuals`)
    # carry `details.execution == "ingested"` — those ARE real
    # ingested-solver evidence outcomes and MUST be persisted, or
    # `cfdtrust report` falls back to the banner-fallback path in
    # `read_artifacts()` and surfaces the generic ingested-WARN
    # message instead of the actual diagnostic (R7-P1 regression).
    #
    # The success path — PASS / WARN / FAIL solver gates carrying
    # `details.execution="ingested"` from `_compute_gate_from_residuals`
    # — IS persisted. That preserves the M2.3a invariant that
    # `read_artifacts()` reads the SAME truth `execute`/`ingest` saw.
    details = gate.get("details", {}) or {}
    if gate.get("status") == "BLOCKED" and details.get("execution") == "skipped":
        return gate
    return _write_gate(case_dir, gate)
