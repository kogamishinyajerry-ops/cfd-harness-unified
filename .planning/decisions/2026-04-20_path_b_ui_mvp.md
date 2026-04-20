---
decision_id: DEC-V61-002
timestamp: 2026-04-20T13:00 local
scope: cfd-harness-unified product-thesis election + UI MVP multi-phase roadmap
autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: false
codex_diff_hash: null
codex_tool_report_path: null
reversibility: fully-reversible-by-branch-revert
  (Phase 0 lands `docs/**`, `ui/**`, `.planning/**` in a single PR; revert
   is one `git revert -m 1 <merge-sha>`. No src/ · tests/ · knowledge/
   gold_standards/ touch; no whitelist membership change; no DB-schema
   migration.)
notion_sync_status: PENDING (will mirror to Decisions DB after Phase 0 PR merges)
external_gate_self_estimated_pass_rate: 92%
  (Kogami's takeover prompt explicitly granted "全权交给你决策开发至 MVP 完成";
   Path B is the narrower and more defensible of the two paths surfaced in
   the prior turn; only residual external-Gate risk is disagreement with
   specific phase ordering or screen priorities, which is reversible by
   re-slicing Phase 1+ without touching Phase 0 artifacts.)
supersedes: null
superseded_by: null
---

# DEC-V61-002: Elect Path B (Agentic V&V-First Workbench) + declare 6-phase UI MVP roadmap

## Decision summary

Two product theses were surfaced in the preceding turn — **Path A**
(compete as a general-purpose CFD workbench against ANSYS / STAR-CCM+ /
SimScale) and **Path B** (Agentic V&V-first workbench for regulated-
industry / audit-trail-required CFD). Kogami elected Path B and granted
the Claude APP Sole Primary Driver full decision authority to execute
through MVP completion, with Notion + GitHub sync required at each phase
landing.

Under Path B, the product thesis is:

> **A CFD case-execution workbench where every run comes with a
> cryptographically-traceable audit package mapping measurement ↔ gold-
> standard ↔ tolerance ↔ literature citation ↔ commit SHA ↔ decision
> trail. The AI agent drafts case setups and flags physics-contract
> violations; the human reviews and approves; the system auto-packages
> the V&V evidence for external review (FDA V&V40, DO-178 / DO-254,
> NQA-1).**

This decision also declares the 6-phase MVP roadmap that supersedes the
abandoned Phase 9 planning queue in `.planning/STATE.md`:

| Phase | Delivery | Branch naming | Gate criteria (brief) |
|---|---|---|---|
| Phase 0 | Product thesis doc + UI design doc + FastAPI backend scaffold + React frontend scaffold + Screen 4 (Validation Report) concept-of-proof wired to DHC / cylinder_wake / turbulent_flat_plate real data | `feat/ui-mvp-phase-0` | Doc reviewable · Scaffold `npm run dev` + `uvicorn` both boot · Screen 4 renders 3 cases from yaml |
| Phase 1 | Screen 2 Case Editor (Monaco + schema-driven YAML lint against `knowledge/schemas/*.yaml`) | `feat/ui-mvp-phase-1-case-editor` | Lint flags 3 synthetic bad-yaml tests · Save round-trips through backend · Dirty-state detection |
| Phase 2 | Screen 5 Decisions Queue (Kanban view of `.planning/external_gate_queue.md` + Notion Decisions DB bidirectional sync) | `feat/ui-mvp-phase-2-decisions` | Pull from Notion DB on page load · Push new decisions to both local `.planning/decisions/` and Notion · Status filter working |
| Phase 3 | Screen 3 Run Monitor (VTK.js mesh/field viewport + WebSocket residual stream + checkpoint controls) | `feat/ui-mvp-phase-3-run-monitor` | One end-to-end MockExecutor run viewable · Residual plot updates live · Checkpoint/resume button emits API call |
| Phase 4 | Screen 1 Project Dashboard (10-case physics-contract matrix fed by `auto_verifier` + decisions-this-week timeline + blocked-on-gate count) | `feat/ui-mvp-phase-4-dashboard` | Matrix renders from real data · Per-cell drill-down to case detail · Gate count matches external_gate_queue.md |
| Phase 5 | Screen 6 Audit Package Builder (one-click export: zip + signed PDF bundling case + gold + run + measurement + audit_concern + decision trail + commit SHA + HMAC signature) | `feat/ui-mvp-phase-5-audit-package` | Export produces byte-reproducible zip from fixed inputs · PDF renders without external CDN · HMAC verifiable from documented procedure · FDA V&V40 reviewer checklist mapping in audit-package README |

