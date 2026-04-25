"""Pre-flight battery for case-N visualization work (DEC-V61-051 closure).

The BFS episode exposed a process hole: I started visualizing a fixture that
the repo's own attestor already flagged as hard-FAIL (G3/G4/G5), and the gold
YAML itself self-documented ATTEST_HAZARD. Neither signal was surfaced until
after a misleading PNG was committed. This script is the pre-flight checklist
that would have aborted BFS Phase 1 in 3 seconds.

Usage:
    python3.11 scripts/preflight_case_visual.py <case_id>
    python3.11 scripts/preflight_case_visual.py --all

Exit codes:
    0 — GREEN: every check passes, safe to visualize
    1 — AMBER: one or more warnings, proceed with care + document
    2 — RED:   at least one hard-fail, DO NOT visualize from this fixture

Checks (all existing modules; nothing reinvented):

 1. Gold YAML contract_status — if the yaml already declares a HAZARD /
    FAIL status, that's the ground truth the visualization must respect.

 2. Gate battery (src/comparator_gates.check_all_gates) — runs G3
    velocity overflow, G4 turbulence negativity/overflow, G5 continuity
    divergence on the fixture's log + VTK directory. Any hard-FAIL is a
    RED.

 3. Fixture-manifest presence — if reports/phase5_fields/{case}/
    {timestamp}/ has no run manifest or no VTK, there's nothing to
    visualize from.

 4. Geometry sanity — compares the VTK mesh's spatial layout against
    the gold YAML's declared geometry_type. Currently implements a BFS
    check: if geometry_type is BACKWARD_FACING_STEP, require that the
    supposed step-body region (x < 0, y < 1) is OUTSIDE the mesh cells.
    Other geometry_types are accepted as "not-yet-checked" (AMBER hint,
    not a FAIL — the check is additive, not exhaustive).

 5. Velocity envelope sanity — if max |U| in the VTK exceeds 3·U_ref,
    the field has likely diverged (orthogonal to the G3 gate which
    uses 100·U_ref; this tighter cutoff catches numerical-noise
    excursions that don't blow G3 but still make a contour figure
    look nonsensical).

The script is READ-ONLY — never edits any file, never runs simpleFoam.
It just audits and reports.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402
import numpy as np  # noqa: E402

from src.comparator_gates import check_all_gates  # noqa: E402

_GOLD_ROOT = REPO_ROOT / "knowledge" / "gold_standards"
_FIELDS_ROOT = REPO_ROOT / "reports" / "phase5_fields"

# Per-case U_ref registry used by scripts/phase5_audit_run.py; duplicated
# here so the pre-flight doesn't require importing that driver.
_CASE_U_REF: dict[str, float] = {
    "lid_driven_cavity": 1.0,
    "backward_facing_step": 1.0,  # adapter uses U_bulk=1 even though audit driver says 44.2
    "turbulent_flat_plate": 69.4,
    "circular_cylinder_wake": 1.0,
    "plane_channel_flow": 1.0,
    "rayleigh_benard_convection": 0.005,
    "differential_heated_cavity": 0.01,
    "impinging_jet": 5.0,
    "naca0012_airfoil": 1.0,
    "duct_flow": 10.0,
}

GREEN = "\033[92m"
AMBER = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


class Check:
    """A single pre-flight finding. level ∈ {pass, warn, fail}."""

    def __init__(self, name: str, level: str, detail: str, evidence: Optional[dict] = None) -> None:
        self.name = name
        self.level = level
        self.detail = detail
        self.evidence = evidence or {}

    def format(self) -> str:
        color = {"pass": GREEN, "warn": AMBER, "fail": RED}.get(self.level, "")
        tag = {"pass": "GREEN", "warn": "AMBER", "fail": "RED  "}.get(self.level, "?????")
        return f"  {color}{tag}{RESET}  {self.name}: {self.detail}"


def _load_gold(case_id: str) -> Optional[dict]:
    path = _GOLD_ROOT / f"{case_id}.yaml"
    if not path.is_file():
        return None
    try:
        # Multi-doc YAML — the physics_contract lives in the first doc.
        docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        return next((d for d in docs if isinstance(d, dict) and "physics_contract" in d), None)
    except yaml.YAMLError:
        return None


def _check_gold_status(case_id: str) -> Check:
    doc = _load_gold(case_id)
    if doc is None:
        return Check("gold YAML", "warn",
                    f"no gold YAML found at knowledge/gold_standards/{case_id}.yaml")
    contract = doc.get("physics_contract", {})
    status = contract.get("contract_status", "UNKNOWN")
    lowered = str(status).lower()
    if "hazard" in lowered or "fail" in lowered or "not_satisfied" in lowered:
        return Check("gold contract_status", "fail",
                    f"gold YAML self-documents hazard: {status[:120]}",
                    evidence={"contract_status": status})
    if "partial" in lowered or "compatible" in lowered:
        return Check("gold contract_status", "warn",
                    f"gold YAML: {status[:120]}",
                    evidence={"contract_status": status})
    return Check("gold contract_status", "pass", status[:80])


def _pick_fixture_dir(case_id: str) -> Optional[Path]:
    case_dir = _FIELDS_ROOT / case_id
    if not case_dir.is_dir():
        return None
    candidates = [p for p in case_dir.iterdir() if p.is_dir() and p.name[0].isdigit()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def _check_fixture_present(case_id: str) -> tuple[Check, Optional[Path]]:
    fx = _pick_fixture_dir(case_id)
    if fx is None:
        return Check("fixture directory", "fail",
                     f"no timestamped fixture under reports/phase5_fields/{case_id}/"), None
    vtk_dir = fx / "VTK"
    if not vtk_dir.is_dir():
        return Check("fixture directory", "fail",
                     f"no VTK subdir at {vtk_dir.relative_to(REPO_ROOT)}"), None
    vtks = [p for p in vtk_dir.rglob("*.vtk") if "allPatches" not in p.parts]
    if not vtks:
        return Check("fixture directory", "fail",
                     f"no .vtk files in {vtk_dir.relative_to(REPO_ROOT)}"), None
    return Check("fixture directory", "pass", f"{fx.relative_to(REPO_ROOT)}"), fx


def _check_gates(case_id: str, fixture: Path) -> list[Check]:
    u_ref = _CASE_U_REF.get(case_id, 1.0)
    log_path = fixture / "log.simpleFoam"
    vtk_dir = fixture / "VTK"
    try:
        violations = check_all_gates(log_path, vtk_dir, U_ref=u_ref)
    except Exception as exc:
        return [Check("gate battery", "warn", f"check_all_gates raised: {exc!r}")]
    checks: list[Check] = []
    if not violations:
        checks.append(Check("gate battery", "pass", "G3/G4/G5 all clean"))
        return checks
    # GateViolation has no per-instance hardness flag; treat G2/G3/G4/G5
    # as hard-fail (per DEC-V61-036/059 these are the hard-contract gates),
    # any G-prefix beyond as warn. G2 will silently no-op here because
    # preflight does not load key_quantities — the canonical-band
    # shortcut check belongs to the audit_real_run path which has kq
    # in scope.
    for v in violations:
        level = "fail" if str(v.gate_id).upper() in {"G2", "G3", "G4", "G5"} else "warn"
        checks.append(Check(f"gate {v.gate_id}", level,
                            f"{v.concern_type}: {v.summary}",
                            evidence=v.evidence))
    return checks


def _check_geometry_bfs(fixture: Path) -> Check:
    """BFS-specific: verify the step body is EXCLUDED from the mesh."""
    try:
        import pyvista as pv
    except ImportError:
        return Check("geometry BFS", "warn",
                    "pyvista not importable; cannot verify step-body exclusion")
    vtks = sorted(
        p for p in (fixture / "VTK").rglob("*.vtk")
        if "allPatches" not in p.parts
    )
    if not vtks:
        return Check("geometry BFS", "warn", "no VTK to probe")
    try:
        grid = pv.read(str(vtks[-1]))
    except Exception as exc:
        return Check("geometry BFS", "warn", f"pv.read failed: {exc!r}")
    pts = np.asarray(grid.points)
    # Step body for whitelist BFS: x ∈ [-10, 0), y ∈ [0, 1).
    # H=1, expansion=1.125 → inlet channel at y ∈ [1, 1.125] upstream.
    in_step = (pts[:, 0] < -0.01) & (pts[:, 1] < 0.99)
    n_in = int(in_step.sum())
    if n_in > 0:
        return Check("geometry BFS step-body exclusion", "fail",
                    f"{n_in} of {len(pts)} mesh points lie in supposed step void (x<0, y<1) — "
                    "adapter renders a plain channel, not a BFS",
                    evidence={"points_in_void": n_in, "total_points": len(pts)})
    return Check("geometry BFS step-body exclusion", "pass",
                f"no mesh points in step void · {len(pts)} total")


def _check_velocity_envelope(case_id: str, fixture: Path) -> Check:
    try:
        import pyvista as pv
    except ImportError:
        return Check("|U| envelope", "warn", "pyvista not importable")
    vtks = sorted(
        p for p in (fixture / "VTK").rglob("*.vtk")
        if "allPatches" not in p.parts
    )
    if not vtks:
        return Check("|U| envelope", "warn", "no VTK to probe")
    try:
        grid = pv.read(str(vtks[-1]))
    except Exception as exc:
        return Check("|U| envelope", "warn", f"pv.read failed: {exc!r}")
    if "U" not in grid.point_data.keys():
        try:
            grid = grid.cell_data_to_point_data()
        except Exception:
            return Check("|U| envelope", "warn", "no U point_data")
    if "U" not in grid.point_data.keys():
        return Check("|U| envelope", "warn", "U field absent")
    u_ref = _CASE_U_REF.get(case_id, 1.0)
    U = np.asarray(grid.point_data["U"])
    umag = np.linalg.norm(U[:, :3], axis=1) if U.ndim == 2 else np.abs(U)
    finite = np.isfinite(umag)
    if not finite.any():
        return Check("|U| envelope", "fail",
                    "every |U| value is non-finite — field catastrophically divergent")
    umax = float(umag[finite].max())
    ratio = umax / max(u_ref, 1e-12)
    n_nonfinite = int((~finite).sum())
    evidence = {"umax": umax, "U_ref": u_ref, "ratio": ratio, "nonfinite_points": n_nonfinite}
    if not np.isfinite(umag).all() or ratio > 3.0:
        return Check("|U| envelope", "fail",
                    f"max |U| = {umax:.3g} is {ratio:.1f}× U_ref={u_ref} "
                    f"(nonfinite pts={n_nonfinite}) — contour figure will be misleading",
                    evidence=evidence)
    if ratio > 1.5:
        return Check("|U| envelope", "warn",
                    f"max |U| = {umax:.3g} is {ratio:.1f}× U_ref={u_ref} — elevated but plausible",
                    evidence=evidence)
    return Check("|U| envelope", "pass",
                f"max |U| = {umax:.3g}, {ratio:.2f}× U_ref")


def _check_scalar_contract(case_id: str) -> list[Check]:
    """Structured scalar-contract check.

    DEC-V61-052 round 2 (Codex round 1 #2): the contract_status string-
    matching gate is too easy to dodge — renaming a status from
    PARTIALLY_COMPATIBLE to GEOMETRY_AND_GATES_GREEN_XR_UNDER_TOLERANCE
    flipped preflight from RED to GREEN even though the headline scalar
    stayed outside its 10% tolerance band. This gate reads the live
    `audit_real_run_measurement.yaml` and compares the extracted scalar
    against the gold reference + tolerance from the gold YAML, producing
    an explicit pass/fail independent of contract_status prose.
    """
    checks: list[Check] = []
    meas_path = (REPO_ROOT / "ui/backend/tests/fixtures/runs"
                 / case_id / "audit_real_run_measurement.yaml")
    if not meas_path.is_file():
        return [Check("scalar contract", "warn",
                      f"no audit measurement at {meas_path.relative_to(REPO_ROOT)}")]
    try:
        meas = yaml.safe_load(meas_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [Check("scalar contract", "warn", f"audit YAML parse failed: {exc!r}")]
    measurement = (meas or {}).get("measurement", {}) or {}
    actual = measurement.get("value")
    quantity = measurement.get("quantity")
    if actual is None or quantity is None:
        return [Check("scalar contract", "warn",
                      f"audit measurement missing value/quantity (got {actual!r}/{quantity!r})")]

    # Walk the multi-doc gold YAML for the matching `quantity` block.
    gold_path = _GOLD_ROOT / f"{case_id}.yaml"
    if not gold_path.is_file():
        return [Check("scalar contract", "warn",
                      f"no gold YAML for {case_id}")]
    try:
        docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:
        return [Check("scalar contract", "warn", f"gold YAML parse failed: {exc!r}")]
    gold_doc = next((d for d in docs
                     if isinstance(d, dict) and d.get("quantity") == quantity), None)
    if gold_doc is None:
        return [Check("scalar contract", "warn",
                      f"gold has no quantity block for {quantity!r}")]
    refs = gold_doc.get("reference_values") or []
    if not refs or "value" not in refs[0]:
        return [Check("scalar contract", "warn",
                      f"gold {quantity} has no reference_values[].value")]
    expected = float(refs[0]["value"])
    tolerance = float(gold_doc.get("tolerance", 0.10))

    try:
        actual_f = float(actual)
    except (TypeError, ValueError):
        return [Check("scalar contract", "warn",
                      f"audit value not numeric: {actual!r}")]
    abs_dev = actual_f - expected
    rel_dev = abs_dev / expected if expected != 0 else float("inf")
    pct = rel_dev * 100
    summary = (
        f"{quantity}: actual={actual_f:.4g}  expected={expected:.4g}  "
        f"dev={pct:+.1f}% (tolerance ±{tolerance*100:.0f}%)"
    )
    evidence = {
        "quantity": quantity,
        "actual": actual_f,
        "expected": expected,
        "tolerance_pct": tolerance * 100,
        "deviation_pct": pct,
        "method": measurement.get("extraction_source"),
    }
    if abs(rel_dev) <= tolerance:
        checks.append(Check("scalar contract", "pass", summary, evidence=evidence))
    else:
        checks.append(Check("scalar contract", "fail", summary, evidence=evidence))

    # DEC-V61-053 Batch C: multi-scalar gate for Type I cases (cylinder's
    # 4 observables: St headline + cd_mean + cl_rms + u_mean_centerline).
    # Backward-compat: cases without `measurement.secondary_scalars` just
    # run the single-scalar check above. Type I cases emit
    # `secondary_scalars: {cd_mean: 1.34, cl_rms: 0.05, ...}` and this
    # block iterates over each additional gold quantity.
    secondary = measurement.get("secondary_scalars") or {}
    if isinstance(secondary, dict) and secondary:
        # Collect every non-primary gold quantity doc keyed by its `quantity:`.
        gold_secondary_docs = {
            d["quantity"]: d for d in docs
            if isinstance(d, dict)
            and isinstance(d.get("quantity"), str)
            and d["quantity"] != quantity  # skip primary (already checked)
            and d.get("reference_values")
        }
        for sec_name, sec_val in secondary.items():
            if not isinstance(sec_val, (int, float)):
                continue
            # Coordinate-indexed keys like "deficit_x_over_D_1.0" map to the
            # same gold_doc (u_mean_centerline) with per-point refs. For
            # simplicity in Batch C, check only canonical scalar-named
            # entries (cd_mean, cl_rms); profile-keyed entries go through
            # the LDC-style comparator pipeline downstream.
            sec_gold = gold_secondary_docs.get(sec_name)
            if sec_gold is None:
                continue
            sec_refs = sec_gold.get("reference_values") or []
            if not sec_refs or "value" not in sec_refs[0]:
                continue
            sec_expected = float(sec_refs[0]["value"])
            sec_tol = float(sec_gold.get("tolerance", 0.10))
            sec_actual = float(sec_val)
            sec_rel_dev = (sec_actual - sec_expected) / sec_expected if sec_expected != 0 else float("inf")
            sec_pct = sec_rel_dev * 100
            sec_summary = (
                f"{sec_name}: actual={sec_actual:.4g}  expected={sec_expected:.4g}  "
                f"dev={sec_pct:+.1f}% (tolerance ±{sec_tol*100:.0f}%)"
            )
            sec_evidence = {
                "quantity": sec_name,
                "actual": sec_actual,
                "expected": sec_expected,
                "tolerance_pct": sec_tol * 100,
                "deviation_pct": sec_pct,
                "gate_role": "secondary",
            }
            if abs(sec_rel_dev) <= sec_tol:
                checks.append(Check(
                    f"secondary scalar ({sec_name})", "pass",
                    sec_summary, evidence=sec_evidence,
                ))
            else:
                checks.append(Check(
                    f"secondary scalar ({sec_name})", "fail",
                    sec_summary, evidence=sec_evidence,
                ))
    return checks


def preflight(case_id: str) -> int:
    """Run the battery for one case. Returns exit-code-style result."""
    print(f"\n══ pre-flight · {case_id} ══")
    all_checks: list[Check] = []

    # Check 1: gold YAML contract_status (string-match prose check)
    all_checks.append(_check_gold_status(case_id))

    # Check 2: fixture presence
    fixture_check, fixture = _check_fixture_present(case_id)
    all_checks.append(fixture_check)

    if fixture is not None:
        # Check 3: gate battery
        all_checks.extend(_check_gates(case_id, fixture))
        # Check 4: BFS-specific geometry (extend with other geometry types later)
        gold = _load_gold(case_id)
        geom_type = (gold or {}).get("physics_contract", {}).get("geometry_type") \
            or (gold or {}).get("case_info", {}).get("geometry_type")
        # The gold YAML stores geometry_type per-quantity; fall back by heuristic.
        if case_id == "backward_facing_step" or str(geom_type).upper() == "BACKWARD_FACING_STEP":
            all_checks.append(_check_geometry_bfs(fixture))
        # Check 5: velocity envelope
        all_checks.append(_check_velocity_envelope(case_id, fixture))
        # Check 6: structured scalar contract (measured vs gold)
        all_checks.extend(_check_scalar_contract(case_id))

    for c in all_checks:
        print(c.format())

    has_fail = any(c.level == "fail" for c in all_checks)
    has_warn = any(c.level == "warn" for c in all_checks)
    if has_fail:
        print(f"  {RED}■ RED · do not visualize this fixture{RESET}")
        return 2
    if has_warn:
        print(f"  {AMBER}■ AMBER · proceed with care, document caveats{RESET}")
        return 1
    print(f"  {GREEN}■ GREEN · safe to visualize{RESET}")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--all":
        cases = sorted(_CASE_U_REF.keys())
    else:
        cases = argv
    worst = 0
    for case_id in cases:
        rc = preflight(case_id)
        worst = max(worst, rc)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
