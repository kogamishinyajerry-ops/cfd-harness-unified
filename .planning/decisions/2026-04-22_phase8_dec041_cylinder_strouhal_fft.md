---
decision_id: DEC-V61-041
timestamp: 2026-04-22T19:10 local
scope: |
  Phase 8 Sprint 1 — cylinder_crossflow emits a proper Strouhal number
  from forceCoeffs function object Cl(t) FFT instead of the hardcoded
  canonical-band shortcut (strouhal_number=0.165 for any Re∈[50,200],
  regardless of whether the flow actually shed). Adds new
  src/cylinder_strouhal_fft.py + `forceCoeffs` + `adjustTimeStep` +
  `endTime=200` in the cylinder controlDict + rewrite of
  `_extract_cylinder_strouhal` to require the FO path. Fail-closed
  when forceCoeffs output is absent — DEC-V61-036 G1 then picks up
  MISSING_TARGET_QUANTITY.

autonomous_governance: true
claude_signoff: yes
codex_tool_invoked: pending
codex_rounds: 0
codex_verdict: pending
counter_status: |
  v6.1 autonomous_governance counter 31 → 32. Arc-size retro was due
  at 30; still deferred until DEC-041 closes (last of the Phase 8
  Sprint 1 PASS-washing-cleanup chain).
reversibility: fully-reversible — new FFT module + new forceCoeffs
  block in cylinder controlDict + extractor rewrite. Revert = remove
  src/cylinder_strouhal_fft.py + drop functions{} block +
  restore the old canonical-band-shortcut branch in
  `_extract_cylinder_strouhal`.
notion_sync_status: pending
github_pr_url: null (direct-to-main after Codex)
external_gate_self_estimated_pass_rate: 0.70
  (FFT is the most algorithmically novel of the Sprint 1 DECs.
  Remaining risks:
  (a) Hann window vs. rectangular for short-duration runs — we
  apply Hann post-trim, but very short post-trim windows (≈10
  cycles) degrade resolution,
  (b) transient_trim_s=50s default assumes f≈1.5-2 Hz shedding;
  lower Re cases with slower shedding could still be in transient
  at t=50s — but gold range is Re=50-200 where f_s is well above
  threshold,
  (c) O(N²) stdlib DFT is slow (~4min for 30000 samples) — test
  suite marks 4 roundtrip tests as slow; production would want
  numpy.fft.rfft but we can't assume numpy in src/,
  (d) forceCoeffs field naming: OF10 writes `coefficient.dat`,
  older OF writes `forceCoeffs.dat` — parser accepts either,
  (e) stdlib-only constraint cost us ~50 LOC of manual DFT
  implementation; future contributor might replace with numpy.)
supersedes: null
superseded_by: null
upstream: |
  - DEC-V61-036 G1 — MISSING_TARGET_QUANTITY gate (fail-closed is
    fed by this DEC — absence of strouhal_number from cylinder
    triggers the gate).
  - DEC-V61-043 — FO-in-controlDict-functions pattern established
    for plane_channel; this DEC reuses it for cylinder forceCoeffs.
  - DEC-V61-042 — BC-plumbing pattern (cylinder_D, U_ref through
    task_spec.boundary_conditions).
  - DEC-V61-044 — complementary NACA FO pattern, also part of
    Phase 8 Sprint 1 PASS-washing cleanup.
  - The original _extract_cylinder_strouhal canonical-band
    shortcut was the last PASS-washing shortcut in the codebase:
    "if 50 ≤ Re ≤ 200: strouhal_number = 0.165" — bypassing all
    flow measurement. Its removal completes the Phase 8 Sprint 1
    cleanup.
---

# DEC-V61-041: Cylinder Strouhal FFT

## Why now

Cylinder_crossflow gold asserts St≈0.165 for Re∈[50,200] (laminar
shedding regime, Williamson 1996). The old extractor
`_extract_cylinder_strouhal` hardcoded `strouhal_number = 0.165` for
the entire canonical band, regardless of whether simulation actually
converged to a shedding limit cycle. That was the last PASS-washing
shortcut — a simulation that diverged or that timed out before
transient decayed would still "pass" the comparator.

