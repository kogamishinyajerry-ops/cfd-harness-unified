# V64-A · M-VAL-CASE-016-FULL · case_016 m219 cavity DES acoustic · Validation Report v2

> **Verdict**: PARTIAL v2. Solver window extension attempted (intent
> endTime 0.0005 → 0.040 s; sed-patched script-level to 0.020 s for
> the first leg; runtime-modify to 0.040 issued mid-run) but
> rhoPimpleFoam crashed at simulated `t = 0.0012422023 s` (≈1.24 ms,
> 26 timesteps) with `sigFpe` (FE_DIVBYZERO / FE_INVALID) inside
> `libfluidThermophysicalModels.so` during PIMPLE iteration 2 of the
> 27th timestep. ExecutionTime at crash = 46.92 s wall (arm64-native
> Docker `opencfd/openfoam-default:2312`, no Rosetta emulation).
>
> This refutes a key premise of `DEC-V64-A-charter` ("M-V64A-VAL-CASE-016-FULL
> first candidate · **solver already converged 8.5e-8, only window
> extension needed**"). The 8.5e-8 cumulative continuity from V63-A
> B50 v1 was achieved inside the **0.5 ms window only**. Extending
> the same solver/mesh/thermo to 20 ms exposes a thermophysical
> instability that the v1 window never reached. The gating mechanism
> for FULL is therefore **compound**, not single-axis:
>
> 1. **(unchanged from v1)** Window must be ≥35.2 ms for Welch
>    statistical convergence of Rossiter mode 1 at 142 Hz
>    (`5 / 142 ≈ 0.0352 s`), or ≥70.4 ms for the robust 10-period
>    target the V64-A dispatch named.
> 2. **(NEW v2)** Solver must remain stable past `t > 0.0012 s`.
>    Current `case/system/{controlDict, thermophysicalProperties,
>    fvSchemes, fvSolution}` configuration produces a thermo-model
>    floating-point exception in PIMPLE iter 2 of the 27th timestep
>    under the same potentialFoam-initialized state that v1 used.
>
> **Done dim #1** (V64-A "≥3 FULL validation reports"): **stays 0/3
> FULL**. Brief's "0/3 → 1/3" target NOT met. Per the dispatch
> contract, the brief explicitly authorized this branch:
> "如果延长后 solver 不稳定 → 完整记录 + 退到 PARTIAL v2 (不是
> fail · 是 case-side limit 暴露)". Honest recording is the
> deliverable.
>
> **NET-NEW vs V63-A B50 PARTIAL v1 retro**: v1 documented one
> gating axis (window-too-short, advisor stack predicted gap, HPC
> long-window re-run prescribed). v2 documents the second
> previously-latent gating axis (thermo-FPE at t > 1.24 ms) and
> therefore upward-revises the FULL cost estimate. The charter's
> "cheapest unblock" framing for case_016 is now refuted by direct
> measurement; main session should reconsider Tier 1 priority.
>
> **Honesty discipline observed**: no fabricated SPL data, no
> fabricated Heller-Bliss comparison delta against measured spectra
> (none captured), no claim of convergence beyond what the log
> shows, no edit to `ui/backend/services/advisor_stack.py` or any
> advisor source, no mesh refinement, no kill of port-occupying
> process.

---

## §1 Session goal + scope

Per V64-A Tier 1 first-sub-DEC dispatch (verbatim from main session
B53 brief):

