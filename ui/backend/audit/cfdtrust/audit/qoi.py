"""QoI extraction + reference comparison.

Sub-commit 2d: when a real OpenFOAM run has emitted wallShearStress at the
latest time step, the comparison gate runs against NASA TMR reference data
(CFL3D SST flat-plate Cf curve). Otherwise the Phase 0 placeholder rows
are kept so the harness still produces all required artifact files (the
`required_artifacts` contract).

Honesty rules:
  - Real comparison only fires when EVERY input (manifest.reference_csv,
    OpenFOAM polyMesh, wallShearStress field) is present and parseable.
    Missing any input → BLOCKED gate, placeholder qoi.csv row preserved.
  - Reference status must be `finalized` to attempt a real comparison.
    `placeholder` / `not_finalized` → mocked gate.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..qoi import flat_plate_cf, wall_shear
from ..status import ensure_artifacts_dir, mocked_gate, utc_now_iso


def _resolved_under(child: Path, root: Path) -> bool:
    """R16-F-05 fix: refuse `reference_csv` paths that escape `case_dir`.
    Both paths are resolved (symlinks followed) before the containment
    check, so a symlink that points outside is rejected too."""
    try:
        child_r = child.resolve()
        root_r = root.resolve()
    except OSError:
        return False
    try:
        child_r.relative_to(root_r)
    except ValueError:
        return False
    return True


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_latest_time(case_dir: Path) -> Optional[str]:
    """Return the name of the largest-numbered time-step directory in
    `case_dir`, or None if no numeric time-step dir exists. The OpenFOAM
    convention is that each iteration writes a directory whose name is
    the float time value.
    """
    candidates: List[Tuple[float, str]] = []
    for child in case_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        if name in ("0", "system", "constant", "artifacts", "reference", "negative_tests", "postProcessing"):
            # `0` is the initial-condition dir; skip it as a final-time candidate
            # but still walk past it. Other reserved names are skipped too.
            continue
        try:
            t = float(name)
        except ValueError:
            continue
        candidates.append((t, name))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def _resolve_u_inf(manifest: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Resolve the reference velocity used for Cf normalization.

    Returns `(value, source_path)` where source_path is the dotted manifest
    field where the value came from, or `(<bad value>, None)` if no
    positive number was found in either location.

    Resolution order (M9.2):
      1. `bc_contract.inlet.velocity.magnitude_m_s` — fixed-velocity inlets
         (flat_plate, BFS). Pre-M9.2 only path.
      2. `physics.reference_velocity_m_s` — cyclic/periodic cases where
         flow is driven by a body source (e.g. meanVelocityForce); the
         *target* bulk velocity the source maintains is the
         semantically-correct normalization scale.

    The reference Cf data MUST use the same normalization
    (verified in reference/provenance.md for each finalized reference).
    """
    inlet = manifest.get("bc_contract", {}).get("inlet", {}).get("velocity", {})
    u_inf = inlet.get("magnitude_m_s")
    if isinstance(u_inf, (int, float)) and u_inf > 0:
        return float(u_inf), "bc_contract.inlet.velocity.magnitude_m_s"
    physics = manifest.get("physics", {})
    u_inf2 = physics.get("reference_velocity_m_s")
    if isinstance(u_inf2, (int, float)) and u_inf2 > 0:
        return float(u_inf2), "physics.reference_velocity_m_s"
    # Return whatever raw value was found (or None) for diagnostics, source=None
    return (u_inf if u_inf is not None else u_inf2), None


