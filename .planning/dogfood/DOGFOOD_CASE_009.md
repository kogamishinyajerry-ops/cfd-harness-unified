# DOGFOOD_CASE_009 — Sandia Flame D · reacting low-Mach (8th regime)

**Date:** 2026-05-22
**Engine:** cfd-audit-merge @ `a03b066` (Merge: close 3 dogfood spikes Gap #12+#13+#14)
**Case:** `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/`
**Charter:** add reacting/combustion regime via case_009 Sandia Flame D — turbulent
piloted diffusion flame, methane jet in air co-flow, DRM-19 chemistry (19 species
+ N2 + AR, 84 reactions), reactingFoam solver in OpenFOAM 2312.
**Result:** **ingest exit 0 · report exit 1 · overall_status = FAIL · solver_execution = ingested · validation_status = not_validated**.
6 net-new gaps surfaced (TBD-15 .. TBD-20). Reacting low-Mach regime is **not
honestly supported end-to-end** — engine ingests the case but its trust signal on
the solver gate is silently wrong.

## What ran

```text
$ cfdtrust validate-manifest <case>
[cfdtrust] OK   manifest valid: case_id=case_009_sandia_flame_d  → exit 0

$ cfdtrust ingest <case>      # /usr/bin/time -l: 36.27s real, 13.0 GiB peak RSS
[cfdtrust] OK   ingest PASS: simpleFoam converged at iter 0 (all 3 field residuals ≤ target).
[cfdtrust] OK     external_log_source = log_reactingFoam.txt
[cfdtrust] OK     checkmesh_image     = openfoam/openfoam11-paraview510:latest
[cfdtrust] WARN Ingested run: harness did NOT witness the solver execution.   → exit 0

$ cfdtrust report <case>
[cfdtrust] OK   trust_report written: artifacts/trust_report.json
        overall_status   = FAIL
        solver_execution = ingested
        validation_status= not_validated                                       → exit 1

$ cfdtrust explain <case>     → exit 0
```

## Pre-ingest setup

The native external run produced two staged logs `log_cold.txt` (2.1 GiB,
combustion-off cold-flow stage) and `log_ignite.txt` (3.3 GiB, ignite stage,
chemistry-on, cut mid-run with 5 timestep dirs written 0.001..0.005 + 0.0055).
Neither matches engine's discovery names (`log_reactingFoam.txt`, `log.reactingFoam`,
`reactingFoam.log`, plus generic simpleFoam/pimpleFoam fallbacks).

Workaround applied (NO engine modification):

```bash
ln -sf log_ignite.txt log_reactingFoam.txt
```

This is **gap #15** — see below.

