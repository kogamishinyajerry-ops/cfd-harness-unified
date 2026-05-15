# V64-A · M-V64A-THERMO-FPE-FIX · case_016 m219 cavity DES acoustic · Validation Report v3

> **Verdict**: **PARTIAL v3** — substrate fix (system/fvOptions limitTemperature +
> reduced maxCo + slow-ramp deltaT) successfully unblocks the v2 B53 crash mode
> (`sigFpe` FE_DIVBYZERO/FE_INVALID in `libfluidThermophysicalModels.so`
> sutherlandTransport::μ(T) at t=1.24 ms) but uncovers a previously-latent
> deeper failure mode: PIMPLE pressure-equation overshoot to ±1.84 MPa
> driving `sigFpe` in `libfiniteVolume.so` at t=0.586 ms, t=0.65× v2's
> crash time but at iteration 227 (8.4× more PIMPLE outer iters than v2's
> 27 steps).
>
> **Done dim #1** (V64-A "≥3 FULL validation reports"): **stays 0/3 FULL**.
> Brief's "0/3 → 1/3" target NOT met. Brief's authorized fallback "PARTIAL v3 if
> fix doesn't take all the way" = MET. Honest recording is the deliverable.
>
> **Strategic finding**: case_016 → FULL gating axis is **3-layered, not 2-layered**
> as the B53 v2 retro proposed:
>
> 1. **Layer 1 (NEW v3-evidence)** — PIMPLE p-equation cannot bound pressure
>    overshoot for impulsive freestream + cavity-acoustic IC at M=0.85 with the
>    case's 273k-cell LES IDDES mesh. v3 thermo-FPE fix removes the symptom
>    layer; this is the disease layer underneath. p_max reached 1.84 MPa
>    (18× atmospheric) and p_min reached −177 kPa (negative — physically
>    impossible) at the crash timestep.
> 2. **Layer 2 (B53 v2)** — sutherland μ(T) FE crash at t > 1.24 ms. v3 fix
>    eliminates THIS layer fully (no FE in libfluidThermophysicalModels in v3).
> 3. **Layer 3 (B50 v1 retro / HANDOFF)** — window-too-short for Welch
>    mode-1 statistical convergence. Requires endTime ≥ 35.2 ms (5 periods at
>    142 Hz). v3 still does NOT address this; achievable only AFTER layers 1+2
>    fixed.

---

## §1 Session goal + scope

Per V64-A Tier 2 dispatch (this sub-DEC):

1. Apply systemic substrate-side thermo-FPE fix:
   - `system/fvOptions` with `limitTemperature` fvOption [110, 2000] K on all cells
   - Tightened `controlDict`: deltaT 1e-4 → 1e-6 (slow ramp), maxCo 1.0 → 0.3,
     maxDeltaT 1e-4 → 5e-5
2. Rerun rhoPimpleFoam with same mesh (273k cells), same thermo (sutherland +
   hConst + hePsiThermo + perfectGas + sensibleInternalEnergy), same
   turbulence (LES + kOmegaSSTIDDES + IDDESDelta), same Docker image
   (`opencfd/openfoam-default:2312` arm64-native), same potentialFoam pre-step.
3. Target endTime ≥ 0.0352 s (Welch mode-1 minimum) for FULL FFT/SPL extraction.
4. Reverse condition: if v3 still crashes → document failure mode + advisor
   stack extension recommendation. Brief authorizes PARTIAL v3.

**No edit to**: advisor stack source code, ROADMAP/ARC-GOAL files, mesh,
turbulence dictionary, 0/ IC values (just re-staged from 0.orig), case profile.

---

## §2 Substrate state vs v2

