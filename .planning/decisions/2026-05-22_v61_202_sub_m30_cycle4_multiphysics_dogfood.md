---
decision_id: DEC-V61-202-SUB-M30-CYCLE4-MULTIPHYSICS-DOGFOOD
title: M3.0 cycle 4 — horizontal multi-physics dogfood (RANS / LES / compressible / multi-region)
status: Proposed
proposed_date: 2026-05-22
parent_dec: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
phase: M3.0 cycle 4 (horizontal validation · physics-regime coverage)
notion_sync_status: pending_accepted
autonomous_governance: true
counter_status: v6.1 telemetry
charter_class: false
scope_class: sub_dec
ssot: .planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md
predecessors:
  - DEC-V61-202-SUB-M30-CYCLE1-DECIDE-STATE
  - DEC-V61-202-SUB-M30-CYCLE2-MUTATION-TOPBAR
  - DEC-V61-202-SUB-M30-CYCLE3-FOCUS-DRIVER
---

## Why

Cycles 1-3 dogfooded the workbench dynamic frame on **case_007 KCS ship
VOF** — a single physics regime (transient incompressible VOF with
kOmegaSST). The SSOT promise is broader: an engineer should be able to
construct a case in ≤30 minutes via the workbench regardless of regime.
Cycle 4 validates that decide() + dynamic frame degrade gracefully —
and where possible, give *useful* guidance — across the four canonical
regime families we expect engineers to construct:

1. **RANS steady incompressible** (e.g., flat plate kOmegaSST,
   simpleFoam) — the "easy" baseline; high audit confidence; engineer
   should see step_default rails throughout if manifest is well-formed.
2. **LES** (e.g., channel WALE, pisoFoam) — transient + sub-grid model
   selection; auditor surfaces should expose intuitive next-action
   gaps when LES-specific knobs (filter width, sub-grid model) are
   absent.
3. **Compressible** (e.g., supersonic wedge, rhoCentralFoam) — density-
   based solver path; thermo block + transport properties required;
   workbench should not pretend it's incompressible.
4. **Multi-region** (e.g., conjugate heat transfer, chtMultiRegionFoam)
   — multiple mesh + bc files per region; decide() should NOT crash
   when bc_audit.json has per-region nested structure; rail.primary
   should surface a coherent first-action.

The cycle 4 question is **not** "does each regime construct in 30 min"
— that's the M3.0 milestone close criterion validated in cycle 7. Cycle
4's question is narrower: **does decide() produce coherent, non-broken
frames across all 4 regime shapes?**

## Method

Per Anthropic agent canon §6 (real-usage eval > benchmark), cycle 4
treats each regime as a **canonical eval case**. The dogfood script
stages each manifest + plausible audit artifacts, walks Steps 1-5 via
the GET frame endpoint, and asserts the frame shape is coherent.

This deliberately does NOT exhaustively cover every physics knob — that's
M3.* depth, not M3.0 horizontal breadth. The bar is "no crashes, no
empty frames, rail.primary always picks something actionable, step
hints surface when no problems exist."

## What

### In scope

**Dogfood**:
- `scripts/dogfood/case_007_cycle4_multiphysics.py` — single script
  with 4 stage helpers (RANS / LES / compressible / multi-region) +
  per-regime Step 1-5 walk. Asserts:
  - GET `/api/cases/{id}/workbench_frame?step=N` returns 200 for all N∈{1..5}
  - `rail_primary.kind ∈ {problem_fix, info_gap, step_default}` (never empty)
  - `bottom_cards` is a list (may be empty, but `len(.)≥0`)
  - `topbar_cta.kind` is one of the 4 enum values
  - `manifest_state_sha` is a non-empty SHA string
  - No `500` / `502` / unhandled exceptions

**Dogfood report**: `.planning/dogfood/DOGFOOD_M30_CYCLE4_MULTIPHYSICS.md`
with per-regime trace + verdict matrix.

**Code (only if dogfood surfaces real gaps)**:
- Backend: targeted fixes to `workbench_decide.py` if any regime
  triggers an unhandled artifact shape. Each fix → new test in
  `test_workbench_frame_cycle4.py` (or extends cycle 3 file).

### Out of scope (cycle 5+)

- LES sub-grid model recommendation engine (V130 advisor)
- Compressible Riemann solver selection logic
- Multi-region conjugate boundary auto-mapping
- Browser e2e via Playwright (cycle 5)
- Default-on `?dynamic_frame=1` (cycle 5)
- Full 30-min beginner test (cycle 7)

## Closure criteria

- [ ] Dogfood script stages 4 regimes and walks Steps 1-5 for each
- [ ] All 4 regimes pass shape-coherence checks (no crashes, frame populated)
- [ ] Dogfood report records per-regime trace + verdict matrix
- [ ] Codex R0 APPROVED or CHANGES_REQUIRED closed ≤ 3 rounds
- [ ] DEC Proposed → Accepted
- [ ] Notion sync (session-end)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| A regime exposes a real decide() bug; cycle 4 expands into a multi-commit fix-chain | Time-box: if more than ~2 gaps surface, defer fixes to cycle 4.5 sub-DEC and close cycle 4 as "horizontal coverage measured" |
| Synthetic artifacts don't reflect real auditor output | Cross-reference shapes against `ui/backend/audit/cases/*/artifacts/` real cases (channel_flow_rans_sst, flat_plate_rans_sst) |
| Test-data sprawl | Single script with 4 stage-helpers; no separate fixture files per regime |

## Provenance

- Charter: DEC-V61-202-WORKBENCH-DYNAMIC-GUIDED
- SSOT: `.planning/workbench/GUIDED_CASE_CONSTRUCTION_FLOW.md` §1 litmus
- Predecessors: cycles 1+2+3 (single-regime focus loop closed)
- User authorization 2026-05-22: "我批准你的多agent团队持续工作，奔着里程碑继续"
- Method backing: Anthropic agent canon §6 real-usage eval > benchmark

Surface-scan-found: ui/backend/services/workbench_decide.py · disposition: extend (only if regime surfaces a real bug; default expectation = pure validation)
