---
decision_id: V61-233
title: P4 V71.A — LIVE rhoCentralFoam oblique-shock solve PASS → V&V BENCHMARK LIVE-VALIDATED (runnable-coverage flip 2→3 NOT earned — gated on backend wiring per DEC-V61-224(b), Codex R0 P2)
status: Accepted
parent_dec: V61-232 (P4 scaffolding-first charter) · V61-224 (P3 solver-environment / fork wall) · V61-207 (Blueprint v4 Law 1 runnable-coverage)
sibling_decs: V61-228 (W3.3b conjugate flip 1→2 — the immediately prior coverage flip) · V61-209 (gold-standard tolerance convention)
phase: P4 (compressible/supersonic vertical) · V71.A rhoCentralFoam anchor — V&V-benchmark-validation milestone (coverage flip deferred)
autonomous_governance: true
confidence: high
kogami_opt_in: false (additive V&V benchmark + live-run artifact + gate hardening; reversible; no §11.1 workbench-freeze paths touched; the high-risk decision — provision ESI vs Foundation — was already ratified by the V61-232 fork analysis + this session's sponsor approval)
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (governance baseline; codex review --uncommitted)
codex_verdict: APPROVE-equivalent — chain CLOSED within cap=3 (R0→R1→R2), NO P1 / no functional defect; every finding an honesty/audit-trail correction, each round narrower. R0 = 2×P2: [P2-1] capability-matrix overclaim — marking rhoCentralFoam ✅ PR / coverage 2→3 violates Law-1 + DEC-V61-224(b) (the workbench foam_agent_adapter/cfdtrust cannot launch a density-based solver; the slice ran it DIRECTLY in a container) → FIX reverted to GAP-TRACKED + "V&V LIVE-VALIDATED" note, coverage stays 2; [P2-2] validation_status had no production consumer → FIX reframed as a TEST-ENFORCED honesty invariant + forward hook (not "coverage tooling reads it today"). R1 = 1×P2: the θ=10 discrimination test passed on a geometry artifact (β≈8°) not reference values → FIX gave the θ=10 gold the live sampling geometry (x=0.12/origin=0.05) so β extracts ~45.24 and the gate fails on a genuine reference-value mismatch vs 39.31. R2 = CLEAN on code ("no functional regression"), 2×P3 doc-hygiene on the report artifact itself → fixed in place. Net: the slice is honestly a V&V-VALIDATION MILESTONE, NOT a runnable-coverage flip (coverage stays 2; flip gated on the deferred backend-wiring slice). In-house red-team (workflow wjjm4tbtp, 5 lenses + triage) verdict HELD (0 real holes; 2 cosmetic nits fixed: stale 5→6 hard-gate docstring + SHA256SUMS tamper-manifest).
codex_tool_report_path: reports/codex_tool_reports/v61_233_p4_wedge_live_flip_report.md
notion_sync_status: synced 2026-06-08 (https://app.notion.com/p/379c68942bed8101a69ece546d56ae3e)
touches_shared_dec: src/wedge_oblique_shock_gate.py (+6th hard gate — shock-locus cross-consistency) · knowledge/gold_standards/wedge_oblique_shock.yaml (contract_status comment + structured key → LIVE_VALIDATED, mesh_info.cells 0→12000) · no schema/loader changes (reuses V61-232 EXTERNAL/SUPERSONIC_WEDGE + multi-doc loader); src/_plane_assignment.py unchanged (modules already registered in V61-232)
date: 2026-06-07
---

# DEC-V61-233 · P4 V71.A LIVE rhoCentralFoam oblique-shock — V&V benchmark LIVE-VALIDATED (coverage flip 2→3 deferred, Codex R0 P2)

## Context

Blueprint v4 **Law 1** (DEC-V61-207): a compute type is "covered" only when its
solver runs end-to-end AND a benchmark passes its tolerance gate. Runnable-coverage
stood at **2** (incompressible RANS NACA0012 = 1; W3.3b conjugate Gnielinski = 2,
DEC-V61-228). The risk-first path names **P4 = compressible/supersonic** as the next
compute type; **V71.A** is the precise gap: `rhoCentralFoam` is wired in the advisor
surface but no anchor case proved the harness can run it AND judge correctness.

**DEC-V61-232** (this session, scaffolding-first) landed the honesty-critical V&V
contract offline: an analytical θ-β-M oblique-shock gold (self-verifying), a PURE
anti-tautology extractor (Execution plane), and a fail-closed Control-plane gate —
but explicitly **did NOT flip coverage**: `contract_status:
ANALYTICAL_REFERENCE_AUTHORED · LIVE_RUN_PENDING`, gated on the DEC-V61-224 fork wall
(no local image runs `rhoCentralFoam`). The sponsor then approved **opening the
live-flip slice**: provision the ESI image, run the wedge live, flip 2→3.

## Decision (user-ratified intent + Codex-corrected outcome)

The sponsor approved "opening the live-flip slice" to flip runnable-coverage 2→3. The
slice ran a **LIVE `rhoCentralFoam` solve** of the M₁=2.0 inviscid 15° wedge on the ESI
v2312 image and validated it through the V61-232 gate — **the V&V benchmark is
LIVE-VALIDATED** (real solve + gate PASS within 0.5%).

**Codex R0 correctly caught that this does NOT flip runnable-coverage.** Per Blueprint
v4 Law-1 + the P4-inherited DEC-V61-224(b) provision, "runnable" requires the workbench
**execution backend (`foam_agent_adapter`) wired to the image AND reconciled with the
`cfdtrust` V&V backend** — not merely a solver run. This slice ran the solver DIRECTLY
in a raw container, bypassing both backends (the adapter has no density-based routing
branch; `cfdtrust/backends/openfoam.py` hardcodes `simpleFoam`). So **runnable-coverage
stays 2**; the flip to 3 is earned only when the backend wiring lands (a separate slice).
The honest outcome of THIS slice: the rhoCentralFoam **V&V layer** (gold + extractor +
gate + a real solve passing) is done; the **execution-backend integration** is not.

### The fork wall, resolved

DEC-V61-224 predicted the Foundation **OF11** image (`foamRun -solver`) lacks
standalone density-based solvers like `rhoCentralFoam`. **Resolution: provision the
ESI image** `opencfd/openfoam-default:2312` (already named in V61-224), which ships a
native-ARM64 `rhoCentralFoam` — verified present in a fresh container. This is the
"provision an ESI image" path V61-232 deferred; the live solve used a **fresh,
disposable container** (`--rm`), never disturbing the running `cfd_v12_run` /
`of11_run` / `of11_probe` containers.

> NOTE — adapter wiring scope (Codex R0 P2-1 correction): this slice ran the solver
> **directly** in a fresh ESI container — the honest minimal path to a live V&V
> ANCHOR, but NOT the Law-1 "runnable" bar. Per DEC-V61-224(b), a runnable-coverage
> flip requires the workbench execution backend (`foam_agent_adapter`) wired to the
> image AND reconciled with the `cfdtrust` V&V backend (`openfoam.py run()` currently
> hardcodes `simpleFoam`). That wiring is a SEPARATE, larger infra change, deferred.
> Therefore this slice **LIVE-VALIDATES the V&V benchmark but does NOT flip coverage**;
> the flip is earned only when the backend wiring lands. (Initial draft of this DEC
> wrongly claimed the flip was earned by the live solve alone — corrected here.)

## What landed (the V&V validation — NOT a coverage flip)

1. **Live solve** — `blockMesh` (12000-cell, 2 all-hex blocks; `checkMesh` OK, max
   aspect 1.41, non-orthogonality 14.9) + `rhoCentralFoam` (Kurganov flux, vanLeer,
   adjustTimeStep maxCo=0.5, endTime=2.0 ≈ 6.5 flow-throughs) in `opencfd/openfoam-default:2312`.
   Top boundary raised to y=0.35 so the β=45.34° shock EXITS THROUGH THE OUTLET and
   never touches the top `symmetryPlane` — no reflected-shock contamination of the
   wedge-surface post-shock average.
2. **Frozen probe** — `reports/showcase_aero/_w71a_wedge_probe/` (REPRODUCE.md +
   solver-produced postProcessing: freestream/postShock `surfaceFieldValue.dat`,
   shockLine `line_rho.xy`; `case_definition/` for re-run; logs). REPLACES the offline
   `_w71a_wedge_probe_SYNTHETIC/` fixture (removed — superseded as V61-232 foresaw).
3. **Gate PASS, measured from the field** — β=45.24° (gold 45.34, −0.23%), M₂=1.444
   (−0.08%), p₂/p₁=2.188 (−0.31%), ρ₂/ρ₁=1.722 (−0.41%), T₂/T₁=1.269 (−0.02%),
   M₁_meas=2.0000. **All 5 observables within 0.5%** (tolerance 3%); **all 6 hard
   gates PASS**.
4. **6th hard gate landed** (V61-232 forward-hardening, scheduled "with the live
   slice") — **shock-locus cross-consistency**: measured β and measured p₂/p₁ must lie
   on the SAME normal-shock locus `p₂/p₁ = 1 + 2γ/(γ+1)((M₁sinβ)²−1)` within 2% (<
   the 3% per-observable band). Catches an internally-contradictory tuple (each
   observable within 3% but not of EACH OTHER — the red team's 2.988% worst case) that
   the five independent checks cannot. Live residual: 0.17%. Anti-cheat test isolates
   it (scale p₂ AND T₂ by 2.5% → observables + ideal-gas still pass, 6th gate trips).
5. **Machine-readable `validation_status`** (V61-232 forward-hardening) — promoted from a
   YAML comment to a structured `case_info.validation_status` key: theta=15 gold =
   `LIVE_VALIDATED`; theta=10 secondary = `ANALYTICAL_REFERENCE_AUTHORED` (no live run).
   Named `validation_status` (NOT `contract_status`) to avoid colliding with the
   load-bearing `physics_contract.contract_status` (physics-compatibility axis, read by
   `report_engine/contract_dashboard.py` + `error_attributor.py`). It is a TEST-ENFORCED
   honesty invariant — the gold self-test reads it and blocks an un-run reference from
   being machine-read as validated — plus a forward hook for coverage tooling; it is NOT
   claimed to be read by any production coverage consumer today (Codex R0 P2-2).
6. **Capability matrix — honest correction (Codex R0 P2-1)** — `rhoCentralFoam` stays
   **GAP-TRACKED** with a "V&V benchmark LIVE-VALIDATED" note; Solvers PR stays 6/10;
   **runnable-coverage stays 2** (the flip is NOT earned — workbench cannot launch a
   supersonic case end-to-end). The matrix's ✅ PR means "the workbench can run it
   end-to-end" (charter §6); a direct container run does not meet that bar.

## Worked reference (unchanged from V61-232, re-derived by the self-verifying test)

M₁=2.0, γ=1.4, θ=15°, weak root: β=45.3436°, M₂=1.4457, p₂/p₁=2.1947, ρ₂/ρ₁=1.7289,
T₂/T₁=1.2694. The live solve reproduces all five within 0.5%.

## Normalized gas (honesty note)

The wedge15Ma5-tutorial **normalized gas** (molWeight 11640.3 ⇒ R=0.71429, Cp=2.5 ⇒
γ=1.4) makes a=√(γRT)=1 at T=1, so M=|U|. The oblique-shock benchmark is
**dimensionless** (β, M₂, and the p/ρ/T ratios depend only on M₁, θ, γ — not R), so
this is the standard, honest setup. The gate's ideal-gas-consistency and shock-locus
checks are dimensionless and never read `R_specific` (kept only as air-context metadata).

## Four-question gate

- **Q1 LLM offline?** YES — extractor + gate + comparator are pure Python over the
  solver's own artifacts; zero model calls.
- **Q2 verdict artifacts-based?** YES — boolean conjunction over `ResultComparator`
  (QoIs MEASURED from postProcessing) AND 6 independent hard gates.
- **Q3 TrustGate explicit + fail-closed?** YES — tolerance 0.03 declared; gate raises
  on missing/NaN/subsonic-inflow; any single failure fails the whole gate.
- **Q4 advisory-not-driver?** YES — reports PASS/FAIL; does not auto-decide engineering.

## Explicitly OUT of scope (follow-ups)

- `foam_agent_adapter` / TRUST-CORE `openfoam.py` live-wiring of `rhoCentralFoam`
  through the ESI image (this slice ran the solver directly in a fresh container).
- θ=10° secondary LIVE run (a different 10° wedge mesh) — stays
  ANALYTICAL_REFERENCE_AUTHORED; documented follow-up.
- `GeometryType.SUPERSONIC_WEDGE` enum + `gold_standard_schema.json` flow_type enum —
  still inert (no consumer); not added speculatively.

## Verification

- `pytest tests/p4/` → **32 passed** (12 self-verifying gold incl. machine-readable
  `validation_status` + 20 gate/anti-cheat incl. live PASS + 6th-gate isolation).
- `pytest tests/p3/` → **367 passed, 1 skipped** (no regression).
- `pytest tests/test_gold_standard_schema/` → 11 passed (new `validation_status` key schema-valid).
- `scripts/gen_importlinter.py --check` → byte-repro in sync (four-plane law).
- Live gate re-run against the frozen probe → PASS (all 6 hard gates).

## Codex review trail

86gs gpt-5.4 xhigh `codex review --uncommitted` · R0 = **2×P2 (no P1)**, both ADDRESSED
(coverage-flip overclaim → honest GAP-TRACKED/coverage-stays-2; `validation_status`
reframed as test-enforced honesty invariant). In-house red-team workflow `wjjm4tbtp`
(5 lenses + triage) verdict **HELD** (0 real holes). Full trail:
`reports/codex_tool_reports/v61_233_p4_wedge_live_flip_report.md`.

— DEC-V61-233 · 2026-06-07 · P4 LIVE rhoCentralFoam V&V benchmark LIVE-VALIDATED · runnable-coverage STAYS 2 (flip gated on backend wiring per DEC-V61-224(b), Codex R0 P2-1)
