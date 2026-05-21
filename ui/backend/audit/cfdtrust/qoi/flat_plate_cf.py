"""Flat-plate Cf reference loading + per-x comparison — pure functions.

Sub-commit 2d. All functions are pure (single-input → single-output, no
side effects outside the function's own scope). The Layer-2 OpenFOAM
extractor (`wall_shear.py`) and the audit layer compose these into the
real `reference_comparison.csv` artifact.

Honesty contract:
  - `compare_against_reference` BLOCKs if measured or reference is empty
    after the skip-window filter — refusing to silently "PASS by checking
    zero points" (same failure mode as R15-F-02).
  - `load_reference_csv` BLOCKs on a missing reference file rather than
    interpolating zeros into the gate.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


# ---------- I/O ----------


def load_reference_csv(path: Path) -> List[Tuple[float, float]]:
    """Read a 2-column CSV of `(x_m, Cf)` rows (with header) and return
    a list of `(x, Cf)` tuples sorted by x.

    Raises FileNotFoundError if the file does not exist; ValueError if any
    row cannot be parsed. The reference is small enough (<1k rows for the
    NASA TMR CFL3D Cf curve) that loading it eagerly is fine.
    """
    if not path.exists():
        raise FileNotFoundError(f"reference CSV not found: {path}")
    rows: List[Tuple[float, float]] = []
    with path.open() as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"reference CSV is empty: {path}")
        # Allow header to be either `x_m,Cf` or numeric (treat as data row).
        try:
            x0 = float(header[0])
            cf0 = float(header[1])
            rows.append((x0, cf0))
        except (ValueError, IndexError):
            pass  # header line; skip
        for i, raw in enumerate(reader, start=2):
            if not raw or all(not c.strip() for c in raw):
                continue
            try:
                rows.append((float(raw[0]), float(raw[1])))
            except (ValueError, IndexError) as e:
                raise ValueError(f"{path}:{i}: cannot parse row {raw!r}: {e}")
    rows.sort(key=lambda r: r[0])
    return rows


# ---------- math ----------


def linear_interpolate(
    curve: Sequence[Tuple[float, float]],
    x: float,
) -> float | None:
    """Piecewise-linear interpolation on a sorted-by-x `(x, y)` curve.

    Returns ``None`` if `x` is outside the curve's x range — refusing to
    extrapolate. Callers must skip those points rather than fabricate
    reference values past the data range.
    """
    if not curve:
        return None
    if x < curve[0][0] or x > curve[-1][0]:
        return None
    # Single-point curve: only the exact match qualifies (covered by the
    # range check above). Without this branch the `range(len(curve)-1)`
    # below would be empty.
    if len(curve) == 1:
        return curve[0][1]
    # Binary search would be tighter; the reference curve has O(400) rows
    # and there's no measured curve with >10k points yet. Linear is fine.
    for i in range(len(curve) - 1):
        x0, y0 = curve[i]
        x1, y1 = curve[i + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            frac = (x - x0) / (x1 - x0)
            return y0 + frac * (y1 - y0)
    return None


# ---------- gate computation ----------


def compare_against_reference(
    measured: Sequence[Tuple[float, float]],
    reference: Sequence[Tuple[float, float]],
    *,
    tolerance: float,
    x_min_compare: float = 0.0,
) -> Dict[str, Any]:
    """Per-x comparison of a measured Cf curve vs a reference Cf curve.

    Inputs MUST be sorted by x. Both curves are pre-filtered with
    `x >= x_min_compare` (laminar/transition skip-window). For every
    measured (x, Cf_run) the reference Cf is linearly interpolated at the
    same x; points where the measured x falls outside the reference's
    x range are dropped from the comparison (NOT silently treated as PASS).

    `tolerance` is interpreted as MAX relative error — the comparison
    PASSES iff every per-point `|Cf_run - Cf_ref| / Cf_ref <= tolerance`.

    Returns a dict with the same shape as other audit-gate outputs:
        {
            "status": "PASS" | "FAIL" | "BLOCKED",
            "summary": str,
            "details": {
                "tolerance": float,
                "x_min_compare": float,
                "n_compared": int,
                "max_rel_error": float,
                "max_rel_error_x": float,
                "rows": [
                    {"x_m": float, "Cf_run": float, "Cf_ref": float,
                     "abs_error": float, "rel_error": float,
                     "within_tolerance": bool},
                    ...
                ],
            },
        }
    """
    if tolerance <= 0:
        return {
            "status": "BLOCKED",
            "summary": f"reference_comparison.tolerance must be positive, got {tolerance!r}",
            "details": {"reason": "invalid_tolerance", "tolerance": tolerance},
        }

    measured_filt = [(x, cf) for (x, cf) in measured if x >= x_min_compare]
    reference_filt = [(x, cf) for (x, cf) in reference if x >= x_min_compare]

    if not measured_filt:
        return {
            "status": "BLOCKED",
            "summary": (
                f"measured Cf curve is empty after x_min_compare={x_min_compare} "
                "filter — nothing to compare."
            ),
            "details": {
                "reason": "no_measured_points_in_compare_window",
                "x_min_compare": x_min_compare,
                "tolerance": tolerance,
            },
        }
    if not reference_filt:
        return {
            "status": "BLOCKED",
            "summary": (
                f"reference Cf curve is empty after x_min_compare={x_min_compare} "
                "filter — cannot compare."
            ),
            "details": {
                "reason": "no_reference_points_in_compare_window",
                "x_min_compare": x_min_compare,
                "tolerance": tolerance,
            },
        }

    rows: List[Dict[str, Any]] = []
    max_rel_err = 0.0
    max_rel_err_x = float("nan")
    any_within = False
    any_outside = False

    for x, cf_run in measured_filt:
        cf_ref = linear_interpolate(reference_filt, x)
        if cf_ref is None:
            # x outside reference range — skip rather than fake a comparison.
            continue
        if cf_ref == 0.0:
            # Avoid div-by-zero; treat as a per-point BLOCK and continue.
            rows.append({
                "x_m": x, "Cf_run": cf_run, "Cf_ref": cf_ref,
                "abs_error": abs(cf_run), "rel_error": float("inf"),
                "within_tolerance": False,
            })
            any_outside = True
            continue
        abs_err = abs(cf_run - cf_ref)
        rel_err = abs_err / abs(cf_ref)
        within = rel_err <= tolerance
        if within:
            any_within = True
        else:
            any_outside = True
        rows.append({
            "x_m": x,
            "Cf_run": cf_run,
            "Cf_ref": cf_ref,
            "abs_error": abs_err,
            "rel_error": rel_err,
            "within_tolerance": within,
        })
        if rel_err > max_rel_err:
            max_rel_err = rel_err
            max_rel_err_x = x

    if not rows:
        return {
            "status": "BLOCKED",
            "summary": (
                "no measured points fell within the reference curve's x range "
                f"({reference_filt[0][0]:.4f} .. {reference_filt[-1][0]:.4f}) "
                f"AND x_min_compare={x_min_compare}."
            ),
            "details": {
                "reason": "no_overlapping_x_points",
                "tolerance": tolerance,
                "x_min_compare": x_min_compare,
                "reference_x_range": (reference_filt[0][0], reference_filt[-1][0]),
                "measured_x_range": (measured_filt[0][0], measured_filt[-1][0]),
            },
        }

    status = "PASS" if not any_outside else "FAIL"
    summary = (
        f"reference comparison: {len(rows)} pts; "
        f"max relative error {max_rel_err*100:.2f}% at x={max_rel_err_x:.4f} m "
        f"(tolerance {tolerance*100:.1f}%)."
    )

    return {
        "status": status,
        "summary": summary,
        "details": {
            "tolerance": tolerance,
            "x_min_compare": x_min_compare,
            "n_compared": len(rows),
            "max_rel_error": max_rel_err,
            "max_rel_error_x": max_rel_err_x,
            "rows": rows,
        },
    }


def write_reference_comparison_csv(
    gate: Dict[str, Any],
    qoi_name: str,
    out_path: Path,
) -> None:
    """Write the per-point comparison rows from `gate` to a CSV file.

    Columns: `name,x_m,Cf_run,Cf_ref,abs_error,rel_error,within_tolerance`.
    Always writes a header even if `gate.status` is BLOCKED — downstream
    tooling expects the file to exist; an empty body with header is the
    honest representation of "no comparison rows produced."
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = gate.get("details", {}).get("rows", []) or []
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "name", "x_m", "Cf_run", "Cf_ref",
            "abs_error", "rel_error", "within_tolerance",
        ])
        for r in rows:
            w.writerow([
                qoi_name,
                f"{r['x_m']:.6e}",
                f"{r['Cf_run']:.6e}",
                f"{r['Cf_ref']:.6e}",
                f"{r['abs_error']:.6e}",
                f"{r['rel_error']:.6e}",
                "true" if r["within_tolerance"] else "false",
            ])
