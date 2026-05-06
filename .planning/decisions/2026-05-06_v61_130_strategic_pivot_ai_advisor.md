---
decision_id: DEC-V61-130
title: Strategic pivot · AI is advisor, not actor · Workbench-first / Fluent-StarCCM parity baseline / on-demand AI review-and-diagnose only
status: Proposed (2026-05-06 · STRATEGIC pivot — autonomous_governance rule change → MANDATORY Kogami review per project CLAUDE.md §"Kogami trigger checklist". Codex governance review not directly triggered by this DEC because it is a charter / methodology document, not code; M1 implementation DECs that follow WILL trigger Codex review per RETRO-V61-001.)
codex_tool_report_path: n/a (charter DEC, no code diff to review; M1 sub-DECs carry their own Codex chain reports)
kogami_review_path: .planning/reviews/kogami/v61_130_strategic_pivot_2026-05-06/ (to be created)
codex_review_relay: n/a (charter)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-05-06
authored_under: User 2026-05-06 mandate "我觉得需要转变设计思路" + "把这次开发规划牢牢记住，开启长期开发推进，全都按照你的建议来" — explicit strategic redirect after V129a closed. The user identified that the prior trajectory (Phase A meshing 三明治 with AI auto-apply paths via regenerate_mesh / Accept-proposal) optimizes for AI-driven workflow at the cost of engineer trust, and that industrial CFD culture rejects AI silently mutating case files. New charter: the workbench must be a Fluent/StarCCM-parity tool that runs the full simulation lifecycle WITHOUT the LLM, and AI re-enters as a consultant — review on demand, diagnose on failure, never write to case files.
parent_decisions:
  - DEC-V61-087 (three-layer governance · this DEC is itself an autonomous_governance rule change → triggers Kogami)
  - DEC-V61-088 (pre-implementation surface scan · this DEC carries Surface-scan trailer)
  - RETRO-V61-001 (risk-tier · the M1 sub-DECs that follow will be Codex-pre-merge per cross-contract triggers)
  - DEC-V61-097 / DEC-V61-098 / DEC-V61-100 (AI-COPILOT envelope + tool dispatch · the regenerate_mesh / Accept-proposal auto-apply paths defined here will be DEPRECATED in M1)
  - DEC-V61-122 → DEC-V61-129a (Phase A + Phase E shell entry · all KEPT — these are data-display only, no AI auto-mutation, fully compatible with new charter)