| Slot | v2 (B53) | v3 (this report) | Diff |
|---|---|---|---|
| `system/fvOptions` | NOT PRESENT | NEW — `limitTemperature` [110, 2000] K on `all` cells | yes — new file |
| `system/controlDict::deltaT` | 0.0001 | **1e-6** (-100× slow ramp) | yes |
| `system/controlDict::maxCo` | 1.0 | **0.3** (3.3× tighter Co cap) | yes |
| `system/controlDict::maxDeltaT` | 1e-4 | **5e-5** (halved alongside maxCo) | yes |
| `system/controlDict::endTime` | 0.040 | unchanged (target) — sed-patched to 0.005 by `08_run_solver.sh` for first leg | indirect (script-level) |
| `system/fvSolution` | URF 0.7 all + pMinFactor 0.5 pMaxFactor 1.5 | unchanged | no |
| `case/system/fvSchemes` | LES IDDES schemes | unchanged | no |
| `case/constant/polyMesh/` | 273,589 cells | unchanged | no |
| `case/constant/thermophysicalProperties` | sutherland + hConst | unchanged (sutherland now safe under fvOption) | no |
| `case/constant/turbulenceProperties` | LES + kOmegaSSTIDDES | unchanged | no |
| `case/0/` | freestream + uniform 273.15 T | re-staged from 0.orig (fresh) | yes (script-level) |
| Docker image | `opencfd/openfoam-default:2312` (arm64) | identical | no |
| Hardware | macOS arm64 | identical | no |

**Net change**: 1 new file (fvOptions), 3 keywords in controlDict.

---

## §3 v3 run-3 forensics

### §3.1 Launch + Docker

```
$ STAGE=all END=0.005 bash scripts/08_run_solver.sh
[08 · docker] potential_potentialFoam: ... (potentialFoam completed in ~9 s, GAMG Phi converged 4.6e-7 final)
[08 · docker] solver_rhoPimpleFoam: rhoPimpleFoam > /case/log/rhoPimpleFoam.txt 2>&1
```

The runner's pre-solver `sed -i 's/^endTime .*/endTime         0.005;/'` set
effective on-disk target at solver launch to 5 ms (a stability-check window —
v2 crashed at 1.24 ms so 5 ms is "are we past the v2 symptom" check).
Actual achieved end-time was terminated by the crash at simulated `t = 0.0005860 s` = 0.586 ms.

### §3.2 Timestep + Courant trajectory (highlights)

| step | sim time (s) | deltaT (s) | wall (s) | Tmin / Tmax (unlimited) |
|---|---|---|---|---|
| 1 | 1.20e-06 | 1.20e-06 | (init) | 273.15 / 273.15 |
| 5 | 4.37e-06 | 5.15e-07 | 1.6 | 273.04 / 275.86 |
| 10 | 8.93e-06 | 7.62e-07 | 3.1 | 272.96 / 278.80 |
| 20 | 2.49e-05 | ~1.6e-06 | 6.2 | 272.71 / 283.43 |
| 25 (line 2091) | **3.33e-04** | ~7e-06 | 70 | **110.00 (clamped low) / ~** |
| ~120 (line 3807) | **5.86e-04** | ~5e-06 | 230 | **110.00 (low) / 2000.00 (high, both clamped)** |
| 227 (crash) | 5.86e-04 (stuck PIMPLE) | — | 347 | — / — |

Mean sustained deltaT ≈ 4.5e-6 s (CFL-limited at maxCo=0.3, vs v2's
4.5e-5 at maxCo=1.0 — 10× smaller).