1. Land V64-A's first sub-DEC `M-VAL-CASE-016-FULL` by extending the
   case_016 m219 cavity DES acoustic solver window from v1's 0.5 ms
   to a Rossiter-mode-1-resolving window (brief recommended
   "endTime ≥ 4.13 ms, 实际推荐 8-10 ms 保底"; this report uses the
   physically-correct target of ≥35.2 ms = 5 × 1/142 Hz periods,
   correcting the brief's mode-1 frequency math — see §4).
2. Run rhoPimpleFoam to endTime, parse residual / continuity, extract
   FW-H + probe time series, FFT to SPL spectrum, compare against
   Heller-Bliss analytical Rossiter prediction and AGARD CP-437
   published K09 anchors {142 / 353 / 592 / 813 Hz at 141.6 / 146.3
   / 143.4 / 130.2 dB}.
3. Push V64-A Done dim #1 from 0/3 → 1/3 FULL if PASS, or write
   PARTIAL v2 if blocked.
4. No edit to `ui/backend/services/advisor_stack.py`, no advisor
   source change, no mesh refinement, no Notion sync (main session
   batch), no Codex review (case substrate is not a security
   boundary).

**v1 baseline preserved unmodified** at
`.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md`
as diff baseline. v1 evidence directories archived in-sandbox as
`case/log.v1/` + `case/postProcessing.v1/` before the v2 run.

---

## §2 Substrate state vs v1

| Slot | v1 (B50, 2026-05-15) | v2 (B53, this report) | Diff |
|---|---|---|---|
| `case/system/controlDict::endTime` | `0.0005` | `0.040` (intent · sed-patched to `0.020` by `scripts/08_run_solver.sh::run_of` at run time · mid-run runtime-modify to `0.040` issued at t≈47 s wall, never picked up before crash) | yes — main substrate change |
| `case/system/controlDict::deltaT` | `0.0001` | unchanged (`0.0001` · adjustTimeStep yes · maxCo 1.0 · maxDeltaT 1e-4) | no |
| `case/system/controlDict::writeInterval` | `0.005` | unchanged (4 field snapshots over 20 ms; functionObjects already write per timeStep) | no |
| `case/constant/polyMesh/` | 273,589 cells from 02_blockmesh_shm.sh v1 | unchanged (no remesh) | no |
| `case/constant/thermophysicalProperties` | hePsiThermo + perfectGas + sutherland + hConst + pureMixture | unchanged | no |
| `case/constant/turbulenceProperties` | LES + kOmegaSSTIDDES + IDDESDelta | unchanged | no |
| `case/system/fvSchemes` + `fvSolution` | v1 (V52-V54 corrected) | unchanged | no |
| `case/0/` initial state | potentialFoam-initialized for M=0.85 freestream | unchanged (reused v1 init; 0.orig→0 not re-staged) | no |
| Docker image | `opencfd/openfoam-default:2312` (`arm64/linux`) | identical (verified `docker info` arch `aarch64`) | no |
| Host hardware | macOS arm64 | identical (verified `uname -m` = arm64; arm64 image runs native, no Rosetta) | no |

**Net change**: a single keyword in one config file (`endTime
0.0005 → 0.040`). Nothing else. Same mesh, same thermo, same
turbulence model, same numerics, same initial state, same hardware,
same Docker image. The crash is therefore attributable to the
window-extension axis alone, not to any latent substrate drift.

---

## §3 Run-2 (v2) execution forensics

### §3.1 Launch + Docker

```
$ STAGE=solver END=0.020 bash scripts/08_run_solver.sh
[08 · docker] solver_rhoPimpleFoam: rhoPimpleFoam > /case/log/rhoPimpleFoam.txt 2>&1; tail -30 ...
docker container `gifted_galileo` (opencfd/openfoam-default:2312, arm64/linux)
```

The launcher's pre-solver `sed -i 's/^endTime .*/endTime         0.020;/' /case/system/controlDict` overwrote my intended `0.040` setting before solver start, so the effective on-disk target at solver launch was `0.020 s`. Mid-run, I re-edited the host file (volume-mounted) to `0.040 s`; OpenFOAM with `runTimeModifiable true` re-reads `controlDict` periodically, but the crash occurred at wall t ≈ 47 s well before the next re-read cycle would have picked up the change. Effective achieved end-time was determined by neither target — the crash terminated the run at simulated `t = 0.0012422023 s`.

### §3.2 Timestep + Courant trajectory

| step | sim time (s) | deltaT (s) | wall (s) | Co mean / max |
|---|---|---|---|---|
| 1 | 6.85e-05 | 6.85e-05 | 4.69 | 0.00228 / 1.4604 |
| 2 | 1.20e-04 | 5.14e-05 | 6.46 | 0.00195 / 1.3393 |
| 3 | 1.65e-04 | 4.48e-05 | 8.25 | 0.00166 / 1.1489 |
| 4 | 2.08e-04 | 4.36e-05 | 9.85 | 0.00157 / 1.0293 |
| 5 | 2.53e-04 | 4.44e-05 | 11.45 | 0.00164 / 0.9858 |
| 6 | 2.98e-04 | 4.52e-05 | 13.05 | 0.00180 / 0.9784 |
| 7 | 3.44e-04 | 4.61e-05 | 14.86 | 0.00203 / 0.9830 |
| 8 | 3.90e-04 | 4.57e-05 | 16.89 | 0.00227 / 1.0020 |
| 9 | 4.36e-04 | 4.56e-05 | 18.61 | 0.00249 / 1.0080 |
| 10 | 4.81e-04 | — | 20.28 | 0.00268 / 1.0035 |
| … | (rate ~26 μs sim / s wall sustained) | … | … | … |
| 24 | 1.095e-03 | 3.68e-05 | 42.25 | — |
| 25 | 1.133e-03 | 3.79e-05 | 43.80 | — |
| 26 | 1.170e-03 | 3.61e-05 | 45.36 | — |
| 27 | 1.204e-03 | 3.51e-05 | 46.92 | — |
| 27 | 1.242e-03 (last successful Time= print) | 3.76e-05 | — | — |
| **28** | **CRASH in PIMPLE iter 2** | — | — | — |

Mean sustained deltaT ≈ 4.5e-5 s (CFL-limited, well below the 1e-4 ceiling). Mean wall/step ≈ 1.7 s. Projected wall to reach 35.2 ms (Welch minimum for mode 1) = **≈ 22 min** if the solver were stable.

### §3.3 PISO / continuity convergence (last 5 timesteps)

| Time (s) | continuity sum local | continuity global | cumulative |
|---|---|---|---|
| 0.001059 | 1.75e-10 | 1.71e-11 | 1.2432e-07 |
| 0.001095 | 1.05e-09 | -5.30e-10 | 1.2379e-07 |
| 0.001133 | 4.33e-10 | 5.47e-11 | 1.2385e-07 |
| 0.001170 | 7.03e-10 | 1.24e-10 | 1.2397e-07 |
| 0.001204 | 3.26e-10 | 6.22e-11 | 1.2403e-07 |

Cumulative continuity stable at ~1.24e-07 (v1 reported 8.5e-08 at t = 0.0005 s, so v2 has drifted up modestly but remains within an acceptable transonic transient envelope; this is not the crash cause).

### §3.4 Pressure-control p_max trajectory

| stage | p_max (Pa) | comment |
|---|---|---|
| step 1 PISO start | 763,402 | potentialFoam→rhoPimpleFoam transient impulse |
| step 1 PISO end | 381,456 | first relaxation |
| step 2 | 172,907 | second relaxation |
| ... | ... | working envelope |
| step 26 | 160,131 | quasi-stable plateau ~1.6 atm |
| step 27 PISO iter 1 | 183,397 | first PISO of crash step |
| step 27 PISO iter 1 (2nd corr) | 182,949 | second pressure corrector |
| step 27 PISO iter 2 | (PIMPLE starts second outer iter) | **CRASH on energy solve** |

The pressure trajectory stayed within a transonic-startup-plausible envelope. The crash signature is not pressure overshoot; it is failure inside the **energy equation solver** (`e`) on PIMPLE iter 2 of step 28, which propagated into `libfluidThermophysicalModels` lookups during `Cp(T)` / `psi(p, T)` evaluation.

### §3.5 Stack trace (verbatim from `case/log/rhoPimpleFoam.txt`)

```
[stack trace]
=============
#1  Foam::sigFpe::sigHandler(int) in libOpenFOAM.so
#2  __kernel_rt_sigreturn
#3  ? in /lib/aarch64-linux-gnu/libm.so.6
#4  ? in libfluidThermophysicalModels.so   ← FAULT FRAME
#5  ? in libfluidThermophysicalModels.so
#6  ? in /usr/lib/openfoam/openfoam2312/.../bin/rhoPimpleFoam
#7  ? in /lib/aarch64-linux-gnu/libc.so.6
```

The fault frame is in the OpenFOAM thermophysical model layer
(stripped symbols, but the chain through `libm.so.6` strongly
suggests a `pow`/`exp`/`log`/`sqrt` call with a domain-invalid input
during T-dependent property evaluation — likely `sutherlandTransport`
viscosity `μ(T) = A·√T / (1 + B/T)` hitting `T ≤ 0` from a local
energy-solver overshoot, or `hConst` enthalpy with extreme T).

### §3.6 Probe sample state (in-cavity acoustic field) — both v1 and v2

```
$ tail -5 case/postProcessing/pressureProbes_kulite/0/p
0.0010586011   101325  101325
0.0010954366   101325  101325
0.0011334450   101325  101325
0.0011694819   101325  101325
0.0012046243   101325  101325
```

**All 26 probe readings (Kulite K05 at 0.279, 0, -0.101 and Kulite K09 at 0.483, 0, -0.101) remain locked at the freestream initialization pressure 101,325 Pa for the entire 1.24 ms window.** The cavity shear layer / acoustic feedback loop never developed enough perturbation to reach the probe locations at this window. This is consistent with the L_cavity / U_inf ≈ 0.508 / 290 ≈ 1.75 ms minimum flow-through time, of which only ~70% elapsed before the crash.

There is no acoustic time series to FFT. There is no SPL spectrum
to compare. The brief's downstream deliverables (Welch FFT,
1/3-octave SPL, Heller-Bliss delta against measured data) are
all unattainable from v2's run, by construction of the achieved
window.