DEC-V61-041 closes this by:
1. Wiring a proper `forceCoeffs` FO into the cylinder controlDict so
   the solver emits Cl(t), Cd(t) time series.
2. Adding `adjustTimeStep true` + `endTime 200` so each run gets
   ≥200s of simulated time (≈100-200 shedding cycles at f≈1.5Hz).
3. Implementing an FFT-based Strouhal extractor
   (`src/cylinder_strouhal_fft.py`) that parses the FO output,
   trims transient (default 50s), applies Hann window, computes DFT,
   finds peak frequency, then computes St = f·D/U.
4. Retiring the canonical-band shortcut. Without FO output (i.e. old
   cached cases with no forceCoeffs), extractor emits NO
   strouhal_number and DEC-036 G1 picks up MISSING_TARGET_QUANTITY.

## What lands

1. **New `src/cylinder_strouhal_fft.py`** (~330 LOC):
   - `CylinderStrouhalError` — fail-loud on malformed input / short
     windows / degenerate signals.
   - `StrouhalResult` frozen dataclass (strouhal_number,
     dominant_frequency_hz, cd_mean, cl_rms, fft_window_s,
     samples_used, low_confidence).
   - `parse_coefficient_dat`: parses
     `postProcessing/forceCoeffs1/<t>/coefficient.dat` (OF10) or
     legacy `forceCoeffs.dat`. Uses `# Time Cm Cd Cl ...` header row
     to map column names — resistant to OF version drift and
     custom column orderings. Falls back to positional layout
     (Time, Cm, Cd, Cl) if no header.
   - `_hann_window`, `_dft_magnitudes`: stdlib-only (no numpy) O(N²)
     DFT. Slow (~4min for 30k samples) but production runs ≤6k
     samples so ≤10s per case.
   - `_resample_uniform`: linear interpolation onto regular dt
     grid — forceCoeffs emits per-step data, which with
     `adjustTimeStep` is non-uniform.
   - `compute_strouhal`: end-to-end pipeline (trim → zero-mean →
     resample → Hann → DFT → peak pick → St). Fails on <100
     post-trim samples, flat Cl, zero D, zero U_ref, length
     mismatch.
   - `emit_strouhal`: wrapper that locates the FO dir, picks the
     latest time, and returns a dict suitable for merging into
     `key_quantities`. Returns None if FO dir absent (not a
     corruption — just old cached case). Raises if FO dir exists
     but no .dat inside.

2. **Generator side** (`_generate_circular_cylinder_wake`):
   - Plumbs `cylinder_D`, `U_ref` into `task_spec.boundary_conditions`.
   - Adds `functions{}` block with `forceCoeffs` FO on patches=(cylinder)
     with `rhoInf` plumbed, `liftDir (0 1 0)`, `dragDir (1 0 0)`,
     `CofR (0 0 0)`, `writeInterval 1`.
   - Changes `endTime` from 100 → 200 to capture ≥100 shedding cycles
     at f≈1.5 Hz (Re=100).
   - Adds `adjustTimeStep true` + `maxCo 0.8` so solver adapts dt
     (previously fixed dt=0.01 gave uniform output but at the cost of
     stability near peaks).

3. **Extractor** (`_extract_cylinder_strouhal`):
   - Primary path: call `emit_strouhal(case_dir, D, U_ref,
     transient_trim_s=50.0)`. Success → merge strouhal_number,
     dominant_frequency_hz, cd_mean, cl_rms, strouhal_source=
     "forceCoeffs_fft_v1", strouhal_low_confidence flag.
   - Malformed FO output → `strouhal_emitter_error` key (fail-closed
     per DEC-V61-040 round-2 pattern).
   - No case_dir (old diagnostic path from p(t) at probe) → emit only
     p_rms / Cp_rms diagnostics; NO strouhal_number. DEC-036 G1
     picks up MISSING_TARGET_QUANTITY.
   - **Retired**: the `0.165 if 50 ≤ Re ≤ 200` canonical band shortcut
     is GONE. No `strouhal_canonical_band_shortcut_fired` flag
     anywhere.

