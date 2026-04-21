"""Validation-report assembly — reads YAML, builds the Screen 4 payload.

Phase 0 scope:
    - list_cases()              → GET /api/cases
    - load_case_detail(id)      → GET /api/cases/{id}
    - build_validation_report() → GET /api/validation-report/{id}

Phase 0 measurement sourcing strategy (in order):
    1. ui/backend/tests/fixtures/{case_id}_measurement.yaml
       (committed alongside the backend for deterministic demo data)
    2. None (returns MeasuredValue=None; UI renders "no run yet")

Phase 3 will extend this to pull from reports/**/slice_metrics.yaml
once live-run streaming is integrated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ui.backend.schemas.validation import (
    AuditConcern,
    CaseDetail,
    CaseIndexEntry,
    ContractStatus,
    DecisionLink,
    GoldStandardReference,
    MeasuredValue,
    Precondition,
    RunDescriptor,
    RunSummary,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Path resolution (repo-root relative)
# ---------------------------------------------------------------------------
# Layout:
#   <repo>/
#     knowledge/whitelist.yaml
#     knowledge/gold_standards/{case_id}.yaml
#     ui/backend/services/validation_report.py  ← this file
#     ui/backend/tests/fixtures/{case_id}_measurement.yaml
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[3]
WHITELIST_PATH = REPO_ROOT / "knowledge" / "whitelist.yaml"
GOLD_STANDARDS_DIR = REPO_ROOT / "knowledge" / "gold_standards"
FIXTURE_DIR = _HERE.parents[1] / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# YAML loaders (cached — Phase 0 content is stable during a server lifetime)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_whitelist() -> dict[str, dict[str, Any]]:
    """Return {case_id: case_def} from knowledge/whitelist.yaml."""
    if not WHITELIST_PATH.exists():
        return {}
    with WHITELIST_PATH.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    cases = doc.get("cases", [])
    out: dict[str, dict[str, Any]] = {}
    for entry in cases:
        cid = entry.get("id")
        if cid:
            out[cid] = entry
    return out


def _load_gold_standard(case_id: str) -> dict[str, Any] | None:
    """Read knowledge/gold_standards/{case_id}.yaml if present.

    Two on-disk shapes are supported:
        (A) Single document with top-level `observables: [{name, ref_value,
            tolerance, ...}]` + `physics_contract: {...}`
            (e.g. differential_heated_cavity, turbulent_flat_plate).
        (B) Multi-document — each YAML doc pins one quantity with
            top-level `quantity / reference_values / tolerance`; the
            first doc typically carries `physics_contract`
            (e.g. circular_cylinder_wake, lid_driven_cavity).

    Both shapes are normalised to (A)'s schema before returning, so
    downstream code only ever sees a single `observables: [...]`.
    """
    candidate = GOLD_STANDARDS_DIR / f"{case_id}.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        docs = [d for d in yaml.safe_load_all(fh) if d]
    if not docs:
        return None

    # Shape A — already has observables[] ⇒ return as-is.
    if len(docs) == 1 and isinstance(docs[0].get("observables"), list):
        return docs[0]

    # Shape B — synthesise an observables[] by flattening each doc.
    primary = docs[0]
    observables: list[dict[str, Any]] = []
    for doc in docs:
        quantity = doc.get("quantity")
        if not quantity:
            continue
        refs = doc.get("reference_values") or []
        ref_value: float | None = None
        unit = ""
        # Scan each reference_values entry for the first non-zero scalar
        # anchor under any known key. (First entry of a profile is often
        # a trivial u_plus=0 at y_plus=0 — picking the next non-zero
        # entry makes the contract engine produce meaningful PASS/FAIL
        # instead of collapsing deviation to 0.)
        scalar_keys = (
            "value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "Re_D", "St",
            "u_plus",
        )
        if refs and isinstance(refs[0], dict):
            unit = refs[0].get("unit", "") or ""
        for entry in refs:
            if not isinstance(entry, dict):
                continue
            for scalar_key in scalar_keys:
                val = entry.get(scalar_key)
                if isinstance(val, (int, float)) and float(val) != 0.0:
                    ref_value = float(val)
                    break
            if ref_value is not None:
                break
        # Fallback: if every entry was zero, accept the first scalar we
        # can find (even zero) to preserve prior behaviour.
        if ref_value is None and refs and isinstance(refs[0], dict):
            for scalar_key in scalar_keys:
                val = refs[0].get(scalar_key)
                if isinstance(val, (int, float)):
                    ref_value = float(val)
                    break
        observables.append(
            {
                "name": quantity,
                "ref_value": ref_value if ref_value is not None else 0.0,
                "unit": unit,
                "tolerance": doc.get("tolerance"),
                "description": (refs[0].get("description") if refs and isinstance(refs[0], dict) else None),
            }
        )
    return {
        "observables": observables,
        "physics_contract": primary.get("physics_contract") or {},
        "source": primary.get("source"),
        "literature_doi": primary.get("literature_doi"),
        "schema_version": primary.get("schema_version"),
        "case_id": primary.get("case_info", {}).get("id") or case_id,
    }


def _load_fixture_measurement(case_id: str) -> dict[str, Any] | None:
    """Read the legacy single-run fixture if present.

    Legacy path: ui/backend/tests/fixtures/{case_id}_measurement.yaml
    This is the pre-multi-run layout and is still honored for back-compat.
    If a multi-run directory exists at fixtures/runs/{case_id}/, those runs
    are preferred (see _list_runs + _load_run_measurement).
    """
    candidate = FIXTURE_DIR / f"{case_id}_measurement.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


RUNS_DIR = FIXTURE_DIR / "runs"


def _list_run_files(case_id: str) -> list[Path]:
    """Return run fixture paths under fixtures/runs/{case_id}/ sorted by
    run_id ascending. Empty list if the directory doesn't exist.
    """
    case_dir = RUNS_DIR / case_id
    if not case_dir.is_dir():
        return []
    return sorted(case_dir.glob("*_measurement.yaml"))


def _run_id_from_path(p: Path) -> str:
    # lid_driven_cavity/reference_pass_measurement.yaml → reference_pass
    return p.stem.removesuffix("_measurement")


_CATEGORY_ORDER: dict[str, int] = {
    "reference": 0,
    "real_incident": 1,
    "under_resolved": 2,
    "wrong_model": 3,
    "grid_convergence": 4,
}


def list_runs(case_id: str) -> list[RunDescriptor]:
    """Enumerate curated + legacy runs for a case.

    Ordering (pedagogical, stable across filesystem locales):
    1. `reference` first — students see "what done right looks like"
       at the top.
    2. `real_incident` next — actual production measurement, auditable
       reality.
    3. `under_resolved` / `wrong_model` — teaching variants.
    4. `grid_convergence` last — mesh-sweep runs live behind the Mesh
       tab and don't belong in the Compare run-picker's first page of
       attention.
    Within a category, sort by run_id ascending (mesh_20 before
    mesh_160 via zero-padded numeric comparison for `mesh_N` ids).
    Legacy `{case_id}_measurement.yaml` is exposed as run_id='legacy'
    only when the multi-run dir is empty.
    """
    runs: list[RunDescriptor] = []
    for path in _list_run_files(case_id):
        try:
            with path.open("r", encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
        except Exception:
            continue
        md = doc.get("run_metadata") or {}
        run_id = md.get("run_id") or _run_id_from_path(path)
        runs.append(
            RunDescriptor(
                run_id=run_id,
                label_zh=md.get("label_zh") or run_id.replace("_", " "),
                label_en=md.get("label_en", "") or "",
                description_zh=md.get("description_zh", "") or "",
                category=md.get("category", "reference"),
                expected_verdict=md.get("expected_verdict", "UNKNOWN"),
            )
        )
    if runs:
        def _sort_key(r: RunDescriptor) -> tuple[int, int, str]:
            cat_rank = _CATEGORY_ORDER.get(r.category, 99)
            # Numeric-aware secondary sort for mesh_N ids so mesh_20 sits
            # before mesh_160 instead of lexicographic (`mesh_160` < `mesh_20`).
            if r.run_id.startswith("mesh_"):
                try:
                    n = int(r.run_id.split("_", 1)[1])
                except ValueError:
                    n = 0
                return (cat_rank, n, r.run_id)
            return (cat_rank, 0, r.run_id)

        runs.sort(key=_sort_key)
        return runs

    legacy = _load_fixture_measurement(case_id)
    if legacy is not None:
        runs.append(
            RunDescriptor(
                run_id="legacy",
                label_zh=legacy.get("run_label_zh") or "历史测量",
                label_en="Legacy fixture",
                description_zh=(
                    legacy.get("run_description_zh")
                    or "来自 §5d 验收批次的原始测量值，保留作审计追溯用。"
                ),
                category="real_incident",
                expected_verdict="UNKNOWN",
            )
        )
    return runs


def _load_run_measurement(case_id: str, run_id: str) -> dict[str, Any] | None:
    """Load a specific run's measurement doc. Falls back to legacy fixture
    when run_id=='legacy'."""
    if run_id == "legacy":
        return _load_fixture_measurement(case_id)
    candidate = RUNS_DIR / case_id / f"{run_id}_measurement.yaml"
    if not candidate.exists():
        return None
    with candidate.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _pick_default_run_id(case_id: str) -> str | None:
    """Default run resolution rule: prefer the first 'reference' category
    run (so the default validation-report shows a PASS narrative), else
    fall back to the first run of any category, else 'legacy' if a
    legacy fixture is on disk."""
    runs = list_runs(case_id)
    for r in runs:
        if r.category == "reference":
            return r.run_id
    if runs:
        return runs[0].run_id
    # No curated runs, no legacy fixture either
    return None


# ---------------------------------------------------------------------------
# Mappers — YAML dict → Pydantic schema
# ---------------------------------------------------------------------------
def _tolerance_scalar(value: Any) -> float | None:
    """Normalise tolerance-shaped YAML (scalar OR {mode, value} dict)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        inner = value.get("value")
        if isinstance(inner, (int, float)):
            return float(inner)
    return None


