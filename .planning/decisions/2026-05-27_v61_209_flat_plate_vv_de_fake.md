---
decision_id: DEC-V61-209
title: P1 cycle-2 — flat-plate V&V de-fake (remove Spalding-fabrication; real U_ref/nu extraction) + exposed non-convergence blocker
status: Proposed
parent_dec: DEC-V61-207 (Blueprint v4 P1) · DEC-V61-208 (Chief Engineer / L2)
phase: Blueprint v4 · P1 · cycle-2 (RANS-aero vertical V&V loop)
notion_sync_status: not_applicable (Proposed — not synced until Accepted)
autonomous_governance: true
confidence: med
date: 2026-05-27
ratified_by: pending (work-in-progress; extraction fix uncommitted, coupled cycle-3 + Codex review outstanding)
---

# DEC-V61-209 · P1 cycle-2 — flat-plate V&V de-fake + non-convergence exposure

## Finding (evidence-backed)

The flat-plate first vertical (`turbulent_flat_plate` / workbench
`flat_plate_rans_sst`) was **not honestly validated**, on three stacked defects:

1. **Fabrication**: `_extract_flat_plate_cf` (`src/foam_agent_adapter.py`) hard-coded
   `U_ref = 1.0` and `nu = 1/Re` (nondimensional assumption). On a dimensional run
   this made `Cf = τ_w/(0.5·U_ref²)` implausible (>0.01), tripping a **Spalding
   fallback** (`Cf = 0.0576/Re_x^0.2`) that **substituted a closed-form value and
   reported it as a measurement** — the bit-identical `0.007600365…` across runs
   and commits (and previously across *cases*, per the 8643-8647 history note).
2. **Wrong-regime gold**: the comparator compares against the laminar Blasius scalar
   `0.0042` (`knowledge/gold_standards/turbulent_flat_plate.yaml`, regime-corrected by
   DEC-V61-006), not the case's own turbulent **NASA TMR SST CFL3D Cf(x)** reference
   (`reference/cf_reference.csv`, SHA-pinned, ~0.0024–0.0038).
