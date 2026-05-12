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
| `methodology/plan_md_passes_field.md` | DEC-V61-199 Rule 2 · PLAN.md task tables from N2+ carry a `passes` column; `status: COMPLETED` alone insufficient. Sets E2E gate convention |
| `methodology/skill_description_audit_protocol.md` | DEC-V61-199 Rule 3 · opt-in transcript-driven loop for rewriting skill `description:` fields. Same posture as Kogami (no auto-trigger) |
| `methodology/advisor_candidates_a4_a8.md` | Harvest-003 prep · A4-A8 advisor candidates (face-orientation / extra-body / curved-tess / non-watertight). Defect-class signatures + pre-drafted specs + cross-topology evidence ledger. Promotes `drafted` → `ready-to-land` when ≥2 cases sediment |

### Kickoff materials (per-case Codex round + sub-session paste-ready)

`methodology/kickoff/` holds the per-case 4-file set:

| Pattern | Purpose |
|---|---|
| `case_NNN_codex_request.md` | What main session sent to Codex |
| `case_NNN_codex_response.md` | Codex's 5 deliverables (full output) |
| `case_NNN_validation.md` | Main session 6-check validation report |
| `case_NNN_<name>.md` | **Paste-ready** sub-session kickoff (template + Codex brief slot) |

Currently (status reconciled to `case_index.md` SSOT 2026-05-08
harvest cycle 002):

- `case_003_*` (4 files) — CRM-HLS boundary layer, dispatched 2026-05-07, **active · v1 paused at advisor-validation** (V20 unit-scale block; CFD pipeline pending). A2 + thin_wall first cross-topology PASSes (per V25 = algorithm-runs-cleanly, not gap-defect-detected)
- `case_004_*` (4 files) — NREL Phase VI MRF rotating machinery, dispatched 2026-05-07, **active · v1 advisor-validation done; MRF infra ready** (CFD pending v2). V22 + V23 + V24 sourced
- `case_005_*` (4 files) — RAE M2129 S-duct compressible-RANS, dispatched 2026-05-08, **active · v1 baseline + v2 V21 disambiguation + v2 CFD push** · first case to exercise LANDED A3 advisor; surfaced V16-V25 chain including V25 (open · A2 placeholder semantic)
- `case_006_*` (4 files) — ONERA M6 transonic wing, compressible-shock-density-based, dispatched 2026-05-08, **deferred awaiting compute** · CRS gpt-5.4 fallback used (86gs 503); first density-based case
- `case_007_*` (4 files) — KCS ship multiphase VOF, dispatched 2026-05-08, **deferred awaiting compute** · round 2 of 2 (round 1 hallucinated read-only); first multiphase
- `case_008_*` (4 files) — GLC305 IRT Lagrangian icing, dispatched 2026-05-08, **deferred awaiting compute** · first Lagrangian; clarification preamble added to prompt template
- `case_009_*` (4 files) — Sandia Flame D reacting-low-Mach, dispatched 2026-05-08, **deferred awaiting compute** · first reacting case; longest sub-session effort 12-16h; DRM-19 chemistry
- `case_010_*` (4 files) — DrivAer fastback LES, dispatched 2026-05-08, **deferred awaiting compute** · final case in original roster; first transient LES; numerics-root coverage matrix complete
- `case_011_*` (4 files) — Plate-fin compact HX, Phase 1 #1, multi-stream CHT NEW root, 86gs xhigh R0 + CRS R1 emit fallback
- `case_012_*` (4 files) — HVAC supply diffuser, Phase 1 #2 close, buoyantSimpleFoam direct 002a inheritance, **D7 first injection · advisor-gap surfacer**
- `case_013_*` (4 files) — Centrifugal pump cavitating, Phase 2 #1, simpleFoam+MRF v1 / cavitatingFoam v2, ERCOFTAC-class water-treatment pump, 86gs network-disconnect → CRS fallback emit
- `case_014_*` (4 files) — NASA CC3 compressor stage, Phase 2 #2 close, rhoSimpleFoam+MRF+cyclicAMI gold-standard turbomachinery
- `case_015_*` (4 files) — Vattenfall T-junction LES+CHT, Phase 3 #1, first compound numerics root (LES+CHT) for project
- `case_016_*` (4 files) — M219 cavity DES+acoustic, Phase 3 #2 close, second compound root (compressible-DES), **D6+D9 first injections**
- `case_017_*` (4 files) — Pin-fin electronic heatsink, Phase 4 #1, microscale 4-region CHT with TIM solid-solid conjugate
- `case_018_*` (4 files) — Stairmand cyclone separator, Phase 4 #2, first 3D swirl + first RSM for project
- `case_019_*` (4 files) — Kenics static mixer, Phase 4 #3, scalar transport + A3 advisor stress-test
- `case_020_*` (4 files) — Porous media filter Darcy-Forchheimer, **Phase 4 #4 FINAL CASE in 11-case batch**, **D10 first injection closes defect-catalog gap (D3+D4 only remaining uncovered)**

**Original 10-case roster complete as of 2026-05-08**. All 10 numerics-class
roots covered (compressible-buoyant-RANS, +CHT, incompressible-RANS,
+MRF, compressible-RANS, compressible-shock-density-based,
multiphase-VOF, RANS-Lagrangian, reacting-low-Mach, incompressible-LES).
Workhorse OpenFOAM solver matrix complete. **3 of 8 dispatched cases
have run v1 sediment** (003 paused on V20, 004 advisor-validation
done, 005 v1+v2). 5 cases (006-010) deferred awaiting compute.

**Industrial-extension batch (case_011-020) FULLY DISPATCHED as of 2026-05-08
evening** — all 11 cases through Codex case-design + main-session validation
+ paste-ready kickoff. None yet sub-session-sedimented (all `dispatched · DEFERRED`).
Codex backend mix: case_011 (86gs+CRS fallback) / case_013 (86gs+CRS fallback) /
all others CRS gpt-5.4 high single-round. Total Codex tokens consumed:
~1.67M across 11 cases.

**Defect catalog coverage post-batch**: D1 (11×) · D2 (1×) · D3 (0× UNCOVERED) ·
D4 (0× UNCOVERED) · D5 (2×) · D6 (2×) · D7 (2×) · D8 (3× +D8 [VALIDATED] arc) ·
D9 (3×) · D10 (1×). D3 + D4 carry to next batch.

**Advisor-gap V-findings to be consolidated by harvest cycle 003**:
A4-A8 candidates surfaced — face-orientation (D7 across 012/013) /
extra-body-in-fluid (D6 across 016/018) / curved-tessellation (D9 across
016/017/020) / non-watertight-shell (D10 from 020). A2-v2 sub-DEC pending
12 D1 cross-topology `[QUESTIONABLE]` PASSes (003-014/017 etc).

**Compound numerics roots validated**: case_015 (LES+CHT) + case_016
(compressible-DES). Pattern 6 numerics-class inheritance methodology
demonstrated across 21 cases.

**Trigger after sediment**: harvest cycle 003 full-mode + `case_021_030_*.md`
strategic doc for next batch.

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
| `strategic/case_011_020_industrial_extension_roadmap_2026-05-08.md` | **Strategic SSOT for case_011-020 batch** (post-original-roster industrial extension) |
| `strategic/case_013_020_dispatch_plan_2026-05-08.md` | Dispatch order, dependencies, blockers, per-case readiness for case_013-020. Companion to roadmap above; case_011 dispatched, case_012 codex_request ready |
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
