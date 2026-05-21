"""Mesh audit gate — M4 (real `mesh_contract` evaluation).

Pre-M4 this module was a Phase-0 MOCKED scaffold that only recorded the
declared contract. It now reads the truth-source persisted by the OpenFOAM
backend in M4.1 (`artifacts/mesh_quality.json`, written between blockMesh
and simpleFoam) PLUS the y+ data persisted in the solver gate
(`artifacts/solver_gate.json.details.y_plus`, written from the simpleFoam
log function-object output), and compares both to the manifest's declared
thresholds.

Honesty contract:
  - We do NOT re-run checkMesh here. The audit gate is a pure observer:
    same single-source-of-truth pattern as M2.3a's solver_gate.json.
  - We do NOT silently treat missing artifacts as PASS. Missing
    `mesh_quality.json` after a real openfoam run is BLOCKED, not "ok".
  - We do NOT silently downgrade `quality_thresholds` violations. If
    max_skewness exceeds the manifest's threshold, gate is FAIL even when
    checkMesh's own terminal `Mesh OK.` line was emitted (its OK is purely
    structural; the manifest's quality bar can be stricter).
  - `solver_backend: mocked` cases still return MOCKED, since no checkMesh
    was ever invoked. Phase-0 mocked-execution honesty rule is preserved.

Two evaluation dimensions, scored independently then combined:

  1. Quality dimension — checkMesh numbers vs manifest.mesh_contract.quality_thresholds.
     Static mesh properties; available whenever checkMesh ran successfully.

  2. y+ dimension      — solver_gate.json y+ vs manifest.mesh_contract.y_plus_target.
     Requires a real solver run (y+ is derived from the velocity field);
     absent for mocked or pre-solver runs. Reported as a separate
     dimension so the quality result is never blocked on solver progress.

Overall status is the worst of the two dimensions (BLOCKED > FAIL > PASS).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..status import ensure_artifacts_dir, mocked_gate, utc_now_iso


# Sentinel returned by a dimension that could not be evaluated (e.g. no
# y+ data because the solver hasn't run yet). NOT a failure — surfaced as
# `ok: null` in the report, contributing INCOMPLETE not FAIL.
_DIM_INCOMPLETE = "incomplete"


def _read_mesh_quality(case_dir: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    """Read artifacts/mesh_quality.json. Returns (data, error_reason).

    error_reason is None on success; otherwise a short machine-readable
    reason the caller can surface in the BLOCKED gate.
    """
    p = case_dir / "artifacts" / "mesh_quality.json"
    if not p.exists():
        return None, "mesh_quality_json_missing"
    try:
        return json.loads(p.read_text()), None
    except (OSError, json.JSONDecodeError) as e:
        return None, f"mesh_quality_json_unreadable: {e}"


def _read_solver_y_plus(case_dir: Path) -> Dict[str, Dict[str, float]] | None:
    """Return the y+ map persisted by `backends/openfoam._compute_gate_from_residuals`
    into solver_gate.json (key path: details.y_plus → {patch: {min,max,avg}}).

    Returns None when no solver_gate.json is present OR it is unreadable
    OR it contains no y+ data (e.g. solver hasn't been run yet).
    """
    p = case_dir / "artifacts" / "solver_gate.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    details = data.get("details") or {}
    y_plus = details.get("y_plus")
    if isinstance(y_plus, dict) and y_plus:
        return y_plus
    return None


def _eval_quality_dimension(
    mesh_quality: Dict[str, Any],
    quality_thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare checkMesh numerics to manifest.mesh_contract.quality_thresholds.

    Returns a dict with per-metric `actual`, `threshold`, `ok` and an
    overall `dimension_status` (PASS / FAIL / INCOMPLETE).

    Manifest keys recognized (each optional):
      - max_non_orthogonality
      - max_skewness
      - max_aspect_ratio

    If a threshold is declared but the corresponding checkMesh metric is
    absent (parser gap or checkMesh died mid-run), that metric's `ok` is
    `incomplete` and the dimension is INCOMPLETE (NOT silently passed).
    """
    geometry = mesh_quality.get("geometry") or {}
    metrics: Dict[str, Dict[str, Any]] = {}
    fails: List[str] = []
    incompletes: List[str] = []

    # The threshold key in the manifest is the same string as the
    # geometry-block key we extract in M4.1; no synonym translation needed.
    for metric in ("max_non_orthogonality", "max_skewness", "max_aspect_ratio"):
        if metric not in quality_thresholds:
            continue
        threshold = float(quality_thresholds[metric])
        actual = geometry.get(metric)
        if actual is None:
            metrics[metric] = {
                "actual": None,
                "threshold": threshold,
                "ok": _DIM_INCOMPLETE,
                "reason": "metric_not_in_checkmesh_log",
            }
            incompletes.append(metric)
            continue
        ok = float(actual) <= threshold
        metrics[metric] = {
            "actual": float(actual),
            "threshold": threshold,
            "ok": ok,
        }
        if not ok:
            fails.append(metric)

    if not metrics:
        # Manifest declared no quality thresholds → dimension is N/A.
        return {
            "dimension_status": "PASS",
            "metrics": {},
            "note": "manifest.mesh_contract.quality_thresholds is empty (nothing to check).",
        }

    if fails:
        status = "FAIL"
    elif incompletes:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    return {
        "dimension_status": status,
        "metrics": metrics,
        "fails": fails,
        "incompletes": incompletes,
    }


def _eval_y_plus_dimension(
    y_plus: Dict[str, Dict[str, float]] | None,
    y_plus_target: Dict[str, Any],
    wall_patch_hint: str | None,
) -> Dict[str, Any]:
    """Compare solver's wall y+ to manifest.mesh_contract.y_plus_target.

    `y_plus_target` shape:
        { min: 0.5, max: 5.0, wall_function_policy: "low_re_resolved" }

    `wall_patch_hint` is the manifest's `reference_comparison.wall_patch`
    (already validated against schema regex in M2.3b); we look it up
    directly. If absent OR the patch isn't in the y+ map, we fall back to
    the first patch whose name contains "wall" (case-insensitive).
    """
    if not y_plus_target:
        return {
            "dimension_status": "PASS",
            "patch_evaluated": None,
            "note": "manifest.mesh_contract.y_plus_target is empty (nothing to check).",
        }

    if y_plus is None:
        return {
            "dimension_status": _DIM_INCOMPLETE.upper(),
            "patch_evaluated": None,
            "reason": "no_solver_y_plus_data",
            "next_step": (
                "Run `cfdtrust run <case>` with solver_backend=openfoam so "
                "simpleFoam emits patch y+ via the yPlus function object."
            ),
        }

    # Patch selection
    patch: str | None = None
    if wall_patch_hint and wall_patch_hint in y_plus:
        patch = wall_patch_hint
    else:
        for name in y_plus.keys():
            if "wall" in name.lower():
                patch = name
                break
    if patch is None:
        # We have y+ data but not for any obviously-wall patch.
        return {
            "dimension_status": _DIM_INCOMPLETE.upper(),
            "patch_evaluated": None,
            "available_patches": sorted(y_plus.keys()),
            "wall_patch_hint": wall_patch_hint,
            "reason": "no_wall_patch_in_y_plus_data",
        }

    patch_data = y_plus[patch]
    avg = float(patch_data.get("avg", 0.0))
    p_min = float(patch_data.get("min", 0.0))
    p_max = float(patch_data.get("max", 0.0))

    tgt_min = float(y_plus_target.get("min", 0.0))
    tgt_max = float(y_plus_target.get("max", 1e9))

    # Compare on `avg` — convention used in NASA TMR / wall-function checks.
    # min/max are reported for context but the gate decision is on the average.
    ok = tgt_min <= avg <= tgt_max

    return {
        "dimension_status": "PASS" if ok else "FAIL",
        "patch_evaluated": patch,
        "actual_avg": avg,
        "actual_min": p_min,
        "actual_max": p_max,
        "target_min": tgt_min,
        "target_max": tgt_max,
        "ok": ok,
    }


def _combine_dimensions(
    quality_dim: Dict[str, Any],
    y_plus_dim: Dict[str, Any],
) -> str:
    """Worst-of-two semantics, with INCOMPLETE distinct from FAIL.

    Priority (worst → best): FAIL > BLOCKED > INCOMPLETE > PASS.
    BLOCKED is reserved for the missing-artifact path (handled by the
    caller before this function); here we only see PASS / FAIL / INCOMPLETE.
    """
    statuses = (
        quality_dim.get("dimension_status", "INCOMPLETE"),
        y_plus_dim.get("dimension_status", "INCOMPLETE"),
    )
    if "FAIL" in statuses:
        return "FAIL"
    if "INCOMPLETE" in statuses:
        # Honesty: if ANY dimension is incomplete, the overall gate is
        # not PASS. We surface it as FAIL because the harness cannot
        # validate what it cannot measure.
        return "FAIL"
    return "PASS"


def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate mesh_contract from persisted backend artifacts.

    Returns one of:
      MOCKED  — solver_backend is mocked; checkMesh was never invoked.
      BLOCKED — backend is openfoam but mesh_quality.json is missing /
                unreadable / shows checkMesh blocked (OSError or timeout).
      FAIL    — quality thresholds exceeded OR y+ outside target OR
                incomplete data (manifest declared a metric that the
                artifacts don't expose).
      PASS    — both dimensions pass against the manifest's declared
                thresholds.
    """
    art = ensure_artifacts_dir(case_dir)
    report_path = art / "mesh_report.json"

    contract = manifest.get("mesh_contract", {}) or {}
    if not contract:
        gate = {
            "status": "FAIL",
            "summary": "mesh_contract missing from manifest.",
            "details": {"reason": "no_mesh_contract"},
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M4",
            "gate_status": gate["status"],
            "reason": "no_mesh_contract",
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    backend = manifest.get("solver_backend")

    # ----- mocked backend: keep Phase-0 honesty (no checkMesh invoked) -----
    if backend == "mocked":
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M4",
            "gate_status": "MOCKED",
            "checkmesh_invoked": False,
            "declared_contract": contract,
            "notes": [
                "solver_backend=mocked; checkMesh was not invoked.",
                "Mesh quality cannot be validated without a real backend run.",
            ],
        }
        report_path.write_text(json.dumps(report, indent=2))
        return mocked_gate(
            name="mesh_contract",
            summary="Mesh contract recorded; checkMesh not run (solver_backend=mocked).",
            artifact=str(report_path.relative_to(case_dir)),
        )

    # ----- real backend: read M4.1 persisted truth -----
    mesh_quality, err = _read_mesh_quality(case_dir)
    if mesh_quality is None:
        gate = {
            "status": "BLOCKED",
            "summary": "Mesh evidence missing — checkMesh has not produced mesh_quality.json yet.",
            "details": {
                "reason": err,
                "expected_artifact": "artifacts/mesh_quality.json",
                "next_step": (
                    "Run `cfdtrust run <case>` with solver_backend=openfoam to "
                    "invoke blockMesh + checkMesh + simpleFoam in sequence."
                ),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M4",
            "gate_status": gate["status"],
            "reason": err,
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    # If M4.1 persisted a `blocked` status (OSError / timeout / etc.),
    # propagate that directly. Pre-fix this would have silently fallen
    # through to "no metrics to compare" → PASS.
    cm_status = mesh_quality.get("checkmesh_status")
    if cm_status == "blocked":
        gate = {
            "status": "BLOCKED",
            "summary": (
                "checkMesh did not complete; cannot evaluate mesh_contract."
            ),
            "details": {
                "reason": mesh_quality.get("reason", "checkmesh_blocked"),
                "detail": mesh_quality.get("detail"),
                "checkmesh_returncode": mesh_quality.get("checkmesh_returncode"),
                "log": mesh_quality.get("log"),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M4",
            "gate_status": gate["status"],
            "reason": mesh_quality.get("reason", "checkmesh_blocked"),
            "checkmesh_log": mesh_quality.get("log"),
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    # ----- per-dimension evaluation -----
    quality_thresholds = contract.get("quality_thresholds") or {}
    quality_dim = _eval_quality_dimension(mesh_quality, quality_thresholds)

    y_plus_target = contract.get("y_plus_target") or {}
    solver_y_plus = _read_solver_y_plus(case_dir)
    # The wall patch hint: reference_comparison.wall_patch (M2.3b schema field).
    ref = manifest.get("reference_comparison") or {}
    wall_patch_hint = ref.get("wall_patch") if isinstance(ref, dict) else None
    y_plus_dim = _eval_y_plus_dimension(solver_y_plus, y_plus_target, wall_patch_hint)

    overall = _combine_dimensions(quality_dim, y_plus_dim)

    # If checkMesh itself reported `Failed N mesh checks.`, that's a FAIL
    # regardless of whether the manifest-thresholded numerics happened to
    # fit (because checkMesh found something outside our threshold list,
    # like non-closed boundaries or face-pyramid errors).
    if not mesh_quality.get("overall_mesh_ok", True):
        overall = "FAIL"

    summary_bits: List[str] = []
    if quality_dim.get("dimension_status") == "FAIL":
        bad = quality_dim.get("fails", [])
        summary_bits.append(f"quality FAIL on {bad}")
    elif quality_dim.get("dimension_status") == "INCOMPLETE":
        summary_bits.append("quality INCOMPLETE (parser gap)")
    else:
        summary_bits.append("quality PASS")

    if y_plus_dim.get("dimension_status") == "FAIL":
        summary_bits.append(
            f"y+ FAIL ({y_plus_dim.get('patch_evaluated')} avg="
            f"{y_plus_dim.get('actual_avg')} outside "
            f"[{y_plus_dim.get('target_min')}, {y_plus_dim.get('target_max')}])"
        )
    elif y_plus_dim.get("dimension_status") == "INCOMPLETE":
        summary_bits.append(f"y+ INCOMPLETE ({y_plus_dim.get('reason', '?')})")
    else:
        summary_bits.append("y+ PASS")

    summary = "; ".join(summary_bits) + "."

    report = {
        "generated_at": utc_now_iso(),
        "case_id": manifest.get("case_id"),
        "phase": "M4",
        "gate_status": overall,
        "checkmesh_invoked": True,
        "checkmesh_overall_ok": mesh_quality.get("overall_mesh_ok"),
        "checkmesh_failed_count": mesh_quality.get("failed_checks_count", 0),
        "stats": mesh_quality.get("stats", {}),
        "quality_dimension": quality_dim,
        "y_plus_dimension": y_plus_dim,
        "declared_contract": contract,
        "checkmesh_log": mesh_quality.get("log"),
    }
    report_path.write_text(json.dumps(report, indent=2))

    return {
        "status": overall,
        "summary": summary,
        "artifact": str(report_path.relative_to(case_dir)),
        "details": {
            "quality_dimension": quality_dim,
            "y_plus_dimension": y_plus_dim,
            "checkmesh_overall_ok": mesh_quality.get("overall_mesh_ok"),
            "checkmesh_log": mesh_quality.get("log"),
        },
    }