3. **Non-convergence (the real blocker, exposed by fixing #1)**: with the fabrication
   removed, the honest extracted Cf is `6.59e-07` from a solution whose **cumulative
   continuity error is 29** (DEC-V61-036b G5 gate) — the solver does **not converge**.
   The Spalding fallback had been **masking a divergent solution** with a plausible fake.

   **Divergence root cause (cycle-3 diagnosis, evidence from run key_quantities)**:
   the case is generated **nondimensional** (inlet-U=1 convention, `foam_agent_adapter.py:91`;
   `nu = 1/Re = 2e-5`, Re=50000) **with kΩSST turbulence on** — regime-incoherent — and
   the steady solve **blows up**: the run reports `cf_u_ref = 682.018` (freestream
   reached 682 m/s, 682× the intended U=1) and `cf_nu = 2e-5`. The extraction is correct;
   the *solution* is divergent garbage. Adapter solves in **OpenFOAM 10 Foundation**
   (`/opt/openfoam10/etc/bashrc`); the static workbench case `flat_plate_rans_sst`
   (U=30 dimensional, Re_L=2e6 — coherent) is a separate OF11-flavored track. Relaxation
   is SIMPLEC `consistent=yes`, U=0.9 / p=0.3, residualControl 1e-5.

## What landed in this cycle (uncommitted WIP)

`_extract_flat_plate_cf` rewritten (truth-chain fix):
- `U_ref` = freestream `max|Ux|` from the actual field (dimensional).
- `nu` read from the case `constant/{physicalProperties,transportProperties}` the
  solver used (no `1/Re` nondimensional assumption; honest failure if unreadable).
- **Spalding fabrication removed**: `Cf > 0.01` is recorded as an *unreliable
  diagnostic* and excluded — never substituted as a measured value. If no plausible
  Cf survives, emit `cf_extraction_failed` + reason, never a fabricated number.

This is a strict truth-chain improvement (removes a fabrication, surfaces honest
failure + the real non-convergence signal). Its **correctness cannot be validated
until the case converges** (a Cf from a divergent field is meaningless), so it is
**coupled** to cycle-3 and intentionally not committed alone.

## Remaining plan (coupled)

- **cycle-3 (the real P1 hardening)**: make the kΩSST flat plate **converge** to a
  steady solution — reconcile regime coherence (Re / U / turbulence model / dimensional
  vs nondim), mesh y+ / wall treatment, relaxation, turbulence BC init. Exit: continuity
  error within gate + a physically-plausible Cf(x).
- **fix B (gold repoint)**: compare against NASA TMR SST Cf(x) at matched x-stations
  (or, minimally, set the scalar gold at `x_target` to the NASA TMR value, e.g.
  `Cf≈0.00296` at x=0.5) — turbulent regime, not the laminar `0.0042`.
- **validate**: real run → extracted Cf(x) ≈ NASA TMR within 10% → honest PASS (or
  honest FAIL with quantified error = a real y+/mesh signal).
- **then**: update the stale `0.0076` fixtures + any `cf_spalding_fallback_count` test
  refs, **Codex review** (correctness-critical V&V — round cap=3), commit, flip
  `trust_report` MOCKED→real, merge the workbench/phase5 dual track, → Status=Accepted.

## VALIDATED — V&V loop closes (cycle-3 manual proof, 2026-05-27)

Controlled manual runs (OF10 Foundation Docker, `openfoam/openfoam10-paraview56`,
case copied to `/private/tmp/p1_fp` — no repo churn) **proved the V&V loop closes**:

- The **nondim Re=50000 + kΩSST** case (what the adapter generates,
  `foam_agent_adapter.py:4136-4138` `Re=50000, nu=1/Re, U_bulk=1`) **diverges**
  (freestream → 682 m/s). The divergence is the regime-incoherent generated setup.
- The **coherent dimensional static workbench case** (U=30, kΩSST) **converges**
  in 159 iters (continuity ~1e-6). Real wallShearStress → physical Cf ~0.0015–0.0057.
- Reconciled to **NASA conditions (Re/unit = 5×10⁶, ν=6e-6)**: converges in 170 iters,
  and **Cf(x) matches the NASA TMR SST CFL3D reference within 1.4% across the
  developed plate** (x≥0.2, NASA-standard LE exclusion); leading edge (x=0.11) 12.8%.
  y+≈120 (wall-function regime; kΩSST all-y+ treatment still nails Cf).

**Proven recipe**: dimensional coherent case + U/ν giving Re/unit=5e6 + the existing
blockMesh (100×60, simpleGrading 1 50 1) + kΩSST → converged + NASA-matched.
This de-risks P1: runnable + validated is demonstrably achievable for the vertical.

## Remaining for the PRODUCT (adapter wiring — next cycle)

The proof was via controlled manual runs. To make the **adapter's automated path**
converge + validate (so `trust_report` flips MOCKED→real PASS):

1. **Fix adapter case-gen** for `turbulent_flat_plate` (`foam_agent_adapter.py:4124-4138`):
   generate a **coherent case** (dimensional, Re/unit=5e6 NASA conditions, U_bulk=1
   nondim is acceptable IF the BC/turbulence init converge — but the static case's
   BC set is proven; prefer matching it) instead of the divergent nondim Re=50000 setup.
2. **Validate the extraction fix** (already WIP) end-to-end through the adapter on the
   now-converged case → expect physical Cf(x), not the old fake 0.0076 / 6.59e-07.
3. **fix B gold repoint**: compare Cf(x) against NASA TMR `reference/cf_reference.csv`
   (turbulent, matched x), not the laminar scalar 0.0042; LE-exclude per NASA practice.
4. Update stale `0.0076` fixtures + `cf_spalding_fallback` test refs; **Codex review**
   (correctness-critical V&V); commit; `trust_report` MOCKED→real PASS; merge dual track.
5. Optional accuracy: refine near-wall to y+~1 (NASA-canonical) — but 1.4% at y+~120
   already clears the gate.

## Governance

- Four-question gate: (1) LLM-offline ✅ (deterministic extraction, no AI) (2) artifacts
  ✅ (audit_real_run_measurement.yaml + raw run) (3) TrustGate ✅ (reports honest
  failure + continuity gate) (4) advisory-only ✅ (no mutating route). Passes.
- Correctness-critical V&V change → **Codex review required before commit** (deferred
  until the coupled fix is validatable on a converged case).
- Driven autonomously by `cfd-chief-engineer` at L2 (DEC-V61-208); guardrails intact.

---

## ADDENDUM — cycle-3b/3c: MOCKED→real flipped, honest FAIL verdict (2026-05-27)

The coupled fix is now validatable on a **converged real run through the cfdtrust
pipeline** (not just a manual side-run). Three things landed:

1. **Case Re coherence** (committed `bde7cae`): `transportProperties` ν 1.5e-5→6e-6
   ⇒ Re/unit = U/ν = 30/6e-6 = 5×10⁶ = NASA TMR canonical. Provenance + manifest
   updated honestly.
2. **y+~1 mesh** (`system/blockMeshDict`): `hex (100 60 1) simpleGrading (1 50 1)` →
   `(180 90 1)` with LE-clustered x (multiGrading bounds max aspect ratio at 260.9 <
   1000 manifest cap) + y-grading 1724 for y+~1. **checkMesh-clean** (the manifest
   declares `checkmesh_required: true`, so a fail-checkMesh grid was not acceptable).
3. **Backend flip** (`case_manifest.yaml`): `solver_backend: mocked → openfoam`. This
   re-routes `solver.execute()` to the real Docker simpleFoam path (proven by
   `channel_flow_rans_sst`, real PASS) **and** unlocks the real NASA TMR Cf(x)
   comparison at `qoi.py:118` (SHA-gated, x<0.01 LE-excluded). No new comparator code
   was needed — `flat_plate_cf.compare_against_reference` already does per-x
   interpolation vs `reference/cf_reference.csv`.

**Real-run result (OpenFOAM, converged @ iter 397, y+ avg 1.31):** the
`trust_report` now carries the **honest V&V signal**, and that signal is
**`overall_status: FAIL`** — not a mock, not a fabrication:
- developed band (x ≥ 0.2): **3.17%** error — inside the 10% gate ✅
- near-LE on-plate (x ≥ 0.05): **5.56%** error — inside gate ✅
- **leading-edge singularity band (7 points, x = 0.0129–0.0352): 10–26% error** ❌
  — these are within `x_min_compare_m = 0.01` so the gate (correctly) counts them,
  and they fail. This is the laminar-LE / mesh-under-resolution band where a steady
  SST RANS on this topology cannot match the CFL3D curve.

**The de-fake is honest and complete; the verdict is a real FAIL on the LE band.**
The P1 sub-goal "flip MOCKED→real" is achieved. The further sub-goal "real PASS" is
**not** achieved and **must not be forced silently**.

4. **Stale tests rewritten** (this commit): the 2 tests in
   `tests/test_foam_agent_adapter.py` that pinned the removed Spalding contract
   (`cf_spalding_fallback_activated is True`, `cf == 0.0576/Re_x^0.2`,
   `cf == 4e-05`) are replaced by (a) an honest-failure test (asserts
   `cf_extraction_failed` when ν is unreadable; no fabricated `cf_skin_friction`)
   and (b) a positive test exercising the real success branch (ν read from
   `constant/transportProperties`, U_ref = max|Ux|, physically-plausible Cf). This
   resolves Codex R0's sole P1 blocker.

### PENDING — Chief Engineer / sponsor decision: the →PASS path (do NOT do silently)

To move the verdict from honest-FAIL to PASS, exactly one of:
- **(a) Document the LE-singularity exclusion**: raise `x_min_compare_m` 0.01 → ~0.05
  *with* a provenance + DEC note citing NASA TMR's own LE-exclusion practice. This is
  legitimate V&V scoping (the LE singularity is a known, standard exclusion) **only**
  when documented; doing it to "make the number pass" without the physical rationale
  would be tolerance-gaming and is forbidden by the standing guardrail.
- **(b) Add a leading symmetry pre-plate** (NASA TMR topology) so the boundary layer
  develops before x=0 — more faithful to the reference setup, more work, no tolerance
  change.

This addendum commits the **honest real-FAIL baseline**. Status stays **Proposed**
until the →PASS path is chosen and validated (then Accepted + Notion sync).