### §3.7 What scripts/09_compute_rossiter_modes.py would emit

The case author's own postp script (read for v2 grounding) enforces a Welch-minimum guard: `min_required_window_s_for_r1_peak_id = 5.0 / 142 ≈ 0.0352 s`. The v2 window is 0.0012 s. The script would emit `window_sufficient_for_r1: false` and skip FFT, by design. Running it for v2 would produce the same fft-skipped JSON the v1 retro already cited; doing so adds no NEW evidence and is therefore omitted.

---

## §4 Heller-Bliss / Rossiter analytical Rossiter prediction (no measured comparison possible)

### §4.1 Mode-1 frequency math correction vs dispatch brief

The B53 dispatch brief stated:

> "Rossiter mode 1 频率 ~2.4 kHz · 周期 ~0.413 ms · 需 ≥10 个周期统计 → endTime ≥ 4.13 ms"

This is physically incorrect. The published m219 cavity mode 1 frequency is **142 Hz** (period **7.04 ms**), per AGARD CP-437 / NTRS ADP010729 and the v1 retro's §6 + HANDOFF.md "What's NOT done" section. The brief appears to have confused **0.413 ms = current solver window** (close to v1's 0.5 ms) with the period. The factor-of-17 ratio in the v1 retro ("17× too short") is `7.04 / 0.413 = 17.04`, which is the window/period ratio, not the frequency.

