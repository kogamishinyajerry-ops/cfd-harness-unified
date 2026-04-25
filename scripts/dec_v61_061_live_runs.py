"""DEC-V61-061 Stage E live-run driver: NACA0012 at α∈{0°, 4°, 8°}.

Runs three OpenFOAM cases via FoamAgentExecutor (cfd-openfoam Docker
container), captures forceCoeffs + yPlus + Cp output, runs the
DEC-V61-061 extractors, and emits:

  reports/phase5_audit/dec_v61_061_live_run_<timestamp>_alpha<N>.json
    raw stdout/stderr per α
  reports/phase5_audit/dec_v61_061_live_summary.yaml
    aggregated multi-α summary (Cl/Cd/y+ per α + slope + sign-convention
    smoke verdict + SANITY_CHECK at α=0)

Closure conditions (intake §9 stage_e_close_checklist):

  - α=+8° run produces Cl > 0 strictly                         (smoke 1)
  - α=0° run produces |Cl| < 0.005                             (sanity)
  - lift_slope_dCl_dalpha_linear_regime within 10% of 0.105/deg (gate 3)
  - drag_coefficient_alpha_zero within 15% of 0.0080            (gate 2)
  - lift_coefficient_alpha_eight within 5% of 0.815             (HEADLINE)
  - y_plus_max_on_aerofoil in PASS/FLAG band (advisory)         (advisory)

Wall-clock target: ≤20 min per α run (intake §4 executable_smoke_test).

Usage:
    .venv/bin/python scripts/dec_v61_061_live_runs.py
"""

from __future__ import annotations

import datetime
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

from src.airfoil_extractors import (  # noqa: E402
    AirfoilExtractorError,
    assert_sign_convention,
    compute_cl_cd,
    compute_lift_slope,
    compute_y_plus_max,
)
from src.foam_agent_adapter import FoamAgentExecutor  # noqa: E402
from src.models import (  # noqa: E402
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)

REPORTS_DIR = REPO_ROOT / "reports" / "phase5_audit"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Gold targets per knowledge/gold_standards/naca0012_airfoil.yaml.
GOLD = {
    "lift_coefficient_alpha_eight": (0.815, 0.05),     # HEADLINE, 5%
    "drag_coefficient_alpha_zero":  (0.0080, 0.15),    # CROSS_CHECK, 15%
    "lift_slope_dCl_dalpha":        (0.105, 0.10),     # QUALITATIVE, 10%
}


def _make_task(alpha_deg: float) -> TaskSpec:
    return TaskSpec(
        name="NACA 0012 Airfoil External Flow",
        geometry_type=GeometryType.AIRFOIL,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=3000000.0,
        boundary_conditions={
            "chord_length": 1.0,
            "angle_of_attack": float(alpha_deg),
        },
    )


