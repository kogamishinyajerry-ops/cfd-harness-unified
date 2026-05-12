# `.planning/` Directory Index

> **Orchestrator-level entry-point.** When you (or a fresh Claude Code
> session) open this repo, this file tells you which documents are
> live SSOT vs. historical archive. Everything below is grouped by
> what role it plays in the post-DEC-V61-198 three-actor workflow.

## Read first if you don't know the project

| File | Purpose |
|---|---|
| `decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md` | Strategic philosophy SSOT — read this BEFORE anything else. The new development model (industrial-case-driven, three-actor orchestration) lives here |
| `STATE.md` | Most recent project state snapshot |
| `PROJECT.md` | Project overview |
| `ROADMAP.md` | High-level milestone plan (M1-M6) |

## Active orchestration surfaces (this is what main session reads/writes most)

### Case orchestration

| File | Purpose |
|---|---|
| `case_index.md` | **Authoritative active/closed thread tracker.** What's running right now, what's queued, what's done |
| `case_proposal_queue.md` | **Codex-fed intake queue.** Lifecycle: proposed → dispatched → in-flight → closed. Coverage map drives next-case selection |
| `case_profiles/case_NNN_<name>.md` | Per-case industrial reference profiles (one per active or closed case-thread). Pointer to desktop sandbox + per-stage wall time + V-series sourced |

### Methodology + Codex 出题 contracts

| File | Purpose |
|---|---|
| `methodology/codex_case_design_protocol.md` | What main session asks Codex; what Codex must return (5 deliverables) |
| `methodology/component_bank.md` | Tier-3 component menu (5 numerics classes A-E) + Defect Catalog (D1-D10) |
| `methodology/public_cad_sources.md` | Tier-1 + Tier-2 catalog (NASA / ONERA / DLR / NREL etc.) — **Codex consults FIRST** before from-scratch generation |
| `methodology/case_kickoff_prompt_template.md` | Reusable sub-session briefing template (gets case-specific Codex content slotted in) |
| `methodology/rag_corpus_format.md` | M6 prerequisite: schema for what each case sediments into corpus-ready artifacts |
| `methodology/industrial_case_solver_findings.md` | **V-series.** Engineer-facing solver/mesh failure mode index. Indexed by numerics class for Pattern 6 inheritance |
| `methodology/solver_convergence_playbook.md` | Decision tree (S1-S12) — engineer's lookup when convergence stalls |
| `methodology/workbench_persona_findings.md` | F-series (persona/UI surface). B-extend arc closed; F-series remains live for individual additions but not primary substrate |

### Kickoff materials (per-case Codex round + sub-session paste-ready)

`methodology/kickoff/` holds the per-case 4-file set:

| Pattern | Purpose |
|---|---|
| `case_NNN_codex_request.md` | What main session sent to Codex |
| `case_NNN_codex_response.md` | Codex's 5 deliverables (full output) |
| `case_NNN_validation.md` | Main session 6-check validation report |
| `case_NNN_<name>.md` | **Paste-ready** sub-session kickoff (template + Codex brief slot) |

Currently:
- `case_003_*` (4 files) — CRM-HLS boundary layer, dispatched 2026-05-07, **deferred awaiting user resources**
- `case_004_*` (4 files) — NREL Phase VI MRF rotating machinery, dispatched 2026-05-07, **deferred awaiting user resources**
- `case_005_*` (4 files) — RAE M2129 S-duct compressible-RANS, dispatched 2026-05-08, **deferred awaiting user resources** · first case to exercise LANDED A3 advisor
- `case_006_*` (4 files) — ONERA M6 transonic wing, compressible-shock-density-based, dispatched 2026-05-08, **deferred awaiting user resources** · CRS gpt-5.4 fallback used (86gs 503); first density-based case
- `case_007_*` (4 files) — KCS ship multiphase VOF, dispatched 2026-05-08, **deferred** · round 2 of 2 (round 1 hallucinated read-only); first multiphase
- `case_008_*` (4 files) — GLC305 IRT Lagrangian icing, dispatched 2026-05-08, **deferred** · first Lagrangian; clarification preamble added to prompt template
- `case_009_*` (4 files) — Sandia Flame D reacting-low-Mach, dispatched 2026-05-08, **deferred** · first reacting case; longest sub-session effort 12-16h; DRM-19 chemistry
- `case_010_*` (4 files) — DrivAer fastback LES, dispatched 2026-05-08, **deferred** · final case; first transient LES; coverage matrix complete

**10-case roster complete as of 2026-05-08**. All 10 numerics-class
roots covered (compressible-buoyant-RANS, +CHT, incompressible-RANS,
+MRF, compressible-RANS, compressible-shock-density-based,
multiphase-VOF, RANS-Lagrangian, reacting-low-Mach, incompressible-LES).
Workhorse OpenFOAM solver matrix complete. 8 deferred kickoffs in
queue (cases 003-010); awaiting compute resources to dispatch
sub-sessions.

## Active work products