Correct numbers used in this v2 report:

| Quantity | Value | Source |
|---|---|---|
| Rossiter mode 1 frequency | 142 Hz | AGARD CP-437 (Henderson, 1991); m219 K09 sensor at 95% L |
| Rossiter mode 1 period | 7.04 ms | 1/142 |
| Welch ≥5-period minimum window | 35.2 ms | 5 × 7.04 |
| Robust 10-period window | 70.4 ms | 10 × 7.04 |
| Wall budget at v2's 26 μs sim/s wall rate | ~22 min for 35.2 ms; ~45 min for 70.4 ms | direct extrapolation |

### §4.2 Heller-Bliss formula evaluated for m219 (analytical, no run dependency)

Rossiter (1964) / Heller-Bliss (1971) semi-empirical:

```
f_n = (U_inf / L) · (n - α) / (M + 1/κ)
```

m219 parameters used:

| Parameter | Value | Provenance |
|---|---|---|
| U_inf | 290.0 m/s | `controlDict::functions::cavity_forces::Uinf` |
| L (cavity length) | 0.508 m | `controlDict::functions::cavity_forces::lRef`; m219 spec L = 20 inch |
| M_inf | 0.85 | U_inf / a_inf, a_inf ≈ 340 m/s |
| α (phase lag) | 0.25 (canonical) | Rossiter 1964 |
| κ (convection ratio) | 0.57 (canonical) | Rossiter 1964 |

Then `f_n = (290/0.508) · (n - 0.25) / (0.85 + 1.7544) = 570.87 · (n-0.25) / 2.6044`:

| n | Heller-Bliss predicted (Hz) | Published m219 K09 (Hz) | Δ Hz (HB − pub) | Δ % |
|---|---|---|---|---|
| 1 | 164.4 | 142.0 | +22.4 | +15.8 |
| 2 | 383.6 | 353.0 | +30.6 | +8.7 |
| 3 | 602.7 | 592.0 | +10.7 | +1.8 |
| 4 | 821.9 | 813.0 | +8.9 | +1.1 |

Canonical Heller-Bliss overpredicts low modes by 8-16% and converges to the published anchors at higher modes. An alternative empirical fit `α = 0.40, κ = 0.65` (used in some compressible-cavity references for high-M cases) yields:

