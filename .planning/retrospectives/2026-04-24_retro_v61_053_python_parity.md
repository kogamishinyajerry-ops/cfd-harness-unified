---
retro_id: RETRO-V61-053
title: DEC-V61-053 cylinder arc · Python version parity + 3-round Codex calibration
date: 2026-04-24
trigger: incident-retro (CHANGES_REQUIRED on R1 AND R2 of same DEC)
related_dec: DEC-V61-053
counter_at_retro: 40
---

## Incident summary

DEC-V61-053 is the first DEC to natively satisfy methodology v2.0 (F1-M1 Stage 0
intake + F1-M2 two-tier close). The arc took **3 Codex rounds** to reach
APPROVE — matching the LDC V61-050 Type I precedent. Two distinct
`CHANGES_REQUIRED` verdicts in the same DEC triggers the
`incident-retro` lane (per CLAUDE.md v6.1 autonomous-governance rules).

Codex round outcomes:

| Round | Verdict | Findings |
|-------|---------|----------|
| Plan (Stage 0) | APPROVE_PLAN_WITH_CHANGES | 7 intake edits: blockage 20%, laminar override, u_deficit semantics, Batch B split, forceCoeffs axis, cylinder_crossflow alias, Batch D preflight |
| R1 (post-B1+B2) | CHANGES_REQUIRED | 1H (count-based windowing) + 3M (residual blockage, mesh coarsening, y/z filter missing) + 1L (stale rename promise) |
| R2 (post-R1-fixes + B3) | CHANGES_REQUIRED | Python 3.9 f-string syntax error + 3 stale doc locations the R1 fix missed |
| R3 (post-R2-fixes) | **APPROVE** | Clean |

Final: 11 commits in the DEC arc, B1+B2+B3+C F1-M2-clean.

## What went right

1. **Intake-level risk prediction was accurate.** Round 1 CHANGES_REQUIRED
   landed findings that mapped 1:1 against intake `risk_flags`:
   - `domain_blockage_mismatch` (HIGH) → MED-1 residual blockage
   - `u_mean_centerline_new_extractor` (HIGH) → HIGH-1 windowing bug
   - `sampleDict_interpolation_and_scaling` (MED) → MED-3 y/z filter missing
   - Only `mesh_density` wasn't explicitly intake-flagged — this is a
     methodology gap (see below).

2. **Pass-rate calibration was honest.** Intake predicted 0.30 round-1 pass
   rate; actual was 0 (CHANGES_REQUIRED). That's below target but the gap
   is explainable: intake accounted for adapter + extractor risk, not for
   the sampling-wiring interaction effect. Estimating lower would have been
   more honest, but 0.30 was within the RETRO-V61-001 "pre-merge Codex
   required at ≤70%" band which did fire correctly.

3. **F1-M2 two-tier close worked as designed.** R1 CHANGES_REQUIRED → R2 →
   R2 CHANGES_REQUIRED → R3 → R3 APPROVE. The gate didn't let
   APPROVE_WITH_COMMENTS sneak through; every "almost clean" verdict got a
   mandatory follow-up round. This is exactly what methodology v2.0 was
   designed for (BFS V61-052 round-4 back-fill was the original
   incident that drove F1-M2).

4. **Batch-splitting after Codex plan review prevented blast-radius bugs.**
   Original batch plan had B1 as one commit; Codex pre-Stage-A review split
   it into B1a (adapter physics) + B1b (sampling infrastructure) + B2
   (extractor module) + B3 (wiring). The py3.9 syntax bug landed in B1a
   only; the split made it easy to bisect and fix without touching B1b/B2/B3.

## What went wrong

### P0 · Python version parity (new methodology gap)

**Incident**: Round 2 FAIL on `python3 -m py_compile src/foam_agent_adapter.py`
with `SyntaxError: f-string: expecting '}'` at line 4795. The nested
multi-line f-string conditional I wrote in B1a parses under Python 3.12
(project `.venv`) but not under Python 3.9 (system `python3`, Codex shim
default, CI shim default).

**Why it happened**: I verified syntax locally with `./.venv/bin/python -c "import ast; ast.parse(...)"` which passed. But `.venv` is 3.12 while both
Codex's compile check and system CI default to 3.9. PEP-701 relaxed
f-string grammar was adopted in 3.12; 3.9 has stricter rules that reject
nested multi-line expressions with embedded f-strings.

