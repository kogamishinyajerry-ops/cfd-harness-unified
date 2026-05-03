"""DEC-V61-116 · case-completeness analyzer.

Resolves a `case_id` to its current YAML, classifies its provenance
(whitelist · imported_user · draft), runs the matching rule set, and
returns a `CaseCompletenessReport` listing every field the engineer
still needs to fill in before the case meets the archive contract.

Read-only. No side-effects on case files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ui.backend.services.case_manifest import (
    CaseManifest,
    ManifestNotFoundError,
    ManifestParseError,
    read_case_manifest,
)
from ui.backend.services.case_scaffold.template_clone import IMPORTED_DIR
from ui.backend.services.validation_report import (
    _load_gold_standard,
    _load_whitelist,
)

from .schemas import CaseCompletenessReport, CaseKind, MissingField, Severity


# Drafts that live as a flat YAML doc directly under user_drafts/. Mirrors
# the storage convention `case_drafts.DRAFTS_DIR`. We re-derive the path
# locally to avoid importing case_drafts (which would couple this read-only
# service to the writable editor).
from ui.backend.services.case_drafts import DRAFTS_DIR


# Re-appropriate turbulence threshold. Above this Re, a `laminar`
# turbulence model is flagged as critical — the simulation will trigger
# numerical instability or yield non-physical results in the steady RANS
# case. Below it, laminar is acceptable. Source: standard CFD textbook
# practice (turbulent transition for internal flows ~ 2300; external
# boundary layers ~ 5e5). We use 2000 as a conservative single threshold
# since the analyzer doesn't currently distinguish internal/external from
# the manifest. This is one place a future v2 could refine.
_RE_LAMINAR_CEILING = 2000.0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CaseNotFoundError(Exception):
    """Raised when no whitelist entry, draft YAML, or imported case_dir
    exists for a given case_id. Routes catch this and return 404."""


# ---------------------------------------------------------------------------
# Resolution: which storage holds this case_id?
# ---------------------------------------------------------------------------


def _resolve_imported_dir(case_id: str) -> Path | None:
    """Return the imported case_dir if present, else None."""
    candidate = IMPORTED_DIR / case_id / "case_manifest.yaml"
    return candidate.parent if candidate.is_file() else None


def _resolve_flat_draft(case_id: str) -> Path | None:
    """Return the flat draft YAML path if present, else None."""
    candidate = DRAFTS_DIR / f"{case_id}.yaml"
    return candidate if candidate.is_file() else None


def _read_flat_yaml(path: Path) -> dict[str, Any]:
    """Read a flat draft / whitelist-style YAML doc into a dict.

    Returns an empty dict (not None) on parse failure so downstream rule
    checks treat it as 'every field missing' rather than crashing.
    """
    try:
        text = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


# ---------------------------------------------------------------------------
# Rule layer 1 — manifest-level required fields
# ---------------------------------------------------------------------------


def _check_imported_manifest(manifest: CaseManifest) -> list[MissingField]:
    """Required fields for a v2 CaseManifest (imported_user kind).

    Minimal contract: every imported case must declare a solver, a
    turbulence model, and at least one boundary patch. Re-appropriate
    turbulence is checked separately (rule layer 3).
    """
    missing: list[MissingField] = []

    if not manifest.physics.solver:
        missing.append(
            MissingField(
                field_path="physics.solver",
                severity="critical",
                why=(
                    "OpenFOAM solver name is required for any executable "
                    "case (e.g. simpleFoam, pimpleFoam, icoFoam)."
                ),
                suggested_default="simpleFoam",
            )
        )

    if not manifest.physics.turbulence_model:
        missing.append(
            MissingField(
                field_path="physics.turbulence_model",
                severity="critical",
                why=(
                    "Turbulence model declaration is required (laminar / "
                    "kEpsilon / kOmegaSST / etc.). Even laminar must be "
                    "explicit — implicit defaults are a known footgun."
                ),
                suggested_default="laminar",
            )
        )

    if not manifest.bc.patches:
        missing.append(
            MissingField(
                field_path="bc.patches",
                severity="critical",
                why=(
                    "At least one boundary patch must be configured — "
                    "without BC, OpenFOAM cannot start. Run the Step 3 "
                    "[AI 处理] action or annotate faces in the viewport."
                ),
            )
        )

    return missing


def _check_whitelist_or_draft(raw: dict[str, Any]) -> list[MissingField]:
    """Required top-level fields for whitelist / flat-draft cases.

    Mirrors the field set checked by `case_drafts.lint_case_yaml` but
    promotes them to the proper severity tiers and adds boundary-condition
    presence + parameter-block presence as critical (the lint check only
    warns).
    """
    missing: list[MissingField] = []

    # Critical fields — without these the case is non-actionable.
    for key, suggestion in (
        ("id", None),
        ("name", None),
        ("flow_type", "INTERNAL"),
        ("geometry_type", "SIMPLE_GRID"),
        ("solver", "simpleFoam"),
        ("turbulence_model", "laminar"),
    ):
        if not raw.get(key):
            missing.append(
                MissingField(
                    field_path=key,
                    severity="critical",
                    why=f"Required top-level field '{key}' is missing or empty.",
                    suggested_default=suggestion,
                )
            )

    # Warning-tier — present in every whitelist case but a fork might
    # legitimately drop them temporarily during edit.
    if not raw.get("parameters"):
        missing.append(
            MissingField(
                field_path="parameters",
                severity="warning",
                why=(
                    "No `parameters:` block (Re, Ra, Pr, …). Most cases "
                    "need at least one dimensionless parameter for the "
                    "comparator to anchor against the gold standard."
                ),
            )
        )

    if not raw.get("boundary_conditions"):
        # Critical only for SIMPLE_GRID / CUSTOM geometries that need
        # engineer-supplied BC values (LDC-style: top_wall_u etc.). Adapter-
        # driven geometries (BACKWARD_FACING_STEP, NATURAL_CONVECTION_CAVITY,
        # CHANNEL, BODY_IN_CHANNEL) inherit canonical BCs from the geometry
        # scaffold and legitimately omit the block.
        bc_critical_geoms = {"SIMPLE_GRID", "CUSTOM"}
        is_critical = (
            str(raw.get("geometry_type") or "").upper() in bc_critical_geoms
        )
        missing.append(
            MissingField(
                field_path="boundary_conditions",
                severity="critical" if is_critical else "warning",
                why=(
                    "No `boundary_conditions:` block. "
                    + (
                        "SIMPLE_GRID / CUSTOM geometries require explicit BC "
                        "values (e.g., top_wall_u for LDC); adapter cannot "
                        "author OpenFOAM dicts without them."
                        if is_critical
                        else (
                            "Adapter-driven geometry uses canonical defaults "
                            "from the scaffold; surface here so engineer can "
                            "override if needed."
                        )
                    )
                ),
            )
        )

    return missing


# ---------------------------------------------------------------------------
# Rule layer 2 — gold-contract precondition tri-state
# ---------------------------------------------------------------------------


def _check_gold_contract(gold: dict[str, Any]) -> list[MissingField]:
    """Translate `physics_contract.physics_precondition[*]` into missing
    entries based on its tri-state `satisfied_by_current_adapter` flag.

    Tri-state mapping (preserves DEC-V61-046 semantics — never bool-coerce
    "partial"):
        true     → no missing entry (already satisfied)
        false    → critical (precondition unmet, blocks archive)
        "partial"→ warning (laundered/degraded — record the gap)
    """
    out: list[MissingField] = []
    contract = gold.get("physics_contract")
    if not isinstance(contract, dict):
        return out

    preconds = contract.get("physics_precondition", [])
    if not isinstance(preconds, list):
        return out

    for idx, pc in enumerate(preconds):
        if not isinstance(pc, dict):
            continue
        satisfied = pc.get("satisfied_by_current_adapter")
        cond_text = str(pc.get("condition") or f"precondition #{idx + 1}")
        evidence = pc.get("evidence_ref")

        # Critical: explicit false. Note: `satisfied is False` matches only
        # the boolean False, NOT 0 or "" — ensures we don't flag a
        # missing key as a false answer.
        if satisfied is False:
            out.append(
                MissingField(
                    field_path=f"physics_contract.physics_precondition[{idx}]",
                    severity="critical",
                    why=(
                        f"Physics precondition unmet: {cond_text}"
                        + (f" (evidence: {evidence})" if evidence else "")
                    ),
                )
            )
        # Warning: explicit "partial" (tri-state laundering risk per V61-046)
        elif satisfied == "partial":
            out.append(
                MissingField(
                    field_path=f"physics_contract.physics_precondition[{idx}]",
                    severity="warning",
                    why=(
                        f"Physics precondition partially satisfied: {cond_text}"
                        + (f" (evidence: {evidence})" if evidence else "")
                        + ". Surface in audit narrative — clean PASS may not "
                        "be physically valid."
                    ),
                )
            )
        # Info: missing the satisfied flag entirely
        elif satisfied is None:
            out.append(
                MissingField(
                    field_path=f"physics_contract.physics_precondition[{idx}]",
                    severity="info",
                    why=(
                        f"Precondition has no satisfied flag set: {cond_text}. "
                        "Gold standard YAML should declare satisfied_by_current_adapter."
                    ),
                )
            )

    return out


# ---------------------------------------------------------------------------
# Rule layer 3 — Re-appropriate turbulence model check
# ---------------------------------------------------------------------------


def _check_re_appropriate_turbulence(
    *,
    turbulence_model: str | None,
    re_value: float | None,
) -> list[MissingField]:
    """Flag laminar turbulence at Re above the laminar ceiling.

    Conservative single threshold (2000) covers most internal / external
    flows. Future v2 could refine per flow_type.
    """
    if turbulence_model is None or re_value is None:
        return []

    if (
        turbulence_model.lower() == "laminar"
        and re_value > _RE_LAMINAR_CEILING
    ):
        return [
            MissingField(
                field_path="turbulence_model",
                severity="critical",
                why=(
                    f"Re = {re_value:g} exceeds the laminar ceiling "
                    f"({_RE_LAMINAR_CEILING:g}); laminar turbulence model "
                    "will produce non-physical results. Switch to a RANS "
                    "model (kOmegaSST recommended for general internal "
                    "flows; kEpsilon for high-Re free shear)."
                ),
                suggested_default="kOmegaSST",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Helpers — extract counts + percentage
# ---------------------------------------------------------------------------


def _build_report(
    *,
    case_id: str,
    case_kind: CaseKind,
    expected_critical_count: int,
    expected_warning_count: int,
    expected_info_count: int,
    missing: list[MissingField],
    notes: list[str],
) -> CaseCompletenessReport:
    """Compose the final report.

    Total = sum of expected counts across all rule layers that actually
    ran for this case_kind. Present = total - missing-count.
    """
    total = (
        expected_critical_count + expected_warning_count + expected_info_count
    )
    present = max(total - len(missing), 0)
    percentage = 100.0 if total == 0 else round(100.0 * present / total, 1)

    blocked_by_critical = sum(1 for m in missing if m.severity == "critical")
    ready = blocked_by_critical == 0

    return CaseCompletenessReport(
        case_id=case_id,
        case_kind=case_kind,
        ready_for_archive=ready,
        blocked_by_critical=blocked_by_critical,
        present_count=present,
        total_count=total,
        percentage=percentage,
        missing=missing,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Resolvers — one per case_kind
# ---------------------------------------------------------------------------


def _analyze_imported(case_id: str, case_dir: Path) -> CaseCompletenessReport:
    """Imported user STL case → CaseManifest v2 + minimal contract.

    Codex R1 P2 #1 fix: read the manifest YAML *raw* before letting the
    Pydantic schema fill defaults. `read_case_manifest()` will migrate
    a missing `physics.turbulence_model` to the schema default `'laminar'`,
    making the field look "set" when the engineer never touched it.
    Comparing the raw YAML's nested keys preserves the user-vs-default
    distinction so unset fields surface as missing.
    """
    notes: list[str] = []
    missing: list[MissingField] = []

    raw_manifest_yaml = _read_flat_yaml(case_dir / "case_manifest.yaml")

    # Helper: was a field actually present in the raw YAML (not just
    # filled by Pydantic defaults)?
    def _raw_has(*path: str) -> bool:
        cur: Any = raw_manifest_yaml
        for seg in path:
            if not isinstance(cur, dict) or seg not in cur:
                return False
            cur = cur[seg]
        return cur not in (None, "", [], {})

    try:
        manifest = read_case_manifest(case_dir)
    except (ManifestNotFoundError, ManifestParseError) as exc:
        notes.append(
            f"Imported case_manifest could not be parsed: {type(exc).__name__}. "
            "Editing the manifest by hand may have left it invalid."
        )
        manifest = None  # type: ignore[assignment]

    # Manifest layer (3 expected critical: solver, turbulence_model, bc.patches).
    # Use raw YAML presence (not Pydantic-filled defaults) so a missing
    # field shows up as missing, even if the schema would default-fill it.
    if not _raw_has("physics", "solver"):
        missing.append(
            MissingField(
                field_path="physics.solver",
                severity="critical",
                why=(
                    "OpenFOAM solver name is required (simpleFoam / "
                    "pimpleFoam / icoFoam / …). Even if a default was "
                    "scaffolded, the engineer must explicitly confirm."
                ),
                suggested_default="simpleFoam",
            )
        )
    if not _raw_has("physics", "turbulence_model"):
        missing.append(
            MissingField(
                field_path="physics.turbulence_model",
                severity="critical",
                why=(
                    "Turbulence model declaration is required (laminar / "
                    "kEpsilon / kOmegaSST / …). The schema default is "
                    "`laminar` but Codex R1 P2 caught that this default-"
                    "fill silently passed user-unset cases. Engineer must "
                    "explicitly choose."
                ),
                suggested_default="laminar",
            )
        )
    if not _raw_has("bc", "patches"):
        missing.append(
            MissingField(
                field_path="bc.patches",
                severity="critical",
                why=(
                    "At least one boundary patch must be configured — "
                    "without BC, OpenFOAM cannot start. Run the Step 3 "
                    "[AI 处理] action or annotate faces in the viewport."
                ),
            )
        )

    # Re-appropriate turbulence (only counted in total when Re actually
    # present; no Re in the v2 imported-manifest schema today, so this
    # layer is effectively dormant for imported cases. Kept for parity
    # with the whitelist analyzer in case a future v2 adds Re.)
    re_value: float | None = None
    re_layer_missing: list[MissingField] = []
    if manifest is not None:
        re_layer_missing = _check_re_appropriate_turbulence(
            turbulence_model=manifest.physics.turbulence_model,
            re_value=re_value,
        )
        missing.extend(re_layer_missing)

    notes.append(
        "Imported STL cases use a minimal contract (solver + turbulence + "
        "≥1 boundary patch). Full physics_contract checks apply once you "
        "link this case to a gold standard."
    )

    # Surface ingest warnings, if any, as info-tier notes.
    if manifest is not None and manifest.ingest_report_summary:
        warnings = manifest.ingest_report_summary.get("warnings") or []
        if isinstance(warnings, list) and warnings:
            notes.append(
                "STL ingest produced "
                f"{len(warnings)} warning(s) — review before archive: "
                + " · ".join(str(w) for w in warnings[:3])
                + ("…" if len(warnings) > 3 else "")
            )

    return _build_report(
        case_id=case_id,
        case_kind="imported_user",
        expected_critical_count=3 + (1 if re_value is not None else 0),
        expected_warning_count=0,
        expected_info_count=0,
        missing=missing,
        notes=notes,
    )


def _normalize_flat_yaml(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize flat-YAML shape variants so checks work uniformly.

    Imported flat drafts may store solver as a dict ``{name: simpleFoam}``
    while whitelist entries use a plain string ``simpleFoam``. Lift the
    nested form so `_check_whitelist_or_draft` can apply one truthiness
    rule.
    """
    out = dict(raw)
    s = out.get("solver")
    if isinstance(s, dict) and s.get("name"):
        out["solver"] = s["name"]
    return out