4. **Tests** (`tests/test_cylinder_strouhal_fft.py`, 19 tests):
   - Parser: OF10 header-based column lookup, positional fallback,
     missing file raise, empty file raise.
   - FFT core: Hann symmetric, DFT recovers known bin, linear
     resample, insufficient window raise.
   - compute_strouhal: clean sinusoid at f=1.64 Hz → St=0.164 within
     1%, transient decay removed, short window raise, flat signal
     raise, zero D raise, zero U_ref raise, length mismatch raise.
   - emit_strouhal: absent FO dir → None, empty FO dir → raise,
     valid → StrouhalResult keys match, legacy `forceCoeffs.dat`
     filename accepted.
   - 4 tests marked as "slow" (run ≥2min each due to O(N²) DFT on
     200s @ dt=0.005 → 40k samples); kept in suite but deselected
     in quick sweeps.

5. **`tests/test_foam_agent_adapter.py`** — 4 cylinder tests updated
   for new fail-closed semantics:
   - `test_extract_cylinder_strouhal_fails_closed_without_case_dir`:
     diagnostic-only path emits no strouhal_number.
   - `test_extract_cylinder_strouhal_records_diagnostic_pressure_rms`:
     p_rms / Cp_rms still emitted for debugging.
   - `test_extract_cylinder_strouhal_no_hardcode_in_canonical_band`:
     Re=100 no longer triggers canonical-band shortcut (renamed from
     `test_extract_cylinder_strouhal_records_canonical_band_shortcut`).
   - `test_extract_cylinder_strouhal_no_shortcut_flag_outside_band`:
     still asserts flag absent, but also asserts strouhal_number
     absent now.

## Out of scope — tracked separately

- **numpy migration**: O(N²) DFT is a stdlib-only artifact. A future
  DEC could pull numpy into src/ (already a test-only dependency)
  and drop ~50 LOC of manual DFT.
- **adaptive transient_trim_s**: default 50s is hand-tuned for gold
  Re range. A future DEC could detect transient decay via moving-
  window standard-deviation stabilization.
- **Fixture regeneration**: existing cylinder fixture still carries
  the hardcoded 0.165; needs Docker+OpenFOAM re-run via
  `scripts/phase5_audit_run.py`.
- **Multi-mode shedding detection**: at Re≥300 the wake goes 3D and
  the spectrum develops sidebands. Current implementation picks the
  single peak and flags low_confidence if peak-to-next-peak ratio
  is <1.5× but doesn't explicitly model the transition.

## Live verification

```
tests/test_cylinder_strouhal_fft.py ................... 15 passed
                                                        (4 slow deselected)
tests/test_foam_agent_adapter.py::*cylinder* ........... 4 passed
tests/test_airfoil_surface_sampler.py .................. 20 passed
tests/test_plane_channel_uplus_emitter.py .............. 20 passed
tests/test_wall_gradient.py ............................ 11 passed
tests/test_dec042_extractor_integration.py ..............  5 passed
ui/backend/tests/ ...................................... 201 passed

Total: 276/276 green post-DEC-041 (excluding 16 pre-existing
unrelated failures in contract_dashboard / audit_package / gold_
standard_schema / LDC sampleDict helpers — these were failing before
DEC-041 was started; verified via `git stash` sanity check).
```

## Counter + Codex

31 → 32. Self-pass 0.70 (lowest of the Phase 8 Sprint 1 DECs —
largest new module, novel FFT algorithm, stdlib-only constraint).
Codex pre-merge per RETRO-V61-001:
- CFD new FO wiring in `_generate_circular_cylinder_wake`
- `foam_agent_adapter.py` > 5 LOC (new FO block + BC plumbing +
  extractor rewrite)
- New shared module with non-trivial algorithm (FFT)

Retro now due per RETRO-V61-001 arc-size cadence (counter ≥30 fired
at DEC-043; deferred through DEC-041 completion). Will land
immediately after DEC-041 Codex APPROVED.

## Related

- DEC-V61-036 G1 — MISSING_TARGET_QUANTITY now fed by this
- DEC-V61-043 — plane_channel u+/y+ emitter (same FO pattern)
- DEC-V61-044 — NACA C3 surface sampler (same FO pattern)
- DEC-V61-042 — BC plumbing pattern
- RETRO-V61-001 — governance rules applied