**Methodology implication**: The intake v2.0 `risk_flags` template does NOT
include a `python_version_parity` category. Adding one would have caught
this at Batch A (when my local syntax passed but nothing verified 3.9
parity). Recommended retroactive P2 patch to the LDC methodology page §8:
- Add `python_version_parity` to the intake risk_flags template
- Add a mandatory step in Stage A: run `python3 -m py_compile <changed_files>` 
  even if .venv tests pass
- Consider adding `.pre-commit-config.yaml` hook for dual-version compile

### P1 · Mesh-density risk not in intake

**Incident**: Round 1 MED-2 surfaced that my (400, 200, 1) block scaling was
a 50% coarsening vs. pre-B1 resolution (old 0.05D → new 0.075D near cylinder).
Intake had a `forceCoeffs_axis_convention` risk but no `mesh_density_on_grow`
risk.

**Why it happened**: When I picked domain-grow option (b), I focused on
blockage (the HIGH risk) and treated mesh as an afterthought. The implicit
assumption "scale cells proportionally" became "halve the resolution
because the mesh scaled 3x but I only scaled 2x".

**Methodology implication**: Add a `mesh_density_on_domain_change` risk flag
to the intake template for any DEC that changes blockMesh dimensions. Very
narrow — only fires when dx or dy changes by > 10%. Low-friction addition.

### P2 · Stale alias doc not caught by R1 fix

**Incident**: Round 2 MED-1 surfaced that `cylinder_crossflow.yaml` (the
legacy alias) still had pre-B1 wording in 3 places (geometry_assumption,
laminar precondition, blockage precondition), even though I had updated
those same sections in `circular_cylinder_wake.yaml` during R1 fixes.

**Why it happened**: My R1 fix commit updated circular_cylinder_wake.yaml
carefully but I "merged" the same physics_contract block into the alias
only partially. The "keep in sync" comment was honored in spirit
(contract_status line matched) but not in letter (individual precondition
blocks drifted).

**Methodology implication**: Two-file syncs are brittle. When a Batch A
decision says "sync both files", the Batch A verification should include a
diff-contract check that asserts the two physics_contract blocks are
field-wise identical modulo comments. Low-priority follow-up; probably
better solved by the post-V61-053 alias-consolidation DEC that deletes
cylinder_crossflow.yaml entirely.

## Numeric calibration metrics

Compare DEC-V61-053 to prior Type I / Type II arcs:

| DEC | Type | Intake est. | Rounds | Actual outcome | Arc/round | Notes |
|-----|------|-------------|--------|----------------|-----------|-------|
| V61-050 (LDC) | I | 0.70 (late-arc) | 4 | APPROVE r4 | retrofit | Pre-v2.0; no intake signature |
| V61-052 (BFS) | II | 0.45 | 5 (incl. r4 back-fill) | APPROVE r5 | back-fill | V61-052 exposed the F1-M2 gap |
| V61-053 (cyl) | I | **0.30** | **3** | **APPROVE r3** | **on-target** | First v2.0 first-apply |

V61-053 is the first DEC where:
- intake + plan-review scoped the arc before code
- 3-round Codex arc completes on schedule (intake predicted 3-4 soft target)
- F1-M2 gates caught an APPROVE_WITH_COMMENTS path that would have closed silently under v1.0

## Recommendations for future DECs

1. **Adopt P0/P1 methodology patches** (python_version_parity + mesh_density_on_domain_change) into the intake template at `.planning/intake/TEMPLATE.yaml` (needs creating; V61-053 was free-form).

2. **Batch D can start** from this clean B1+B2+B3+C state. It's frontend (Compare-tab multi-dim UI + solver_output figure) and will need its own Codex round post-close per F1-M2. Audit fixture regen remains the blocker for end-to-end Batch D verification but not for code landing.

3. **Intake template lesson**: add a `verified_on` field listing actual Python versions (3.9 AND 3.12) that all Stage A commits must compile under. Belongs in P2 methodology patch.

4. **Retro cadence** — this is the first DEC-arc incident retro under v2.0 F1-M2 rules. The "write retro when CHANGES_REQUIRED fires twice in same DEC" trigger works; keeping it.

## Addendum (2026-04-24 post-R3 live-run findings)

After R3 APPROVE, attempting the Batch D live audit fixture regen uncovered **two more methodology gaps** that neither static Codex review nor the existing unit tests caught:

### P0 (new) · `self._db.get_execution_chain` accessor bug (d3ffc06)

**Incident**: First cylinder audit run errored immediately with
`AttributeError: 'FoamAgentExecutor' object has no attribute '_db'`. The
expression was introduced in B1a (63c11cb) while threading whitelist-driven
`turbulence_model` overrides. Codex round 1 reviewed the *logic* of the
lookup (whitelist demands laminar, adapter should honor it) but not the
*accessor* (`self._db` doesn't exist; correct path was a module-level
YAML loader).

**Why the tests missed it**: B1 unit tests call `_generate_circular_cylinder_wake(tmp, task, turbulence_model="laminar")` directly, bypassing the
dispatch path where `self._db.get_execution_chain(...)` is evaluated. The
tests demonstrate correct downstream behavior *given* a turbulence_model
value but never exercise the upstream whitelist lookup.

**Methodology implication** — new Type III intake risk flag:
`executable_smoke_test`. Require at least one short-duration (<10 min wall,
can be Docker container or mock) end-to-end invocation of the changed code
path before accepting any Codex APPROVE. Ideally integrated into the
F1-M2 Stage E close: "has the post-R3 code been invoked end-to-end once?"
Otherwise any accessor / attribute-dereference bug downstream of the
tested method signature is invisible.

### P0 (new) · Solver numerical stability risk (35f3278)

**Incident**: First successful invocation of pimpleFoam on the post-B1
grown-domain (144k-cell) cylinder geometry diverged pressure on the
**first timestep**: GAMG with GaussSeidel smoother returned Initial=1,
Final=nan after 1000 iterations. Ux/Uy solves were fine. Everything
NaN thereafter.

**Why no review caught it**: Codex reviews static code; pimpleFoam's
GAMG behavior on a specific mesh+BC combination is runtime-emergent. The
B1 unit tests don't invoke the actual solver. Even running `checkMesh`
reports OK (max skewness 4.4e-13, non-ortho 0) — the mesh is clean; the
failure is an interaction between GAMG's Gauss-Seidel smoother and the
noSlip pressure Neumann boundary at the cylinder wall.

**Fix**: PCG+DIC for p (recommended OF.org fallback for 2D external
wakes), plus shorter endTime (200s→10s) and maxCo relaxation (0.5→1.0)
to bring projected wall time from 40 hours → ~2.8 hours.

**Methodology implication** — new Type II intake risk flag:
`solver_stability_on_novel_geometry`. Triggers whenever any BC type or
domain dimension changes in the adapter. Mitigations should include:
(a) explicit fvSolution review against OF.org tutorials for the closest
matching case, (b) optional `potentialFoam` initialization for external
flows, (c) the executable_smoke_test rule above catches the failure
immediately.

### Updated counter calibration

| DEC | Type | Intake est. | Rounds | Actual outcome | Hidden defects caught post-R3 | Arc |
|-----|------|-------------|--------|----------------|-------------------------------|-----|
| V61-050 (LDC) | I | 0.70 (late-arc) | 4 | APPROVE r4 | N/A | retrofit |
| V61-052 (BFS) | II | 0.45 | 5 (incl. r4 back-fill) | APPROVE r5 | 1 (wall-shear provenance) | back-fill |
| V61-053 (cyl) | I | **0.30** | **3 + 2 live fixes** | APPROVE r3 + live-run recalibration | **2 (accessor + solver)** | first-apply |
| V61-059 (plane-channel) | II | 0.40 | **4 + Stage B sub-arc r1+r2** | APPROVE r4 + APPROVE_WITH_COMMENTS sub-arc r2 | **3 (OF10 file rename + solver-framework drift + FO output filename)** | first-apply |

V61-053's 3-round Codex arc was genuinely clean on the code paths Codex
could see. The post-R3 defects are a **blind spot category**, not a
Codex miss — no static review can catch an attribute-dereference bug
on an object graph that isn't exercised, or a solver divergence in a
numerical solver that isn't invoked.

**V61-059 addendum (2026-04-25)**: 3 distinct hidden post-R3 defects,
all variants of the same underlying class —
**OpenFOAM-version-emitter API drift**:

1. `constant/turbulenceProperties` → `constant/momentumTransport`
   (OF10 incompressible rename; commit `a71e8ec`). Necessary fix
   surfaced when Stage B crashed at 4.6s with FOAM FATAL ERROR
   "Unable to find turbulence model in the database" from inside
   the wallShearStress function-object.
2. `icoFoam` → `pisoFoam` swap (commit `4af21a2`). Renaming the
   file alone was insufficient because icoFoam is hard-coded
   laminar PISO that does not register a momentumTransportModel
   at all; pisoFoam is the laminar-capable PISO that does. Plus
   fvSchemes additions (`div((nuEff*dev2(T(grad(U)))))`,
   `interpolationSchemes`, `snGradSchemes`) that the
   momentumTransport framework requires.
3. `<set_name>_<field>.xy` → `<set_name>.xy` (OF10 sets-FO output
   filename; commit `42158e2`). Reader was looking for the legacy
   per-field naming; OF10 packs all components into one file. The
   case ran cleanly but the emitter raised "uLine output absent"
   on FO output that was right there.

A 4th finding (commit `59198cf`) was a runtime-budget tuning
regression — endTime=50, deltaT=0.002 burned 3-hour wall-clock on
flow that converged at simulated t≈1.5s. Reduced to endTime=5,
deltaT=0.05, p-solver PCG/DIC → GAMG/GaussSeidel; per-run wall now
~9 minutes. Not a correctness defect, but it would have made the
Stage B verdict cycle unworkable in batch.

Codex round-5 (Stage B sub-arc round 1) caught two genuine static-
review defects that the post-R3 fixes themselves introduced:

- **F7**: the OF10-first reader silently returned packed-`U` data
  when the caller asked for `field="p"` (`src/plane_channel_uplus_emitter.py`).
- **F8**: three downstream consumers (`render_case_report.py`,
  `metrics/residual.py`, `audit_package/manifest.py`) still
  hard-coded the old solver/file names, so the Stage B
  artifact dir didn't round-trip through report/manifest tooling.

Codex even **empirically verified F8** by running probes against
the actual artifact dir — that's the dynamic-vs-static frontier
RETRO-V61-053 §10 was about. The sub-arc round 2 returned
APPROVE_WITH_COMMENTS with two P3 nits (coexistence test gap and
log-name preference order divergence across the 3 consumers); both
landed in commit `efae759`.

**The methodology lesson V61-059 hardens**: when Codex reaches
APPROVE on a code path that depends on an **emitter-side API**
(filenames, file conventions, registry objects, simulation-type
keywords) of an external tool whose minor-version output format
might have drifted, Codex APPROVE is a *static-review* clean
verdict, not a *runtime-correctness* clean verdict. The Stage B
executable smoke test is what closes that gap.

### Concrete action items for RETRO-V61-053 + successors

1. **Write `.planning/intake/TEMPLATE.yaml`** with all 5 risk_flag categories:
   - `python_version_parity` (2026-04-24 R2 finding)
   - `mesh_density_on_domain_change` (2026-04-24 R1 finding)
   - `executable_smoke_test` (2026-04-24 post-R3 finding)
   - `solver_stability_on_novel_geometry` (2026-04-24 post-R3 finding)
   - `openfoam_version_emitter_api_drift` (2026-04-25 V61-059 post-R3 — promoted to **HIGH** for any case that depends on OpenFOAM-generated auxiliary files or registry objects: function-object outputs, momentumTransport vs turbulenceProperties, solver-log naming, sets-FO `<set>.xy` vs `<set>_<field>.xy`)
2. **Amend RETRO-V61-001 cadence rule**: add "post-R3 live-run defect" as a 4th retro trigger (currently 3: phase complete / counter≥20 / CHANGES_REQUIRED on PR).
3. **Methodology page §10**: dedicate a section to "static review vs dynamic invocation" — be explicit that Codex can't catch what it can't exercise.

## Counter status

`autonomous_governance_counter_v61`: **40** after DEC-V61-053 lands. Up from
39 (V61-052 close). Well under any soft-review threshold. V61-053 still
IN_PROGRESS (Batch D + fixture regen pending) so no counter bump yet from
full close.

## Cross-refs

- DEC file: `.planning/decisions/2026-04-23_cfd_cylinder_multidim_dec053.md`
- Intake: `.planning/intake/DEC-V61-053_circular_cylinder_wake.yaml`
- Codex logs: `reports/codex_tool_reports/dec_v61_053_{plan_review,round1,round2,round3}.log`
- Methodology: Notion page `34bc68942bed8189be77c703cc62d0f4` §8 (v2.0 patches)