def _per_run(alpha_deg: float, timestamp: str) -> dict:
    """Run one α case end-to-end. Returns a dict for aggregation."""
    print(f"\n=== α={alpha_deg:+.1f}° run start ===", flush=True)
    t0 = time.monotonic()
    executor = FoamAgentExecutor()
    task = _make_task(alpha_deg)
    result = executor.execute(task)
    wall_s = time.monotonic() - t0
    print(
        f"=== α={alpha_deg:+.1f}° run complete in {wall_s:.1f}s "
        f"(success={result.success}, exit={result.exit_code}) ===",
        flush=True,
    )

    raw_path = REPORTS_DIR / (
        f"dec_v61_061_live_run_{timestamp}_alpha{int(alpha_deg)}.json"
    )
    raw_path.write_text(
        json.dumps(
            {
                "alpha_deg": alpha_deg,
                "success": result.success,
                "is_mock": result.is_mock,
                "exit_code": result.exit_code,
                "execution_time_s": result.execution_time_s,
                "wall_clock_s": wall_s,
                "residuals": result.residuals,
                "key_quantities": _to_jsonable(result.key_quantities),
                "raw_output_path": result.raw_output_path,
                "error_message": result.error_message,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    record: dict = {
        "alpha_deg": alpha_deg,
        "success": result.success,
        "exit_code": result.exit_code,
        "wall_clock_s": wall_s,
        "Cl": None,
        "Cd": None,
        "y_plus_max": None,
        "y_plus_advisory": None,
        "extractor_error": None,
        "raw_path": str(raw_path),
    }

    if not result.success:
        record["extractor_error"] = (
            f"FoamAgentExecutor failed: {result.error_message}"
        )
        return record

    # Pull Cl/Cd/y+ from key_quantities populated by Stage C populator.
    kq = result.key_quantities or {}
    record["Cl"] = kq.get("lift_coefficient")
    record["Cd"] = kq.get("drag_coefficient")
    record["y_plus_max"] = kq.get("y_plus_max")
    record["y_plus_advisory"] = kq.get("y_plus_max_advisory_status")
    record["force_coeffs_source"] = kq.get("force_coeffs_source")
    record["alpha_deg_observed"] = kq.get("alpha_deg")
    record["cl_drift_pct_last_100"] = kq.get("cl_drift_pct_last_100")
    record["cd_drift_pct_last_100"] = kq.get("cd_drift_pct_last_100")
    if kq.get("lift_coefficient_emitter_error"):
        record["extractor_error"] = kq["lift_coefficient_emitter_error"]
    if kq.get("y_plus_max_emitter_error"):
        record["y_plus_emitter_error"] = kq["y_plus_max_emitter_error"]

    # Sign-convention smoke / SANITY_CHECK assertions (intake §9).
    smoke_status = "n/a"
    if record["Cl"] is not None:
        try:
            from src.airfoil_extractors import CoeffsResult

            assert_sign_convention(
                CoeffsResult(
                    alpha_deg=alpha_deg,
                    Cl=float(record["Cl"]),
                    Cd=float(record["Cd"] or 0.0),
                    final_time=0.0,
                    n_samples=0,
                )
            )
            smoke_status = "PASS"
        except AirfoilExtractorError as exc:
            smoke_status = f"FAIL: {exc}"
    record["sign_convention_smoke"] = smoke_status

    return record


def _to_jsonable(obj):
    """Make key_quantities (potentially with numpy/non-JSON types) serializable."""
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _aggregate(records: list, timestamp: str) -> dict:
    """Compose multi-α summary including slope + gate verdicts."""
    summary = {
        "dec_id": "DEC-V61-061",
        "case_id": "naca0012_airfoil",
        "timestamp": timestamp,
        "runs": records,
        "gates": {},
        "smoke_assertions": {},
        "headline_verdict": "PENDING",
    }

    by_alpha = {r["alpha_deg"]: r for r in records}

    # HEADLINE: Cl@α=8°
    r8 = by_alpha.get(8.0)
    if r8 and r8["Cl"] is not None:
        gold, tol = GOLD["lift_coefficient_alpha_eight"]
        rel_err = abs(r8["Cl"] - gold) / abs(gold)
        summary["gates"]["lift_coefficient_alpha_eight"] = {
            "value": r8["Cl"],
            "gold": gold,
            "rel_error": rel_err,
            "tolerance": tol,
            "pass": rel_err <= tol,
            "role": "HEADLINE_PRIMARY_SCALAR",
        }

    # CROSS_CHECK: Cd@α=0°
    r0 = by_alpha.get(0.0)
    if r0 and r0["Cd"] is not None:
        gold, tol = GOLD["drag_coefficient_alpha_zero"]
        rel_err = abs(r0["Cd"] - gold) / abs(gold)
        summary["gates"]["drag_coefficient_alpha_zero"] = {
            "value": r0["Cd"],
            "gold": gold,
            "rel_error": rel_err,
            "tolerance": tol,
            "pass": rel_err <= tol,
            "role": "SAME_RUN_CROSS_CHECK",
        }

    # SANITY_CHECK: |Cl@α=0| < 0.005
    if r0 and r0["Cl"] is not None:
        cl0 = float(r0["Cl"])
        summary["smoke_assertions"]["sanity_cl_at_alpha_zero"] = {
            "value": cl0,
            "abs_band": 0.005,
            "pass": abs(cl0) < 0.005,
        }

    # Sign-convention smoke (α=+8 → Cl>0).
    if r8:
        summary["smoke_assertions"]["sign_convention_alpha_eight"] = {
            "Cl": r8["Cl"],
            "expected": ">0",
            "pass": r8["Cl"] is not None and r8["Cl"] > 0,
        }

    # QUALITATIVE: dCl/dα slope from 3-pt fit
    pts = []
    for a in (0.0, 4.0, 8.0):
        r = by_alpha.get(a)
        if r and r["Cl"] is not None:
            pts.append((a, float(r["Cl"])))
    if len(pts) >= 2:
        try:
            slope_res = compute_lift_slope(pts)
            gold, tol = GOLD["lift_slope_dCl_dalpha"]
            rel_err = abs(slope_res.slope_per_deg - gold) / abs(gold)
            summary["gates"]["lift_slope_dCl_dalpha_linear_regime"] = {
                "value": slope_res.slope_per_deg,
                "intercept": slope_res.intercept,
                "linearity_check_applicable": slope_res.linearity_check_applicable,
                "linearity_ok": slope_res.linearity_ok,
                "linearity_residual": slope_res.linearity_residual,
                "n_points": slope_res.n_points,
                "gold": gold,
                "rel_error": rel_err,
                "tolerance": tol,
                "pass": rel_err <= tol,
                "role": "QUALITATIVE_GATE",
            }
        except AirfoilExtractorError as exc:
            summary["gates"]["lift_slope_dCl_dalpha_linear_regime"] = {
                "error": str(exc),
                "pass": False,
            }

    # Headline verdict roll-up (HARD gates only; advisory excluded).
    hard_gates = [g for g in summary["gates"].values() if g.get("role") != "PROVISIONAL_ADVISORY"]
    smoke_ok = all(s.get("pass", False) for s in summary["smoke_assertions"].values())
    if hard_gates and all(g.get("pass") for g in hard_gates) and smoke_ok:
        summary["headline_verdict"] = "PASS"
    elif hard_gates:
        failed = [k for k, g in summary["gates"].items() if not g.get("pass")]
        if not smoke_ok:
            failed.append("smoke_assertion")
        summary["headline_verdict"] = f"FAIL: {failed}"

    out_path = REPORTS_DIR / "dec_v61_061_live_summary.yaml"
    out_path.write_text(yaml.safe_dump(summary, sort_keys=False), encoding="utf-8")
    print(f"\n→ summary written: {out_path}", flush=True)
    return summary


def main() -> int:
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    print(f"DEC-V61-061 Stage E live-run driver · timestamp={timestamp}", flush=True)
    records = []
    for alpha in (0.0, 4.0, 8.0):
        try:
            records.append(_per_run(alpha, timestamp))
        except Exception as exc:  # don't abort the sweep on one failure
            records.append({
                "alpha_deg": alpha,
                "success": False,
                "extractor_error": f"driver exception: {exc}",
            })
            print(f"!! α={alpha}° driver exception: {exc}", flush=True)

    summary = _aggregate(records, timestamp)
    print("\n=== HEADLINE VERDICT:", summary.get("headline_verdict"), "===")
    print(yaml.safe_dump(summary["gates"], sort_keys=False))
    print(yaml.safe_dump(summary["smoke_assertions"], sort_keys=False))
    return 0 if summary.get("headline_verdict") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
