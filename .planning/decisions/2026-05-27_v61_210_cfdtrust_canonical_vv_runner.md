---
decision_id: DEC-V61-210
title: cfdtrust is the canonical V&V audit runner — P1 flat-plate V&V-loop deliverable complete; adapter dual-track reconciliation queued separately
status: Accepted
parent_dec: DEC-V61-207 (Blueprint v4 P1) · DEC-V61-208 (Chief Engineer / L2) · DEC-V61-209 (flat-plate V&V de-fake)
phase: Blueprint v4 · P1 · cycle-4 (scope decision)
notion_sync_status: synced 2026-05-29 (https://www.notion.so/36fc68942bed8122b11ed741f104660c)
autonomous_governance: true
confidence: high
date: 2026-05-27
ratified_by: sponsor (chose option A — declare cfdtrust canonical, queue adapter reconciliation as a separate DEC)
---

# DEC-V61-210 · cfdtrust canonical V&V runner — P1 V&V-loop deliverable complete

## Context

DEC-V61-209 closed the flat-plate V&V loop with a real, independently-reviewed,
empirically-validated PASS — gated on NASA TMR's own convention plus a developed-region
shape guard — through the **`cfdtrust` audit path** (`cfdtrust.cli run` → real Docker
simpleFoam → `cfdtrust.cli report`).

Cycle-4 investigation surfaced a **dual-track inconsistency**: the codebase has two live
runners in `ui/backend`, with genuinely different flat-plate definitions:

| Runner | Used by | Flat-plate definition | State |
|---|---|---|---|
| **`cfdtrust`** (audit path) | `case_family_registry.py`, `manifest_patch.py`, `workbench_decide.py` | `flat_plate_rans_sst`: U=30 m/s, ν=6e-6, Re/L=5e6, NASA 2-block topology, y+~1.3, NASA freestream | **validated PASS** (DEC-209) |
| **`foam_agent_adapter`** (case-gen / exec path) | `case_export.py`, `wizard*.py`, `preflight.py`, `meshing_gmsh/`, `case_scaffold/` | `_generate_steady_internal_flow` flat-plate branch: U_bulk=1, ν=1/Re, Re=5e4 nondim, single-block `(100 80 1)` crude mesh; `phase5_audit_run.py` uses U=69.4 (M=0.2) | **diverges** (continuity blow-up; old fake Cf 0.0076 masked it — DEC-209 cycle-2) |

## Decision

1. **The `cfdtrust` audit path is the canonical V&V / benchmark-validation runner.** It is
   what produces the truth-chain `trust_report.json` with `validation_status: validated`
   against pinned references. Blueprint v4 Law-1 ("covered" = runnable + passes-benchmark)
   and Law-2 (V&V loop first-class) are satisfied for the incompressible-RANS-aero vertical
   **through this path**.
2. **P1's flat-plate V&V-loop deliverable is COMPLETE.** The headline P1 goal — a runnable,
   benchmark-passing incompressible RANS aero vertical with a closed V&V loop — is achieved
   and independently verified (DEC-209 ADDENDUM 5).
3. **The `foam_agent_adapter` dual-track reconciliation is QUEUED as a separate decision**
   (see below), to be scoped and ratified on its own merits — NOT folded into P1 under
   schedule pressure. The adapter is a second live product subsystem; repointing/retiring
   its divergent flat-plate regeneration is a structural change deserving its own DEC.

## Queued follow-up — adapter dual-track reconciliation (future DEC, not yet scoped)

Preserved so the cycle-4 investigation is not lost. When picked up, promote to its own DEC.

**Problem:** `foam_agent_adapter._generate_steady_internal_flow` (`src/foam_agent_adapter.py`
~L4118-4138) regenerates a divergent nondim flat-plate case that no longer matches the
validated `flat_plate_rans_sst`. `scripts/phase5_audit_run.py` drives it at U=69.4. The
`knowledge/gold_standards/turbulent_flat_plate.yaml` is laminar Blasius (Cf 0.0042) — a
naming collision with the turbulent case + its NASA reference. Stale `0.0076` /
`cf_spalding_fallback` fixtures persist.

**Candidate approaches (decide in the follow-up DEC):**
- **(a) Delegate** — repoint the adapter's `turbulent_flat_plate` to run the validated
  `flat_plate_rans_sst` case dir via the existing `mesh_already_provided` +
  `case_dir_override` staging path (DEC-V61-090, `foam_agent_adapter.py` L631-708). Single
  source of truth; no duplicated case-gen. Likely lowest-risk.
- **(b) Regenerate matching** — rewrite the flat-plate branch to self-generate a
  NASA-conditions case (duplicates the definition; drift risk).
- **(c) Retire** — if no live product flow actually needs the adapter to *generate* a flat
  plate (only to *run* provided cases), retire the regeneration branch entirely.

**Required when picked up:** correctness-critical V&V change → Codex review (cap=3); update
stale `0.0076` + `cf_spalding_fallback` fixtures; resolve the gold-standard naming collision;
four-question gate; `trust_report` MOCKED→real on the adapter path (if (a)/(b) chosen).

## Governance

- Four-question gate (this decision is doc/scope-only, no code change): (1) LLM-offline —
  N/A (no runtime change) (2) artifacts — N/A (3) TrustGate — unaffected (4) advisory-only —
  unaffected. The decision strengthens, not weakens, the advisor-not-driver boundary by
  naming the deterministic audit path canonical.
- Driven autonomously by `cfd-chief-engineer` at L2 (DEC-V61-208); the consequential
  dual-track fork was surfaced to the sponsor (option A chosen) rather than unilaterally
  restructuring a second live subsystem — consistent with "small/surgical/reversible" +
  "no drive-by refactor" guardrails that persist at all autonomy levels.
- `autonomous_governance: true` → counter +1 (telemetry only, per RETRO-V61-001 / v2.3).

## Status

**Accepted.** P1 incompressible-RANS-aero V&V loop closed (canonical runner = cfdtrust).
Next: sponsor directs P1-additional-hardening vs P2 entry (pre-flight signals + ruleset
distillation). Notion sync (DEC-V61-206/207/208/209/210 Accepted) at session-end.
