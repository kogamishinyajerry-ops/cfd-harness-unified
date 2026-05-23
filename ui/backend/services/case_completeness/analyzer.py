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


# BC field set OpenFOAM authors at time-zero (0/). Any one of these
# present and newer than the polyMesh boundary indicates a setup_bc
# has run AGAINST the current mesh. Codex R7 fix.
_BC_TIME_ZERO_DICT_NAMES = (
    "U",
    "p",
    "p_rgh",  # buoyant variants
    "k",
    "epsilon",
    "omega",
    "nut",
    "T",  # natural convection
    "alphat",
    "nuTilda",
)


def _bc_dicts_current(case_dir: Path) -> bool:
    """True iff the case has a BC dict file (under 0/) whose mtime is
    ≥ the polyMesh points file's mtime — i.e. the BC was authored
    against the current mesh, not a stale earlier mesh.

    Codex R8 P1 fix: use `constant/polyMesh/points` as the mesh-only
    signal, NOT `boundary`. setup_bc_from_stl_patches() rewrites
    `polyMesh/boundary` to update patch types (e.g. wall → symmetry)
    as part of BC setup itself, so a boundary-mtime gate would
    spuriously fail right after a successful BC setup. `points` is
    the actual mesh geometry (vertex coordinates) — it's only
    rewritten by mesh generation (gmshToFoam / blockMesh), never
    by BC setup.

    Returns False if:
      - polyMesh points doesn't exist (case not meshed yet)
      - polyMesh boundary doesn't exist (corrupted partial polyMesh —
        downstream setup_bc paths still require this file even though
        the analyzer's mtime gate is on points; Codex R9 P2)
      - no 0/X file exists
      - all 0/X mtimes are older than polyMesh.points mtime (BC stale
        after a re-mesh)

    All errors swallow → False (analyzer never crashes on filesystem
    weirdness; it just reports the field as missing).
    """
    try:
        poly_dir = case_dir / "constant" / "polyMesh"
        points_path = poly_dir / "points"
        boundary_path = poly_dir / "boundary"
        # Codex R9 P2: fail closed when boundary is missing — downstream
        # setup_bc / setup_bc_from_stl_patches require boundary to
        # exist even though the analyzer's mtime gate is on points.
        # Otherwise a partial-restore state (points present, boundary
        # absent) could spuriously clear bc.patches while every BC
        # setup path would still fail.
        if not (points_path.is_file() and boundary_path.is_file()):
            return False
        points_mtime = points_path.stat().st_mtime
        zero_dir = case_dir / "0"
        if not zero_dir.is_dir():
            return False
        for name in _BC_TIME_ZERO_DICT_NAMES:
            candidate = zero_dir / name
            if candidate.is_file():
                if candidate.stat().st_mtime >= points_mtime:
                    return True
        return False
    except OSError:
        return False


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


# DEC-V61-202-SUB-M31-CYCLE1 (Codex R4 P2 fix): solver → plausible
# case_family candidates. The case_family warning fires only when the
# manifest's solver appears here. Cycle 1 ships one helper (ship_vof for
# bc.patches), so only interFoam manifests get the warning today; other
# solvers' completeness reports stay clean.
#
# TODO(M3.1 cycle 2+): extract this + _FORM_HELPER_SKELETONS into a
# shared domain registry (e.g. `ui/backend/domain/case_family.py`)
# once a second helper lands. Cycle 1 inlines because there's exactly
# one entry and the cross-module coupling has no value yet.
_SOLVER_TO_CASE_FAMILY_CANDIDATES: dict[str, frozenset[str]] = {
    "interFoam": frozenset({"ship_vof"}),
}