| n | (α=0.4, κ=0.65) Hz | Published Hz | Δ Hz | Δ % |
|---|---|---|---|---|
| 1 | 143.4 | 142.0 | +1.4 | +1.0 |
| 2 | 382.4 | 353.0 | +29.4 | +8.3 |
| 3 | 621.4 | 592.0 | +29.4 | +5.0 |
| 4 | 860.4 | 813.0 | +47.4 | +5.8 |

Mode 1 fits within 1.4 Hz with the alternative coefficients but higher modes drift in the opposite direction. The published m219 anchors do not fit a single (α, κ) Rossiter pair cleanly — this is a known limitation of the linear Rossiter model at M ≥ 0.8 (shock-induced phase modulation), well-documented in the cavity-acoustics literature.

**No measured SPL spectrum was captured in v2** (run terminated at t = 0.00124 s before any cavity-acoustic content developed in the probe time series; §3.6). The brief's deliverable "列 dominant mode frequency delta (Hz % error) / 列 dominant mode amplitude delta (dB error) / 列 1/3 octave 整带 SPL delta" cannot be produced from v2's run. The table above is **analytical-only** and is unchanged from what the v1 retro § §4-5 already cited; v2 adds no NEW measured-vs-published evidence on this axis.

---

## §5 V-row attribution v2 (vs v1 B50 delta)

| V-row | v1 B50 emission | v2 B53 status | Net new |
|---|---|---|---|
| V52 (kOmegaSSTIDDES → LES block) | LANDED upstream (HANDOFF) | LANDED upstream | no |
| V53 (PBiCGStab/DILU for compressible PIMPLE) | LANDED upstream | LANDED upstream | no |
| V54 (probe ≥ 0.5 mm offset from patch helpers) | LANDED upstream | LANDED upstream | no |
| V55 (`extra_body_in_fluid` D6 candidate) | [QUESTIONABLE] from v1 | unchanged | no |
| V56 (`curved_surface_tessellation_accuracy` D9 candidate) | [QUESTIONABLE] from v1 | unchanged | no |
| V57 (first compound-DES root anchor) | LANDED | LANDED + reaffirmed | no |
| V81 fail-class (boundary emission missing-annotation + bbox-mismatch) | 2 findings in advisor pass | unchanged (stack not re-run for v2) | no |
| V93 degenerate-physics class | not applicable | not applicable | no |
| **V-candidate v2-new-1**: `rhoPimpleFoam + kOmegaSSTIDDES + sutherland m219 substrate: solver-FPE in libfluidThermophysicalModels at t > 1.24 ms under v1 controlDict + same potentialFoam init` | [QUESTIONABLE 2026-05-15] | candidate for V-series promotion pending second-case corroboration (different cavity / different M / same thermo) | **YES** |
| **V-candidate v2-new-2**: `Heller-Bliss canonical (α=0.25, κ=0.57) overpredicts m219 mode 1 by +15.8% (164.4 vs 142 Hz); alt (α=0.4, κ=0.65) fits mode 1 within 1% but drifts higher modes; m219 does not admit a single Rossiter pair across all 4 modes — shock-modulated phase regime` | [QUESTIONABLE 2026-05-15] | candidate; provenance is literature analysis, not v2 measurement; ready to land if a downstream cavity case corroborates | **YES** |
| **V-candidate v2-new-3**: `V64-A charter assumption "case_016 → FULL is cheapest unblock; only window extension needed" empirically refuted — actual gating is compound (window + thermo-FPE); future charter-elevation drafts must verify "convergence at target window" not just "convergence at v1 window"` | [QUESTIONABLE 2026-05-15] | charter-process candidate; promotion path is via V64-A close DEC or a methodology document update | **YES** |

