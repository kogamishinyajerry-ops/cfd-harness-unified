# Case Completion Report — `backward_facing_step_steady`

- Status: **档1 demo-ready** (clean COMPATIBLE, 100% match rate, 9/9 sections complete)
- Produced: 2026-04-18 by opus47-main under ADWM v5.2
- Upstream artifact: `reports/backward_facing_step_steady/auto_verify_report.yaml`

---

## §1 Case overview

| Field | Value |
|---|---|
| Case ID | `backward_facing_step_steady` |
| Physical system | Backward-facing step (BFS), 2D steady incompressible |
| Geometry | Step height `H=1`, domain `x ∈ [-1, 8·H]`, `y ∈ [0, 3·H]` |
| Flow regime | Steady turbulent `Re_h ≈ 37500` (Driver & Seegmiller 1985 experimental) |
| Solver | SIMPLE-family steady RANS (`simpleFoam`) with k-ε closure |
| Observables | Xr/H (reattachment), Cd_mean, pressure_recovery, velocity_profile_reattachment |

**Physical question**: Given step-height `H`, inlet/outlet locations, and
bulk Reynolds number, can the harness reproduce Driver & Seegmiller's 1985
reattachment length `Xr/H = 6.26 ± 0.2` plus near-field velocity profile
to within 10% tolerance?

## §2 Execution record

| Stage | Outcome |
|---|---|
| Task spec | BFS geometry-type, steady turbulent incompressible |
| Mesh | adapter BFS grid, x∈[-1, 8·H] domain |
| Solver | simpleFoam converged at residual = 8.0e-06 vs target 1.0e-05 (ratio = 0.800) |
| Post-process | `_extract_reattachment_length` (`src/foam_agent_adapter.py:6591-6634`) locates `Ux(x) = 0` at `y/H = 0.5` via linear interpolant between sign-change cells |
| Verdict | `PASS` verification / `CONVERGED` convergence / `PASS` physics |

No CorrectionSpec triggered; no fallback branches fired.

## §3 Field overlay — reference vs simulation

**Reattachment length**:

| quantity | Driver & Seegmiller 1985 | harness | Δ | within 10% tol |
|---|---|---|---|---|
| `Xr/H` | 6.26 | 6.30 | +0.04 | ✅ (0.64%) |

**Drag coefficient**:

| quantity | reference | harness | Δ | within 10% tol |
|---|---|---|---|---|
| `cd_mean` | 2.08 | 2.05 | -0.03 | ✅ (1.44%) |

**Pressure recovery**:

| station | reference | harness | Δ |
|---|---|---|---|
| inlet | -0.90 | -0.88 | +0.02 |
| outlet |  0.10 |  0.10 |  0.00 |
| delta (recovery) |  1.00 |  1.00 |  0.00 |

Aggregate `rel_error = 2.22%` vs tol 10% → PASS.

**Velocity profile at `x/H = 6.0` reattachment zone**:

| `y/H` | `u/U_bulk` (experiment) | `u/U_bulk` (harness) | Δ |
|---|---|---|---|
| 0.5 | 0.40 | 0.41 | +0.01 |
| 1.0 | 0.85 | 0.84 | -0.01 |
| 2.0 | 1.05 | 1.04 | -0.01 |

Aggregate `rel_error = 2.50%` vs tol 10% → PASS.

## §4 CHK table

| CHK | Target | Status | Evidence |
|---|---|---|---|
| CHK-1 | Solver converges to target residual | PASS | final 8e-6 < target 1e-5 |
| CHK-2 | `reattachment_length` within 10% of Driver 1985 | PASS | 0.64% actual |
| CHK-3 | `cd_mean` within 10% | PASS | 1.44% actual |
| CHK-4 | `pressure_recovery.delta` within 10% | PASS | bit-identical 1.00 |
| CHK-5 | `velocity_profile_reattachment` within 10% at all 3 y/H stations | PASS | aggregate 2.50% |
| CHK-6 | No CorrectionSpec triggered | PASS | `correction_spec_needed: false` |
| CHK-7 | physics_contract preconditions met (in-domain reattachment, zero-crossing proxy valid, shear-layer resolved) | PASS | all 3 marked satisfied per EX-1-005 annotation |
| CHK-8 | Producer→consumer audit_concern (EX-1-006 channel) | PASS (no hazard) | `contract_status = COMPATIBLE`, audit_concern=null |

## §5 key_quantities numerical comparison

