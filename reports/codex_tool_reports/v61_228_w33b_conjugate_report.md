# Codex review report — DEC-V61-228 · P3 W3.3b conjugate Gnielinski coverage flip

- **Relay**: CRS (`~/.codex-crs`), `gpt-5.4`, effort=high (fallback — 86gs xhigh hung
  with empty output >3 min, consistent with the W3.2b/W3.3a sessions → CRS per
  standing recommendation; effort downgrade noted in DEC frontmatter).
- **Round cap**: 3. **Scope**: `src/cht_conjugate_{extractor,gate}.py`, the
  Gnielinski gold, the offline replay test, frozen artifacts.

## R0 — `codex review --commit 40420ab` (the coverage-flip commit)

**Verdict**: no P0/P1; **2 findings (P2 + P3)** — both hardening of the validity
hard gates so they verify the *replayed case* rather than trusting the gold YAML.

### [P2] Derive the Reynolds hard gate from the replayed case, not the YAML
`src/cht_conjugate_gate.py:112-116` — `reynolds_in_band` read
`case_info.conjugate_inputs.Re` from the gold, so it never verified the `case_dir`
was actually solved at that flow. A stale/misconfigured postProcessing set, or a
live run drifted to the wrong mass flow, would still report `Re_in_band=PASS`
(the probe headers already carry the inlet area needed to recover the solved Re).
That weakens the hard-stop meant to prevent a false coverage flip on the wrong run.

### [P3] Enforce the Prandtl validity limit of the Gnielinski correlation
`src/cht_conjugate_gate.py:112-116` — the validity gate only checked `Re`, though
the gold itself states Gnielinski is valid for `0.5 < Pr < 2000`. Because
`gate_conjugate_against_gold()` accepts an arbitrary `gold_path`, a future
re-anchor / alternate fluid with out-of-range `Pr` could PASS as long as Nu +
energy happened to match, even though the reference is outside its declared domain.

## R0 fix — commit `2969ede`

Both findings addressed (gate still PASSES on the committed artifacts — all 5
checks green; the fixes tighten, not loosen):

- **P2**: extractor parses the inlet probe `# Area` header and computes
  `reynolds_solved = mdot·D_h/(A_in·mu)` from the measured inlet mass flux
  (verified = 50000.0 from the committed probes). The gate now hard-gates the
  SOLVED Re on **two** checks — inside the Gnielinski band AND within ±5% of the
  gold's target Re (the replayed run must be the one the gold describes).
- **P3**: new Prandtl hard gate — `Pr = mu·cp/k_fluid` must lie inside the gold's
  `Pr_validity_{min,max}` (0.5/2000). Out-of-domain fluid cannot pass.
- Tests +2 (`test_reynolds_is_derived_from_case_not_the_yaml`,
  `test_prandtl_validity_is_a_hard_gate`) → 11 green; 364 p3 + 1 skip; lint 5/5.

## R1 — `codex review --commit 2969ede`

**Verdict**: escalated — **2 findings (P1 + P2)**. The R0 fix derived Re/Pr from
the *gold's* `mu`/`cp`/`k_fluid`, so it still trusted YAML transport properties
rather than the replayed case.

### [P1] Read viscosity from the replayed case before recovering Re
`src/cht_conjugate_gate.py:99-104` — `reynolds_solved` was computed with
`ci["mu"]`. A rerun whose `constant/fluid/physicalProperties` changed `mu` (same
inlet mass flux) would still satisfy `Re_matches_target`, even though the actual
solved Re drifted — defeating the stale-run protection. The replay bundle already
ships the case transport properties.

### [P2] Derive the Prandtl gate from case properties, not YAML
`src/cht_conjugate_gate.py:143-149` — `Pr_in_band` was computed entirely from
`ci["mu"], ci["cp"], ci["k_fluid"]`, never inspecting the solved case; a rerun
with a different fluid could pass as long as the gold stayed in-range.

## R1 fix — commit `<this commit>`

The extractor now reads **all** fluid transport properties (mu, cp, k_fluid, Pr)
from the replayed case's `constant/<region>/physicalProperties` — not the gold:

- `extract_conjugate_qois(case_dir, *, D_h, fluid_region)` (mu/cp/k/Pr no longer
  args) → `_read_fluid_properties()` parses the case dict (rhoConst: Cp=Cv;
  kappa=mu·Cp/Pr). `reynolds_solved`, `prandtl`, and Nu are dimensionalised with
  the CASE properties; QoIs expose `mu_pa_s/cp_j_kgk/k_fluid_w_mk/prandtl/rho_kg_m3`.
- Gate **HARD gate 4 `fluid_matches_gold`**: the case fluid must match the gold
  reference fluid (mu, cp, k, Pr within 1%) — a rerun with drifted props is caught.
- Bundle restructured into a proper case dir (`postProcessing/` + `constant/` +
  `system/` + `0/` at the probe root) so the case fluid is co-located with the probes.
- Tests +3 (`test_reynolds_uses_case_viscosity_not_yaml`,
  `test_prandtl_uses_case_properties_not_yaml`,
  `test_fluid_mismatch_with_gold_is_a_hard_gate`) → 14 green. Gate still PASSES
  (6/6 checks green). 367 p3 + 1 skip; lint 5/5.

## R2 — `codex review` (pending)

_(verdict to be filled on completion)_