Each phase: one branch → one PR → one `DEC-V61-00N` decision record →
one Notion Decisions DB mirror. Merge method: **regular merge commit**
(留痕 > 聪明; no squash, no rebase).

## Why

The commercial CFD workbench market is dominated by ANSYS Workbench,
Siemens STAR-CCM+, SimScale, and COMSOL. Competing head-on requires
multi-year, multi-team, multi-10-million-dollar investment and offers
no defensible differentiator — those vendors' CAD/mesh/solver/post
stacks have 20+ years of incumbency.

The market Path B targets (AI-governed CFD with cryptographic audit
packages, for regulated industries: aerospace / medical device / nuclear
/ automotive-FSI) currently has:
- Academic prototypes (NVIDIA Modulus, SimNet, DeepXDE variants) but
  none packaged as commercial workbenches
- Internal tools inside regulated-CFD consultancies (Ansys' V&V40
  compliance playbook is a whitepaper, not a product)
- Zero products that bundle "AI-drafted case + physics-contract gate +
  decision trail + audit package" as a first-class workflow

The `cfd-harness-unified` project already has (a) whitelist-governed
V&V benchmarks with literature-citation-backed `gold_standards/*.yaml`,
(b) autonomous-decision discipline (ADWM v5.2 → v6.1) with `audit_
concern` emission at PASS-with-hazard runs, (c) producer/consumer
wiring for runtime flag detection (Spalding fallback, canonical-band
shortcut — see DEC-ADWM-005, DEC-ADWM-006). These are the three primary
ingredients of the Path B product. Adding a UI that surfaces them to
non-governance-literate reviewers is the single largest value-unlock.

## Alternatives considered

- **Path A. Pursue full-workbench parity.** Rejected: 2-3 year timeline,
  $5-10M eng spend minimum, no defensible moat against ANSYS. Would
  commoditize the existing V&V-governance differentiator by burying it
  under a bloated workbench shell.
- **Path C. Ship only the `auto_verifier` CLI + library, no UI.**
  Considered: matches the repo's current CLI-native posture and lowest
  engineering cost. Rejected as MVP because regulated-industry buyers
  procure workbenches, not libraries — the UI is the commercialization
  surface, not optional polish.
- **Path D. Build as a VS Code extension instead of standalone web
  app.** Considered: zero UI-framework learning curve for engineer
  audience, near-zero distribution cost. **Deferred to Phase 5+ as a
  secondary distribution channel** — the standalone web app remains
  canonical because audit-package buyers are frequently not the same
  person as the CFD engineer (compliance officer, external reviewer),
  and VS Code is a poor surface for that secondary audience.
- **Path B (elected).** Agentic V&V-first workbench, standalone web
  app, audit-package export as Phase 5 commercial gate.

## Impact

- **Affected processes going forward**: every new CFD case added to
  `knowledge/whitelist.yaml` now has a UI-side story (Phase 1 Case
  Editor will lint it, Phase 4 Dashboard will show its status);
  every ADWM decision now has a Phase 2 Decisions-Queue card; every
  Run produces a Phase 5 audit package on demand.
- **New directory**: `ui/` (NOT in the three 禁区). Contains
  `ui/backend/` (FastAPI wrapping existing Python) and `ui/frontend/`
  (Vite + React + TS + Tailwind + shadcn/ui).
- **pyproject.toml**: adds optional dependency group `[project.
  optional-dependencies.ui]` with `fastapi`, `uvicorn[standard]`,
  `pydantic>=2`. Existing `[dev]` group is untouched.
- **Phase 9 activation review** (per STATE.md `next_phase`): folded
  into this roadmap. Phase 9 as a standalone planning phase is
  retired; its concerns (gate Q-1 / Q-2 resolution) are out of
  scope for the UI MVP and remain blocked behind external Gate per
  `external_gate_queue.md`.
- **autonomous_governance counter (v6.1-era)**: 2 (DEC-V61-001 + this
  entry). Hard-floor-4 threshold ≥ 10 still has 8 slots of runway.

## Scope (禁区 perimeter compliance)

This decision and its Phase 0 concrete actions touch:
- `.planning/decisions/2026-04-20_path_b_ui_mvp.md` ✅ (non-禁区 · this file)
- `.planning/STATE.md` ✅ (non-禁区 · planning state reconciliation)
- `.planning/external_gate_queue.md` ✅ (non-禁区 · add Q-4 placeholder)
- `docs/product_thesis.md` ✅ (non-禁区 · NEW)
- `docs/ui_design.md` ✅ (non-禁区 · NEW)
- `docs/ui_roadmap.md` ✅ (non-禁区 · NEW)
- `ui/**` ✅ (non-禁区 · NEW top-level directory)
- `pyproject.toml` ⚠️ (NOT in the 3 禁区; adds optional [ui] dep group
  only — no change to [dev], no change to existing install invocation)