def _attempt_real_comparison(
    case_dir: Path,
    manifest: Dict[str, Any],
) -> Optional[Tuple[Dict[str, Any], List[Tuple[float, float]]]]:
    """Return `(gate, measured_cf_rows)` if a real comparison can be
    performed, else None. None covers: solver_backend != openfoam, no
    wallShearStress file, reference status != finalized, missing
    reference_csv, etc. — every "graceful no" reason. Hard errors
    (malformed boundary file, mismatched vector counts) are surfaced
    as a BLOCKED gate via the returned tuple, NOT as None.
    """
    if manifest.get("solver_backend") != "openfoam":
        return None

    ref_block = manifest.get("reference_comparison", {})
    if ref_block.get("status") != "finalized":
        return None

    ref_csv_rel = ref_block.get("reference_csv")
    if not ref_csv_rel:
        return None

    # R16-F-05 fix: reject absolute paths and paths that would resolve
    # outside the case dir (e.g. `../../etc/passwd` or a symlinked file).
    if Path(ref_csv_rel).is_absolute():
        return ({
            "status": "BLOCKED",
            "summary": "reference_csv must be a relative path inside the case dir.",
            "details": {
                "reason": "reference_csv_path_unsafe",
                "value": ref_csv_rel,
                "detail": "absolute paths not allowed",
            },
        }, [])
    ref_csv_path = case_dir / ref_csv_rel
    if not _resolved_under(ref_csv_path, case_dir):
        return ({
            "status": "BLOCKED",
            "summary": "reference_csv resolves outside the case dir.",
            "details": {
                "reason": "reference_csv_path_unsafe",
                "value": ref_csv_rel,
                "detail": "resolves outside case_dir (traversal or symlink-escape)",
            },
        }, [])
    if not ref_csv_path.exists():
        return ({
            "status": "BLOCKED",
            "summary": f"reference CSV missing on disk: {ref_csv_rel}",
            "details": {
                "reason": "reference_csv_missing",
                "expected_path": str(ref_csv_path.relative_to(case_dir)),
                "next_step": "Place the reference CSV at the path declared in manifest.reference_comparison.reference_csv.",
            },
        }, [])

    # R16-F-01 fix: if manifest declares an expected SHA-256 for the
    # reference CSV, verify the on-disk file matches. Refuses to compare
    # against tampered reference data — same honesty principle as R-17
    # (refuse when we can't prove the input is what we expected).
    expected_sha = ref_block.get("reference_csv_sha256")
    if expected_sha:
        actual_sha = _file_sha256(ref_csv_path)
        if actual_sha.lower() != str(expected_sha).lower():
            return ({
                "status": "BLOCKED",
                "summary": "reference CSV SHA-256 does not match manifest.",
                "details": {
                    "reason": "reference_csv_sha_mismatch",
                    "expected_sha256": expected_sha,
                    "actual_sha256": actual_sha,
                    "next_step": (
                        "Either restore the reference CSV from its source "
                        "(see reference/provenance.md), OR re-derive it AND "
                        "update manifest.reference_comparison.reference_csv_sha256."
                    ),
                },
            }, [])

    # Latest time step (where wallShearStress field is written).
    latest = _find_latest_time(case_dir)
    if latest is None:
        return None  # no real run yet → fall through to mocked

    # R16-F-03 fix: refuse to read time-step dirs or WSS files that are
    # symlinks. The OpenFOAM adapter's R-17 walk only fires on the
    # adapter's own `case_dir` audit; the audit-layer path reads case-dir
    # files independently and must apply the same posture. Defense in
    # depth: a malicious case_dir could symlink `159/` to `/etc/`, and
    # without this guard we'd try to open `/etc/wallShearStress`.
    time_dir = case_dir / latest
    if time_dir.is_symlink():
        return ({
            "status": "BLOCKED",
            "summary": f"latest time directory {latest!r} is a symlink — refusing to read it.",
            "details": {
                "reason": "time_dir_is_symlink",
                "detail": f"{latest}/ → {time_dir.resolve()} (refused by R-17 posture)",
            },
        }, [])
    wss_path = case_dir / latest / "wallShearStress"
    if not wss_path.exists():
        return None  # solver ran but the WSS FO did not fire → fall through
    if wss_path.is_symlink():
        return ({
            "status": "BLOCKED",
            "summary": "wallShearStress file is a symlink — refusing to read it.",
            "details": {
                "reason": "wallshearstress_is_symlink",
                "detail": f"{wss_path.relative_to(case_dir)} → {wss_path.resolve()}",
            },
        }, [])
    # Also fence polyMesh files for the same reason.
    for pm_name in ("boundary", "faces", "points"):
        pm_file = case_dir / "constant" / "polyMesh" / pm_name
        if pm_file.exists() and pm_file.is_symlink():
            return ({
                "status": "BLOCKED",
                "summary": f"polyMesh/{pm_name} is a symlink — refusing to read it.",
                "details": {
                    "reason": "polymesh_file_is_symlink",
                    "detail": f"constant/polyMesh/{pm_name} → {pm_file.resolve()}",
                },
            }, [])

    # Velocity magnitude for Cf normalization. See _resolve_u_inf for
    # full resolution order (inlet.magnitude_m_s → physics.reference_velocity_m_s).
    u_inf, u_inf_source = _resolve_u_inf(manifest)
    if u_inf_source is None:
        return ({
            "status": "BLOCKED",
            "summary": (
                "cannot normalize Cf: neither "
                "`bc_contract.inlet.velocity.magnitude_m_s` nor "
                "`physics.reference_velocity_m_s` is set to a positive number."
            ),
            "details": {
                "reason": "missing_u_inf",
                "got": repr(u_inf),
            },
        }, [])

    # M2.3b: case-declared patch name. Defaults to "wall" for back-compat
    # with flat_plate's manifest (which has a single patch literally named
    # "wall"); BFS-class cases declare e.g. `wall_patch: bottomWall`.
    wall_patch = ref_block.get("wall_patch", "wall")
    try:
        measured = wall_shear.extract_wall_cf(
            case_dir, latest, patch=wall_patch, u_inf_m_s=float(u_inf),
        )
    except (FileNotFoundError, ValueError) as e:
        return ({
            "status": "BLOCKED",
            "summary": f"failed to extract wall Cf from OpenFOAM output: {e}",
            "details": {
                "reason": "wall_shear_extract_failed",
                "detail": str(e),
                "time_step": latest,
            },
        }, [])

    try:
        reference = flat_plate_cf.load_reference_csv(ref_csv_path)
    except (FileNotFoundError, ValueError) as e:
        return ({
            "status": "BLOCKED",
            "summary": f"failed to load reference CSV: {e}",
            "details": {
                "reason": "reference_csv_parse_failed",
                "detail": str(e),
                "path": str(ref_csv_path.relative_to(case_dir)),
            },
        }, [])

    tolerance = float(ref_block.get("tolerance", 0.10))
    x_min = float(ref_block.get("x_min_compare_m", 0.0))

    # DEC-V61-209 ADDENDUM 3: opt-in NASA-TMR-convention gate (integrated drag
    # + downstream Cf station as PASS criteria; per-point near-LE deviations
    # demoted to informational known_deviations). Default stays per-point so
    # other cases are unaffected.
    gate_mode = str(ref_block.get("gate_mode", "per_point"))
    if gate_mode == "nasa_integrated":
        station = float(ref_block.get("verification_station_m", 0.97008))
        gate = flat_plate_cf.evaluate_nasa_convention(
            measured, reference, tolerance=tolerance, x_min_compare=x_min,
            verification_station_m=station,
        )
    else:
        gate = flat_plate_cf.compare_against_reference(
            measured, reference, tolerance=tolerance, x_min_compare=x_min,
        )
    gate["details"]["reference_status"] = "finalized"
    gate["details"]["reference_source"] = ref_block.get("source", "unknown")
    gate["details"]["reference_csv"] = ref_csv_rel
    gate["details"]["real_comparison_performed"] = True
    gate["details"]["u_inf_source"] = u_inf_source
    gate["details"]["latest_time"] = latest
    gate["details"]["u_inf_m_s"] = float(u_inf)
    return gate, measured


