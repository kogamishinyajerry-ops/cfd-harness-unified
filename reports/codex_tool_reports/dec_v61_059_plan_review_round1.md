# DEC-V61-059 — Codex round-1 review summary

- **Branch**: `dec-v61-059-pc` (commits 48cf994 → 55b3759)
- **Reviewer**: Codex CLI v0.118.0, model gpt-5.5 (fallback to default after `gpt-5.4` override unavailable on installed CLI), reasoning effort xhigh
- **Account**: picassoer651@gmail.com (score 35%, no switch needed)
- **Invocation**: `codex review --base origin/main`
- **Session ID**: 019dc3ba-d0ce-7e53-8d05-fb6874b8bc7b
- **Verdict tier**: P2 (medium-priority) — 2 findings, both actionable

## Findings

### F1 [P2] — `src/foam_agent_adapter.py:3591-3592` — bc declaration trust on icoFoam path

**Issue (verbatim from Codex):**
> If a caller uses the new `boundary_conditions["turbulence_model"]` override (the
> comment explicitly mentions tests and forward-compat specs), this field is
> stamped with `kOmegaSST`/etc. even though the generated case still writes
> `application icoFoam;` and does not emit the RAS fields from A.4.b.
> `_check_g2_canonical_band_shortcut()` treats any trusted `turbulence_model_used`
> as an honest turbulent run and returns early, so the current laminar
> plane-channel path can bypass the new G2 hard-fail purely by changing metadata.

**Impact:** PASS-washing risk — a metadata-only override bypasses G2 even though
the generator still emits the laminar icoFoam case dir. This contradicts the
core safety invariant DEC-V61-059 was meant to enforce.

**Fix (committed in this round):** Untie `bc["turbulence_model_used"]` from
caller declaration. Stage A.4.a is the laminar-only emission path; the bc
field hard-pins to `"laminar"` regardless of the resolved declared model
until A.4.b lands the simpleFoam + RAS files. A new internal flag
`_emits_rans_path = False` (default in A.4.a) gates BOTH the bc stamp AND
the `constant/turbulenceProperties` content so they cannot drift apart.
A.4.b will flip the flag to `(resolved != "laminar")` in a single line
once it also emits the corresponding solver dictionaries.

**Test:** `test_a4a_locks_bc_to_laminar_even_when_caller_overrides` —
asserts that even with `bc["turbulence_model"]="kOmegaSST"` set,
`bc["turbulence_model_used"]` resolves to `"laminar"` AND
`turbulenceProperties` emits `simulationType laminar` (no `RASModel` block).

### F2 [P2] — `src/plane_channel_extractors.py:168-173` — repo-standard hyphenated spellings

**Issue (verbatim):**
> The canonicalizer only recognizes camelCase names, but this repo already uses
> hyphenated spellings like `k-omega SST` and `k-epsilon` in its knowledge
> sources. When a plane-channel run carries one of those existing values,
> `turbulence_model_used` falls through unchanged and G2 treats the run as
> untrusted, hard-failing a legitimate turbulent case as
> `CANONICAL_BAND_SHORTCUT_LAMINAR_DNS`.

**Verification of claim:**
```
knowledge/whitelist.yaml:60   turbulence_model: k-epsilon
knowledge/whitelist.yaml:137  turbulence_model: k-epsilon
knowledge/whitelist.yaml:215  turbulence_model: k-omega SST
knowledge/whitelist.yaml:243  turbulence_model: k-omega SST
src/knowledge_db.py:209       return "k-omega SST"
```
Confirmed: hyphenated spellings are the canonical whitelist convention.

**Fix (committed in this round):** Strip-based normalization — `re.sub(r"[\s\-_]+", "", raw).lower()`
collapses `"k-omega SST"`, `"k_omega_sst"`, `"k omega SST"` → `"komegasst"` →
maps to `"kOmegaSST"` via `_MODEL_CANONICAL`. Other models covered:
`k-epsilon → kEpsilon`, `RNG k-epsilon → RNGkEpsilon`,
`spalart-allmaras → SpalartAllmaras`, `realizable k-epsilon → realizableKE`.

**Test:** `test_canonicalize_turbulence_model_hyphenated_repo_spellings` —
9 cases covering whitelist conventions + delimiter variants.

## Positive observations from review

- Codex independently verified the G2 detector logic by running it through a
  fabricated canonical-band emission (`k-omega SST` declaration with Moser-DNS
  u+ values) and confirmed it correctly fires when canonicalization fails to
  match — i.e. the gate's fail-closed semantics are intact, just the
  trusted-model recognition was too narrow.
- Codex did not flag concerns on:
  - G2 two-region match logic (viscous-sublayer + log-law)
  - G2 tolerance constant 20%
  - Mesh grading numerical assertion (X=15, dy_wall ≈ 2.30e-3, y+_first ≈ 1.82)
  - `compute_friction_coefficient` formula
  - ADR-001 plane assignments
  - Test coverage gaps (intake §6 honest-pass-rate calibration)
- Both findings are P2 (medium priority) — no P0/P1 surfaced, indicating the
  Stage A surface is broadly sound.

## Pass-rate calibration

- **Self-estimated**: 0.40 (intake §6, predicting CHANGES_REQUIRED with 2-3 HIGH + 1-2 MED)
- **Actual**: 0 HIGH + 2 MED → verdict CHANGES_REQUIRED
- **Calibration**: I over-estimated the HIGH count by 2-3, under-estimated the
  MED count by 0-1. Net pass-rate read closer to 0.55 than 0.40 — the Stage A
  surface was actually cleaner than my honesty-clause forecast. This is the
  reverse direction of the DEC-V61-036b miss (claimed 0.60, actual 0.42), so
  the calibration is converging.

## Round-2 readiness

- Both fixes landed (this commit)
- Tests: 48/48 DEC-V61-059 green (added 2 regression tests for F1+F2)
- Codex round-2 invocation budget: 3 remaining (per intake §8)
- Recommend round-2 review after this commit lands to clean-close Stage A
  before A.4.b/A.5 begin.
