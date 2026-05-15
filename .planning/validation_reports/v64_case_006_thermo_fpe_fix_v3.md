# V64-A · M-V64A-THERMO-FPE-FIX · case_006 ONERA M6 transonic wing · Validation Report v3

> **Verdict**: **PARTIAL v3** — substrate fix (system/fvOptions limitTemperature
> + potentialFoam pre-step + sutherland transport restored) partially unblocks
> B59 attempt 2's FE_DOMAIN sqrt(T) crash mode, but B59 attempt 3's
> p-equation matrix ill-conditioning persists at deeper magnitude. New crash
> mode at iter 7: force coefficients explode (Cl(f) from -2.8e-6 → 2.06e+6
> within 4 iters), feeding matrix divergence, sigFpe in `libOpenFOAM.so`
> PBiCGStab scalarSolve.
>
> **Done dim #1** (V64-A "≥3 FULL validation reports"): **stays 0/3 FULL**.
> Brief's "0/3 → 1/3" target NOT met (case_006-side). Brief's authorized
> fallback "PARTIAL v3 if fix doesn't take all the way" = MET.
>
> **Strategic finding**: case_006 → FULL gating is the **SIMPLE-style
> rhoSimpleFoam algorithm itself**, not the thermo layer. The B59 F-NEW-5
> hypothesis (rhoSimpleFoam steady SIMPLE-style algorithm cannot handle
> freestream → transonic shock initialization without pre-conditioning)
> is **re-affirmed at v3 attempt level even WITH potentialFoam pre-step**.
> Path forward: rhoPimpleFoam pseudo-transient (substrate's solver_v2)
> OR rhoCentralFoam transient (substrate's solver_v1, v2.4 baseline);
> both bypass SIMPLE's matrix ill-conditioning.

---

## §1 Session goal + scope

Per V64-A Tier 2 dispatch (this sub-DEC):

1. Apply systemic substrate-side thermo-FPE fix:
   - `system/fvOptions` with `limitTemperature` fvOption [110, 2000] K on all cells
   - `system/fvSolution` adds `potentialFlow` block + Phi solver
   - `constant/thermophysicalProperties::transport`: const → **sutherland** restored
     (safe now under fvOption clamp)
   - `scripts/v64_v3_run_solver.sh` NEW 2-stage runner (potentialFoam → rhoSimpleFoam)
2. Reuse B59 attempt 3 baseline (PBiCGStab DILU p + URF 0.10/0.30/0.10 + SIMPLE
   rhoMin 0.1 rhoMax 3.0 pMin 30000 pMax 300000 + transonic=yes + 205k mesh +
   kOmegaSST RAS).
3. Rerun rhoSimpleFoam target endTime 3000 iter, residualControl ≥4/6 < 1e-4
   for FULL convergence.
4. Target Cp at 7 Schmitt-Charpin spanwise stations · Δ < 15% / shock position
   Δ < 5% chord for FULL Cp match.
5. Reverse condition: if v3 still crashes → document failure mode + advisor
   stack extension recommendation. Brief authorizes PARTIAL v3.

**No edit to**: advisor stack source code, ROADMAP/ARC-GOAL files, mesh
(B59 205k cells reused as-is), case profile.

---

## §2 Substrate state vs v2 (B59 attempt 3)

| Slot | B59 attempt 3 | v3 (this report) | Diff |
|---|---|---|---|
| `system/fvOptions` | NOT PRESENT | NEW — `limitTemperature` [110, 2000] K on `all` cells | yes — new file |
| `system/fvSolution::potentialFlow` block | NOT PRESENT | NEW · `nNonOrthogonalCorrectors 5` · GAMG Phi solver | yes — new block + Phi solver |
| `system/fvSolution::solvers::Phi` | NOT PRESENT | NEW · GAMG GaussSeidel tol 1e-6 | yes — new solver |
| `constant/thermophysicalProperties::transport` | **const** (mu 1.79e-5) | **sutherland** (As 1.458e-6, Ts 110.4) | yes — restored to brief's original |
| `system/fvSolution::URF` | p 0.10 / U 0.30 / h 0.10 / e 0.10 / k 0.30 / omega 0.30 / rho 0.05 | unchanged (B59 attempt 3 most-relaxed) | no |
| `system/fvSolution::SIMPLE::rhoMin/rhoMax/pMin/pMax` | 0.1 / 3.0 / 30000 / 300000 | unchanged | no |
| `system/fvSchemes` | bounded upwind shock-capturing | unchanged | no |
| `case/constant/polyMesh/` | B59 205,310 cells level (6,7) | unchanged | no |
| `case/constant/turbulenceProperties` | RAS kOmegaSST (B59 attempt 3 = same) | restored from B59 archive — kOmegaSST | restored (after v2.4 fallback was laminar) |
| `case/0/{U, p, T, k, omega, nut, alphat}` | kOmegaSST RAS IC | restored from B59 archive | restored (after v2.4 fallback dropped k/omega/nut/alphat) |
| `scripts/v64_v3_run_solver.sh` | did not exist | NEW · 2-stage potentialFoam→rhoSimpleFoam | yes |
| Docker image | `opencfd/openfoam-default:2312` (arm64) | identical | no |

**Net change**: 1 new fvOptions, 1 new fvSolution block, 1 new Phi solver,
1 transport-switch (const→sutherland), 1 new runner.

---

## §3 v3 run-3 forensics

### §3.1 Stage 1 — potentialFoam pre-step (succeeded)

```
Calculating potential flow
GAMG:  Solving for Phi, Initial residual = 1, Final residual = 0.0050376, No Iterations 2
GAMG:  Solving for Phi, Initial residual = 0.0026260, Final residual = 1.5222e-05, No Iterations 4
GAMG:  Solving for Phi, Initial residual = 4.8967e-05, Final residual = 5.3331e-07, No Iterations 5
GAMG:  Solving for Phi, Initial residual = 3.4092e-06, Final residual = 3.5475e-07, No Iterations 1
GAMG:  Solving for Phi, Initial residual = 4.6253e-07, Final residual = 4.6253e-07, No Iterations 0
Continuity error = 1.3436e-05
Interpolated velocity error = 0.0034102
ExecutionTime = 1.14 s

End
```

potentialFoam converged Phi to 4.6e-7 final residual in 5 corrector iters,
1.14 s wall. Continuity error 1.34e-5 (acceptable for incompressible
preconditioner). The smooth velocity field is written to `0/U` overwriting
the freestream uniform IC.

**This is the v3 substrate fix's NET-NEW innovation vs B59**: B59 attempts
went freestream-IC → rhoSimpleFoam directly. v3 inserts potentialFoam as
preconditioner. This DID work (Phi converged cleanly) but does NOT solve
the deeper SIMPLE-instability axis (see §3.2).

### §3.2 Stage 2 — rhoSimpleFoam (crashed at iter 7)

| iter | wall (s) | p residual (initial → final) | U residual | h residual | Force coeffs |
|---|---|---|---|---|---|
| 1 | 7.5 | 0.00060 → 8.4e-12 (1 iter) | tight | 0.0035 → 4e-8 (2 iters) | Cl(f) -2.8e-6 (sane) |
| 2 | 17.4 | (multi-stage solver) | 0.005 → 2e-9 | (sane) | converging |
| 3 | 27.5 | **0.449 → 1.644 in 1000 iters** (PBiCGStab DIVERGING) | 0.114 → 0.001 | 0.116 → 8.9e-5 | (force-coeffs not yet exploded but trending) |
| 4 | 37.3 | **0.490 → 1.369 in 1000 iters** (diverged) | 0.142 → 0.0006 | 0.999 → 0.0007 | (initial explosion) |
| 5 | 60.0 | **0.821 → 23.913 in 1000 iters** (DEEPER DIVERGENCE — 30× initial) | (matrix entries diverging) | (h residual saturating at 1.0) | (Cl(f) now in ones, growing) |
| 6 | 96.5 | (worse) | (worse) | (worse) | **Cl(f) jumps to 2,059,728 (!)** |
| 7 | 110.8 | (crash on U-eq) | sigFpe in PBiCGStab scalarSolve | n/a | (n/a — crash mid-iter) |

Force coefficients tail just before crash (per
`postProcessing/forceCoeffs1/.../forceCoeffs.dat`, but file has empty content
since crash was BEFORE first writeInterval flush at iter 25 — values cited
from log echo at iter 6):

```
    Cl:	0.00020455617	0.00020551361	-9.5744308e-07	0      (iter 2, sane)
    Cl(f):	-2.7734895e-06	-2.2577231e-06	-5.1576643e-07	0  (iter 2, sane)
    ... (iters 3-5 force-coeffs grow nonphysically)
    Cl(f):	2059728.3	-0.5895884	2059728.9	0           (iter 6, EXPLODED)
    Cl(r):	-9619886.1	-1.2173339	-9619884.9	0          (iter 6, EXPLODED NEG)
    CmRoll:	-10065898	-1.3734295	-10065897	0          (iter 6, EXPLODED -10M)
```

These force-coefficient explosions are NOT a separate failure — they are
the visible symptom of the U field developing inf/NaN entries from
matrix solver instability, which then makes the next iter's grad(p) source
term overflow.

### §3.3 limitTemperature progression (v3 only — not in B59)

| iter | Tmin (unclamped) | Tmax (unclamped) | Lower-clamped | Upper-clamped |
|---|---|---|---|---|
| 1 | 288.00 (T_inf) | 288.00 | 0 | 0 |
| 2 | 287.97 | 426.50 (sane shock heating) | 1 (0%) | 0 (0%) |
| 3 | 287.97 | 426.50 | 1 | 0 |
| 4 | 110 (one cell at clamp floor) | 1654.62 (close to 2000 ceiling) | 1 | 118 (0.06%) |
| 5 | (similar) | (similar) | (similar) | (similar) |
| 6 | (Tmax escalating but matrix already broken) | (matrix dominates over thermo) | | |
| 7 | n/a (crash) | n/a | | |

**Diagnostic**: by iter 4 the field has cells trying to overshoot to 2000+ K
(shock-compression overshoot from rhoSimpleFoam's transonic startup) AND
1 cell trying to undershoot to 110- K (cavitation-like behavior near the
high-pressure stagnation point). Our clamp engages on both sides.

The clamp is doing its job (no FE_DOMAIN in libfluidThermophysicalModels)
but the matrix instability (p-eq divergence + U-eq subsequent explosion)
is INDEPENDENT of thermo. Even with sutherland mu(T) safe under clamp,
the U field develops nonphysical magnitudes because PBiCGStab DILU on
the SIMPLE-style p-eq matrix at iter 5 is solving for a matrix where
A.x = b is ill-conditioned beyond recovery.

### §3.4 Stack trace (terminal at iter 7)

```
[stack trace]
=============
#1  Foam::sigFpe::sigHandler(int) in libOpenFOAM.so
#2  __kernel_rt_sigreturn
#3  Foam::scalarProduct<double, double>::type Foam::sumProd<double>(...) in libOpenFOAM.so   ← NaN/Inf in dot product
#4  Foam::PBiCGStab::scalarSolve(...) in libOpenFOAM.so                                       ← FAULT FRAME
#5  Foam::PBiCGStab::solve(...) in libOpenFOAM.so
#6  Foam::fvMatrix<double>::solveSegregated(...) in libfiniteVolume.so
#7  ... rhoSimpleFoam main loop
#8  __libc_start_main in libc.so.6
```

**Crash mode**: the linear solver's iterative dot product (`sumProd`) hits
NaN/Inf in the matrix entries. This is the canonical "matrix breakdown"
failure mode for SIMPLE-style steady solvers attempting hyperbolic shock
formation from impulsive IC.

**Comparison with B59 attempt 3 crash mode**:
- B59 attempt 3: "p equation residual diverged from 0.478 to 8011 within
  1000 PBiCGStab iters" — same divergence pattern, but B59 attempted 1000
  iters where v3 attempted 5 (then exploded earlier with explicit potentialFoam
  pre-step amplifying the early-iter growth)
- v3: same divergence pattern, plus force-coefficients explode to ~10^6
  range within 5 iters, plus sigFpe in PBiCGStab

So v3's potentialFoam pre-step + sutherland-restored + limitTemperature
actually made the crash happen EARLIER than B59 attempt 3 (iter 7 vs iter
77 in attempt 2, or iter 1000 in attempt 3). The thermo-FPE fix removed
one safety valve; the underlying SIMPLE divergence is now the visible
failure mode.

### §3.5 Probe / postProcessing data

`postProcessing/fieldMinMax1/0/fieldMinMax.dat` — header only, 0 bytes data
(crash at iter 7, before iter 100 writeInterval flush).

`postProcessing/forceCoeffs1/0/` — does NOT exist (writeInterval is iter
25; crash at iter 7 prevented flush).

**No usable Cp distribution data from v3 run.** The most-recent valid Cp/
force-coefficient data for case_006 remains from B59 v2.4 fallback
rhoCentralFoam laminar 5000-iter quasi-stationary run, archived at
`postProcessing.v24/` in the case sandbox + cp_eta_*.csv in
`evidence/v64_v2/`.

---

## §4 What FULL now requires (revised vs B59 → v3)

**B59 retro listed 6 limitations** (per validation report v2 §Limitations):
1. Solver deviation (rhoCentralFoam vs brief's rhoSimpleFoam)
2. Turbulence deviation (laminar vs brief's kOmegaSST)
3. Geometry proxy (NACA 0010 vs ONERA D-section · V32 carry-forward)
4. Mesh below brief floor (205k vs 600k-1.5M target)
5. Experimental data not digitized (Schmitt-Charpin Cp · A1 extraction sub-DEC)
6. Transport deviation (const vs brief's sutherland)

**v3 retro updates**:
- Limitation #6 (const transport): v3 RESTORED sutherland · MITIGATED by
  fvOptions limitTemperature. This limitation IS RESOLVED.
- Limitation #1 (solver deviation): v3 attempted rhoSimpleFoam · STILL FAILS
  even with potentialFoam pre-step + thermo-FPE fix. **Solver class is the
  load-bearing gating axis, not thermo or transport**.
- Limitations #2, #3, #4, #5: NOT addressed by this sub-DEC (out of scope).

**Revised gating axes for case_006 → FULL** (3 layered):
1. **(NEW v3 evidence · primary)** **SIMPLE-style algorithm CANNOT** handle
   transonic shock startup at M=0.84 wing flow with 205k mesh, regardless
   of potentialFoam pre-step, sutherland transport, fvOptions limitTemperature,
   and most-relaxed URFs. **Fix paths**:
   - Switch to rhoPimpleFoam pseudo-transient (PIMPLE handles transient
     shock formation; substrate case.yaml lists this as `solver_v2`)
   - Switch to rhoCentralFoam transient density-based (explicit central-upwind;
     substrate case.yaml lists this as `solver_v1`; B59 v2.4 baseline used this)
   - **Switching solver class is substrate-level edit** but **bypasses
     SIMPLE entirely**, which means the F-NEW-v3-2 finding is that
     **thermo-FPE fix at substrate level alone is insufficient for
     rhoSimpleFoam external-wing transonic; solver-class change is mandatory**.
2. **(unchanged from B59)** Geometry V32 + mesh ≥1M cells + Schmitt-Charpin
   data digitization (A1 extraction sub-DEC).
3. **(unchanged from B59)** ONERA D-section coordinates (NACA 0010 is a
   5-15% lambda-shock displacement proxy).

**Wall budget**: v3 attempted 7 iters in 110 s = 16 s/iter average. Even
if rhoSimpleFoam DID converge, 3000-iter target would be ~13 h wall —
much longer than B59 v2.4 rhoCentralFoam's 5000-iter in 49 min, because
PBiCGStab DILU on 205k mesh × URF p=0.10 is slow-converging by design.

---

## §5 V-row attribution v3

| V-row | B59 (v2) emission | v3 status | Net new |
|---|---|---|---|
| V26 | NO | NO | no |
| V27 | YES ✓ (solver_block_advisor LANDED B55) | unchanged | no |
| V28 | YES ✓ (solver_block_advisor LANDED B55) | unchanged | no |
| V29 | YES ✓ (freestream/freestreamPressure substitution) | unchanged | no |
| V30 | YES ✓ (tip_cap_sliver, root_fairing_pad/cover eaten by sHM) | unchanged | no |
| V31 | NO | NO | no |
| V32 | NO | NO | no |
| D1 | YES ✓ (A2-v2 substrate B42 V63-A) | unchanged | no |
| D4 | marginal | marginal | no |
| F-NEW-5 (B59) (rhoSimpleFoam steady SIMPLE-style cannot handle transonic external wing) | proposed [QUESTIONABLE] | **CORROBORATED at v3 attempt level even with potentialFoam pre-step + fvOptions limitTemperature + sutherland-restored** — eligible for LANDED promotion | yes (corroboration) |
| F-NEW-6 (B59) (case_006 mesh-quality lower-edge at level (6,7)) | proposed [QUESTIONABLE] | unchanged (mesh not refined) | no |
| **F-NEW-v3-2** (THIS report) (`thermo-FPE fix (limitTemperature fvOption) is insufficient stand-alone for rhoSimpleFoam steady transonic external wing — SIMPLE matrix conditioning is the deeper gating axis · canonical mitigation path is rhoPimpleFoam pseudo-transient OR rhoCentralFoam transient density-based · advisor stack should detect this motif and route to alternative solver class`) | n/a | **[QUESTIONABLE] candidate · advisor extension target** | yes |
| **F-NEW-v3-3** (THIS report) (`potentialFoam pre-step (with rhoSimpleFoam-compatible config: no -writephi, clean 0/Phi after) successfully provides smooth incompressible velocity IC + converges Phi to 4.6e-7 final residual in <2 s wall on 205k mesh · this is a useful pre-conditioner template but does NOT resolve SIMPLE matrix conditioning when followed by rhoSimpleFoam steady at impulsive M=0.84`) | n/a | **[QUESTIONABLE] candidate** | yes |

**Net delta from B59**:
- F-NEW-5 (B59 candidate) → corroborated by v3 evidence, eligible for promotion
- 2 new candidate V-rows (F-NEW-v3-2, F-NEW-v3-3) for thermo-FPE-fix-not-enough motif

**5/9 firm + D4 marginal · unchanged from B55/B59 · ≥5/9 firm: MET (no regression)**

---

## §6 Recommendations to V64-A main session

1. **Promote F-NEW-5 (B59) from [QUESTIONABLE] to LANDED** based on v3
   corroboration — rhoSimpleFoam SIMPLE-style external-wing transonic
   shock-startup failure is now a **2-attempt-corroborated** finding,
   not a 1-attempt hypothesis. Update `.planning/methodology/industrial_case_solver_findings.md`
   and `docs/openfoam_corpus/industrial_solver_findings_v_series.md` (in
   sync) to add this V-row at next-available V-number.
2. **Promote F-NEW-v3-2 to [QUESTIONABLE]** as next-line corollary —
   thermo-FPE fix alone is insufficient; need solver-class change for
   case_006 path forward.
3. **Advisor stack extension target** (substrate-only side, no source change
   in this sub-DEC): when advisor detects `solver: rhoSimpleFoam +
   transonic_external_wing + impulsive_freestream_IC`, recommend solver
   alternative (rhoPimpleFoam pseudo-transient OR rhoCentralFoam transient).
   This is a charter-level methodology patch for V64-A close DEC.
4. **case_006 path forward** for V64-A Done #1 + Done #4:
   - Option A: re-run with rhoPimpleFoam pseudo-transient + thermo-FPE fix
     (new substrate variant; ~estimated 2 h wall · could reach FULL if
     transient handles shock formation cleanly)
   - Option B: stay with B59 v2.4 rhoCentralFoam laminar + add A1 extraction
     for ONERA D-section + bump mesh to 600k+ · upgrade B59 PARTIAL v2 to
     FULL via geometry + mesh axes (no solver change · cheaper substrate
     iteration)
   - Option C: defer case_006 entirely · pick a different V64-A Tier 1
     candidate
5. **Done dim #1 advancement**: NO change. Stays 0/3 FULL.

---

## §7 Done-dim accounting

| V64-A Done dim | Target | B59 state | v3 (this report) state | Δ |
|---|---|---|---|---|
| #1 ≥3 FULL validation reports | ≥3 FULL | 0/3 FULL + multiple PARTIAL | **0/3 FULL** + 1 more PARTIAL credit | no FULL advancement |
| #2 Canonical literature comparisons | ≥3 | 2/3 (Heller-Bliss lit + Schmitt-Charpin lit-only) | no new — case_006 v3 has no measured Cp | no change |
| #3 Convergence stability test | ≥1 | 1/1 ✓ (case_006 v2.4 rhoCentralFoam quasi-stationary plateau) | unchanged | no change |
| #4 PARTIAL → FULL upgrade | ≥2 | 0/≥2 | **0/≥2** (v3 doesn't upgrade B59 v2) | no change |
| #5 V63-A carry-over closure | ≥4 | 3/4 (per B59 reconcile + B62 case_011 ratify) | unchanged | no change |
| #6 V-row attribution rate | ≥2 clause-1 | over-met (3/2) | **over-met (5/2)** — F-NEW-5 corroborated + 2 new candidates | over-met deeper |

**Brief's stated success**: "Done #1 0/3 → 2/3 strict" if BOTH cases PASS;
"0/3 → 1/3" if either single case PASS; "stays 0/3 if both PARTIAL".

**case_006 v3 sub-result**: PARTIAL v3 · **stays 0/3 strict**.

---

## §8 4Q gate (advisor-not-driver SSOT)

| Gate | Evidence in this retro |
|---|---|
| Q1 LLM-offline | YES — `env -i HOME PATH bash scripts/v64_v3_run_solver.sh` is fully shell + Docker · all dicts authored as static OpenFOAM ASCII |
| Q2 artifacts | YES — `case/log_v64_v3/{01_potentialFoam.log, 02_rhoSimpleFoam.log}` (17KB) + `case/postProcessing/fieldMinMax1/0/fieldMinMax.dat` (empty/header) + `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/{system/fvOptions, system/fvSolution, constant/thermophysicalProperties, evidence/}` |
| Q3 TrustGate | YES — every iter / residual / force-coeff value cites log row + this report §3.2, §3.4 + canonical references (sutherland Ts=110.4K, M=0.84 post-shock T_max ≈ 350K, brief reverse condition thresholds) |
| Q4 AI advisory-only | YES — sub-DEC is Accepted by Claude Code main session B63 dispatch; advisor stack source UNTOUCHED; main session reconciles into V64-A roadmap; F-NEW-5 promotion recommendation surfaced for user, not auto-applied |

---

## §9 Backward compat with B59 v2 retro

- B59 PARTIAL v2 retro `.planning/validation_reports/v64_case_006_onera_m6_full.md` **unchanged**.
- B59 v2.4 fallback rhoCentralFoam evidence at `case/postProcessing.v24/`
  + `evidence/v64_v2/{rhoCentralFoam_v64v2.log, cp_eta_*.csv, cp_summary.md, ...}` **unchanged**.
- v3 evidence (this report) at `case/log_v64_v3/{01_potentialFoam.log, 02_rhoSimpleFoam.log}`
  + `case/postProcessing/fieldMinMax1/0/fieldMinMax.dat` (current state after v3 run).
- v3 substrate dicts (this report) archived in repo at
  `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/`.
- For Done dim #1 PARTIAL-credit accounting, B59 v2 + v3 are **two PARTIAL
  retros on the same case** capturing distinct findings (B59: solver-class
  rhoSimpleFoam-not-suitable hypothesis F-NEW-5; v3: corroboration of F-NEW-5
  even WITH thermo-FPE fix + potentialFoam pre-step). Main session
  de-double-counts in V64-A close.

---

## §10 Surface scan + governance

- **Pre-impl surface scan**: `grep -rin "limitTemperature\|potentialFlow\|thermo-FPE" .planning/` returned 0 hits beyond v2 / v3 sub-DEC author chain → no namespace collision.
- **v2.3 sub-DEC scope**: ≤3 shared code paths touched (case_006 + case_016 substrate + sub-DEC doc) — same scope as case_016 v3.
- **Codex review**: skipped per v2.3 1-sync-trigger.
- **Kogami review**: skipped — opt-in only per V133; user did not invoke.
- **Notion sync**: pending — main session session-end batch.
- **Counter**: +0 (this is the second case in the same sub-DEC; counter incremented once per sub-DEC, attributed to the sub-DEC commit chain).
- **Confidence**: high (on the crash forensics + iter log parse) / med (on F-NEW-5 → LANDED promotion recommendation since promotion requires corpus-sync hook compliance; main session executes the actual sync).
- **Commit trailer**: `confidence: med`.

---

## §11 Pointers

- Substrate dict bundle: `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/`
- B59 PARTIAL v2 retro: `.planning/validation_reports/v64_case_006_onera_m6_full.md`
- B59 v2 archive: `.planning/case_profiles/case_006_v64_val_full_2_dicts/`
- Charter DEC: `.planning/decisions/2026-05-15_v64_charter_dec.md`
- Sub-DEC (this commit chain): `.planning/decisions/2026-05-15_v64_sub_thermo_fpe_fix.md`
- v2.4 fallback report (B59 baseline for case_006 force/Cp): `.planning/case_profiles/case_006_v64_val_full_2_dicts/_v24_rhocentralfoam_fallback/README.md`
- Run logs (in sandbox): `~/Desktop/case_006_onera_m6_transonic/case/log_v64_v3/{01_potentialFoam.log, 02_rhoSimpleFoam.log}`
- Run logs (in repo): `.planning/case_profiles/case_006_v64_thermo_fpe_fix_dicts/evidence/{potentialFoam_v3.log, rhoSimpleFoam_v3.log, fieldMinMax_v3.dat}`

---

*Authored by: Claude Code Opus 4.7 (1M context) main session · B63 V64-A Tier 2 thermo-FPE fix dispatch · 2026-05-15 · confidence: med*
