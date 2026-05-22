"""Boundary-condition audit gate — M6 + M7 (real `bc_contract` evaluation).

M7 adds the fourth dimension `value_match` on top of M6's three. The
backend (M7.1 in `backends/openfoam.py`) extracts `value` (scalar or
vector) and whitelisted scalar params (`intensity`, `mixingLength`) per
patch; this audit compares them to the manifest's numeric declarations
within tolerance.

Pre-M6 this module was a Phase-0 MOCKED scaffold. It now reads the truth
sources persisted by the OpenFOAM backend in M5.1 (`geometry_quality.json`)
and M6.1 / M7.1 (`bc_quality.json`) and evaluates the manifest's
`bc_contract` against the realized 0/<field> dictionaries.

Honesty contract (identical to M4 / M5):
  - We do NOT re-parse 0/<field> files here. Backend persists; audit reads.
  - We do NOT silently treat missing artifacts as PASS.
  - We do NOT downgrade a missing field file ("nut" declared in
    turbulence_fields but no 0/nut on disk) to a soft warning — that's
    FAIL.
  - `solver_backend: mocked` still returns MOCKED (Phase-0 honesty rule).

Three evaluation dimensions, combined worst-of:

  1. **File presence** — every expected field file (`U`, `p`, plus each
     entry in `bc_contract.turbulence_fields`) must be present in `0/`
     and parseable. Missing or unparseable → FAIL.

  2. **Patch coverage** — every realized polyMesh patch (from
     `geometry_quality.json`) must have a BC entry in EVERY parseable
     field file. A solver run with missing patch BCs in one field would
     fail at simpleFoam time; the audit catches it pre-run.

  3. **BC type match** — for each (manifest_key, field_class) explicitly
     declared in `bc_contract`:
       - Resolve `manifest_key`: literal polyMesh patch name → just that
         patch; otherwise treat as a polyMesh patch TYPE (e.g. `wall`)
         and expand to all realized patches of that type.
       - Map `field_class` to the field file (velocity→U, pressure→p,
         else identity).
       - Each resolved (patch, file) pair's realized type MUST equal
         the manifest-declared type. Mismatch → FAIL.

Worst-of-three combine: FAIL > INCOMPLETE > PASS. INCOMPLETE rolls up to
FAIL (cannot validate what we cannot interpret).

The geometry-quality cross-artifact dependency is the first such check
in the harness; the failure mode is "geometry_quality.json missing or
unreadable" → BC audit cannot do the patch-coverage / type-match checks
(both depend on knowing the realized polyMesh patch list and types). In
that case we BLOCK with `geometry_evidence_missing` so the operator
knows the chain stops at the upstream gate.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..status import ensure_artifacts_dir, mocked_gate, utc_now_iso


# Manifest BC field-class → 0/<file> name mapping. Anything not listed
# maps to itself (k → k, omega → omega, nut → nut, epsilon → epsilon).
_FIELD_CLASS_TO_FILE: Dict[str, str] = {
    "velocity": "U",
    "pressure": "p",
}

# Reserved manifest keys under `bc_contract` that are NOT per-patch sections.
_NON_PATCH_BC_KEYS = {"turbulence_fields"}


def _field_class_to_file(field_class: str) -> str:
    return _FIELD_CLASS_TO_FILE.get(field_class, field_class)


def _read_json(case_dir: Path, fname: str) -> Tuple[Dict[str, Any] | None, str | None]:
    p = case_dir / "artifacts" / fname
    if not p.exists():
        return None, f"{fname}_missing"
    try:
        return json.loads(p.read_text()), None
    except (OSError, json.JSONDecodeError) as e:
        return None, f"{fname}_unreadable: {e}"


def _eval_file_presence(
    bc_quality: Dict[str, Any],
    expected_fields: List[str],
) -> Dict[str, Any]:
    """Every entry in `expected_fields` (U + p + turbulence_fields) must
    be parsed=True in bc_quality. Missing or parse_error → FAIL."""
    fields_data = bc_quality.get("fields") or {}
    present: List[str] = []
    missing: List[str] = []
    unparseable: List[Dict[str, Any]] = []
    for fname in expected_fields:
        fdata = fields_data.get(fname, {})
        if fdata.get("parsed"):
            present.append(fname)
        elif fdata.get("missing"):
            missing.append(fname)
        else:
            # File exists but parser couldn't extract a boundaryField, OR
            # an OSError happened on read.
            unparseable.append({
                "field": fname,
                "reason": fdata.get("parse_error") or fdata.get("read_error") or "unknown",
            })

    status = "PASS" if (not missing and not unparseable) else "FAIL"
    return {
        "dimension_status": status,
        "present": sorted(present),
        "missing_files": sorted(missing),
        "unparseable_files": unparseable,
    }


def _eval_patch_coverage(
    bc_quality: Dict[str, Any],
    realized_polymesh_patches: List[str],
) -> Dict[str, Any]:
    """For every parsed field file, every polyMesh patch must have a BC
    entry. Missing patches in one or more files → FAIL with a per-field
    breakdown so the cockpit can surface exactly which patches are
    unmapped."""
    fields_data = bc_quality.get("fields") or {}
    polymesh_set = set(realized_polymesh_patches)
    gaps: Dict[str, List[str]] = {}
    checked_fields: List[str] = []
    for fname, fdata in fields_data.items():
        if not fdata.get("parsed"):
            continue
        checked_fields.append(fname)
        realized_patches = set((fdata.get("patches") or {}).keys())
        missing = sorted(polymesh_set - realized_patches)
        if missing:
            gaps[fname] = missing

    if not realized_polymesh_patches:
        return {
            "dimension_status": "INCOMPLETE",
            "reason": "no_polymesh_patches",
            "checked_fields": sorted(checked_fields),
        }

    if not checked_fields:
        return {
            "dimension_status": "INCOMPLETE",
            "reason": "no_parsed_field_files",
            "checked_fields": [],
        }

    return {
        "dimension_status": "FAIL" if gaps else "PASS",
        "checked_fields": sorted(checked_fields),
        "polymesh_patch_count": len(realized_polymesh_patches),
        "gaps_by_field": gaps,
    }


def _resolve_manifest_key(
    key: str,
    realized_patches: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Manifest BC keys mean either a literal patch name or a patch-type
    class. Literal wins if the key matches a realized patch name exactly;
    otherwise expand to all realized patches whose `type` equals the key.

    Returns the (possibly empty) list of resolved realized patch names.
    """
    if key in realized_patches:
        return [key]
    matches = sorted(
        n for n, p in realized_patches.items() if p.get("type") == key
    )
    return matches


