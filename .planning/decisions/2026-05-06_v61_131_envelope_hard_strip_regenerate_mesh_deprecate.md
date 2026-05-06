---
dec_id: V61-131
title: Envelope mode backend hard-strip + regenerate_mesh tool deprecate (advisory only)
status: Accepted (R17 · 2026-05-06 · 86gs APPROVE on c20dade)
parent_dec: V61-130
parent_artifacts:
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md
  - ui/backend/services/ai_actions/__init__.py
  - ui/backend/services/ai_actions/classifier/__init__.py
  - ui/backend/services/llm_coach/tool_registry.py
  - ui/backend/services/case_annotations/__init__.py
  - ui/backend/routes/case_solve.py
  - ui/backend/routes/case_annotations.py
  - ui/backend/routes/ai_coach.py
  - ui/backend/schemas/ai_action.py
  - ui/backend/schemas/case_solve.py
  - ui/frontend/src/api/client.ts
  - ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx
  - ui/frontend/src/pages/workbench/step_panel_shell/AnnotationPanel.tsx
  - ui/frontend/src/pages/workbench/step_panel_shell/ProposalCard.tsx
  - ui/frontend/src/pages/workbench/step_panel_shell/types.ts
phase: N1 (workbench-first / AI is advisor)
trigger: V130 charter §4 N1.1 — Kogami P1 finding #2 close (backend hard-strip)
autonomous_governance: true
counter_impact: +1
counter_value_after: 28
external_gate_self_estimated_pass_rate: 70%
external_gate_actual_outcome: 17 rounds (R0 → R17 APPROVE; CRS once on R10 fallback when 86gs 503)
codex_review_relay: 86gs (xhigh) primary; CRS (high) fallback round R10 when 86gs 503
codex_tool_report_path: /tmp/n11_r17_review_86gs.log (last round APPROVE)
notion_sync_status: pending (session-end batch)
---

# DEC-V61-131 · N1.1 · Envelope hard-strip + regenerate_mesh deprecate

## 1. Goal

