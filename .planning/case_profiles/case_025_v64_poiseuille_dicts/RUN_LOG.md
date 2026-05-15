# case_025 · RUN_LOG · simpleFoam laminar Poiseuille

> Commit 3 of 4 — solver run + sampling + analytical comparison
> Build: opencfd/openfoam-default:2312 · linuxARM64GccDPInt32Opt · macOS Apple Silicon host

## Invocation (verbatim · re-runnable)

```bash
# Run as non-root user (required for codedFixedValue dynamic-code compile)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_025_poiseuille_channel/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && simpleFoam' > SIMPLEFOAM_LOG.txt 2>&1

# Sample u(y) profiles + centerline p(x)
docker run --rm --user $(id -u):$(id -g) \
    -v ~/Desktop/case_025_poiseuille_channel/case:/case \
    opencfd/openfoam-default:2312 \
    bash -c 'cd /case && postProcess -func sampleDict -latestTime -dict system/sampleDict' \
    > POSTPROCESS_LOG.txt 2>&1

# Extract + compare to analytical (Q1 LLM-offline pure-stdlib)
env -i HOME=$HOME PATH=/usr/bin:/bin python3 extract_poiseuille.py
```

## Codex sync status

**Skipped**. Same justification as case_022 / case_024 sub-DECs: no security boundary (read-only solver + analysis · no auth / signing / authz / operator endpoint). No byte-reproducibility-sensitive path. No Phase E2E batch. Within v2.3 spike-class-adjacent scope per V64-A charter; sub-DEC executed by main session with confidence:med.

## codedFixedValue setup notes (first time in this repo)

Initial run failed under default `--user root` with:
```
This code should not be executed by someone with administrator rights for security reasons.
```
OpenFOAM blocks dynamic-code (codedFixedValue) compilation when running as UID 0 by design. Fixed by passing `--user $(id -u):$(id -g)` to `docker run`. Compile path then succeeded:
```
Using dynamicCode for patch inlet on field U at line 31 in "/case/0/U/boundaryField/inlet"
Creating new library in "dynamicCode/poiseuilleProfile/platforms/linuxARM64GccDPInt32Opt/lib/libpoiseuilleProfile_3013599ff7a203782dd5043d30408227b9315d3b.so"
Invoking wmake libso /case/dynamicCode/poiseuilleProfile
wmake libso /case/dynamicCode/poiseuilleProfile
    ln: ./lnInclude
    dep: fixedValueFvPatchFieldTemplate.C
    Ctoo: fixedValueFvPatchFieldTemplate.C
    link: /case/dynamicCode/poiseuilleProfile/.../libpoiseuilleProfile_...so
```
Compiled .so persists in `~/Desktop/case_025_poiseuille_channel/case/dynamicCode/` for repeat runs (re-uses on second invocation). **F-NEW candidate** for V-row corpus: codedFixedValue under Docker container needs `--user` flag.

## Convergence summary

| Iter | Ux (init) | Uy (init) | p (init) | continuity (sum local) | Notes |
|---|---|---|---|---|---|
| 1 | 4.4e+00 | (transient) | 1.0e+00 | (startup) | initial setup · field at uniform 0.1 vs codedFixedValue 0.15 max |
| 250 | ~1e-04 | ~1e-04 | ~1e-04 | ~1e-05 | settling |
| 750 | ~1e-08 | ~1e-08 | ~1e-09 | ~1e-09 | approaching strict gate |
| 1375 | 3.22e-12 | 9.86e-09 | 7.36e-11 | 6.27e-11 | **SIMPLE converged** |

Final residuals (last iteration before solver-decision EXIT):
```
DILUPBiCGStab:  Solving for Ux, Initial residual = 3.222223773e-12, Final residual = 3.222223773e-12, No Iterations 0
DILUPBiCGStab:  Solving for Uy, Initial residual = 9.861046369e-09, Final residual = 2.279764306e-10, No Iterations 1
GAMG:  Solving for p, Initial residual = 7.363622796e-11, Final residual = 7.363622796e-11, No Iterations 0
time step continuity errors : sum local = 6.349753119e-11, global = 7.362861863e-14, cumulative = 1.136901407e-05
SIMPLE solution converged in 1375 iterations
```

**Field-count transparency** (per case_024 cavity precedent): laminar simpleFoam has 3 prognostic fields (p, Ux, Uy) — no k/ω. Briefing's "residuals 4/4 < 1e-8" is honored as **3/3 < 1e-8** (field-count adjusted for laminar, NOT gate relaxed). All 3 hit strict at iter 1375; SIMPLE auto-exit fired (not endTime exhaustion). Same convention as case_024 RUN_LOG §2.

Strict-gate compliance on residuals:
- p_kin: 7.36e-11 << 1e-8 ✓ (margin ×135)
- Ux:    3.22e-12 << 1e-8 ✓ (margin ×3100)
- Uy:    9.86e-09 <  1e-8 ✓ (margin ×1.01 — tightest of 3)

## Wall shear stress (analytical cross-check)

simpleFoam wallShearStress functionObject reported at end:
```
min/max(bottomWall) = (-0.0004516952864, -0.0004432961683)  [x-component]
min/max(topWall)    = (-0.0004516952878, -0.0004432961701)  [x-component]
```

Magnitudes range 4.43e-4 to 4.52e-4 m²/s² (kinematic). Analytical:
```
τ_w_kinematic = 3·ν·u_mean/H = 3·1.5e-5·0.1/0.01 = 4.5e-4 m²/s²
```

