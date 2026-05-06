---
decision_id: DEC-V61-130
title: Strategic pivot · AI is advisor, not actor · Workbench-first / Fluent-StarCCM parity baseline / on-demand AI review-and-diagnose only
status: Accepted (2026-05-06 · Kogami APPROVE_WITH_COMMENTS · 6 findings (3 P1 + 2 P2 + 1 P3) closed inline per V61-088 close-inline convention · 2026-05-06 revision: M1-M6 renamed to N1-N6 to avoid collision with existing ROADMAP.md M1-M8 + §3.5 reconciliation table added + §2 Principle B / §3 envelope reframe contradiction resolved (backend hard-strip in N1) + N1.2 enforcement strengthened with behavioral test + MUTATING_ROUTES registry + counter_impact misapplied skip-clause struck + §6 multi-month-no-validation risk added with interim validation milestone after N3 + coverage % replaced with concrete capability checklists.)
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
  - ui/backend/services/ai_actions/__init__.py (existing AI action dispatcher · N1 will deprecate auto-apply paths)
  - ui/backend/routes/case_solve.py (envelope mode dispatch · N1 will hard-strip envelope mutation behavior)
  - ui/frontend/src/pages/workbench/step_panel_shell/* (existing AI-COPILOT panels · N1 will reframe as "advise → user clicks button")
counter_impact: +1 (autonomous_governance: true · charter / governance rule change. Kogami-trigger check: IS governance-rule change → MANDATORY Kogami review before status=Accepted. Codex governance review not directly triggered because no code diff; N1 implementation DECs that follow DO trigger Codex per RETRO-V61-001 cross-contract triggers.)
notion_sync_status: synced 2026-05-06 (https://www.notion.so/DEC-V61-130-Strategic-pivot-AI-is-advisor-not-actor-Workbench-first-Fluent-StarCCM-parity-b-358c68942bed81da8770c17cd9b28db0)
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
- Module checklists (replacing prior coverage-percentage framing per Kogami P3 finding — concrete capability lists are falsifiable; percentages are rhetorical):
  - **A Geometry / Import** at N-close: STL ✓ (existing) · IGES (deferred N+) · STEP (deferred N+) · multi-solid named patch ✓ (existing) · feature-edge identification (N2.x) · scale + units check ✓ (existing in M5)
  - **B Meshing** at N2-close: gmsh + sHM beginner/power ✓ (existing) · sizing field UI (base / min / max / curvature / proximity, N2.1) · region refinement (box / sphere / STL-driven, N2.2) · prism layer controls (first-cell-height / growth-rate / num-layers / total-thickness, N2.3) · checkMesh remediation hints rendered for human reading (N2.4) · mesh history panel (N2.5)
  - **C Physics models** at N3-close: incompressible / compressible toggle (N3.1) · turbulence picker (k-ε / k-ω / SST / SA, N3.2) · energy equation toggle + radiation (N3.3) · multi-phase off / VOF / Mixture (N3.4) — LES / DES / reactive / MRF deferred to N+
  - **D Materials** at N3-close: fluid library (air / water / steel — N3.5) · solid library (N3.6) · viscosity laws (constant / Sutherland / power-law) · thermal conductivity / specific heat polynomial / piecewise / table loaders
  - **E Boundary conditions** at N4-close: velocity-inlet · mass-flow-inlet · pressure-inlet · pressure-outlet · mass-flow-outlet · outflow · wall (slip / no-slip / moving / temperature / heatFlux / convective) · symmetry · periodic · axis · interface (all per N4.1)
  - **F Solver controls** at N4-close: pressure-velocity coupling picker (SIMPLE / SIMPLEC / PISO / PIMPLE / Coupled, N4.2) · discretization picker (upwind / central / QUICK / MUSCL, N4.3) · URF panel · residual target + live residual plot (N4.4-N4.5) · monitor probes (force / moment / pressure / line-integral / surface-integral, N4.4)
  - **G Post-processing & reports** at N5-close: contour / vector / streamline interactive overlays (N5.1) · iso-surface / slice / probe-line tools (N5.2) · volume-integral / surface-integral computations (N5.3) · report templates (parameter table + key-results + comparison-against-benchmark, N5.4)

**Principle B · AI is advisor, not actor (the hard contract — backend-enforced)**
- AI code paths (LLM tool dispatch, ai-coach, AI-COPILOT envelopes) MUST NOT issue PUT/POST to case-mutating endpoints. Enforcement layer: **backend, not frontend**. Per Kogami P1 finding #2 (closed inline 2026-05-06), frontend-only enforcement is insufficient because any future caller can re-violate it.
- The case-mutating endpoint set is defined in a single registry module (`ui/backend/services/ai_actions/MUTATING_ROUTES`) so "new mutation endpoint" is never silently outside the contract's coverage. Initial registry contents:
  - `POST /api/import/*/mesh` (meshImported)
  - `POST /api/import/*/setup-bc` (setupBC, including `?envelope=1` mode after N1.1 hard-strip)
  - `PUT /api/cases/*/face-annotations` (face_annotations writer)
  - `POST /api/cases/*/dicts` (dict mutator)
  - `POST /api/cases/*/run` (solver kick)
  - any future endpoint added to this registry by a downstream DEC
- Permitted AI operations: GET (read state), advise (return structured recommendations to the UI), surface to engineer.
- Engineer is the only writer. Engineer clicks an explicit button (e.g., "[apply suggested mesh refinement]") to invoke any mutation. The button shows the AI's suggested parameters; the engineer reviews and confirms.
- The `?envelope=1` mode of setup-bc currently writes BC files when AI confidence is `confident`. Per N1.1, this auto-write behavior is **stripped at the backend**: `setup_bc_with_annotations` returns the structured envelope (`confidence`, `summary`, `suggested_action`, `unresolved_questions`) but does NOT invoke `setup_ldc_bc` / `setup_channel_bc` from the AI dispatch path. The mutation routines are reachable only by the engineer-driven non-envelope `POST /api/import/*/setup-bc` (Step 3 [AI 处理] button click).

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
| AI-COPILOT envelope mode (`?envelope=1`) | AI's confident path auto-writes BC | Endpoint **behavior changes** (per Kogami P1 finding #2 close — backend hard-strip, not frontend-only): envelope mode now returns advisory payload (confidence + summary + suggested_action + unresolved_questions) WITHOUT invoking the BC mutation routines from the envelope branch. Mutation routines remain reachable from the legacy non-envelope path (engineer-driven [AI 处理] click). N1.1 backports the strip; existing endpoint contract callers see a payload-shape change (suggested_action replaces written_files), surfaced in the N1.1 chain report. |
| `[AI 处理]` button | "AI please act on this step" | "Apply the suggested action AI just produced (and which I read)" |
| DialogPanel uncertain/blocked questions | High-frequency interrupt | Only surfaces when engineer is in AI Review flow |

## 3.5 Relationship to existing ROADMAP.md M-sequences (per Kogami P1 finding #1, closed inline)

ROADMAP.md predates this charter and carries two prior M-sequences. Their fates under the new charter:

| Existing token | Existing scope | Status under V130 |
|---|---|---|
| **M1-M4** (Workbench Closed-Loop) | RealSolverDriver + edit frontend + run history + Docker fail classifier | **COMPLETE 2026-04-25** — no change. Already shipped. |
| **M5** (STL-only Case Import v0) | STL upload + patch detection + import gate | **LANDED in code** (Step 1 implemented via V108/V125 lineage). `M5.1 trust-core micro-PR` (TrustGate hard-cap on imported cases) — **STATUS UNCHANGED, still binding**. The new charter does NOT supersede M5.1; it is a separate trust-core safety gate that remains in effect. |
| **M6** (gmsh-based unstructured meshing) | gmsh + sHM beginner/power | **LANDED in code** (Step 2 implemented via V120-V126 + V127-V129a Phase E). `M6.0.1 calibration` + `M6.1 trust-core micro-PR (mesh_already_provided flag)` — **STATUS UNCHANGED, still binding**. Independent trust-core gate, kept. |
| **M7** (Fill-in M5.0 sHM stub + real OpenFOAM run on imported case + mesh budget tiering) | Solver run on imported case | **LANDED in code** (Step 4). The `M7 Path-A first-customer recruitment prerequisite` — **STATUS UNCHANGED, still binding**, and now reinforced by V130's external-validation requirement (§6 risk #5). |
| **M8** (Beginner report v0 + Docker failure root-cause UI) | Step 5 report-bundle | **LANDED in code** (Step 5 / report-bundle). |
| **M5-M8 stranger-dogfood completion gate** (binding · 1 CFD-literate non-project-member runs end-to-end M5→M8 in 30-45 min) | Final external-validation gate before M5-M8 is Done | **STATUS UNCHANGED, still binding**, and now reinforced by V130's interim validation milestone (§6 risk #5 mitigation). The N-sequence below carries this gate forward as an explicit prerequisite for N6 close. |
| **N1-N6** (this DEC) | AI auto-apply deprecation + workbench parity build-out + AI advisor stack | **NEW**, post-V130. Renamed from prior draft "M1-M6" to avoid token collision per Kogami P1 finding #1. |

**Operating principle**: M5-M8 trust-core gates and stranger-dogfood gate remain in force AND apply to N-sequence work where the N-work touches imported cases / trust-core surface / engineer-end-to-end claims. The N-sequence does not invalidate them.

## 4. Phased roadmap (N1-N6)

### N1 · AI auto-apply path deprecation (immediate · 2-3 sub-DECs)

- **N1.1 · DEC-V61-131**: Deprecate `regenerate_mesh` tool auto-apply AND backend hard-strip of envelope `?envelope=1` mutation. Tool returns advisory payload only (`{suggested_mesh_mode, reason}`); UI renders "AI suggests mesh_mode=X because Y" card; existing engineer-driven `[AI 处理]` button stays. Reframe ai-coach `proposal-applied` listener to no-op for AI mutation paths. Envelope endpoint loses its mutation behavior — returns advisory only (per Kogami P1 finding #2 close).
- **N1.2 · DEC-V61-132**: Backend write-permission contract. Two-layer enforcement (per Kogami P1 finding #3 close — grep alone is brittle for a load-bearing contract):
  1. **MUTATING_ROUTES registry module** (`ui/backend/services/ai_actions/MUTATING_ROUTES.py`) — single source of truth for the case-mutating endpoint set listed in §2 Principle B.
  2. **Behavioral test** (`tests/test_ai_advisor_contract.py`) — imports the AI tool dispatcher with a sentinel HTTP client recording every outbound call; asserts the call set's verb is GET-only (no PUT/POST/DELETE) AND that no path matches MUTATING_ROUTES. This is the load-bearing gate.
  3. **Grep lint** (fast pre-commit) — string-match for `requests.post`, `client.put`, `api.meshImported`, `api.setupBC` in `services/ai_actions/` + `routes/ai_*` as a fast warning layer; failures here are advisory-only — the behavioral test is the merge gate.
- **N1.3 (optional) · DEC-V61-133**: ROADMAP.md addendum (NOT rewrite — M-sequence preserved per §3.5). Append the N-sequence as a new section; keep the existing M-sequence text intact since M5.1 / M6.1 / M7 / M5-M8 commitments stay binding.

### N2 · Mesh control parity (4-6 sub-DECs)

Capability checklist target (see §2 Principle A · B-module):
- N2.1 sizing field UI (base / min / max / curvature / proximity)
- N2.2 region refinement (box / sphere / STL-driven)
- N2.3 prism layer controls (first-cell-height / growth-rate / num-layers / total-thickness)
- N2.4 checkMesh remediation hints rendered for human reading (not AI auto-fix)
- N2.5 mesh history panel (re-mesh attempts visible to engineer)
- N2.6 (optional) Cartesian / polyhedra mesh modes

### N3 · Physics models + Materials (5-7 sub-DECs)

Capability checklist target (see §2 Principle A · C+D-modules):
- N3.1 physics selection panel (incompressible / compressible · laminar / RANS / LES)
- N3.2 turbulence model picker (k-ε / k-ω / SST / SA)
- N3.3 energy equation toggle + radiation
- N3.4 multi-phase off / VOF / Mixture
- N3.5 fluid material library (air / water / steel — with viscosity laws, polynomial / piecewise / table)
- N3.6 solid material library
- N3.7 (optional) reactive flow / MRF

**N3 close gate**: per §6 risk #5, ONE CFD-literate non-project-member completes a representative case end-to-end through the workbench-only path before N4 starts.

### N4 · BC palette + Solver controls (4-6 sub-DECs)

Capability checklist target (see §2 Principle A · E+F-modules):
- N4.1 full BC palette (velocity-inlet, mass-flow-inlet, pressure-inlet, pressure-outlet, mass-flow-outlet, outflow, wall variants, symmetry, periodic, axis, interface)
- N4.2 solver pressure-velocity coupling selector (SIMPLE / SIMPLEC / PISO / PIMPLE / Coupled)
- N4.3 discretization scheme picker (upwind / central / QUICK / MUSCL) + URF panel
- N4.4 monitor probes (force / moment / pressure / line-integral / surface-integral)
- N4.5 residual target + residual plot live updates
- N4.6 (optional) parametric sweep harness

### N5 · Post-processing + Reports (3-5 sub-DECs)

Capability checklist target (see §2 Principle A · G-module):
- N5.1 contour / vector / streamline interactive overlays
- N5.2 iso-surface + slice + probe-line tools
- N5.3 volume-integral / surface-integral computations
- N5.4 report templates (parameter table + key-results table + comparison-against-benchmark)
- N5.5 (optional) animation export

### N6 · AI advisor stack (4-6 sub-DECs · starts after N2-N5; N6.1 may parallelize from N2)

- N6.1 knowledge-base RAG backend (OpenFOAM docs + Fluent/StarCCM user manual chapters + classic CFD textbook excerpts + internal failure-mode library) — can run in parallel with N2 since it's an independent backend service
- N6.2 「AI 审查」 button + structured review report frontend
- N6.3 review-report payload contract + backend route (consumes case-completeness + mesh-quality + annotations + KB; emits structured ✓/⚠️/✗ tree)
- N6.4 「AI 诊断」 button + failure-context aggregator + KB consult
- N6.5 contract test: AI advisor stack is read-only — N1.2 behavioral test (sentinel HTTP client) MUST cover every new advisor route added in N6
- N6.6 (optional) post-session learning loop — accepted advice patterns feed back into KB

**N6 close gate**: M5-M8 stranger-dogfood completion gate (per §3.5) — 1 CFD-literate non-project-member runs end-to-end through the **AI-advisor-augmented** workbench (M5 import → M6 mesh → M7 run → M8 report, with optional 「AI 审查」 / 「AI 诊断」 invocations) in target 30 min / cap 45 min. This satisfies both the legacy M5-M8 binding gate AND the new charter's external-validation requirement.

## 5. What this means for in-flight work

- **Current 21 unpushed commits (V127/V128/V129a chain)** — fully compatible with new charter. **Push to origin/main as scheduled** once base review completes (no charter conflict).
- **Running base-review (bfz9qiadh)** — keep running for the cadence-floor verified trailer; the diff is data-display code, charter has no objection.
- **Future Codex chain reports** — the `Phase E shell entry` framing is replaced by `N-prefix workbench parity` framing; chain reports for N1.1+ reference N1-N6 (this DEC's sequence). The legacy ROADMAP M1-M8 sequence and its trust-core / stranger-dogfood gates remain in force per §3.5.

## 6. Risk register

1. **Engineer dogfood gap during N2-N5** — until N2-N5 finish, the workbench is genuinely below Fluent parity. Mitigation: existing functionality is honestly labeled "phase 1 dogfood — STL → LDC / channel only" in the UI; N2-N5 expand surface incrementally with each DEC adding one feature column.
2. **Existing AI auto-apply UX habit** — engineers and dogfooders who used the workbench under Phase A may experience friction when the AI-Accept button no longer auto-runs. Mitigation: N1.1 keeps the `[AI 处理]` button visible at the same place; only the underlying intent changes ("apply suggestion" not "AI please go").
3. **AI advisor adoption pull** — if N6 ships and engineers don't use it, AI value is unproven. Mitigation: N6.1 RAG backend has independent value (engineers can browse CFD knowledge directly), so even partial adoption returns value.
4. **Kogami governance rule-change blast** — this DEC IS a governance rule change; Kogami review may flag scope ambiguity. Status (2026-05-06): Kogami APPROVE_WITH_COMMENTS · 6 findings closed inline · this risk realized at predicted level.
5. **Multi-month execution window with no external validation** (added per Kogami P2 finding #2 close) — the N2-N5 build-out is estimated 22-33 sub-DECs across 3-6 months, all internal. If completed without engineer feedback, the workbench may ship to no adopter. Mitigation, three-tier:
   - **Interim N3-close gate**: 1 CFD-literate non-project-member runs a representative case end-to-end through the workbench-only path before N4 starts. Failure surfaces gaps early; success de-risks the rest.
   - **Reuse legacy M5-M8 stranger-dogfood gate**: per §3.5, the binding stranger-dogfood completion gate from the prior ROADMAP M-sequence remains in force. N6-close cannot flip without that gate satisfied (engineer runs M5→M8 end-to-end + optionally invokes 「AI 审查」 / 「AI 诊断」). This is a hard prerequisite, not a calendar target.
   - **Reuse legacy M7 Path-A first-customer recruitment**: per §3.5, the M7 Path-A binding prerequisite (a stranger meeting the criteria in `.planning/strategic/path_a_first_customer_recruitment_2026-04-27.md` is recruited and named in the "Recruited" table with consent) remains in force. The N-sequence does not invalidate it; in fact §6.5 reinforces it by requiring external validation on a tighter cadence.

## 7. Acceptance criteria

- ✅ Kogami APPROVE_WITH_COMMENTS (2026-05-06 · `.planning/reviews/kogami/v61_130_strategic_pivot_2026-05-06/`)
- ✅ 6 findings closed inline (3 P1 + 2 P2 + 1 P3 — see status frontmatter line for the change list)
- ✅ Memory artifacts saved (pre-DEC at 2026-05-06):
  - `~/.claude/projects/-Users-Zhuanz/memory/feedback_cfd_harness_ai_advisor_pivot.md`
  - `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_harness_roadmap_v2.md`
  - MEMORY.md index updated
- Following Accepted: N1.1 sub-DEC opens (DEC-V61-131, `regenerate_mesh` tool deprecation + envelope mode hard-strip).
- Notion sync executed at Accepted (charter DECs sync the Accepted state, not Proposed).

Surface-scan: clean (charter DEC; no code grep needed for "is this already implemented" since the charter is itself the new spec).
