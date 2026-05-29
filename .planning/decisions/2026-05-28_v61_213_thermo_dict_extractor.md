---
decision_id: V61-213
title: thermo_dict extractor (case dir → Mapping[str, Any]) — sub-DEC
status: Accepted
parent_dec: V61-211
phase: P2 (Blueprint v4)
notion_sync_status: synced 2026-05-30 (https://www.notion.so/36fc68942bed8167a825d46059874a7e)
---

# DEC-V61-213 · thermo_dict extractor for case-behavioral eval (Stage-2 2c)

## Context

DEC-V61-211 landed `solver_block_extractor` as the first `case_extractors/`
member — a stdlib-only, line-anchored, pure-function reader over
`system/controlDict` that turns a case dir into a `SolverBlockSnapshot`
the advisor stack consumes via
`assemble_stack(solver_block_snapshot=…)`. DEC-V61-212 followed the
same shape for `system/snappyHexMeshDict` → `Mapping[str, Any]` feeding
`validate_shm_dict`.

The corresponding rung for the **A10 thermo-polynomial-range** advisor
(`ui/backend/services/geometry_ingest/thermo_polynomial_range_advisor.py:315`,
`check_thermo_polynomial_range(janaf_thermo_dict, boundary_conditions, …)`)
is still hand-built fixtures: `tests/test_advisor_stack.py:77-92`
synthesizes a 1-species shape, and
`tests/test_thermo_polynomial_range_advisor.py:61-114` synthesizes the
case_009 53-species janaf shape. No production code constructs
`thermo_dict` from a case dir today.
`ui/backend/services/advisor_stack.py:881-896` dispatches the advisor
under the `thermo_polynomial_range_advisor` name whenever
`thermo_dict is not None`. **This DEC closes that gap** as the third
member of the `case_extractors` sub-package.

Survey (this session, 2026-05-28) — 6 in-repo `*_dicts/` profiles ship
a `constant/thermophysicalProperties`:

- `case_006_v64_thermo_fpe_fix_dicts/constant/thermophysicalProperties`
- `case_006_v64_val_full_2_dicts/constant/thermophysicalProperties`
- `case_006_v64_val_full_2_dicts/_v24_rhocentralfoam_fallback/constant/thermophysicalProperties`
- `case_016_v64_thermo_fpe_fix_dicts/constant/thermophysicalProperties`
- `case_030_v65_wedge15ma5_v106_2nd_witness_dicts/constant/thermophysicalProperties`
- `case_031_v65_naca0012_supersonic_v106_retry_dicts/constant/thermophysicalProperties`

5 of 6 use `thermo hConst`; the 6th (`_v24_rhocentralfoam_fallback`)
uses `thermo eConst` with `Cv 717.5` — v0.1 returns `None` for the
eConst profile (scope-locked OUT, see §"Scope-locking rationale").

## Decision

Add `case_extractors/thermo_dict_extractor.py` exporting:

```python
extract(case_dir: Path) -> tuple[Mapping[str, Any], ThermoModelTags] | None
```

returning the **single-species `mixture`-block shape** the in-repo
case_profiles ship, in the species-keyed form
`check_thermo_polynomial_range` already understands
(`{"_mixture": {"specie": …, "thermodynamics": {…}, "transport": {…}}}`)
PAIRED with a `ThermoModelTags` companion dataclass exposing the
`thermoType` block tokens. The advisor consumes only the dict; the
eval/test layer consumes the tags for case-discrimination (4 distinct
`(transport, energy)` tuples across 5 hConst profiles).

### Scope (v0.1 · this DEC)

**In** — parse `<case_dir>/constant/thermophysicalProperties` and emit:

| Extractor key | Source key in OF dict | Type | Required? |
|---|---|---|---|
| `_mixture` (sentinel top-level key) | synthesized — paired-brace `mixture { … }` block | dict | required (refused if no `mixture` block) |
| `_mixture.specie.molWeight` | `mixture.specie.molWeight` | float | **REQUIRED** (extractor → None if absent / unparseable) |
| `_mixture.thermodynamics.Cp` | `mixture.thermodynamics.Cp` (when `thermo hConst`) | float | optional |
| `_mixture.thermodynamics.Hf` | `mixture.thermodynamics.Hf` | float | optional |
| `_mixture.transport.As` / `Ts` | `mixture.transport.{As,Ts}` (when `transport sutherland`) | float | both required when transport=sutherland (partial → None) |
| `_mixture.transport.mu` / `Pr` | `mixture.transport.{mu,Pr}` (when `transport const`) | float | both required when transport=const (partial → None) |
| `ThermoModelTags.type` | `thermoType.type` | str (e.g. `hePsiThermo`) | required |
| `ThermoModelTags.mixture` | `thermoType.mixture` | str (e.g. `pureMixture`) | required |
| `ThermoModelTags.transport` | `thermoType.transport` | str (`sutherland` ∨ `const`) | required |
| `ThermoModelTags.thermo` | `thermoType.thermo` | str (`hConst`; `eConst` → extractor None) | required |
| `ThermoModelTags.equation_of_state` | `thermoType.equationOfState` | str (`perfectGas`) | required |
| `ThermoModelTags.specie` | `thermoType.specie` | str (`specie`) | required |
| `ThermoModelTags.energy` | `thermoType.energy` | str (`sensibleEnthalpy` ∨ `sensibleInternalEnergy`) | required |

The advisor's `_extract_species_tlows`
(`thermo_polynomial_range_advisor.py:248-259`) iterates `dict.items()`
over top-level species names; the sentinel `_mixture` (leading
underscore — recognizable as synthetic) gives a faithful subtree for
path-(d) typo walking (lines 486-512) where every emitted key is in
`CANONICAL_THERMO_KEYS` and thus does NOT trigger a typo finding.

### Why thermo_dict v0.1 has real discrimination

5 hConst profiles split as follows (verified 2026-05-28 by reading
each file end-to-end):

| Profile | `thermoType.transport` | `energy` | `thermo` |
|---|---|---|---|
| `case_006_v64_thermo_fpe_fix_dicts` (`thermophysicalProperties:14-22`) | `sutherland` | `sensibleEnthalpy` | `hConst` |
| `case_006_v64_val_full_2_dicts` (`thermophysicalProperties:8-17`) | `const` | `sensibleEnthalpy` | `hConst` |
| `case_016_v64_thermo_fpe_fix_dicts` (`thermophysicalProperties:18-27`) | `sutherland` | `sensibleInternalEnergy` | `hConst` |
| `case_030_v65_wedge15ma5_v106_2nd_witness_dicts` (`thermophysicalProperties:17-26`) | `const` | `sensibleInternalEnergy` | `hConst` |
| `case_031_v65_naca0012_supersonic_v106_retry_dicts` (`thermophysicalProperties:18-27`) | `sutherland` | `sensibleInternalEnergy` | `hConst` |

**4 distinct `(transport, energy)` combinations across 5 profiles** —
real differentiation from v0.1 alone, before any mechanism support is
added. Mirrors DEC-211's "5 distinct solvers across 26 profiles"
pattern at smaller scale.

The advisor's path-(a)/(b)/(c) logic
(`thermo_polynomial_range_advisor.py:393-481`) returns clean (no
findings) on all 5 profiles — every species's `Tlow` is absent
(hConst, not janaf), so the species_tlows census is empty and both
rules vacuously pass. This is the **correct** result; the value of
v0.1 is feeding `assemble_stack` so the dispatcher records "A10
advisor dispatched → 0 findings" rather than "A10 advisor skipped
(no thermo_dict)" — a truth-chain distinction the eval depends on
(DEC-211 §"Why solver_block first" rhymes here).

### Scope-locking rationale (anti-feature-creep)

A general OpenFOAM-dict parser is multi-hour edge-case infrastructure.
v0.1 deliberately:

- handles only **the single-`mixture` shape**
  (`mixture { specie {…} thermodynamics {…} transport {…} }`) all 6
  in-repo profiles use;
- restricts numeric parsing to `int`/`float`/scientific notation
  (mirrors `solver_block_extractor`);
- refuses (returns `None`) when any **structurally-required** block or
  key is absent (no `thermoType`, no `mixture`, no
  `mixture.specie.molWeight`, `thermo == eConst`, partial
  sutherland/const transport block).

The extractor's docstring records exactly what it does NOT support
(mirror DEC-211 module docstring §"Scope-locked NON-features" and
DEC-212's 9-line-item NON-feature list), so a future caller cannot
assume more than is there.

### v0.1 explicit NON-features (deferred / out of scope)

The extractor will NOT parse — and the docstring will record each
line-item so a future caller cannot quietly assume more:

1. **janaf-polynomial / multi-species mechanism shape**
   (`lowCpCoeffs`/`highCpCoeffs` + per-species `Tlow`/`Thigh`/`Tcommon`
   records). **Zero in-repo case_profiles ship this format today**
   (verified 2026-05-28: only `case_009_sandia_flame_d.md` discusses
   it; no `*_dicts/` directory contains it). Adding mechanism support
   is a follow-on sub-DEC the day case_009 sediments a `_dicts/`
   artifact.
2. **`thermo == eConst`** (the `_v24_rhocentralfoam_fallback` profile).
   v0.1 returns `None` — sole eConst profile carries `Cv` not `Cp`,
   and the v0.1-narrow contract mirrors `solver_block_extractor`'s
   "don't emit a half-shape we can't validate." Follow-on sub-DEC adds
   eConst→Cv reading when a real run needs it.
3. **`#include`d sub-dicts** (e.g. `#include "thermoMixture.foam"`).
   Pre-flight audit of all 6 in-repo thermo files confirms **zero**
   `#`-directives, so the extractor never needs to handle them in v0.1
   (mirror DEC-212 R2 retro lesson #2: enumerate ALL forms BEFORE
   writing, but only ship the form real evidence requires).
4. **Macro substitution** (`$molWeight`, `$Cp`) and `#calc`
   expressions. Captured as literal token by regex, would be
   unparseable float ⇒ snapshot `None` (honest refusal, not
   fabrication). Mirror solver_block_extractor.py:24-28
   macro-substitution scope-out language.
5. **Multi-species top-level shape** (e.g.
   `mixture { species (CH4 O2 N2); … }` or species-keyed dict where
   top-level keys ARE species names). v0.1 emits only the single
   `_mixture` synthetic key. Separate sub-DEC when real multi-species
   ships.
6. **`0/T` boundary conditions** (`thermo_boundary_conditions` kwarg of
   `check_thermo_polynomial_range`) — separate extractor under
   separate sub-DEC; different directory (`0/T` not `constant/…`),
   different failure modes.
7. **Synthesizing a default `Tlow` under hConst/eConst** — extractor
   MUST NOT (Truth-chain R2 below). Absence is the truth.
8. **Brace-depth-unawareness inside the mixture/thermoType slices** —
   once the paired-brace scan locates the outer block, inner regexes
   are line-anchored at column 0 within the slice. A malformed
   nested-block-with-same-key would false-match. All 6 in-repo files
   verified well-formed; mirror solver_block_extractor.py:32-42
   language.
9. **String-literal-unaware comment stripping** — mirror
   solver_block_extractor.py:43-49 + shm_dict_extractor.py:83-85. Safe
   for v0.1's numeric-value-only keys.

## Architectural placement

- New module:
  `ui/backend/services/case_extractors/thermo_dict_extractor.py`
  + `__init__.py` re-export `extract_thermo_dict_snapshot`.
- **Import-linter (ADR-001) scope**: `ui/backend/*` is out of contract
  scope per ADR-001 §3.2 (root_package=`src`). No contract impact
  (mirrors DEC-211/212).
- **Local-mirror policy** (mirror DEC-211 R0 P1): `ThermoModelTags` is
  a **new** dataclass defined in this extractor, NOT imported from
  geometry_ingest. There is no upstream `ThermoModelTags` to mirror
  today; the advisor consumes a plain dict and never reads
  `thermoType`. If a future advisor consumes `ThermoModelTags`, a
  `test_thermo_model_tags_mirror_parity` canary in the geometry_ingest
  module would be added then.
- **trimesh import risk** (DEC-211 R0 P1 root cause): same risk applies
  — `from geometry_ingest.thermo_polynomial_range_advisor import …`
  would pull `geometry_ingest/__init__.py → health_check → trimesh`.
  Resolution identical to DEC-211/212: this extractor does NOT import
  the advisor; it emits a plain dict shape the advisor already
  accepts.
- Imports: stdlib only (`pathlib`, `re`, `dataclasses`, `typing`).

## Four-question gate

| Question | Answer |
|---|---|
| LLM-offline runnable? | yes — pure function, stdlib only, no LLM in import chain |
| Clear artifacts? | the returned `(Mapping, ThermoModelTags)` tuple + pytest |
| TrustGate/audit explains trust? | extractor's docstring enumerates non-features; truth-chain: returns `None` on any structural gap (never a half-built dict); `_mixture` sentinel + absent `Tlow` documented as deliberate honest-omission |
| AI advisory-only, no mutating route? | yes — read-only `Path.read_text`, no writes, no route registration |

## Truth-chain (mirror DEC-211 §"Codex R0 P2#2" + DEC-212 §"Truth-chain risk")

Every extractor key traces to a verifiable source line:

| Extractor key | Verifiable source line(s) | Detection path in advisor |
|---|---|---|
| `_mixture` (sentinel top-level key) | synthesized — NOT read from source; triggered by paired-brace `mixture { … }` at e.g. `case_006_v64_thermo_fpe_fix:24-40`. | `thermo_polynomial_range_advisor.py:248-249` iterates top-level keys as species names; never validated against canonical species set. |
| `_mixture.specie.molWeight` (REQUIRED) | `case_006_v64_thermo_fpe_fix:28` `molWeight 28.96;` · `case_006_v64_val_full_2:23` · fallback:21 · `case_016:33` · `case_030:33` · `case_031:33` — all 6 profiles. | path (d) walker (`thermo_polynomial_range_advisor.py:486-512`) — canonical (no typo flag). |
| `_mixture.thermodynamics.Cp` (when hConst) | `case_006_v64_thermo_fpe_fix:32` `Cp 1004.5;` · `case_006_v64_val_full_2:27` · `case_016:37` · `case_030:37` `Cp 2.5;` · `case_031:37` `Cp 1005;` — 5 hConst profiles. Fallback uses `Cv 717.5` (eConst) — extractor → None. | path (d) walker — canonical. |
| `_mixture.thermodynamics.Hf` | all 6 profiles emit `Hf 0;`. | path (d) walker — canonical. |
| `_mixture.thermodynamics.Tlow` (ABSENT under hConst/eConst) | never present in any of the 6 in-repo files — that IS the truth (hConst has no polynomial range). | `thermo_polynomial_range_advisor.py:255-258` `_extract_species_tlows` drops species with no coercible Tlow ⇒ census empty ⇒ paths (a)/(b)/(c) vacuous ⇒ `is_clean=True` (acceptance #4). |
| `_mixture.transport.As` / `Ts` (when sutherland) | `case_006_v64_thermo_fpe_fix:37-38` `As 1.458e-06; Ts 110.4;` · `case_016:42-43` · `case_031:42-43`. | path (d) walker — canonical. |
| `_mixture.transport.mu` / `Pr` (when const) | `case_006_v64_val_full_2:32-33` `mu 1.79e-5; Pr 0.71;` · `case_030:42-43`. | path (d) walker — canonical. |
| `ThermoModelTags.type` (e.g. `hePsiThermo`) | all 6 profiles emit `hePsiThermo` in `thermoType { … }`. | NOT consumed by advisor today; eval discriminator only. |
| `ThermoModelTags.transport` (`sutherland` ∨ `const`) | 3 sutherland + 3 const across 6 profiles per discrimination table above. | eval discriminator — `assemble_stack` consumes dict; eval reads tags. |
| `ThermoModelTags.thermo` (`hConst` ∨ `eConst`) | hConst in 5 of 6; eConst in fallback:11. | eval discriminator; extractor returns None if thermo == eConst (v0.1 scope-out). |
| `ThermoModelTags.energy` (`sensibleEnthalpy` ∨ `sensibleInternalEnergy`) | 2 sensibleEnthalpy + 4 sensibleInternalEnergy across 6 profiles. | eval discriminator. |
| `ThermoModelTags.equation_of_state` (`perfectGas`) | all 6 profiles emit `perfectGas`. | eval discriminator. |
| `ThermoModelTags.mixture` (`pureMixture`) | all 6 profiles emit `pureMixture`. | eval discriminator; gates the `_mixture` sentinel choice. |

Three fabrication risks the implementation must defend against (mirror
DEC-211 P2#2 pattern):

**(R1) `pureMixture` has no explicit species name**. The OF dict uses
a single block called `mixture { specie { molWeight … } … }`. The
advisor's `_extract_species_tlows`
(`thermo_polynomial_range_advisor.py:239-259`) iterates `dict.items()`
over top-level species names. If we pick a sentinel name (e.g.
`"air"`) the advisor will silently process a species that doesn't
exist by that name in the case. **Resolution**: use the literal
sentinel `"_mixture"` (leading underscore) — recognizable as
"synthetic name, derived from pureMixture block" by anyone reading
eval output. Document in docstring + pin in a test. (An alternative —
derive name from `thermoType.mixture` — gives the string
`"pureMixture"` which is worse: looks like a real species name to a
glancing reader.)

**(R2) `Cp` without `Tlow`/`Thigh`** (hConst case). The advisor's
`_extract_species_tlows` skips species with no coercible Tlow
(correctly — `thermo_polynomial_range_advisor.py:255-258`). Our
extractor MUST NOT synthesize a default `Tlow`; the truth is "this
case uses hConst, there is no per-species polynomial range". Leave
`thermodynamics.Tlow` absent. The advisor will census `0/0/0` species
which is the honest answer.

**(R3) Mixed-line block syntax** (e.g.
`FoamFile { … object thermophysicalProperties; }` on one line —
`case_006_v64_thermo_fpe_fix:11`, `case_006_v64_val_full_2:6`,
fallback:4). The regex strategy must not false-match a key buried in
a one-liner like that. Mirror DEC-211's
`_strip_comments`-then-line-anchored-regex pattern but additionally
require the key to appear inside `mixture { … }` /
`thermoType { … }` blocks (not at module top level). The safest v0.1
implementation: locate the `mixture { … }` and `thermoType { … }`
braces by paired-brace scan (mirror
`shm_dict_extractor.py:152-176 _find_top_level_block`), then run
regexes inside the slice. Paired-brace scan is ~25 LOC and is the
strict minimum to handle the in-repo shapes without false-matching
`FoamFile` braces.

**Honest-omission contract**: if `constant/thermophysicalProperties`
is missing → `None`. If file exists but lacks `mixture { … }` or
`thermoType { … }` block → `None`. If `mixture.specie.molWeight` is
absent or unparseable → `None`. If `thermo == eConst` (v0.1
scope-out) → `None`. If transport block parses partially (sutherland
with only one of As/Ts; const with only one of mu/Pr) → `None`. If
duplicate top-level `thermoType` or duplicate `molWeight` inside
specie → `None` (mirror solver_block_extractor.py:200-228
duplicate-key refusal). **Half-populated snapshots are never
returned.**

## Acceptance (sub-DEC passes when)

1. `ui/backend/services/case_extractors/thermo_dict_extractor.py`
   exists, imports cleanly without trimesh in chain, exports
   `extract(case_dir) → (Mapping, ThermoModelTags) | None` and
   `ThermoModelTags` dataclass.
2. `tests/test_thermo_dict_extractor.py` parametrizes over all 5
   in-repo hConst profiles
   (`case_006_v64_thermo_fpe_fix`, `case_006_v64_val_full_2`,
   `case_016_v64_thermo_fpe_fix`,
   `case_030_v65_wedge15ma5_v106_2nd_witness`,
   `case_031_v65_naca0012_supersonic_v106_retry`), asserts every
   profile yields a non-None `(Mapping, ThermoModelTags)` whose
   `(transport, energy)` tuple matches the baseline mapping (4
   distinct tuples across 5). Includes a
   `covers_all_in_repo_profiles` canary scanning
   `.planning/case_profiles/**/constant/thermophysicalProperties` —
   fails on new profile not in baseline (DEC-211 silent-drift guard
   pattern at `test_solver_block_extractor.py:98-120`).
3. `test_econst_profile_returns_none` — the sole eConst profile
   (`case_006_v64_val_full_2/_v24_rhocentralfoam_fallback`) → `None`.
   Pin: docstring §NON-features documents `thermo == eConst → None`.
4. Edge-case units (mirror DEC-211 / DEC-212 patterns): missing
   `constant/thermophysicalProperties` → `None`; no `mixture` block
   → `None`; no `thermoType` block → `None`; missing `molWeight`
   → `None`; commented `// molWeight 99.0;` does NOT false-match
   (real `molWeight 28.96;` extracted); FoamFile one-liner header
   does NOT false-match (paired-brace scan correctly identifies
   mixture/thermoType blocks); duplicate `molWeight` or duplicate
   `thermoType { … }` → `None`.
5. `test_sutherland_emits_As_Ts` / `test_const_emits_mu_Pr`:
   Sutherland tmp_path → snap has `As`, `Ts` (floats), NO `mu`/`Pr`;
   const tmp_path → has `mu`, `Pr`, NO `As`/`Ts`. Partial sutherland
   (As only, no Ts) → `None` (honest refusal); partial const (mu
   only, no Pr) → `None`.
6. `test_thermo_model_tags_emitted_per_profile`: for each of the 5
   hConst profiles, the returned `ThermoModelTags` has all 6 string
   fields populated and matches baseline.
7. `test_advisor_returns_is_clean_for_all_hconst_profiles`: for each
   of the 5 hConst profiles, feed `extract(case_dir)` directly into
   `check_thermo_polynomial_range(snap, None)` (under
   `pytest.importorskip('trimesh')` guard to keep module-load
   stdlib-only). Assert `report.findings == ()` and
   `report.species_coverage.total_species_with_tlow == 0`. This is
   the critical truth-chain pin that no findings are fabricated from
   hConst input.
8. `test_extractor_module_loads_without_trimesh` — subprocess with
   `PYTHONPATH=REPO_ROOT`, sentinel-raise on `import trimesh`,
   import `case_extractors.thermo_dict_extractor` + access
   `extract`, `ThermoModelTags` — succeeds. Mirror
   `test_solver_block_extractor.py:465-513` — pins the stdlib-only
   architectural promise (DEC-211 R0 P1 lesson).
9. `test_assemble_stack_discriminates_compressible_vs_incompressible`:
   call `assemble_stack(thermo_dict=extract(case_006_v64_thermo_fpe_fix))`
   → `'thermo_polynomial_range_advisor'` in `advisors_dispatched`;
   call `assemble_stack(thermo_dict=extract(case_021_v64_val_full_3_incomp_dicts))`
   → `extract` returns `None` (no `constant/thermophysicalProperties`),
   so `thermo_dict=None`, so `'thermo_polynomial_range_advisor'` NOT
   in `advisors_dispatched`. Live case-discrimination proof. Skip if
   trimesh missing.
10. `test_macro_value_returns_none`: tmp_path source with
    `molWeight $molWeight;` (macro substitution v0.1 scope-out) →
    `None` (unparseable float ⇒ honest refusal).
11. Codex relay APPROVE or APPROVE_WITH_COMMENTS-with-inline-fixes
    (cap=3); local commit before review allowed under L2.
12. No regression in v9 + canonical + advisor_stack test sweeps.

## Estimated LOC

- `thermo_dict_extractor.py` impl: ~140-180 LOC (paired-brace scan
  + 6-8 inner regexes for thermoType tokens + 4-6 inner regexes for
  mixture sub-blocks + `ThermoModelTags` dataclass + extract +
  docstring block). Slightly larger than DEC-211's ~205 LOC (more
  tokens to extract) and comparable to DEC-212's ~150-180 LOC.
- `__init__.py` patch: +2 LOC (re-export).
- `tests/test_thermo_dict_extractor.py`: ~250-320 LOC (parametrized
  sweep over 5 hConst profiles + 1 eConst negative + ~10 edge-case
  units + advisor round-trip test + module-loads-without-trimesh
  subprocess + assemble_stack discrimination test). Comparable to
  DEC-212's ~200-260 LOC (extra: ThermoModelTags assertions +
  hConst/eConst branching).
- **Total ~390-500 LOC including tests** — comfortably sub-DEC
  scope (not charter, not spike).

## Status

Accepted 2026-05-28 by cfd-chief-engineer under user-approved
"α′ extension sub-DEC" L2 route, mirroring DEC-V61-211 / DEC-V61-212
landing pattern. Implementation + Codex review chain landed
**2026-05-30** (workflow `wf_2effcd52-5a5` → Codex CRS R0
APPROVE_WITH_COMMENTS with 1 P3 finding → R1 fix in same commit).

### Cadence Codex R1 (2026-05-30 · CRS APPROVE_WITH_COMMENTS · 1 P3 closed)

CRS gpt-5.4 high reviewed the staged extractor + tests + sub-DEC
diff and surfaced one P3 truth-chain finding that the workflow's
Hf-optional branch silently dropped instead of refusing:

- **[P3]** `Hf` field treated as absent when duplicated (`Hf 0; Hf 1;`)
  or macro (`Hf $macro;`). Root cause: the value-capturing `_HF_RE`
  regex requires a numeric value, so `_HF_RE.findall(body)` returns
  0 matches for both "Hf absent" and "Hf present but ambiguous";
  `_single_match_or_none()` collapsed both into the optional-omission
  branch — emitting a snapshot with Hf silently dropped, hiding
  source ambiguity. Violates the v0.1 truth-chain/refusal contract
  (architecture invariant #4 "honest None over fabrication").

- **R1 fix (this commit):** added `_HF_KEY_PRESENCE_RE` — a key-only
  matcher independent of numeric parseability — and a key-present
  guard in `_extract_thermodynamics_block`: when the `Hf` key is
  detected in source but the value-capturing single-match returns
  None (duplicate / macro / `#calc` / other unparseable form),
  snapshot now refuses honestly (returns None). When the key is
  truly absent, optional omission preserved. Two pinning tests
  added: `test_hf_duplicate_refuses_snapshot` +
  `test_hf_macro_refuses_snapshot` (38 → 40 thermo tests · 151 → 153
  Stage-2 2b sibling regression green).

The same fix pattern (key-presence detector + ambiguity refusal)
should be considered for any future optional numeric field that
shares the `_NUMERIC_VALUE` regex shape — track as a follow-on
audit if more optional numeric fields land in `case_extractors/`.

## Out of scope (do NOT do under this DEC; record as follow-on)

- janaf-polynomial / multi-species mechanism shape (v0.2 — when
  case_009 sediments a `_dicts/` artifact).
- `0/T` boundary-conditions extractor (separate sub-DEC; needed for
  `thermo_boundary_conditions` kwarg in `assemble_stack`).
- `thermo == eConst` → emit Cv-based dict (separate sub-DEC; needs
  a real run that exercises the fallback profile).
- `#include` / macro / `#calc` resolution.
- `step` / `thin_wall` / `parts_manifest` extractors (DEC-V61-214 +
  future sub-DECs).
- Same-line block-form `#`-directives (`#codeStream {`,
  `#calc {`) — pre-flight audit confirms zero in-repo thermo files
  use them; if a future case does, add the ~10 LOC peek fix per
  DEC-V61-212 carry-forward.
- Wiring into production `ai_diagnose.py` / `ai_review.py` routes
  (route-side decision under a different DEC).
- Extending behavioral assertions to FULL E-case firing sets (needs
  all extractors landed first).

— cfd-chief-engineer, 2026-05-28
