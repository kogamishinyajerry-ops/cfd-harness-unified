---
decision_id: V61-232
title: P4 charter (scaffolding-first) — rhoCentralFoam supersonic-wedge oblique-shock V&V contract authored offline (LIVE_RUN_PENDING, no coverage flip)
status: Accepted
accepted_date: 2026-06-07
parent_dec: V61-224
phase: P4 compressible/supersonic coverage · V71.A rhoCentralFoam anchor (scaffolding slice)
autonomous_governance: true
confidence: high
kogami_opt_in: false (scaffolding is offline + self-verifying + reversible; no §11.1 workbench-freeze paths touched; the high-risk Docker/TRUST-CORE live-flip is explicitly DEFERRED to a separate gated slice)
round_cap: 3
codex_review_relay: pending (charter-class new-domain V&V code — extractor/gate + gold; sync-gate per project rule)
codex_verdict: pending
codex_tool_report_path: reports/codex_tool_reports/v61_232_p4_wedge_scaffolding_report.md
touches_shared_dec: src/_plane_assignment.py (+2 module assignments → .importlinter regenerated) — four-plane SSOT is consumed by the runtime guard + lint-imports CI; new src.wedge_oblique_shock_{extractor,gate} modules
notion_sync_status: pending_accepted (session-end batch)
date: 2026-06-07
---

# DEC-V61-232 · P4 supersonic-wedge oblique-shock V&V scaffolding (V71.A rhoCentralFoam anchor)

## Context

`runnable-coverage` just flipped **1 → 2** (W3.3b conjugate Gnielinski, DEC-V61-228).
The risk-first path names **P4 = compressible/supersonic** as the next compute type;
the capability matrix tracks the precise gap as **V71.A**: `rhoCentralFoam` is wired in
the advisor surface (`solver_block_advisor` R1/V27 + R2/V28) but **no anchor case validates
the harness can run it and judge correctness from artifacts**.

## Decision (user-ratified, this session)

Two forks were surfaced to the sponsor and decided:

1. **Scope = scaffolding-first** (NOT a live coverage flip this arc). Author the full
   offline, self-verifying V&V contract now; **defer** the Docker/ESI image provisioning +
   adapter live-wiring to a separate gated slice.
2. **Benchmark = M₁=2.0 inviscid wedge** (θ=15° primary + θ=10° secondary), gold =
   analytical oblique-shock via the **θ-β-M + normal-shock relations** — the only candidate
   that is fully self-verifying (every reference re-derives from `(M₁, θ, γ)` alone), exactly
   mirroring the W3.3a (fin `tanh(mL)/mL`) and W3.3b (Gnielinski) honesty pattern.

### Why scaffolding-first (the BLOCKER that forced the fork)

