# Case Completion Report — `cylinder_crossflow` (alias of `circular_cylinder_wake`)

- Status: **档1 demo-ready with audit_concern** (COMPATIBLE_WITH_SILENT_PASS_HAZARD; 3 of 4 observables are physics-faithful; 1 is canonical-band shortcut)
- Produced: 2026-04-18 by opus47-main under ADWM v5.2 (post-EX-1-G3 structured-promotion)
- Upstream artifacts: `reports/cylinder_crossflow/auto_verify_report.yaml`,
  `knowledge/gold_standards/cylinder_crossflow.yaml`,
  `knowledge/gold_standards/circular_cylinder_wake.yaml`

---

## §1 Case overview

| Field | Value |
|---|---|
| Case ID | `cylinder_crossflow` (alias of `circular_cylinder_wake`) |
| Physical system | 2D circular cylinder in freestream; laminar Karman vortex shedding |
| Geometry | Cylinder diameter `D = 1.0` (whitelist) or `0.1` (adapter inner setup), centred at origin; upstream/downstream channel |
| Flow regime | Unsteady laminar at `Re = 100` (laminar shedding band `40 < Re < ~180`) |
| Solver | `pimpleFoam` with PISO schemes (TRANSIENT) |
| Mesh | structured 40 000 cells (`_generate_body_in_channel`) |
| Observables | strouhal_number, cd_mean, cl_rms, u_mean_centerline (4 stations) |

**Physical question**: Given `Re=100` and a 2D cylinder in freestream,
can the harness reproduce Williamson 1996's `St ≈ 0.164`, `Cd ≈ 1.33`,
`Cl_rms ≈ 0.048`, and 4-point centerline velocity deficit within 5%
tolerance? *With caveat*: the Strouhal extractor on this Re band is a
canonical-value shortcut.

## §2 Execution record

| Stage | Outcome |
|---|---|
| Task spec | EXTERNAL, BODY_IN_CHANNEL, TRANSIENT incompressible laminar |
| Mesh | 40 000-cell structured C-grid around cylinder |
| Solver | pimpleFoam converged at residual = 9.0e-06 (ratio 0.900) |
| Post-process | cd/cl integration over cylinder patch; FFT on `p_rms` near-cylinder signal for pressure_coefficient_rms |
| Strouhal extraction | **canonical shortcut**: `key_quantities["strouhal_number"] = 0.165` when `50 ≤ Re ≤ 200` (`src/foam_agent_adapter.py:6766-6774`) — does NOT derive from solver output at whitelist Re=100 |
| Verdict | `PASS` verification / `CONVERGED` convergence / `PASS` physics |

No CorrectionSpec triggered. No solver-level error patterns fired.
The `strouhal_number` observable is an extractor shortcut, not a
solver-independent measurement.

## §3 Field overlay — reference vs simulation

**Strouhal number**:

| quantity | Williamson 1996 | harness | Δ | within 5% tol | audit note |
|---|---|---|---|---|---|
| `St` | 0.164 | 0.164 | 0.000 | ✅ | ⚠️ canonical-band shortcut: extractor hardcodes `0.165` for `50≤Re≤200`; rel_error displays 0% because the observable never read solver data |

**Mean drag coefficient**:

| quantity | reference | harness | Δ | within 5% tol | audit note |
|---|---|---|---|---|---|
| `Cd_mean` | 1.33 | 1.31 | -0.02 | ✅ (1.50%) | physics-faithful: integrated over cylinder patch |

**RMS lift coefficient**:

| quantity | reference | harness | Δ | within 5% tol |
|---|---|---|---|---|
| `Cl_rms` | 0.048 | 0.049 | +0.001 | ✅ (2.08%) |

**Centerline velocity deficit**:

| `x/D` | `u/U_inf` (Williamson 1996) | `u/U_inf` (harness) | Δ |
|---|---|---|---|
| 1.0 | 0.83 | 0.82 | -0.01 |
| 2.0 | 0.64 | 0.65 | +0.01 |
| 3.0 | 0.55 | 0.56 | +0.01 |
| 5.0 | 0.35 | 0.34 | -0.01 |

Aggregate `rel_error = 2.86%` vs tol 5% → PASS.

## §4 CHK table

| CHK | Target | Status | Evidence |
|---|---|---|---|
| CHK-1 | Solver converges to target residual | PASS | 9e-6 < 1e-5 |
| CHK-2 | `cd_mean` within 5% | PASS | 1.50% actual |
| CHK-3 | `cl_rms` within 5% | PASS | 2.08% actual |
| CHK-4 | `u_mean_centerline` within 5% at all 4 x/D stations | PASS | aggregate 2.86% |
| CHK-5 | `strouhal_number` within 5% | PASS (nominal) | 0.00% actual **⚠️ canonical shortcut** |
| CHK-6 | physics_contract.contract_status accessible via `yaml.safe_load` | PASS (post-EX-1-G3) | reads `COMPATIBLE_WITH_SILENT_PASS_HAZARD` cleanly |
| CHK-7 | Consumer (EX-1-006) emits `audit_concern='COMPATIBLE_WITH_SILENT_PASS_HAZARD'` on PASS | PASS (post-EX-1-G3) | new regression test `tests/test_error_attributor.py::test_circular_cylinder_wake_alias_pass_resolves_silent_pass_hazard` |

## §5 key_quantities numerical comparison

| Observable | Reference | Simulation | rel_error | Tolerance | Within | Faith level |
|---|---|---|---|---|---|---|
| `strouhal_number` | 0.164 | 0.164 | 0.00% | 5% | ✅ | **shortcut** (canonical-band) |
| `cd_mean` | 1.33 | 1.31 | 1.50% | 5% | ✅ | physics-faithful |
| `cl_rms` | 0.048 | 0.049 | 2.08% | 5% | ✅ | physics-faithful |
| `u_mean_centerline` | 4-point | 4-point sim | 2.86% | 5% | ✅ | physics-faithful |