---

## Addendum 2026-04-24 · risk_flag registry promotion (G-6)

`executable_smoke_test` + `solver_stability_on_novel_geometry` (both P0
findings from this retro's post-R3 analysis) were **promoted to a
canonical enum** on 2026-04-24 per G-6 of Post-Pivot Go/No-Go.

- Registry: `knowledge/schemas/risk_flag_registry.yaml` (schema_version=1)
- Per-case assessments: `.planning/case_profiles/<case_id>.yaml` (10 cases
  backfilled; cylinder marks both flags `triggered: true`, others `false`)
- Intake TEMPLATE pointer: `.planning/intake/TEMPLATE.yaml` header note

This retro's narrative §10 remains the historical record; the registry
is the machine-readable source of truth going forward.

---

## Addendum 2026-04-25 · attempt-7 live run post-mortem

**Background.** A final attempt-7 live OpenFOAM run for
`circular_cylinder_wake` was triggered mid-RETRO-V61-004 P1 arc as a
background task (id `bbuywy0ry`, started 2026-04-24, completed
2026-04-25 after 8628.2s = ~2.4 hours wall). It finished with
`FAIL · audit_real_run_measurement.yaml` and this addendum closes
the decision loop.

### Observed outcome (ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml)

```yaml
solver_success: true
comparator_passed: false
measurement:
  value: 0.13784461152882208    # strouhal_number
  reference: 0.165
  deviation: ~16.5%             # exceeds gold tolerance=5%
secondary_scalars:
  cd_mean: 1.3790543620796876   # within tolerance vs Williamson 1996 (1.33)
  cl_rms: 0.08094277312528547
attestation:
  overall: ATTEST_NOT_APPLICABLE
  checks: []
commit_sha: c4d89b2
measured_at: '2026-04-24T18:05:07Z'
```

### Classification: NOT a new defect

Attempt-7's Strouhal number 0.1378 is within 0.14% of attempt-6's
0.138 (the prior audit-fixture baseline). This is the **same physics-
precision ceiling** that DEC-V61-053 frontmatter already acknowledged:

> "precision-limited at 10s endTime, gold-grade requires future
> endTime bump DEC"
> — DEC-V61-053 `external_gate_actual_outcome_partial` field

Mechanism: at endTime=10s with shedding frequency f≈1.63 Hz (St=0.165,
U=1, D=0.1), the post-50s-transient-trim window mathematically cannot
be computed (10s total < 50s default trim). The extractor gracefully
degrades to a shorter trim + smaller FFT window, which sits well below
the 8-shedding-period confidence threshold set by DEC-V61-040 round-2.
Result: a legitimate measurement but with large FFT Δf uncertainty,
and `strouhal_low_confidence=True` flag set by the extractor.

### The P1 arc (RETRO-V61-004) partially mitigates this

Two P1 deliverables already landed on main would soften attempt-7's
FAIL when threaded through the new pipeline:

1. **P1-T3b** backfilled `.planning/case_profiles/circular_cylinder_wake.yaml`
   with `tolerance_policy.strouhal_number.tolerance = 0.25` (25%),
   reflecting the known precision ceiling. Under the new
   `MetricsRegistry.evaluate_all(..., tolerance_policy=...)` dispatch,
   deviation 16.5% vs 25% tolerance → PASS.

2. **P1-T1c** SpectralMetric demotes PASS → WARN when
   `strouhal_low_confidence=True` is observed in `key_quantities`.
   So even under the loose 25% policy tolerance, the honest verdict
   would be WARN (not silent PASS).

**Why attempt-7 still shows FAIL in the fixture:** the legacy
`ResultComparator` path in `task_runner.run_task` does NOT yet call
`load_tolerance_policy`. This is RETRO-V61-004 Recommendation #1 —
"next DEC should add `load_tolerance_policy` call to
`_build_trust_gate_report`" — explicitly deferred in P1-T5 per the
no-refactor-of-comparator-path scope. Until that DEC lands, audit
fixtures continue to use the gold-standard 5% tolerance and FAIL.

### Not a runtime-emergent blind spot

Unlike the 6 runtime-emergent defects documented in this retro's
original §§ (d3ffc06 accessor, 35f3278 solver divergence, e8b92ed
extractor gating, c81c0aa transient trim sizing, fdfa98a FO
executeControl), attempt-7 exhibits **no new runtime defect**. The
solver ran, the extractor ran, and the physics output is the
expected 10s-endTime-budget number. The FAIL is a pre-declared
precision ceiling, not a bug.

**Update 2026-04-25 (Opus 4.7 P1-arc verdict)**: Opus independent review
adjudicated candidate C ("parameter envelope precision ceiling") as
**ADD** at medium severity. New `flag_id: parameter_envelope_precision_ceiling`
now lives in `knowledge/schemas/risk_flag_registry.yaml` and has been
retroactively added to this DEC's intake `risk_flags:` list (with
`retroactive: true`, `triggered: true`, `triggered_by: endTime=10s`,
and an `unblock_path` field pointing at the V61-058 parameter-bump re-run).

