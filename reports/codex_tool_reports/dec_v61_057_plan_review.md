# DEC-V61-057 · Codex Pre-Stage-A Plan Review

**Reviewer**: Codex GPT-5.4 (xhigh reasoning)
**Date**: 2026-04-25 22:43 +0800
**Workdir**: cfd-harness-unified @ commit e7909ac (pre-Stage-A)
**Tokens used**: 199,208

## Verdict

**REQUEST_CHANGES** · Stage A NO_GO until v1 → v2 edits applied.

| | Findings |
|---|---|
| HIGH | 3 |
| MED  | 2 |
| LOW  | 1 |
| Estimated pass-rate after edits | 0.55 |

## Findings

### F1-HIGH · Canonical DHC contract is not actually established before extractor work

**File refs**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:125-135,142-156,218-227,303-318` (v1 batch_plan understated scope)
- `knowledge/gold_standards/differential_heated_cavity.yaml:6-25`
- `knowledge/whitelist.yaml:149-175`
- `src/foam_agent_adapter.py:2063-2091` (Ra<1e9 → AR=2.0 dispatch trap)
- `src/foam_agent_adapter.py:2323-2328` (RAS/kOmegaSST hard-write)
- `src/foam_agent_adapter.py:2895-3095` (turbulence-field initial conditions hard-written for laminar regime)
- `tests/test_foam_agent_adapter.py:1427-1440` (test bakes Ra=1e6 → AR=2.0)
- `ui/backend/tests/fixtures/runs/differential_heated_cavity/mesh_80_measurement.yaml:1-20`
- `ui/backend/tests/fixtures/runs/differential_heated_cavity/reference_pass_measurement.yaml:12-28`

**Finding**: Intake assumed DHC at Ra=1e6 baseline is square + laminar + wall-graded. Live state:
- Adapter dispatch routes Ra<1e9 to `aspect_ratio = 2.0` (rayleigh_benard branch), ignoring whitelist `parameters.aspect_ratio = 1.0`.
- Adapter natural-convection emits `simulationType RAS` with `kOmegaSST` regardless of `whitelist.turbulence_model = laminar`.
- Mesh is `80²` uniform (no grading); BL resolution at Ra=1e6 = 2.56 cells, below 5-cell minimum.
- Plumbing test locks the wrong default into the suite.

If Stage B builds extractors against this contract, every Nu/u/v/ψ measurement is fighting the wrong geometry/solver/mesh.

**Required edit (applied in v2 §7 Batch A)**: Expand Batch A from 2 commits → 5 commits:
- A.1 dispatch fix + test update (case_id-aware AR resolution)
- A.2 laminar emit fix (consult whitelist turbulence_model)
- A.3 mesh upgrade (extend high-Ra grading branch to DHC Ra=1e6, ≥5 BL cells)
- A.4 validation-artifact lineage repair (regen `auto_verify_report.yaml`)
- A.5 integration smoke

Also corrected stale reference `whitelist_cases/...` → `knowledge/whitelist.yaml`.

### F2-HIGH · Report drift is mis-scoped; the stale source is `auto_verify_report.yaml`, not `report.md`

**File refs**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:158-172,305-310` (v1 mis-located the bug)
- `reports/differential_heated_cavity/report.md:20-31` (rendered ref=8.8)
- `reports/differential_heated_cavity/auto_verify_report.yaml:17-30,39-50` (stale ref=30.0/sim=5.85, commit c3a1a4c, 2026-04-18 — pre-demotion)
- `ui/backend/tests/fixtures/runs/differential_heated_cavity/audit_real_run_measurement.yaml:19-28,35-37` (third source, ref=8.8 actual=11.4)
- `src/report_engine/generator.py:88-100`
- `templates/partials/gold_standard_ref.md.j2:6-9`
- `templates/partials/results_comparison.md.j2:3-9`

**Finding**: Three-way split — gold YAML (8.8), `auto_verify_report.yaml` (30.0/5.85), audit fixture (11.4/8.8). Templates `gold_standard_ref.md.j2` and `results_comparison.md.j2` consume different upstream pipeline stages, so a single rendered `report.md` shows different reference values across its tables.

Fixing `report.md` directly is the wrong layer — the source is the renderer's data feed.