def _case_family_helper_candidate_applies(raw_manifest_yaml: dict[str, Any]) -> bool:
    """True iff a registered form-helper exists for some case_family that
    is plausible for the manifest's solver.

    Cycle 1: interFoam → {ship_vof} only. Other solvers (simpleFoam,
    pimpleFoam, rhoSimpleFoam, etc.) currently have no candidate, so the
    case_family advisory does not fire — completeness percentage stays at
    100% for those cases.

    Why not infer the family directly: per Codex R1, solver-alone is not
    a sound classifier — interFoam covers ship_vof / sloshing / dam-break
    / multiphase pipes. The candidate set just means "labeling could
    benefit"; the engineer still chooses the actual family.

    Codex R7 / user-ratified defeat (2026-05-24): this helper reads
    ONLY `manifest.physics.solver`. Merged manifest+flat-draft
    resolution was attempted in R5+R6 but produced an unresolvable
    design ambiguity:
      - scaffold pre-writes `flat.solver.name=simpleFoam` by default
      - `switch_solver` writes manifest only
      - `PUT /api/cases/{id}/yaml` writes flat only
      - either precedence loses fresh edits in the OTHER direction
    Cycle 1 punts the solver-source authority question to a proper
    cycle-2 design DEC. Known limitation: engineers who set
    `solver: interFoam` in the flat draft but haven't run
    `switch_solver` yet get no case_family advisory until they run it.
    """
    physics = raw_manifest_yaml.get("physics")
    if not isinstance(physics, dict):
        return False
    solver = physics.get("solver")
    if not isinstance(solver, str) or not solver:
        return False
    return solver in _SOLVER_TO_CASE_FAMILY_CANDIDATES


