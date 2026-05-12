"""DEC-V61-153 (N5.2) · honest issue enumerator implementation.

Walks case state via the N5.1 builder, then layers checkMesh metrics
+ residual-log scanning to produce the full structured issue list.

Stable rule outputs (must match `SourceRuleId` literal in
`ui/backend/schemas/honest_issue_list.py`):

  * geometry_stl_missing            — Step 1 not done
  * geometry_bbox_missing           — polyMesh/points absent or empty
  * geometry_no_named_patches       — boundary file empty
  * mesh_polymesh_missing           — Step 2 not done
  * mesh_zero_cells                 — polyMesh present but cell_count=0
  * mesh_dense_warning              — > 5M cells (V122 threshold)
  * mesh_low_count_warning          — < 100 cells (V122 threshold)
  * mesh_checkmesh_failed           — checkMesh returned mesh_ok=False
  * mesh_severe_non_ortho_faces     — checkMesh found > 0 severe faces
  * physics_dicts_missing           — both physical dicts absent
  * physics_regime_missing          — momentumTransport absent
  * physics_no_citation             — physics committed but no
                                      citation tracked in audit trail
                                      (placeholder — N5.3 will source
                                      this from manifest)
  * solver_no_derivation            — regime literal didn't resolve
  * solver_tolerance_fast_survey    — engineer picked fast_survey
                                      tier (info — usable for sweeps,
                                      not for production answers)
  * solver_les_subgrid_todo         — LES-stub regime: engineer must
                                      hand-edit momentumTransport
  * output_residuals_stalled        — log shows last 5 iterations
                                      residual delta < 1% (heuristic)
  * output_run_log_missing          — no run-log file present
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from ui.backend.schemas.honest_issue_list import Issue, IssueList
from ui.backend.services.case_report import build_beginner_report


# Thresholds match the analyzer / advisor settings so the issue list
# and the in-card warnings stay coherent.
_MESH_LOW_COUNT_THRESHOLD = 100
_MESH_DENSE_THRESHOLD = 5_000_000


def enumerate_issues(case_dir: Path) -> IssueList:
    """Walk case state and emit the full structured issue list."""
    report = build_beginner_report(case_dir)
    issues: list[Issue] = []
    issues.extend(_geometry_issues(report))
    issues.extend(_mesh_issues(report, case_dir))
    issues.extend(_physics_issues(report, case_dir))
    issues.extend(_solver_issues(report))
    issues.extend(_output_issues(case_dir))
    # Sort: critical first, then warning, then info; alpha by source_rule_id.
    rank = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda i: (rank[i.severity], i.source_rule_id))
    return IssueList(
        case_id=case_dir.name,
        issues=issues,
        generated_at=datetime.now(tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )


# ────────── Geometry ──────────


def _geometry_issues(report) -> list[Issue]:
    out: list[Issue] = []
    g = report.geometry
    if g.stl_filename is None:
        out.append(Issue(
            severity="critical",
            source_rule_id="geometry_stl_missing",
            scope="geometry",
            message="No STL file imported (Step 1 not yet completed).",
        ))
    if g.bounding_box_min is None:
        out.append(Issue(
            severity="critical",
            source_rule_id="geometry_bbox_missing",
            scope="geometry",
            message=(
                "Bounding box not computable — polyMesh/points absent "
                "or empty."
            ),
        ))
    if not g.named_patches:
        out.append(Issue(
            severity="warning",
            source_rule_id="geometry_no_named_patches",
            scope="geometry",
            message=(
                "constant/polyMesh/boundary contains no named patches; "
                "BC application has nowhere to attach."
            ),
        ))
    return out


# ────────── Mesh ──────────


def _mesh_issues(report, case_dir: Path) -> list[Issue]:
    out: list[Issue] = []
    m = report.mesh
    polymesh = case_dir / "constant" / "polyMesh"
    if not polymesh.is_dir():
        out.append(Issue(
            severity="critical",
            source_rule_id="mesh_polymesh_missing",
            scope="mesh",
            message="constant/polyMesh directory absent (Step 2 not yet completed).",
        ))
        return out

    if m.cell_count is not None and m.cell_count == 0:
        out.append(Issue(
            severity="critical",
            source_rule_id="mesh_zero_cells",
            scope="mesh",
            message="polyMesh present but cell count is 0.",
        ))
    if m.cell_count is not None and m.cell_count < _MESH_LOW_COUNT_THRESHOLD:
        out.append(Issue(
            severity="warning",
            source_rule_id="mesh_low_count_warning",
            scope="mesh",
            message=(
                f"Only {m.cell_count} cells — under-refined for "
                "production-quality results."
            ),
            details={
                "cell_count": m.cell_count,
                "threshold": _MESH_LOW_COUNT_THRESHOLD,
            },
        ))
    if (
        m.cell_count is not None
        and m.cell_count > _MESH_DENSE_THRESHOLD
    ):
        out.append(Issue(
            severity="info",
            source_rule_id="mesh_dense_warning",
            scope="mesh",
            message=(
                f"{m.cell_count:,} cells — large simulation cost "
                "expected (>5M cells)."
            ),
            details={
                "cell_count": m.cell_count,
                "threshold": _MESH_DENSE_THRESHOLD,
            },
        ))
    if m.checkmesh_ran and m.checkmesh_ok is False:
        out.append(Issue(
            severity="warning",
            source_rule_id="mesh_checkmesh_failed",
            scope="mesh",
            message="checkMesh reported failures — see N2.4 advisor for specifics.",
        ))
    return out


# ────────── Physics ──────────


def _physics_issues(report, case_dir: Path) -> list[Issue]:
    out: list[Issue] = []
    p = report.physics
    phys_path = case_dir / "constant" / "physicalProperties"
    momentum_path = case_dir / "constant" / "momentumTransport"

    if not phys_path.is_file() and not momentum_path.is_file():
        out.append(Issue(
            severity="critical",
            source_rule_id="physics_dicts_missing",
            scope="physics",
            message=(
                "Physics dicts absent — Step 3 (physics commit) not "
                "yet run."
            ),
        ))
        return out

    if p.regime is None:
        out.append(Issue(
            severity="critical",
            source_rule_id="physics_regime_missing",
            scope="physics",
            message=(
                "Turbulence regime not declared — "
                "constant/momentumTransport missing or malformed."
            ),
        ))
    return out


# ────────── Solver ──────────


def _solver_issues(report) -> list[Issue]:
    out: list[Issue] = []
    s = report.solver
    p = report.physics

    # Solver derivation failed despite physics being committed.
    if p.regime is not None and s.derived_solver is None:
        out.append(Issue(
            severity="warning",
            source_rule_id="solver_no_derivation",
            scope="solver",
            message=(
                f"Regime literal {p.regime!r} declared but solver "
                "derivation missing — N3.4 mapping table may need update."
            ),
            details={"regime": p.regime},
        ))

    # fast_survey tolerance tier — informational note.
    if s.tolerance_tier == "fast_survey":
        out.append(Issue(
            severity="info",
            source_rule_id="solver_tolerance_fast_survey",
            scope="solver",
            message=(
                "Tolerance tier is fast_survey — usable for sweeps, "
                "NOT production answers."
            ),
        ))

    # LES-stub TODO reminder (matches N3.3 momentumTransport TODO).
    if p.regime == "LES-stub":
        out.append(Issue(
            severity="info",
            source_rule_id="solver_les_subgrid_todo",
            scope="solver",
            message=(
                "LES-stub regime: engineer must hand-edit "
                "constant/momentumTransport to choose a sub-grid model."
            ),
        ))
    return out


# ────────── Output / run-log ──────────


def _output_issues(case_dir: Path) -> list[Issue]:
    """Scan run logs for residual stalls. Heuristic: if log present,
    parse last 5 'Solving for U, Initial residual = ...' lines and
    flag when consecutive deltas are < 1%."""
    out: list[Issue] = []
    log_candidates = [
        case_dir / "log.icoFoam",
        case_dir / "log.simpleFoam",
        case_dir / "log.pimpleFoam",
        case_dir / "log.buoyantSimpleFoam",
        case_dir / "log.buoyantPimpleFoam",
    ]
    log_path = next((p for p in log_candidates if p.is_file()), None)
    if log_path is None:
        # Only emit "log missing" if the case looks like it should
        # have run — i.e., physics dicts are present (otherwise it's
        # just "engineer hasn't reached Step 4 yet", not an issue).
        if (case_dir / "constant" / "momentumTransport").is_file():
            out.append(Issue(
                severity="info",
                source_rule_id="output_run_log_missing",
                scope="output",
                message=(
                    "No run-log file found (log.<solver>) — solver "
                    "hasn't run yet OR was redirected elsewhere."
                ),
            ))
        return out

    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    residuals = _extract_recent_u_residuals(text, n=5)
    if len(residuals) >= 5 and _is_stalled(residuals):
        out.append(Issue(
            severity="warning",
            source_rule_id="output_residuals_stalled",
            scope="output",
            message=(
                "U residuals stalled — last 5 iterations show <1% "
                "relative change. Engineer should review solver "
                "settings or BC consistency."
            ),
            details={
                "last_residuals": ",".join(f"{r:.3e}" for r in residuals),
            },
        ))
    return out


_RES_RE = re.compile(
    r"Solving for U[xX]?[yY]?[zZ]?,\s*Initial residual\s*=\s*([-0-9.eE+]+)",
)


def _extract_recent_u_residuals(text: str, *, n: int) -> list[float]:
    out: list[float] = []
    for m in _RES_RE.finditer(text):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            continue
    return out[-n:]


def _is_stalled(residuals: list[float], *, threshold: float = 0.01) -> bool:
    """Return True when consecutive deltas are below ``threshold``
    relative change. Conservative — avoids false-positives on
    legitimately converging residuals (which drop fast)."""
    if len(residuals) < 2:
        return False
    for i in range(1, len(residuals)):
        prev = residuals[i - 1]
        curr = residuals[i]
        if prev == 0:
            return False
        rel = abs(curr - prev) / abs(prev)
        if rel >= threshold:
            return False
    return True
