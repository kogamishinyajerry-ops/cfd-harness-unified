"""Geometry audit gate — M5 (real `geometry_contract` evaluation).

Pre-M5 this module was a Phase-0 MOCKED scaffold. It now reads the truth
source persisted by the OpenFOAM backend (`artifacts/geometry_quality.json`,
written from `constant/polyMesh/boundary` after blockMesh) and evaluates
the manifest's `geometry_contract` against the realized mesh.

Honesty contract (identical posture to M4):
  - We do NOT re-parse `polyMesh/boundary` here. The audit is a pure
    observer of the M5.1-persisted JSON; the boundary file → JSON
    translation happens once in the backend, like checkMesh's output.
  - Missing `geometry_quality.json` after an openfoam run is BLOCKED,
    NOT silently treated as PASS.
  - Missing required patches → FAIL (the case did NOT deliver the
    geometry the manifest promised).
  - Dimensionality mismatch (manifest says 2.5D but no empty patch
    realized, or says 3D but empty patches present) → FAIL.
  - `solver_backend: mocked` still returns MOCKED (Phase-0 honesty rule).

Two evaluation dimensions:
  1. Patch presence — every manifest.geometry_contract.required_patches
     entry must appear in the realized polyMesh/boundary.
  2. Dimensionality — `2.5D` ↔ ≥1 empty patch; `3D` ↔ 0 empty patches.
     The `unit_system` field is informational (OpenFOAM does not encode
     a unit attribute on patches), recorded but not gated.

Overall status = worst of the two (BLOCKED > FAIL > PASS).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..status import ensure_artifacts_dir, mocked_gate, utc_now_iso


_DIMENSIONALITY_EMPTY_REQUIRED = ("2.5D", "2D")  # both treat empty as canonical


def _read_geometry_quality(case_dir: Path) -> Tuple[Dict[str, Any] | None, str | None]:
    p = case_dir / "artifacts" / "geometry_quality.json"
    if not p.exists():
        return None, "geometry_quality_json_missing"
    try:
        return json.loads(p.read_text()), None
    except (OSError, json.JSONDecodeError) as e:
        return None, f"geometry_quality_json_unreadable: {e}"


def _eval_patch_presence(
    realized: Dict[str, Dict[str, Any]],
    required: List[str],
) -> Dict[str, Any]:
    """Compare manifest's required_patches to realized polyMesh patches.

    Returns:
        {
          dimension_status: PASS | FAIL,
          missing: [patch names not in realized],
          present: [patch names found],
          extras: [realized patches NOT in required] (informational only),
        }
    """
    if not required:
        return {
            "dimension_status": "FAIL",
            "missing": [],
            "present": [],
            "extras": sorted(realized.keys()),
            "note": "manifest.geometry_contract.required_patches is empty.",
        }

    realized_names = set(realized.keys())
    required_set = set(required)
    missing = sorted(required_set - realized_names)
    present = sorted(required_set & realized_names)
    extras = sorted(realized_names - required_set)

    return {
        "dimension_status": "FAIL" if missing else "PASS",
        "missing": missing,
        "present": present,
        "extras": extras,
    }


def _eval_dimensionality(
    realized: Dict[str, Dict[str, Any]],
    declared: str | None,
) -> Dict[str, Any]:
    """Check that empty-patch presence matches the manifest's dimensionality.

    OpenFOAM convention:
      - 2.5D / 2D meshes have ≥1 `empty` patch (front+back wedge faces);
      - 3D meshes have 0 `empty` patches.

    Returns dimension_status PASS / FAIL / INCOMPLETE.
    """
    if not declared:
        return {
            "dimension_status": "PASS",
            "declared": None,
            "note": "manifest does not declare dimensionality (nothing to check).",
        }

    empty_patches = sorted(
        n for n, p in realized.items() if p.get("type") == "empty"
    )

    if declared in _DIMENSIONALITY_EMPTY_REQUIRED:
        ok = len(empty_patches) >= 1
        return {
            "dimension_status": "PASS" if ok else "FAIL",
            "declared": declared,
            "empty_patches": empty_patches,
            "reason": None if ok else (
                f"manifest declares {declared!r} but mesh has no empty patch — "
                f"OpenFOAM 2.5D/2D meshes require front+back wedge or empty faces."
            ),
        }

    if declared == "3D":
        ok = len(empty_patches) == 0
        return {
            "dimension_status": "PASS" if ok else "FAIL",
            "declared": declared,
            "empty_patches": empty_patches,
            "reason": None if ok else (
                f"manifest declares '3D' but mesh has empty patches "
                f"{empty_patches} — empty is reserved for 2.5D/2D meshes."
            ),
        }

    # Unknown dimensionality string. Surface as INCOMPLETE; the audit
    # gate's overall status will combine into FAIL (honesty: cannot
    # validate against an unrecognized contract).
    return {
        "dimension_status": "INCOMPLETE",
        "declared": declared,
        "reason": (
            f"manifest declares unrecognized dimensionality {declared!r}; "
            f"recognized values are '2D', '2.5D', '3D'."
        ),
    }


def _combine_dimensions(
    presence: Dict[str, Any],
    dimensionality: Dict[str, Any],
) -> str:
    """Worst-of-two: FAIL > INCOMPLETE > PASS. Honesty: INCOMPLETE rolls
    up to FAIL because we cannot validate what we cannot interpret."""
    statuses = (
        presence.get("dimension_status", "INCOMPLETE"),
        dimensionality.get("dimension_status", "INCOMPLETE"),
    )
    if "FAIL" in statuses:
        return "FAIL"
    if "INCOMPLETE" in statuses:
        return "FAIL"
    return "PASS"


def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate geometry_contract from M5.1-persisted backend artifacts."""
    art = ensure_artifacts_dir(case_dir)
    report_path = art / "geometry_report.json"

    contract = manifest.get("geometry_contract", {}) or {}
    required = contract.get("required_patches", []) or []
    declared_dim = contract.get("dimensionality")

    # Empty contract is itself a manifest defect — flag immediately.
    if not contract or not required:
        gate = {
            "status": "FAIL",
            "summary": "geometry_contract missing or required_patches empty.",
            "details": {"reason": "no_geometry_contract"},
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M5",
            "gate_status": gate["status"],
            "reason": "no_geometry_contract",
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    backend = manifest.get("solver_backend")

    # ----- mocked backend: keep Phase-0 honesty (no blockMesh invoked) -----
    if backend == "mocked":
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M5",
            "gate_status": "MOCKED",
            "polymesh_inspected": False,
            "declared_required_patches": required,
            "declared_dimensionality": declared_dim,
            "notes": [
                "solver_backend=mocked; blockMesh was not invoked.",
                "Geometry cannot be validated without a real backend run.",
            ],
        }
        report_path.write_text(json.dumps(report, indent=2))
        return mocked_gate(
            name="geometry_contract",
            summary=(
                f"Declared {len(required)} required patches; "
                f"no real geometry inspected (solver_backend=mocked)."
            ),
            artifact=str(report_path.relative_to(case_dir)),
        )

    # ----- real backend: read M5.1 persisted truth -----
    geometry_quality, err = _read_geometry_quality(case_dir)
    if geometry_quality is None:
        gate = {
            "status": "BLOCKED",
            "summary": (
                "Geometry evidence missing — blockMesh has not produced "
                "geometry_quality.json yet."
            ),
            "details": {
                "reason": err,
                "expected_artifact": "artifacts/geometry_quality.json",
                "next_step": (
                    "Run `cfdtrust run <case>` with solver_backend=openfoam to "
                    "invoke blockMesh; the geometry parser runs immediately after."
                ),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M5",
            "gate_status": gate["status"],
            "reason": err,
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    if geometry_quality.get("status") == "blocked":
        gate = {
            "status": "BLOCKED",
            "summary": "polyMesh/boundary could not be parsed; cannot evaluate geometry_contract.",
            "details": {
                "reason": geometry_quality.get("reason", "boundary_unparsed"),
                "detail": geometry_quality.get("detail"),
                "boundary_file": geometry_quality.get("boundary_file"),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M5",
            "gate_status": gate["status"],
            "reason": geometry_quality.get("reason", "boundary_unparsed"),
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    realized = geometry_quality.get("patches") or {}

    presence = _eval_patch_presence(realized, required)
    dim_eval = _eval_dimensionality(realized, declared_dim)
    overall = _combine_dimensions(presence, dim_eval)

    # Summary string — keep it scannable in cockpit / CLI output.
    bits: List[str] = []
    if presence["dimension_status"] == "FAIL":
        bits.append(f"presence FAIL (missing: {presence['missing']})")
    else:
        bits.append(f"presence PASS ({len(presence['present'])}/{len(required)})")

    if dim_eval["dimension_status"] == "FAIL":
        bits.append(f"dimensionality FAIL ({dim_eval.get('reason', '?')})")
    elif dim_eval["dimension_status"] == "INCOMPLETE":
        bits.append(f"dimensionality INCOMPLETE ({dim_eval.get('reason', '?')})")
    else:
        bits.append("dimensionality PASS")

    summary = "; ".join(bits) + "."

    report = {
        "generated_at": utc_now_iso(),
        "case_id": manifest.get("case_id"),
        "phase": "M5",
        "gate_status": overall,
        "polymesh_inspected": True,
        "realized_patches": realized,
        "realized_patch_count": len(realized),
        "declared_required_patches": required,
        "declared_dimensionality": declared_dim,
        "presence_dimension": presence,
        "dimensionality_dimension": dim_eval,
        "boundary_file": geometry_quality.get("boundary_file"),
    }
    report_path.write_text(json.dumps(report, indent=2))

    return {
        "status": overall,
        "summary": summary,
        "artifact": str(report_path.relative_to(case_dir)),
        "details": {
            "presence_dimension": presence,
            "dimensionality_dimension": dim_eval,
            "realized_patch_count": len(realized),
            "boundary_file": geometry_quality.get("boundary_file"),
        },
    }
