---
decision_id: V61-228
title: P3 W3.3b — full two-region conjugate Gnielinski benchmark LIVE PASS → runnable-coverage 1→2
status: Accepted
parent_dec: V61-217 (P3 CHT charter) · V61-207 (Blueprint v4 Law 1 runnable-coverage)
sibling_decs: V61-227 (W3.3a fin gate-wiring) · V61-225 (W3.2b CHT live-run adapter) · V61-224 (P3 solver-environment / fork reconciliation) · V61-209 (gold-standard tolerance convention)
phase: P3 (CHT vertical) · W3.3b (full two-region conjugate benchmark — the coverage-flip milestone)
autonomous_governance: true
confidence: high
kogami_opt_in: false (additive V&V benchmark + gate plumbing; reversible; no §11.1 workbench-freeze paths touched)
round_cap: 3
codex_review_relay: CRS gpt-5.4 high (effort=high, fallback — 86gs xhigh hung with empty output >3min, consistent with W3.2b/W3.3a; effort downgrade noted)
codex_verdict: pending_R2 (R0 2×[P2,P3] → fix 2969ede; R1 2×[P1,P2] → fix reads CASE fluid props; R2 review pending)
codex_tool_report_path: reports/codex_tool_reports/v61_228_w33b_conjugate_report.md
notion_sync_status: pending_accepted
touches_shared_dec: knowledge/gold_standards/cht_pipe_gnielinski.yaml (Re re-anchor 10000→50000 + contract_status LIVE_RUN_PASS) · no schema/loader changes (reuses V61-227 CONJUGATE enum + multi-doc loaders)
date: 2026-06-03
---

# DEC-V61-228 · P3 W3.3b full two-region conjugate Gnielinski benchmark — coverage flip 1→2

## Context

Blueprint v4 **Law 1** (DEC-V61-207): a compute type is "covered" only when its
solver runs end-to-end AND a benchmark passes its tolerance gate. W3.3a
(DEC-V61-227) validated only the **solid side** of CHT — solid conduction + an
**IMPOSED** Robin `h` — through an offline comparison gate; runnable-coverage
stayed **1**. The formal **1→2** flip required **W3.3b**: a FULL two-region
conjugate solve where the **FLUID flow PRODUCES `h`**, validated against a
published turbulent-internal-flow correlation.

## Decision

W3.3b is **LANDED with a genuine live PASS** — runnable-coverage **flips 1→2**.

### What ran (honest live result)

A full two-region conjugate solve, OF11 **Foundation** fork `foamMultiRun`
(`regionSolvers {fluid fluid; solid solid;}`, `coupledTemperature` interface from
`splitMeshRegions -cellZones`), fluid `kOmegaSST` + `eddyDiffusivity` (Prt=0.85),
conducting solid wall. Parallel-plate realization of the Gnielinski pipe
(D_h = 2·full-gap; half-channel with centerline symmetry), L = 40·D_h.

| quantity | live solve | Gnielinski (1976) ref | error | gate |
|---|---|---|---|---|
| Nu | **113.21** | 104.7987 | **+8.03%** | PASS (10% band) |
| energy balance \|Q_iface − ṁcp·ΔT\| | 0.977 W = **2.12%** of Q_iface | — | PASS (<5% HARD gate) |
| Re | 50000 | 3e3–5e6 valid | — | PASS (in band) |

The +8% is the **real, honestly-reported** kOmegaSST+const-Prt internal-HT bias —
inside the 10% honest band at Re=50000. Nu is assembled from the solver's OWN
integrated wall-heat flux + cup-mixing bulk T, **never** the Gnielinski closed
form (anti-tautology). Cross-checked: an energy-conservative whole-channel LMTD
estimate gives Nu≈108 (+3%), confirming the FO-flux estimate (the harder-to-pass
measure) is not flattering the result.

### Re RE-ANCHOR 10000 → 50000 (the one user decision this session)

A baseline conjugate solve at **Re=10000 over-predicted Gnielinski by ~17%** —
established as **energy-consistent (0.04–0.09%), fully developed (local Nu flat
over 22–38 D_h), NOT a bug**: a documented low-Re RANS + constant-Prt
internal-heat-transfer bias at the lower turbulent edge, exactly where BOTH the
RANS closure and the Gnielinski correlation are least reliable. That was a
documented **NO-GO**. Per the user's decision **"Re-anchor at higher Re"**, the
gold was re-anchored to **Re=50000** (mid-turbulent, where closure + correlation
are both robust and turbulent Nu(D_h) is more geometry-insensitive). This is a
**principled fix to a weak validation point, NOT results-driven cherry-picking**:
the reference is still the closed-form Gnielinski value re-derived from inputs
(self-verifying test), and the **10% tolerance is unchanged**.

### Production code (mirrors the W3.3a fin gate, ADR-001 plane split)

- **QoI extractor** `src/cht_conjugate_extractor.py` (**Execution Plane**, pure):
  parse `postProcessing/{qWindowAvg,qWindowInt,TwallWindow,QifaceTotal,TbulkOut,
  Tin,mdotIn}/<t>/surfaceFieldValue.dat` → `h = q_wall/(T_wall − T_bulk_window)`,
  `Nu = h·D_h/k_fluid`, with `T_bulk_window` from a cumulative wall-heat energy
  balance (no interpolated cut-plane). Inputs only; never the closed form.
  Fail-closed on missing/NaN/non-physical dT.