**Required edit (applied in v2 §4 risk_flags + §7 Batch A.4)**:
- Renamed Batch A item: `report.md ref-cell inconsistency fix` → `validation-artifact lineage repair`
- Added 3-way invariant test:
  ```
  gold YAML ref_value  ==  auto_verify_report.gold_standard_comparison.observables[].ref_value  ==  report.md/html reference cell
  ```
  (byte-identical, not just within tolerance)

### F3-HIGH · `stream_function_max` declared before scaling and gate status are correctly defined

**File refs**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:115-123,174-188,291-295,321-325` (v1 §3 missing nondim formula; v1 §6 had `psi via L*α` which is wrong dimensionally)
- `knowledge/schemas/risk_flag_registry.yaml:116-121` (numerical_noise_snr flag)
- `knowledge/gold_standards/lid_driven_cavity.yaml:79-85` (LDC ψ precedent)

**Finding**: Raw `ψ = ∫u dy` has units m²/s. Intake §3 had no scaling formula; §6 listed `psi via L*α` — incorrect dimensionally. ψ has been declared as a hard gate while §4 also says "may demote to advisory if SNR fails" — Batch C wiring was inconsistent with provisional status.

**Required edit (applied in v2 §3 observable_scope + §7 Batch C)**:
- Explicit scaling: `psi_raw = ∫₀ʸ u(x, y') dy'`, `psi_nondim = psi_raw / α`
- Gate status: `PROVISIONAL_ADVISORY` until B3 closure-residual + SNR validates (not hard-wired in Batch C)
- Closure residual gate: `(ψ_top - 0) / |psi_max_gold| < 1e-2` else demote
- B3 prototype is trapezoidal first; Poisson solve `∇²ψ = -ω_z` reserved as fallback sub-batch

### F4-MED · Type-I independence claim overstated

**File refs**: `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:23-50,87-124`

**Finding**: v1 said "Five physically-independent scalar gates". The text itself acknowledged Nu_avg and Nu_max share the hot-wall gradient field with different reduction operators — that's a same-surface cross-check family, not a separate physical family.

**Required edit (applied in v2 §1)**:
- Reframed: "5 scalar gates planned; ≥3 independent families exist"
- Family 1 = wall-gradient (Nu_avg + Nu_max as same-surface)
- Family 2 = interior velocity profile (u_max + v_max sampleSet)
- Family 3 = stream-function (ψ post-process)
- Type I claim survives even if Nu_max collapses or ψ demotes

### F5-MED · Round budget too optimistic

**File refs**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:303-345` (v1 codex_budget_rounds=3)
- `.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml:231-287` (v2 precedent bumped to 4)

**Finding**: V61-053 (cylinder Type I) had to raise budget 3 → 4 once batch split materialized. V61-057 has more concrete scope (contract repair + 3 new extractor families + ψ provisional path) yet kept budget at 3.

**Required edit (applied in v2 §8)**: `codex_budget_rounds: 3 → 4`. Round 4 = normal planned checkpoint, NOT early halt. Round 5 = halt risk_flag check. Round 6 = force abandon.

### F6-LOW · Strict template hygiene inconsistent

**File refs**:
- `.planning/intake/DEC-V61-057_differential_heated_cavity.yaml:153-155` (4 case-specific flags not in registry)
- `.planning/intake/TEMPLATE.yaml:72-76` (registry-strict directive)
- `knowledge/schemas/risk_flag_registry.yaml:11-12,22-152`
- `docs/specs/KNOWLEDGE_OBJECT_MODEL.md:36-37`

**Finding**: Template directive says all `flag:` values must exist in the registry; intake adds 4 case-specific flags (`ra_aspect_ratio_dispatch_inversion`, `turbulence_emit_vs_whitelist_mismatch`, `mesh_resolution_at_ra_1e6_marginal`, `validation_artifact_lineage_drift`) that aren't yet registered. v1 also referenced nonexistent `whitelist_cases/...` path.

**Required edit (applied in v2 §3 NOTE + §4)**:
- Added strictness-scope NOTE: registry strictness applies only to MANDATORY v2.0+ slots; case-specific flags documented inline pending eventual promotion (deferred to ≥3-case threshold to avoid premature canonicalization).
- Whitelist path corrected: `knowledge/whitelist.yaml` (no `whitelist_cases/...` references).

## v1 → v2 Disposition

All 6 required edits applied. v2 intake committed; Codex re-review pending to confirm APPROVE_PLAN_WITH_CHANGES (or APPROVE_PLAN). Stage A on hold until re-review verdict.