def _make_gold_reference(
    case: dict[str, Any],
    gs_doc: dict[str, Any] | None,
) -> GoldStandardReference | None:
    """Extract the anchor ref_value + tolerance from either the
    whitelist `gold_standard` block or the gold_standards/*.yaml
    `observables[*]` (preferring the one matching the whitelist
    `gold_standard.quantity` to stay quantity-faithful)."""
    citation = case.get("reference") or (gs_doc or {}).get("source", "")
    doi = case.get("doi") or (gs_doc or {}).get("literature_doi")
    wl_gs = case.get("gold_standard") or {}
    target_quantity = wl_gs.get("quantity")

    # Prefer matching observable from gold_standards/*.yaml.
    if gs_doc:
        observables = gs_doc.get("observables") or []
        ob: dict[str, Any] | None = None
        if target_quantity:
            for candidate in observables:
                if candidate.get("name") == target_quantity:
                    ob = candidate
                    break
        if ob is None and observables:
            ob = observables[0]
        if ob is not None:
            tolerance = _tolerance_scalar(ob.get("tolerance"))
            if tolerance is None:
                tolerance = _tolerance_scalar(wl_gs.get("tolerance"))
            if tolerance is None:
                tolerance = 0.1  # conservative default
            ref_value = ob.get("ref_value")
            if isinstance(ref_value, (int, float)):
                return GoldStandardReference(
                    quantity=ob.get("name") or target_quantity or "unknown",
                    ref_value=float(ref_value),
                    unit=ob.get("unit", "") or "",
                    tolerance_pct=float(tolerance),
                    citation=citation or "",
                    doi=doi,
                )
            # Profile-shaped ref_value (list of {x, y/value} dicts) — fall
            # through to wl_gs.reference_values scanning below, which picks
            # the first non-zero scalar anchor (Cp at stagnation, etc.) so
            # the contract engine can produce meaningful PASS/FAIL on
            # cases like naca0012_airfoil whose gold is a Cp profile.

    # Fallback: synthesize from whitelist.yaml `gold_standard` inline.
    refs = wl_gs.get("reference_values") or []
    if not refs:
        return None
    value: float | None = None
    # Scan entries for the first non-zero scalar under any known key.
    # (First entry of a profile is often a trivial anchor like u_plus=0
    # at y_plus=0; skipping-to-first-nonzero gives the engine a
    # pedagogically meaningful ref.)
    value_keys = ("value", "Cf", "f", "Nu", "u", "u_Uinf", "Cp", "u_plus")
    first = refs[0]
    for entry in refs:
        if not isinstance(entry, dict):
            continue
        for key in value_keys:
            if key in entry and isinstance(entry[key], (int, float)):
                if float(entry[key]) != 0.0:
                    value = float(entry[key])
                    first = entry
                    break
        if value is not None:
            break
    # If every entry is zero (or none match), fall back to the very first
    # dict's first matching key (even if zero) to preserve prior behavior.
    if value is None:
        if not isinstance(first, dict):
            return None
        for key in value_keys:
            if key in first and isinstance(first[key], (int, float)):
                value = float(first[key])
                break
    if value is None:
        return None
    tol = _tolerance_scalar(wl_gs.get("tolerance")) or 0.1
    return GoldStandardReference(
        quantity=wl_gs.get("quantity", "unknown"),
        ref_value=value,
        unit=first.get("unit", "") or "",
        tolerance_pct=tol,
        citation=citation or "",
        doi=doi,
    )


