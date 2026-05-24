"""DEC-V61-202-SUB-M30-CYCLE1 · WorkbenchFrame response schemas.

The frame is what `decide(CaseState) -> WorkbenchFrame` produces.
It's a pure function of state; no LLM call is involved (V130).
Frontend renders the frame additively above existing StepPanelShell
components — does NOT replace them.

See `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §4 for the
load-bearing state-machine sketch and §3 for the 4 UI-content drivers
this schema serves.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RailPrimaryKind = Literal["info_gap", "problem_fix", "step_default"]
OverlayKind = Literal[
    "patch_highlight",
    "region_highlight",
    "cell_count_badge",
    "checkmesh_warn",
]
CardKind = Literal["audit_finding", "missing_field", "step_hint"]
Severity = Literal["info", "warn", "fail"]

# Cycle 2: the 4th driver slot.
TopbarCtaKind = Literal[
    "next_step",
    "re_audit",
    "submit_solve",
    "step_default",
]


class RailPrimary(BaseModel):
    """The Engineer Control Rail's top-of-rail primary action card.

    Driven by `decide()`'s top-priority signal (FAIL problem > critical
    info gap > WARN problem > soft info gap > step default).
    """

    kind: RailPrimaryKind = Field(
        ...,
        description=(
            "Why this card was chosen as the rail's primary content. "
            "`info_gap` = a manifest field is missing the engineer must "
            "supply; `problem_fix` = an audit artifact reports a "
            "blocker the engineer must address; `step_default` = no "
            "blocking issue, render the step's neutral starting affordance."
        ),
    )
    title: str = Field(
        ...,
        description="Short headline, ≤ 60 chars. Engineer-readable.",
    )
    body_text: str | None = Field(
        default=None,
        description=(
            "Optional 1-3 sentence body explaining what to do + why. "
            "Curated text, NOT LLM-generated (V130)."
        ),
    )
    field_path: str | None = Field(
        default=None,
        description=(
            "JSON-path back to the manifest field this card targets "
            "(e.g. 'mesh_contract.y_plus_target.max'). Lets the frontend "
            "deep-link to the right form field. None when no specific "
            "field is being edited (e.g. step_default frames)."
        ),
    )
    suggested_default: Any | None = Field(
        default=None,
        description=(
            "Optional fallback value the UI may pre-fill. None = engineer "
            "types manually. Mirrors `MissingField.suggested_default` shape."
        ),
    )
    suggested_skeleton: dict[str, Any] | None = Field(
        default=None,
        description=(
            "DEC-V61-202-SUB-M31-CYCLE1 · domain-aware form helper. "
            "Structural dict skeleton for complex nested fields "
            "(e.g. `bc.patches` for ship_vof). The frontend renders a "
            "secondary 'Apply skeleton' CTA when this is non-null; "
            "clicking it PATCHes the full dict at field_path. Parallel "
            "to `suggested_default` (scalar) — both can be non-null "
            "when both a scalar default AND a skeleton make sense, "
            "though typically only one is offered per gap."
        ),
    )
    cta_label: str | None = Field(
        default=None,
        description=(
            "Action button text, e.g. '应用' / 'Apply' / '查看详情'. "
            "None = no CTA button on this card."
        ),
    )
    severity: Severity = Field(
        default="info",
        description=(
            "DEC-V61-202-SUB-M32-CYCLE1: rail urgency surface. Frontend "
            "picks tone (rose/amber/sky) by (kind, severity) — lets "
            "engineers visually distinguish a critical info_gap "
            "(corrupted manifest from M3.1 cycle 7) from a soft info "
            "info_gap (unknown patch_type from M3.1 cycle 8) without "
            "parsing the provenance string. Source severities map via "
            "`_normalize_severity` (critical→fail, warning→warn). "
            "Default `info` preserves step_default + legacy fixtures."
        ),
    )
    provenance: list[str] = Field(
        default_factory=list,
        description=(
            "Debug provenance — why decide() chose this card. Each entry "
            "is a one-line trace like 'mesh_contract.y_plus_target.max is "
            "missing AND step=2'. Surfaces in dev-mode tooltips for the "
            "'why is the workbench showing this?' question."
        ),
    )


class ViewportOverlay(BaseModel):
    """A single overlay decoration over the main Viewport.

    Examples:
        - patch_highlight + target='inlet' → frontend draws a colored
          outline around the inlet patch in the 3D view.
        - cell_count_badge + label='1.2M cells' → frontend renders a
          floating badge top-right of the viewport.
        - checkmesh_warn + severity='warn' + label='non-orthogonality 72°'
          → frontend renders a warning ribbon near the affected region.
    """

    kind: OverlayKind
    target: str | None = Field(
        default=None,
        description=(
            "Spatial reference: patch name (for patch_highlight), region "
            "name (for region_highlight), or None when the overlay is "
            "viewport-global (cell_count_badge, checkmesh_warn at the "
            "case scale)."
        ),
    )
    severity: Severity = "info"
    label: str | None = Field(
        default=None,
        description="Optional inline text for the overlay decoration.",
    )


class BottomCard(BaseModel):
    """A single advisor-style card in the bottom panel.

    These are distinct from the existing `AIAdvisorPanel` (V130 LLM-
    backed, advisor-tab content). BottomCards in WorkbenchFrame are
    DETERMINISTIC — sourced from audit artifacts + completeness report.
    LLM-offline by construction.
    """

    kind: CardKind
    title: str
    body_text: str = Field(
        ...,
        description="1-4 sentence curated body. NOT LLM-generated (V130).",
    )
    severity: Severity = "info"
    source_artifact: str | None = Field(
        default=None,
        description=(
            "Provenance: which audit artifact this card cites "
            "(e.g. 'bc_quality.json', 'mesh_report.json'). None for "
            "step_hint cards that are static guidance."
        ),
    )
    field_path: str | None = Field(
        default=None,
        description=(
            "JSON-path back to the manifest field this card discusses. "
            "Lets clicking the card deep-link to the right form field."
        ),
    )


class TopbarCta(BaseModel):
    """The 4th dynamic slot (DEC-V61-202-SUB-M30-CYCLE2).

    Rendered as the rightmost pill in the TopBar. The CTA decides what
    "next thing to do" is based on (a) what the rail_primary is asking
    for and (b) which step the engineer is on. Disabled state surfaces
    a tooltip explaining why progress is blocked.
    """

    kind: TopbarCtaKind
    label: str = Field(..., description="Button text shown in the pill.")
    target_step: int | None = Field(
        default=None,
        description=(
            "Step the engineer transitions to if they click. None when "
            "the CTA isn't a step transition (re_audit / submit_solve)."
        ),
    )
    enabled: bool = Field(
        ...,
        description=(
            "False when a critical info_gap blocks progress. The pill "
            "renders gray and the click is a no-op; tooltip shows reason."
        ),
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Why the CTA is disabled (when `enabled=False`). Engineer-"
            "readable; e.g. '先补齐 vof_contract.phases 才能进入下一步'."
        ),
    )


class WorkbenchFrame(BaseModel):
    """The frame descriptor returned by `decide(CaseState)`.

    A frame is what the dynamic workbench renders for one
    (case_id, step, focus) triple. Re-evaluated on every state change.

    Reproducibility: `state_sha` is the SHA-256 of canonical input
    bytes. Same state → same frame, always.
    """

    case_id: str
    step: int = Field(..., ge=1, le=5)
    rail_primary: RailPrimary
    viewport_overlays: list[ViewportOverlay] = Field(default_factory=list)
    bottom_cards: list[BottomCard] = Field(default_factory=list)
    topbar_cta: TopbarCta = Field(
        ...,
        description=(
            "DEC-V61-202-SUB-M30-CYCLE2: the 4th dynamic slot, rendered "
            "in TopBar. Always present (defaults to step_default kind)."
        ),
    )
    state_sha: str = Field(
        ...,
        description=(
            "SHA-256 hex digest of full canonical input bytes "
            "(case_id + step + sorted-key manifest + audit artifacts + "
            "completeness + focus). Frontend can use this to skip re-"
            "render when state hasn't changed."
        ),
    )
    manifest_state_sha: str = Field(
        ...,
        description=(
            "DEC-V61-202-SUB-M30-CYCLE2: SHA-256 of manifest-only "
            "canonical bytes. Frontend sends this as "
            "`expected_state_sha` on PATCH /api/cases/{id}/manifest. "
            "Excludes artifacts/step/focus so a single field PATCH "
            "doesn't cause a state_sha conflict storm whenever an "
            "unrelated audit artifact refreshes."
        ),
    )
    decided_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp when decide() ran.",
    )


class CaseStateSnapshot(BaseModel):
    """Input to `decide()`. Captured server-side from disk + query params.

    Not part of the public response schema (engineers don't see this),
    but exposed for testability — `decide()` is a pure function of
    `CaseStateSnapshot`, so tests construct snapshots directly without
    needing real on-disk cases.
    """

    case_id: str
    step: int = Field(..., ge=1, le=5)
    manifest: dict = Field(default_factory=dict)
    artifacts: dict = Field(
        default_factory=dict,
        description=(
            "Loaded audit artifacts keyed by filename "
            "(e.g. {'bc_quality.json': {...}, 'mesh_report.json': {...}})."
        ),
    )
    completeness: dict | None = Field(
        default=None,
        description=(
            "Serialized CaseCompletenessReport (DEC-V61-116). None when "
            "the completeness analyzer couldn't run (case not found, "
            "etc.) — decide() degrades gracefully to artifact-only mode."
        ),
    )
    focus_patch: str | None = None
    focus_region: str | None = None
    focus_panel: str | None = None
