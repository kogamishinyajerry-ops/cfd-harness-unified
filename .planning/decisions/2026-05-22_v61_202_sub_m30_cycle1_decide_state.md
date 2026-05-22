---
decision_id: DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
title: M3.0 cycle 1 — backend decide(CaseState) + WorkbenchFrame schema + additive frontend layer
status: Accepted
proposed_date: 2026-05-22
accepted_date: 2026-05-22
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 1 (first guided-UX implementation cycle)
notion_sync_status: pending
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
codex_review:
  r0_commit: 75210f8
  r0_relay: crs (effort=high, fallback) — 86gs gpt-5.4 xhigh hung ≥25 min, switched to CRS gpt-5.4 high; DEC frontmatter notes the effort downgrade per v2.3 rule
  r0_verdict: CHANGES_REQUIRED (3 P1 + 1 P2)
  r0_findings:
    - "P1-1: _load_manifest missed whitelist resolver branch — catalog cases would 404"
    - "P1-2: _STEP_PATH_PREFIXES[4] missed `bc.patches` prefix — imported-user BC gaps invisible on Step 4"
    - "P1-3: _iter_problems_from_artifact didn't parse real cfdtrust gate_status / *_dimension / gates.* shapes — real audit failures hidden"
    - "P2: mesh overlays read flat n_cells / max_non_orthogonality but real shape is stats.cells + quality_dimension.metrics.max_non_orthogonality.actual"
  r1_commit: 4ef8b65
  r1_verdict: APPROVED (verbatim Codex P1 fix per v2.3 verbatim exception)
---

## Why

DEC-V61-202 charter declared the strategic pivot to workbench guided UX
and named M3.0 cycle 1 as the first concrete implementation step:
"backend `decide(CaseState)` function + frontend frame-descriptor renderer
+ 3 dynamic-content slots wired (rail.primary / viewport.overlays /
bottom.cards) + case_007 KCS VOF dogfood as first verification."

Pre-implementation surface scan (V61-088):
- **ROADMAP**: this cycle implements DEC-V61-202 charter directly.
- **Existing surfaces found**: `ui/backend/services/case_completeness/`
  (DEC-V61-116) already detects info gaps via `MissingField` schema with
  severity tiers (critical / warning / info). `decide()` composes on top
  rather than reimplementing. **Disposition: extend** — `decide()`
  consumes `CaseCompletenessReport` + audit artifacts + step + focus.
- **Existing UI shell**: `ui/frontend/src/pages/workbench/StepPanelShell.tsx`
  (DEC-V61-096) renders the 5-step spine with TaskPanel → step body →
  CompletenessCard → AIAdvisorPanel → AICoachPanel. **Disposition:
  extend additively** — new `DynamicFramePanel` renders ABOVE existing
  components without replacing them. Confirmed by user 2026-05-22 Q1=B.

## What landed (scope)

### In scope

**Backend** (~400 LOC + tests):
- `ui/backend/schemas/workbench_frame.py`: pydantic models for
  `WorkbenchFrame` + `RailPrimary` + `ViewportOverlay` + `BottomCard` +
  `CaseStateSnapshot`.
- `ui/backend/services/workbench_decide.py`: pure function
  `decide(state: CaseStateSnapshot) -> WorkbenchFrame`. Reads
  CaseCompletenessReport + audit artifacts; **no LLM call** (V130
  invariant). Deterministic; reproducible from state SHA.
- `ui/backend/routes/workbench_frame.py`: FastAPI route
  `GET /api/cases/{case_id}/workbench_frame` with query params
  `step: 1..5` (required), `focus_patch?`, `focus_region?`,
  `focus_panel?`.
- Wire into `ui/backend/main.py`.
- Tests in `ui/backend/tests/test_workbench_frame.py`: unit tests for
  `decide()` covering all 5 steps + the 3 driver-priority branches
  (problem > info gap > default) + route smoke + V130 LLM-offline check.

**Frontend** (~300 LOC + tests):
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/types.ts`:
  TS mirror of backend `WorkbenchFrame`.
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/useWorkbenchFrame.ts`:
  React Query hook polling `GET /api/cases/{id}/workbench_frame?step=N`.
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicFramePanel.tsx`:
  rail.primary slot renderer.
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicViewportOverlays.tsx`:
  viewport.overlays renderer (badge/highlight layer over existing
  Viewport component).
- `ui/frontend/src/pages/workbench/step_panel_shell/dynamic_frame/DynamicBottomCards.tsx`:
  bottom.cards renderer (advisor-card-styled, distinct from existing
  AIAdvisorPanel which is V130 LLM-backed).
- Wire into `StepPanelShell.tsx`: render dynamic-frame components
  additively, gated by feature flag `?dynamic_frame=1` initially so we
  can A/B without breaking existing user flows.
- Vitest unit tests for each component + hook.

**Dogfood** (`.planning/dogfood/DOGFOOD_CASE_007_CYCLE1.md`):
- Set up case_007 KCS ship VOF synthetic case in `_sandboxes/`.
- Walk the engineer-sim through Step 1→5; at each step transition,
  verify ≥1 of the 4 frame slots differs from previous (anti-pattern
  check per SSOT §8.4).
- Verify Gap #48 (`p_rgh`) and Gap #49 (phases derivation) surface as
  `bottom_cards` problems WITHOUT the engineer needing to read
  `bc_quality.json` directly (per SSOT §8.3).

### Out of scope

- Manifest PATCH endpoints (engineer applying frame changes back to
  manifest) — cycle 2.