**No local runner can live-run `rhoCentralFoam` today** — independently verified, fact not
inference:
- `src/foam_agent_adapter.py` (the charter's TaskSpec→solver path) is hardwired to a
  Foundation **OF10/ESI** image that is **absent on disk**; the only present image is
  Foundation **OF11**, which has **no density-based `rhoCentralFoam`** (it does compressible
  only via pressure-based `fluid`/`isoThermalFluid` modules).
- `ui/backend/audit/cfdtrust/backends/openfoam.py` `run()` **hardcodes `simpleFoam`**
  (code comment `:671`: *"hardcoded simpleFoam …, which lies for rhoCentralFoam, interFoam"*);
  it only *recognises the log* in ingest mode (`:2401`).
- **DEC-V61-224 predicted exactly this**: *"P4 (rhoCentralFoam) + P4+ (VOF/LES) will re-hit
  the same wall."* Law-1 "runnable" is image-gated.

A genuine live coverage 2→3 flip therefore requires provisioning an **ESI image**
(`opencfd/openfoam-default:2312`, already named in DEC-V61-224) + wiring the TRUST-CORE
adapter to it — real, high-risk Docker/infra work. The sponsor chose to land the
honesty-critical V&V logic first (low-risk, fully testable offline) and gate the Docker
investment separately. This mirrors how **W3.3a** landed: contract + self-verifying test
authored, contract_status `ANALYTICAL_REFERENCE_AUTHORED · LIVE_RUN_PENDING`, then the live
run flipped it later.

## Scope of THIS slice (what landed)

Honesty-critical, all offline:
1. `knowledge/gold_standards/wedge_oblique_shock.yaml` (θ=15°, 5 observables) +
   `knowledge/gold_standards/wedge_oblique_shock_theta10.yaml` (θ=10° sensitivity).
   `flow_type: EXTERNAL` (precedented; **no shared-schema enum change**),
   `geometry_type: SUPERSONIC_WEDGE` (descriptive free string), `tolerance: 0.03`,
   `contract_status: ANALYTICAL_REFERENCE_AUTHORED · LIVE_RUN_PENDING`. Reference values are
   CLOSED-FORM functions of `case_info.wedge_inputs` — never transcribed.
2. `tests/p4/test_wedge_oblique_shock_gold.py` — **self-verifying** honesty lock:
   independently re-solves θ-β-M + normal-shock and fails if any committed value drifts.
   Needs NO fixture (pure math).
3. `src/wedge_oblique_shock_extractor.py` (**Execution** plane) — PURE; measures β from the
   solver's own density-gradient locus + M₂/ratios from area-averaged pre/post-shock state;
   **NEVER reads the θ-β-M form** (anti-tautology); fail-closed on missing/NaN.
4. `src/wedge_oblique_shock_gate.py` (**Control** plane) — comparator PASS AND 5 independent
   HARD gates (supersonic-inflow + inflow-matches-target + downstream-supersonic + β-above-
   Mach-angle + ideal-gas thermodynamic consistency across the shock). Zero magic numbers
   (all from `wedge_inputs`).
5. `src/_plane_assignment.py` +2 assignments → `.importlinter` regenerated (`gen_importlinter.py`).
6. `reports/showcase_aero/_w71a_wedge_probe_SYNTHETIC/` — a **transparently generated**
   (not solver-produced) fixture + generator script + REPRODUCE.md, used ONLY to exercise
   the gate's parsing + fail-closed logic offline. Unmistakably labeled SYNTHETIC; the
   real frozen probe lands with the deferred live-flip.
7. `tests/p4/test_wedge_oblique_shock_gate.py` — gate coverage + anti-cheat (doctored
   shock-line / doctored ratio / subsonic inflow / detached M₂<1 → FAIL; missing → raise).
8. `.planning/evals/canonical/E22_case_037_rhoCentralFoam_supersonic.md` — **correctness fix**:
   `β≈42°` was wrong (β=42° ⇒ θ=12.36°); correct weak-shock β for M=2.0/θ=15° is **45.34°**;
   substrate re-cited from `AGARD AR-211` (experimental) to the θ-β-M relation (NACA 1135 /
   Anderson, *Modern Compressible Flow*) — the wedge gold is analytical, not experimental.
9. `.planning/cfd_capability_matrix.md` — note V71.A scaffolding authored; rhoCentralFoam
   stays **no-live-anchor** (coverage NOT flipped).

## Worked reference (re-derived in the self-verifying test)

M₁=2.0, γ=1.4, weak root:

| Observable | θ=15° | θ=10° |
|---|---|---|
| β (deg) | 45.3436 | 39.3139 |
| M₂ | 1.4457 | 1.6405 |
| p₂/p₁ | 2.1947 | 1.7066 |
| ρ₂/ρ₁ | 1.7289 | 1.4584 |
| T₂/T₁ | 1.2694 | 1.1702 |

## Four-question gate

- **Q1 LLM offline?** YES — extractor + gate + comparator are pure Python over solver
  artifacts; zero model calls.
- **Q2 verdict artifacts-based?** YES — flat boolean conjunction over `ResultComparator`
  (measured-from-artifacts QoIs vs re-derivable gold) AND independent hard gates.
- **Q3 TrustGate explicit + fail-closed?** YES — `tolerance: 0.03` declared + re-asserted by
  the self-verifying test; gate raises on missing/NaN/subsonic-inflow; any single failure
  fails the whole gate.
- **Q4 advisory-not-driver?** YES — reports a PASS/FAIL verdict; does not auto-decide
  engineering.

## Explicitly OUT of scope (deferred → separate gated DEC)

- ESI Docker image provisioning + `foam_agent_adapter` live-wiring of `rhoCentralFoam`
  (Path A in the scan) — the only path that flips coverage 2→3 live.
- `GeometryType.SUPERSONIC_WEDGE` enum + `gold_standard_schema.json` `flow_type` enum +
  `regime_contract`/`case_family_registry` compressible branch — runtime wiring with no
  consumer until the live slice; adding now would be speculative.
- Pulling the external `~/Desktop/case_006_*` rhoCentralFoam templates into the repo
  (auditability decision deferred with the live slice).

## Forward-hardening backlog (from the adversarial red-team pass · workflow `wig61u2wt` · verdict HELD)

The red team broke nothing (zero `is_real_hole`), but flagged two **non-blocking**
hardenings to land WITH the live slice (premature offline — a synthetic fixture has
no real discretization smearing to discriminate):
- **6th cross-consistency hard gate** — tie the MEASURED β to the MEASURED p₂/p₁ via
  the normal-shock relation `p₂/p₁ = 1 + 2γ/(γ+1)·((M₁·sinβ)²−1)` within a band tighter
  than the 3% per-observable tolerance. The current 5 gates check each observable
  independently, so an internally-contradictory tuple **within 3% of a real shock**
  (red team's measured worst case: 2.988%) can pass. This is *inside* the documented
  per-observable tolerance (not a contract violation; a real conservative solve is
  self-consistent), but a physics-*locus* gate would reject it. Value is at live-run
  time when real smearing must be told apart from a wrong solution.
- **Machine-readable `contract_status`** — promote the gold's `contract_status` from a
  YAML comment to a structured key + a test asserting it ≠ a LIVE/validated value, so
  future coverage tooling can never machine-read the scaffolding as validated. (Today
  the comment is honest and unread by any coverage consumer — verified inert.)

— DEC-V61-232 · 2026-06-07 · scaffolding-first P4 anchor · LIVE_RUN_PENDING (no coverage flip)