_QOI_CSV_HEADER = ["name", "x_m", "value", "units", "source"]


def _write_qoi_csv(
    qoi_path: Path,
    qois: List[Dict[str, Any]],
    measured_cf: Optional[List[Tuple[float, float]]],
) -> None:
    """Write qoi.csv.

    R16-F-08 fix: the column layout is the SAME 5 columns
    `name,x_m,value,units,source` whether real measured data is present
    or the row is a Phase 0 placeholder. Pre-fix, the mocked path
    emitted 4 columns and the real path emitted 5 — any consumer that
    expected a fixed schema would silently break across modes.
    """
    with qoi_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_QOI_CSV_HEADER)
        if measured_cf is not None and len(measured_cf) > 0:
            for x, cf in measured_cf:
                w.writerow([
                    "skin_friction_coefficient",
                    f"{x:.6e}",
                    f"{cf:.6e}",
                    "dimensionless",
                    "openfoam_wallShearStress",
                ])
            # Also emit any scalar QoIs from the manifest as placeholder
            # rows so the harness's `required_artifacts` is still
            # satisfied for those.
            for q in qois:
                if q.get("kind") == "scalar":
                    w.writerow([
                        q.get("name", "unknown"),
                        "",
                        "N/A (scalar extraction not yet implemented)",
                        q.get("units", ""),
                        "phase1_pending",
                    ])
        else:
            for q in qois:
                w.writerow([
                    q.get("name", "unknown"),
                    "",
                    "N/A (Phase 0 mocked)",
                    q.get("units", ""),
                    "phase0_mocked",
                ])


