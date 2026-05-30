# Codex chain report · DEC-V61-220 (P3 W3.0.2 thermo_dict multi-region)

- **Date**: 2026-05-30
- **Relay**: R0 on **86gs `gpt-5.4` xhigh** (governance baseline); **R1 86gs
  stream-failed mid-review ("Upstream request failed" ×5) → failed over to CRS
  `gpt-5.4` high** per DEC-V61-214 precedent; R2 on CRS. Effort-downgrade
  xhigh→high logged (consistent with W3.0.1's 86gs 502 instability).
- **Target**: `thermo_dict_multi_region.py` (new) + `thermo_dict_extractor.py`
  (shared-helper depth-0 hardening) + `__init__.py` (re-export) + 3 p3 test files
  + 1 single-region regression test + DEC-V61-220.
- **Outcome**: **cap=3 reached** (R0→R1→R2 all CHANGES_REQUIRED). ALL findings
  fixed + regression-pinned. R2 fixed at cap WITHOUT an independent R3 round
  (consult tool errored — autonomous-mode option (a) per W3.0.1 precedent;
  overflow record `.planning/retrospectives/codex_round3_overflow_w302.md`).
- **Pre-Codex hardening**: the 2-lens `test-red-team` workflow caught **P1×3
  (solid-kappa gating + nesting-depth `thermoType.type` discriminator leak ×2),
  P2×2 (nested molWeight leak, directive-inside-block), P3 (docstring overclaim)**
  — all fixed before R0. The nesting leak was a **latent bug in the single-region
  extractor too**; hardened at root (`_strip_nested_blocks` in 4 leaf scanners).

---

## R0 — CHANGES_REQUIRED (2× P2) · 86gs xhigh

1. **eConst / non-pureMixture not refused** — a region declaring `thermo eConst`
   or `mixture != pureMixture` still built a populated snapshot (single-region
   returns None; docstring promised None). **Fix**: scope-out gate in
   `_parse_region_thermo` → region None. Tests: `test_econst_region_must_refuse...`,
   `test_non_puremixture_region_must_refuse...`.
2. **solid `rho` extracted regardless of declared EOS** — `_extract_rho_const`
   scraped `rho` from any `equationOfState` block; a non-`rhoConst` EOS with a
   stray `rho` fabricated a constant density. **Fix**: gate on
   `eos_kind == "rhoConst"` (symmetric with the kappa gate). Test:
   `test_solid_non_rhoconst_eos_stray_rho_must_be_none`.

## R1 — CHANGES_REQUIRED (2× P1) · CRS high (86gs stream-failed)

3. **Partial snapshots where single-region refuses (fluid)** — a `heRhoThermo`/
   `hePsiThermo` region missing transport (absent/dup/incomplete or out-of-scope
   model) or missing/ambiguous `Cp` returned a populated snapshot with those None.
4. **Partial snapshots where single-region refuses (solid)** — a `heSolidThermo`
   region missing thermodynamics/`Cp` returned a snapshot with `cp=None`.
   **Fix (both)**: **Contract A** — required-field-absent → region None, symmetric
   with the wrapped single-region extractor. Required = `molWeight` + `Cp`
   (universal) + complete fluid transport; solid `kappa`/`rho` stay OPTIONAL
   payload (forced by the documented constAnIso / non-rhoConst scope-out contracts).
   Unknown `type` token also → region None (no half-populated snapshot). Builders
   now return `RegionThermoSnapshot | None`. 5 Contract-B pins updated to region-None.

## R2 — CHANGES_REQUIRED (1× P1) · CRS high → cap=3, fixed at cap (no R3)

5. **Duplicate map key on name-in-both-tuples** — a region name in BOTH
   `fluid_regions` and `solid_regions` made `all_regions` contain it twice; the
   name-keyed `result` dict collapsed it → fewer keys than declared. **Fix**:
   `dict.fromkeys` order-preserving dedup; in-both name → single key mapping to
   None (ambiguous kind). Test: `test_region_name_in_both_tuples_single_key_none`.

---

## Outcome

- All findings fixed + pinned. R2 implicitly validated the substantial R1
  Contract-A refactor (reviewed it, did not re-flag). Only the trivial 5-LOC R2
  dedup is un-re-reviewed (honest residual — low risk, pinned).
- Tests: **153 passed, 6 skipped** (p3 multi-region + single-region thermo) ·
  **308 passed, 38 skipped** (full case-extractor surface — no regression).
  Stdlib-only.
- DEC-V61-220 → **Accepted** (`confidence: med` — chain did not reach clean
  APPROVE; R2 fixed at cap without re-review per discipline).

## Calibration (RETRO-V61-001 intake)

1. **Add a "wrapper refusal-bar parity" checklist item**: when a new extractor
   wraps an existing one, enumerate the wrapped extractor's required-vs-optional
   fields UP FRONT and pin a region-None test per required field — the R1 P1
   (Contract A) was the gap the W3.0.1 honest-refusal checklist didn't cover.
2. **Map-key uniqueness under union iteration** (R2): any name-keyed map drawn
   from ≥2 source lists must dedup + pin the in-both case.
3. **86gs upstream instability persists** (R1 stream-fail after W3.0.1's 502×2);
   consider CRS-primary for governance review if it continues.