def _analyze_whitelist_like(
    *,
    case_id: str,
    raw: dict[str, Any],
    case_kind: CaseKind,
    notes: list[str],
) -> CaseCompletenessReport:
    """Whitelist case OR flat-draft (whitelist-fork) — 6 critical top-level
    + 2 critical/warning (parameters, boundary_conditions) + gold contract.

    Codex R1 P2 #2 fix: Re-rule contributes to both `missing` AND
    `total_count` when it actually runs. Earlier draft hard-coded the
    denominator at 8 + gold preconds even when the rule fired, producing
    14/15 instead of 14/16 on Re-based whitelist cases.
    """
    missing: list[MissingField] = []
    raw_norm = _normalize_flat_yaml(raw)

    # Manifest-equivalent layer (6 critical top-level + 1 critical bc + 1
    # warning parameters = 8 expected total)
    missing.extend(_check_whitelist_or_draft(raw_norm))

    # Re-appropriate turbulence layer (1 critical, gated on Re presence)
    re_value: float | None = None
    params = raw_norm.get("parameters")
    if isinstance(params, dict):
        try:
            re_raw = params.get("Re")
            if re_raw is not None:
                re_value = float(re_raw)
        except (TypeError, ValueError):
            re_value = None

    re_layer_missing = _check_re_appropriate_turbulence(
        turbulence_model=str(raw_norm.get("turbulence_model") or "") or None,
        re_value=re_value,
    )
    missing.extend(re_layer_missing)

    # Gold-contract layer (count = number of preconditions in the gold)
    gold = _load_gold_standard(case_id)
    gold_expected = 0
    if gold is not None:
        contract = gold.get("physics_contract")
        if isinstance(contract, dict):
            preconds = contract.get("physics_precondition", [])
            if isinstance(preconds, list):
                gold_expected = len(preconds)
        missing.extend(_check_gold_contract(gold))
    else:
        notes.append(
            "No gold_standard YAML linked for this case_id — using base "
            "manifest contract only. Link a gold standard to enable "
            "physics_contract precondition checks."
        )

    # Codex R1 P2 #2: include the Re-rule in expected_critical_count when
    # it actually ran (i.e. Re is present).
    re_rule_expected = 1 if re_value is not None else 0

    return _build_report(
        case_id=case_id,
        case_kind=case_kind,
        expected_critical_count=7 + re_rule_expected,
        expected_warning_count=1,  # parameters
        expected_info_count=gold_expected,  # gold-contract preconds
        missing=missing,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_case_completeness(case_id: str) -> CaseCompletenessReport:
    """Resolve `case_id` and run the matching completeness analysis.

    Resolution order (Codex R1 P1 fix · 2026-05-04):
        1. user_drafts/{case_id}.yaml → draft (flat YAML)
           — engineer's saved edits ALWAYS win when present, regardless
             of whether the case is whitelist-forked or imported. The
             editor (`case_drafts.put_case_yaml`) writes here unconditionally,
             so this is the source of truth for current intent.
        2. user_drafts/imported/{case_id}/case_manifest.yaml → imported_user
           — import-time scaffold; used only if no flat draft exists yet.
        3. whitelist[case_id] → whitelist
           — fallback for un-edited canonical cases.
        4. raise CaseNotFoundError

    Earlier draft inverted (1) and (2): for an imported case with edits,
    the imported manifest short-circuited the flat draft and the
    completeness report stayed stuck on the import-time snapshot
    (Codex R1 P1).

    Raises:
        CaseNotFoundError: case_id resolves to nothing.
    """
    if not case_id:
        raise CaseNotFoundError("case_id is empty")

    # Resolution 1: flat draft (engineer's most recent edits — always wins)
    flat_draft = _resolve_flat_draft(case_id)
    if flat_draft is not None:
        raw = _read_flat_yaml(flat_draft)
        # Imported case_ids are detectable by prefix; surface the origin
        # in notes so the engineer knows the editor is now driving.
        is_imported = case_id.startswith("imported_") or _resolve_imported_dir(
            case_id
        ) is not None
        notes = [
            (
                "Analyzing the editor's saved draft (user_drafts/{id}.yaml). "
                + (
                    "This is an imported case with engineer edits — the "
                    "import-time case_manifest.yaml is no longer the source "
                    "of truth; the flat draft is."
                    if is_imported
                    else "Whitelist fork or fresh draft."
                )
            )
        ]
        return _analyze_whitelist_like(
            case_id=case_id, raw=raw, case_kind="draft", notes=notes
        )

    # Resolution 2: imported case_dir (no flat draft yet)
    imported_dir = _resolve_imported_dir(case_id)
    if imported_dir is not None:
        return _analyze_imported(case_id, imported_dir)

    # Resolution 3: whitelist entry
    whitelist = _load_whitelist()
    entry = whitelist.get(case_id)
    if entry is not None:
        return _analyze_whitelist_like(
            case_id=case_id,
            raw=entry,
            case_kind="whitelist",
            notes=[],
        )

    # Resolution 4: not found
    raise CaseNotFoundError(f"case_id not found: {case_id}")