def _analyze_imported(
    case_id: str,
    case_dir: Path,
    flat_draft: Path | None = None,
) -> CaseCompletenessReport:
    """Imported user STL case → merged-source minimal contract.

    Per Codex R4: the scaffold writes a manifest *without* the physics/bc
    sections that this analyzer requires; those get filled by setup_bc /
    switch_solver / mesh-wizard later. The flat editor YAML at
    `user_drafts/{id}.yaml` is what the engineer mutates via PUT
    /api/cases/{id}/yaml in the meantime. So neither file alone has all
    the engineer-set state — the analyzer has to consider both.

    Field-presence rule: a required field counts as "present" if *either*
    the manifest YAML or the flat draft has it set to a non-empty value.
    This makes:
      · scaffold-state import without flat edits → bc.patches absent in
        both → flagged missing (correct: engineer hasn't run setup_bc yet)
      · engineer edits flat YAML to set turbulence_model → flat has it →
        not flagged missing even if manifest lacks the field
      · setup_bc populates manifest.bc.patches → manifest has it → not
        flagged missing even if flat draft never set boundary_conditions

    History: R1-R3 each tried different single-source rules with
    structural failure modes (R1 stale manifest, R2 fresh-import
    skipped imported path, R3 mtime fragile, R4 manifest-only ignores
    flat edits). R5 settles on a per-field merge.

    Codex R1 P2 #1 carry-over: read raw YAMLs (not Pydantic-migrated
    instances) so schema defaults like turbulence_model='laminar'
    don't mask user-unset fields.

    Codex R2 P2 carry-over: ManifestParseError → critical missing entry
    so the verdict tracks downstream-route reality.
    """
    notes: list[str] = []
    missing: list[MissingField] = []

    raw_manifest_yaml = _read_flat_yaml(case_dir / "case_manifest.yaml")
    raw_flat_yaml: dict[str, Any] = (
        _read_flat_yaml(flat_draft) if flat_draft is not None else {}
    )

    # Per-source presence helpers (raw, not Pydantic-defaulted).
    def _has_in(d: dict[str, Any], *path: str) -> bool:
        cur: Any = d
        for seg in path:
            if not isinstance(cur, dict) or seg not in cur:
                return False
            cur = cur[seg]
        return cur not in (None, "", [], {})

    # Helper: per-field merge — present if either source has it. Each
    # source can supply MULTIPLE alternative paths; ALL paths must
    # narrow to a *meaningful* presence (not just "the key exists").
    def _present(manifest_paths: list[tuple[str, ...]], flat_paths: list[tuple[str, ...]]) -> bool:
        for mp in manifest_paths:
            if _has_in(raw_manifest_yaml, *mp):
                return True
        for fp in flat_paths:
            if _has_in(raw_flat_yaml, *fp):
                return True
        return False

    schema_invalid = False
    try:
        manifest = read_case_manifest(case_dir)
    except ManifestNotFoundError as exc:
        notes.append(
            f"Imported case_manifest could not be found: {exc}. "
            "Re-run the STL import to scaffold the manifest."
        )
        manifest = None  # type: ignore[assignment]
    except ManifestParseError as exc:
        schema_invalid = True
        missing.append(
            MissingField(
                field_path="case_manifest.yaml",
                severity="critical",
                why=(
                    "Imported case_manifest.yaml is parseable YAML but "
                    f"fails schema validation: {exc}. Every backend route "
                    "that reads the manifest will reject it; fix the "
                    "schema before continuing."
                ),
            )
        )
        notes.append(
            "Manifest schema invalid — completeness checks below run "
            "best-effort against the raw YAMLs; downstream routes will "
            "still 500 until the manifest is repaired."
        )
        manifest = None  # type: ignore[assignment]

    # Per-field presence: merged across manifest YAML + flat editor YAML.
    # The fields-vs-sources matrix below is intentional and narrow:
    # only paths that genuinely express the canonical state count.
    #
    # Codex R5 P1+P2 fixes:
    #  - bc.patches: ONLY manifest bc.patches counts. Flat-draft
    #    `boundary_conditions` is the editor's values block; nothing
    #    in the codebase syncs it into manifest patch setup.
    #  - solver: dict shape requires `solver.name`. Bare `solver: {...}`
    #    without a `name` is metadata-only (family / steady_state /
    #    note) and doesn't satisfy the contract.

    # DEC-V61-202-SUB-M31-CYCLE1 (Codex R2 P1 fix + R4 P2 demand-driven
    # narrowing): case_family gap, surfaced only when a registered
    # form-helper skeleton plausibly applies to this manifest's solver.
    #
    # Without demand-driving, the warning fires for every imported case
    # (e.g. simpleFoam RANS cases) even though cycle 1 only has the
    # ship_vof skeleton — penalizing those cases' completeness percentage
    # to 80% with no possible benefit. Codex R4 P2 flagged this.
    #
    # Demand-driven rule: the warning fires only when the manifest's
    # `physics.solver` matches a candidate solver for at least one
    # registered helper. Cycle 1 ships one helper (`ship_vof`/interFoam),
    # so only interFoam imports see the warning today.
    raw_case_family = raw_manifest_yaml.get("case_family")
    helper_candidate_applies = _case_family_helper_candidate_applies(
        raw_manifest_yaml
    )
    if (
        helper_candidate_applies
        and (not isinstance(raw_case_family, str) or not raw_case_family)
    ):
        # Codex R1 rationale (NO auto-pre-fill): interFoam is a generic
        # VOF solver covering ship_vof, sloshing, dam-break, multiphase
        # pipes — pre-filling ship_vof would mislabel the latter. We
        # surface the gap as advisory only; the engineer chooses the
        # family.
        #
        # Codex cycle-2 R1 P3 + R2 P2 fix: renderer-agnostic copy.
        # The `why` text appears in DynamicFramePanel (rail), but ALSO
        # in CompletenessCard, DynamicBottomCards, and the legacy
        # shell (`?legacy=1`). Cycle-2's inline input lives only in
        # DynamicFramePanel — referencing "the input below" was
        # accurate there but false on every other renderer. Text now
        # describes WHAT labeling unlocks without prescribing HOW to
        # set the field; that's the renderer's responsibility (rail
        # inline input, completeness card link, etc.).
        missing.append(
            MissingField(
                field_path="case_family",
                severity="warning",
                why=(
                    "This interFoam case could be ship_vof, sloshing, "
                    "dam-break, etc. — labeling `case_family` (e.g. "
                    "ship_vof) unlocks the Step-4 BC skeleton. "
                    "Non-blocking — case can run without a family, but "
                    "the canonical BC skeleton won't be offered."
                ),
            )
        )

    # Solver: manifest physics.solver, OR flat `solver` (string), OR
    # flat `solver.name` (dict shape). Bare `solver` *dict* without
    # `.name` does NOT count.
    flat_solver = raw_flat_yaml.get("solver")
    flat_solver_string = isinstance(flat_solver, str) and bool(flat_solver)
    flat_solver_named = (
        isinstance(flat_solver, dict) and bool(flat_solver.get("name"))
    )
    if not (
        _has_in(raw_manifest_yaml, "physics", "solver")
        or flat_solver_string
        or flat_solver_named
    ):
        missing.append(
            MissingField(
                field_path="physics.solver",
                severity="critical",
                why=(
                    "OpenFOAM solver name is required (simpleFoam / "
                    "pimpleFoam / icoFoam / …). Set it in the editor "
                    "(/workbench/case/{id}/edit) or via switch_solver. "
                    "If your flat draft has `solver: {family: ..., note: "
                    "...}` without a `name`, that doesn't count — the "
                    "name is what every OpenFOAM author path consumes."
                ),
                suggested_default="simpleFoam",
            )
        )

    # Turbulence model: manifest physics.turbulence_model OR flat
    # turbulence_model. (No dict-shape ambiguity here — turbulence_model
    # is always a plain string.)
    if not _present(
        manifest_paths=[("physics", "turbulence_model")],
        flat_paths=[("turbulence_model",)],
    ):
        missing.append(
            MissingField(
                field_path="physics.turbulence_model",
                severity="critical",
                why=(
                    "Turbulence model declaration is required (laminar / "
                    "kEpsilon / kOmegaSST / …). Codex R1 P2 caught that "
                    "Pydantic default-fill silently passed user-unset "
                    "cases — analyzer reads raw YAML to require an "
                    "explicit engineer choice."
                ),
                suggested_default="laminar",
            )
        )

    # Boundary-patch setup signal — Codex R7 → R8 fix.
    #
    # Filesystem-mtime check: a BC dict file (0/U, 0/p, 0/k, …) must
    # have mtime ≥ polyMesh.points mtime to count as current. R8
    # corrected the earlier draft that compared against polyMesh.boundary:
    # boundary is rewritten by setup_bc_from_stl_patches() too (to
    # change patch types like wall → symmetry), so it's not a clean
    # mesh-only signal. polyMesh.points is the vertex-coordinates
    # file — it's only rewritten by mesh generation (gmshToFoam /
    # blockMesh), never by BC setup. Workflow:
    #   · meshed but no BC → 0/X absent → flag missing (correct)
    #   · setup_bc ran → 0/X mtime > points mtime → BC current
    #   · re-mesh after setup_bc → points mtime > 0/X mtime → BC stale
    #     → flag missing (correct: setup_bc must rerun)
    #   · BC setup that also rewrites boundary (symmetry case) → 0/X
    #     mtime > points mtime → still current (R8 P1 fix)
    bc_present = _bc_dicts_current(case_dir)
    bc_patches_set = _has_in(raw_manifest_yaml, "bc", "patches")
    if not (bc_present or bc_patches_set):
        # Codex R10 P3: distinguish the corrupted partial-polyMesh state
        # from the regular "BC not set up yet" state. setup_bc paths
        # fail immediately when boundary is missing, so the remediation
        # copy must point engineer to mesh restore/regen instead of
        # Step 3 [AI 处理].
        poly_dir = case_dir / "constant" / "polyMesh"
        points_exists = (poly_dir / "points").is_file()
        boundary_exists = (poly_dir / "boundary").is_file()
        if points_exists and not boundary_exists:
            missing.append(
                MissingField(
                    field_path="bc.patches",
                    severity="critical",
                    why=(
                        "constant/polyMesh/boundary is missing but "
                        "constant/polyMesh/points exists — the polyMesh "
                        "is in a corrupted partial state (likely a "
                        "partial restore or manual cleanup). Step 3 "
                        "[AI 处理] cannot recover this — setup_ldc_bc / "
                        "setup_bc_from_stl_patches both fail immediately "
                        "without `boundary`. Restore the polyMesh from "
                        "backup OR re-run the mesh wizard to regenerate "
                        "polyMesh/* from scratch, THEN run Step 3 BC "
                        "setup."
                    ),
                )
            )
        else:
            missing.append(
                MissingField(
                    field_path="bc.patches",
                    severity="critical",
                    why=(
                        "Boundary-patch setup has not run, OR has been "
                        "invalidated by a later re-mesh. The analyzer "
                        "accepts either: (a) manifest.bc.patches non-empty, "
                        "OR (b) at least one BC dict in 0/ (U, p, k, "
                        "epsilon, omega, nut, …) with mtime ≥ "
                        "constant/polyMesh/points mtime — proving the BC "
                        "was authored AGAINST the current mesh geometry. "
                        "(We compare against `points` rather than `boundary` "
                        "because BC setup itself rewrites `boundary` to "
                        "change patch types.) Run the Step 3 [AI 处理] "
                        "action or annotate faces in the viewport."
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
        # 3 base critical (solver, turbulence, bc.patches) + Re-rule slot
        # (gated on Re presence) + manifest-schema-validity slot (always
        # counted; counts as "present" when read_case_manifest passes).
        expected_critical_count=(
            3
            + (1 if re_value is not None else 0)
            + 1  # manifest_schema_invalid slot
        ),
        # DEC-V61-202-SUB-M31-CYCLE1 (Codex R3 P2 + R4 P2 fixes):
        # case_family is counted in totals only when the demand-driven
        # predicate fires (solver matches at least one helper candidate).
        # For non-applicable solvers, the slot does not exist, so
        # percentage stays 100% when other required fields are present.
        # For applicable solvers (interFoam in cycle 1), the slot is
        # always counted — present when manifest carries case_family,
        # missing-warning when absent. Keeps totals consistent with the
        # rule set actually surfaced for the case.
        expected_warning_count=1 if helper_candidate_applies else 0,
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

    Resolution policy (Codex R4 → R5 · 2026-05-04):

      Imported cases have TWO independent state stores updated by
      different code paths:
        - `user_drafts/imported/{id}/case_manifest.yaml` — schema-typed
          v2 manifest. Updated by setup_bc_from_stl_patches (bc.patches),
          mesh wizard (history + bc.patches), switch_solver, and
          mark_user_override / mark_ai_authored (overrides + history).
          NOT updated by the editor PUT.
        - `user_drafts/{id}.yaml` — flat editor YAML. Updated by
          `PUT /api/cases/{id}/yaml` (CaseEditorPage / EditCasePage).
          NOT updated by setup_bc / mesh / switch_solver.

      Neither file alone has all the engineer-set state. R1 (manifest-
      first), R2 (flat-first), R3 (mtime arbitration), and R4
      (manifest-canonical) each hit a different correctness wall.

      R5 settles on **per-field merge**: for the 3 base critical fields
      (solver, turbulence_model, bc.patches), a field counts as
      "present" if EITHER source has it. This matches the actual
      workflow:
        · scaffold-time, no edits: bc.patches absent in both → flagged
          missing (correct: engineer hasn't set up BC yet)
        · engineer edits flat YAML to set turbulence_model: flat has it
          → not flagged missing
        · setup_bc populates manifest.bc.patches: manifest has it → not
          flagged missing even if flat draft never set it

    Resolution rules:
        1. imported_dir exists → run merged analysis (`_analyze_imported`
           with flat_draft passed in).
        2. flat_draft exists alone (whitelist fork or fresh manual
           draft, not from STL import) → analyze flat draft as "draft".
        3. whitelist[case_id] exists → analyze whitelist entry.
        4. Else → raise CaseNotFoundError.

    History:
      - R1 (initial): imported_dir → flat → whitelist (manifest first).
        Codex R1 P1: stale manifest hides engineer flat edits.
      - R2: flat → imported_dir → whitelist (flat first).
        Codex R2 P1: scaffold writes flat YAML too, so fresh imports
        always resolve as draft, never imported_user.
      - R3: mtime-based imported with both. Codex R3 P1+P2:
        sub-second mtimes regress; metadata-only manifest writes flip
        analyzer mid-workflow.
      - R4: manifest-canonical for imported cases. Codex R4 P1:
        scaffolded manifest lacks physics/bc; permanently blocks.
      - R5 (this · final): per-field merge across both sources.

    Raises:
        CaseNotFoundError: case_id resolves to nothing.
    """
    if not case_id:
        raise CaseNotFoundError("case_id is empty")

    flat_draft = _resolve_flat_draft(case_id)
    imported_dir = _resolve_imported_dir(case_id)

    # Case 1: imported case (with or without a co-existing flat draft).
    # Per Codex R4: pass both files to _analyze_imported so it can merge
    # presence checks across the manifest YAML and flat editor YAML.
    # Neither file is sole canonical — solver/turbulence flow through the
    # editor (PUT /api/cases/{id}/yaml → flat draft); bc.patches flows
    # through setup_bc / mesh wizard → manifest. A field is "present"
    # if either source has it.
    if imported_dir is not None:
        return _analyze_imported(case_id, imported_dir, flat_draft=flat_draft)

    # Case 2: flat_draft alone (whitelist fork or fresh manual draft).
    if flat_draft is not None:
        raw = _read_flat_yaml(flat_draft)
        notes = [
            "Analyzing user_drafts/{case_id}.yaml (flat draft, may be "
            "a whitelist fork or a fresh manual draft)."
        ]
        return _analyze_whitelist_like(
            case_id=case_id, raw=raw, case_kind="draft", notes=notes
        )

    # Case 3: whitelist entry.
    whitelist = _load_whitelist()
    entry = whitelist.get(case_id)
    if entry is not None:
        return _analyze_whitelist_like(
            case_id=case_id,
            raw=entry,
            case_kind="whitelist",
            notes=[],
        )

    # Case 4: not found.
    raise CaseNotFoundError(f"case_id not found: {case_id}")
