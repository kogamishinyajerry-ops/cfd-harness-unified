---
decision_id: V61-213
title: thermo_dict extractor (case dir → Mapping[str, Any]) — sub-DEC (DRAFT)
status: Proposed
parent_dec: V61-211
phase: P2 (Blueprint v4)
notion_sync_status: not synced (DRAFT — sync gated on Accepted)
---

# DEC-V61-213 (DRAFT) · thermo_dict extractor for case-behavioral eval (Stage-2 2c)

## Context

DEC-V61-211 landed `solver_block_extractor` as the first
`case_extractors/` member — a 3-regex line-anchored reader over
`system/controlDict` that turns a case dir into a `SolverBlockSnapshot`
the advisor stack consumes via `assemble_stack(solver_block_snapshot=…)`.

The corresponding rung for the **A10 thermo-polynomial-range** advisor
(`ui/backend/services/geometry_ingest/thermo_polynomial_range_advisor.py:315`,
`check_thermo_polynomial_range(janaf_thermo_dict, boundary_conditions, …)`)
is still hand-built fixtures: `tests/test_advisor_stack.py:77-92`
synthesizes a 1-species shape, and `tests/test_thermo_polynomial_range_advisor.py:61-114`
synthesizes the case_009 53-species janaf shape. No production code
constructs `thermo_dict` from a case dir.

## Decision

Add `case_extractors/thermo_dict_extractor.py` with:
```
extract(case_dir: Path) -> Mapping[str, Any] | None
```
returning the **single-species `mixture`-block shape** the in-repo
case_profiles ship, in the species-keyed form
`check_thermo_polynomial_range` already understands
(`{"<species>": {"specie": …, "thermodynamics": {…}, "transport": {…}}}`).

### Scope (v0.1 · this DEC)

**In** — parse `<case_dir>/constant/thermophysicalProperties` and emit:

| Field | Source key in OF dict | Shape in returned dict |
|---|---|---|
| species name | `mixture { … }` (pureMixture has no explicit name) | top-level key — derive from `thermoType.mixture` value or a fixed sentinel (see "Truth-chain" below) |
| `specie.molWeight` | `mixture.specie.molWeight` | float |
| `thermodynamics.Cp` | `mixture.thermodynamics.Cp` (when `thermo hConst`) | float |
| `thermodynamics.Hf` | `mixture.thermodynamics.Hf` | float |
| `transport.As`/`Ts` | `mixture.transport.{As,Ts}` (when `transport sutherland`) | float |
| `transport.mu`/`Pr` | `mixture.transport.{mu,Pr}` (when `transport const`) | float |

Plus a small **discriminator companion dataclass** `ThermoModelTags`
recording: `thermo_type`, `transport`, `thermo`, `equation_of_state`,
`energy`, `mixture` — the `thermoType` block tokens.