def run(case_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    art = ensure_artifacts_dir(case_dir)
    qoi_path = art / "qoi.csv"
    ref_path = art / "reference_comparison.csv"

    qois: List[Dict[str, Any]] = manifest.get("qoi", [])
    ref_status = manifest.get("reference_comparison", {}).get("status", "missing")

    # Try the real comparison path first.
    real = _attempt_real_comparison(case_dir, manifest)

    if real is not None:
        ref_gate, measured = real
        _write_qoi_csv(qoi_path, qois, measured)
        # reference_comparison.csv driven by the gate's per-point rows.
        flat_plate_cf.write_reference_comparison_csv(
            ref_gate, qoi_name="skin_friction_coefficient", out_path=ref_path,
        )
        ref_gate["artifact"] = str(ref_path.relative_to(case_dir))

        qoi_gate = {
            "status": "PASS" if measured else "BLOCKED",
            "summary": (
                f"Extracted {len(measured)} wall-face Cf samples from "
                f"OpenFOAM output."
                if measured
                else "wall-shear-stress extraction produced zero rows."
            ),
            "artifact": str(qoi_path.relative_to(case_dir)),
            "details": {
                "real_extraction_performed": True,
                "n_samples": len(measured),
                "generated_at": utc_now_iso(),
            },
        }
        return {"qoi_gate": qoi_gate, "reference_gate": ref_gate}

    # Phase 0 / not-yet-real path: mocked rows.
    _write_qoi_csv(qoi_path, qois, None)
    # Placeholder reference_comparison.csv.
    with ref_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "measured", "reference", "abs_error", "rel_error", "within_tolerance", "tolerance", "source"])
        for q in qois:
            w.writerow([
                q.get("name", "unknown"),
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                q.get("tolerance", ""),
                f"reference_status={ref_status}",
            ])

    qoi_gate = mocked_gate(
        name="qoi_extraction",
        summary=f"QoI extraction not yet performed; {len(qois)} declared QoIs.",
        artifact=str(qoi_path.relative_to(case_dir)),
    )
    qoi_gate["details"]["generated_at"] = utc_now_iso()

    ref_gate = {
        "status": "MOCKED" if ref_status in ("finalized", "placeholder", "not_finalized") else "FAIL",
        "summary": f"Reference comparison status = {ref_status}; no real comparison performed (solver_backend != openfoam or wallShearStress not emitted yet).",
        "artifact": str(ref_path.relative_to(case_dir)),
        "details": {
            "reference_status": ref_status,
            "real_comparison_performed": False,
            "note": "Real comparison runs only when solver_backend=openfoam AND a real run has emitted wallShearStress at the latest time step.",
        },
    }
    if ref_status == "missing":
        ref_gate["summary"] = "reference_comparison.status is 'missing'."

    return {"qoi_gate": qoi_gate, "reference_gate": ref_gate}