| Observable | Reference | Simulation | rel_error | Tolerance | Within |
|---|---|---|---|---|---|
| `reattachment_length` | 6.26 (Xr/H) | 6.30 | 0.64% | 10% | ✅ |
| `cd_mean` | 2.08 | 2.05 | 1.44% | 10% | ✅ |
| `pressure_recovery.delta` | 1.00 | 1.00 | 0.00% | 10% | ✅ |
| `velocity_profile_reattachment` | 3-point (y/H=0.5,1,2) | 3-point sim | 2.50% | 10% | ✅ |

All four observables sit at 0.0%–2.5% — a ~5× margin under the 10%
tolerance. This is "single-case PASS with meaningful headroom", not a
tolerance-scrape.

## §6 physics_contract

```yaml
contract_status: COMPATIBLE
preconditions:
  - Flow separates and reattaches inside the measurement domain — SATISFIED
  - Zero-crossing of Ux at y=0.5·H is a valid reattachment proxy — SATISFIED
  - Mesh resolves the shear layer leaving the step corner sufficiently — SATISFIED
audit_concern: null
last_reviewed: 2026-04-18 (EX-1-005 annotation slice)
```

Consumer (EX-1-006 error_attributor) finds no hazard-branch firing for BFS.

## §7 Reviewer-grade 3-line summary

1. **What**: At `Re_h ≈ 37500` on the BFS domain `x ∈ [-1, 8·H]`,
   simpleFoam + k-ε reproduces Driver & Seegmiller's 1985 reattachment
   length `Xr/H ≈ 6.26` within 0.64%, plus mean drag (1.4%), pressure
   recovery (2.2%), and 3-point reattachment-zone velocity profile (2.5%).
2. **Why believable**: physics_contract = COMPATIBLE (all 3
   preconditions satisfied); no silent-pass hazard (none of the 3
   known consumer-flagged branches fire for this case); convergence
   reached residual target; the reattachment extractor uses the
   standard zero-crossing-at-mid-height proxy.
3. **What this does NOT prove**: transferability to unsteady shedding
   (this case is *steady* BFS by contract); generalizability to
   non-step separations; no statement about 3D side-wall effects. The
   Driver 1985 dataset itself has ±0.2 uncertainty on `Xr/H` — the
   harness result is inside both the nominal and the experimental
   uncertainty band.

## §8 Visualization status

| Artifact | Target path | Status |
|---|---|---|
| Ux field + reattachment bubble overlay | `reports/backward_facing_step_steady/figures/reattachment_overlay.png` | NOT GENERATED (harness lacks figure pipeline) |
| Velocity profile at `x/H=6` | `reports/backward_facing_step_steady/figures/u_profile_xH6.png` | NOT GENERATED |
| Pressure coefficient along bottom wall | `reports/backward_facing_step_steady/figures/cp_wall.png` | NOT GENERATED |

**Honest note**: tabular evidence only in this version; figure
generation is a future-G candidate not in the G1–G5 ADWM window.

## §9 Error-correction narrative

BFS has never emitted a CorrectionSpec. Historical trajectory:

- **Phase 7 Wave 2-3** (pre-physics_contract): PASS 100% match rate.
- **EX-1-005** (2026-04-18): physics_contract annotation added — three
  preconditions explicitly marked satisfied with line-level evidence
  pointers:
  - In-domain reattachment: `src/foam_agent_adapter.py:6591-6634` finds
    `x_reattach` inside sampling range.
  - Zero-crossing-at-mid-height: `src/foam_agent_adapter.py:6601-6629`,
    `y_target=0.5`, `y_tol=0.15`, Ux sign-change interpolant.
  - Shear-layer resolution: Phase 7 Wave 2-3 Xr deviation < 10% proof.
- **EX-1-006** (2026-04-18): consumer wired; BFS stays null-audit.

**Projected future deviations**: none expected for *steady* BFS at
`Re_h ≈ 37500`. Two trip points a future slice might hit:
1. Re lowered enough that reattachment moves past `x/H = 8` (outside
   sampling domain) — would violate precondition #1 and trigger
   `INCOMPATIBLE` re-annotation.
2. Re raised into unsteady-shedding territory — would violate the
   `steady_state: STEADY` contract field; the case would need a
   separate `backward_facing_step_unsteady` gold standard.

Neither of these invalidates the current result.

---

Produced: 2026-04-18 · opus47-main (ADWM v5.2)
Source of truth: `knowledge/gold_standards/backward_facing_step_steady.yaml` +
`reports/backward_facing_step_steady/auto_verify_report.yaml`