**Net delta**: 3 candidate V-rows (none of them yet [QUESTIONABLE 2026-05-15] → LANDED — single-case substrate, would need second case corroboration per the standard QUESTIONABLE → LANDED protocol). 0 advisor source change, 0 stack invocation in v2 (the v1 stack pass already established the advisor evidence; v2's substrate-side evidence does not change the advisor verdict).

---

## §6 What FULL now requires (revised vs v1)

v1 retro (B50) said:
> "case_016 → FULL: HPC long-window re-run (endTime ≥ 0.12 s minimum, 0.75 s for full 100-cycle FFT); estimated ≥ 12 h wall on 273k cells; advisor stack predicts gap; not a stack failure, a substrate-window limit."

v2 retro (B53) revises to **compound requirement**:

1. **(NEW gate before window extension)** Stabilize the solver past `t ≈ 1.24 ms`. Likely candidate fixes — none of which has been validated in this session:
   - reduce initial `deltaT` (try `1e-6` first ramp until t > 2 ms, then loosen)
   - tighten PISO pressure tolerance (`p::tolerance` smaller, `nCorrectors` higher)
   - replace `sutherlandTransport` with `polynomialTransport` over a wider T validity range, OR add a `Tmin/Tmax` limiter to `thermophysicalProperties`
   - replace `kOmegaSSTIDDES` with a less LES-aggressive blend (`kOmegaSSTDES` first; revert IDDES only after the cavity-acoustic loop is established)
   - mesh refinement near cavity LE to reduce shock-induced cell-local T overshoot
2. **(unchanged from v1)** After stability achieved, extend to `endTime ≥ 0.0352 s` (Welch ≥5 mode-1 periods minimum) or `≥ 0.0704 s` (10 periods robust) or `≥ 0.12 s` (HANDOFF "v1 minimum") or `≥ 0.75 s` (full 100-cycle spectrum, original Codex kickoff brief target).
3. **Wall budget** at observed v2 sustained rate (26 μs sim / s wall, sustained through 26 timesteps before crash, mesh = 273k cells, arm64-native Docker, single-process serial) — assuming the stability fix doesn't slow the run materially:
   - 35.2 ms (Welch min) → ~22 min wall
   - 70.4 ms (10 periods) → ~45 min wall
   - 0.12 s (HANDOFF min) → ~77 min wall
   - 0.75 s (full spectrum) → ~8 h wall
4. **Charter premise revision**: case_016 → FULL is no longer "cheapest unblock". Alternative V64-A Tier 1 candidates from the charter (case_004 mesh gen v2 + NREL UAE Seq S; case_006 substrate full e2e; case_011 non-degenerate substrate) should be re-evaluated for actual gating cost, not assumed-cheap.

---

## §7 Recommendations to V64-A main session

1. **Update `DEC-V64-A-charter`** (or write a charter-supplement DEC, or fold into V64-A close DEC) to refute the "solver already converged 8.5e-8, only window extension needed" claim. v2 evidence shows the 8.5e-8 was a 0.5 ms-window artifact; the actual production-window stability is not yet established.
2. **Re-tier the charter's M-V64A-VAL-CASE-016-FULL** to either:
   - (a) split into M-VAL-CASE-016-STABILITY-FIX (prerequisite) + M-VAL-CASE-016-WINDOW-EXT + M-VAL-CASE-016-FULL-COMPARE, or
   - (b) defer case_016 to a later V64-A tier and promote case_004 / case_006 / case_011 candidates to Tier 1.
3. **Do not** invoke Codex review on this v2 retro (no source code change, non-security-boundary documentation per v2.3 1-sync-trigger). Do not invoke Kogami (opt-in only per V133; user did not invoke).
4. **Notion sync**: this sub-DEC is `status: Accepted` so it ships in main session's next batch sync per v2.3 Notion-Accepted-only convention.
5. **Done dim #1 advancement**: NO change. Stays 0/3 FULL. If V64-A wants to land a Tier 1 FULL by end of arc, the cheapest remaining candidate from the charter — case_004 + NREL UAE comparison or case_006 full e2e — should be evaluated next, not another attempt on case_016 without the stability fix.

---

## §8 Done-dim accounting

| V64-A Done dim | Target | v1 (B50) state | v2 (B53) state | Δ |
|---|---|---|---|---|
| #1 ≥3 FULL validation reports | ≥3 FULL | 0/3 FULL + 2/3 PARTIAL (PARTIAL-credit) | **0/3 FULL** + 3/3 PARTIAL (adds this v2 PARTIAL to the prior 2) | no FULL advancement |
| (other dims) | per V64-A charter | n/a for this sub-DEC | n/a (sub-DEC scope is only #1) | — |

**Brief's stated success target** ("推 V64-A Done dim #1 0/3 → 1/3") = **NOT MET**. **Brief's authorized fallback** ("如果延长后 solver 不稳定 → 完整记录 PARTIAL v2 · 不掩盖") = **MET**. Net session contract = **honored**.

---

## §9 4Q gate (advisor-not-driver SSOT)

| Gate | Evidence in this retro |
|---|---|
| Q1 LLM-offline (advisor stack reproducible without LLM dependency) | not exercised in v2 (no advisor stack invocation; v1's stack-axis evidence is the authoritative case_016 advisor pass) |
| Q2 artifacts (deterministic on-disk evidence) | YES — `case/log/rhoPimpleFoam.txt` (109,031 bytes) + `case/postProcessing/pressureProbes_kulite/0/p` (26 timesteps) + `case/log.v1/` + `case/postProcessing.v1/` preserved as diff baseline |
| Q3 TrustGate (verdict + reasoning visible to engineer) | YES — this report §1 + §3 + §6 + §7 |
| Q4 AI advisory-only (no AI autonomous decision; engineer / charter ratifies) | YES — sub-DEC is Accepted by Claude Code main session B53 dispatch; main session reconciles into V64-A roadmap; charter premise refutation is surfaced for user, not auto-applied |

---

## §10 Backward compat with v1 (B50) retro

- v1 retro file `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md` is **unchanged**.
- v1 evidence directories archived as `case/log.v1/` + `case/postProcessing.v1/` inside the sandbox (not in repo).
- v2 evidence is `case/log/` + `case/postProcessing/` (current state after v2 run).
- v2 does NOT supersede or replace v1 PARTIAL credit accounting — v1 + v2 are **two PARTIAL retros on the same case** capturing distinct gating mechanisms (v1: window-too-short; v2: thermo-FPE at t > 1.24 ms compound with window-too-short). For Done dim #1 PARTIAL-credit accounting, only one of v1/v2 should count (de-double-counting); main session reconciles in V64-A close.

---

## §11 Surface scan + governance

- **Pre-impl surface scan**: `grep -rin "case_016.*FULL\|VAL-CASE-016" .planning/` returned 0 hits beyond v1 PARTIAL retro + ARC-GOAL B50 line + methodology playbook entries → no prior FULL artifact, no namespace collision (commit trailer `Surface-scan: clean`).
- **v2.3 sub-DEC scope**: 3 shared code paths touched (controlDict in sandbox + this validation report + sub-DEC) — at the charter-trigger threshold but no schema change, no security boundary, no contract break. Authored as sub-DEC, not elevated to charter (v2.3 round-1 loosen rule).
- **Codex review**: skipped per v2.3 1-sync-trigger — case substrate config change + documentation, no auth/signing/security-boundary touch. APPROVE-required gates not crossed.
- **Kogami review**: skipped — opt-in only per V133; user did not invoke.
- **Notion sync**: pending — main session session-end batch (Status=Accepted only per v2.3).
- **Counter**: +1 `autonomous_governance: true` (sub-DEC LANDED).
- **Confidence**: med (high on the crash forensics + log parse + Heller-Bliss math; med on the charter-premise refutation framing since it depends on user accepting "v1's 8.5e-8 was a 0.5 ms-window artifact" as a charter premise rather than a v1 narrow-window observation).
- **Commit trailer**: `confidence: med`.

---

## §12 Pointers

- v1 PARTIAL retro: `.planning/validation_reports/v63_case_016_m219_cavity_des_acoustic_validation_report.md`
- Case profile (in repo): `.planning/case_profiles/case_016_m219_cavity_des_acoustic.md` (B53 v2 sub-section added in commit chain)
- Charter DEC: `.planning/decisions/2026-05-15_v64_charter_dec.md` (`DEC-V64-A-charter` Accepted 2026-05-15)
- Sub-DEC (this commit chain): `.planning/decisions/2026-05-15_v64_sub_val_case_016_full.md` (`DEC-V64-A-sub-M-VAL-CASE-016-FULL` Accepted)
- HANDOFF (in sandbox): `~/Desktop/case_016_m219_cavity_des_acoustic/HANDOFF.md` (2026-05-11 session-author handoff; predicted HPC scope, did NOT predict thermo-FPE at t > 1.24 ms)
- Postp script reused: `~/Desktop/case_016_m219_cavity_des_acoustic/scripts/09_compute_rossiter_modes.py` (window-sufficient guard correctly gates FFT for this case, by case author's own design)
- Run launcher: `~/Desktop/case_016_m219_cavity_des_acoustic/scripts/08_run_solver.sh` (script-level `sed -i endTime` patch behavior is documented here for future debug)

---

*Updated by: Claude Code Opus 4.7 (1M context) main session · B53 V64-A first sub-DEC dispatch · 2026-05-15 · confidence: med*
