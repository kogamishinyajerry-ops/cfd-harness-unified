---
decision_id: DEC-ADWM-002
timestamp: 2026-04-18T21:05 local
autonomous_governance: true
reversibility: reversible (single-commit revert)
notion_sync_status: synced 2026-04-19 (Decisions DB page https://www.notion.so/346c68942bed814ba573c8ac7bdb4901; confirmed by re-probe 2026-04-20T12:20)
---

# DEC-ADWM-002: Self-APPROVE EX-1-008 Fix Plan Packet, dispatch Codex

## Decision summary
Under ADWM v5.2 granted authority, opus47-main self-approves the EX-1-008 Fix
Plan Packet (reports/ex1_008_dhc_mean_nu/fix_plan_packet.md) and dispatches
it to codex-gpt54 for execution. CHK-1..10 binding criteria apply; CHK-3
(Nu ∈ [25, 35] on B1 mesh) is the physics-dependent gate.

## Trigger / evidence
- EX-1-007 B1 post-commit measurement (commit 50ec0a3): Nu=66.25 vs gold=30,
  ABOVE_BAND verdict by 120% relative error.
- Root cause in slice_metrics addendum §honest_interpretation: extractor
  computes LOCAL mid-height Nu while gold reference is MEAN wall-integrated.
- G1 goal in ADWM activation plan (.planning/adwm/2026-04-18_activation_plan.md
  §2) explicitly targets this refactor.

## Alternatives considered
- **Option A (wallHeatFlux function object)**: rejected for cycle 1 due to
  cost — needs solver re-run per iteration (~20 min) for algorithm validation.
  Deferred to future QoL slice.
- **Option B (snGrad patch integration)**: rejected for cycle 1 — higher
  implementation risk for same tolerance target; can be Codex's cycle-2
  pivot if cycle 1 fails CHK-3.
- **Option D (leave it, document as known methodology bug)**: rejected —
  leaves case #7 with active methodology-FAIL masking; blocks future DHC
  contract-status promotion.

## Chosen: Option C (post-hoc area-average) via Codex dispatch
Fix Plan Packet approved 2026-04-18T21:05 local. Cycle budget 2.

## External-Gate pass-through likelihood estimate
- 70% (honest self-estimate)
- Down-weights:
  - Physics risk on CHK-3 (~15%): algorithm may produce Nu 20 or 34–38
    depending on BL resolution symmetry.
  - Ambiguity in Dhir 2001 "mean Nu" definition: arithmetic mean over y
    versus area-weighted over wall patch. Codex's implementation assumes
    unweighted; if gold uses weighted, there's a ~5% additional deviation.
- No policy risk: aligned with ADWM granted authority; scope clean.

## Reversibility
- Fully reversible: single git revert restores Nu=66.25 behavior.
- No downstream consumer depends on the Nu numeric value (only on presence
  of the key_quantities["nusselt_number"] slot).

## Hard-floor touches
- #2 (禁区 dispatch-to-Codex): ACTIVE — src/foam_agent_adapter.py +
  tests/test_foam_agent_adapter.py both dispatched to codex-gpt54.
- #7 (trailer): CHK-8 requires `Execution-by: codex-gpt54` on resulting commit.
- No other floors touched.

## Cycle protocol
- Cycle 1 budget: one Codex dispatch round with §2.1 Option C algorithm.
- If cycle 1 FAIL CHK-3: Codex pivots to Option B (snGrad patch integration).
- If cycle 2 FAIL CHK-3: FUSE triggers → DEC-EX-B equivalent (defer to Tier-1
  wallHeatFlux function object rewrite).

## Notion mirror TODO
When MCP reachable: Decisions DB entry with same fields; link to Fix Plan
Packet URL and eventual commit SHA.