The companion is **NOT consumed by `check_thermo_polynomial_range`
today** (the advisor only reads species `thermodynamics.Tlow`); it is
needed by the eval to differentiate cases meaningfully (the 5 thermo
profiles split into `const+hConst` vs `sutherland+hConst` and
`sensibleEnthalpy` vs `sensibleInternalEnergy` — that IS the
case-discrimination signal — see §"Why thermo_dict v0.1 has real
discrimination").

**Architectural placement** — `ui/backend/services/case_extractors/thermo_dict_extractor.py`;
exposed via the package as `extract_thermo_dict_snapshot`. Stdlib only.

**Out (deferred to v0.2 / future sub-DEC)**:
- **janaf-polynomial / multi-species mechanism shape**
  (`constant/thermo.compressibleGas` with `highCpCoeffs`/`lowCpCoeffs`
  + per-species `Tlow`/`Thigh` records). **Zero in-repo
  case_profiles ship this format today** (verified 2026-05-28: only
  `case_009_sandia_flame_d.md` discusses it; no `*_dicts/` directory
  contains it). Adding mechanism support is a follow-on sub-DEC the
  day case_009 sediments a `_dicts/` artifact.
- **`#include`d sub-dicts** (e.g. `#include "thermoMixture.foam"`).
- **Macro substitution** (`$molWeight`, `$Cp`, `#calc "…"`).
- **Reading `0/T` for `thermo_boundary_conditions`** — that's a separate
  extractor (T BC dict is in `0/` not `constant/`; different file, different
  failure modes).

**Out (separate sub-DECs)**: `shm_dict`, `step_path`, `thin_wall_inputs`,
`parts_manifest` extractors. Each is its own arc.

### Why thermo_dict v0.1 has real discrimination

The 5 in-repo profiles split as follows
(verified 2026-05-28 by reading each file end-to-end):

| Profile | `thermoType.transport` | `energy` | `thermo` |
|---|---|---|---|
| `case_006_v64_thermo_fpe_fix_dicts` (`thermophysicalProperties:14-22`) | `sutherland` | `sensibleEnthalpy` | `hConst` |
| `case_006_v64_val_full_2_dicts` (`thermophysicalProperties:8-17`) | `const` | `sensibleEnthalpy` | `hConst` |
| `case_016_v64_thermo_fpe_fix_dicts` (`thermophysicalProperties:18-27`) | `sutherland` | `sensibleInternalEnergy` | `hConst` |
| `case_030_v65_wedge15ma5_v106_2nd_witness_dicts` (`thermophysicalProperties:17-26`) | `const` | `sensibleInternalEnergy` | `hConst` |
| `case_031_v65_naca0012_supersonic_v106_retry_dicts` (`thermophysicalProperties:18-27`) | `sutherland` | `sensibleInternalEnergy` | `hConst` |

That's **4 distinct `(transport, energy)` combinations across 5 profiles** —
real differentiation from v0.1 alone, before any mechanism support is
added. Mirrors DEC-211's "5 distinct solvers across 26 profiles"
pattern at smaller scale.

The `check_thermo_polynomial_range` path-(a)/(b)/(c) logic
(`thermo_polynomial_range_advisor.py:393-481`) will return clean
(no findings) on all 5 profiles — every species's `Tlow` is absent
(hConst, not janaf), so the species_tlows census is empty and
both rules vacuously pass. This is the **correct** result for these
single-species cases; the value of the extractor in v0.1 is feeding
`assemble_stack` so the dispatcher records "A10 advisor dispatched →
0 findings" rather than "A10 advisor skipped (no thermo_dict)" — a
truth-chain distinction the eval depends on.

### Scope-locking rationale (anti-feature-creep)

A general OpenFOAM-dict parser is multi-hour edge-case infrastructure.
v0.1 deliberately:
- handles only **the single `mixture { specie {…} thermodynamics {…} transport {…} }`
  shape** all 5 in-repo profiles use,
- restricts numeric parsing to `int`/`float`/scientific notation
  (mirrors `solver_block_extractor`),
- refuses (returns `None`) when any **structurally-required** block is
  absent (no `thermoType`, no `mixture`, no `mixture.specie.molWeight`).

The extractor's docstring records exactly what it does NOT support
(mirror DEC-211 module docstring §"Scope-locked NON-features"), so a
future caller cannot assume more than is there.

### Codex review

Correctness-critical shared code (extractor output feeds advisor
findings consumed by the eval). Codex relay review required (cap=3)
before commit lands on `origin/main`. Local commit allowed under L2.
Report archived to `reports/codex_tool_reports/dec213_*`.

## Architectural placement

- New module: `ui/backend/services/case_extractors/thermo_dict_extractor.py`
  + `__init__.py` re-export `extract_thermo_dict_snapshot`.
- **Local-mirror policy** (mirror DEC-211 R0 P1): `ThermoModelTags` is a
  **new** dataclass defined in this extractor, NOT imported from
  geometry_ingest. There is no upstream `ThermoModelTags` to mirror today;
  the advisor consumes a plain dict and never reads `thermoType`. If a
  future advisor consumes `ThermoModelTags`, a `test_thermo_model_tags_mirror_parity`
  canary in the geometry_ingest module would be added then.
- **trimesh import risk** (DEC-211 R0 P1 root cause): same risk applies —
  `from geometry_ingest.thermo_polynomial_range_advisor import …` would
  pull `geometry_ingest/__init__.py → health_check → trimesh`. Resolution
  identical to DEC-211: this extractor does NOT import the advisor; it
  emits a plain dict shape the advisor already accepts.
- Imports: stdlib only (`pathlib`, `re`, `dataclasses`).

## Four-question gate

| Question | Answer |
|---|---|
| LLM-offline runnable? | yes — pure function, stdlib only, no LLM in import chain |
| Clear artifacts? | the returned `dict` snapshot + `ThermoModelTags`; pytest |
| TrustGate/audit explains trust? | extractor's docstring enumerates non-features; truth-chain: returns `None` on any structural gap (never a half-built dict) |
| AI advisory-only, no mutating route? | yes — read-only `Path.read_text`, no writes, no route registration |

## Truth-chain concerns (mirror DEC-211 §"Codex R0 P2#2" pattern)

Three fabrication risks the implementation must defend against:

1. **`pureMixture` has no explicit species name**. The OF dict uses a
   single block called `mixture { specie { molWeight … } … }`. The
   advisor's `_extract_species_tlows`
   (`thermo_polynomial_range_advisor.py:239-259`) iterates `dict.items()`
   over top-level species names. If we pick a sentinel name (e.g.
   `"air"`) the advisor will silently process a species that doesn't
   exist by that name in the case. **Resolution**: use the literal
   sentinel `"_mixture"` (leading underscore) — recognizable as
   "synthetic name, derived from pureMixture block" by anyone reading
   the eval output. Document in docstring + pin in a test. (An
   alternative — derive name from `thermoType.mixture` — gives the
   string `"pureMixture"` which is worse: looks like a real species
   name to a glancing reader.)
2. **`Cp` without `Tlow`/`Thigh`** (hConst case). The advisor's
   `_extract_species_tlows` skips species with no coercible Tlow
   (correctly — `thermo_polynomial_range_advisor.py:255-258`). Our
   extractor MUST NOT synthesize a default `Tlow`; the truth is "this
   case uses hConst, there is no per-species polynomial range". Leave
   `thermodynamics.Tlow` absent. The advisor will census `0/0/0`
   species which is the honest answer.
3. **Mixed-line block syntax** (e.g. `FoamFile { … object thermophysicalProperties; }`
   on one line — case_006_v64_thermo_fpe_fix:11). The regex strategy
   must not false-match a key buried in a one-liner like that. Mirror
   DEC-211's `_strip_comments`-then-line-anchored-regex pattern but
   additionally require the key to appear inside `mixture { … }` /
   `thermoType { … }` blocks (not at module top level). The safest
   v0.1 implementation: locate the `mixture { … }` and `thermoType { … }`
   braces by paired-brace scan, then run regexes inside the slice.
   Paired-brace scan is ~25 LOC and is the strict minimum to handle
   the in-repo shapes without false-matching `FoamFile` braces.

Honest-omission contract: if `constant/thermophysicalProperties` is
missing → `None`. If file exists but lacks `mixture { … }` or
`thermoType { … }` block → `None`. If `mixture.specie.molWeight` is
absent or unparseable → `None`. **Half-populated snapshots are never
returned.**

## Acceptance (sub-DEC passes when)

1. `ui/backend/services/case_extractors/thermo_dict_extractor.py` exists,
   imports cleanly without trimesh in chain, exports `extract`.
2. `tests/test_thermo_dict_extractor.py` parametrizes over all 5 in-repo
   `*_dicts/` profiles that ship `constant/thermophysicalProperties`,
   asserts every profile yields a non-None snapshot whose
   `(transport, energy)` tuple matches the baseline mapping (4 distinct
   tuples across 5).
3. Test asserts a missing-file case returns `None`, a malformed
   (no `mixture` block) case returns `None`, a comment-buried key does
   not false-match — mirrors DEC-211 edge-case unit pattern.
4. Test asserts `check_thermo_polynomial_range(snap, None)` returns
   `is_clean=True` for all 5 profiles (the advisor's correct behavior
   on hConst — no janaf Tlow census to populate) — pins the truth-chain
   guarantee that no findings are fabricated from hConst input.
5. `test_advisor_stack_real_case_behavioral_spike` (or sibling) extended:
   feed extractor output through `assemble_stack(thermo_dict=…)` for
   case_006 (compressible) vs case_021 (incompressible — no thermo
   file). Assert dispatched-advisor sets differ
   (`thermo_polynomial_range_advisor` in former, not latter) — live
   case-discrimination proof.
6. Codex relay APPROVE or APPROVE_WITH_COMMENTS-with-inline-fixes
   (cap=3); local commit before review allowed under L2.
7. No regression in v9 + canonical + advisor_stack test sweeps.

## Estimated LOC

- `thermo_dict_extractor.py` impl: ~120-140 LOC (paired-brace scan +
  3-5 inner regexes + ThermoModelTags dataclass + extract + docstring
  block similar in length to DEC-211's). Slightly larger than DEC-211's
  ~205 LOC because of the paired-brace scan (~25 LOC) + extra block
  walk. Estimate **~140 LOC** for impl, **~180-200 LOC** for tests
  (parametrized sweep over 5 profiles + ~8 edge-case units + advisor
  round-trip test). **Total ~320-340 LOC** — comfortably sub-DEC scope
  (not charter, not spike).

## Status

Proposed (DRAFT — awaiting cfd-chief-engineer review + user approval to
promote to Accepted under the same "α′ extension sub-DEC" L2 route as
DEC-V61-211).

## Out of scope (do NOT do under this DEC; record as follow-on)

- janaf-polynomial / multi-species mechanism shape (v0.2 — when case_009
  sediments a `_dicts/` artifact).
- `0/T` boundary-conditions extractor (separate sub-DEC; needed for
  `thermo_boundary_conditions` kwarg in `assemble_stack`).
- `#include` / macro / `#calc` resolution.
- shm_dict / step / thin_wall extractors (each its own sub-DEC).
- Wiring into production `ai_diagnose.py` / `ai_review.py` routes
  (route-side decision under a different DEC).

— cfd-chief-engineer (DRAFT), 2026-05-28
