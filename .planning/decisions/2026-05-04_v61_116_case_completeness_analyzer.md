---
decision_id: DEC-V61-116
title: Case completeness analyzer · backend service + sticky right-rail "距离入库标准还差 N 项" card
status: Proposed (2026-05-04 · authored under user 2026-05-04 autonomous-mode mandate "全都按你的建议来"; arc item C; awaiting Codex pre-merge approval per RETRO-V61-001 risk-tier)
codex_tool_report_path: pending
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-04
authored_under: User 2026-05-04 design discussion — "AI助手不仅提供自动化的操作建议，同时也要时刻记得'按照项目的治理规则，用户目前还需要提供哪些信息，才能让这个case更完整，指引、配合用户来让case最终达到可以入库的标准'". Five-DEC arc plan A→C→B→D→E confirmed by user "全都按你的建议来"; this is item C — the rule-based foundation for the eventual LLM-wrapped completeness coaching (V61-119 · item E).
parent_decisions:
  - DEC-V61-115 (workbench-first default landing · this DEC's right-rail card mounts inside the StepPanelShell that V61-115 raised the visibility of)
  - DEC-V61-046 (precondition tri-state contract · this DEC reads the same precondition.satisfied: bool|"partial" tri-state from gold_standards/{case_id}.yaml without bool-coercing "partial")
  - DEC-V61-088 (pre-implementation surface scan rule · this DEC carries Surface-scan-found trailer per §)
  - RETRO-V61-001 (risk-tier · new backend service + new operator endpoint + multi-file frontend = mandatory Codex pre-merge)
parent_artifacts:
  - knowledge/schemas/gold_standard_schema.json (oneOf · StructuredGoldStandardFile required: case_id + source + observables; LegacyGoldStandardFile = array)
  - knowledge/gold_standards/lid_driven_cavity_benchmark.yaml (canonical Phase 8 alias shape · physics_contract block at lines 7-20: geometry_assumption + reference_correlation_context + physics_precondition[] + contract_status + precondition_last_reviewed)
  - ui/backend/services/case_manifest/schema.py:136-174 (CaseManifest v2 · physics + bc + numerics + overrides + history sections)
  - ui/backend/services/case_drafts.py:90-114 (lint_case_yaml · existing structural-gap detector — extension target, not duplication target)
  - ui/backend/services/validation_report.py:565-664 (_derive_contract_status · keep this for run-time concerns; completeness analyzer operates on config YAML, NOT on solver output)
  - ui/backend/services/case_inspect/preview.py:1-80 (existing precedent for "snapshot of current state" service — naming + return-shape pattern to mirror)
  - ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx:22-57 (right-rail mount point: above the scrollable Body div, below the header)
counter_impact: +1 (autonomous_governance: true · new presentation surface for existing governance schemas, NOT a governance-rule change. Kogami-trigger check: not a phase-close, not a RETRO draft, not a high-risk PR (no enforcement — `ready_for_archive` is informational, not gating archival), not arc-size retro, not a governance rule-change DEC · Kogami SKIP per DEC-V61-087 §4.2. Codex pre-merge MANDATORY per RETRO-V61-001 multi-file frontend + new operator endpoint triggers.)
self_estimated_pass_rate: 60% (MEDIUM baseline. Scope: new backend module (~3 files: analyzer.py + schemas.py + __init__.py) + new route + new frontend type + new sticky card component (~6 files total, ~400-500 LOC). Risk surface: (a) Codex may flag the gold-vs-draft schema divergence (different shapes need different completeness rules), (b) Codex may want explicit ready_for_archive threshold rationale rather than ad-hoc, (c) Codex may catch that "missing field X" must distinguish "absent" from "explicitly null", (d) Codex may want unit tests for the analyzer with both whitelist + imported drafts, (e) Codex may want the right-rail card to gracefully degrade when /api/cases/{id}/completeness 404s (case not yet saved). Expect 2-3 rounds; possible P1-P2 on edge cases.)
notion_sync_status: pending (will sync after Codex APPROVE + commit lands)

---

# DEC-V61-116 · Case completeness analyzer

## Why now

User feedback 2026-05-04 design-discussion turn (verbatim): "AI助手不仅提供自动化的操作建议，同时也要时刻记得'按照项目的治理规则，用户目前还需要提供哪些信息，才能让这个case更完整，指引、配合用户来让case最终达到可以入库的标准'".

This is the most product-differentiating point in the user's three-part workbench redesign — market AI for CFD does automation; nobody surfaces governance-aware completeness coaching. The repo already encodes 90% of the knowledge needed (gold_standard_schema · physics_contract preconditions · case_manifest required fields · contract_status enum), but there is **no service that reads a working case and tells the user "you still need fields X / Y / Z before this can be archived"**.

Without it:
- Engineers don't know they're missing a turbulence_model until solver run-time crashes
- Imported STL cases land with `solver: laminar` default and never get prompted to set Re-appropriate turbulence
- No checklist guides a user from "draft" to "ready for archive" — the only signal is the eventual contract_status verdict on a solver run, which is *measurement-time*, not *config-time*
- The eventual LLM-wrapped coaching (V61-119) needs a deterministic rule-based foundation; without it, the LLM has to re-derive completeness from raw schemas every conversation

## Decision

**3-part deliverable**, ALL rule-based (no LLM in this DEC):

### Part 1: Backend service `ui/backend/services/case_completeness/`

New module with 3 files:

#### `schemas.py` — Pydantic response shape

```python
class MissingField(BaseModel):
    field_path: str  # JSON-path: "physics.turbulence_model" or "boundary_conditions.inlet.patch_type"
    severity: Literal["critical", "warning", "info"]
    why: str  # human-readable: "required by physics contract: Re=15000 implies non-laminar"
    suggested_default: Any | None = None  # optional fallback for auto-fill UI

class CaseCompletenessReport(BaseModel):
    case_id: str
    case_kind: Literal["whitelist", "imported_user", "draft"]  # provenance
    ready_for_archive: bool
    blocked_by_critical: int  # count of severity=critical missing
    present_count: int
    total_count: int
    percentage: float  # 100.0 * present / total
    missing: list[MissingField]
    notes: list[str] = []  # contextual explanations (e.g., "this case has no gold standard linked; using minimal contract")
```

#### `analyzer.py` — The diff engine

Three-layer analysis:
1. **Manifest-level** (always runs): read `CaseManifest` v2; validate required physics + bc + numerics fields are non-null. Use existing `case_manifest.read_case_manifest()` (handles v1→v2 migration).
2. **Gold-contract-level** (runs only if a gold_standard YAML exists for the case_id): read `knowledge/gold_standards/{case_id}.yaml`; for each `physics_precondition` entry where `satisfied_by_current_adapter: false` or `"partial"`, emit a missing-field with `severity = critical` (false) or `warning` ("partial"). Preserves the V61-046 tri-state — never bool()-cast "partial".
3. **Source-origin-aware** (imported_user vs whitelist): imported cases get a *minimal* contract (turbulence_model must be Re-appropriate; STL must be watertight; solver must match flow_type). Whitelist cases get the full gold contract.

`ready_for_archive` = `(blocked_by_critical == 0) AND (manifest required fields all present)`. Does NOT require percentage = 100% (warnings + info are non-blocking).

#### `__init__.py` — Public surface

Exports `analyze_case_completeness(case_id: str) -> CaseCompletenessReport`. Single entry point; no internal helpers leaked.

### Part 2: New route `GET /api/cases/{case_id}/completeness`

Mount in `ui/backend/routes/cases.py` (existing file, extend pattern). Returns `CaseCompletenessReport`. 200 if case exists; 404 if not. No 500 on incomplete data — the WHOLE POINT of the endpoint is to surface incompleteness without crashing.

### Part 3: Frontend sticky card in StepPanelShell right rail

#### `ui/frontend/src/types/case_completeness.ts` — TS mirror of CaseCompletenessReport

#### `ui/frontend/src/api/client.ts` — Add `getCaseCompleteness(caseId)` per existing `get<Resource>` pattern (sibling of `getMeshMetrics`, `getPreflight`, `getWorkbenchBasics`)

#### `ui/frontend/src/pages/workbench/step_panel_shell/CompletenessCard.tsx` — NEW component

Mounted as the FIRST child inside TaskPanel's scrollable Body div (per surface map: "scrolls with step content, integrates seamlessly"). Renders:

- **Compact summary bar**: "距离入库标准还差: **3 项** · 完整度 **78%**" with status pill (绿: ready_for_archive · 黄: warnings only · 红: blocked_by_critical > 0)
- **Click-to-expand** missing-fields list: each row = `[severity icon] field_path · why` + `[去补全 →]` button (Tier-A: button is `disabled` placeholder; click-through-to-step is V61-117 scope)
- **Empty state**: when ready_for_archive=true and percentage=100%, shows "✓ 已达入库标准" with green pill
- **Loading state**: "完整度分析中…" while React-Query fetches
- **Error state**: graceful "（完整度分析暂不可用）" — non-blocking; the workbench still works without this card

Use React Query with key `["case-completeness", caseId]`, stale-time 30s (re-fetches on case-edit success).

## Acceptance criteria

§1 New service `ui/backend/services/case_completeness/` exists with 3 files (schemas.py · analyzer.py · __init__.py). `analyze_case_completeness(case_id)` returns the documented `CaseCompletenessReport` shape.

§2 Three-layer analysis implemented:
- Manifest-level: required fields detection on CaseManifest v2 (physics.solver, physics.turbulence_model, bc.patches non-empty, etc.)
- Gold-contract-level (gated on gold YAML existence): physics_precondition tri-state preserved (`satisfied: bool|"partial"` → severity mapping, NEVER bool-coerced)
- Source-origin-aware: imported_user gets minimal contract; whitelist gets full gold contract

§3 New route `GET /api/cases/{case_id}/completeness` returns 200 with valid payload for: (a) a whitelist case (lid_driven_cavity), (b) an imported user draft, (c) a case_id with no gold standard linked (falls back to minimal contract + `notes` explanation). Returns 404 only if case_id doesn't resolve at all.

§4 Frontend `getCaseCompleteness(caseId)` exists and is typed with `CaseCompletenessReport`. Mirrors the existing `get<Resource>(caseId)` pattern.

§5 `CompletenessCard.tsx` renders inside StepPanelShell's right-rail TaskPanel body with: summary bar (status pill + "还差 N 项" + "完整度 X%") · expandable missing list · graceful loading / empty / error states.

§6 At least 3 unit tests (`tests/case_completeness/test_analyzer.py`):
- Whitelist case (lid_driven_cavity) with full gold → percentage 100, ready_for_archive=true
- Imported user draft missing turbulence_model with Re=15000 → critical-severity missing, ready_for_archive=false
- Case_id with no gold linked → falls back to minimal contract, returns notes explanation

§7 Frontend component test (`__tests__/CompletenessCard.test.tsx`): renders summary bar correctly for the 3 status pill colors (green/yellow/red).

§8 No regressions: existing 169 frontend tests still pass; existing backend tests (incl. case_manifest, case_drafts, validation_report) still pass.

§9 Codex pre-merge APPROVE / APPROVE_WITH_COMMENTS per RETRO-V61-001 (multi-file frontend + new backend service + new operator endpoint).

§10 Surface scan applied per V61-088: see `Surface-scan-found:` trailer.

## Out of scope

- LLM-wrapped completeness coaching — separate DEC (V61-119 · item E)
- Click-through-to-step navigation from missing-field rows — Tier-A ships disabled placeholder buttons; full wireup in V61-117 (item B · StepTree refactor with sub-nodes that can be deep-linked)
- Auto-fill of `suggested_default` values — surfaced in API response but UI doesn't apply them (engineer types the field manually for V61-116)
- Modifying existing case_manifest schemas, validation_report, or contract_status semantics — read-only consumer
- New gold_standard.yaml authoring or precondition rule changes — purely consumes existing data

## Process note

This is item C of the user-confirmed 5-DEC arc (A → C → B → D → E):
- A · V61-115 — workbench default landing flip ✅ Accepted 2026-05-04 (3-round Codex chain)
- **C · V61-116 — completeness analyzer (this DEC, rule-based foundation for V61-119)**
- ARC RETRO V61-088 → V61-114 — deferred to between this DEC and V61-117 (per user mandate; counter ≥20 trigger noted)
- B · V61-117 — StepTree expandable Fluent-style tree
- D · V61-118 — DeepSeek V4 Pro + MiniMax-M2.7-highspeed LLM integration
- E · V61-119 — LLM-wrapped completeness coaching (depends on this DEC for the deterministic checklist baseline)

Methodology: V61-115 chain report logged a NEW calibration anchor "engineer-first UI redesign with new contract: ~70% / 2-3 rounds typical". V61-116 is partially in that category (frontend card + UX) AND partially in "new backend service" category — predicting 60% reflects the compound risk.

`Surface-scan-found: ui/backend/services/case_completeness/ (new directory · top-level service · V61-088 §"new top-level service file") + ui/backend/routes/cases.py (existing route file · extend) + ui/frontend/src/api/client.ts (existing client · extend) + ui/frontend/src/types/ (new type file · sibling of existing case-detail/validation types) + ui/frontend/src/pages/workbench/step_panel_shell/CompletenessCard.tsx (new component · top-level page-folder file · V61-088 §"top-level page component") + ui/frontend/src/pages/workbench/step_panel_shell/TaskPanel.tsx (existing · extend to mount CompletenessCard) · disposition: parallel new (analyzer service + card component) + extend existing (route, client, TaskPanel mount)`

## Counter impact

This DEC's acceptance advances `autonomous_governance_counter_v61` 74 → 75. Arc retro V61-088 → V61-114 stays explicitly deferred per user mandate (task #23) until between this DEC and V61-117. Counter at retro time will be 75 (this DEC's acceptance + retro itself = +0).
