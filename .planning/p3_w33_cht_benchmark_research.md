# P3 W3.3 · CHT V&V benchmark gate — RESEARCH + plan (2026-06-03)

> Opens the W3.3 arc: the V&V benchmark tolerance gate that flips
> **runnable-coverage 1 → 2** (Blueprint v4 Law 1: a compute type is "covered"
> only when its benchmark passes a published-tolerance gate end-to-end).
> W3.2b proved CHT *runs* through the adapter (live OF11 foamMultiRun, DEC-225);
> W3.3 makes it *covered*. This is research+plan only — NO benchmark file
> committed until the benchmark choice (§3) is ratified (charter discipline,
> `.planning/p3_cht_kickoff_considerations.md` Consideration 3).

## 1. The existing gate pattern to mirror (grounded, not invented)

The RANS vertical (coverage=1) is gated by an existing, reusable pipeline:

- **Comparator**: `src/auto_verifier/gold_standard_comparator.py:15` —
  `GoldStandardComparator.compare(gold_standard, sim_results) → GoldStandardComparison`
  with `overall ∈ {PASS, PASS_WITH_DEVIATIONS, FAIL}`. Per-observable relative
  error `(|actual−ref|/|ref|) > tolerance → out-of-tolerance`
  (`src/result_comparator.py:184`), with a `|ref|<1e-6` absolute-error fallback.
- **Post-extraction physics gates** (`src/comparator_gates.py:256`): G3
  velocity-overflow, G4 turbulence-negativity, G5 continuity-divergence — fire
  BEFORE the tolerance compare and hard-block any PASS.
- **Gold-standard schema**: `knowledge/schemas/gold_standard_schema.json` +
  canonical example `knowledge/gold_standards/lid_driven_cavity.yaml` (Ghia 1982,
  observables u_centerline/v_centerline/primary_vortex, `tolerance: 0.05`,
  `source` + `literature_doi`, a `physics_contract` block with per-precondition
  `evidence_ref`).
- **Coverage assertion test**: `tests/test_e2e_mock.py:75` asserts the benchmark
  comparison returns PASS.

**W3.3 = author a CHT gold-standard YAML in this exact schema + extract the CHT
QoI + run it through this exact comparator + a test that asserts PASS.** No new
gate infra; reuse the RANS machinery.

## 2. Candidate CHT benchmarks (real, cited)

| Candidate | Reference type | Source | Fit for FIRST coverage |
|---|---|---|---|
| **Straight fin / extended surface** efficiency η = tanh(mL)/(mL) | **Analytical (closed form)** | Incropera & DeWitt, *Fundamentals of Heat & Mass Transfer*, §3.6 (Table 3.4); used as step 1 of Schmid et al.'s OpenFOAM CHT validation hierarchy | **Best** — reference is *derivable*, not transcribed; honest + not gameable |
| **Internal pipe flow** Nu vs Gnielinski correlation | Empirical correlation | Schmid et al., *ChemEngineering* 3(2):59, 2019 (MDPI) — reports <5% (low Re) / <10% (high Re) for chtMultiRegion | Good full-conjugate step; needs turbulent fluid + correlation (not analytical) |
| **Saitoh horizontal cylinder** natural convection | Experimental benchmark | Saitoh, Sajiki & Maruhara 1993; ready OpenFOAM cases on Zenodo (10.5281/zenodo.7635861) | Strong but buoyant (buoyantPimpleFoam) — outside the W3.2b incompressible/foamMultiRun reconciliation; defer |

## 3. Recommendation + the open decision (needs ratification)