- Topbar dynamic CTA (the 4th driver slot) — cycle 2.
- Feature flag removal (`?dynamic_frame=1` → always-on) — cycle 2 after
  dogfood passes.
- `case_007` real OpenFOAM solver run — cycle 2+.
- Non-OpenFOAM backends.
- Multi-user collaboration / live cursors.

## Schema sketch

```python
# ui/backend/schemas/workbench_frame.py
class RailPrimary(BaseModel):
    kind: Literal["info_gap", "problem_fix", "step_default"]
    title: str
    body_text: str | None = None
    field_path: str | None = None  # JSON-path back to manifest field
    suggested_default: Any | None = None
    cta_label: str | None = None
    provenance: list[str]  # why this rendered — debuggable

class ViewportOverlay(BaseModel):
    kind: Literal["patch_highlight", "region_highlight",
                  "cell_count_badge", "checkmesh_warn"]
    target: str | None = None
    severity: Literal["info", "warn", "fail"] = "info"
    label: str | None = None

class BottomCard(BaseModel):
    kind: Literal["audit_finding", "missing_field", "step_hint"]
    title: str
    body_text: str
    severity: Literal["info", "warn", "fail"] = "info"
    source_artifact: str | None = None
    field_path: str | None = None  # deep-link to manifest field if relevant

class WorkbenchFrame(BaseModel):
    case_id: str
    step: int  # 1..5
    rail_primary: RailPrimary
    viewport_overlays: list[ViewportOverlay] = []
    bottom_cards: list[BottomCard] = []
    state_sha: str  # SHA-256 of canonical input state
    decided_at: str  # ISO 8601 UTC
```

## Priority decision tree (the `decide()` semantics)

```
decide(state) -> frame:
  artifacts = load_audit_artifacts(state.case_id)
  completeness = analyze_case_completeness(state.case_id)
  problems = extract_problems(artifacts, completeness)
  step_problems = [p for p in problems if step_relevant(p, state.step)]

  # Priority 1: FAIL on current step
  if step_problems and step_problems[0].severity == "fail":
    return frame_from_problem(state, step_problems[0])

  # Priority 2: critical missing field on current step
  step_gaps = [g for g in completeness.missing
               if step_relevant(g, state.step) and g.severity == "critical"]
  if step_gaps:
    return frame_from_gap(state, step_gaps[0])

  # Priority 3: WARN on current step
  if step_problems and step_problems[0].severity == "warn":
    return frame_from_problem(state, step_problems[0])

  # Priority 4: warning/info gap on current step
  step_soft_gaps = [g for g in completeness.missing
                    if step_relevant(g, state.step)
                    and g.severity in ("warning", "info")]
  if step_soft_gaps:
    return frame_from_gap(state, step_soft_gaps[0])

  # Priority 5: step default
  return step_default_frame(state)
```

**Step-relevance mapping** (which JSON-path / artifact belongs to which step):
- Step 1 (Geometry): `geometry_contract.*` + `geometry_report.json`
- Step 2 (Mesh): `mesh_contract.*` + `mesh_report.json`
- Step 3 (Physics): `physics.*` + `compressible_contract.*` + `les_contract.*` + `vof_contract.*` + `solver_contract.*`
- Step 4 (BCs): `bc_contract.*` + `bc_quality.json` + `bc_audit.json`
- Step 5 (Solve+Postp): `solver_contract.residual_targets.*` + `qoi_contract.*` + `trust_report.json`

## Closure criteria

- [x] Backend schema + service + route landed (commits `75210f8`, `4ef8b65`)
- [x] Backend tests passing — 29/29 (20 from R0 + 9 R1 regression)
- [x] Frontend components + hook landed (commit `f7ec6c5`)
- [x] Frontend unit tests passing — 16/16
- [x] Wired into StepPanelShell.tsx behind `?dynamic_frame=1` flag
- [x] case_007 dogfood report written (commit `304f0d9`) — anti-pattern check PASS at every transition
- [x] Gap #48 + Gap #49 surface as bottom_cards on Step 4 + Step 3 respectively (dogfood verified)
- [x] Codex R0 review APPROVED — R0 CHANGES_REQUIRED (3 P1 + 1 P2) closed in 1 round via verbatim R1 fix
- [x] DEC flipped Proposed → Accepted (this commit)
- [ ] Notion sync at session-end batch

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Existing Step* React components break when dynamic layer added | Additive layer (per user Q1=B); existing components untouched; feature flag for rollback |
| `decide()` becomes a god function | Priority decision tree explicit + linear; ≤200 LOC service file target |
| V130 violation slips in (LLM call in decide()) | Test `test_decide_makes_no_network_calls` asserts no httpx/aiohttp/openai imports invoked |
| State SHA changes on incidental fields (e.g. timestamps) → frame flaps | Canonicalize input state before SHA (sort keys, drop volatile fields) |
| case_007 dogfood reveals semantic gap in step-relevance mapping | Mapping is in code, not config — easy to extend in cycle 2 |
| Cycle scope creeps past 700 LOC | Topbar CTA + manifest PATCH explicitly deferred to cycle 2 |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED (Accepted 2026-05-22)
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` (especially §3 4-driver model + §4 state-machine sketch + §8 success criteria)
- User scoping answers 2026-05-22: Q1=Backend+additive, Q2=case_007, Q3=all-3-slots
- Existing service composed with: `ui/backend/services/case_completeness/` (DEC-V61-116)
- Existing UI shell extended: `ui/frontend/src/pages/workbench/StepPanelShell.tsx` (DEC-V61-096)

Surface-scan-found: ui/backend/services/case_completeness/__init__.py · disposition: extend