Manifest authored at `case_manifest.yaml`. Real patch names extracted from
`constant/polyMesh/boundary` (11 patches: 3 inlets, 4 wall, 1 outlet, 2 wedge,
1 defaultFaces=empty). residual_targets covers 27 fields:
Ux/Uy/Uz/p/h/k/epsilon + 20 species (AR + 19 DRM-19 species — CH2(S) excluded
because the engine's regex strips parens).

## Honesty fences — verified

| Fence | Required | Observed | OK? |
|---|---|---|---|
| ingest-execution marker | `details.execution == "ingested"` | yes | ✓ |
| top-level solver_execution | `"ingested"` | `"ingested"` | ✓ |
| overall_status cap | `≤ WARN` (cannot be PASS) | `FAIL` (driven by mesh+bc gate fails) | ✓ |
| validation_status cap | `≤ partial` | `not_validated` | ✓ |
| solver.log banner | `INGEST_BANNER` prepended | yes (in `artifacts/solver.log`) | ✓ |
| `real_solver_invoked` | `false` | `false` | ✓ |

Top-level honesty contract held. The fence on **the solver gate's individual
verdict**, however, did not — see TBD-17.

## Per-gate verdicts

| Gate | Status | Notable |
|---|---|---|
| `geometry_contract` | PASS | 10/10 declared patches present + defaultFaces extra detected as empty (correct for 2.5D wedge) |
| `mesh_contract` | FAIL | quality PASS (max skew 0.331 / non-orth 0.0 / aspect 22.0); y+ INCOMPLETE (no_solver_y_plus_data, expected — no yPlus function object in this case) |
| `bc_contract` | FAIL | patch_coverage misses 6 field/patch pairs incl. `alphat` on 4 walls + `defaultFaces` on all 6 declared fields; type_match catches outer_side `slip` vs declared `noSlip` (real physics issue in this case); 21 species BC files exist (CH4, O2, ...) but bc_contract schema has no way to declare per-species BCs, so they're ignored entirely |
| `solver_execution` | **PASS (spurious)** | "simpleFoam converged at iter 0 (all 3 field residuals ≤ target)" — see TBD-17 |
| `qoi_extraction` | MOCKED | Phase 0 placeholder fired correctly given QoI not staged |
| `reference_comparison` | MOCKED | `not_finalized` correctly mocked out without false claim |

## NEW gaps (numbered TBD-15..TBD-20; coordinate with case_010 agent before merging into engine code-comments)

### TBD-15 · Solver log discovery doesn't know reactingFoam multi-stage runs

**Symptom:** engine's `_INGEST_LOG_FALLBACK_CANDIDATES` lists simpleFoam,
pimpleFoam, icoFoam, potentialFoam, foamRun — no reactingFoam, no reactingPimpleFoam,
no XiFoam, no fireFoam, no chemFoam. Even the manifest-driven primary
(`log_reactingFoam.txt`) didn't exist on the case as authored — the real run
output `log_cold.txt` + `log_ignite.txt` (the case-team's multi-stage naming
convention).

**Impact:** any reacting/combustion case ingested as-shipped from a project
following the cold→ignite→ramp staging idiom (which is the recommended startup
pattern per case_009's S17/S18 playbook entries) hits BLOCKED `no_solver_log_found`.

**Fix:** widen the fallback list to include reacting-class solver names AND
support a `solver_log_patterns` manifest-side glob hint, OR extend
`_find_external_solver_log` to do a manifest-keyed fuzzy match (`log_*.txt` →
prefer ones whose content header begins with `Exec : <manifest.solver>`).

**Workaround used:** `ln -s log_ignite.txt log_reactingFoam.txt`.

### TBD-16 · `_parse_simplefoam_log` collapses sub-second physical time to iter=0

**Symptom:** `_TIME_LINE_RE` matches `Time = 0.005001`, but the parser then does
`int(float(m_time.group(1)))` (line 501 in `backends/openfoam.py`). For
unsteady solvers running sub-second physical time, **every Time entry truncates
to `iter=0`**. Witnessed in `residuals.csv`: 593 rows, every single one with
iter=0, despite 593 distinct `Time = ` lines (0.005001 → 0.005594).

**Impact:** the iteration discriminator is destroyed for ALL unsteady cases
(reactingFoam, pimpleFoam, pisoFoam, fireFoam) where physical time is in
seconds-to-milliseconds. Downstream consumers can't distinguish iterations;
QoI-stability windowing (`window_iterations: 50`) is meaningless.

**Fix:** preserve `iter` as `float`, not `int`. Downstream comparators
(`final_iter`, `max_iter` int compare) need updating to accept either, OR
add a separate `time_s` column and keep `iter` as a 1-indexed monotonic counter.

### TBD-17 · solver_execution gate falsely PASSes when last-iteration residual block is partial

**Symptom (the worst finding):** the gate declared `PASS — simpleFoam converged at
iter 0 (all 3 field residuals ≤ target)` despite the manifest declaring 27 target
fields. Reality: `parsed["iterations"][-1]["residuals"]` happened to contain
only `{Ux, Uy, Uz}` because the source log was cut mid-PIMPLE-outer-loop
(species/p/h/k/epsilon hadn't been emitted yet for the very last timestep).

The gate logic at `_compute_gate_from_residuals` iterates manifest targets and
**silently skips any target field absent from `final`** (`if actual is None:
continue`). Then `failed = []`, `checked = [Ux, Uy, Uz]`, `not failed → PASS`.
Only 3/27 fields were actually checked yet the gate claimed all-PASS.

**Impact:** This is **exactly the failure mode the trust harness exists to
prevent.** A reactingFoam case can be cut at any partial PIMPLE iteration and the
gate will declare PASS on whichever fields happened to be solved before the cut.
Worse: 21 species residuals (which are the entire point of a reacting case) can
be missing from `final` if the cut happens before the species ODE batch fires —
and the gate has no signal that anything is wrong.

The pre-existing R15-F-02 fix already covers "ZERO target fields in log → refuse
PASS", but it stops at zero — it does NOT enforce "missing >threshold of declared
fields → BLOCKED". Reacting cases blow through this gap because they always have
*some* checked field (Ux is solved before species).

**Fix:** introduce a minimum-coverage threshold:
```python
COVERAGE_THRESHOLD = 0.5    # 50% of declared targets must be in final
if targets and len(checked) / len(targets) < COVERAGE_THRESHOLD:
    return BLOCKED("partial_final_iteration_coverage", ...)
```
Recommend threshold = manifest-declarable so reacting cases can require ≥95%.

### TBD-18 · No species-transport awareness in any schema or audit gate

**Symptom:** the manifest schema's `bc_contract` has slots `inlet/outlet/wall/
turbulence_fields` but no `species` slot. The case_009 case has 21 species BC
files in `0/` (CH4, O2, N2, H2O, CO2, CO, H2, OH, H, O, HO2, HCO, CH3, CH3O,
CH2O, CH2, C2H4, C2H5, C2H6, AR — CH2(S) is the 21st) each with per-inlet
mass-fractions — the engine's BC audit ignores them entirely because no
manifest field references them.

The schema also has no concept of:
- `chemistryProperties` (solver dispatch — `ode`/`Euler`/`PaSR`/`EDC`)
- `combustionProperties` (model name — `PaSR`/`EDC`/`laminar`/`infinitelyFastChemistry`)
- `thermophysicalProperties` for reacting mixtures (`hePsiThermo`/`reactingMixture`/
  `janafThermo`/`sutherland`)
- chemistry mech file (`constant/reactions`, `constant/thermo.compressibleGas`)

**Impact:** the engine cannot validate ANY of: (a) species are conserved at
inlets (sum(Y_i) = 1), (b) species inlet BCs match expected mixture composition
for the canonical case, (c) combustion model is one the solver supports, (d)
chemistry mech is consistent (e.g. species count in `0/Y_i` matches species
list in `constant/thermo.compressibleGas`), (e) thermo header T-bound matches
case T-range (the V41 finding from case_009: janafThermo Tlow=300 vs cell
T~294 floods log).

This is a **schema gap**, not just an implementation gap — even a perfect
backend can't audit what the contract doesn't declare.

**Fix (sketch):** extend manifest schema with optional `reacting_contract`:
```yaml
reacting_contract:
  species_list: [CH4, O2, N2, H2O, CO2, ...]   # validate 0/Y_i files
  inlet_compositions:
    fuel_jet: {CH4: 0.156, N2: 0.539, O2: 0.196, ...}
    pilot_annulus: {...}
    coflow_air: {O2: 0.232, N2: 0.768}
  combustion_model: PaSR
  chemistry_solver: ode
  thermo_temperature_range: {Tlow: 200, Thigh: 5000}
```
Each adds 1 audit dimension — none are blocking but reaching honest trust on
reacting cases needs all of them.

### TBD-19 · Regex `(\w+)` strips parens from species names like CH2(S)

**Symptom:** OpenFOAM species naming convention uses `(S)` suffix for spin
singlet (`CH2(S)` is a stable DRM-19 species distinct from `CH2`). The engine's
`_RESIDUAL_LINE_RE` captures the field name via `(\w+)` which stops at the
opening paren. Result: log line `Solving for CH2(S), Initial residual = ...`
gets captured as `CH2`, **silently collides with the also-present `CH2`**
residual line. `residuals.csv` shows 20 species columns, missing `CH2(S)`
entirely; whichever is parsed last clobbers the first under `setdefault` (which
only persists the first per iter — so CH2 wins and CH2(S) is lost).

**Impact:** any DRM-19 / GRI-3.0 / USC-Mech reacting case loses 1+ species
silently. Mass conservation across species is impossible to audit when a
species disappears.

**Fix:** widen field-name capture to `([A-Za-z][A-Za-z0-9_]*(?:\([A-Za-z]\))?)`
or just `(\S+?)` followed by `,`. Test against DRM-19 + GRI-Mech 3.0 species
lists.

### TBD-20 · Engine reads multi-GiB logs into memory (3.3 GB log → 13.0 GiB peak RSS)

**Symptom:** `read_artifacts` calls `log_path.read_text().splitlines()[:5]` for
banner detection, then `_parse_simplefoam_log` calls
`log_text.splitlines()` over the whole text. For a 3.3 GiB log this materialised
13.0 GiB peak RSS (`/usr/bin/time -l` measurement) and took 36 seconds wall.

Reacting cases generate enormous logs because (a) per-cell per-species ODE chemistry
ticks emit residual lines for every iteration AND (b) the V41 janafThermo
temperature-bound warning spam (one warning line PER CELL OOB PER PIMPLE iter).
case_009 v1 ignite stage produced 3.3 GiB in ~1 ms of physical time. v2 ramp
to 1.0 s would produce TB-scale logs.

**Impact:** any reacting case at production scale, any LES case, any unsteady
turbulence case with adjustTimeStep is at risk. The engine will OOM on
modest-spec workstations (16 GiB RAM machine cannot ingest).

**Fix:** stream the log line-by-line (`for line in log_path.open()`) for parser
and banner-head sniff. Don't materialize full text. Pre-existing
`_scan_solver_log_for_divergence` (line 1884) already streams tail-only with
seek — same idiom needed in `_parse_simplefoam_log`.

## Species count parsed

20 unique species columns parsed in `artifacts/residuals.csv`:

```
AR, C2H4, C2H5, C2H6, CH2, CH2O, CH3, CH3O, CH4, CO, CO2,
H, H2, H2O, HCO, HO2, O, O2, OH
```

(19 DRM-19 species visible — note `CH2(S)` missing per TBD-19; `N2` missing
because it's the bath gas, not transported; engine sees 19 species correctly
on the CSV side but the gate only checked Ux/Uy/Uz per TBD-17.)

## Reacting regime conclusion (1 paragraph)

The engine **mechanically ingests** a reactingFoam case end-to-end without
crashing, but its trust signal is silently wrong in ways that make it
**unfit-for-purpose for reacting/combustion validation as of `a03b066`**. The
audit gates that work (geometry presence, mesh quality, BC type-match on
non-species fields) work uniformly across regimes — they're regime-agnostic.
The audit gate that matters most for a reacting case (solver_execution checking
species residuals) silently passes on 3/27 declared fields (TBD-17) and loses
1 species name to a regex bug (TBD-19). The schema has no species, no
combustion model, no chemistry-mech declaration (TBD-18), so even a fixed
parser couldn't honestly validate the reacting physics. Plus the engine OOMs on
production-sized reacting logs (TBD-20). **Verdict: 8th regime is NOT
honestly covered.** Reacting low-Mach support requires (a) a manifest schema
extension for `reacting_contract`, (b) a partial-coverage threshold in the
solver gate, (c) a streaming log parser, (d) species-name regex fix, (e)
extended solver-log discovery patterns. All 5 items are tractable engine PRs
in the same shape as Gap #12/#13/#14 already closed at `a03b066`.

## Artifacts

- Authored: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/case_manifest.yaml`
- Symlink: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/log_reactingFoam.txt → log_ignite.txt`
- Trust report: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/artifacts/trust_report.json`
- Ingested log: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/artifacts/solver.log` (with INGEST_BANNER prefix)
- Residuals CSV: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/artifacts/residuals.csv` (594 rows × 27 cols, all iter=0 per TBD-16)
- Gate JSON: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_009_sandia_flame_d/case/artifacts/solver_gate.json`

## Engine modifications: none

Per dogfood charter, no engine source files were modified. No commits.
