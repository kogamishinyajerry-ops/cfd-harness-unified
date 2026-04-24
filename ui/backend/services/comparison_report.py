"""Phase 7c — CFD vs Gold comparison report service.

Renders an 8-section HTML report for a given (case_id, run_label), using:
- Phase 7a field artifacts at reports/phase5_fields/{case}/{ts}/
- Phase 7b rendered figures at reports/phase5_renders/{case}/{ts}/
- knowledge/gold_standards/{case}.yaml gold reference
- ui/backend/tests/fixtures/runs/{case}/mesh_{20,40,80,160}_measurement.yaml for grid convergence

Backend route: ui/backend/routes/comparison_report.py calls `render_report_html`
and `render_report_pdf` from this module. No DOM / no JS — static HTML + PNG
inlined assets referenced by file:// for WeasyPrint PDF, served via FileResponse
or embedded iframe on frontend.

Design: report_html is a self-contained string (no asset URLs pointing to
/api/... — uses file:// for PDF rendering and relative paths for HTML serving).
"""
from __future__ import annotations

import datetime
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Codex round 1 HIGH (2026-04-21): strict shape gate on manifest-supplied
# timestamp and artifact paths. Mirrors ui/backend/services/field_artifacts.py
# defense-in-depth pattern so tampered runs/{label}.json cannot steer reads
# outside reports/phase5_fields/ or writes outside reports/phase5_reports/.
_TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parents[2]
_TEMPLATES = _MODULE_DIR.parent / "templates"
_FIELDS_ROOT = _REPO_ROOT / "reports" / "phase5_fields"
_RENDERS_ROOT = _REPO_ROOT / "reports" / "phase5_renders"
_GOLD_ROOT = _REPO_ROOT / "knowledge" / "gold_standards"
_FIXTURE_ROOT = _REPO_ROOT / "ui" / "backend" / "tests" / "fixtures" / "runs"

# DEC-V61-034 Tier C: gold-overlay MVP cases get the full 8-section report;
# visual-only cases get a reduced 3-section report (Metadata + Contour + Residuals)
# — real OpenFOAM evidence without the per-case gold-overlay plumbing.
# _REPORT_SUPPORTED_CASES is the union; gate membership checks use this.
_GOLD_OVERLAY_CASES = frozenset({"lid_driven_cavity"})
# DEC-V61-052 Batch D: BFS stays in the visual-only tier but
# _build_visual_only_context now emits `metrics_reattachment` +
# `paper_reattachment` when the case is backward_facing_step. This
# surfaces the measured Xr/H vs the gold anchor as a scalar card in
# the Compare tab (mirroring the LDC D7/D8 pattern) without having
# to fork the full LDC gold-overlay pipeline (which expects uCenterline
# .xy + psi_extraction — neither applicable to BFS).
_VISUAL_ONLY_CASES = frozenset({
    "backward_facing_step",
    "plane_channel_flow",
    "turbulent_flat_plate",
    "circular_cylinder_wake",
    "impinging_jet",
    "naca0012_airfoil",
    "rayleigh_benard_convection",
    "differential_heated_cavity",
    "duct_flow",
})
_REPORT_SUPPORTED_CASES = _GOLD_OVERLAY_CASES | _VISUAL_ONLY_CASES

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "htm"]),
)


class ReportError(Exception):
    """Recoverable — caller should 404 or return partial payload."""


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def _run_manifest_path(case_id: str, run_label: str) -> Path:
    return _FIELDS_ROOT / case_id / "runs" / f"{run_label}.json"


def _renders_manifest_path(case_id: str, run_label: str) -> Path:
    return _RENDERS_ROOT / case_id / "runs" / f"{run_label}.json"


def _load_run_manifest(case_id: str, run_label: str) -> dict:
    p = _run_manifest_path(case_id, run_label)
    if not p.is_file():
        raise ReportError(f"no run manifest for {case_id}/{run_label}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReportError(f"run manifest not an object: {p}")
    return data


def _load_renders_manifest(case_id: str, run_label: str) -> Optional[dict]:
    p = _renders_manifest_path(case_id, run_label)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    return data


def _validated_timestamp(ts: Any) -> Optional[str]:
    """Codex round 1 HIGH: reject any manifest-supplied timestamp that doesn't
    match the exact YYYYMMDDTHHMMSSZ shape. Blocks '../../outside' etc."""
    if not isinstance(ts, str) or not _TIMESTAMP_RE.match(ts):
        return None
    return ts


def _safe_rel_under(candidate: str, root: Path) -> Optional[str]:
    """Return `candidate` if it resolves under `root`, else None.

    Used to validate manifest-supplied output file paths before they flow
    into template `img src`. Prevents a tampered renders manifest from
    pointing WeasyPrint base_url resolution at arbitrary local files
    (which would then be embedded into PDFs as image data URLs).
    """
    if not isinstance(candidate, str) or not candidate:
        return None
    if candidate.startswith("/") or "\\" in candidate or ".." in candidate.split("/"):
        return None
    try:
        resolved = (_REPO_ROOT / candidate).resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _load_ldc_gold() -> tuple[list[float], list[float], dict]:
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        raise ReportError(f"gold file missing: {gold_path}")
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    u_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_centerline"),
        None,
    )
    if u_doc is None:
        raise ReportError("no u_centerline doc in LDC gold")
    ys: list[float] = []
    us: list[float] = []
    for entry in u_doc.get("reference_values", []):
        if isinstance(entry, dict):
            y = entry.get("y")
            u = entry.get("value") or entry.get("u")
            if y is not None and u is not None:
                ys.append(float(y))
                us.append(float(u))
    return ys, us, u_doc


def _load_ldc_v_gold() -> tuple[list[float], list[float], dict] | None:
    """Load the v_centerline gold block from lid_driven_cavity.yaml.

    DEC-V61-050 batch 1: returns (xs, vs, doc) for the Ghia 1982 Table II
    Re=100 native 17-point non-uniform x grid + v values. Returns None if
    the block is missing, empty, or still uses the legacy y-indexed shape
    (silent degrade — caller treats absence as "v_centerline not
    exercised for this case"). Reads the SAME multi-doc YAML as
    _load_ldc_gold so both share a single IO.
    """
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        return None
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    v_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "v_centerline"),
        None,
    )
    if v_doc is None:
        return None
    xs: list[float] = []
    vs: list[float] = []
    for entry in v_doc.get("reference_values", []):
        if not isinstance(entry, dict):
            continue
        # Post-DEC-V61-050-batch-1 shape: {x: float, v: float}. Old shape
        # pre-batch-1 was {y: float, v: float} (axis-label bug). Accept
        # the new shape only — the old shape's values were unusable even
        # if read, so silently return None rather than degrade to garbage.
        x = entry.get("x")
        v = entry.get("value") or entry.get("v")
        if x is not None and v is not None:
            xs.append(float(x))
            vs.append(float(v))
    if not xs:
        return None
    return xs, vs, v_doc