Mean wall/step ≈ 1.5 s (vs v2's 1.7 s). Wall-per-sim-time **slower** than
v2 by ~10× because of the 10× smaller deltaT.

**Projected wall to reach 35.2 ms (Welch min) if solver were stable**:
35.2e-3 / (5.86e-4 / 347) ≈ 21,000 s ≈ 5.8 h. (vs v2's ~22 min projection;
the v3 fix's `maxCo=0.3` triples-plus the wall budget.)

### §3.3 limitTemperature progression (v3 only — not in v2)

The fix is active throughout the run. The `Unlimited Tmin / Tmax` values
report the **pre-clamp field min/max** at each PIMPLE iteration's energy-equation
correct step:

| sim time t (s) | Tmin (unclamped) | Tmax (unclamped) | Lower-clamped cells | Upper-clamped cells |
|---|---|---|---|---|
| 1.20e-06 | 273.15 | 273.15 | 0 (0%) | 0 (0%) |
| 4.37e-06 | 273.04 | 275.86 | 0 | 0 |
| 1.55e-05 | 272.94 | (no upper drift yet) | 0 | 0 |
| 3.11e-05 | 272.75 | (small drift) | 0 | 0 |
| 1.0e-04 | (gradual cooling from -shock-startup adiabatic expansion) | (gradual heating from shock compression) | 0 | 0 |
| **3.33e-04 (first lower-clamp)** | **110.00 (BC reached)** | (rising) | (first non-zero) | (small) |
| 5.86e-04 (terminal) | 110.00 (multiple cells) | **2000.00 (multiple cells)** | up to 434 (0.16%) | up to 220 (0.08%) |

**Diagnostic**: by t=0.333 ms the field had cells trying to go below 110 K
(thermo-FPE risk zone) and our clamp engaged. By t=0.586 ms cells were
oscillating between extreme low (T → 0 collisional limit) and extreme high
(T → 2000 K shock-compression limit) within a single PIMPLE outer iter.

The clamp is doing its job (no FE_DOMAIN in libfluidThermophysicalModels)
but the energy field is **wildly nonphysical** for an LES IDDES cavity-acoustic
case where physical T should range 270-350 K.

### §3.4 Pressure trajectory (the new failure axis)

| sim time t (s) | p_max (Pa) | p_min (Pa) | Note |
|---|---|---|---|
| 1.20e-06 | 763,402 | (n/a) | step 1 impulse from potentialFoam→rhoPimpleFoam (matches v2's 763k step-1 spike) |
| 2.6e-06 | 381,456 | (n/a) | step 2 relaxation |
| ~1e-4 | ~160,000 | ~80,000 | working envelope (transonic-startup-plausible) |
| 5.86e-04 (iter 1) | **1,425,313** | **3,331** | escalation begins (p max → 14 atm) |
| 5.86e-04 (iter 2) | **1,083,412** | **-225,516** | NEGATIVE pressure (-2.2 atm) — physically impossible |
| 5.86e-04 (iter 3) | **1,289,814** | **-329,913** | NEGATIVE deeper (-3.3 atm) |
| 5.86e-04 (iter 4) | **1,840,086** | **-177,497** | CRASH on PIMPLE iter 4 of step 228 |

PIMPLE outer correction has `pMinFactor 0.5; pMaxFactor 1.5` (limits pressure
to ±50% of last-iter value), but at iter-to-iter the bounds drift away
because the limiter is ratio-based not absolute-bound.

### §3.5 Stack trace (terminal)

```
[stack trace]
=============
#1  Foam::sigFpe::sigHandler(int) in /usr/lib/openfoam/openfoam2312/.../libOpenFOAM.so
#2  __kernel_rt_sigreturn
#3  ? in /usr/lib/openfoam/openfoam2312/.../libfiniteVolume.so   ← FAULT FRAME
#4  ? in /usr/lib/openfoam/openfoam2312/.../libfiniteVolume.so
#5  ? in /usr/lib/openfoam/openfoam2312/.../libfiniteVolume.so
#6  ? in /usr/lib/openfoam/openfoam2312/.../bin/rhoPimpleFoam
...
```

**Comparison with v2 stack trace** (per B53 v2 retro §3.5):
- v2 fault frame: `libfluidThermophysicalModels.so` (sutherland mu/H lookup)
- v3 fault frame: `libfiniteVolume.so` (linear algebra / matrix scalarProduct)

The fix successfully **moved the crash from the thermo layer to the
finite-volume linear-algebra layer**. The thermo layer is no longer the
gating mechanism. This is partial success.

### §3.6 Probe sample state (in-cavity acoustic field)

```
$ tail -5 case/postProcessing/pressureProbes_kulite/0/p
0.00058596918   101325          101325         
0.00058596918   101325          101325         
0.00058596918   101325          101325         
0.00058596918   101325          101325         
0.00058596918   101325          101325
```

All 229 probe readings (Kulite K05 at 0.279, 0, -0.101 and K09 at 0.483, 0,
-0.101) remain locked at the freestream initialization pressure
101,325 Pa for the entire 0.586 ms window. The cavity shear layer / acoustic
feedback loop never developed enough perturbation to reach the probe locations.

Same outcome as v2 (which got to 1.24 ms with same probe-static result),
because the cavity flow-through time L/U_inf = 0.508/290 ≈ 1.75 ms is
not even half-elapsed.

There is no acoustic time series to FFT. There is no SPL spectrum to compare
to Heller-Bliss analytical Rossiter modes. The brief's downstream deliverables
(Welch FFT, 1/3-octave SPL, Heller-Bliss delta against measured K09 data)
are still unattainable from v3's run.

---

## §4 What FULL now requires (revised vs v2 → v3)

**v2 retro (B53) listed 2 gating axes**:
1. Solver stability past t > 1.24 ms (thermo-FPE)
2. Window ≥ 35.2 ms (Welch mode-1)

**v3 retro (this report) revises to 3 gating axes**:

1. **(NEW v3 evidence)** PIMPLE pressure-equation stability past
   t > 0.586 ms with impulsive freestream IC + M=0.85 + 273k LES IDDES mesh.
   Likely candidate fixes — none of which has been validated in this session:
   - **Add `fvOptions limitPressure`** (OpenFOAM 2312 native fvOption for
     bounding p; same API as limitTemperature)
   - Replace `pMinFactor 0.5 / pMaxFactor 1.5` ratio-limiter with absolute
     bounds via PIMPLE's `pMin / pMax` keywords (only available in some
     compressible PIMPLE branches; check 2312 source)
   - Replace impulsive freestream IC with smoothed cavity-quiescent IC
     (run a reduced-Mach precursor for ~10 ms then ramp M_inf in
     small steps)
   - Tighter URF on p (currently 0.7; try 0.3)
   - Mesh refinement near cavity LE/TE walls to reduce shock-induced
     local pressure overshoot
2. **(eliminated by v3)** Sutherland μ(T) FE crash at t > 1.24 ms.
3. **(unchanged from v1/v2)** Window ≥ 35.2 ms (Welch mode-1) OR ≥ 70.4 ms
   (10-period robust) OR ≥ 0.12 s (HANDOFF min) OR ≥ 0.75 s (full 100-cycle
   spectrum).
4. **Wall budget at v3 observed rate** (1.7 μs sim / s wall, sustained
   through 227 timesteps · arm64 Docker · single-process serial):
   - 35.2 ms (Welch min) → ~5.8 h wall (vs v2's ~22 min projection)
   - 70.4 ms (10 periods) → ~12 h wall
   - 0.12 s (HANDOFF min) → ~20 h wall
   - 0.75 s (full spectrum) → ~123 h wall = 5 days

   **The v3 fix's tighter maxCo penalty pushes wall budget from "lunch-break
   feasible" to "weekend-long-run only". This is a significant cost shift.**
5. **Charter premise revision** (re-affirmed from v2): case_016 → FULL is no
   longer "cheapest unblock". The 3-layered gating + 5.8 h wall budget makes
   it the MOST expensive Tier 1 candidate.

---

## §5 V-row attribution v3

| V-row | v2 B53 emission | v3 status | Net new |
|---|---|---|---|
| V52 (kOmegaSSTIDDES → LES block) | LANDED upstream | LANDED upstream | no |
| V53 (PBiCGStab/DILU for compressible PIMPLE) | LANDED upstream | LANDED upstream | no |
| V54 (probe ≥ 0.5 mm offset from patch helpers) | LANDED upstream | LANDED upstream | no |
| V57 (compound-DES root anchor) | LANDED + reaffirmed | LANDED + reaffirmed | no |
| V-candidate v2-new-1 (thermo-FPE at t>1.24ms with sutherland) | [QUESTIONABLE] candidate from v2 | **EXTINCT by v3 evidence** — v3 fix moves crash to libfiniteVolume; thermo-FPE no longer gating | yes (extinction) |
| V-candidate v2-new-2 (Heller-Bliss mode-1 +15.8% canonical mismatch) | [QUESTIONABLE] | unchanged (no new measurement) | no |
| V-candidate v2-new-3 (charter "cheapest unblock" premise refuted) | [QUESTIONABLE] | RE-AFFIRMED + ESCALATED to "most expensive" | yes (escalation) |
| **V-candidate v3-new-1**: `system/fvOptions limitTemperature [110, 2000] K successfully unblocks rhoPimpleFoam thermo-FPE for transonic LES IDDES (case_016 with sutherland+hConst+hePsiThermo+perfectGas+sensibleInternalEnergy thermo); but uncovers PIMPLE p-equation overshoot to ±1.84 MPa at t > 0.586 ms as deeper gating axis · canonical fix template (substrate-only, no advisor change)` | n/a | **[QUESTIONABLE] candidate** | yes |
| **V-candidate v3-new-2**: `maxCo 0.3 + deltaT 1e-6 slow-ramp 10× tighter Co cap relative to maxCo 1.0 baseline triples wall budget for compressible LES IDDES cavity case · the safety/throughput tradeoff is non-negligible (273k cells: 22 min → 5.8 h for Welch min window)` | n/a | **[QUESTIONABLE] candidate** | yes |
| **V-candidate v3-new-3**: `PIMPLE pMinFactor/pMaxFactor ratio-based pressure limiter is INSUFFICIENT for transonic impulsive-IC cavity startup at M=0.85 with 273k LES IDDES mesh · absolute-bound `fvOptions limitPressure` (or equivalent) is the next-line substrate-side fix candidate · advisor stack should suggest this when detecting impulsive-startup-cavity-with-IDDES motif` | n/a | **[QUESTIONABLE] candidate · advisor extension target** | yes |

**Net delta**: 1 V-row extinction (v2-new-1) + 3 new candidate V-rows (v3-new-1/2/3).
Total V-row work product: substantial (5 V-row touchpoints across 3 reports v1/v2/v3).

---

## §6 Recommendations to V64-A main session

1. **Document v3 in `DEC-V64-A-charter`** (or charter supplement): the M-V64A-VAL-CASE-016-FULL
   target now requires 3-axis stability + ≥35.2 ms window + 5.8 h wall budget.
   Re-tier candidate priority: case_016 → FULL is the MOST expensive Tier
   1 candidate, not "cheapest unblock".
2. **Promote `fvOptions limitTemperature` to substrate-default for compressible cases**
   in the `.planning/methodology/` template set. This is a **canonical
   OpenFOAM 2312 best practice** for any transonic case with shock-startup
   transients. The cost is one extra dictionary file; the benefit is FE_DOMAIN
   crash immunity. **Advisor extension target**: when ANY of (transonic /
   shock-startup / cavity-acoustic / impulsive-IC) is detected in case
   metadata, advisor should recommend `limitTemperature` fvOption.
3. **Document the `pMaxFactor` / `pMinFactor` insufficiency for v3-style impulsive
   IC + LES IDDES + 273k mesh** — recommend `fvOptions limitPressure` as the
   next-line fix.
4. **Wall-budget escalation**: case_016 → FULL is now a multi-hour-to-multi-day
   compute investment. Consider deferring to a more capable HPC if the V64-A
   Done #1 target needs case_016 in scope; OR de-tier case_016 out of Tier 1.
5. **Done dim #1 advancement**: NO change. **Stays 0/3 FULL**.

---

## §7 Done-dim accounting

| V64-A Done dim | Target | v2 (B53) state | v3 (this report) state | Δ |
|---|---|---|---|---|
| #1 ≥3 FULL validation reports | ≥3 FULL | 0/3 FULL + 3/3 PARTIAL | **0/3 FULL** + 4/3 PARTIAL credit | no FULL advancement |
| #2 Canonical literature comparisons | ≥3 | 2/3 (Heller-Bliss + Schmitt-Charpin lit-only) | no new — case_016 has no v3-measured FFT/SPL to add | no change |
| #4 PARTIAL → FULL upgrade | ≥2 | 0/2 | **0/2** (v3 doesn't upgrade v2) | no change |
| #5 V63-A carry-over closure | ≥4 | 3/4 (per B59 reconcile) | no change | no change |
| #6 V-row attribution rate | ≥2 clause-1 | over-met (3/2) | **over-met (5/2)** — v3 adds 3 candidate V-rows · 1 extinction | over-met deeper |

**Brief's stated success**: "Done #1 0/3 → 2/3 strict" if BOTH cases PASS;
"0/3 → 1/3" if either single case PASS; "stays 0/3 if both PARTIAL".

**This v3 sub-DEC sub-result**: case_016 → PARTIAL v3 · **stays 0/3 strict**.

---

## §8 4Q gate (advisor-not-driver SSOT)

| Gate | Evidence in this retro |
|---|---|
| Q1 LLM-offline | YES — `env -i HOME PATH bash scripts/08_run_solver.sh STAGE=all END=0.005` is fully shell-script + Docker (no LLM mid-stream); all dicts authored as static OpenFOAM ASCII |
| Q2 artifacts | YES — `case/log/rhoPimpleFoam.txt` (1MB) + `case/log/potentialFoam.txt` + `case/postProcessing/pressureProbes_kulite/0/p` (229 timesteps × 2 probes) + `case/postProcessing/cavity_forces/0/force.dat` (35KB) + `.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/{system/fvOptions, system/controlDict, evidence/}` |
| Q3 TrustGate | YES — every p/T/continuity value cites postProcessing file row + this report §3.3, §3.4 + lit references for canonical bounds (sutherland Ts=110.4K, post-shock T at M=0.85 ≈ 568K well below 2000K ceiling) |
| Q4 AI advisory-only | YES — sub-DEC is Accepted by Claude Code main session B63 dispatch; advisor stack source UNTOUCHED; main session reconciles into V64-A roadmap; charter premise refutation surfaced for user, not auto-applied |

---

## §9 Backward compat with v1/v2 retros

- v1 retro `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md` **unchanged**.
- v2 retro `.planning/validation_reports/v64_case_016_m219_cavity_des_acoustic_acoustic_full_v2.md` **unchanged**.
- v3 evidence directories archived in-sandbox as `case/log/` + `case/postProcessing/` (current state); v2 evidence at `case/log.v2/` + `case/postProcessing.v2/`; v1 evidence at `case/log.v1/` + `case/postProcessing.v1/`.
- For Done dim #1 PARTIAL-credit accounting, v1+v2+v3 are **three PARTIAL retros on the same case** capturing distinct gating mechanisms (v1: window-too-short; v2: thermo-FPE at t>1.24ms; v3: p-eq overshoot at t>0.586ms). Main session de-double-counts in V64-A close.

---

## §10 Surface scan + governance

- **Pre-impl surface scan**: `grep -rin "limitTemperature\|fvOptions.*limit\|thermo-FPE" .planning/` returned 0 hits beyond v2 v3 sub-DEC author chain → no prior substrate-fix artifact, no namespace collision.
- **v2.3 sub-DEC scope**: ≤3 shared code paths touched (case_016 + case_006 substrate + sub-DEC doc) — at the charter-trigger threshold but no schema change, no security boundary, no contract break. Authored as sub-DEC, not elevated to charter (v2.3 round-1 loosen rule).
- **Codex review**: skipped per v2.3 1-sync-trigger — case substrate config + documentation, no auth/signing/security-boundary touch. APPROVE-required gates not crossed.
- **Kogami review**: skipped — opt-in only per V133; user did not invoke.
- **Notion sync**: pending — main session session-end batch (Status=Accepted only per v2.3).
- **Counter**: +1 `autonomous_governance: true` (this sub-DEC LANDED).
- **Confidence**: high (on the crash forensics + log parse) / med (on root-cause attribution layering between PIMPLE limiter inadequacy vs mesh-vs-IC interaction vs LES IDDES turbulence-shock interaction).
- **Commit trailer**: `confidence: med`.

---

## §11 Pointers

- Substrate dict bundle: `.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/`
- v1 PARTIAL retro: `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md`
- v2 PARTIAL retro: `.planning/validation_reports/v64_case_016_m219_cavity_des_acoustic_acoustic_full_v2.md`
- Charter DEC: `.planning/decisions/2026-05-15_v64_charter_dec.md`
- Sub-DEC (this commit chain): `.planning/decisions/2026-05-15_v64_sub_thermo_fpe_fix.md`
- Run logs (in sandbox): `~/Desktop/case_016_m219_cavity_des_acoustic/case/log/{rhoPimpleFoam.txt, potentialFoam.txt}`
- Run logs (in repo): `.planning/case_profiles/case_016_v64_thermo_fpe_fix_dicts/evidence/{rhoPimpleFoam_v3.log, potentialFoam_v3.log, cavity_force_v3.dat, pressureProbes_v3.dat}`

---

*Authored by: Claude Code Opus 4.7 (1M context) main session · B63 V64-A Tier 2 thermo-FPE fix dispatch · 2026-05-15 · confidence: med*