def _make_preconditions(gs_doc: dict[str, Any] | None) -> list[Precondition]:
    if not gs_doc:
        return []
    physics_contract = gs_doc.get("physics_contract") or {}
    rows = physics_contract.get("physics_precondition") or []
    out: list[Precondition] = []
    for row in rows:
        out.append(
            Precondition(
                condition=row.get("condition", ""),
                satisfied=bool(row.get("satisfied_by_current_adapter", False)),
                evidence_ref=row.get("evidence_ref"),
                consequence_if_unsatisfied=row.get("consequence_if_unsatisfied"),
            )
        )
    return out


def _make_audit_concerns(
    gs_doc: dict[str, Any] | None,
    measurement_doc: dict[str, Any] | None,
) -> list[AuditConcern]:
    out: list[AuditConcern] = []
    # (1) Contract-status narrative from gold_standards → top-level concern.
    if gs_doc:
        status_narrative = (
            (gs_doc.get("physics_contract") or {}).get("contract_status") or ""
        ).strip()
        if status_narrative:
            out.append(
                AuditConcern(
                    concern_type="CONTRACT_STATUS",
                    summary=(
                        status_narrative.splitlines()[0][:240]
                        if status_narrative
                        else ""
                    ),
                    detail=status_narrative,
                    decision_refs=_extract_decision_refs(status_narrative),
                )
            )
    # (2) Measurement-level audit concerns (fixture or slice_metrics).
    if measurement_doc:
        for concern in measurement_doc.get("audit_concerns", []) or []:
            out.append(
                AuditConcern(
                    concern_type=concern.get("concern_type", "UNKNOWN"),
                    summary=concern.get("summary", ""),
                    detail=concern.get("detail"),
                    decision_refs=concern.get("decision_refs", []) or [],
                )
            )
    return out


