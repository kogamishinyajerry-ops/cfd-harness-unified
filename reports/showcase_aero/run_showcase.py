#!/usr/bin/env python3
"""Pure-aerodynamic aircraft showcase: NACA0012 2D wing-section RANS at flight Re.

Runs an angle-of-attack sweep (0,4,8,12 deg) END-TO-END through the reconciled
FoamAgentExecutor.execute() against the live OF11/foamRun cfd-openfoam container.

This is the CANONICAL aircraft-aerodynamics building block: a 2D wing-section
kOmegaSST RANS at flight Reynolds number (Re=3e6). It is NOT a full 3D aircraft.

Per-AoA we run the case the adapter HONESTLY produces (GeometryType.AIRFOIL,
the _generate_airfoil_flow generator: ~96k-cell C-grid, kOmegaSST, freestream
BCs, forceCoeffs1 + yPlus function objects), translated by W3.2b (DEC-V61-225)
to `foamRun -solver incompressibleFluid` in OF11.

REAL values only:
  - Cl, Cd from the forceCoeffs1 FO coefficient.dat / forceCoeffs.dat (final-time row)
  - final residuals (Ux/Uy/p/k/omega) + iteration count parsed from the solver log
  - y+_max on the aerofoil patch from the yPlus FO

The adapter's own in-execute() Cl/Cd extraction does NOT survive, because
execute()'s finally-block deletes the host case dir AND _copy_postprocess_fields
never stages postProcessing/forceCoeffs1 back to the host. So this driver pulls
forceCoeffs1 + yPlus + the solver log DIRECTLY FROM THE CONTAINER after each run
(the container-side case dir /tmp/cfd-harness-cases/<case_id> survives execute()),
then runs the same proven extractors (src.airfoil_extractors).

Nothing is fabricated: if a run fails to converge or Cl/Cd cannot be extracted,
that is recorded per-run.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tarfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import docker  # noqa: E402

import src.foam_agent_adapter as fa  # noqa: E402
from src.airfoil_extractors import (  # noqa: E402
    AirfoilExtractorError,
    compute_cl_cd,
    compute_lift_slope,
    compute_y_plus_max,
)
from src.models import (  # noqa: E402
    Compressibility,
    FlowType,
    GeometryType,
    SteadyState,
    TaskSpec,
)

OUT_DIR = REPO / "reports" / "showcase_aero"
CONTAINER = "cfd-openfoam"
RE_FLIGHT = 3.0e6  # flight-relevant Reynolds number (Ladson 1988 NASA TM-4074 gold ref)
CHORD = 1.0
AOA_SWEEP = [0.0, 4.0, 8.0, 12.0]  # linear-lift range toward stall (NACA0012 stall ~15-16 deg)


def _pull_dir_from_container(client, container_path: str, dest: Path) -> bool:
    """Copy a directory tree out of the container via get_archive (tar stream)."""
    container = client.containers.get(CONTAINER)
    try:
        bits, _ = container.get_archive(container_path)
        data = b"".join(bits)
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(dest)  # noqa: S202 - trusted local container output
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"    [warn] pull {container_path} failed: {exc}")
        return False


def _parse_log_residuals(log_text: str):
    """Final-iteration initial residuals + iteration count + solver-declared
    convergence flag from the solver log.

    The airfoil mesh is the x-z plane (thin span in y), so the solved velocity
    components are Ux and Uz — there is NO Uy equation. Convergence judgment
    must check the components that actually exist.
    """
    residuals: dict = {}
    for var in ("Ux", "Uy", "Uz", "p", "k", "omega"):
        matches = re.findall(
            rf"Solving for {var},.*?Initial residual\s*=\s*([\d.eE+-]+)", log_text
        )
        if matches:
            residuals[var] = float(matches[-1])
    # SIMPLE iteration count: count "Time = N" lines (foamRun steady prints Time = iter)
    time_lines = re.findall(r"^Time = (\d+)", log_text, flags=re.MULTILINE)
    n_iters = int(time_lines[-1]) if time_lines else None
    # foamRun prints this when SIMPLE residualControl targets are all met and
    # it stops BEFORE endTime — the solver's own convergence verdict.
    solver_converged = "SIMPLE solution converged in" in log_text
    return residuals, n_iters, solver_converged


def _converged(residuals: dict, solver_converged: bool) -> bool:
    """Honest convergence judgment.

    PRIMARY: trust the solver's own "SIMPLE solution converged in N iterations"
    message — foamRun only prints it when ALL fvSolution residualControl targets
    (p 1e-6, U 1e-5, k 1e-5, omega 1e-5) are simultaneously met and it stops
    before endTime.

    CROSS-CHECK: independently verify the final initial residuals are at/below
    those bands using the components that actually exist (Ux, Uz — the x-z-plane
    airfoil mesh has no Uy equation). A run that hit endTime with residuals still
    above target is NOT converged.
    """
    if not residuals:
        return bool(solver_converged)
    u_components = [
        residuals[v] for v in ("Ux", "Uy", "Uz") if v in residuals
    ]
    p_ok = residuals.get("p", 1.0) <= 1e-6
    u_ok = bool(u_components) and max(u_components) <= 1e-5
    k_ok = residuals.get("k", 1.0) <= 1e-5
    w_ok = residuals.get("omega", 1.0) <= 1e-5
    residual_ok = bool(p_ok and u_ok and k_ok and w_ok)
    # Converged if the solver said so OR our independent residual check passes.
    return bool(solver_converged or residual_ok)


def run_one(client, alpha_deg: float) -> dict:
    tag = f"a{int(round(alpha_deg)):02d}"
    name = f"naca0012_showcase_{tag}"
    work_dir = OUT_DIR / "_work" / name  # unique host work_dir per run
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    run_out = OUT_DIR / name
    run_out.mkdir(parents=True, exist_ok=True)

    spec = TaskSpec(
        name=name,
        geometry_type=GeometryType.AIRFOIL,
        flow_type=FlowType.EXTERNAL,
        steady_state=SteadyState.STEADY,
        compressibility=Compressibility.INCOMPRESSIBLE,
        Re=RE_FLIGHT,
        boundary_conditions={"chord_length": CHORD, "angle_of_attack": alpha_deg},
    )

    ex = fa.FoamAgentExecutor(work_dir=str(work_dir))
    print(f"\n=== AoA {alpha_deg:.0f} deg | {name} | work_dir={work_dir} ===")
    t0 = time.monotonic()
    result = ex.execute(spec)
    wall = time.monotonic() - t0
    print(f"    execute() success={result.success} time={result.execution_time_s:.1f}s wall={wall:.1f}s")

    rec: dict = {
        "alpha_deg": alpha_deg,
        "name": name,
        "Re": RE_FLIGHT,
        "chord": CHORD,
        "turbulence_model": "kOmegaSST",
        "solver_command": "foamRun -solver incompressibleFluid",
        "execute_success": bool(result.success),
        "execute_time_s": round(result.execution_time_s, 2),
        "raw_output_path": result.raw_output_path,
        "error_message": result.error_message,
    }

    if not result.success or not result.raw_output_path:
        rec["status"] = "EXECUTE_FAILED"
        rec["cl"] = None
        rec["cd"] = None
        rec["converged"] = False
        rec["note"] = (
            "ex.execute() returned success=False — see error_message. "
            "No Cl/Cd extracted."
        )
        (run_out / "run_record.json").write_text(json.dumps(rec, indent=2))
        return rec

    # Container-side case dir survives execute() (only the host dir is rm'd).
    case_id = Path(result.raw_output_path).name
    cont_case = f"/tmp/cfd-harness-cases/{case_id}"
    rec["container_case_dir"] = cont_case

    # Pull postProcessing + solver log out of the container into the report dir.
    _pull_dir_from_container(client, f"{cont_case}/postProcessing", run_out / "_pp")
    # get_archive nests under the basename; normalize: run_out/_pp/postProcessing/...
    pp_root = run_out / "_pp" / "postProcessing"
    case_for_extract = run_out / "_extract"
    if pp_root.is_dir():
        (case_for_extract / "postProcessing").mkdir(parents=True, exist_ok=True)
        for child in pp_root.iterdir():
            dest = case_for_extract / "postProcessing" / child.name
            if child.is_dir():
                shutil.copytree(child, dest, dirs_exist_ok=True)

    # Solver log (log.simpleFoam — W3.2b keeps log_name=solver_name).
    log_text = ""
    for logname in ("log.simpleFoam", "log.foamRun"):
        cont = client.containers.get(CONTAINER)
        try:
            bits, _ = cont.get_archive(f"{cont_case}/{logname}")
            data = b"".join(bits)
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                for m in tar.getmembers():
                    if m.name.endswith(logname.split(".")[-1]) or m.name.endswith(logname):
                        f = tar.extractfile(m)
                        if f:
                            log_text = f.read().decode("utf-8", errors="replace")
                        break
            if log_text:
                (run_out / logname).write_text(log_text)
                break
        except Exception:  # noqa: BLE001
            continue

    residuals, n_iters, solver_converged = _parse_log_residuals(log_text)
    converged = _converged(residuals, solver_converged)
    rec["final_residuals"] = residuals
    rec["iterations"] = n_iters
    rec["solver_declared_converged"] = solver_converged
    rec["converged"] = converged

    # REAL Cl/Cd from forceCoeffs FO.
    try:
        coeffs = compute_cl_cd(case_for_extract, alpha_deg=alpha_deg)
        rec["cl"] = coeffs.Cl
        rec["cd"] = coeffs.Cd
        rec["force_coeffs_final_time"] = coeffs.final_time
        rec["force_coeffs_n_samples"] = coeffs.n_samples
        rec["cl_drift_pct_last_100"] = coeffs.cl_drift_pct_last_100
        rec["cd_drift_pct_last_100"] = coeffs.cd_drift_pct_last_100
        rec["force_coeffs_source"] = "forceCoeffs1_FO_aerofoil"
        print(f"    Cl={coeffs.Cl:.4f} Cd={coeffs.Cd:.5f} (t={coeffs.final_time:g}, n={coeffs.n_samples})")
    except AirfoilExtractorError as exc:
        rec["cl"] = None
        rec["cd"] = None
        rec["cl_cd_error"] = str(exc)
        print(f"    [Cl/Cd extract FAILED] {exc}")

    # y+_max from yPlus FO (advisory wall-resolution diagnostic).
    try:
        yp = compute_y_plus_max(case_for_extract)
        rec["y_plus_max"] = yp.y_plus_max
        rec["y_plus_min"] = yp.y_plus_min
        rec["y_plus_avg"] = yp.y_plus_avg
        rec["y_plus_advisory"] = yp.advisory_status
        print(f"    y+_max={yp.y_plus_max:.1f} ({yp.advisory_status})")
    except AirfoilExtractorError as exc:
        rec["y_plus_error"] = str(exc)

    rec["status"] = "OK" if rec.get("cl") is not None else "RAN_NO_COEFFS"
    rec["wall_clock_s"] = round(wall, 1)
    (run_out / "run_record.json").write_text(json.dumps(rec, indent=2))

    # Clean container-side case dir to avoid accumulation (best-effort).
    try:
        client.containers.get(CONTAINER).exec_run(
            cmd=["bash", "-c", f"rm -rf {cont_case}"], user="0"
        )
    except Exception:  # noqa: BLE001
        pass
    # Drop the bulky _pp/_extract scratch; keep the canonical pp copy.
    shutil.rmtree(run_out / "_pp", ignore_errors=True)
    return rec


def main() -> int:
    client = docker.from_env()
    cont = client.containers.get(CONTAINER)
    if cont.status != "running":
        print(f"FATAL: container {CONTAINER} not running (status={cont.status})")
        return 2

    runs = []
    for a in AOA_SWEEP:
        runs.append(run_one(client, a))

    # Lift-curve slope (REAL, only across runs that produced Cl).
    polar_pts = [(r["alpha_deg"], r["cl"]) for r in runs if r.get("cl") is not None]
    slope_info = None
    if len(polar_pts) >= 2:
        try:
            ls = compute_lift_slope(polar_pts)
            slope_info = {
                "dCl_dalpha_per_deg": ls.slope_per_deg,
                "intercept_cl_at_alpha0": ls.intercept,
                "linearity_check_applicable": ls.linearity_check_applicable,
                "linearity_ok": ls.linearity_ok,
                "linearity_residual": ls.linearity_residual,
                "points": [list(p) for p in ls.points],
            }
        except AirfoilExtractorError as exc:
            slope_info = {"error": str(exc)}

    summary = {
        "case": "NACA0012 2D wing-section RANS, AoA sweep at flight Re",
        "honest_scope": (
            "2D airfoil (wing-section) kOmegaSST RANS at flight Re=3e6 — the "
            "canonical aircraft-aerodynamics building block. NOT a full 3D "
            "aircraft. Single freestream Mach incompressible (kinematic). "
            "Each point ran end-to-end via FoamAgentExecutor.execute() against "
            "the live OF11/foamRun cfd-openfoam container."
        ),
        "Re": RE_FLIGHT,
        "turbulence_model": "kOmegaSST",
        "solver_command": "foamRun -solver incompressibleFluid (W3.2b/DEC-V61-225)",
        "mesh_cells_approx": 96000,
        "aoa_sweep_deg": AOA_SWEEP,
        "converged_count": sum(1 for r in runs if r.get("converged")),
        "ran_count": sum(1 for r in runs if r.get("status") in ("OK", "RAN_NO_COEFFS")),
        "coeffs_extracted_count": sum(1 for r in runs if r.get("cl") is not None),
        "lift_curve_slope": slope_info,
        "runs": runs,
    }
    (OUT_DIR / "showcase_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
