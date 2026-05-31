---
decision_id: V61-220
title: thermo_dict multi-region variant (per-region thermophysicalProperties, fluid+solid) — P3 W3.0.2 sub-DEC
status: Accepted
parent_dec: V61-217
phase: P3 (Blueprint v4 · CHT)
autonomous_governance: true
confidence: med
kogami_opt_in: false
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh (R0) → CRS gpt-5.4 high (R1+R2, 86gs upstream stream-failed mid-R1 per DEC-V61-214 fallback precedent; effort-downgrade xhigh→high noted for retro)
codex_verdict: cap=3 reached (R0 2×P2 → R1 2×P1 → R2 1×P1, all CHANGES_REQUIRED) — every finding fixed+pinned; R2 (3rd round) fixed at cap without an independent R3 re-review (consult tool errored; W3.0.1 precedent + overflow record). R2 implicitly validated the substantial R1 Contract-A refactor (reviewed, not re-flagged); only the 5-LOC R2 dedup is un-re-reviewed (low-risk honest residual)
codex_tool_report_path: reports/codex_tool_reports/v61_220_chain_report.md
overflow_record: .planning/retrospectives/codex_round3_overflow_w302.md
notion_sync_status: synced 2026-05-31 (https://www.notion.so/371c68942bed81689883f294598e7932)
touches_shared_dec: V61-213 (thermo_dict_extractor leaf-scanners hardened with depth-0 stripping — fixes a latent nested-leak fabrication shared by the single-region path)
---

# DEC-V61-220 · thermo_dict multi-region variant for CHT topology (P3 W3.0.2)

## Context

DEC-V61-217 W3.0.2 — the region-aware `thermophysicalProperties` reader, third
P3 item, consuming W3.0's `RegionPropertiesSnapshot` (DEC-V61-218). Surface scan
(V61-088): single-region `thermo_dict_extractor` (DEC-V61-213) reads
`constant/thermophysicalProperties` (one path); CHT stores per-region thermo at
`constant/<regionName>/thermophysicalProperties`. New extractor,
**parallel-new** disposition (mirrors W3.0.1's relation to `shm_dict_extractor`).

## Decision

Add `ui/backend/services/case_extractors/thermo_dict_multi_region.py`:
`extract(case_dir, region_snapshot) → Mapping[str, RegionThermoSnapshot | None] | None`,
keyed by every region in the snapshot (fluid + solid). Stdlib-only; reuses
`thermo_dict_extractor`'s parsing helpers. Re-exported as
`extract_thermo_dict_multi_region` (package SIX→SEVEN).

### Load-bearing design fork: fluid-only wrapper vs solid-thermo extension

The charter calls W3.0.2 a "region-iteration wrapper around DEC-V61-213
`thermo_dict_extractor`." But the single-region extractor is **fluid-shaped**:
its transport branch handles only `sutherland`/`const` (fluid viscosity), so a
CHT **solid** region (`heSolidThermo` + `constIso` transport carrying a single
isotropic `kappa`, `rhoConst` EOS) is scope-out → None. The charter's acceptance
explicitly requires "case_002b 7-region thermo (1 air + **6 Ti**) yielding
correct per-region thermo_type + property snapshots" — the 6 Ti solids and
case_011's Al-6061 are the *point* of multi-region thermo. **Resolution: extend
for solid thermo** (fork b). New solid helpers parse `constIso` kappa, `rhoConst`
rho, `hConst` Cp/Hf. A pure fluid-only wrapper would return None for every solid
and defeat the charter.

### RegionThermoSnapshot (frozen dataclass, local — DEC-V61-211 mirror pattern)

Each property field **independently optional** (DEC-V61-213 key-presence): `None`
= absent/scope-out, never fabricated. Fields: `thermo_type` (the `thermoType.type`
token), `tags` (reused `ThermoModelTags` 6-token descriptor), `kind`
(`'fluid'|'solid'|None`), `mol_weight`, `cp`, `hf`, fluid transport (`mu`, `pr`,
`sutherland_as`, `sutherland_ts`), solid transport/EOS (`kappa`, `rho`).

### Two load-bearing invariants

1. **No name-pattern inference** (charter-mandated): `kind` derives ONLY from
   which snapshot tuple the region is in — NEVER from the region name string
   (`air`/`aluminum`/`Ti`) or the `thermoType.type` token. The property-parse
   branch is driven by the FILE's `thermoType.type` token; `kind` is recorded
   independently so a snapshot/file mismatch is preserved as evidence, not masked.
2. **Honest refusal over silent collapse**: malformed / ambiguous / duplicate /
   directive / nested-only inputs → field None or region None, never fabricated.

## Build trail (workflow + adversarial pre-review + main-session fixes)

Implementation produced by the 3-phase workflow (`wf_22557e72-e82`): understand
(directive survey + solid-shape confirmation, `Explore`) → `backend-engineer`
implement → 2-lens `test-red-team`. The understand pass confirmed **zero
`#include`/`#calc`/`#codeStream` directives** in the 6 in-repo
`thermophysicalProperties` files (so a `#`-directive may be honest-refused) and
the `heSolidThermo`/`constIso`/`rhoConst` solid shape. The main session then
verified diffs and **fixed every red-team finding before Codex**:

- **P1 (fabrication · solid-kappa gating)**: `_extract_solid_transport_kappa`
  scraped any scalar `kappa` and gated the constAnIso scope-out ONLY on a vector-
  paren heuristic — so a solid declaring `transport constAnIso` (or `polynomial`)
  with a *scalar* `kappa` fabricated an isotropic constIso value the file never
  declared, **asymmetric** with the fluid branch's strict transport-kind refusal.
  **Fixed**: gate on the declared `tags.transport == "constIso"` (mirrors fluid).
  The existing constAnIso fixtures only used the VECTOR form (circular — the
  type-token-vs-scalar mismatch was untested); anti-circularity pins added.
- **P1×2 (fabrication · nesting-depth leak)**: the THREE reused single-region
  leaf-scanners (`_extract_thermo_model_tags`, `_extract_specie_block`,
  `_extract_transport_block`) scanned raw block bodies with NO depth-strip, so a
  token declared only inside a nested decoy sub-block leaked to the parent — most
  severely the load-bearing `thermoType.type` discriminator (`decoy { type
  heSolidThermo; }` → fabricated branch). **Single-region shared this latent
  bug.** **Fixed at root**: added `_strip_nested_blocks` to `thermo_dict_extractor.py`
  and applied depth-0 stripping in all four leaf-scanners (`_extract_thermo_model_tags`
  / `_extract_specie_block` / `_extract_transport_block` / `_extract_thermodynamics_block`)
  — hardens BOTH paths. Single-region regression pins added
  (`test_nested_thermotype_type_decoy_does_not_satisfy_discriminator`,
  `test_nested_molweight_decoy_does_not_fabricate`).
- **P2 (honest-refusal · directive-inside-block)**: a `#include` inside an
  otherwise-parseable block was silently skipped → a partial snapshot reported as
  complete (the documented contract promised region None). **Fixed**: `_DIRECTIVE_RE`
  refusal at the top of `_parse_region_thermo` (any `#`-directive anywhere →
  region None).
- **P2 (honest-refusal · nested molWeight)** + **P3 (docstring overclaim, partial-
  solid no-regression pin)**: closed by the root depth-strip fix + the directive
  fix; docstring item 3 now accurately scopes the depth-0 guarantee to BOTH
  new and reused scanners.

### Touches a shared DEC (V61-213) — explicit

The nesting-depth fix modifies `thermo_dict_extractor.py` (DEC-V61-213's file).
Blast radius is **tiny and strictly more honest**: the depth-0 strip changes
behavior ONLY for inputs with nested sub-blocks inside thermoType/specie/
transport/thermodynamics leaf blocks — which is **invalid OpenFOAM** (these
blocks never contain sub-dicts in real cases). All 34 single-region tests pass
unchanged; only adversarial/malformed nested input now refuses instead of
fabricating. Documented here per the cross-DEC-modification discipline.

## Open-question resolutions (resolved in main session)

1. **Solid thermo in scope?** — RESOLVED yes (fork b above): the charter's
   case_002b/case_011 acceptance requires real solid property snapshots.
2. **constAnIso (kappa vector)** — scope-out: `kappa` None, `thermo_type` still
   captured. Now gated on the declared token, not a payload-shape heuristic.
3. **`#`-directives** — honest region None (enforced), documented v0.1 limit.
4. **Snapshot/file kind mismatch** — `kind` from snapshot, branch from file;
   mismatch preserved as evidence (raw `tags` + `kind`), not masked. A future
   R13/R14 CHT rule (W3.1) can consume the divergence.

## Passes-criteria

1. `pytest -q tests/p3/test_thermo_dict_multi_region.py` + `..._redteam.py` +
   `..._redteam_nesting.py` → **all green** (113 p3 total).
2. case_002b-shaped 7-region (1 air fluid + 6 Ti solids) → 7 populated snapshots
   with correct thermo_type/kind/properties; case_011-shaped 3-region (2 air
   streams + 1 Al-6061) → 3 populated, distinct air templates (no name inference).
3. Solid kappa gated on declared `constIso`; constAnIso/polynomial → kappa None.
4. Nested-only token (incl. `thermoType.type`) → field None / region None (both
   single- and multi-region paths).
5. `#`-directive anywhere → region None.
6. Single-region `thermo_dict_extractor` tests: **34 passed, 6 skipped** — no
   regression from the shared depth-strip. Case-extractor surface: **304 passed,
   38 skipped**. Stdlib-only.
7. Codex APPROVE — **gate pending R0**.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept).
- Kogami opt-in: false (sub-DEC class; reversible).
- Codex round cap = 3; pre-merge mandatory (new OF-dict parser + shared-DEC change).
- Four-question gate (V130): LLM offline ✓ · artifacts canonical ✓ (reads
  on-disk per-region thermophysicalProperties) · TrustGate-explainable ✓ (honest
  `None` for any region/field without on-disk evidence; never fabricates) ·
  advisory-only ✓.
- Surface-scan-found: `ui/backend/services/case_extractors/thermo_dict_extractor.py`
  · disposition: extend (leaf-scanner depth-0 hardening); new extractor otherwise
  parallel-new.

## Ratification

**Codex chain R0→R1→R2 — cap=3 reached, all CHANGES_REQUIRED, every finding
fixed+pinned.** Chain report `reports/codex_tool_reports/v61_220_chain_report.md`;
overflow record `.planning/retrospectives/codex_round3_overflow_w302.md`.

- **R0** (86gs xhigh) 2×P2 — eConst/non-pureMixture region built a populated
  snapshot (single-region refuses; docstring promised None) · solid `rho`
  extracted regardless of declared EOS. **Fixed**: scope-out gate → region None;
  `_extract_rho_const` gated on `eos_kind=="rhoConst"`; +3 pins.
- **R1** (CRS high; 86gs stream-failed mid-review) 2×P1 — multi-region returned
  partial snapshots (required `Cp`/transport/`molWeight` None) where single-region
  returns None ("malformed file looks parsed"). **Fixed**: **Contract A** —
  required-field-absent → region None, symmetric with the wrapped single-region
  extractor (required = molWeight+Cp universal + complete fluid transport; solid
  kappa/rho optional, forced by the scope-out contracts); unknown-type → region
  None; builders return `| None`. 5 Contract-B pins updated to region-None.
- **R2** (CRS high) 1×P1 — a region name in BOTH `fluid_regions` and
  `solid_regions` collapsed the map key (fewer keys than declared). **cap=3
  reached** → per CLAUDE.md "remaining findings → overflow" + user "stop at R3".
  **Fixed**: `dict.fromkeys` order-preserving dedup; in-both → single None key;
  +1 pin. The AskUserQuestion consult to ratify the R3 decision errored ("Stream
  closed") twice (same failure as W3.0.1); given the R2 fix is a trivial 5-LOC
  dedup, R2 had already implicitly validated the substantial R1 refactor (reviewed
  it, did not re-flag), and the standing autonomous-mode grant, the main session
  applied the W3.0.1-precedent option (a): **R2 fix applied + verified WITHOUT an
  independent R3 round** (honest residual: only the 5-LOC dedup is un-re-reviewed;
  low risk, regression-pinned).

Status flipped Proposed → **Accepted** (`confidence: med` — honest, the chain did
not reach a clean APPROVE; R2 fixed at cap). Counter +1. Session-end Notion sync.

Tests: **153 passed, 6 skipped** (`tests/p3/test_thermo_dict_multi_region*.py` +
`tests/test_thermo_dict_extractor.py`) · **308 passed, 38 skipped** (full
case-extractor surface — no regression). Stdlib-only.

**Calibration notes (RETRO-V61-001 intake)**:
1. **Wrapper refusal-bar parity** was the gap behind the R1 P1: when a new
   extractor wraps an existing one, the wrapper's refusal bar must match the
   wrapped extractor's required-field bar. Carry-forward: enumerate required-vs-
   optional fields UP FRONT and pin a region-None test per required field.
2. **Map-key uniqueness under union iteration** (R2 P1): any name-keyed map drawn
   from ≥2 source lists must `dict.fromkeys`-dedup and pin the in-both case.
3. The pre-Codex **2-lens red-team** caught the heaviest defects (P1×3 incl. the
   load-bearing `thermoType.type` nesting-leak that also affected single-region,
   hardened at root) — consistent with W3.0.1: the adversarial workflow pass is
   the highest-value pre-review move for these parsers.
4. **86gs upstream instability persists** (R1 stream-fail after W3.0.1's 502×2);
   the CRS effort-downgrade (xhigh→high) is acceptable here (red-team did the deep
   pass) but logged — consider CRS-primary for governance if it continues.
