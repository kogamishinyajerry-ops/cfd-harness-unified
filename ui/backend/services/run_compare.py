"""Run-vs-run comparison · ROADMAP §60-day item.

Diff two runs of the same case_id side-by-side. Distinct from
`comparison_report.py` (run-vs-gold).

Public surface:
    compare_runs(case_id, run_a_id, run_b_id) -> dict
        Returns a JSON-serializable dict with:
          - meta (case_id, both run_ids, durations, timestamps)
          - task_spec_diff (param-level changes a→b, e.g. Re=100 vs Re=400)
          - scalar_diffs (per-key absolute + relative deltas for scalar
            key_quantities; flags inf/nan)
          - array_diffs (per-key for array key_quantities: length match,
            pointwise pairing, max-abs-deviation index, mean-abs-dev)
          - residual_diffs (same shape as scalar_diffs but for residuals)
          - verdict_diff (success a vs b, exit_code a vs b)
"""
from __future__ import annotations

import math
from typing import Any

from ui.backend.services.run_history import get_run_detail


def _is_scalar(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_numeric_array(v: Any) -> bool:
    return isinstance(v, list) and len(v) > 0 and all(
        isinstance(x, (int, float)) and not isinstance(x, bool) for x in v
    )


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _scalar_diff(key: str, a: Any, b: Any) -> dict[str, Any]:
    """Compute |b-a| and relative pct change. Returns a dict with the
    raw values plus diff fields. Handles non-finite gracefully."""
    a_f = _safe_float(a)
    b_f = _safe_float(b)
    out: dict[str, Any] = {
        "key": key,
        "a": a if a_f is not None else (str(a) if a is not None else None),
        "b": b if b_f is not None else (str(b) if b is not None else None),
        "a_finite": a_f is not None,
        "b_finite": b_f is not None,
    }
    if a_f is None or b_f is None:
        out["delta_abs"] = None
        out["delta_pct"] = None
        return out
    delta = b_f - a_f
    out["delta_abs"] = delta
    if abs(a_f) > 1e-30:
        out["delta_pct"] = (delta / a_f) * 100.0
    else:
        # a is essentially zero — relative change undefined; surface absolute only
        out["delta_pct"] = None
    return out


def _array_diff(key: str, a: list, b: list) -> dict[str, Any]:
    """Pointwise diff of two numeric arrays. Surfaces shape mismatch
    rather than padding/truncating — let the caller decide how to display.

    Per Codex r1 P1.2: NaN/inf at any index marks the diff as `tainted`
    so a partially-diverged run cannot pose as identical to the clean
    run. `tainted_indices` lists the first up-to-10 offending positions
    for diagnosis. `mean_abs_dev` reflects only finite-paired indices
    (same as before — the bug was the silent absence of a taint flag).
    """
    out: dict[str, Any] = {
        "key": key,
        "a_len": len(a),
        "b_len": len(b),
        "shape_match": len(a) == len(b),
    }
    if not out["shape_match"]:
        out["max_abs_dev"] = None
        out["max_abs_dev_index"] = None
        out["mean_abs_dev"] = None
        out["tainted"] = False
        out["tainted_indices"] = []
        return out
    finite_devs: list[float] = []
    tainted_indices: list[int] = []
    max_dev = 0.0
    max_idx: int | None = None
    for i, (av, bv) in enumerate(zip(a, b)):
        a_f = _safe_float(av)
        b_f = _safe_float(bv)
        if a_f is None or b_f is None:
            # NaN / inf at this index — record taint, do NOT contribute
            # to the dev statistics (so they reflect only valid pairs).
            tainted_indices.append(i)
            continue
        d = abs(b_f - a_f)
        finite_devs.append(d)
        if max_idx is None or d > max_dev:
            max_dev = d
            max_idx = i
    out["tainted"] = bool(tainted_indices)
    # Cap to first 10 tainted indices so the response stays bounded
    # even on a fully-NaN array.
    out["tainted_indices"] = tainted_indices[:10]
    out["max_abs_dev"] = max_dev if finite_devs else None
    out["max_abs_dev_index"] = max_idx if finite_devs else None
    out["mean_abs_dev"] = (
        sum(finite_devs) / len(finite_devs) if finite_devs else None
    )
    return out


def _diff_dicts(a: dict, b: dict) -> tuple[list[dict], list[dict], list[str]]:
    """Walk a + b's keys, classify each as scalar / array / unknown, and
    diff numerically when possible. Returns (scalar_diffs, array_diffs,
    skipped_keys). Keys present in only one side are still emitted with
    one-sided values.

    Per Codex r1 P2.1: when a key's value type differs across runs
    (scalar↔array), surface a `type_mismatch=true` flag in the array
    bucket rather than falling through to scalar_diff (which would lose
    the array's shape entirely). The frontend should treat
    type_mismatch entries as a structural change worth highlighting.
    """
    all_keys = sorted(set(a.keys()) | set(b.keys()))
    scalar_diffs: list[dict] = []
    array_diffs: list[dict] = []
    skipped: list[str] = []
    for k in all_keys:
        va = a.get(k)
        vb = b.get(k)
        a_is_arr = _is_numeric_array(va)
        b_is_arr = _is_numeric_array(vb)
        a_is_sc = _is_scalar(va)
        b_is_sc = _is_scalar(vb)

        # Per Codex r2 P2 follow-up: route ALL list-bearing keys through
        # the array bucket, including empty / non-numeric lists. Otherwise
        # scalar↔[] would still collapse to scalar_diffs and lose the
        # shape change. _kind_of() distinguishes numeric/empty/nonnumeric
        # variants so the frontend can render appropriately.
        a_is_list = isinstance(va, list)
        b_is_list = isinstance(vb, list)

        if a_is_arr and b_is_arr:
            array_diffs.append(_array_diff(k, va, vb))
        elif a_is_list or b_is_list:
            # Either (a) one side list + other not, or (b) both lists but
            # at least one is empty / non-numeric. Either way: shape
            # change is structural, route to array bucket with mismatch
            # flag.
            array_diffs.append({
                "key": k,
                "a_len": len(va) if a_is_list else 0,
                "b_len": len(vb) if b_is_list else 0,
                "shape_match": False,
                "type_mismatch": (a_is_list != b_is_list)
                                 or (a_is_arr != b_is_arr),
                "a_kind": _kind_of(va),
                "b_kind": _kind_of(vb),
                "max_abs_dev": None,
                "max_abs_dev_index": None,
                "mean_abs_dev": None,
                "tainted": False,
                "tainted_indices": [],
            })
        elif a_is_sc or b_is_sc:
            scalar_diffs.append(_scalar_diff(k, va, vb))
        else:
            # String/bool/None on both sides — emit as scalar with raw
            # values, no delta. Logged in skipped_keys for the frontend
            # to optionally hide.
            scalar_diffs.append({
                "key": k, "a": va, "b": vb,
                "a_finite": False, "b_finite": False,
                "delta_abs": None, "delta_pct": None,
            })
            skipped.append(k)
    return scalar_diffs, array_diffs, skipped


def _kind_of(v: Any) -> str:
    if v is None:
        return "none"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "scalar"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        if not v:
            return "list_empty"
        if _is_numeric_array(v):
            return "array"
        return "list_nonnumeric"
    return type(v).__name__


def _diff_task_specs(a: dict, b: dict) -> list[dict]:
    """task_spec is small + heterogeneous (Re, geometry_type, etc.).
    Surface every key whose value differs, plus type info."""
    all_keys = sorted(set(a.keys()) | set(b.keys()))
    out: list[dict] = []
    for k in all_keys:
        va = a.get(k)
        vb = b.get(k)
        if va == vb:
            continue
        out.append({"key": k, "a": va, "b": vb})
    return out


def compare_runs(case_id: str, run_a_id: str, run_b_id: str) -> dict[str, Any]:
    """Read both runs' artifacts and return a JSON-serializable diff.

    Raises FileNotFoundError if either run dir is missing (caller maps
    that to HTTP 404 in the route layer).
    """
    detail_a = get_run_detail(case_id, run_a_id)
    detail_b = get_run_detail(case_id, run_b_id)

    scalar_kq, array_kq, skipped_kq = _diff_dicts(
        detail_a.key_quantities or {}, detail_b.key_quantities or {}
    )
    scalar_res, _, _ = _diff_dicts(
        detail_a.residuals or {}, detail_b.residuals or {}
    )

    task_diff = _diff_task_specs(
        detail_a.task_spec or {}, detail_b.task_spec or {}
    )

    return {
        "case_id": case_id,
        "run_a": {
            "run_id": run_a_id,
            "started_at": detail_a.started_at,
            "duration_s": detail_a.duration_s,
            "success": detail_a.success,
            "exit_code": detail_a.exit_code,
            "verdict_summary": detail_a.verdict_summary,
            "task_spec": detail_a.task_spec,
        },
        "run_b": {
            "run_id": run_b_id,
            "started_at": detail_b.started_at,
            "duration_s": detail_b.duration_s,
            "success": detail_b.success,
            "exit_code": detail_b.exit_code,
            "verdict_summary": detail_b.verdict_summary,
            "task_spec": detail_b.task_spec,
        },
        "task_spec_diff": task_diff,
        "scalar_diffs": scalar_kq,
        "array_diffs": array_kq,
        "residual_diffs": scalar_res,
        "skipped_keys": skipped_kq,
        "verdict_diff": {
            "success_changed": detail_a.success != detail_b.success,
            "exit_code_changed": detail_a.exit_code != detail_b.exit_code,
        },
    }
