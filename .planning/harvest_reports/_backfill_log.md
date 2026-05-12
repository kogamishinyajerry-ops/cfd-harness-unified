# Backfill Log (append-only)

> **Established 2026-05-08 by harvest cycle 002 / cfd-harness-harvest skill.**
> Records `backfill-sweep` mode invocations cumulatively without
> inflating harvest report count. Each row = one trigger + sweep.

## Format

```
### YYYY-MM-DD · <trigger summary> · session=<N>

- Trigger: <what changed in the truth>
- Files touched: <list of paths>
- Commits: <commit shas if separate, or "session-batch" if accumulated>
- Mode: backfill-sweep
- Convention: <markers applied per knowledge_status_convention.md>
- Round: <N of ≤3>
- Notes: <residual stale not yet swept; or "complete">
```

## Entries

### 2026-05-08 · A2 advisor LANDED (commit a09ae0a) · session 1

- Trigger: V2 advisor extracted as productized form of `virtual_interface_detector` (commit a09ae0a). All cases 003-010 had `_pending_A2` markers in their kickoff files.
- Files touched: cases 003/004/005/006/007/008/009/010 kickoffs, case_005_codex_response.md (yaml field), case_005/007 validation files, v_series_2026-05-08.md (8-case rows landed)
- Commits: e3e6526 → 56f1a11 → a09ae0a → 4d2fb26 → 15ae33e (5-commit chain)
- Mode: backfill-sweep
- Convention: pre-convention (predates knowledge_status_convention.md)
- Round: 1 of 3
- Notes: complete; sweep happened during harvester directive execution session 1

### 2026-05-08 · A2 LANDED → 003/004 kickoff "expect detection" framing · session 2 (early)

- Trigger: Main session backfilling cases 003/004/005/006 kickoffs to use landed A2 advisor with 3-step protocol + 3-branch V-finding decision tree
- Files touched: case_003_crm_hls_boundary_layer.md, case_004_nrel_phase_vi_mrf.md, case_005_rae_m2129_sduct.md, case_006_onera_m6_transonic.md
- Commits: session 2 working-tree edits (not separate commits — done as conversational edits before convention established)
- Mode: backfill-sweep (retroactively classified)
- Convention: pre-convention (predates knowledge_status_convention.md)
- Round: 2 of 3
- Notes: STALE within hours — V25 (open · 2026-05-08 v2) revealed A2 has no gap-detection API; "expect A2 to detect" framing was inherited implication, not coded capability. Triggered cycle-002 harvest.

### 2026-05-08 · V25 reveals A2 placeholder semantic → harvester cycle 002 sweep · session 3

- Trigger: V25 (open · 2026-05-08 v2) shows A2's `_run_shared` returns hardcoded `bbox_overlap_fraction=1.0`, `area_diff_fraction=0.0` regardless of geometry. "A2 PASS" reported by case_003/004/005 v2 confirms only that algorithm runs, NOT that gap-detection works (no API surface for gap distance).
- Files touched: cases 003/004/005/006 kickoffs (apply [QUESTIONABLE 2026-05-08] markers per knowledge_status_convention.md to "exercise A2; expect detection" framing), INDEX.md (case_003/004/005 status reconcile to case_index.md SSOT), this _backfill_log.md entry
- Commits: session-batch — written as cycle-002 harvest output, grouped with case orchestration docs
- Mode: backfill-sweep
- Convention: applies knowledge_status_convention.md (established this cycle)
- Round: 3 of 3 — round-cap reached for A2 backfill chain. If further A2-related sweep needed, escalate to A2-v2 land + full-mode harvest.
- Notes: complete; harvest_002 report documents synthesis. A2-v2 sub-DEC drafted (`patches/draft_a2_v2_gap_detection_2026-05-08.md`).

## Round-cap reset rule

A backfill chain ends when:
- The trigger root cause is resolved (e.g., A2-v2 lands → A2 capability is now real, no more inherited-implication decay), OR
- 3 sweeps complete (round-cap), OR
- Trigger evolves into a different root cause (e.g., V25 surfaces during V19 sweep — that's a new chain, not continuation)

After round-cap, escalate to `full`-mode harvest if residual stale remains.