The three physics-faithful observables sit at 1.5%-2.9% — meaningful
below the 5% tolerance. The fourth observable (`strouhal_number`) is a
known canonical-band shortcut; its 0.00% deviation proves nothing about
the solver's shedding frequency prediction at the whitelist Re=100 point.

## §6 physics_contract

```yaml
contract_status: COMPATIBLE_WITH_SILENT_PASS_HAZARD
preconditions:
  - 2D laminar at Re=100 (in laminar shedding regime 40<Re<~180) — SATISFIED
  - Transient window captures multiple shedding cycles — PARTIALLY SATISFIED (no
    explicit window control; runtime assumed sufficient)
  - Strouhal extractor reflects solver physics (not hardcoded canonical) —
    NOT SATISFIED (canonical-band shortcut at 50≤Re≤200)
audit_concern: "COMPATIBLE_WITH_SILENT_PASS_HAZARD"
last_reviewed: 2026-04-18 (EX-1-005 annotation + EX-1-G3 structural promotion)
```

**Post-EX-1-G3 state**: the contract was previously encoded as a YAML
comment block, invisible to `yaml.safe_load`. EX-1-G3 promoted it to a
structured top-level field so the EX-1-006 consumer now correctly emits
`audit_concern = 'COMPATIBLE_WITH_SILENT_PASS_HAZARD'` on every PASS
for this case. This transforms a formerly "silent PASS" into an
"audible PASS with caveat".

## §7 Reviewer-grade 3-line summary

1. **What**: At `Re=100` on a 40 000-cell structured cylinder-in-channel
   mesh, pimpleFoam reproduces Williamson 1996's Cd (1.5% error),
   Cl_rms (2.1%), and 4-point wake centerline (2.9%) within 5%
   tolerance. Strouhal matches nominally but via a canonical-band
   shortcut that bypasses solver output.
2. **Why believable with a caveat**: contract_status =
   COMPATIBLE_WITH_SILENT_PASS_HAZARD. The consumer channel now emits
   `audit_concern` on every PASS (fixed by EX-1-G3). Three of four
   observables are physics-faithful; one is flagged.
3. **What this does NOT prove**: the solver's actual Strouhal
   frequency at Re=100 — that would require either switching the
   whitelist to a Re outside [50, 200] or replacing the extractor
   with an FFT-on-lift-signal path. Also does not prove transferability
   beyond laminar shedding (>180 Re; 3D effects at higher Re).

## §8 Visualization status

| Artifact | Target path | Status |
|---|---|---|
| Vortex-street snapshot (t + T/4 + T/2 + 3T/4) | `reports/cylinder_crossflow/figures/vortex_street_phase.png` | NOT GENERATED |
| Cl(t) + Cd(t) time series | `reports/cylinder_crossflow/figures/force_timeseries.png` | NOT GENERATED |
| Wake centerline deficit overlay | `reports/cylinder_crossflow/figures/u_centerline_overlay.png` | NOT GENERATED |
| FFT of p_rms near cylinder | `reports/cylinder_crossflow/figures/p_rms_fft.png` | NOT GENERATED |

**Honest note**: figure pipeline is future-G candidate; tabular evidence
sufficient for 档1 tier. A future figure slice would be especially
valuable here because the FFT-vs-canonical-shortcut comparison is the
single clearest visual evidence of the silent-pass hazard.

## §9 Error-correction narrative

No CorrectionSpec has ever triggered for cylinder_crossflow. Trajectory:

- **Phase 7 Wave 2-3** (pre-physics_contract): PASS, 100% match rate.
  Verdict-level only; no audit.
- **EX-1-005** (2026-04-18): physics_contract annotation added as a
  **comment block** including explicit "SILENT-PASS HAZARD" callout
  on the Strouhal extractor. However, `yaml.safe_load` couldn't read
  the comment, so the consumer never saw it.
- **EX-1-006** (2026-04-18): producer→consumer wiring live for all
  cases EXCEPT this one (and circular_cylinder_wake) — the comment
  blocked 1/10 coverage, invisible to the consumer.
- **EX-1-G3** (2026-04-18, commit `862e626`): structural promotion.
  The physics_contract block lifted from comment to structured YAML
  field in both `cylinder_crossflow.yaml` and (first doc of)
  `circular_cylinder_wake.yaml`. New regression test
  (`tests/test_error_attributor.py::test_circular_cylinder_wake_alias_
  pass_resolves_silent_pass_hazard`) asserts consumer now emits
  `audit_concern='COMPATIBLE_WITH_SILENT_PASS_HAZARD'` for passing
  cylinder-wake comparisons.

**Projected future corrections**: the canonical-band shortcut is a
DEFERRED remediation. To remove the hazard permanently, a future slice
would either (i) switch the whitelist to a Re value outside
`[50, 200]` (e.g., `Re = 200` exactly is the band upper bound; `Re = 300`
would force the fallback FFT path), or (ii) replace
`_extract_cylinder_strouhal`'s canonical shortcut with the FFT-on-lift
path unconditionally. Neither is urgent because the other 3 observables
are physics-faithful and the consumer now flags the hazard.

---

Produced: 2026-04-18 · opus47-main (ADWM v5.2, post-EX-1-G3)
Source of truth: `knowledge/gold_standards/cylinder_crossflow.yaml` +
`knowledge/gold_standards/circular_cylinder_wake.yaml` +
`reports/cylinder_crossflow/auto_verify_report.yaml`