| Path | Purpose |
|---|---|
| `decisions/` | All DECs by date — Notion-mirrored. Most recent = `2026-05-07_v61_198_*` (strategic pivot) |
| `retrospectives/` | Post-arc retros. Most recent = arc retros for V61-088..V61-116 |
| `sessions/` | Long-form session summaries (rare; auto-memory replaces most) |
| `gates/` | External gate review docs (Q1/Q2/Q5 verification) |
| `governance/` | Governance protocols (kogami_invoke etc.) |

## Reference / strategic documents

| Path | Purpose |
|---|---|
| `strategic/` | Strategic memos (Pivot Charter Addendum 3, Blueprint v3, etc.) — historical record of strategic shifts |
| `roadmaps/` | Roadmap drafts (post_w5, workbench_rollout) |
| `specs/` | Technical specs (executor abstraction, etc.) |
| `protocols/` | Cross-session protocols |
| `north_star_drift_log/` | Drift detection log |

## Historical / pre-pivot artifacts (kept for audit, not actively consumed)

| Path | Purpose |
|---|---|
| `dogfood/` | B-arc + B-extend dogfood reports (V61-162..V61-197). Arc closed by DEC-V61-198. CI smoke tests in `ui/backend/tests/test_persona_facing_smoke_e2e.py` are the live regression; these reports are historical |
| `handoffs/` | Pre-orchestrator-model session handoffs (April 2026). Now superseded by the kickoff/template flow |
| `reviews/` | Pre-pivot Codex review prompts/findings (April 2026). Superseded by the codex_case_design_protocol |
| `audit_evidence/` | Pre-pivot audit artifacts |
| `ops/` | Pre-pivot ops plans |
| `notes/` | Loose notes (limited use) |
| `research/` | Pre-pivot research docs |
| `adwm/` | Pre-pivot ADWM activation plan |
| `external_gate_queue.md` | Pre-pivot gate queue (limited use) |
| `phase5_audit_package_builder_kickoff.md` | Phase 5 historical doc |
| `PHASE0_CONTEXT_PACK.md` | Phase 0 historical context |
| `STATE_BACKFILL_2026-05-03.md` | One-time backfill |
| `workbench_rollout_summary.md` | Workbench rollout summary |

## Three-actor workflow ↔ which files

```
┌──────────────────────────────────────────────────────────────────┐
│  MAIN SESSION (this Claude Code)                                  │
│  reads:  case_index, case_proposal_queue, V-series, playbook     │
│  writes: case_index, case_proposal_queue (lifecycle moves),       │
│          methodology/kickoff/case_NNN_codex_request.md,           │
│          methodology/kickoff/case_NNN_validation.md,              │
│          methodology/kickoff/case_NNN_<name>.md (sub-session ready)│
└──────────────────────────────────────────────────────────────────┘
              │ (invokes via codex-relay-with gpt-5.5)
              ▼
┌──────────────────────────────────────────────────────────────────┐
│  CODEX (gpt-5.5 / case 出题者)                                    │
│  reads:  codex_case_design_protocol, component_bank,              │
│          public_cad_sources, case_002a/b examples, V-series       │
│  writes: case_NNN_codex_response.md (5 deliverables: brief +      │
│          CadQuery script + STEP file path + parts manifest +      │
│          defect manifest)                                         │
└──────────────────────────────────────────────────────────────────┘
              │ (deliverable handoff via repo files)
              ▼
┌──────────────────────────────────────────────────────────────────┐
│  SUB-SESSION (per-case Claude Code, paste kickoff in fresh term)  │
│  reads:  case_NNN_<name>.md (its kickoff), DEC-V61-198, V-series, │
│          playbook, codex_case_design_protocol                     │
│  writes: case_profiles/case_NNN_<name>.md (reference profile),    │
│          industrial_case_solver_findings.md (V-series rows),      │
│          solver_convergence_playbook.md (S-rows if new pattern),  │
│          case_index.md (status updates),                          │
│          case_proposal_queue.md (lifecycle: dispatched →           │
│          in-flight → closed),                                      │
│          desktop sandbox at ~/Desktop/case_NNN_<name>/             │
└──────────────────────────────────────────────────────────────────┘
```

## When to update this INDEX

- A new top-level `.planning/` document appears that's actively
  consumed by main session, Codex, or sub-session
- A document moves from active to archive (or vice versa)
- The three-actor workflow gains a new step
- A naming convention changes

DO NOT update for:
- Each new DEC file (those go in `decisions/`)
- Each new V-series row (those go in V-series file directly)
- Each new case kickoff (the pattern `kickoff/case_NNN_*` already
  documented; only update if pattern changes)

## Cross-references

- Strategic SSOT: `decisions/2026-05-07_v61_198_apu_bay_strategic_pivot.md`
- Project memory (auto-loaded): `~/.claude/projects/-Users-Zhuanz/memory/project_cfd_apu_bay_strategic_pivot.md`
- Notion mirror: https://www.notion.so/359c68942bed81e0ba4eef75df08d778