def _extract_decision_refs(text: str) -> list[str]:
    """Pull DEC-ADWM-00N / DEC-V61-00N tokens out of narrative text."""
    import re

    return sorted(set(re.findall(r"DEC-(?:ADWM|V61)-\d{3}", text)))


def _make_decisions_trail(
    measurement_doc: dict[str, Any] | None,
) -> list[DecisionLink]:
    if not measurement_doc:
        return []
    out: list[DecisionLink] = []
    for row in measurement_doc.get("decisions_trail", []) or []:
        out.append(
            DecisionLink(
                decision_id=row.get("decision_id", ""),
                date=row.get("date", ""),
                title=row.get("title", ""),
                autonomous=bool(row.get("autonomous", False)),
            )
        )
    return out


def _derive_contract_status(
    gs_ref: GoldStandardReference,
    measurement: MeasuredValue | None,
    preconditions: list[Precondition],
    audit_concerns: list[AuditConcern],
) -> tuple[ContractStatus, float | None, bool | None, float, float]:
    """Compute the three-state contract status + tolerance bounds.

    Returns (status, deviation_pct, within_tolerance, lower, upper)."""
    # For negative ref_values the naive (1-tol)*ref > (1+tol)*ref, so
    # take min/max to keep `lower` as the numerically smaller bound.
    # This matters for LDC where u_centerline can be negative near the
    # bottom-left corner (Ghia Re=100 at y=0.0625 gives u/U = -0.03717).
    bound_a = gs_ref.ref_value * (1.0 - gs_ref.tolerance_pct)
    bound_b = gs_ref.ref_value * (1.0 + gs_ref.tolerance_pct)
    lower = min(bound_a, bound_b)
    upper = max(bound_a, bound_b)

    if measurement is None:
        return ("UNKNOWN", None, None, lower, upper)

    deviation_pct = 0.0
    if gs_ref.ref_value != 0.0:
        deviation_pct = (measurement.value - gs_ref.ref_value) / gs_ref.ref_value * 100.0

    # Tolerance test in deviation space (sign-invariant + consistent with
    # the percentage shown in the UI). `within_tolerance` matches when
    # |deviation| <= tolerance_pct expressed as a percentage.
    within = abs(deviation_pct) <= gs_ref.tolerance_pct * 100.0
    precondition_fails = any(not p.satisfied for p in preconditions)
    has_silent_pass_hazard = any(
        "SILENT_PASS_HAZARD" in c.concern_type or "SILENT_PASS_HAZARD" in (c.summary or "")
        or "SILENT_PASS_HAZARD" in (c.detail or "")
        for c in audit_concerns
    )

    if not within:
        return ("FAIL", deviation_pct, within, lower, upper)
    if precondition_fails or has_silent_pass_hazard:
        return ("HAZARD", deviation_pct, within, lower, upper)
    return ("PASS", deviation_pct, within, lower, upper)