def _eval_type_match(
    bc_contract: Dict[str, Any],
    bc_quality: Dict[str, Any],
    realized_polymesh: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """For each manifest (key, field_class) declaration, verify realized
    BC type matches. Surfaces three classes of issue:

      - `unresolvable_keys`: manifest key matches no realized patch name
        AND no realized patch type. Manifest/case drift — FAIL.
      - `field_class_missing_in_bc_quality`: declared field has no parsed
        BC file. Already caught by file_presence dim, but recorded here
        for the type-match-specific breakdown.
      - `type_mismatches`: realized type != declared type.

    Empty manifest declarations are PASS (nothing to check).
    """
    fields_data = bc_quality.get("fields") or {}

    unresolvable_keys: List[str] = []
    field_class_missing: List[Dict[str, Any]] = []
    type_mismatches: List[Dict[str, Any]] = []
    checked: List[Dict[str, Any]] = []

    for key, key_block in bc_contract.items():
        if key in _NON_PATCH_BC_KEYS:
            continue
        if not isinstance(key_block, dict):
            continue
        resolved = _resolve_manifest_key(key, realized_polymesh)
        if not resolved:
            unresolvable_keys.append(key)
            continue

        for field_class, field_block in key_block.items():
            if not isinstance(field_block, dict):
                continue
            declared_type = field_block.get("type")
            if declared_type is None:
                continue
            file_name = _field_class_to_file(field_class)
            fdata = fields_data.get(file_name) or {}
            if not fdata.get("parsed"):
                field_class_missing.append({
                    "manifest_key": key,
                    "field_class": field_class,
                    "expected_file": f"0/{file_name}",
                })
                continue
            field_patches = fdata.get("patches") or {}
            for patch in resolved:
                realized_entry = field_patches.get(patch)
                if realized_entry is None:
                    type_mismatches.append({
                        "manifest_key": key,
                        "resolved_patch": patch,
                        "field": file_name,
                        "declared_type": declared_type,
                        "realized_type": None,
                        "reason": "patch_not_in_field_file",
                    })
                    continue
                realized_type = realized_entry.get("type")
                checked.append({
                    "manifest_key": key,
                    "resolved_patch": patch,
                    "field": file_name,
                    "declared_type": declared_type,
                    "realized_type": realized_type,
                })
                if realized_type != declared_type:
                    type_mismatches.append({
                        "manifest_key": key,
                        "resolved_patch": patch,
                        "field": file_name,
                        "declared_type": declared_type,
                        "realized_type": realized_type,
                    })

    if not checked and not unresolvable_keys and not field_class_missing and not type_mismatches:
        return {
            "dimension_status": "PASS",
            "checked": [],
            "note": "manifest.bc_contract has no per-patch type declarations.",
        }

    failed = bool(unresolvable_keys or type_mismatches)
    incomplete = bool(field_class_missing) and not failed
    if failed:
        status = "FAIL"
    elif incomplete:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    return {
        "dimension_status": status,
        "checked_count": len(checked),
        "unresolvable_keys": sorted(unresolvable_keys),
        "field_class_missing": field_class_missing,
        "type_mismatches": type_mismatches,
        "checked": checked,
    }


# M7.2: manifest numeric field → realized lookup spec.
# Each entry: (realized_lookup_kind, default_rtol, default_atol).
#   - "vector_magnitude":  L2 norm of realized.value_vector (vector field)
#   - "value_scalar":       realized.value_scalar (scalar field)
#   - "param":              realized.params[<manifest_field>]
#
# rtol / atol are conservative defaults; both compared via
# math.isclose(actual, declared, rel_tol=rtol, abs_tol=atol). atol is set
# so a declared 0.0 reference doesn't divide-by-zero into FAIL via rtol.
_NUMERIC_FIELD_SPEC: Dict[str, Tuple[str, float, float]] = {
    "magnitude_m_s": ("vector_magnitude", 1e-6, 1e-9),
    "value_Pa":      ("value_scalar",     1e-6, 1e-9),
    "intensity":     ("param",            1e-6, 1e-12),
    "mixingLength":  ("param",            1e-6, 1e-12),
}


def _close(actual: float, declared: float, *, rel_tol: float, abs_tol: float) -> bool:
    """math.isclose wrapper; centralizes the FP comparison policy."""
    try:
        return math.isclose(actual, declared, rel_tol=rel_tol, abs_tol=abs_tol)
    except (TypeError, ValueError):
        return False


def _eval_value_match(
    bc_contract: Dict[str, Any],
    bc_quality: Dict[str, Any],
    realized_polymesh: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """For each manifest declaration with a recognized numeric field
    (`magnitude_m_s`, `value_Pa`, `intensity`, `mixingLength`), look up
    the realized BC's corresponding numeric and compare within tolerance.

    Surfaces three classes of issue:
      - `value_mismatches`: realized number ≠ declared number (FAIL).
      - `value_missing`: declared a numeric field but realized BC has
        no corresponding value/param (e.g. manifest says
        `magnitude_m_s: 44.2` but realized has no `value_vector`). FAIL.
      - `numeric_field_unknown` (informational): manifest contains a
        numeric key the audit does not know how to compare. Currently
        recorded but does NOT fail — extension surface, not a defect.

    PASS when every recognized numeric declaration matches realized
    within tolerance.
    """
    fields_data = bc_quality.get("fields") or {}

    matched: List[Dict[str, Any]] = []
    value_mismatches: List[Dict[str, Any]] = []
    value_missing: List[Dict[str, Any]] = []
    numeric_field_unknown: List[Dict[str, Any]] = []

    for key, key_block in bc_contract.items():
        if key in _NON_PATCH_BC_KEYS:
            continue
        if not isinstance(key_block, dict):
            continue
        resolved = _resolve_manifest_key(key, realized_polymesh)
        if not resolved:
            # Already a FAIL in type_match dim; the value_match dim
            # silently skips so we don't double-count.
            continue
        for field_class, field_block in key_block.items():
            if not isinstance(field_block, dict):
                continue
            file_name = _field_class_to_file(field_class)
            fdata = fields_data.get(file_name) or {}
            if not fdata.get("parsed"):
                # Already FAIL in file_presence / type_match.
                continue
            field_patches = fdata.get("patches") or {}

            for numeric_field, declared in field_block.items():
                if numeric_field == "type":
                    continue
                if not isinstance(declared, (int, float)):
                    # Could be a unit string, an enum, etc. Not in scope.
                    continue
                spec = _NUMERIC_FIELD_SPEC.get(numeric_field)
                if spec is None:
                    numeric_field_unknown.append({
                        "manifest_key": key,
                        "field_class": field_class,
                        "numeric_field": numeric_field,
                        "declared": float(declared),
                    })
                    continue
                lookup_kind, rtol, atol = spec
                declared_f = float(declared)

                for patch in resolved:
                    realized = field_patches.get(patch)
                    if realized is None:
                        # Already FAIL in patch_coverage / type_match.
                        continue
                    actual: float | None = None
                    if lookup_kind == "vector_magnitude":
                        vec = realized.get("value_vector")
                        if isinstance(vec, list) and len(vec) == 3:
                            try:
                                actual = math.sqrt(
                                    float(vec[0]) ** 2
                                    + float(vec[1]) ** 2
                                    + float(vec[2]) ** 2
                                )
                            except (TypeError, ValueError):
                                actual = None
                    elif lookup_kind == "value_scalar":
                        v = realized.get("value_scalar")
                        if isinstance(v, (int, float)):
                            actual = float(v)
                    elif lookup_kind == "param":
                        params = realized.get("params") or {}
                        v = params.get(numeric_field)
                        if isinstance(v, (int, float)):
                            actual = float(v)

                    if actual is None:
                        value_missing.append({
                            "manifest_key": key,
                            "resolved_patch": patch,
                            "field": file_name,
                            "field_class": field_class,
                            "numeric_field": numeric_field,
                            "declared": declared_f,
                            "lookup_kind": lookup_kind,
                            "reason": "no_realized_value",
                        })
                        continue

                    ok = _close(actual, declared_f, rel_tol=rtol, abs_tol=atol)
                    record = {
                        "manifest_key": key,
                        "resolved_patch": patch,
                        "field": file_name,
                        "field_class": field_class,
                        "numeric_field": numeric_field,
                        "declared": declared_f,
                        "actual": actual,
                        "lookup_kind": lookup_kind,
                        "rel_tol": rtol,
                        "abs_tol": atol,
                    }
                    if ok:
                        matched.append(record)
                    else:
                        value_mismatches.append(record)

    if not matched and not value_mismatches and not value_missing and not numeric_field_unknown:
        return {
            "dimension_status": "PASS",
            "matched": [],
            "note": "manifest.bc_contract has no recognized numeric declarations.",
        }

    if value_mismatches or value_missing:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "dimension_status": status,
        "matched_count": len(matched),
        "value_mismatches": value_mismatches,
        "value_missing": value_missing,
        "numeric_field_unknown": numeric_field_unknown,
        # Keep the matched list short-tailed for cockpit display.
        "matched": matched,
    }


# M8: derived turbulent-quantity tolerances.
#
# Both BFS and flat_plate carry human-edited 0/ files where the operator
# wrote `value uniform 779` instead of the math-exact `778.2221`. That's
# a 0.1% rounding gap that should NOT be a FAIL — but a 10% gap would
# indicate a real BC/manifest drift (e.g. user used a different velocity
# in the derivation).
#
# Default rtol=5e-3 (0.5%) accepts realistic human rounding; tightens
# from the 1e-6 used in `_NUMERIC_FIELD_SPEC` (M7) precisely because the
# derived check spans formula → human-typed file (lossy) rather than
# manifest → realized (exact). atol guards near-zero.
_DERIVED_REL_TOL = 5e-3
_DERIVED_ABS_TOL = 1e-9

# Standard k-omega closure constant. Hard-coded because every k-omega
# SST manifest uses this convention; a manifest-level override would
# only confuse the audit.
_K_OMEGA_CMU = 0.09


def _eval_derived_consistency(
    bc_contract: Dict[str, Any],
    bc_quality: Dict[str, Any],
    realized_polymesh: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Verify k = 1.5 * (I * U)^2 and omega = sqrt(k) / (Cmu^0.25 * L)
    derivations against realized values at the same patch.

    Only the inlet patches matter — these are the only ones where the
    manifest declares `velocity.magnitude_m_s` AND `k.intensity` (and
    optionally `omega.mixingLength`). Wall patches use wall functions
    which don't have a closed-form derived value (the solver computes
    them from the local U_tau).

    Per-patch logic (skipping silently when prerequisites absent):
      1. If patch declares velocity.magnitude_m_s + k.intensity:
         expected_k = 1.5 * (I * U)^2
         compare to realized k value_scalar
      2. If step 1 fired AND patch declares omega.mixingLength:
         expected_omega = sqrt(expected_k) / (Cmu^0.25 * L)
         compare to realized omega value_scalar

    A FAIL surfaces specifically as `derived_mismatches`, distinguishing
    derivation drift from raw value drift (which the value_match dim
    already catches).
    """
    fields_data = bc_quality.get("fields") or {}

    matched: List[Dict[str, Any]] = []
    derived_mismatches: List[Dict[str, Any]] = []
    derived_missing: List[Dict[str, Any]] = []

    for key, key_block in bc_contract.items():
        if key in _NON_PATCH_BC_KEYS:
            continue
        if not isinstance(key_block, dict):
            continue
        velocity_block = key_block.get("velocity") if isinstance(key_block.get("velocity"), dict) else None
        k_block = key_block.get("k") if isinstance(key_block.get("k"), dict) else None
        omega_block = key_block.get("omega") if isinstance(key_block.get("omega"), dict) else None
        if not velocity_block or not k_block:
            # Need both U and intensity to derive k.
            continue
        U = velocity_block.get("magnitude_m_s")
        I = k_block.get("intensity")
        if not isinstance(U, (int, float)) or not isinstance(I, (int, float)):
            continue
        U_f = float(U)
        I_f = float(I)
        expected_k = 1.5 * (I_f * U_f) ** 2

        resolved = _resolve_manifest_key(key, realized_polymesh)
        if not resolved:
            continue

        k_field = fields_data.get("k") or {}
        if not k_field.get("parsed"):
            continue
        k_patches = k_field.get("patches") or {}

        for patch in resolved:
            realized_k = k_patches.get(patch, {})
            actual_k = realized_k.get("value_scalar")
            if not isinstance(actual_k, (int, float)):
                derived_missing.append({
                    "manifest_key": key,
                    "resolved_patch": patch,
                    "derivation": "k_from_I_U",
                    "expected": expected_k,
                    "reason": "no_realized_k_value_scalar",
                })
                continue
            actual_k_f = float(actual_k)
            ok = _close(actual_k_f, expected_k, rel_tol=_DERIVED_REL_TOL, abs_tol=_DERIVED_ABS_TOL)
            record = {
                "manifest_key": key,
                "resolved_patch": patch,
                "derivation": "k_from_I_U",
                "formula": "1.5 * (intensity * magnitude_m_s)^2",
                "inputs": {"intensity": I_f, "magnitude_m_s": U_f},
                "expected": expected_k,
                "actual": actual_k_f,
                "rel_tol": _DERIVED_REL_TOL,
                "abs_tol": _DERIVED_ABS_TOL,
            }
            if ok:
                matched.append(record)
            else:
                derived_mismatches.append(record)

            # If omega data is declared, chain-derive expected omega from
            # the EXPECTED k (NOT the realized k) — we want to know if
            # the user's manifest values are internally consistent.
            if omega_block is None:
                continue
            L = omega_block.get("mixingLength")
            if not isinstance(L, (int, float)) or float(L) <= 0:
                continue
            L_f = float(L)
            if expected_k < 0:
                continue
            expected_omega = (expected_k ** 0.5) / (_K_OMEGA_CMU ** 0.25 * L_f)
            omega_field = fields_data.get("omega") or {}
            if not omega_field.get("parsed"):
                continue
            omega_patches = omega_field.get("patches") or {}
            realized_omega = omega_patches.get(patch, {})
            actual_omega = realized_omega.get("value_scalar")
            if not isinstance(actual_omega, (int, float)):
                derived_missing.append({
                    "manifest_key": key,
                    "resolved_patch": patch,
                    "derivation": "omega_from_k_L",
                    "expected": expected_omega,
                    "reason": "no_realized_omega_value_scalar",
                })
                continue
            actual_omega_f = float(actual_omega)
            ok_om = _close(
                actual_omega_f, expected_omega,
                rel_tol=_DERIVED_REL_TOL, abs_tol=_DERIVED_ABS_TOL,
            )
            record_om = {
                "manifest_key": key,
                "resolved_patch": patch,
                "derivation": "omega_from_k_L",
                "formula": "sqrt(k_expected) / (Cmu^0.25 * mixingLength)",
                "inputs": {
                    "intensity": I_f,
                    "magnitude_m_s": U_f,
                    "mixingLength": L_f,
                    "Cmu": _K_OMEGA_CMU,
                    "k_expected": expected_k,
                },
                "expected": expected_omega,
                "actual": actual_omega_f,
                "rel_tol": _DERIVED_REL_TOL,
                "abs_tol": _DERIVED_ABS_TOL,
            }
            if ok_om:
                matched.append(record_om)
            else:
                derived_mismatches.append(record_om)

    if not matched and not derived_mismatches and not derived_missing:
        return {
            "dimension_status": "PASS",
            "matched_count": 0,
            "note": "no patch declares both magnitude_m_s + intensity (no derivation possible).",
        }

    status = "FAIL" if (derived_mismatches or derived_missing) else "PASS"
    return {
        "dimension_status": status,
        "matched_count": len(matched),
        "matched": matched,
        "derived_mismatches": derived_mismatches,
        "derived_missing": derived_missing,
    }


def _combine_dimensions(
    file_presence: Dict[str, Any],
    patch_coverage: Dict[str, Any],
    type_match: Dict[str, Any],
    value_match: Dict[str, Any] | None = None,
    derived: Dict[str, Any] | None = None,
) -> str:
    """Worst-of-N combine. INCOMPLETE rolls up to FAIL."""
    statuses = [
        file_presence.get("dimension_status", "INCOMPLETE"),
        patch_coverage.get("dimension_status", "INCOMPLETE"),
        type_match.get("dimension_status", "INCOMPLETE"),
    ]
    if value_match is not None:
        statuses.append(value_match.get("dimension_status", "INCOMPLETE"))
    if derived is not None:
        statuses.append(derived.get("dimension_status", "INCOMPLETE"))
    if "FAIL" in statuses:
        return "FAIL"
    if "INCOMPLETE" in statuses:
        return "FAIL"
    return "PASS"


def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate bc_contract from M5.1 + M6.1 persisted artifacts."""
    art = ensure_artifacts_dir(case_dir)
    report_path = art / "bc_audit.json"

    contract = manifest.get("bc_contract", {}) or {}
    if not contract:
        gate = {
            "status": "FAIL",
            "summary": "bc_contract missing from manifest.",
            "details": {"reason": "no_bc_contract"},
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": gate["status"],
            "reason": "no_bc_contract",
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    backend = manifest.get("solver_backend")

    # ----- mocked backend: keep Phase-0 honesty -----
    if backend == "mocked":
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": "MOCKED",
            "zero_dir_inspected": False,
            "declared_sections": {k: contract.get(k) for k in contract},
            "notes": [
                "solver_backend=mocked; 0/ files were not parsed by the backend.",
                "BC validation requires a real-backend run.",
            ],
        }
        report_path.write_text(json.dumps(report, indent=2))
        return mocked_gate(
            name="bc_contract",
            summary="BC contract recorded; 0/ not inspected (solver_backend=mocked).",
            artifact=str(report_path.relative_to(case_dir)),
        )

    # ----- real backend: read M6.1 + M5.1 persisted truth -----
    bc_quality, err = _read_json(case_dir, "bc_quality.json")
    if bc_quality is None:
        gate = {
            "status": "BLOCKED",
            "summary": "BC evidence missing — bc_quality.json has not been written yet.",
            "details": {
                "reason": err,
                "expected_artifact": "artifacts/bc_quality.json",
                "next_step": (
                    "Run `cfdtrust run <case>` with solver_backend=openfoam to "
                    "trigger the 0/ parser."
                ),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": gate["status"],
            "reason": err,
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    if bc_quality.get("bc_parsing_status") == "blocked":
        gate = {
            "status": "BLOCKED",
            "summary": "0/ parsing was blocked; cannot evaluate bc_contract.",
            "details": {
                "reason": bc_quality.get("reason", "bc_parsing_blocked"),
                "detail": bc_quality.get("detail"),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": gate["status"],
            "reason": bc_quality.get("reason"),
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    # Multi-region wiring (DEC-V61-201-SUB-INGEST-MULTI-REGION-BC
    # cycle-4 follow-up): chtMultiRegionFoam cases place per-region
    # fields under `0/region_<name>/<field>`. The cycle-1 data layer
    # surfaced this in bc_quality.json with `layout: "multi_region"`
    # + per-region sub-dicts. The cycle-1 verdict layer BLOCKED with
    # `multi_region_bc_validation_not_yet_wired` — honest but
    # pessimistic, since the parser already has enough evidence to
    # render a verdict that does NOT depend on per-region per-class
    # expected-field schema (Gap #28 charter, still queued).
    #
    # Wiring (this cycle): emit a real verdict using region-shape
    # classification + manifest fluid-expected-field coverage check.
    # The verdict does NOT claim per-class accuracy (e.g. solid region
    # legitimately missing U/p is reported in per-region detail but
    # does NOT cause top-level FAIL). What it CAN claim:
    #
    #   - Every detected region has ≥1 parseable field (no empty regions)
    #   - At least one fluid region exists (U + p both present)
    #   - Every manifest-declared fluid expected field is present in
    #     at least one fluid region
    #
    # When all three hold → PASS with `multi_region_per_class_pending`
    # caveat. Otherwise → WARN or BLOCKED with the specific failed check.
    # Per-class verdict refinement (solid wants T-only, fluid wants
    # U/p/turbulence/thermal) is deferred to Gap #28 charter.
    if bc_quality.get("layout") == "multi_region":
        regions_dict = bc_quality.get("regions", {}) or {}
        per_region_summary: Dict[str, Dict[str, List[str]]] = {}
        empty_regions: List[str] = []
        fluid_regions: List[str] = []
        solid_regions: List[str] = []
        for rname, rdata in regions_dict.items():
            present = list(rdata.get("fields_present", []))
            missing = list(rdata.get("fields_missing", []))
            per_region_summary[rname] = {
                "fields_present": present,
                "fields_missing": missing,
            }
            if not present:
                empty_regions.append(rname)
            elif "U" in present and "p" in present:
                fluid_regions.append(rname)
            else:
                solid_regions.append(rname)

        # Manifest-declared expected fluid fields (U, p + turbulence_fields
        # + thermal_fields). Per the cycle-3 charter, turbulence_fields
        # can be empty for laminar declarations; thermal_fields can be
        # absent for incompressible. Default expected fluid set is just
        # U + p when both are empty.
        bc_contract_manifest = manifest.get("bc_contract", {}) or {}
        manifest_turb = list(bc_contract_manifest.get("turbulence_fields", []) or [])
        manifest_thermal = list(bc_contract_manifest.get("thermal_fields", []) or [])
        # Apply the same sentinel filter the backend uses.
        manifest_turb = [
            f for f in manifest_turb
            if not (isinstance(f, str) and f.startswith("__") and f.endswith("__"))
        ]
        manifest_thermal = [
            f for f in manifest_thermal
            if not (isinstance(f, str) and f.startswith("__") and f.endswith("__"))
        ]
        expected_fluid_fields = ["U", "p", *manifest_turb, *manifest_thermal]
        seen: set = set()
        expected_fluid_fields = [
            f for f in expected_fluid_fields if not (f in seen or seen.add(f))
        ]
        # Union of fields present across ALL fluid regions — any single
        # region carrying the field counts (a CHT case might split U/p
        # across hot/cold fluid regions; both are valid evidence).
        fluid_fields_union: set = set()
        for rname in fluid_regions:
            fluid_fields_union.update(per_region_summary[rname]["fields_present"])
        missing_in_all_fluid = [
            f for f in expected_fluid_fields if f not in fluid_fields_union
        ]

        # Verdict computation.
        if empty_regions:
            status = "BLOCKED"
            reason = "multi_region_empty_region_detected"
            summary = (
                f"Multi-region CHT layout detected with {len(empty_regions)} "
                f"empty region(s) (no parseable field files): "
                f"{sorted(empty_regions)}."
            )
            next_step = (
                "Verify each detected region directory contains at least "
                "one OpenFOAM field file (U, p, T, k, omega, etc.). Empty "
                "regions indicate either case staging error or premature "
                "ingest before Allrun-Pre."
            )
        elif not fluid_regions:
            status = "BLOCKED"
            reason = "multi_region_no_fluid_region"
            summary = (
                "Multi-region CHT layout detected with zero fluid regions "
                "(no region carries both U and p). Case cannot run without "
                "at least one fluid region."
            )
            next_step = (
                "Verify at least one detected region declares U and p (the "
                "fluid-region signature). chtMultiRegionFoam always requires "
                "≥1 fluid region by definition."
            )
        elif missing_in_all_fluid:
            status = "WARN"
            reason = "multi_region_fluid_field_missing"
            summary = (
                f"Multi-region CHT layout: {len(fluid_regions)} fluid "
                f"region(s) detected, but expected fluid fields "
                f"{missing_in_all_fluid} not present in any fluid region. "
                f"Solid region count: {len(solid_regions)}. Per-class "
                f"verdict deferred to Gap #28 charter."
            )
            next_step = (
                f"Either add the missing fluid fields {missing_in_all_fluid} "
                f"to a fluid region's 0/region_<name>/ directory, OR update "
                f"manifest bc_contract.turbulence_fields / thermal_fields "
                f"to reflect the actual physics declared in 0/."
            )
        else:
            status = "PASS"
            reason = "multi_region_per_class_pending"
            summary = (
                f"Multi-region CHT layout: {len(fluid_regions)} fluid "
                f"region(s) + {len(solid_regions)} solid region(s); all "
                f"manifest-declared fluid expected fields present. "
                f"Per-class verdict (solid wants T-only, fluid wants "
                f"U/p/turbulence/thermal) deferred to Gap #28 charter."
            )
            next_step = (
                "PASS at the fluid-coverage layer. Per-region per-class "
                "validation (Gap #28) would tighten this to PASS-strict; "
                "current PASS asserts the case carries all manifest-declared "
                "BC evidence distributed across regions."
            )

        gate = {
            "status": status,
            "summary": summary,
            "details": {
                "reason": reason,
                "regions_detected": sorted(regions_dict.keys()),
                "region_count": len(regions_dict),
                "fluid_region_count": len(fluid_regions),
                "solid_region_count": len(solid_regions),
                "empty_region_count": len(empty_regions),
                "fluid_regions": sorted(fluid_regions),
                "solid_regions": sorted(solid_regions),
                "expected_fluid_fields": expected_fluid_fields,
                "missing_in_all_fluid_regions": missing_in_all_fluid,
                "per_region_field_summary": per_region_summary,
                "next_step": next_step,
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": gate["status"],
            "reason": reason,
            "layout": "multi_region",
            "regions_detected": sorted(regions_dict.keys()),
            "fluid_region_count": len(fluid_regions),
            "solid_region_count": len(solid_regions),
            "expected_fluid_fields": expected_fluid_fields,
            "missing_in_all_fluid_regions": missing_in_all_fluid,
            "per_region_field_summary": per_region_summary,
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    geom_quality, geom_err = _read_json(case_dir, "geometry_quality.json")
    if geom_quality is None or geom_quality.get("status") == "blocked":
        # Cross-artifact dependency: patch coverage + type match both
        # need the realized polyMesh patch list. Without it we BLOCK
        # rather than guess.
        gate = {
            "status": "BLOCKED",
            "summary": (
                "Cannot evaluate bc_contract without geometry evidence — "
                "geometry_quality.json missing or blocked."
            ),
            "details": {
                "reason": "geometry_evidence_missing",
                "geometry_detail": geom_err or (geom_quality or {}).get("reason"),
                "next_step": (
                    "Resolve the upstream geometry gate first (see audit/geometry.py "
                    "output). Once blockMesh produces polyMesh/boundary cleanly, "
                    "the BC audit can proceed."
                ),
            },
        }
        report = {
            "generated_at": utc_now_iso(),
            "case_id": manifest.get("case_id"),
            "phase": "M6",
            "gate_status": gate["status"],
            "reason": "geometry_evidence_missing",
        }
        report_path.write_text(json.dumps(report, indent=2))
        gate["artifact"] = str(report_path.relative_to(case_dir))
        return gate

    realized_polymesh = geom_quality.get("patches") or {}
    realized_patch_names = sorted(realized_polymesh.keys())
    expected_fields = bc_quality.get("expected_fields") or []

    file_presence = _eval_file_presence(bc_quality, expected_fields)
    patch_coverage = _eval_patch_coverage(bc_quality, realized_patch_names)
    type_match = _eval_type_match(contract, bc_quality, realized_polymesh)
    value_match = _eval_value_match(contract, bc_quality, realized_polymesh)
    derived = _eval_derived_consistency(contract, bc_quality, realized_polymesh)

    overall = _combine_dimensions(file_presence, patch_coverage, type_match, value_match, derived)

    # Summary string for the CLI / cockpit
    bits: List[str] = []
    if file_presence["dimension_status"] == "FAIL":
        miss = file_presence.get("missing_files", [])
        bad = file_presence.get("unparseable_files", [])
        bits.append(f"file_presence FAIL (missing={miss}, unparseable={[b['field'] for b in bad]})")
    else:
        bits.append(f"file_presence PASS ({len(file_presence['present'])} fields)")

    if patch_coverage["dimension_status"] == "FAIL":
        bits.append(f"patch_coverage FAIL (gaps={patch_coverage.get('gaps_by_field', {})})")
    elif patch_coverage["dimension_status"] == "INCOMPLETE":
        bits.append(f"patch_coverage INCOMPLETE ({patch_coverage.get('reason', '?')})")
    else:
        bits.append("patch_coverage PASS")

    if type_match["dimension_status"] == "FAIL":
        bits.append(
            f"type_match FAIL "
            f"(unresolvable={type_match.get('unresolvable_keys', [])}, "
            f"mismatches={len(type_match.get('type_mismatches', []))})"
        )
    elif type_match["dimension_status"] == "INCOMPLETE":
        bits.append("type_match INCOMPLETE (declared field-class with no parsed file)")
    else:
        bits.append(f"type_match PASS ({type_match.get('checked_count', 0)} pairs)")

    if value_match["dimension_status"] == "FAIL":
        n_mm = len(value_match.get("value_mismatches", []))
        n_miss = len(value_match.get("value_missing", []))
        bits.append(f"value_match FAIL (mismatches={n_mm}, missing={n_miss})")
    elif value_match["dimension_status"] == "INCOMPLETE":
        bits.append("value_match INCOMPLETE")
    else:
        bits.append(f"value_match PASS ({value_match.get('matched_count', 0)} pairs)")

    if derived["dimension_status"] == "FAIL":
        n_dm = len(derived.get("derived_mismatches", []))
        n_dmiss = len(derived.get("derived_missing", []))
        bits.append(f"derived FAIL (mismatches={n_dm}, missing={n_dmiss})")
    else:
        bits.append(f"derived PASS ({derived.get('matched_count', 0)} pairs)")

    summary = "; ".join(bits) + "."

    report = {
        "generated_at": utc_now_iso(),
        "case_id": manifest.get("case_id"),
        "phase": "M8",
        "gate_status": overall,
        "zero_dir_inspected": True,
        "file_presence_dimension": file_presence,
        "patch_coverage_dimension": patch_coverage,
        "type_match_dimension": type_match,
        "value_match_dimension": value_match,
        "derived_consistency_dimension": derived,
        "expected_fields": expected_fields,
        "realized_patch_count": len(realized_patch_names),
        "declared_bc_contract": contract,
    }
    report_path.write_text(json.dumps(report, indent=2))

    return {
        "status": overall,
        "summary": summary,
        "artifact": str(report_path.relative_to(case_dir)),
        "details": {
            "file_presence": file_presence,
            "patch_coverage": patch_coverage,
            "type_match": type_match,
            "value_match": value_match,
            "derived_consistency": derived,
            "realized_patch_count": len(realized_patch_names),
        },
    }