parent_artifacts:
  - .planning/decisions/2026-05-06_v61_130_strategic_pivot_ai_advisor.md (this file)
  - .planning/ROADMAP.md (to be created/rewritten by M1.1 — current roadmap predates pivot)
  - ui/backend/services/ai_actions/__init__.py (existing AI action dispatcher · M1 will deprecate auto-apply paths)
  - ui/backend/routes/case_solve.py (envelope mode dispatch · M1 will keep envelope but stop the auto-apply trigger)
  - ui/frontend/src/pages/workbench/step_panel_shell/* (existing AI-COPILOT panels · M1 will reframe as "advise → user clicks button")
counter_impact: +1 (autonomous_governance: true · charter / governance rule change. Kogami-trigger check: IS governance-rule change → MANDATORY Kogami review before status=Accepted. Codex: charter DECs are not code-diff reviews per project CLAUDE.md §"Skip Kogami when ... meta-DECs touching DEC-V61-087 / its successors" — but this DEC is NOT meta-Kogami-files; it's a charter that REPLACES the Phase A "AI-driven workflow" arc that ended in V126. Per RETRO-V61-001 risk-tier, no code = no Codex. M1 implementation DECs DO trigger Codex.)
notion_sync_status: not_synced (sync after Kogami review, per Kogami contract — Notion archives the Accepted state, not Proposed)
self_estimated_pass_rate: 70% (predicted Kogami may flag 1-2 governance-hygiene findings in the charter wording — typical for charter-class DECs per V61-087/088 history; 70% reflects a clean charter with reasonable chance of some scope-clarification or phrase-tightening). Kogami CHANGES_REQUIRED would block status=Accepted; APPROVE_WITH_COMMENTS allows close-inline per V61-088 convention.

---

# DEC-V61-130 · Strategic pivot · AI is advisor, not actor

## 1. Why now (the pivot)

The user's 2026-05-06 mandate identified two flaws in the prior trajectory:

1. **AI auto-apply paths violate engineer trust.** The Phase A arc (DEC-V61-097/098/100/120-126) built a workflow where AI proposes mesh / BC actions and a single Accept click invokes the underlying mutation routes (`api.meshImported`, `api.setupBC`, the regenerate_mesh tool). Industrial CFD culture rejects this — engineers want a workbench they trust, where AI can advise but never silently write to case files.

2. **The workbench is not Fluent/StarCCM parity yet.** Total module coverage estimated at ~17% (Geometry import / Meshing / Physics / Materials / BCs / Solver / Post & Report). Without LLM-offline completeness, the workbench is a demo, not a tool.

This DEC formalizes the redirect. The remaining 80%+ of workbench functionality must be built before AI re-enters at the right layer: as an **on-demand consultant** that reads case state and produces structured advice, **never modifying files**.

## 2. New charter — three principles

**Principle A · Workbench-first, Fluent/StarCCM parity baseline**
- The workbench MUST allow an engineer to complete the full simulation lifecycle (geometry → mesh → physics → materials → BC → solver → post → report) with **zero LLM dependency**.
- Module coverage targets (per M2-M5 in §4):
  - A Geometry / Import: 30% → 70%
  - B Meshing: 25% → 60%
  - C Physics models: 5% → 50%
  - D Materials: 0% → 50%
  - E Boundary conditions: 20% → 60%
  - F Solver controls: 15% → 60%
  - G Post-processing & reports: 25% → 60%

**Principle B · AI is advisor, not actor (the hard contract)**
- AI code paths (LLM tool dispatch, ai-coach, AI-COPILOT envelopes) MUST NOT issue PUT/POST to case-mutating endpoints: `/api/import/*/mesh`, `/api/import/*/setup-bc`, `/api/cases/*/face-annotations`, `/api/cases/*/dicts`, `/api/cases/*/run`, etc.
- Permitted AI operations: GET (read state), advise (return structured recommendations to the UI), surface to engineer.
- Engineer is the only writer. Engineer clicks an explicit button (e.g., "[apply suggested mesh refinement]") to invoke any mutation. The button shows the AI's suggested parameters; the engineer reviews and confirms.

**Principle C · AI value is review-on-demand and diagnose-on-failure**
- Two and only two AI invocation points in the workbench UI:
  1. **「AI 审查」(AI Review)** — explicit button, default collapsed. Engineer clicks after building a case; AI pulls case-completeness + mesh-quality + face-annotations + classification + (engineer-provided) simulation goal, consults knowledge base, returns structured review report (✓ pass / ⚠️ note / ✗ fix-required, each with reason + suggestion + file path). No file modification.
  2. **「AI 诊断」(AI Diagnose)** — appears as a problem indicator when a case fails (mesh fail / solver diverge / results deviate from benchmark). Engineer clicks; AI pulls failure context (logs, residual history, last dict snapshots), consults knowledge base for failure-mode patterns, returns root-cause hypothesis + evidence + remediation steps. No file modification.
- The dialog-panel "uncertain / blocked envelope" pattern (DEC-V61-098 §A) is RE-PURPOSED but NOT discarded — it remains the conversational substrate for both invocation points. What changes: it is no longer triggered automatically by every `[AI 处理]` click. It triggers only inside the AI Review / AI Diagnose flows.

## 3. What stays / what deprecates

### Stays (no rework, fully compatible with new charter)

| DEC range | Content | Why kept |
|---|---|---|
| V120-V126 | mesh-quality data pipeline + Docker checkMesh integration + V126 schema discrimination | Pure read paths. AI consults this data without writing. |
| V127 | Step 2 mesh-quality card · verdict pill + 3 gauges | Display-only. Engineer-readable. |
| V128 | Patch chip derived coloring | Display-only. |
| V129a | Per-patch severe-non-ortho count from nonOrthoFaces faceSet | Display-only; the new "AI Review" will consume this same data. |
| Step 1 STL import (V108 lineage) | Geometry import | Workbench-first foundation. Will be expanded in M2. |
| Step 5 report-bundle (V61-094 / V61-110) | matplotlib-driven HTML report | Workbench-first; M5 will deepen this. |

### Deprecates (M1 work)

| Path | Why deprecated | Replacement |
|---|---|---|
| `regenerate_mesh` tool dispatch (DEC-V61-100) — auto-applies via `api.meshImported` | AI mutates case file | Tool returns `{suggested_mesh_mode, reason}` only; UI renders suggestion card; engineer clicks `[AI 处理]` to invoke (existing button, same code path, but engineer-driven) |
| ai-coach `proposal-applied` event with auto-trigger for setup-bc | AI mutates case file | Same pattern: AI returns suggestion; engineer's existing Accept button now means "I read the suggestion and want to apply it myself", not "AI please go execute" |
| Bidirectional dialog auto-loop (after engineer answers, AI re-runs setup automatically) | AI mutates case file | Engineer clicks `[继续 AI 处理]` to re-run; this is already the existing UI; M1 just removes any background auto-trigger |

### Reframes (kept, but semantically reinterpreted)

| Path | Old semantic | New semantic |
|---|---|---|
| AI-COPILOT envelope mode (`?envelope=1`) | AI's confident path auto-writes BC | Endpoint behavior unchanged; the FRONTEND no longer auto-fires it. It fires only inside the AI Review flow, where the engineer has explicitly asked AI to evaluate. |
| `[AI 处理]` button | "AI please act on this step" | "Apply the suggested action AI just produced (and which I read)" |
| DialogPanel uncertain/blocked questions | High-frequency interrupt | Only surfaces when engineer is in AI Review flow |

## 4. Phased roadmap (M1-M6)

### M1 · AI auto-apply path deprecation (immediate · 2-3 sub-DECs)

- **M1.1 · DEC-V61-131**: Deprecate `regenerate_mesh` tool auto-apply. Tool returns advisory payload only; UI renders "AI suggests mesh_mode=X because Y" card; existing engineer-driven `[AI 处理]` button stays. Reframe ai-coach `proposal-applied` listener to no-op for AI mutation paths.
- **M1.2 · DEC-V61-132**: Backend write-permission audit. Add a regression test that greps `services/ai_actions/` + `routes/ai_*` for any `requests.post`, `client.put`, `api.meshImported`, `api.setupBC` calls and fails the build if found. Establish the hard contract.
- **M1.3 (optional) · DEC-V61-133**: ROADMAP.md rewrite. Replace the Phase A→B→C→D→E→F→G arc with M1-M6 breakdown.

### M2 · Mesh control parity (4-6 sub-DECs · B 25% → 60%)

- M2.1 sizing field UI (base / min / max / curvature / proximity)
- M2.2 region refinement (box / sphere / STL-driven)
- M2.3 prism layer controls (first-cell-height / growth-rate / num-layers / total-thickness)
- M2.4 checkMesh remediation hints rendered for human reading (not AI auto-fix)
- M2.5 mesh history panel (re-mesh attempts visible to engineer)
- M2.6 (optional) Cartesian / polyhedra mesh modes

### M3 · Physics models + Materials (5-7 sub-DECs · C 5%/D 0% → 50%)

- M3.1 physics selection panel (incompressible / compressible · laminar / RANS / LES)
- M3.2 turbulence model picker (k-ε / k-ω / SST / SA)
- M3.3 energy equation toggle + radiation
- M3.4 multi-phase off / VOF / Mixture
- M3.5 fluid material library (air / water / steel — with viscosity laws, polynomial / piecewise / table)
- M3.6 solid material library
- M3.7 (optional) reactive flow / MRF

### M4 · BC palette + Solver controls (4-6 sub-DECs · E 20%/F 15% → 60%)

- M4.1 full BC palette (velocity-inlet, mass-flow-inlet, pressure-inlet, pressure-outlet, mass-flow-outlet, outflow, wall variants, symmetry, periodic, axis, interface)
- M4.2 solver pressure-velocity coupling selector (SIMPLE / SIMPLEC / PISO / PIMPLE / Coupled)
- M4.3 discretization scheme picker (upwind / central / QUICK / MUSCL) + URF panel
- M4.4 monitor probes (force / moment / pressure / line-integral / surface-integral)
- M4.5 residual target + residual plot live updates
- M4.6 (optional) parametric sweep harness

### M5 · Post-processing + Reports (3-5 sub-DECs · G 25% → 60%)

- M5.1 contour / vector / streamline interactive overlays
- M5.2 iso-surface + slice + probe-line tools
- M5.3 volume-integral / surface-integral computations
- M5.4 report templates (parameter table + key-results table + comparison-against-benchmark)
- M5.5 (optional) animation export

### M6 · AI advisor stack (4-6 sub-DECs · starts after M2-M5; M6.1 may parallelize from M2)

- M6.1 knowledge-base RAG backend (OpenFOAM docs + Fluent/StarCCM user manual chapters + classic CFD textbook excerpts + internal failure-mode library) — can run in parallel with M2 since it's an independent backend service
- M6.2 「AI 审查」 button + structured review report frontend
- M6.3 review-report payload contract + backend route (consumes case-completeness + mesh-quality + annotations + KB; emits structured ✓/⚠️/✗ tree)
- M6.4 「AI 诊断」 button + failure-context aggregator + KB consult
- M6.5 contract test: AI advisor stack is read-only — no file mutation calls (regression test from M1.2 stays armed)
- M6.6 (optional) post-session learning loop — accepted advice patterns feed back into KB

## 5. What this means for in-flight work

- **Current 21 unpushed commits (V127/V128/V129a chain)** — fully compatible with new charter. **Push to origin/main as scheduled** once base review completes (no charter conflict).
- **Running base-review (bfz9qiadh)** — keep running for the cadence-floor verified trailer; the diff is data-display code, charter has no objection.
- **Future Codex chain reports** — the `Phase E shell entry` framing is replaced by `M0 closed` framing; chain reports for M1.1+ will reference M1-M6 instead of the old Phase A-G arc.

## 6. Risk register

1. **Engineer dogfood gap during M2-M5** — until M2-M5 finish, the workbench is genuinely below Fluent parity. Mitigation: M0 (existing functionality) is honestly labeled "phase 1 dogfood — STL → LDC / channel only" in the UI; M2-M5 expand surface incrementally with each DEC adding one feature column.
2. **Existing AI auto-apply UX habit** — engineers and dogfooders who used the workbench under Phase A may experience friction when the AI-Accept button no longer auto-runs. Mitigation: M1.1 keeps the `[AI 处理]` button visible at the same place; only the underlying intent changes ("apply suggestion" not "AI please go").
3. **AI advisor adoption pull** — if M6 ships and engineers don't use it, AI value is unproven. Mitigation: M6.1 RAG backend has independent value (engineers can browse CFD knowledge directly), so even partial adoption returns value.
4. **Kogami governance rule-change blast** — this DEC IS a governance rule change; Kogami review may flag scope ambiguity. Mitigation: §2 "Three principles" + §3 "Stays/Deprecates/Reframes" tables are deliberately concrete and grep-able.

## 7. Acceptance criteria

- This DEC's status MUST become Accepted only after Kogami review APPROVE or APPROVE_WITH_COMMENTS (close-inline per V61-088). Kogami CHANGES_REQUIRED blocks Accepted.
- Following Kogami APPROVE: M1.1 sub-DEC opens (`regenerate_mesh` tool deprecation).
- Notion sync only after Accepted (charter DECs sync the Accepted state, not Proposed).
- Memory artifacts saved (this happened pre-DEC at 2026-05-06):
  - `~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_harness_ai_advisor_pivot.md`
  - `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_harness_roadmap_v2.md`
  - MEMORY.md index updated.

Surface-scan: clean (charter DEC; no code grep needed for "is this already implemented" since the charter is itself the new spec).