The existing `solver_stability_on_novel_geometry` flag stays triggered
for the live-run divergence blind spot (a genuine runtime-emergent class);
the new `parameter_envelope_precision_ceiling` sits alongside it to
annotate the *pre-declared* precision ceiling, which is NOT a defect
class but a compute-budget contract. Per Opus hard constraint, retroactive
triggering of this flag requires explicit verdict authority (cannot be
self-issued) — future runs MUST pre-declare the flag in the pre-run
frontmatter, not back-fit after seeing the FAIL number.

### Side-observation: attestation ATTEST_NOT_APPLICABLE

`attestation.overall == ATTEST_NOT_APPLICABLE` with empty checks
indicates the attestor did not locate a solver log after the run.
Probable causes:

- `FoamAgentExecutor.execute()` finally-block teardown removed the
  case dir before the attestor inspected it (known limitation in
  STATE.md: "FoamAgentExecutor: case dirs auto-deleted in finally block")
- `raw_output_path` captured in `ExecutionResult` points at a
  location whose `log.{solver}` file was cleaned up

This is the **same gap** that V61-056 R1 finding #1 addressed at
the Control layer (the no-log WARN reason was being dropped; fixed
to emit an explicit "attestor not applicable (no solver log
resolvable from artifacts)" note). For a future audit re-run,
the Control-plane fix is already in — verdict will surface the
explicit note rather than a silent NOT_APPLICABLE.

### Recommendation · gold-grade follow-up DEC

Keep attempt-7's result as **demonstration-grade**, not gold-grade,
consistent with DEC-V61-053's clean-close verdict. A follow-up DEC
(tentative id DEC-V61-057 or later depending on sequencing) should:

1. Bump `CYLINDER_ENDTIME_S` from 10s to 60s (or 200s for ±3%
   precision). At 60s post-trim window would be ~10s = ~16 shedding
   periods, well above the 8-period confidence threshold →
   `strouhal_low_confidence` should clear and ΔSt should collapse
   from ~20% to ~3-5%.
2. Re-run as attempt-8 for the authoritative audit fixture.
3. Tighten `tolerance_policy.strouhal_number.tolerance` from 25%
   back to 5-10% in `circular_cylinder_wake.yaml`.
4. This follow-up DEC is a pure parameter bump + re-run; no new
   code path. Self-pass-rate 0.90+, minimal Codex scope.

Wall-time budget for the endTime-60s re-run: ~16 hours (6× current
~2.4h wall × endTime scaling). Feasible for an overnight run.

### Counter impact

This addendum is doc-only; no counter tick. V61-053 DEC counter
stays at 40; P1 arc end counter stays at 43.

### Cross-refs for attempt-7

- Background task output: `/private/tmp/claude-502/.../bbuywy0ry.output`
- Measurement fixture:
  `ui/backend/tests/fixtures/runs/circular_cylinder_wake/audit_real_run_measurement.yaml`
  (commit_sha `c4d89b2` · measured_at `2026-04-24T18:05:07Z`)
- P1 arc retrospective that triggered this analysis:
  `.planning/retrospectives/2026-04-25_p1_arc_complete_retrospective.md`
  (RETRO-V61-004)
- Recommendation #1 for the P1-to-production transition:
  Add `load_tolerance_policy` to `_build_trust_gate_report`
  (RETRO-V61-004 §Recommendations)
- Current case_profile with 25% policy override:
  `.planning/case_profiles/circular_cylinder_wake.yaml` (P1-T3b commit e8a0565)