Enforce V130 Principle B at the backend layer (per Kogami P1 #2 close): the
two AI code paths that currently mutate the case (envelope mode of
`POST /setup-bc` and `regenerate_mesh` tool dispatch) **stop mutating**.
They become advisory: they read, classify, and emit a structured
suggestion the engineer applies (or doesn't) by clicking a confirm button
that calls the legacy non-envelope mutation route.

This is the load-bearing implementation of V130's "AI is advisor not actor"
contract. N1.2 (DEC-V61-132) will add the backend `MUTATING_ROUTES`
registry + behavioral test that locks the contract.

## 2. Scope

**In scope (R0 backend):**
- `ui/backend/services/ai_actions/__init__.py setup_bc_with_annotations`:
  remove `setup_ldc_bc` / `setup_channel_bc` calls from confident branches.
  Confident envelope returns advisory payload describing what *would* be
  applied (lid/wall counts via classifier output, not by writing dicts).
  `force_uncertain` still surfaces the dialog questions but no longer wraps
  a real `setup_ldc_bc` write.
- `ui/backend/services/llm_coach/tool_registry.py _handle_regenerate_mesh`:
  remove `mesh_imported_case` call. Return `ApplyResult` describing the
  mode/density the AI suggests; no polyMesh rewrite.

**In scope (R0 frontend):**
- `ui/frontend/src/api/client.ts setupBCWithEnvelope`: remove
  `dispatchMeshMutated` call (envelope no longer mutates polyMesh under
  any branch).
- `ui/frontend/src/pages/workbench/step_panel_shell/steps/Step3SetupBC.tsx`:
  on confident envelope, render an `[应用 AI 建议]` button that calls
  `api.setupBC` (legacy non-envelope route) to actually apply the BC
  setup. The legacy route remains the only mutation surface for Step 3.
- `ProposalCard` (ai-coach proposal list): when the proposal's tool is
  `regenerate_mesh`, render advisory state (no Accept button); engineer
  manually re-meshes via Step 2.

**In scope (R0 tests):**
- Update `tests/test_setup_bc_envelope_route.py` to assert the new
  contract: confident envelope does NOT write `0/U`, `0/p`, etc.;
  payload carries summary + suggested action shape only.
- Update `tests/test_llm_coach_tool_registry.py regenerate_mesh` cases:
  no polyMesh rewrite; ApplyResult.summary describes suggestion.
- Add one new behavioral test asserting that the envelope code path
  is callable without polyMesh existing (no mutation = no precondition).

**Out of scope (defer to N1.2):**
- `MUTATING_ROUTES` registry module + sentinel HTTP client behavioral test.
- Pre-commit grep lint warning layer.
- Pre-commit hook for AI-path import cleanliness.

## 3. Contract change details

### 3.1 setup_bc_with_annotations envelope

Before (V61-098 / V61-100 / V61-101):
- classifier confident → `setup_ldc_bc` or `setup_channel_bc` writes
  `0/*`, `system/controlDict`, etc., then envelope returns
  `confidence='confident'` with summary "Set up LDC defaults: lid=N..."
- classifier blocked → no write, blocked envelope.
- classifier uncertain → no write, uncertain envelope with questions.
- `force_blocked` → no write, blocked envelope.
- `force_uncertain` → `setup_ldc_bc` runs, then wraps as 'uncertain'.

After (N1.1):
- classifier confident → **NO write**. Envelope returns
  `confidence='confident'` with summary describing what would be applied
  (`"AI is confident this is an LDC cube. Click [应用 AI 建议] to apply: lid=N faces, walls=M faces, Re=X."`).
  The frontend's `[应用 AI 建议]` button calls legacy `api.setupBC` to
  actually mutate.
- classifier blocked → unchanged (blocked envelope, no write).
- classifier uncertain → unchanged (uncertain envelope with questions, no write).
- `force_blocked` → unchanged (blocked envelope, no write).
- `force_uncertain` → **NO write**. Envelope returns `confidence='uncertain'`
  describing what would be applied with the LDC questions appended (purely
  for dialog dogfood; the engineer answers, the next confident envelope
  surfaces the apply button).

### 3.2 _handle_regenerate_mesh

Before (V61-123 / V61-124 / V61-125):
- `mesh_imported_case(case_id, ...)` rewrites `polyMesh/` in place under
  case_lock; ApplyResult carries the actual cell_count/face_count.

After (N1.1):
- Handler **does not call** `mesh_imported_case`. Returns ApplyResult
  describing the suggested mesh_mode / target_cell_count / lc_override.
  `state_after` carries the suggestion (not actual mesh state).
- The proposal-applied UI path becomes a no-op for `regenerate_mesh`;
  the engineer re-meshes via Step 2's `[AI 处理]` button (which is a
  human-driven `api.meshImported` call).

### 3.3 Envelope schema

`AIActionEnvelope` already has `summary` + `next_step_suggestion` fields
that fit advisory mode. R0 does NOT add a new `suggested_action` field —
the frontend infers "apply" from `confidence === 'confident'` since
that is now the only meaning of confident. If a structured action
selector is needed in N2+ (e.g., to support multiple AI tools), that's
a forward extension.

## 4. Verification

R0 checklist:
- [ ] Backend grep: `services/ai_actions/__init__.py` and
  `services/llm_coach/tool_registry.py` contain no `setup_ldc_bc(`,
  `setup_channel_bc(`, or `mesh_imported_case(` call sites in the
  AI dispatch paths.
- [ ] Existing envelope/tool-registry test suites updated; full pytest
  green.
- [ ] New behavioral test: envelope mode runs against a case with NO
  polyMesh (mesh-missing) and the classifier-blocked path returns
  blocked envelope without raising; this is testable today only because
  the strip removes the precondition that polyMesh exist for the
  confident write.
- [ ] Frontend Step 3 confident envelope renders `[应用 AI 建议]` button.
- [ ] `dispatchMeshMutated` is no longer called from
  `setupBCWithEnvelope`.

## 5. Predicted rounds

V123 §L1 cross-contract calibration: contract change touching
backend + frontend + tests + AI dispatch surface. Predict 3-4 rounds.

## 6. Risks

- **Test churn**: ~30 existing tests assert mutation-on-confident; R0
  must rewrite their assertions. Risk of regression by misreading test
  intent. Mitigation: rewrite by intent ("did N happen?" → "does
  envelope describe N?"), don't just delete assertions.
- **Engineer UX friction**: Step 3 used to complete on AI click;
  now needs a second click. Mitigation: V130 §6 risk #1 already
  scoped this — UX label updates ship with R0.
- **Existing dogfood scripts**: `scripts/smoke/dogfood_loop.py` may
  call envelope mode expecting mutation. Audit + adjust in R0.

## 7. Decision

**R0 (this commit)**: backend strip + frontend confirm button + test
updates. Push for Codex review. On APPROVE, advance to Accepted and
proceed to N1.2.
