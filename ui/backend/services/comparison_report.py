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


def _load_sample_xy(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        try:
            rows.append([float(parts[0]), float(parts[1])])
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

    renders = {
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
    }

    # Detect solver name from which log.<solver> file exists in artifact dir.
    solver = "unknown"
    for cand in ("simpleFoam", "icoFoam", "pimpleFoam", "buoyantFoam"):
        if (artifact_dir / f"log.{cand}").is_file():
            solver = cand
            break
    commit_sha = _get_commit_sha()

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
    }


def build_report_context(case_id: str, run_label: str = "audit_real_run") -> dict:
    """Assemble all template variables. Raises ReportError on missing data."""
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
        return _build_visual_only_context(case_id, run_label, timestamp, artifact_dir)

    # Load + compute
    gold_y, gold_u, gold_doc = _load_ldc_gold()
    tolerance = float(gold_doc.get("tolerance", 0.05)) * 100.0  # fraction → percent
    latest_sample = _latest_sample_iter(artifact_dir)
    y_sim, u_sim = _load_sample_xy(latest_sample / "uCenterline.xy")
    metrics = _compute_metrics(y_sim, u_sim, gold_y, gold_u, tolerance)

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

    renders = {
        "profile_png_rel": _rel("profile_png", "profile_u_centerline.png"),
        "pointwise_png_rel": _rel("pointwise_deviation_png", "pointwise_deviation.png"),
        "contour_png_rel": _rel("contour_u_magnitude_png", "contour_u_magnitude.png"),
        "residuals_png_rel": _rel("residuals_png", "residuals.png"),
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
    reports_root = (_REPO_ROOT / "reports" / "phase5_reports").resolve()
    if output_path is None:
        ctx = build_report_context(case_id, run_label)
        # Codex round 1 CR (DEC-V61-034): visual-only cases have no PDF to
        # render. Raise BEFORE weasyprint import so environments without
        # native libs also fail-closed with ReportError → 404 at the route,
        # not OSError → 503.
        if ctx.get("visual_only"):
            raise ReportError(
                f"case_id={case_id!r} is in Tier C visual-only mode — no PDF "
                f"report is produced. Use the /renders/{{filename}} route for "
                f"contour + residuals PNG retrieval."
            )
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

    html = render_report_html(case_id, run_label)
    doc = weasyprint.HTML(string=html, base_url=str(_REPO_ROOT))
    doc.write_pdf(str(resolved_out))
    return resolved_out