def _load_ldc_vortex_gold() -> dict | None:
    """Load the primary_vortex_location gold block from lid_driven_cavity.yaml.

    DEC-V61-050 batch 3: returns the dict with {vortex_center_x,
    vortex_center_y, psi_min, position_tolerance, psi_tolerance, source}
    extracted from the reference_values entries. Returns None if the
    block is missing or still has the pre-batch-3 shape (x=0.5, y=0.7650).
    """
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        return None
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    pv_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "primary_vortex_location"),
        None,
    )
    if pv_doc is None:
        return None
    rvs = {
        entry.get("name"): entry.get("value")
        for entry in pv_doc.get("reference_values", [])
        if isinstance(entry, dict)
    }
    # Require all three Ghia Table III fields. Pre-batch-3 block had
    # u_min instead of psi_min — we refuse to load that and silently
    # return None so the comparator degrades rather than reporting
    # garbage against the wrong reference.
    if "vortex_center_x" not in rvs or "vortex_center_y" not in rvs or "psi_min" not in rvs:
        return None
    return {
        "vortex_center_x": float(rvs["vortex_center_x"]),
        "vortex_center_y": float(rvs["vortex_center_y"]),
        "psi_min": float(rvs["psi_min"]),
        "position_tolerance": float(pv_doc.get("position_tolerance", 0.02)),
        "psi_tolerance": float(pv_doc.get("psi_tolerance", 0.05)),
        "source": pv_doc.get("source", "Ghia 1982 Table III"),
        "literature_doi": pv_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
    }


def _load_ldc_secondary_vortices_gold() -> dict | None:
    """Load the secondary_vortices gold block from lid_driven_cavity.yaml.

    DEC-V61-050 batch 4: returns {eddies: [{name, x, y, psi,
    x_window_norm, y_window_norm, mode, description}, ...],
    position_tolerance, psi_tolerance, source, literature_doi}
    or None if the block is missing.
    """
    gold_path = _GOLD_ROOT / "lid_driven_cavity.yaml"
    if not gold_path.is_file():
        return None
    docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    sv_doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "secondary_vortices"),
        None,
    )
    if sv_doc is None:
        return None
    eddies: list[dict] = []
    for entry in sv_doc.get("reference_values", []):
        if not isinstance(entry, dict):
            continue
        if not all(k in entry for k in ("name", "x", "y", "psi", "x_window_norm", "y_window_norm", "mode")):
            continue
        eddies.append({
            "name": str(entry["name"]),
            "x_gold": float(entry["x"]),
            "y_gold": float(entry["y"]),
            "psi_gold": float(entry["psi"]),
            "x_window_norm": tuple(float(v) for v in entry["x_window_norm"]),
            "y_window_norm": tuple(float(v) for v in entry["y_window_norm"]),
            "mode": str(entry["mode"]),
            "description": str(entry.get("description", "")),
        })
    if not eddies:
        return None
    return {
        "eddies": eddies,
        "position_tolerance": float(sv_doc.get("position_tolerance", 0.02)),
        "psi_tolerance": float(sv_doc.get("psi_tolerance", 0.10)),
        "source": sv_doc.get("source", "Ghia 1982 Table III secondary vortex rows"),
        "literature_doi": sv_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
    }


def _load_cylinder_scalar_gold(quantity: str, default_tol: float = 0.05) -> dict | None:
    """Load a scalar-block gold for circular_cylinder_wake by quantity name.

    DEC-V61-053 Batch D: supports strouhal_number, cd_mean, cl_rms (all
    scalar docs in the multi-doc gold YAML). u_mean_centerline is a
    profile — handled by _load_cylinder_centerline_gold below.
    """
    gold_path = _GOLD_ROOT / "circular_cylinder_wake.yaml"
    if not gold_path.is_file():
        return None
    try:
        docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    except yaml.YAMLError:
        return None
    doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == quantity),
        None,
    )
    if doc is None:
        return None
    refs = doc.get("reference_values") or []
    if not refs or "value" not in refs[0]:
        return None
    return {
        "value": float(refs[0]["value"]),
        "unit": refs[0].get("unit", "dimensionless"),
        "tolerance": float(doc.get("tolerance", default_tol)),
        "source": doc.get("source", "Williamson 1996"),
        "literature_doi": doc.get("literature_doi", "10.1146/annurev.fl.28.010196.002421"),
    }


def _load_cylinder_centerline_gold() -> dict | None:
    """Load the u_mean_centerline profile gold (4 x_D points, u_deficit).

    DEC-V61-053 Batch D: returns {
        "stations": [{x_D: 1.0, deficit: 0.83}, ...],
        "tolerance": 0.05,
        "source": "Williamson 1996",
    } or None. Ref_value key is `u_Uinf` for back-compat (per B2 resolution;
    semantic is wake deficit per description field).
    """
    gold_path = _GOLD_ROOT / "circular_cylinder_wake.yaml"
    if not gold_path.is_file():
        return None
    try:
        docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    except yaml.YAMLError:
        return None
    doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "u_mean_centerline"),
        None,
    )
    if doc is None:
        return None
    refs = doc.get("reference_values") or []
    stations: list[dict] = []
    for entry in refs:
        if not isinstance(entry, dict):
            continue
        x_D = entry.get("x_D")
        deficit = entry.get("u_Uinf")  # historical key name; value IS deficit
        if isinstance(x_D, (int, float)) and isinstance(deficit, (int, float)):
            stations.append({"x_D": float(x_D), "deficit": float(deficit)})
    if not stations:
        return None
    return {
        "stations": stations,
        "tolerance": float(doc.get("tolerance", 0.05)),
        "source": doc.get("source", "Williamson 1996"),
        "literature_doi": doc.get("literature_doi", "10.1146/annurev.fl.28.010196.002421"),
    }


def _load_bfs_reattachment_gold() -> dict | None:
    """Load the reattachment_length gold block from backward_facing_step.yaml.

    DEC-V61-052 Batch D: mirrors _load_ldc_vortex_gold's shape.
    Returns {value, tolerance, source, literature_doi} or None.
    """
    gold_path = _GOLD_ROOT / "backward_facing_step.yaml"
    if not gold_path.is_file():
        return None
    try:
        docs = list(yaml.safe_load_all(gold_path.read_text(encoding="utf-8")))
    except yaml.YAMLError:
        return None
    doc = next(
        (d for d in docs if isinstance(d, dict) and d.get("quantity") == "reattachment_length"),
        None,
    )
    if doc is None:
        return None
    refs = doc.get("reference_values") or []
    if not refs or "value" not in refs[0]:
        return None
    return {
        "value": float(refs[0]["value"]),
        "unit": refs[0].get("unit", "Xr/H"),
        "tolerance": float(doc.get("tolerance", 0.10)),
        "source": doc.get("source", "Driver & Seegmiller 1985"),
        "literature_doi": doc.get("literature_doi", ""),
    }


