# Track C · Advisor e2e — Session 4 · case_009 Sandia Flame D reacting low-Mach

> **Date**: 2026-05-13
> **Track**: C (Claude Code session as M6 advisor, per `feedback_claude_code_is_the_advisor.md`)
> **Mandate**: M6 charter empirical close — widen Track C advisor-e2e coverage across numerics class. Session 1 = incompressible-LES (case_010); session 2 = steady-laminar-CHT-multi-stream (case_011); session 3 = incompressible-RANS-MRF (case_004); session 4 = **reacting low-Mach combustion** (case_009). V38-V42 cluster around chemkin loader / mech-format normalization, hand to a class that no prior session has touched.
> **Subject case**: `~/Desktop/case_009_sandia_flame_d/` v1 (case_009 in 16-case roster · reacting-low-Mach root · Sandia/TUD piloted-jet methane-air flame · DRM-19 19+2 species · PaSR + Cmix=1.0 + kEpsilon)
> **Authored by**: Claude Code Opus 4.7 (1M context)
> **Counter impact**: nil (Track C is methodology validation, not autonomous_governance DEC chain)

---

## 1. Protocol

**Substrate state on arrival** — case_009 v1 is the deepest pipeline state of any Track C case so far (deeper than session 1 case_010 LES, comparable mesh depth to session 2 case_011 v1):

- `scripts/build_cad.py` (Codex CadQuery, 227 LOC) · `scripts/02_verify_defects.py` · `scripts/02c_advisor_exercise.py` · `scripts/04_scaffold_case.py` · `scripts/05_make_dicts.py` (stage-aware) · `scripts/08b_load_chemistry_mech.py` (DRM-19 chemkinToFoam) · `scripts/08d_write_species_bcs.py` · `scripts/08e_write_combustion_properties.py` (stage-aware) · `scripts/09_run_solver.sh` (3-stage cold→ignite→ramp) · `scripts/10b_compute_mixture_fraction.py` · `scripts/10c_compute_temperature_profile.py`
- `case/system/{blockMeshDict,controlDict,fvSchemes,fvSolution,sampleDictTNF}`
- `case/constant/{thermophysicalProperties,combustionProperties,chemistryProperties,turbulenceProperties,reactions,thermo.compressibleGas,g,chemistry/{DRM19,westbrook_dryer_2step},polyMesh}`
- `case/0/` with **28 fields**: U, p, T, k, epsilon, alphat, nut + 21 species mass fractions (H2..AR)
- `case/log_cold.txt` (~23M lines, ~23 MB) · `case/log_ignite.txt` (~35M lines, ~35 MB)
- `case/0.001 .. 0.0055` write-time snapshots
- `inputs/cad_codex_v1.step` (387 KB STEP, 13 named bodies) · `inputs/parts_manifest.yaml` · `inputs/defect_manifest.yaml`
- `evidence/v1/REPORT.md` + `defect_ground_truth.txt` + `d1_advisor_exercise.md` + `d8_advisor_exercise.md` + `face_geometry.json` + `mixture_fraction_report.md` + `temperature_report.md` + `Z_profiles.csv`
- `docs/decisions_v1.md` · `README.md`

Files **absent** vs sessions 1+2: `case/log/01_blockMesh.log` / `02_surfaceFeatureExtract.log` / `03_snappyHexMesh.log` (case_009 uses blockMesh-only axisymmetric wedge; no sHM needed) · `case/system/snappyHexMeshDict` (intentional) · `evidence/v1/check_mesh_summary.json` (replaced by REPORT.md §Mesh quality section). **This forecloses A8 (shm_dict_validator) and A6 (hvac_adpi) 2nd-evidence channels by construction** — case_009 is neither a sHM case nor an HVAC case.

**Blind-mode inputs read** (engineer-equivalent surface, V38-V42 + REPORT.md deferred until §3):

- `scripts/build_cad.py` (full, 227 LOC) — CAD topology + defect placement
- `scripts/08b_load_chemistry_mech.py` (full, 111 LOC) — mech-loader recipe (V41 territory)
- `scripts/05_make_dicts.py` lines around `control_dict_context` (stage-aware logic)
- `scripts/08e_write_combustion_properties.py` (full, 60 LOC)
- `scripts/09_run_solver.sh` (full, 33 LOC) — 3-stage runner
- `case/system/controlDict` · `fvSchemes` · `fvSolution`
- `case/constant/thermophysicalProperties` · `combustionProperties` · `chemistryProperties` · `turbulenceProperties`
- `case/constant/thermo.compressibleGas` — partial scan + `grep "Tlow\s\+300;"` audit (53 species, 13 hit at 300K)
- `case/constant/reactions` head (species block + reactions header)
- `case/0/T` + `case/0/U` + `case/0/N2` (representative field BCs)
- `case/log_cold.txt` head + tail + warning grep counts
- `case/log_ignite.txt` head + tail + warning grep counts + final `Time = ` reached
- `README.md` lines 1-85 (case overview; lines 87-103 listing V38-V42 sediment **were technically read pre-blind-verdict due to README structure** — see §10 pacing notes for protocol-drift note)

## 2. Blind verdict (issued before reading evidence/v1/REPORT.md and the V38-V42 corpus entries)

Ten findings. Strong **P0** cluster around thermo-polynomial-range gap and stage-drift; **P1** cluster around mech-loader automation + PIMPLE-mode choice; **P2/P3** are minor / known-limitation flags. Confidence column reflects evidence strength (direct file/log inspection = high).