- **Gate** `src/cht_conjugate_gate.py` (**Control Plane** — only plane that may
  import both Execution + Evaluation): `gate_conjugate_against_gold()` extract →
  `ResultComparator.compare()` vs the Gnielinski gold + **four HARD gates**
  (hardened by the Codex chain — see below): (1) energy-balance closure
  `|Q_iface − ṁcp·(T_out−T_in)| ≤ 5%·|Q_iface|`; (2) Reynolds — recovered from the
  SOLVED inlet mass flux + the CASE viscosity (NOT the YAML) — both inside the band
  (3e3 < Re < 5e6) AND matching the gold target Re; (3) Prandtl (from the CASE
  mu·cp/k) inside the band (0.5 < Pr < 2000); (4) the CASE physicalProperties
  match the gold reference fluid. Fluid transport props are read from the replayed
  case's `constant/<region>/physicalProperties`, not trusted from the gold.
- **Contract** `knowledge/gold_standards/cht_pipe_gnielinski.yaml`: Re re-anchored
  10000→50000 (ref Nu=104.7987 re-derived), `contract_status →
  LIVE_RUN_PASS_W3.3b_B` with the live evidence, mesh_info/solver_info updated.
  Reuses the V61-227 `CONJUGATE` enum + multi-doc loaders (no new schema changes).
- **Plane SSOT** `_plane_assignment.py` + `.importlinter` already carried both
  modules; `lint-imports` **5/5 KEPT** (extractor=Execution, gate=Control).
- **Offline replay test** `tests/p3/test_cht_conjugate_gate.py` (**9 green**):
  drives the frozen probe artifacts → gate PASS; anti-cheat (doctored qWindowAvg →
  Nu out of band → FAIL; doctored TbulkOut → energy hard-gate FAIL; out-of-band Re
  → FAIL); extracted Nu ≠ gold reference yet within 10%; missing input → raise.
  Self-verifying `test_cht_pipe_gnielinski_gold.py` (4) re-derives 104.7987.
- **Frozen artifacts** `reports/showcase_aero/_w33b_pipe_probe/` — a proper case
  dir: `postProcessing/` (converged-tail .dat, the gate-replay source),
  `constant/{fluid,solid}/physicalProperties` (the fluid props the gate reads),
  `system/`, `0/` (uniform IC), `REPRODUCE.md` (live recipe incl. mapFields restart).

## Scope / honesty boundary

- **Solver fork**: foamMultiRun (Foundation OF11), reconciled with the `cfdtrust`
  V&V backend per **DEC-V61-224**, NOT the ESI `chtMultiRegionSimpleFoam` the P3
  charter originally named. The compute *type* (conjugate heat transfer) is what
  Law 1 counts — and it is now runnable + benchmark-passed.
- **Mesh-stability path is documented, not hidden**: the resolved (y+~0.8) mesh
  cold-starts unstable at Re=50000, so the production solve restarts from a
  converged coarse wall-function field via `mapFields -consistent`. The committed
  `0/` is the uniform-IC definition; the restart is a runtime convergence aid, not
  a physical change. The coarse wall-function mesh over-predicted (+10.75%); the
  resolved mesh is the more-accurate value and lands in band — refinement reduces
  the error, it was not selected to pass.
- **CI reproduction is offline** from frozen artifacts (no Docker). A
  live-through-`foam_agent_adapter` dispatch for the conjugate case is a separate
  follow-on (the gate is what flips coverage; the adapter dispatch is plumbing).
- **The honesty mandate held**: coverage flipped ONLY on a genuine live PASS
  within the honest 10% band. The Re=10000 NO-GO is documented, not buried; the
  tolerance was NOT loosened; the reference was NOT transcribed or engineered.

## Verification

- `tests/p3/test_cht_conjugate_gate.py` — 9 passed (gate PASS + 2 hard gates +
  anti-cheat + measure-not-echo + honest-error).
- `tests/p3/test_cht_pipe_gnielinski_gold.py` — 4 passed (reference re-derivation).
- `python -m pytest tests/p3/` — 362 passed, 1 skipped.
- `lint-imports` — 5 contracts kept, 0 broken (ADR-001 plane separation).
- Gate run on committed artifacts: `passed=True, energy_balance_ok=True,
  reynolds_in_band=True, Nu=113.2126`.

## Codex review

Risk-tier (CFD new geometry type + new gate code + coverage flip) → Codex chain,
CRS `gpt-5.4` effort=high (86gs xhigh hung with empty output; effort downgrade per
fallback rule). Report: `reports/codex_tool_reports/v61_228_w33b_conjugate_report.md`.

- **R0** (`40420ab`) — no P0/P1; **2 findings**: [P2] Re hard gate read `Re` from
  the gold YAML, not the replayed case; [P3] only Re was range-checked, not Pr.
  → **fix `2969ede`**: derive Re from the measured inlet mass flux + patch area;
  add a Prandtl hard gate.
- **R1** (`2969ede`) — escalated; **2 findings**: [P1] viscosity for the Re recovery
  still came from the gold YAML; [P2] Pr likewise. A rerun with drifted transport
  props (same mass flux) could pass undetected. → **fix (this commit)**: the
  extractor reads ALL fluid transport properties (mu, cp, k_fluid, Pr) from the
  replayed case's `constant/<region>/physicalProperties`; the gate adds a
  fluid-matches-gold hard gate. Gate still PASSES (6/6 checks green). Bundle
  restructured into a proper case dir so the case fluid is co-located with the probes.
- **R2** — review pending (cap=3). `notion_sync_status` advances only after APPROVE.