**CASE_SPEC §4 correction**: CASE_SPEC originally listed τ_w = `2·ν·u_mean/H = 3.0e-4 m²/s²` — that formula was wrong (factor 2 instead of 3). Correct derivation from u(y) = (3/2)·u_mean·(1 - (y/H)²): du/dy|_{y=±H} = ∓3·u_mean/H, so τ_w = ν·|du/dy| = 3·ν·u_mean/H = 4.5e-4. simpleFoam output **confirms the corrected analytical**. This correction is duplicated in `extract_poiseuille.py` comment block and validation report §3.

Sampled vs corrected analytical Δ:
- Δ_min = (4.4330 - 4.5000)/4.5000 × 100% = **-1.49%** (low end of wall-shear range)
- Δ_max = (4.5170 - 4.5000)/4.5000 × 100% = **+0.38%** (high end)
- Δ_mean = **-0.56%**

τ_w as a single statistic (Δ_mean) is within 1%; the spatial range (-1.49% to +0.38%) reflects bilinear-grading cell-size variation along the 0.5 m wall and is within 2% tolerance per CASE_SPEC §6 cross-check.

## Strict-gate verdict (per CASE_SPEC §7)

| Criterion | Target | Achieved | Status |
|---|---|---|---|
| max \|Δu\| at exit station (40 y-points) | < 1% of u_max | **0.0425%** | ✓ PASS (margin ×24) |
| Exit station 40/40 y-points within strict 1% | 40/40 | **40/40** | ✓ PASS |
| Mid-station 40/40 y-points within strict 1% | 40/40 | **40/40** (max 0.286%) | ✓ over-PASS |
| \|Δ dp/dx\| (linear fit x ∈ [0.05, 0.45]) | < 1% | **-0.1233%** | ✓ PASS (margin ×8) |
| residuals (laminar 3/3 field count) | all < 1e-8 | 3/3 ✓ (p 7e-11, Ux 3e-12, Uy 9.9e-9) | ✓ PASS |
| τ_w cross-check (Δ_mean) | < 2% | **-0.56%** | ✓ PASS (margin ×3.6) |
| NO solver crash | always | **converged at iter 1375** | ✓ PASS |
| NO turbulence model | always | **laminar** | ✓ PASS |
| advisor stack untouched | always | **ui/backend/ not modified** | ✓ PASS |

**Strict trifecta** (u 1% AND dp/dx 1% AND residuals 1e-8): ✓✓✓ **3/3 strict PASS**

## Verdict

**FULL** per briefing §canonical reverse condition. First strict-FULL outcome in V64-A Tier 2 arc (6th attempt; prior 5 = PARTIAL/marginal).

## Done dim advancement

- **Done #1**: 0/3 strict → **1/3 strict FULL** (standalone advance)
- Per briefing § reverse condition: "OR standalone 0→1/3 strict ✓"
- If B65 cavity Re=1000 is independently ratified by user as standalone strict-PASS (17/17 u-strict; v needs revisit per cavity-v2 retro work landed in parallel B67 session), Done #1 reaches **2/3 strict FULL**
- This sub-DEC does NOT modify cavity-v2 work or reach into that scope per briefing §out-of-scope

## V-row attribution (anticipated · finalized in validation report)

Reuse from prior V64-A sub-DECs (≥1):
- **V100** (incompressible canonical advisor stack baseline · LANDED B55) — direct reuse ✓
- **V47** (incompressible inlet BC conventions) — partial reuse (codedFixedValue extends V47's `fixedValue` pattern)

F-NEW candidates surfaced this run:
- **F-NEW-A**: codedFixedValue under Docker container needs `--user $(id -u):$(id -g)` flag (security check on UID 0)
- **F-NEW-B**: simpleGrading bilinear single-block symmetric-grading (first time in this repo · different from case_022 multi-region multi-block bilinear)
- **F-NEW-C**: laminar simpleFoam strict 1e-8 residual achievable in 1375 iter on Re=133 plane Poiseuille (lower bound for V64-A residual-depth baseline)
- **F-NEW-D**: CASE_SPEC τ_w formula error caught by sampled vs analytical mismatch (factor 2 vs 3 in 3·ν·u_mean/H · diagnostic value of cross-check)

These F-NEWs will receive V-row IDs in validation report (commit 4) §V-row attribution after distinct-signature verification against existing V100 corpus.

## 4Q gate

- **Q1 LLM-offline**: env -i HOME PATH python3 extract_poiseuille.py re-runnable (pure stdlib · no numpy/pandas/scipy) ✓
- **Q2 artifacts**: SIMPLEFOAM_LOG_TRIMMED.txt (422 lines, every 50th iter sampled) + POSTPROCESS_LOG.txt + 3 sampled .xy files (raw_samples/) + extract_poiseuille.py + 3 CSV results + summary.json + EXTRACT_STDOUT.txt
- **Q3 TrustGate**: every Δ% cites postProcessing file row (exitProfile_p_U.xy:line N) + analytical formula explicit (extract_poiseuille.py:u_analytical line 49) + comparison reproducible from raw_samples/ alone
- **Q4 advisor-only**: NO advisor stack edits (ui/backend/ untouched · this entire sub-session)

## Next action

Commit 4: write validation report + sub-DEC frontmatter+body · update RESUME with verdict · main session reconciles ARC-GOAL + Notion sync.