def _make_measurement(doc: dict[str, Any] | None) -> MeasuredValue | None:
    if not doc:
        return None
    m = doc.get("measurement") or {}
    if "value" not in m:
        return None
    return MeasuredValue(
        value=float(m["value"]),
        unit=m.get("unit", "") or "",
        source=doc.get("source", "fixture"),
        run_id=m.get("run_id"),
        commit_sha=m.get("commit_sha"),
        measured_at=m.get("measured_at"),
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
def list_cases() -> list[CaseIndexEntry]:
    whitelist = _load_whitelist()
    out: list[CaseIndexEntry] = []
    for cid, case in whitelist.items():
        gs = _load_gold_standard(cid)
        # Use the same default-run resolution as build_validation_report so
        # the catalog contract_status matches what the Compare tab shows on
        # first click (reference_pass preferred → student's first impression
        # is PASS when curated).
        default_run_id = _pick_default_run_id(cid)
        measurement_doc = (
            _load_run_measurement(cid, default_run_id) if default_run_id else None
        )
        gs_ref = _make_gold_reference(case, gs)
        preconditions = _make_preconditions(gs)
        audit_concerns = _make_audit_concerns(gs, measurement_doc)
        measurement = _make_measurement(measurement_doc)
        if gs_ref is not None:
            status, *_ = _derive_contract_status(
                gs_ref, measurement, preconditions, audit_concerns
            )
        else:
            status = "UNKNOWN"
        # Run distribution for the catalog-card badge. Evaluate every run
        # through the actual contract engine — never report `expected_verdict`,
        # which is only a curator hint and can drift from the live contract
        # (e.g. a `PASS`-hinted run whose gold arms a silent-pass hazard).
        runs = list_runs(cid)
        verdict_counts: dict[str, int] = {}
        for r in runs:
            run_doc = _load_run_measurement(cid, r.run_id)
            run_audits = _make_audit_concerns(gs, run_doc)
            run_measurement = _make_measurement(run_doc)
            if gs_ref is not None:
                run_status, *_ = _derive_contract_status(
                    gs_ref, run_measurement, preconditions, run_audits
                )
            else:
                run_status = "UNKNOWN"
            verdict_counts[run_status] = verdict_counts.get(run_status, 0) + 1
        run_summary = RunSummary(total=len(runs), verdict_counts=verdict_counts)
        out.append(
            CaseIndexEntry(
                case_id=cid,
                name=case.get("name", cid),
                flow_type=case.get("flow_type", "UNKNOWN"),
                geometry_type=case.get("geometry_type", "UNKNOWN"),
                turbulence_model=case.get("turbulence_model", "UNKNOWN"),
                has_gold_standard=gs is not None,
                has_measurement=measurement is not None,
                run_summary=run_summary,
                contract_status=status,
            )
        )
    return out


def load_case_detail(case_id: str) -> CaseDetail | None:
    whitelist = _load_whitelist()
    case = whitelist.get(case_id)
    if case is None:
        return None
    gs = _load_gold_standard(case_id)
    gs_ref = _make_gold_reference(case, gs)
    preconditions = _make_preconditions(gs)
    narrative = None
    if gs:
        narrative = (gs.get("physics_contract") or {}).get("contract_status")
        if isinstance(narrative, str):
            narrative = narrative.strip() or None
    return CaseDetail(
        case_id=case_id,
        name=case.get("name", case_id),
        reference=case.get("reference"),
        doi=case.get("doi"),
        flow_type=case.get("flow_type", "UNKNOWN"),
        geometry_type=case.get("geometry_type", "UNKNOWN"),
        compressibility=case.get("compressibility"),
        steady_state=case.get("steady_state"),
        solver=case.get("solver"),
        turbulence_model=case.get("turbulence_model", "UNKNOWN"),
        parameters=case.get("parameters") or {},
        gold_standard=gs_ref,
        preconditions=preconditions,
        contract_status_narrative=narrative,
    )


def build_validation_report(
    case_id: str,
    run_id: str | None = None,
) -> ValidationReport | None:
    """Build the Screen-4 validation report for a case.

    Run resolution:
    - If `run_id` is None, resolves to the first 'reference' run (so
      default view shows PASS narrative where curated), falling back to
      any curated run, then to the legacy {case_id}_measurement.yaml
      fixture.
    - If `run_id` is provided but doesn't exist, returns None (treat
      as 404 at the route layer).
    """
    case_detail = load_case_detail(case_id)
    if case_detail is None or case_detail.gold_standard is None:
        return None
    gs = _load_gold_standard(case_id)

    # Resolve which run's measurement to load.
    if run_id is None:
        resolved_run_id = _pick_default_run_id(case_id)
    else:
        resolved_run_id = run_id

    if resolved_run_id is None:
        # No fixture at all for this case — report renders with measurement=None.
        measurement_doc = None
    else:
        measurement_doc = _load_run_measurement(case_id, resolved_run_id)
        if measurement_doc is None and run_id is not None:
            # User explicitly asked for an unknown run_id.
            return None
    measurement = _make_measurement(measurement_doc)
    preconditions = case_detail.preconditions
    audit_concerns = _make_audit_concerns(gs, measurement_doc)
    decisions_trail = _make_decisions_trail(measurement_doc)
    status, deviation, within, lower, upper = _derive_contract_status(
        case_detail.gold_standard, measurement, preconditions, audit_concerns
    )
    return ValidationReport(
        case=case_detail,
        gold_standard=case_detail.gold_standard,
        measurement=measurement,
        contract_status=status,
        deviation_pct=deviation,
        within_tolerance=within,
        tolerance_lower=lower,
        tolerance_upper=upper,
        audit_concerns=audit_concerns,
        preconditions=preconditions,
        decisions_trail=decisions_trail,
    )
