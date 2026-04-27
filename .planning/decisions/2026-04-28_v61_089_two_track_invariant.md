---
decision_id: DEC-V61-089
title: Two-track invariant — gold-case-line ≠ workbench-line · parallelizable · share-downstream-only
status: Accepted (2026-04-28 · docs-only CLASS-1 · no Kogami trigger · no Codex trigger)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-28
authored_under: cross-session alignment anchor (post S-002 user concern about Notion drift after M5.0/M6.0 framing confusion in status report)
parent_decisions:
  - Pivot Charter 2026-04-26 + Addendum 1 (user-as-first-customer pivot)
  - DEC-V61-087 (v6.2 three-layer governance · NOT modified)
  - DEC-V61-088 (pre-implementation surface scan · NOT modified)
  - RETRO-V61-001 (risk-tier Codex triggers · NOT modified)
parent_artifacts:
  - .planning/strategic/m5_kickoff/spec_v2_2026-04-27.md (M5.0 routine + M5.1 PASS_WITH_DISCLAIMER cap)
  - .planning/strategic/m6_kickoff/spec_v2_2026-04-27.md (M6.0 gmsh + M7 sHM-stub-fill-in framing)
  - .planning/strategic/path_a_first_customer_recruitment_2026-04-27.md (M7 phase-Done gate)
  - knowledge/whitelist.yaml (Track A entry surface · 10 gold cases)
  - src/foam_agent_adapter.py (shared downstream · executor)