| # | Severity | Finding | Confidence |
|---|---|---|---|
| F1 | P0 · governance-drift | **Stage `ignite` controlDict `endTime=0.006s` is inconsistent across three documentation surfaces**: `05_make_dicts.py:79-81` docstring says "v1 demo window: shortened from kickoff's 0.15s to 0.025s"; `05_make_dicts.py:89` code is `0.006`; `09_run_solver.sh` comment says "t_end=0.15s". Same drift on cold stage: code 0.005 vs runner comment "t_end=0.05s". Production `log_ignite.txt` ran from t=0.005 → t≈0.005593 (the value reported in `min/max(T)` final block) = **593 μs of physical-time advancement**. Reader cannot tell from any single artifact what the **intended** v1 window is; the code is authoritative but the docstrings and runner.sh comments are misleading. Not a correctness bug per se — REPORT.md §Convergence Stage B independently states the 0.006 endTime as designed — but a methodology-grade documentation-drift finding | high (direct file inspection · 3-way mismatch verifiable in 30 seconds) |
| F2 | P0 · production-state | **janafThermo Tlow-clamp warning flood at 14.69M lines across the two v1 logs** — `grep -c "out of temperature range" log_cold.txt` = **5,828,511**; `log_ignite.txt` = **8,860,176**. Log file sizes ~23 MB + ~35 MB = ~58 MB combined. The root warning is `attempt to use janafThermo<EquationOfState> out of temperature range 300 -> 3000;  T = 299.99xxx` repeated at every chemistry source-term evaluation per cell per inner PIMPLE iter. **min/max(T) shown in log tail**: cold ends at `294, 1880`; ignite progresses to `294, 1982`. The min=294 K is the fuel-jet inlet (per `0/T` boundary block); it is below the active Tlow=300 K of the dominant `coflow_air` species. Production state of v1 has the warning flood; the patch claimed for it ("after the patch, cold-flow runs cleanly with no warning flood") is contradicted by direct grep | high (direct grep on production logs) |
| F3 | P0 · sediment-state | **Tlow=200K patch is INCOMPLETE in `constant/thermo.compressibleGas`** — `grep "Tlow[[:space:]]\+300;"` returns 13 species: `N2`, `HOCN`, `C3H8`, `H2CN`, `HCCOH`, `CH2CHO`, `HNCO`, `HCCO`, `C3H7`, `CH3O`, `HCNN`, `HCNO`, `AR`. Of those, **N2, AR, CH3O are in the active 21-species DRM-19 set** (N2 = 76.8% mass of `coflow_air` per `0/N2` BC value 0.768; AR = ~1% of air; CH3O is an intermediate species in DRM-19's methane oxidation path). The remaining 10 species at Tlow=300 are inactive in DRM-19 but live in the GRI-3.0 superset thermo file. **Per-species records override the global thermo-file header** in janafThermo (the global header at the top of thermo30.dat sets the FALLBACK Tlow, but per-species `Tlow N` records in 4-line NASA-9 blocks are authoritative). F2 warning flood is a direct symptom of F3 sediment-state defect | high (grep + per-species block inspection) |
| F4 | P1 · loader-automation | **`scripts/08b_load_chemistry_mech.py:patch_thermo_header()` (lines 38-46) only rewrites `THERMO\n` → `THERMO ALL\n`** — does NOT rewrite the global `300.000  1000.000  5000.000` header to `200.000  1000.000  5000.000`. Comment in code says "OpenFOAM chemkinReader expects 'THERMO ALL' (not bare 'THERMO')" — V38 only. **The V41 patch is not in the loader**; it must have been applied manually at v1 sediment time and only partially. Re-running `08b` from scratch (e.g., cache miss on `chem.inp`/`therm.dat`/`tran.dat` after refresh) would regenerate the unpatched thermo file. **Reproducibility risk class**: case_009's "reacting infrastructure validated" claim depends on a manual step not encoded in the case's pipeline | high (direct script read) |
| F5 | P1 · boundary-config | **`0/T fuel_jet` boundary `fixedValue 294K`** is below the N2/AR Tlow=300K, so warnings fire at every fuel-jet-region cell evaluation. The `0/T` file's own inline comment (lines 13-15) explicitly documents that **coflow_air** was bumped from 291 K → 300 K to "stay within thermo polynomial range" but the same bump was NOT applied to fuel_jet. The fuel jet at 294 K is also below the polynomial range — the comment is half-applied. The asymmetric application is detectable from the BC file alone (no need to read REPORT.md) | high (direct file inspection) |
| F6 | P1 · solver-stability | **`fvSolution.PIMPLE { nOuterCorrectors 1; nCorrectors 2; }`** plus log line `PIMPLE: Operating solver in PISO mode` (which OpenFOAM prints when nOuterCorrectors=1). Reacting low-Mach with PaSR + DRM-19 (84 reactions, stiff chemistry) typically benefits from 2-3 outer correctors during the ignite stage when chemistry sources ramp from zero to peak in 200-500 μs. v1 ran 593 μs of ignite without crashing, so PISO-mode is empirically tolerable for this case at this t-window, but **stability margin is thin** and a longer ramp (v2 target 1.0 s) at PISO would likely require either tighter dt or fall back to PIMPLE-mode with nOuterCorrectors=2-3 | med (best-practice convention · not a current failure) |
| F7 | P2 · governance-drift | **`scripts/09_run_solver.sh` cold/ignite stage comment-strings** ("t_end=0.05s" / "t_end=0.15s" / "t_end=1.0s") disagree with `05_make_dicts.py` actual endTime values (0.005 / 0.006 / variable). Same drift family as F1 — different surface (runner script vs dict-writer). The fact that BOTH comments are off by an order of magnitude (.05 vs .005, .15 vs .006) suggests the runner.sh was authored against the kickoff brief's original windows and not updated when the v1 demo-window shortening was applied | high (direct file inspection) |
| F8 | P2 · solver-relaxation | **`relaxationFactors.equations { ".*" 1.0; }`** — no under-relaxation on any equation. For transient PIMPLE with PaSR + 84-reaction chemistry source, this is aggressive; ignite stage's first ~100 μs (chemistry initialization) would benefit from light under-relaxation (e.g., `Yi 0.7` or `h 0.8`) until the flame structure stabilizes. Not a current failure — v1 ran — but a thin stability margin for v2 ramp | med |
| F9 | P3 · scheme-redundancy | **`fvSchemes.divSchemes` declares both `div(phi,Yi_h) Gauss multivariateSelection { ... }` (the 21-species + h block, canonical for reactingFoam) AND `div(phi,Yi) Gauss limitedLinear 1` (a generic fallback)**. The fallback is either dead code or covers a code-path I am not aware of in reactingFoam internals. Cosmetic concern at most | low |
| F10 | P3 · physics-coverage | **No `radiation` model dict** in `constant/`. Sandia Flame D is experimentally well-approximated as optically thin, so this is documented best practice (REPORT.md §Limitations row 5 acknowledges as v3 candidate). Flagged for completeness, NOT a correctness issue | low |

**Cluster-level interpretation** (issued before §3 ground-truth read):

The three P0 findings (F1 stage-drift, F2 warning flood, F3 thermo patch incomplete) form a coherent **production-vs-sediment-state delta** cluster: the case_009 v1 sandbox is in a state where the **sediment record** (V38-V42 series, REPORT.md "VALIDATED" claims) over-promises relative to the **production state** (warning flood persists, patch not in loader, stage-drift across docstrings). This is the strongest reusable finding of the session — a sediment-correction-grade observation. I expect §3 ground-truth read to show V41 sediment claims "fix applied + cold-flow runs cleanly" — and the §3 verdict will be that this claim is currently false. The other findings (F4-F10) are second-order details.

**Hypothesis going into §3**: V41 should be `[QUESTIONABLE]` not `[VALIDATED]`; the V41 verification at sediment time was the unit-test ("chemkinToFoam succeeds without erroring out") not the integration-test ("logs are warning-clean").

## 3. Ground truth comparison

Read after blind verdict committed: `evidence/v1/REPORT.md` (167 lines) + `.planning/methodology/industrial_case_solver_findings.md` V38..V42 (5 rows, ~50 lines each) + `README.md` lines 87-103 (V-findings sourced section).

**V38** (THERMO ALL header): handled by `08b_load_chemistry_mech.py:patch_thermo_header` lines 38-46. **`[VALIDATED]` standing is correct** — script automates the patch. Blind verdict did NOT surface anything in V38 territory (the patched header is invisible from downstream artifacts).

**V39** (transport END terminator): handled by `08b_load_chemistry_mech.py:patch_tran_end` lines 49-55. **`[VALIDATED]` standing is correct** — script automates the patch. Blind verdict did NOT surface anything in V39 territory.

**V40** (transport-input dual-mode: chemkin tran.dat vs OpenFOAM-format dict): case_009 v1 uses the OpenFOAM-dict path (`08b` lines 87-95 writes `transportProperties` if missing). Blind verdict did NOT surface this; transport-input choice is invisible from the field-side files I read.

**V41** (thermo header Tlow=300 vs per-species Tlow=200; warning flood eats CPU): Sediment claims `[VALIDATED 2026-05-08]`, "Edit thermo30.dat header before chemkinToFoam: `sed 's/^   300.000  1000.000  5000.000/   200.000  1000.000  5000.000/'`. Idempotent; preserves per-species records (which already support Tlow=200). Verified by inspection of converted constant/thermo.compressibleGas: all species now show `Tlow 200; Thigh 3500;`. After the patch, cold-flow runs cleanly with no warning flood". **Both claims fail blind verification**: (a) 13 species in `thermo.compressibleGas` still have Tlow=300 (per F3 grep); (b) log_cold has 5.8M warnings (per F2 grep). This is the strongest contradiction the session surfaces.

**V42** (A2 advisor `_run_shared` cross-topology PASS as 6-of-6 confirmation): blind verdict does not touch — A2 advisor outputs live in `evidence/v1/d1_advisor_exercise.md` which I deferred to §3. Acknowledged hit on `[QUESTIONABLE]` standing per V25; no new finding from this session on V42 (case_010 = session 1 already extended to 7-of-7).

**REPORT.md §Convergence Stage B** (line 99): `t = 0.005 → 0.006 s, dt = 1e-6 (1000 steps)` — confirms F1 stage-drift IS in `05_make_dicts.py` 89 by design; the drift is the docstrings (lines 79-81 "0.025s") and runner.sh comments ("t_end=0.15s"), not the code. **F1 downgraded**: still a real documentation-drift finding (3-way disagreement) but the "actual run" was per spec.

**REPORT.md §Limitations row 3** (line 131): "Coflow T = 300 K vs Sandia spec 291 K — 3% perturbation, documented". F5 is acknowledged for coflow but NOT for fuel_jet — the half-applied band-aid is precisely what F5 surfaces.

**REPORT.md §Limitations row 5** (line 135): no radiation, v3 candidate. F10 known.

**README §What ran in v1 baseline** (line 56): "blockMesh wedge | ✓ 11600 cells, max skew 0.33, non-orth 0" — confirms case_009 is blockMesh-only (no sHM). A8 channel **closed by construction**.

## 4. Score

| Blind finding | vs corpus + REPORT | Verdict |
|---|---|---|
| F1 ignite endTime 0.006 vs docstring 0.025 vs runner 0.15 (3-way drift) | not in V-corpus; REPORT.md §Convergence confirms code is canonical | **NEW · governance-drift class · DOES NOT promote to V-row** (documentation-only; recorded in retro §6 deliverables list only) |
| F2 14.7M warning flood persists in production logs | V41 claims warning flood eliminated by patch — **contradicted** | **NEW V91 (compound row sub-mechanism α): symptom-level falsification of V41 `[VALIDATED]`** |
| F3 Tlow=200 patch incomplete: 13 species still 300; N2/AR/CH3O active | V41 claims "all species now show Tlow 200" — **contradicted** | **NEW V91 (sub-mechanism β): defect-level falsification of V41 `[VALIDATED]`** |
| F4 08b loader does NOT automate V41 patch | V41 reference-case says function "covers both V38 and V41" — **contradicted by direct script read** | **NEW V91 (sub-mechanism γ): reproducibility-state falsification of V41 sediment** |
| F5 0/T fuel_jet=294 not bumped; only coflow was | REPORT.md §Limitations row 3 acknowledges coflow only | **partial hit** (REPORT acknowledges half; F5 widens to the missing-half) — folded into V91 root-cause |
| F6 PIMPLE nOuterCorrectors=1 (PISO mode) for ignite | not in V-corpus | retro note (LOW · best-practice flag · v2 ramp may need PIMPLE) |
| F7 09_run_solver.sh stage comments wrong | not in V-corpus | retro note (same drift family as F1) |
| F8 relaxationFactors all 1.0 | not in V-corpus | retro note (LOW) |
| F9 div(phi,Yi) fallback redundant | not in V-corpus | retro note (LOW) |
| F10 no radiation | REPORT.md §Limitations row 5 explicit | hit (REPORT-acknowledged) |
| (V38, V39, V40, V42 corpus hits) | invisible from blind surface (script-patched / dict-path / advisor-output) | not surfaced — expected miss class |

**Tally**: 1 net-new V-row (V91, compound, 3 sub-mechanisms) + 1 partial hit folded into V91 root-cause (F5) + 1 REPORT-acknowledged hit (F10) + 4 minor retro notes (F1, F6, F7, F8, F9) + 4 V-corpus expected-misses (V38/V39/V40 patched at script-level invisible; V42 advisor-output-only).

**Hit rate vs V38-V42 (5 rows): 1/5** explicit-touch on **V41** with sediment-correction-grade evidence that `[VALIDATED]` standing is currently wrong. V38/V39 not blind-surfaceable (script automation hides the surface). V40 not blind-surfaceable (transport-input choice invisible from field files). V42 not blind-surfaceable (advisor-output exercise lives in evidence/, deferred to §3).

The Track C session 4 caught **one load-bearing sediment-state error** that the case_009 v1 sub-session author + V-series sedimentation pipeline both ratified:

- **V41 sediment status `[VALIDATED 2026-05-08]` is currently false in two independently-verifiable ways**: (a) 13 species still at Tlow=300 (defect side); (b) 14.7M warning lines in production logs (symptom side). The patch was authored aspirationally; v1 production state has neither the defect resolution NOR the symptom elimination V41 claims.

## 5. What this validates / what it doesn't

**Validates**:

- The Track C protocol reproduces on a **fourth numerics class** (reacting low-Mach) — the most physically distinct yet, and the only one with active chemistry source terms. Blind-verdict capability surfaces the V41 sediment-state error at production-log grep level, demonstrating that the protocol can falsify previously-`[VALIDATED]` rows when the production state regresses or when sediment was aspirational. **Pattern 6 closure across 4 numerics classes**: protocol robustness independent of fluid/physics family.
- **Sediment-state-correction is a first-class finding output of Track C**. Sessions 1+2+3 surfaced NEW V-rows in territory the source-case author had not covered; session 4 surfaces a NEW V-row that **retroactively corrects** a previously-landed row. This is a new finding class for Track C — sessions 1-3 established the "discover gap" mode; session 4 adds the "audit prior sediment" mode. Both modes use the same blind-protocol.
- **Production logs are a load-bearing source for sediment-status verification**. F2's warning-count grep took ~10 seconds and is reproducible by any future blind reader. The defect-level grep on `thermo.compressibleGas` took ~5 seconds. Together they constitute a 15-second falsification of a `[VALIDATED]` row that had stood unchallenged for 5 days. **Lesson for future sediment authors**: include the cheap verification grep commands in the `Status` column at sediment time so they're reproducible without reading the entire reference case.
- **V83 "intent-cross-reference" pattern overdetermined further**: V83 → V88 sub-mechanism a (session 3 mrf_audit) → V91 (session 4 V41 sediment) is the 4th cross-application of the same methodology gap across 4 surfaces (mesh_ok, mesh_summary, mrf_audit, V-series sediment itself). The cross-cutting `audit_verdict_semantics_advisor` (Pillar-2 candidate noted in session 1+2+3 retros) is now overdetermined for extraction; **V91 broadens its scope to include V-series sediment-status as a verifiable artifact class**.

**Does NOT validate**:

- **A6/A8 2nd-evidence pathway: NOT advanced**. case_009 is reacting-low-Mach (not HVAC, no ADPI surface → A6 channel closed) and uses blockMesh-only axisymmetric wedge (no sHM dict → A8 channel closed). Both promotion gates remain at 1-case sediment after session 4. **Honest negative on the briefing's leverage-point hypothesis** ("case_009 chemistry dict could be A8 candidate scope") — chemistry dicts ARE dict-validation surface in principle but they get processed by chemkinToFoam BEFORE sHM ever runs, so the `shm_dict_validator` scope doesn't cleanly extend. A V41/V91-aware advisor is a separate scope (A10 candidate registered).
- **The V41 patch fix-verification arc is NOT closed**. V91 surfaces V41-incomplete; the actual completion (extending 08b_load_chemistry_mech.py to walk per-species records OR bumping 0/T fuel_jet to 300K) is **case_009 v1.5 sub-session scope, deferred**. Track C session 4 produces the audit finding, not the fix.
- **A10 (`thermo_polynomial_range_advisor`) is registered as candidate but extraction is deferred**. The 16-case roster has no other reacting case; promotion gate requires either a 2nd reacting case in a future milestone or a thermo-range issue surfacing in a non-reacting case (e.g., compressible-RANS with cold inlet T below a species' Tlow if any future case has a non-air mixture with extended thermo).
- **F1/F7 governance-drift findings do not promote to V-rows**. They are documentation-only — production behavior is correct per code. Recorded in this retro as methodology notes; would only escalate to V-row if a future bug is traced to someone acting on the wrong docstring (e.g., extending ignite to "0.025s" mentioned in docstring without realizing the code is 0.006).

**Caveats**:

- **Pacing — 4th session same day**: sessions 1+2+3+4 all 2026-05-13. Session 1 §7 recommended ≥1 week cadence; session 3 §10 noted "3 sessions / 1 day" already deviated. Session 4 extends this to **4 sessions / 1 day**. Per main-session direction (briefing §pacing-warning), this is acknowledged as user-directed accelerated cadence beyond original session-1 §7 weekly recommendation. **Risk addressed** = arc-velocity (Track C counter 3→4 closes more of the Done Definition target ≥6 within active context window). **Risk incurred** = (a) priming bias visible in F2/F3/F4 surfacing as V91 compound row — this *is* mostly net-positive (V91 is a strong audit finding) but the same priming made me almost frame F1 + F7 as V-row candidates before checking REPORT.md §Convergence confirmed the code as canonical; (b) cumulative token-spend across 4 sessions ~250-280k tokens; (c) inter-session methodology-pattern reuse — I leaned heavily on the V83 cross-application frame from sessions 1-3 to position V91 as the 4th cross-application. The frame fits genuinely (V91 IS an intent-cross-reference pattern) but reads as suspiciously rapid pattern-fitting.
- **README.md V-findings section spoiler**: README lines 87-103 list V38-V42 names and one-line descriptions before §3 ground-truth read. I noted this in §1 protocol and consciously deferred the detailed body inspection to §3 — the blind verdict §2 was authored using direct code/dict inspection (08b script + thermo file + 0/T file + production logs), not the V41 body. The README spoiler degraded blind-purity but the §3 verdict mechanism (production-log grep contradicts V41 claims) is independent of the README spoiler. Mark this as protocol-drift acknowledged.
- **No fix-verification appendix**: F2/F3/F4 fixes are case_009 v1.5 sub-session work (08b extension OR 0/T fuel_jet bump). Track C session 4 does not test the fix because the briefing constrains to "不写代码 · 不动 case_009 substrate". The v1.5 sub-session, when dispatched, should incorporate V91's fix paths (alternative quick-fix = bump 0/T fuel_jet to 300K with `applied per V41 patch widening 2026-05-13` comment) as MANDATORY initial deliverable, analogous to case_011 v2 incorporating V85's insidePoint repositioning.
- **A6/A8 2nd-evidence: confirmed not produced by case_009 — by-construction.** Honest negative report. A6 (HVAC) and A8 (sHM dict) channels are foreclosed by case_009's reacting-low-Mach axisymmetric-wedge substrate. A10 (`thermo_polynomial_range_advisor`) is registered as a *new* advisor candidate scoped against reacting / multi-species cases.

## 6. Concrete deliverables (this session)

1. **V91 backfill** — `industrial_case_solver_findings.md` § V91 + `docs/openfoam_corpus/industrial_solver_findings_v_series.md` § V91 (runtime corpus mirror, synced same commit per `scripts/governance/check_corpus_sync.py` commit-msg hook). Documents V41 sediment-state correction: Tlow=200K patch incomplete (13/53 species still 300K; N2/AR/CH3O in active set) + mech-loader doesn't automate V41 + 14.7M warning lines persist in production logs. Cross-applies V83 intent-cross-reference pattern to V-series sediment-status as a verifiable artifact class. **A10 candidate registered** (`thermo_polynomial_range_advisor`) post-2nd-reacting-case extraction gate.
2. **ARC-GOAL.md M-TRACK-4** row checked off with retro file path + Track C counter incremented 3 → 4. V-series count 90 → 91. End-to-end numerics class count: case_009 v1 ran cold-flow (PASS) + 593 μs of ignite (incomplete but not failed). Stage A "PASS" per REPORT.md is `[QUESTIONABLE]` per V91 (warning flood is technically non-fatal, but adds ~10× CPU cost per timestep per V41 sediment's own lesson). **Conservative count: +0 to e2e numerics class** until v1.5 sub-session lands cleanly without warning flood; reacting-low-Mach reaches "demonstrated infrastructure, not validated solver-pass".
3. **V41 status amendment** — DEFERRED to a follow-on edit (separate from this retro commit). The V41 row should be amended `[VALIDATED 2026-05-08]` → `[QUESTIONABLE 2026-05-13 — patch incomplete per V91, defect-side grep returns 13 species; symptom-side 14.7M warnings in production logs]`. Amendment is recorded in V91 §Fix path (a). Not done in this session's commit because: (a) editing a previously-authored row alters the V-series audit trail timeline; would benefit from explicit user ratification; (b) this retro is itself the artifact justifying the amendment — committing them as separate commits preserves the audit causality.
4. **This retro file**.

**No source code changes this session.** F2/F3/F4 fixes are case_009 v1.5 sub-session actions (08b script extension OR 0/T fuel_jet boundary bump). A10 advisor extraction is Pillar-2-deferred until 2nd reacting case.

**Lessons-flagged for A6/A8 promotion** (the briefing's primary leverage point):

- A6 (HVAC ADPI) — case_009 produces ZERO 2nd evidence by construction (reacting low-Mach has no thermal-comfort surface). A6 promotion gate UNCHANGED at 1-case sediment (case_012).
- A8 (shm_dict_validator) — case_009 has no sHM dict by construction (blockMesh-only axisymmetric wedge). A8 promotion gate UNCHANGED at 1-case sediment (case_012 V52).
- A10 (`thermo_polynomial_range_advisor`) — NEW candidate, 1-case sediment (case_009 V91). Promotion gate = 2nd reacting case (or thermo-range issue in non-reacting case). The 16-case roster has no other current reacting case → A10 deferred until next reacting-class case lands.
- **Honest negative**: case_009 substrate state (no sHM, no HVAC physics, single-mech-loader) foreclosed BOTH A6 and A8 evidence channels by construction. The briefing's leverage hypothesis ("case_009 chemistry dict has chemkin loader / mechanism file format issues that could be A8 candidate scope") is correct in spirit — V38/V39 ARE chemistry-dict typo-class — but they're patched at the loader-script level (08b), which means they don't surface as live dict-validation issues; they surface only as "patch must exist + must be complete" issues. **Session 5 should target a case with substrate depth that includes a CURRENTLY-LIVE sHM dict OR HVAC physics surface for A6/A8 channel.**

## 7. Suggested next Track C sessions

Per sessions 1+2+3 §7 recommendations + session 4 substrate-constraint learnings:

- **Session 5** (recommended): **case_007 KCS ship VOF** (multiphase-VOF · numerics class). Already probed in session 1 §10 (negative on V82 reproduction) but not full-session-treated. Substrate readiness check: `ls ~/Desktop/case_007*/case/log/ ~/Desktop/case_007*/evidence/v1*/REPORT.md ~/Desktop/case_007*/case/system/snappyHexMeshDict`. If sHM dict is present, **A8 2nd-evidence pathway re-opens** — V52 (case_012 typo) + any case_007 sHM dict-validity finding would constitute the 2-case promotion gate. VOF-specific findings (alpha.water BC, surface-tension model, wallDist for kOmegaSST) are orthogonal to all 4 prior session classes.
- **Session 6** (alternative): **case_008 airfoil-with-mount** (transonic-compressible · numerics class) — sparse main-corpus coverage (V28/V53 cluster on transonic PCG/PBiCGStab), good blind-spot probe. Also includes sHM dict for A8 widening.
- **Session 7+** (post-arc-target): **cross-numerics-class re-visit** — instead of yet another new case, re-visit case_010 (session 1) or case_011 v3 (session 2) with the full Track C protocol after recent fixes have landed. This would test "session N+1 catches finding X that session N missed" cross-session consistency — a different validation than "session-each-on-different-case roster coverage".
- **Session 8+** (deferred): **case_004 v2** (when dispatched) for V88 fix-verification + e2e numerics-class advancement (MRF + solver run). Same V41/V91-style retroactive-audit applicable.

**Pacing reset urgency increased**: sessions 1+2+3+4 all on 2026-05-13 = 4 sessions / 1 day. Aggregate token spend in this session window ≈ 250-280k tokens across 4 retros + 3 V-rows (V88, V89/V90 carried, V91). Sessions 5+ should resume **weekly cadence** unless user explicitly directs continued same-day. Risk addressed by clustering = "Track C arc momentum + warm protocol context" — observed net-positive across 4 sessions. Risk incurred = (a) priming bias accumulating in V83/V88/V91 cross-application chain (the framing is genuine but fast); (b) main-session token budget consumption at ~280k cumulative; (c) potential staleness of substrate verifiability — sessions 1-4 are all auditable against the on-disk substrate which is itself in flux. Per session 3 §7 note: "the bias is mostly net-positive but should be tracked across the arc".

**Substrate readiness check before scheduling session 5**: `ls ~/Desktop/case_007*/case/log/ ~/Desktop/case_007*/evidence/v1*/REPORT.md ~/Desktop/case_007*/case/system/snappyHexMeshDict`. Specifically: (a) does sHM completed log exist? (b) does REPORT.md document any v1-level limitations? (c) does sHM dict have any feature-list / region-syntax / locationInMesh choices that A8 could exercise?

**A6/A8/A10 leverage update**:
- A6 hvac_adpi: foreclosed by case_009 substrate. Sessions 5-6 should pre-flight for an HVAC-relevant case (case_015 chtMR-LES candidate if it has interior thermal-comfort surface) — currently no HVAC case in the 16-case roster active list.
- A8 shm_dict_validator: foreclosed by case_009 substrate. Sessions 5-6 with sHM-using cases (case_007, case_008, case_016) are the natural A8 leverage points.
- A10 thermo_polynomial_range_advisor: 1-case sediment after this session. Promotion gate = 2nd reacting case which is NOT in the 16-case roster active list → A10 extraction blocked until M-NUMERICS adds a 2nd reacting case OR a thermo-range issue surfaces in a non-reacting case via some other mechanism (unlikely in current roster).

## 8. Cross-references

- **Parent feedback**: `feedback_claude_code_is_the_advisor.md` (M6 charter advisor button → replaced by Track C dogfooding)
- **Parent DEC**: V61-198 (industrial-case container pivot; case_009 declared the first reacting-low-Mach root case)
- **V-row landed this session**: **V91** (V41 sediment-state correction · 3 sub-mechanisms · sediment-status-as-verifiable-artifact methodology extension)
- **V-rows cross-applied (4th application widening)**: **V83** (case_010 mesh_ok blind-spot) — V91 is 4th cross-application of intent-cross-reference pattern across 4 surfaces (mesh_ok, mesh_summary, mrf_audit, V-series sediment-status itself). The cross-cutting `audit_verdict_semantics_advisor` (Pillar-2 candidate noted in sessions 1+2+3 retros) is now **overdetermined at 4 cross-applications and broadened to include V-series sediment-status as a verifiable artifact class**. Recommend escalation from "deferred" to "next-after-A4/A5" priority for ARC review.
- **V-rows referenced (4th PASS in arc) but not amended**: V38, V39, V40 (chemkin loader patches, all `[VALIDATED]` and confirmed by this session's blind read — script automation is complete for these three); V42 (A2 advisor `_run_shared` 6th-of-6 PASS, status `[QUESTIONABLE]` per V25 chain — A2-v2 LANDED 2026-05-12 closes the placeholder)
- **V-row pending amendment (NOT done this commit)**: **V41** — status `[VALIDATED 2026-05-08]` → `[QUESTIONABLE 2026-05-13 — patch incomplete per V91]`. Amendment justified by this retro; recommended for separate user-ratified commit
- **A6/A8 promotion status post-session-4**: A6 hvac_adpi UNCHANGED at 1-case sediment; A8 shm_dict_validator UNCHANGED at 1-case sediment. Neither advanced by case_009 (substrate foreclosure)
- **A10 candidate registered**: `thermo_polynomial_range_advisor.py` — per-species Tlow/Thigh vs 0/T fixedValue boundary check with safety margin. Defer to 2nd reacting case
- **ARC-GOAL row**: M-TRACK-4 main-line table
- **Session 1 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_1_case_010.md`
- **Session 2 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_2_case_011.md`
- **Session 3 retro**: `.planning/retrospectives/2026-05-13_track_c_advisor_e2e_session_3_case_004.md`

## 9. F2-F4 fix-verification (NOT performed this session)

Unlike session 1 §9 (V82 fix verified in-place on case_010 sandbox), session 4 does **not** include a fix-verify appendix. Reasons:

1. **Briefing constraint**: "不写代码 · 不动 case_009 substrate". Session 4 is verification, not development.
2. **F2-F4 fixes are case_009 v1.5 sub-session scope**: (a) extend `08b_load_chemistry_mech.py:patch_thermo_header` to walk per-species records and rewrite Tlow=300→200 where lowCpCoeffs polynomial supports it (~25 LOC), OR alternative quick-fix (b) bump `0/T fuel_jet` boundary from 294→300K (1-LOC change) + add inline comment crediting V91. Multi-step, scoped to v1.5 dispatch.
3. **v1.5 sub-session is not yet dispatched** for case_009; when it is, the kickoff should incorporate V91 sub-mechanism α/β/γ fix paths as MANDATORY initial deliverable, analogous to case_011 v2 incorporating V85's plate-bumping + insidePoint repositioning.

**Path to V91 promotion from `open` to `fix-verified · 1 case`**:
1. case_009 v1.5 sub-session lands with: (a) thermo.compressibleGas has 0 species at Tlow=300 (`grep -c "Tlow[[:space:]]\+300;" thermo.compressibleGas` returns 0); OR (b) 0/T fuel_jet is 300K + log_cold + log_ignite warning count = 0.
2. Track C session re-visits case_009 v1.5 (same protocol, fresh blind reading) — confirms F2/F3/F4 no longer reproducible from grep.
3. Update V91 Status `open` → `fix-verified · 1 case` + amend V41 Status to `[VALIDATED 2026-05-XX — patch re-applied per V91 fix path]`.
4. Promotion to `validated · cross-case (≥2 reacting cases)` deferred until 2nd reacting case lands in the roster.

**What this leaves unverified**: V91 Status is `open`. A10 extraction is Pillar-2-deferred. The 16-case roster has no other reacting candidate — Track C session 7+ may need to wait for Phase-2 industrial cases or a new reacting case dispatch.

## 10. Pacing + protocol notes

**Pacing — 4-session same-day acknowledgment**: per user direction 2026-05-13 — session 4 runs same-day as sessions 1+2+3 (~5-7 hours after session 1 start, ~2-3 hours after session 3 close). Session 1 §7 recommended ≥1 week cadence; session 2 was 1-day cadence; session 3 §10 noted "3 sessions / 1 day"; session 4 extends to **4 sessions / 1 day**, acknowledged as **accelerated cadence beyond original session-1 §7 weekly recommendation**. Per main-session direction (briefing §pacing-warning), this is acceptable for Track C arc-velocity reasons — accumulating data points while context + protocol mental model are warm. Specifically session 4 leverages the V83 cross-application frame primed by sessions 1-3 to position V91 as the 4th cross-application; the frame fits genuinely (V91 IS an intent-cross-reference pattern in V-series-sediment-as-artifact form) but the pattern-fitting was rapid and would benefit from independent verification at session-5+ cadence reset.

**Risks addressed by clustering** = "Track C arc-velocity" — sessions 1-4 cover 4 numerics classes (incompressible-LES + steady-laminar-CHT + RANS-MRF + reacting-low-Mach) and add 4 V-rows or V-row corrections (V82..V88, V91) in 1 day; this is high-value substrate coverage that would dilute across multi-week gaps.

**Risks incurred**:
- **Inter-session priming**: V83 cross-application frame is now load-bearing across sessions 1-2-3-4. Each session deepens the methodology pattern but if the frame is wrong (e.g., V83 is actually 4 different defects that happen to look similar), the cumulative session-1-4 work over-leverages a flawed frame. Mitigation: session 5+ should be EITHER a different methodology frame OR an explicit independent verification of V83 cross-applicability across the 4 surfaces.
- **Token budget**: cumulative spend across sessions 1-4 retros + V-row authoring ~250-280k tokens of main-session context. Approaching but not exceeding the 1M-ctx budget; auto-compaction not yet triggered. Sessions 5+ should monitor.
- **Verifiability staleness**: sessions 1-4 are all auditable against on-disk substrate which is itself in flux (case_009 v1.5 sub-session, case_004 v2 sub-session, case_011 v3 deferred → all change the substrate that future Track C re-visits would read). Mitigation: V91 records the exact grep commands and counts so a future reader can re-run them to confirm or falsify the finding regardless of substrate drift.

**Protocol drift from sessions 1+2+3**:
- **README.md spoiler partial-protocol-drift**: case_009's README lines 87-103 list V38-V42 names + one-line descriptions, which I technically read pre-blind-verdict due to README structure (no clean way to read lines 1-86 without seeing 87-103 in the same viewport). I consciously deferred body inspection of V38-V42 to §3. Net effect: I knew V38-V42 EXIST and what they NAME (header, terminator, transport, Tlow-flood, A2-PASS) but not the body details (e.g., V41's `[VALIDATED]` status was discovered in §3 not §1). **The §2 blind verdict's main finding (V91) was authored on direct file/log inspection, not on README disclosure** — F3 grep + F4 script-read + F2 log-grep are independent of V41 body. Marked as protocol-drift acknowledged; the verdict structure survives.
- **Sediment-correction is a new finding class for Track C**: sessions 1-3 surfaced gaps in territory the source-case author hadn't covered; session 4 surfaces a finding that retroactively corrects a previously-`[VALIDATED]` row. This is a different mode of advisor utility — "audit prior sediment for production-state truth" vs "discover NEW gap". Both modes use the same blind protocol. **Recommend cataloging "sediment-state-correction" as an explicit Track C finding class going forward** alongside "NEW V-row" and "primed-match" classes.
- **No §10 cross-case probe appendix** (unlike session 1 §10 which probed case_007 sHM log for V82 reproduction). V91 is reacting-low-Mach-specific; the 16-case roster has no other current reacting case to probe. The closest cross-class probe would be looking at case_004 or case_011 v1 for similar sediment-state-vs-production-state drift on V88 or V85 — left as session-7+ "re-visit" deferred work.
- **Substrate depth at maximum for Track C so far**: case_009 has more pipeline artifacts than case_010 (LES) or case_011 (CHT) or case_004 (MRF, paused). Per the §1 substrate inventory: scripts 11, dict files 9, evidence files 8, advisor outputs 2, production logs 2 totaling ~58 MB. Yet the blind verdict still surfaces only 1 V-row plus minor notes — testing protocol robustness against substrate-depth-overload. Result: protocol scales; the finding distribution shifts toward production-state + sediment-state findings (vs sessions 2+3 where substrate-depth-deficiency forced config-only findings).

**Track C arc state after session 4** (per ARC-GOAL Done Definition):
- Done Definition #1 "Track C session 通过 case 数": 3 → **4** (target: ≥ 6)
- Done Definition #2 "LANDED advisor 数 (含 D-class ≥ 1)": **6 UNCHANGED** (A1, A2-v2, A3, A4, A5, A7 LANDED · A6/A8 still at 1-case sediment, A9 mrf_setup_advisor candidate from session 3, A10 thermo_polynomial_range_advisor candidate newly registered this session)
- Done Definition #3 "V-series 行数": 90 → **91** (target: ≥ 100)
- Done Definition #4 "End-to-end solver 跑通 numerics class 数": **1 UNCHANGED conservative count** (case_009 v1 cold-flow ran PASS per REPORT.md, but ignite ran only 593 μs and the cold-flow PASS is `[QUESTIONABLE]` per V91 warning-flood evidence — the 14.7M warnings include the message "attempt to use janafThermo<EquationOfState> out of temperature range" which means the chemistry source-term evaluations were clamped to Tlow=300 rather than using the physical T=294 polynomial; this is a documented physics inaccuracy, however small. Conservative: do not count reacting-low-Mach as solver-pass yet; await v1.5 cleanup)
- Done Definition #5 capability radar left-half: UNCHANGED (Track C doesn't directly move radar; V91 adds small +0.03Δ to 工作流-完整性 axis only when A10 lands)
- Done Definition #6 capability radar right-half: UNCHANGED

**Triggered redirect conditions** (per ARC-GOAL):
- "Track C 中 ≥ 2 case 同类 advisor 盲点" → session 4's V91 surfaces sediment-state-as-verifiable-artifact class, which IS cross-application of V83 family but at META level (V-series sediment) rather than at audit-script level (mesh_ok / mesh_summary / mrf_audit). Whether this counts as "same advisor blind-spot class as V88-sub-mechanism-a" is judgement call: I argue YES — they're all the same "intent-cross-reference" methodology gap at different audit surfaces — but the META-level extension is a step up in scope. Flag for ARC review: **does the 4-cross-application count of V83's pattern across sessions 1-4 trigger harvest-003 (Pillar-2 advisor extraction)?**. Recommended: YES, escalate `audit_verdict_semantics_advisor` from "deferred" to "next-after-A4/A5" priority.

**Open questions to surface for next-session decision**:
1. **V41 status amendment commit timing**: should I commit the V41 `[VALIDATED]` → `[QUESTIONABLE]` amendment as part of this retro commit, or as a separate user-ratified commit? Current retro deliverable §6 item 3 chose separate commit to preserve audit causality; user may prefer combined commit to land the audit + correction atomically. Flag for next-session user decision.
2. **A10 candidate registration vs deferral**: 1-case sediment with no 2nd-reacting-case in 16-case roster active list. Should A10 stay as "registered candidate awaiting Phase-2 case" OR should we explore "synthetic 2nd reacting case" (e.g., extend case_007 to add a methane-air pilot region)? Current default is deferral; user may have view.
3. **Pacing reset for session 5**: explicit ratification that session 5 returns to weekly cadence vs continued same-day. The 4-session same-day cluster has yielded V-row corrections + cross-class coverage; marginal value of session 5 same-day vs +1 week is judgement call. Recommend explicit user direction.
4. **V83-cross-application overdetermination**: 4 cross-applications across 4 sessions. Does the cross-cutting `audit_verdict_semantics_advisor` graduate from Pillar-2 candidate to "queue for next implementation session"? Recommend YES given the methodology gap is now overdetermined; defer to user ratification.

— EOF —