Explicitly **not** touched in Phase 0:
- `src/**` — no change (FastAPI backend imports from src/ but does not
  modify it)
- `tests/**` — no change (UI-scoped tests live under `ui/frontend/src/
  **/*.test.tsx` and `ui/backend/tests/`, outside the repo's existing
  tests/ tree)
- `knowledge/gold_standards/**` — no change
- `whitelist.yaml` — no change (10-case membership preserved exactly)

Hard-floor compliance matrix:
| Hard floor | Status for Phase 0 |
|---|---|
| #1 GS tolerance edit | NOT TOUCHED |
| #2 项目北极星 edit | NOT TOUCHED (10-case whitelist, gold-standard physics contracts all preserved; the UI is a consumer of the北极星, not a mutator) |
| #3 Notion DB destruction | NOT TOUCHED (new page creation only, in existing Decisions DB) |
| #4 主导-工具链路失调 | NOT ARMED (zero Codex invocations in Phase 0; all code is in ui/ which is Claude APP direct-write territory) |

## Reversibility

**Phase 0 revert**: `git revert -m 1 <phase-0-merge-sha>` removes all
Phase 0 artifacts (docs, ui/, decision file, STATE.md + external_gate_
queue.md updates) in a single commit. No orphan state.

**Full roadmap abandonment**: if Path B proves wrong at any phase gate,
revert all phase-N merge commits in reverse order; `ui/` directory
disappears; `src/`, `tests/`, `knowledge/` are never touched. The
worst case is wasted engineering time, not corrupted product state.

**Notion revert**: DEC-V61-002 mirror page can be archived in Notion
(not deleted — hard floor #3) without affecting DEC-ADWM-001..006 or
DEC-V61-001, which remain independently valid.

## Phase 0 specific deliverable list (what this session produces)

1. `.planning/decisions/2026-04-20_path_b_ui_mvp.md` — THIS FILE
2. `docs/product_thesis.md` — product positioning, competitive
   landscape, non-goals, commercial model hypothesis
3. `docs/ui_design.md` — 6-screen information architecture, layout
   sketches, design language, tech-stack rationale
4. `docs/ui_roadmap.md` — phase-by-phase gate criteria, risk
   register, time estimates
5. `ui/backend/` — FastAPI app, routes for `/api/health`, `/api/
   cases`, `/api/validation-report/{case_id}`
6. `ui/frontend/` — Vite + React + TS + Tailwind skeleton, Screen 4
   `<ValidationReport>` component wired to 3 real cases
7. `ui/README.md` — `npm run dev` + `uvicorn` runbook
8. Updates to `.planning/STATE.md` and `.planning/external_gate_
   queue.md` recording the new roadmap
9. `pyproject.toml` optional `[ui]` dep group
10. One PR (#2), merged via regular merge commit
11. DEC-V61-002 mirrored to Notion Decisions DB with PR #2 URL as
    Canonical Follow-up

## Self-verification (what Phase 0 will NOT do)

- Will NOT run the FastAPI server against a live OpenFOAM container
  — Phase 0 wires only `MockExecutor`-produced `slice_metrics.yaml`
  fixtures. Real-solver wiring is Phase 3 scope.
- Will NOT integrate VTK.js or 3D viewport — Phase 3 scope.
- Will NOT add authentication / authorization to the FastAPI backend
  — Phase 4 scope (the backend binds to 127.0.0.1 only in Phase 0,
  no network exposure).
- Will NOT touch any of the 10 existing benchmark cases' numeric
  data — hard floor #1.
- Will NOT modify existing Python modules in `src/**` — the FastAPI
  app imports and calls them read-only. If a wrapper needs to grow
  into `src/**`, that is a separate Codex-tool dispatch and a
  separate DEC-V61-00N entry.

## Notion mirror TODO

When Phase 0 PR #2 lands on origin/main: write to Decisions DB page
(collection `54bb6521-2e59-4af5-93bd-17d55c7c34e1`) with:
- Scope = Project
- Status = Accepted
- Canonical Follow-up = PR #2 GitHub URL
- Page body includes: phase roadmap table, 禁区 compliance matrix,
  Phase 0 deliverable checklist, reversibility notes
- Update frontmatter `notion_sync_status` on this local file with
  the Notion page URL once written.