notion_sync_status: synced 2026-04-28 (https://www.notion.so/34fc68942bed81828556fb1839137168)
autonomous_governance: false  # docs-only architectural anchor; does NOT modify any rule, executor, or governance contract
codex_tool_report_path: null  # CLASS-1 docs-only per CLAUDE.md — Codex skipped
kogami_review: skipped (no §4 trigger fires — not phase-close, not retro, not high-risk PR, not counter ≥20, not autonomous_governance rule-change)
---

# DEC-V61-089 · Two-track invariant

## Why this exists

Session 2026-04-27/28 surfaced a framing slip: a status summary told the
user that "M6.1 + M7 add the ability to run OpenFOAM," when in fact
OpenFOAM has been running on 10 gold cases for months. The user
correctly pushed back. The misframing was contained to one chat reply
(no code, no commit, no decision was made on that wrong basis), but the
risk it exposes is real — across-session re-onboarding could flatten
the two distinct development tracks into "the workbench is the
project," obscuring that the gold-case line is the project's actual
load-bearing capability.

This DEC anchors the architectural distinction in the decisions
directory so future sessions / agents / Notion readers don't have to
re-derive it from spec v2 footnotes.

## The invariant

The repository contains two independent development tracks that share
**only downstream infrastructure**. They never compete for the same
upstream code path.

### Track A — Gold-case line (mature · ongoing)

- **Entry**: developer authors `knowledge/whitelist.yaml` entry +
  `knowledge/gold_standards/<case>.yaml` (literature reference data) +
  `_generate_*` method in `src/foam_agent_adapter.py`
- **Mesh**: hand-written `blockMeshDict` per case
- **BC + physics**: hand-tuned to match a specific literature reference
  (Ghia 1982, Spalding 1961 wall function, Williamson 1996, etc.)
- **Verdict ceiling**: `PASS` reachable — there is ground truth to
  compare against
- **Currently shipping**: lid_driven_cavity, turbulent_flat_plate,
  backward_facing_step, circular_cylinder_wake,
  rayleigh_benard_convection, airfoil_flow, impinging_jet,
  fully_developed_turbulent_pipe_flow, differentially_heated_cavity,
  natural_convection_cavity (10 total)
- **Recent work on this line**: DEC-V61-053 4-round arc on
  turbulent_flat_plate (URF=0.3, 4:1 wall grading, wall-cell skip +
  Spalding fallback in Cf extractor), Phase 5/6 audit-package builder,
  batch matrix, comparison overlay

### Track B — Workbench line (new · building)

- **Entry**: end user uploads STL via `POST /api/import/stl` →
  `/workbench/import` page
- **Mesh**: gmsh + gmshToFoam (M6.0 ·
  `ui/backend/services/meshing_gmsh/`) → `constant/polyMesh/`
- **BC + physics**: editor YAML form (M2 closed-loop · `EditCasePage`)
  + LDC defaults injected at scaffold time
- **Verdict ceiling**: `PASS_WITH_DISCLAIMER` (M5.1 trust-core hard-cap
  — no literature ground truth, so verdict cannot claim literature
  validation)
- **Status**: M5.0 (STL import) + M6.0 (mesh) shipped 2026-04-27/28
  via the routine path; M6.1 + M7 + M5.1 + M8 remaining
- **Geometry-type tag**: `GeometryType.CUSTOM` + `source_origin:
  imported_user` on the editor YAML

### Shared downstream (both tracks consume)

- `FoamAgentExecutor.execute()` solver invocation (simpleFoam /
  pimpleFoam / icoFoam / buoyantFoam / buoyantSimpleFoam) — Track A
  hits geometry-specific dispatch arms; Track B hits CUSTOM arm (M7
  work)
- GCI convergence analysis
- Validation report rendering
- Audit package builder (Phase 5/6)
- Run history / run detail / run comparison overlay
- Governance: Codex per-risky-PR baseline, Kogami strategic gates,
  retro cadence, Notion sync, codex-cadence pre-push hook
- Three-state contract markers (PASS / PARTIAL / FAIL ·
  PASS_WITH_DISCLAIMER for Track B)

## Parallelization rules

1. **Tracks advance independently** in the same session OR different
   sessions — they do not share upstream code paths, so concurrent
   commits in their respective directories do not conflict.

2. **Shared-downstream changes touch both tracks**. Modifications to
   `FoamAgentExecutor` (e.g., M6.1's blockMesh-skip flag), GCI, audit
   package, governance scripts, etc. are still subject to the standard
   Codex per-risky-PR baseline — and benefit both tracks atomically.

3. **Track A is NOT replaced by Track B**. New gold cases continue to
   enter via Track A. A user importing their own STL through Track B
   never produces a new gold case — they have no literature reference,
   so the verdict is capped at PASS_WITH_DISCLAIMER. The two surfaces
   are answering different questions:
   - Track A: "does this CFD harness reproduce known physics on a
     literature benchmark?"
   - Track B: "can a non-developer user feed their own geometry through
     the harness and get an honest verdict?"

4. **Track B never invents ground truth**. The M5.1
   PASS_WITH_DISCLAIMER cap is the load-bearing invariant. Lifting it
   would require an explicit superseding DEC that defines what
   "ground truth" means for user geometry — that is out of scope until
   M8 dogfood data exists.

## Session-topology guidance

- A single session can drive either track or both. There is no
  architectural reason to split chats.
- Multi-session split is appropriate only when the **user's attention**
  needs to split (e.g., Track A debugging is interactive while Track B
  is mid-Codex-review and waiting). Architecture itself imposes no
  constraint.
- Cross-track context cost is low: a single CLAUDE.md + recent commit
  log + relevant spec v2 read brings either track up to current state.
- Long arc compactions can compress one track's history harder than
  the other's without information loss, since the tracks don't share
  upstream files.

## What this DEC does NOT change

- No Kogami contract change (V61-087 untouched)
- No retro cadence change (V61-001 untouched)
- No counter rule change (V61-087 §5 truth table untouched)
- No executor code change
- No new governance gate
- This is a **docs anchor only**, designed to prevent across-session
  re-derivation of an invariant that already exists implicitly in the
  spec v2 / Pivot Charter / M5.1 cap

## Sync + verification

- Sync to Notion immediately after this DEC lands (project rule: every
  DEC syncs · CLAUDE.md "Notion 深度同步规则")
- Spec v2 docs for M5 and M6 are already synced and are consistent
  with this invariant — this DEC simply makes the cross-track summary
  explicit so future readers don't have to reconstruct it from
  phase-specific footnotes
- Verification of correctness: ten gold cases continue to run via
  Track A entry; M5.0 + M6.0 commits already shipped via Track B
  entry; both used the shared `FoamAgentExecutor` (Track A) or will
  use it via the M6.1 patch (Track B). The split is empirically
  observable in the current commit graph.