**Recommended primary: the straight-fin extended-surface benchmark**, because its
reference value is **analytically exact** — the single most important honesty
property for a coverage gate (the project forbids engineered-to-pass / transcribed
values whose correctness I can't verify in-session).

**Closed form (Incropera Table 3.4, adiabatic-tip):** with
`m = √(hP/(k·A_c))`, fin efficiency `η = tanh(mL)/(mL)` and tip-temperature ratio
`θ_tip/θ_b = 1/cosh(mL)`.

**Worked draft inputs (canonical Al fin):** k=180 W/m·K, h=100 W/m²·K, L=0.05 m,
t=0.003 m, w=1 m → A_c=3e-3 m², P≈2 m → m=19.24 m⁻¹, mL=0.962 →
**η ≈ 0.775**, **θ_tip/θ_b ≈ 0.666** (derived here from the formula above; the
authored YAML will recompute + show the derivation, not hard-code a magic number).

**⚠️ OPEN DECISION (charter-level — needs your ratification):** the fin closed-form
assumes a *uniform, known* convection coefficient `h` on the fin surface. Two ways
to use it as a CHT coverage case:

- **W3.3a · solid-side verification (smaller, cleaner)** — single solid region with
  an imposed convective BC `h`; verify the solid conduction + the coupling-BC
  machinery against the exact η / tip-temp. Honest + analytical, but does NOT
  exercise the fluid region (so it verifies the *conjugate coupling BC*, not the
  full two-region solve).
- **W3.3b · full conjugate (bigger)** — mesh the fluid, let the solve PRODUCE `h`,
  validate against the pipe/Gnielinski correlation at 10% (Schmid precedent). This
  is the "real" coverage=2 flip but the reference is a correlation, not analytical.

**My recommendation:** do **W3.3a first** (analytical, de-risks the gate wiring +
the per-region QoI extraction with an exact reference), then **W3.3b** for the
formal coverage=2 flip. This mirrors the RANS arc (lid-driven-cavity analytical-ish
first, then richer cases). If you'd rather go straight to the full conjugate flip,
we skip to W3.3b (more solver-tuning risk, correlation tolerance).

## 4. Draft gold-standard contract (in-doc; NOT yet committed to knowledge/)

```yaml
# knowledge/gold_standards/cht_straight_fin.yaml  (DRAFT — pending §3 ratify)
case_id: cht_straight_fin_adiabatic_tip
source: "Incropera & DeWitt, Fundamentals of Heat and Mass Transfer, 7th ed., §3.6, Table 3.4"
literature_doi: "ISBN 978-0470501979"   # textbook; analytical, no DOI
gate_mode: cht_analytical               # new analogue of nasa_integrated (§5)
observables:
  - quantity: fin_efficiency
    reference_values: [{ value: 0.775 }]     # = tanh(mL)/(mL), mL=0.962 (derived, §3)
    tolerance: { mode: relative, value: 0.05 }
    derivation: "eta = tanh(mL)/(mL); m=sqrt(hP/(k*Ac)); inputs in case_info"
  - quantity: tip_temperature_ratio
    reference_values: [{ value: 0.666 }]     # = 1/cosh(mL)
    tolerance: { mode: relative, value: 0.05 }
case_info:
  k_solid: 180; h_conv: 100; L: 0.05; t: 0.003; w: 1.0
  flow_type: conjugate; steady_state: true; radiation: false
physics_contract:
  geometry_assumption: "1 solid fin region; uniform h convective BC (W3.3a) — fluid not solved"
  physics_precondition:
    - condition: "steady conduction in solid, foamMultiRun multi-region path"
      satisfied_by_current_adapter: true
      evidence_ref: "src/foam_agent_adapter.py:_execute_cht_multi_region (DEC-225)"
  contract_status: "SOLID_SIDE_VERIFICATION_ONLY (W3.3a)"
```

## 5. Implementation surgical map (after §3 ratified)

1. **CHT QoI extractor** — add a per-region extractor that computes fin_efficiency
   + tip-temperature-ratio from the foamMultiRun result (solid-region T field +
   base/tip sampling). Mirror the RANS QoI path
   (`ui/backend/audit/cfdtrust/audit/qoi.py`) but region-aware.
2. **gate_mode `cht_analytical`** — register in the comparator alongside
   `nasa_integrated`; reuse `GoldStandardComparator.compare()` + G-gates unchanged.
3. **Author** `knowledge/gold_standards/cht_straight_fin.yaml` (the ratified
   benchmark; values recomputed from the formula, derivation shown).
4. **Live run** the fin case through the adapter (foamMultiRun, OF11 — proven in
   W3.2b), extract QoI, compare → assert PASS within 5%.
5. **Coverage test** — `tests/p3/test_cht_coverage_gate.py` asserting the benchmark
   PASS (+ an opt-in `CFD_LIVE_OF11` live variant), mirroring `test_e2e_mock.py:75`.
6. **Flip coverage 1→2** in the coverage ledger ONLY after the live PASS; update
   STATE/Blueprint. Full Codex round-cap=3 chain on the gate code.

## 6. Four-question gate (pre-check)

- LLM offline ✓ (analytical reference + deterministic solver + comparator; no AI).
- Artifacts ✓ (real OpenFOAM multi-region case + solver log + extracted QoI).
- TrustGate-explainable ✓ (PASS/BLOCK from a published/analytical reference + tol).
- Advisory-only ✓ (deterministic gate; AI not in the loop).

## Sources
- Schmid et al., *Simulation of Conjugate Heat Transfer in Thermal Processes with
  Open Source CFD*, ChemEngineering 3(2):59, 2019 — https://www.mdpi.com/2305-7084/3/2/59
- OpenFOAM CHT validation cases (Saitoh 1993 benchmark), Zenodo —
  https://zenodo.org/records/7635861
- SimFlow CHT pipe validation — https://help.sim-flow.com/validation/heat-transfer-at-pipe-CHT
- Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer*, §3.6 (extended surfaces / fin efficiency).