def _load_sample_xy(path: Path, value_col: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Load an OpenFOAM raw-xy sample file. Returns (coord, value) arrays.

    OpenFOAM's lineUniform function object writes either 2-col files
    (coord + single-field-scalar) or 5-col files (coord + U_x + U_y + U_z
    + p) depending on fields requested. Col 0 is always the sampling axis
    coordinate. For u_centerline (sampled along y, U_x is the observable)
    value_col=1 is correct. For v_centerline (sampled along x, U_y is the
    observable) value_col=2.

    DEC-V61-050 batch 1: value_col parameter added so a single helper
    services both LDC observables without duplicating parser code.
    """
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        try:
            if value_col >= len(parts):
                continue
            rows.append([float(parts[0]), float(parts[value_col])])
        except (ValueError, IndexError):
            continue
    if not rows:
        raise ReportError(f"empty sample: {path}")
    arr = np.array(rows)
    return arr[:, 0], arr[:, 1]


def _latest_sample_iter(artifact_dir: Path) -> Path:
    sample_root = artifact_dir / "sample"
    if not sample_root.is_dir():
        raise ReportError(f"sample/ missing under {artifact_dir}")
    iters = sorted(
        (d for d in sample_root.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    if not iters:
        raise ReportError(f"no sample iter dirs under {sample_root}")
    return iters[-1]


def _compute_metrics(
    y_sim: np.ndarray, u_sim: np.ndarray,
    y_gold: list[float], u_gold: list[float],
    tolerance_pct: float,
) -> dict[str, Any]:
    """Compute L2/Linf/RMS + per-point |dev|% + pass count."""
    y_sim_norm = y_sim / max(float(y_sim.max()), 1e-12)
    u_sim_interp = np.interp(np.array(y_gold), y_sim_norm, u_sim)
    u_gold_arr = np.array(u_gold)
    diff = u_sim_interp - u_gold_arr

    denom = np.where(np.abs(u_gold_arr) < 1e-9, 1e-9, np.abs(u_gold_arr))
    dev_pct = 100.0 * np.abs(diff) / denom
    n_total = len(u_gold_arr)
    n_pass = int((dev_pct < tolerance_pct).sum())

    return {
        "l2": float(np.sqrt(np.mean(diff ** 2))),
        "linf": float(np.max(np.abs(diff))),
        "rms": float(np.sqrt(np.mean(diff ** 2))),  # alias
        "max_dev_pct": float(dev_pct.max()) if n_total else 0.0,
        "n_pass": n_pass,
        "n_total": n_total,
        "per_point_dev_pct": dev_pct.tolist(),
    }


def _parse_residuals_csv(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"total_iter": 0, "final_ux": None, "note": None}
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return {"total_iter": 0, "final_ux": None, "note": None}
    header = [c.strip() for c in lines[0].split(",")]
    last = None
    count = 0
    for ln in lines[1:]:
        parts = [c.strip() for c in ln.split(",")]
        if len(parts) != len(header):
            continue
        last = parts
        count += 1
    final_ux = None
    if last is not None and len(last) > 1 and last[1].upper() != "N/A":
        try:
            final_ux = float(last[1])
        except ValueError:
            pass
    note = None
    if final_ux is not None and final_ux > 1e-3:
        note = (f"注意：Ux 终值 {final_ux:.2e} 大于 1e-3 — "
                f"收敛可能未达稳态。建议增加 endTime 或降低 residualControl。")
    return {"total_iter": count, "final_ux": final_ux, "note": note}


def _load_grid_convergence(case_id: str, gold_y: list[float], gold_u: list[float]) -> tuple[list[dict], str]:
    """Read mesh_20/40/80/160_measurement.yaml fixtures, build table rows."""
    rows: list[dict] = []
    # LDC fixtures compare at y≈0.0625 (first gold point >0).
    sample_y = 0.0625
    try:
        sample_gold = next(u for y, u in zip(gold_y, gold_u) if abs(y - sample_y) < 1e-3)
    except StopIteration:
        sample_gold = gold_u[1] if len(gold_u) > 1 else 0.0

    case_dir = _FIXTURE_ROOT / case_id
    meshes = [("mesh_20", 20), ("mesh_40", 40), ("mesh_80", 80), ("mesh_160", 160)]
    for name, _n in meshes:
        path = case_dir / f"{name}_measurement.yaml"
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        meas = doc.get("measurement", {}) if isinstance(doc, dict) else {}
        val = meas.get("value")
        if val is None:
            continue
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            continue
        denom = abs(sample_gold) if abs(sample_gold) > 1e-9 else 1e-9
        dev_pct = 100.0 * abs(val_f - sample_gold) / denom
        if dev_pct < 5.0:
            verdict, cls = "PASS", "pass"
        elif dev_pct < 10.0:
            verdict, cls = "WARN", "warn"
        else:
            verdict, cls = "FAIL", "fail"
        rows.append({
            "mesh": name,
            "value": val_f,
            "dev_pct": dev_pct,
            "verdict": verdict,
            "verdict_class": cls,
        })
    if len(rows) < 2:
        return rows, "insufficient mesh data"
    devs = [r["dev_pct"] for r in rows]
    monotone = all(devs[i] >= devs[i + 1] for i in range(len(devs) - 1))
    note = "单调递减 ✓" if monotone else "非严格单调 — 检查 fixture"
    return rows, note


def _gci_to_template_dict(gci: Any) -> dict:
    """Flatten a RichardsonGCI dataclass into a JSON-serializable dict for the template."""
    return {
        "coarse_label": gci.coarse.label,
        "coarse_n": gci.coarse.n_cells_1d,
        "coarse_value": gci.coarse.value,
        "medium_label": gci.medium.label,
        "medium_n": gci.medium.n_cells_1d,
        "medium_value": gci.medium.value,
        "fine_label": gci.fine.label,
        "fine_n": gci.fine.n_cells_1d,
        "fine_value": gci.fine.value,
        "r_21": gci.r_21,
        "r_32": gci.r_32,
        "p_obs": gci.p_obs,
        "f_extrapolated": gci.f_extrapolated,
        "gci_21_pct": gci.gci_21 * 100 if gci.gci_21 is not None else None,
        "gci_32_pct": gci.gci_32 * 100 if gci.gci_32 is not None else None,
        "asymptotic_range_ok": gci.asymptotic_range_ok,
        "note": gci.note,
    }


def _get_commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=_REPO_ROOT, timeout=5,
        )
        return r.stdout.strip() or "unknown"
    except (subprocess.SubprocessError, OSError):
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_visual_only_context(
    case_id: str, run_label: str, timestamp: str, artifact_dir: Path,
    *, for_pdf: bool = False,
) -> dict:
    """Tier C reduced context (DEC-V61-034): real contour + residuals PNGs from
    the captured OpenFOAM artifacts, no gold overlay / verdict / GCI. The
    frontend + template detect ``visual_only: True`` and suppress the
    gold-dependent sections.
    """
    renders_manifest = _load_renders_manifest(case_id, run_label)
    renders_dir = _RENDERS_ROOT / case_id / timestamp

    def _rel(key: str, default: str = "") -> str:
        candidate: Optional[str] = None
        if renders_manifest:
            raw = renders_manifest.get("outputs", {}).get(key)
            if isinstance(raw, str):
                validated = _safe_rel_under(raw, _RENDERS_ROOT)
                if validated:
                    candidate = validated
        if candidate is None and default:
            guess = renders_dir / default
            if guess.is_file():
                try:
                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
                    if _safe_rel_under(rel, _RENDERS_ROOT):
                        candidate = rel
                except ValueError:
                    pass
        return candidate or ""

    # _rel = repo-relative path (PDF base_url=_REPO_ROOT resolves it).
    # _url = browser URL (HTML served at /api/... needs an absolute path
    # that hits the working renders route — repo-relative paths would
    # otherwise resolve against the /api/cases/... URL and 404).
    def _url(basename: str) -> str:
        return f"/api/cases/{case_id}/runs/{run_label}/renders/{basename}"

    renders = {
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
        "contour_png_url": _url("contour_u_magnitude.png"),
        "residuals_png_url": _url("residuals.png"),
        # Unified field read by the template — PDF mode gets repo-rel
        # paths (WeasyPrint base_url resolves them); HTML browser mode
        # gets API URLs that the /renders/ route serves.
        "contour_png": _rel("contour_u_magnitude_png", "contour_u_magnitude.png") if for_pdf else _url("contour_u_magnitude.png"),
        "residuals_png": _rel("residuals_png", "residuals.png") if for_pdf else _url("residuals.png"),
    }

    # Detect solver name from which log.<solver> file exists in artifact dir.
    solver = "unknown"
    for cand in ("simpleFoam", "icoFoam", "pimpleFoam", "buoyantFoam"):
        if (artifact_dir / f"log.{cand}").is_file():
            solver = cand
            break
    commit_sha = _get_commit_sha()

    # DEC-V61-052 Batch D: BFS scalar-anchor Xr/H comparison. Reads the
    # audit measurement + gold anchor and emits a compact scalar block
    # that the frontend Compare tab renders as a card (mirrors LDC D7
    # primary-vortex shape). Fail-soft: any missing piece → None, card
    # silently hides. Other visual-only cases (plane_channel_flow,
    # turbulent_flat_plate, etc.) see None here until their own anchors
    # are wired — this is intentionally narrow scope.
    metrics_reattachment: Optional[dict] = None
    paper_reattachment: Optional[dict] = None
    if case_id == "backward_facing_step":
        try:
            meas_path = (_REPO_ROOT / "ui/backend/tests/fixtures/runs"
                         / case_id / f"{run_label}_measurement.yaml")
            if meas_path.is_file():
                meas = yaml.safe_load(meas_path.read_text(encoding="utf-8")) or {}
                m = meas.get("measurement", {}) or {}
                actual = m.get("value")
                # DEC-V61-052 Codex r3 #3: prefer the explicit extractor
                # method key (wall_shear_tau_x_zero_crossing / near_wall_
                # tau_x_proxy_via_Ux) over the generic extraction_source
                # (key_quantities_direct / comparator_deviation / ...),
                # so the Compare tab can tell authoritative wall-shear
                # success from proxy fallback.
                method = m.get("reattachment_method") or m.get("extraction_source")
                if actual is not None:
                    gold = _load_bfs_reattachment_gold()
                    if gold is not None:
                        actual_f = float(actual)
                        expected = gold["value"]
                        dev_pct = (actual_f - expected) / expected * 100 if expected else 0.0
                        tol_pct = gold["tolerance"] * 100.0
                        metrics_reattachment = {
                            "quantity": "reattachment_length",
                            "symbol": "Xr/H",
                            "actual": actual_f,
                            "expected": expected,
                            "deviation_pct": dev_pct,
                            "tolerance_pct": tol_pct,
                            "within_tolerance": abs(dev_pct) <= tol_pct,
                            "method": method,
                        }
                        paper_reattachment = {
                            "source": gold["source"],
                            "doi": gold.get("literature_doi", ""),
                            "short": "Driver 1985 / LMK 1997",
                            "tolerance_pct": tol_pct,
                        }
        except (OSError, yaml.YAMLError, ValueError, TypeError):
            metrics_reattachment = None
            paper_reattachment = None

    # DEC-V61-053 Batch D: cylinder 4-scalar anchor cards (Type I case).
    # Mirrors BFS single-scalar pattern above × 4 observables:
    #   D-St   (strouhal_number, headline gate)
    #   D-Cd   (cd_mean)
    #   D-Cl   (cl_rms)
    #   D-u@4  (u_mean_centerline profile, 4 x_D stations)
    # Emission path: measurement.value is the headline St; cd_mean / cl_rms
    # / deficit_x_over_D_* come from measurement.secondary_scalars (Batch C
    # schema). Until a live solver run regenerates the fixture with the
    # new primary+secondary surface, all 4 return None (silently hidden).
    metrics_strouhal: Optional[dict] = None
    paper_strouhal: Optional[dict] = None
    metrics_cd_mean: Optional[dict] = None
    paper_cd_mean: Optional[dict] = None
    metrics_cl_rms: Optional[dict] = None
    paper_cl_rms: Optional[dict] = None
    metrics_u_centerline: Optional[dict] = None
    paper_u_centerline: Optional[dict] = None
    if case_id == "circular_cylinder_wake":
        try:
            meas_path = (_REPO_ROOT / "ui/backend/tests/fixtures/runs"
                         / case_id / f"{run_label}_measurement.yaml")
            if meas_path.is_file():
                meas = yaml.safe_load(meas_path.read_text(encoding="utf-8")) or {}
                m = meas.get("measurement", {}) or {}
                primary_quantity = m.get("quantity")
                primary_value = m.get("value")
                secondary = m.get("secondary_scalars") or {}

                # D-St · primary-scalar path
                if primary_quantity == "strouhal_number" and primary_value is not None:
                    gold = _load_cylinder_scalar_gold("strouhal_number")
                    if gold is not None:
                        actual_f = float(primary_value)
                        expected = gold["value"]
                        dev_pct = (actual_f - expected) / expected * 100 if expected else 0.0
                        tol_pct = gold["tolerance"] * 100.0
                        metrics_strouhal = {
                            "quantity": "strouhal_number",
                            "symbol": "St",
                            "actual": actual_f,
                            "expected": expected,
                            "deviation_pct": dev_pct,
                            "tolerance_pct": tol_pct,
                            "within_tolerance": abs(dev_pct) <= tol_pct,
                            "method": m.get("extraction_source"),
                        }
                        paper_strouhal = {
                            "source": gold["source"],
                            "doi": gold.get("literature_doi", ""),
                            "short": "Williamson 1996",
                            "tolerance_pct": tol_pct,
                        }

                # D-Cd, D-Cl · secondary_scalars path (Batch C schema)
                for sec_name, metrics_var_name, paper_var_name, symbol in [
                    ("cd_mean", "metrics_cd_mean", "paper_cd_mean", "C_d"),
                    ("cl_rms", "metrics_cl_rms", "paper_cl_rms", "C_l,rms"),
                ]:
                    sec_val = secondary.get(sec_name)
                    if isinstance(sec_val, (int, float)):
                        gold = _load_cylinder_scalar_gold(sec_name)
                        if gold is not None:
                            actual_f = float(sec_val)
                            expected = gold["value"]
                            dev_pct = (actual_f - expected) / expected * 100 if expected else 0.0
                            tol_pct = gold["tolerance"] * 100.0
                            _metrics_block = {
                                "quantity": sec_name,
                                "symbol": symbol,
                                "actual": actual_f,
                                "expected": expected,
                                "deviation_pct": dev_pct,
                                "tolerance_pct": tol_pct,
                                "within_tolerance": abs(dev_pct) <= tol_pct,
                                "method": "forceCoeffs_time_average",
                            }
                            _paper_block = {
                                "source": gold["source"],
                                "doi": gold.get("literature_doi", ""),
                                "short": "Williamson 1996",
                                "tolerance_pct": tol_pct,
                            }
                            if metrics_var_name == "metrics_cd_mean":
                                metrics_cd_mean = _metrics_block
                                paper_cd_mean = _paper_block
                            else:
                                metrics_cl_rms = _metrics_block
                                paper_cl_rms = _paper_block

                # D-u_centerline · 4-station profile from deficit_x_over_D_* keys
                gold_centerline = _load_cylinder_centerline_gold()
                if gold_centerline is not None:
                    station_rows: list[dict] = []
                    for gs in gold_centerline["stations"]:
                        x_D = gs["x_D"]
                        gold_deficit = gs["deficit"]
                        sec_key = f"deficit_x_over_D_{x_D}"
                        measured = secondary.get(sec_key)
                        if isinstance(measured, (int, float)):
                            actual_f = float(measured)
                            dev_pct = (actual_f - gold_deficit) / gold_deficit * 100 if gold_deficit else 0.0
                            station_rows.append({
                                "x_D": x_D,
                                "actual": actual_f,
                                "expected": gold_deficit,
                                "deviation_pct": dev_pct,
                                "within_tolerance": abs(dev_pct) <= gold_centerline["tolerance"] * 100.0,
                            })
                    if station_rows:
                        tol_pct = gold_centerline["tolerance"] * 100.0
                        all_pass = all(r["within_tolerance"] for r in station_rows)
                        metrics_u_centerline = {
                            "quantity": "u_mean_centerline",
                            "symbol": "u_deficit(x/D)",
                            "stations": station_rows,
                            "tolerance_pct": tol_pct,
                            "all_within_tolerance": all_pass,
                            "method": "sampleDict_cylinderCenterline_time_average",
                        }
                        paper_u_centerline = {
                            "source": gold_centerline["source"],
                            "doi": gold_centerline.get("literature_doi", ""),
                            "short": "Williamson 1996 Fig.19",
                            "tolerance_pct": tol_pct,
                        }
        except (OSError, yaml.YAMLError, ValueError, TypeError):
            # Fail-soft: any parse/type issue → all 4 stay None; UI hides cards silently.
            metrics_strouhal = None; paper_strouhal = None
            metrics_cd_mean = None; paper_cd_mean = None
            metrics_cl_rms = None; paper_cl_rms = None
            metrics_u_centerline = None; paper_u_centerline = None

    return {
        "visual_only": True,
        "case_id": case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "renders": renders,
        "solver": solver,
        "commit_sha": commit_sha,
        "verdict": None,
        "verdict_gradient": "#64748b 0%, #94a3b8 100%",
        "subtitle": (
            "Visual-only mode (DEC-V61-034 Tier C): real OpenFOAM field + "
            "residual evidence captured; per-case gold-overlay plumbing pending "
            "Phase 7c Sprint 2 (Tier B)."
        ),
        "paper": None,
        "metrics": None,
        "gci": None,
        "grid_convergence": None,
        "deviations": None,
        "residual_info": None,
        "tolerance_percent": None,
        # DEC-V61-052 Batch D: BFS scalar-anchor block.
        "metrics_reattachment": metrics_reattachment,
        "paper_reattachment": paper_reattachment,
        # DEC-V61-053 Batch D: cylinder 4-scalar + profile anchor blocks.
        "metrics_strouhal": metrics_strouhal,
        "paper_strouhal": paper_strouhal,
        "metrics_cd_mean": metrics_cd_mean,
        "paper_cd_mean": paper_cd_mean,
        "metrics_cl_rms": metrics_cl_rms,
        "paper_cl_rms": paper_cl_rms,
        "metrics_u_centerline": metrics_u_centerline,
        "paper_u_centerline": paper_u_centerline,
    }


def build_report_context(case_id: str, run_label: str = "audit_real_run", *, for_pdf: bool = False) -> dict:
    """Assemble all template variables. Raises ReportError on missing data.

    for_pdf: when True, the `renders.*_png` fields carry repo-relative
    paths (e.g. reports/phase5_renders/...) that WeasyPrint resolves
    against base_url=_REPO_ROOT. When False (default), those fields
    carry absolute HTTP URLs to the /api/cases/.../renders/{file}
    route so the HTML served at /api/cases/.../comparison-report
    actually displays images in a browser — without this, img srcs
    were resolved against the report URL and 404'd (2026-04-23
    user-reported bug).
    """
    if case_id not in _REPORT_SUPPORTED_CASES:
        raise ReportError(
            f"case_id={case_id!r} not in Phase 7 report scope. "
            f"Supported: {sorted(_REPORT_SUPPORTED_CASES)}."
        )

    run_manifest = _load_run_manifest(case_id, run_label)
    timestamp = _validated_timestamp(run_manifest.get("timestamp"))
    if timestamp is None:
        raise ReportError(
            f"invalid timestamp in run manifest for {case_id}/{run_label}"
        )
    artifact_dir = _FIELDS_ROOT / case_id / timestamp
    # Containment: must be inside _FIELDS_ROOT/case_id/ even after .resolve().
    try:
        artifact_dir.resolve(strict=True).relative_to(
            (_FIELDS_ROOT / case_id).resolve()
        )
    except (ValueError, OSError, FileNotFoundError):
        raise ReportError(f"artifact dir escapes fields root: {artifact_dir}")
    if not artifact_dir.is_dir():
        raise ReportError(f"artifact dir missing: {artifact_dir}")

    # Tier C: visual-only cases skip gold-overlay / verdict / GCI assembly.
    if case_id in _VISUAL_ONLY_CASES:
        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir, for_pdf=for_pdf)

    # Load + compute
    gold_y, gold_u, gold_doc = _load_ldc_gold()
    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
    latest_sample = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)

    # DEC-V61-050 batch 1: v_centerline second observable (Ghia Table II).
    # Best-effort: silently skip if gold block missing, xy file missing,
    # or sample file malformed (e.g., old fixtures predating the v
    # sampler). The u path above must work; v is additive evidence.
    metrics_v: dict[str, Any] | None = None
    v_tolerance: float | None = None
    v_gold_pair = _load_ldc_v_gold()
    if v_gold_pair is not None:
        gold_x, gold_v, v_doc = v_gold_pair
        v_tolerance = float(v_doc.get("tolerance", 0.05)) * 100.0
        v_xy_path = latest_sample / "vCenterline.xy"
        if v_xy_path.is_file():
            try:
                # v observable is U_y; in OF native xy format that is col 2.
                x_sim, v_sim = _load_sample_xy(v_xy_path, value_col=2)
                metrics_v = _compute_metrics(x_sim, v_sim, gold_x, gold_v, v_tolerance)
            except ReportError:
                metrics_v = None

    # DEC-V61-050 batches 3 + 4: primary vortex + secondary vortices via
    # ψ on a resampling of the audit VTK. Share the ψ grid + VTK-read
    # between both dimensions (one integration, two argmin windows) so
    # the cache hit stays warm.
    #
    # Codex round 1 MEDs: (a) widen exception envelope — pyvista/VTK can
    # raise RuntimeError/TypeError/KeyError/etc. beyond ImportError+OSError
    # +ValueError, so catch Exception here (this is an optional viz
    # dimension, not a critical path). (b) compute ψ wall-closure
    # residuals so the UI can flag when the observable scale is
    # dwarfed by numerical noise (especially secondary eddies ψ ~1e-6
    # vs typical wall residual ~1e-3 on 129² trapezoidal).
    metrics_primary_vortex: dict[str, Any] | None = None
    metrics_secondary_vortices: dict[str, Any] | None = None
    psi_wall_residuals: dict[str, Any] | None = None
    vortex_gold = _load_ldc_vortex_gold()
    secondary_gold = _load_ldc_secondary_vortices_gold()
    if vortex_gold is not None or secondary_gold is not None:
        try:
            from ui.backend.services.psi_extraction import (
                compute_streamfunction_from_vtk,
                find_vortex_core,
                pick_latest_internal_vtk,
                psi_wall_closure_residuals,
            )
            vtk_path = pick_latest_internal_vtk(artifact_dir / "VTK")
            if vtk_path is not None:
                psi_result = compute_streamfunction_from_vtk(vtk_path)
                if psi_result is not None:
                    psi, xs, ys = psi_result
                    psi_wall_residuals = psi_wall_closure_residuals(psi, xs, ys)
                    # --- Primary vortex (D7) ---
                    if vortex_gold is not None:
                        core = find_vortex_core(psi, xs, ys, mode="min")
                        if core is not None:
                            x_c_meas, y_c_meas, psi_meas = core
                            pos_err = float(
                                ((x_c_meas - vortex_gold["vortex_center_x"]) ** 2
                                 + (y_c_meas - vortex_gold["vortex_center_y"]) ** 2) ** 0.5
                            )
                            psi_gold_abs = abs(vortex_gold["psi_min"])
                            psi_err_pct = (
                                100.0 * abs(psi_meas - vortex_gold["psi_min"]) / psi_gold_abs
                                if psi_gold_abs > 1e-12 else 0.0
                            )
                            pos_pass = pos_err <= vortex_gold["position_tolerance"]
                            psi_pass = psi_err_pct <= vortex_gold["psi_tolerance"] * 100.0
                            # SNR — how far above the ψ wall-closure residual
                            # is the signal? Codex round 1 MED #2.
                            snr = (
                                psi_gold_abs / psi_wall_residuals["max"]
                                if psi_wall_residuals and psi_wall_residuals["max"] > 0
                                else None
                            )
                            metrics_primary_vortex = {
                                "x_meas": x_c_meas,
                                "y_meas": y_c_meas,
                                "psi_meas": psi_meas,
                                "x_gold": vortex_gold["vortex_center_x"],
                                "y_gold": vortex_gold["vortex_center_y"],
                                "psi_gold": vortex_gold["psi_min"],
                                "position_error": pos_err,
                                "psi_error_pct": psi_err_pct,
                                "position_tolerance": vortex_gold["position_tolerance"],
                                "psi_tolerance_pct": vortex_gold["psi_tolerance"] * 100.0,
                                "position_pass": pos_pass,
                                "psi_pass": psi_pass,
                                "all_pass": pos_pass and psi_pass,
                                "signal_to_residual_ratio": snr,
                                "signal_above_noise": snr is not None and snr >= 3.0,
                            }
                    # --- Secondary vortices BL/BR (D8) ---
                    if secondary_gold is not None:
                        eddy_results: list[dict] = []
                        for eddy in secondary_gold["eddies"]:
                            core = find_vortex_core(
                                psi, xs, ys,
                                x_window_norm=eddy["x_window_norm"],
                                y_window_norm=eddy["y_window_norm"],
                                mode=eddy["mode"],
                            )
                            if core is None:
                                continue
                            x_m, y_m, psi_m = core
                            pos_err = float(
                                ((x_m - eddy["x_gold"]) ** 2
                                 + (y_m - eddy["y_gold"]) ** 2) ** 0.5
                            )
                            psi_gold_abs = abs(eddy["psi_gold"])
                            psi_err_pct = (
                                100.0 * abs(psi_m - eddy["psi_gold"]) / psi_gold_abs
                                if psi_gold_abs > 1e-12 else 0.0
                            )
                            pos_pass = pos_err <= secondary_gold["position_tolerance"]
                            psi_pass = psi_err_pct <= secondary_gold["psi_tolerance"] * 100.0
                            # Per-eddy SNR vs wall-closure residual. Codex
                            # round 1 MED #2: BL ψ gold is O(1e-6), wall
                            # residual on 129² trapezoidal is O(1e-3), so
                            # BL signal is 2000× BELOW the numerical floor —
                            # the coordinate match is a coincidence of
                            # argmax landing near the Ghia point, NOT a
                            # validated physics reproduction. Expose this
                            # so the UI can flag it honestly.
                            snr = (
                                psi_gold_abs / psi_wall_residuals["max"]
                                if psi_wall_residuals and psi_wall_residuals["max"] > 0
                                else None
                            )
                            signal_above_noise = snr is not None and snr >= 3.0
                            eddy_results.append({
                                "name": eddy["name"],
                                "description": eddy["description"],
                                "x_meas": x_m,
                                "y_meas": y_m,
                                "psi_meas": psi_m,
                                "x_gold": eddy["x_gold"],
                                "y_gold": eddy["y_gold"],
                                "psi_gold": eddy["psi_gold"],
                                "position_error": pos_err,
                                "psi_error_pct": psi_err_pct,
                                "position_pass": pos_pass,
                                "psi_pass": psi_pass,
                                "all_pass": pos_pass and psi_pass and signal_above_noise,
                                "signal_to_residual_ratio": snr,
                                "signal_above_noise": signal_above_noise,
                            })
                        if eddy_results:
                            metrics_secondary_vortices = {
                                "eddies": eddy_results,
                                "position_tolerance": secondary_gold["position_tolerance"],
                                "psi_tolerance_pct": secondary_gold["psi_tolerance"] * 100.0,
                                "all_pass": all(e["all_pass"] for e in eddy_results),
                                "n_pass": sum(1 for e in eddy_results if e["all_pass"]),
                                "n_total": len(eddy_results),
                                "all_above_noise": all(
                                    e["signal_above_noise"] for e in eddy_results
                                ),
                                "any_above_noise": any(
                                    e["signal_above_noise"] for e in eddy_results
                                ),
                                # Codex round 3 MED: distinguish "at least one
                                # eddy is above noise AND fails tolerance" from
                                # "one passes above-noise + one is noise-floor".
                                # Only the former is a genuine physics deviation.
                                "any_above_noise_fail": any(
                                    e["signal_above_noise"] and not e["all_pass"]
                                    for e in eddy_results
                                ),
                            }
        except Exception:
            # Codex round 1 MED #4: pyvista/VTK sampling can raise a wide
            # variety of exceptions (RuntimeError, TypeError, KeyError,
            # pyvista.core.errors.*, VTK C++ exceptions surfaced as Python
            # RuntimeError, etc.). The D7/D8 dimensions are optional viz
            # augmentations — a pyvista internal failure must not 500 the
            # whole report endpoint. Broad catch is warranted here because
            # the comparator for u_centerline (D1-D5) is a separate code
            # path that's already run above and is not guarded by this
            # try/except. Real programmer bugs in psi_extraction itself
            # are caught in tests + by the module's __main__ smoke test.
            metrics_primary_vortex = None
            metrics_secondary_vortices = None
            psi_wall_residuals = None

    residual_info = _parse_residuals_csv(artifact_dir / "residuals.csv")
    grid_conv_rows, grid_note = _load_grid_convergence(case_id, gold_y, gold_u)
    # Phase 7d: Richardson extrapolation + GCI over the finest 3 meshes.
    try:
        from ui.backend.services.grid_convergence import compute_gci_from_fixtures
        gci = compute_gci_from_fixtures(case_id, fixture_root=_FIXTURE_ROOT)
    except (ValueError, ImportError, OverflowError, ArithmeticError):
        # Pathological mesh triples can still raise from deep math — the
        # grid_convergence module already catches these internally on the
        # documented branches, but belt-and-suspenders keeps report
        # generation from 500'ing on a numerical corner we did not predict.
        gci = None

    # Verdict logic: all-pass OR tolerance met.
    is_all_pass = metrics["n_pass"] == metrics["n_total"] and metrics["n_total"] > 0
    majority_pass = metrics["n_pass"] >= math.ceil(metrics["n_total"] * 0.6)
    if is_all_pass:
        verdict, verdict_gradient, subtitle = "PASS", "#059669 0%, #10b981 100%", (
            f"全部 {metrics['n_total']} 个 gold 点在 ±{tolerance:.1f}% 容差内。"
        )
    elif majority_pass:
        verdict, verdict_gradient, subtitle = "PARTIAL", "#d97706 0%, #f59e0b 100%", (
            f"{metrics['n_pass']}/{metrics['n_total']} 点通过；"
            f"{metrics['n_total'] - metrics['n_pass']} 点残差为已记录物理项 "
            f"(见 DEC-V61-030 关于 Ghia 非均匀网格 vs 均匀网格的插值误差)。"
        )
    else:
        verdict, verdict_gradient, subtitle = "FAIL", "#dc2626 0%, #ef4444 100%", (
            f"仅 {metrics['n_pass']}/{metrics['n_total']} 点通过 — "
            f"需要诊断 (solver, mesh, 或 gold 本身)。"
        )

    # Renders — use Phase 7b manifest if available; else None placeholders.
    # Codex round 1 HIGH: every manifest-supplied output path is validated to
    # resolve inside reports/phase5_renders/ before being emitted into HTML.
    renders_manifest = _load_renders_manifest(case_id, run_label)
    renders_dir = _RENDERS_ROOT / case_id / timestamp

    def _rel(key: str, default: str = "") -> str:
        candidate: Optional[str] = None
        if renders_manifest:
            raw = renders_manifest.get("outputs", {}).get(key)
            if isinstance(raw, str):
                validated = _safe_rel_under(raw, _RENDERS_ROOT)
                if validated:
                    candidate = validated
        if candidate is None:
            guess = renders_dir / default
            if guess.is_file():
                try:
                    rel = str(guess.resolve().relative_to(_REPO_ROOT.resolve()))
                    if _safe_rel_under(rel, _RENDERS_ROOT):
                        candidate = rel
                except ValueError:
                    pass
        return candidate or ""

    # _rel = repo-relative (PDF base_url=_REPO_ROOT resolves it).
    # _url = browser URL — fixes "all comparison report images fail to
    # load" when the HTML is served at /api/cases/.../comparison-report
    # (browser otherwise resolves `reports/...` src against the URL
    # path → /api/cases/X/runs/Y/reports/... which 404s; the working
    # renders route is /api/cases/X/runs/Y/renders/{basename}).
    def _url(basename: str) -> str:
        return f"/api/cases/{case_id}/runs/{run_label}/renders/{basename}"

    renders = {
        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
        "profile_png_url": _url("profile_u_centerline.png"),
        "pointwise_png_url": _url("pointwise_deviation.png"),
        "contour_png_url": _url("contour_u_magnitude.png"),
        "residuals_png_url": _url("residuals.png"),
        # Unified field read by the template.
        "profile_png": _rel("profile_png", "profile_u_centerline.png") if for_pdf else _url("profile_u_centerline.png"),
        "pointwise_png": _rel("pointwise_deviation_png", "pointwise_deviation.png") if for_pdf else _url("pointwise_deviation.png"),
        "contour_png": _rel("contour_u_magnitude_png", "contour_u_magnitude.png") if for_pdf else _url("contour_u_magnitude.png"),
        "residuals_png": _rel("residuals_png", "residuals.png") if for_pdf else _url("residuals.png"),
    }

    paper = {
        "title": gold_doc.get("source", "Ghia, Ghia & Shin 1982 — Lid-Driven Cavity benchmark"),
        "source": "J. Comput. Phys. 47, 387-411 (1982), Table I Re=100 column",
        "doi": gold_doc.get("literature_doi", "10.1016/0021-9991(82)90058-4"),
        "short": "Ghia 1982",
        "gold_count": metrics["n_total"],
        "tolerance_pct": tolerance,
    }

    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    return {
        "case_id": case_id,
        "case_display_name": "Lid-Driven Cavity (Re=100)" if case_id == "lid_driven_cavity" else case_id,
        "run_label": run_label,
        "timestamp": timestamp,
        "verdict": verdict,
        "verdict_gradient": verdict_gradient,
        "verdict_subtitle": subtitle,
        "metrics": metrics,
        "paper": paper,
        # DEC-V61-050 batch 1: v_centerline observable bundled as
        # sibling to metrics/paper. Both are optional — a case that
        # does not emit vCenterline.xy (or a YAML without the v block)
        # will see null here and frontend silently hides the D6 card.
        "metrics_v_centerline": metrics_v,
        "paper_v_centerline": (
            {
                "source": v_gold_pair[2].get(
                    "source",
                    "Ghia, Ghia & Shin 1982 — Table II Re=100 column",
                ),
                "doi": v_gold_pair[2].get(
                    "literature_doi", "10.1016/0021-9991(82)90058-4"
                ),
                "short": "Ghia 1982 Table II",
                "gold_count": metrics_v["n_total"] if metrics_v else 0,
                "tolerance_pct": v_tolerance,
            }
            if v_gold_pair is not None and metrics_v is not None
            else None
        ),
        # DEC-V61-050 batch 3: primary vortex (x_c, y_c, ψ_min) from 2D
        # argmin of ψ. Optional — null when pyvista missing, VTK
        # unreadable, or gold still has the pre-batch-3 shape. Frontend
        # D7 card silently hides on null.
        "metrics_primary_vortex": metrics_primary_vortex,
        "paper_primary_vortex": (
            {
                "source": vortex_gold["source"],
                "doi": vortex_gold["literature_doi"],
                "short": "Ghia 1982 Table III",
                "position_tolerance": vortex_gold["position_tolerance"],
                "psi_tolerance_pct": vortex_gold["psi_tolerance"] * 100.0,
            }
            if vortex_gold is not None and metrics_primary_vortex is not None
            else None
        ),
        # DEC-V61-050 batch 4: secondary vortices BL/BR from Ghia Table III
        # cells 3-4, extracted via corner-windowed ψ_max on the same 129²
        # grid used for primary vortex. Frontend D8 card silently hides
        # when null (same fail-soft pattern as D6/D7).
        # Codex round 1 MED #2: ψ wall-closure residuals — UI uses these
        # to render a "signal below noise floor" warning for D8 BL (ψ
        # ~1e-6 vs typical wall residual ~1e-3 on 129² trapezoidal ∫U_x
        # integration + pyvista resampling interpolation). Null when
        # extraction failed or gold blocks absent.
        "psi_wall_residuals": psi_wall_residuals,
        "metrics_secondary_vortices": metrics_secondary_vortices,
        "paper_secondary_vortices": (
            {
                "source": secondary_gold["source"],
                "doi": secondary_gold["literature_doi"],
                "short": "Ghia 1982 Table III (secondaries)",
                "position_tolerance": secondary_gold["position_tolerance"],
                "psi_tolerance_pct": secondary_gold["psi_tolerance"] * 100.0,
            }
            if secondary_gold is not None and metrics_secondary_vortices is not None
            else None
        ),
        "renders": renders,
        "contour_caption": (
            "2D |U| contour + streamlines 由 OpenFOAM VTK 体数据渲染（Phase 7b polish）。"
            "白色流线显示 LDC Re=100 的主涡结构；黄色高 |U| 区沿 lid 剪切层分布。"
        ),
        "residual_info": residual_info,
        "grid_conv": grid_conv_rows,
        "grid_conv_note": grid_note,
        "gci": _gci_to_template_dict(gci) if gci is not None else None,
        "meta": {
            "openfoam_version": "v10",
            "solver": "simpleFoam (SIMPLE, laminar)",
            "docker_image": "cfd-openfoam (local arm64 OpenFOAM v10)",
            "commit_sha": _get_commit_sha(),
            "mesh": "129×129 uniform",
            "tolerance": f"±{tolerance:.1f}%",
            "schemes": "steadyState + linearUpwind + Gauss linear corrected",
            "report_generated_at": now,
        },
    }


def render_report_html(case_id: str, run_label: str = "audit_real_run") -> str:
    """Return the full HTML string for the comparison report.

    Visual-only cases (DEC-V61-034 Tier C) have no gold-overlay data to render
    in the 8-section template — they expose their renders (contour + residuals
    PNG) via the JSON context + /renders/ route instead. Requesting the HTML
    report for a visual-only case raises ReportError which the route layer
    maps to 404 (Codex round 1 CR finding: prevents template UndefinedError
    500 on dereferencing `metrics.max_dev_pct` / `paper.title`).
    """
    ctx = build_report_context(case_id, run_label)
    if ctx.get("visual_only"):
        raise ReportError(
            f"case_id={case_id!r} is in Tier C visual-only mode — no 8-section "
            f"HTML/PDF report is produced. Use the JSON context at "
            f"/api/cases/{case_id}/runs/{run_label}/comparison-report/context "
            f"plus /api/cases/{case_id}/runs/{run_label}/renders/{{filename}} "
            f"to retrieve the contour + residuals renders directly."
        )
    tmpl = _env.get_template("comparison_report.html.j2")
    return tmpl.render(**ctx)


def render_report_pdf(case_id: str, run_label: str = "audit_real_run",
                      output_path: Optional[Path] = None) -> Path:
    """Render HTML to PDF via WeasyPrint and write to disk. Returns the file Path.

    Asset resolution: WeasyPrint converts the HTML's relative img src paths.
    We pass base_url=_REPO_ROOT so /reports/phase5_renders/... resolves correctly.

    Codex round 2 (2026-04-21): containment check runs BEFORE weasyprint import
    so ReportError from a malicious output_path is raised regardless of whether
    native libs are installed. Native load failures (libgobject etc.) surface
    as OSError and are mapped by the route layer to 503, same as ImportError.
    """
    # Codex round 1 HIGH: ensure PDF always lands under reports/phase5_reports/.
    # Codex round 2 MED: run containment FIRST, before WeasyPrint import so we
    # fail-closed on traversal even on systems where WeasyPrint native libs are
    # unavailable.
    # DEC-V61-034 Codex R2 comment: build context + visual-only guard BEFORE
    # the output_path branch so caller-supplied output_path callers also hit
    # the guard (avoids importing weasyprint only to have render_report_html
    # raise downstream).
    ctx = build_report_context(case_id, run_label, for_pdf=True)
    if ctx.get("visual_only"):
        raise ReportError(
            f"case_id={case_id!r} is in Tier C visual-only mode — no PDF "
            f"report is produced. Use the /renders/{{filename}} route for "
            f"contour + residuals PNG retrieval."
        )
    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
    if output_path is None:
        ts = ctx["timestamp"]  # already validated by build_report_context
        out_dir = reports_root / case_id / ts
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{run_label}_comparison_report.pdf"
    try:
        resolved_out = output_path.resolve(strict=False)
        # Must stay inside reports/phase5_reports/
        resolved_out.relative_to(reports_root)
    except (ValueError, OSError):
        raise ReportError(f"PDF output path escapes reports_root: {output_path}")

    # Import weasyprint lazily — heavy import, only when PDF actually needed.
    import weasyprint  # type: ignore  # ImportError → 503 via route layer.

    # Render the template with the for_pdf=True context (img srcs are
    # repo-rel paths that WeasyPrint resolves against base_url).
    # Deliberately not calling render_report_html — that builds a
    # for_pdf=False context whose img srcs are /api/ URLs, which
    # WeasyPrint cannot fetch without a live backend.
    tmpl = _env.get_template("comparison_report.html.j2")
    html = tmpl.render(**ctx)
    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
    doc.write_pdf(str(resolved_out))
    return resolved_out
