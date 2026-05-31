---
decision_id: V61-218
title: regionProperties reader (case dir → RegionPropertiesSnapshot) — P3 W3.0 sub-DEC
status: Accepted
parent_dec: V61-217
phase: P3 (Blueprint v4 · CHT)
autonomous_governance: true
confidence: high
kogami_opt_in: false
round_cap: 3
codex_review_relay: 86gs gpt-5.4 xhigh
codex_verdict: APPROVE (R2 clean · chain R0→R1→R2)
codex_tool_report_path: reports/codex_tool_reports/v61_218_chain_report.md
notion_sync_status: synced 2026-05-31 (https://www.notion.so/371c68942bed812da2ccd4b0a30414c8)
---

# DEC-V61-218 · regionProperties reader for CHT multi-region topology (P3 W3.0)

## Context

DEC-V61-217 (P3 CHT charter) sequences nine sub-DEC workstreams. **W3.0 is the
first executable item and the PIVOT** — `constant/regionProperties` is the
bootstrap dict telling `chtMultiRegionSimpleFoam` which sub-regions exist and
which are fluid vs solid. Its output is the iteration source feeding W3.0.1
(`shm_dict` multi-region variant), W3.0.2 (`thermo_dict` multi-region variant),
and W3.0.6 (multi-region `RunArtifactSlice` extension). No region-aware P3 work
can start until this extractor exists.

Pre-implementation surface scan (V61-088): `grep -rin regionProperties
ui/backend/services/ src/` returned **zero** production references — no extractor
reads `regionProperties` today. `case_extractors/` ships four P2 siblings
(solver_block / shm_dict / thermo_dict / step). `regionProperties` is the new
fifth extractor with **no P2 analogue** (the charter's "new-extractor-needed"
disposition). Disposition: **parallel new** (additive to the package).

## Decision

Add `ui/backend/services/case_extractors/region_properties_reader.py`:
`extract(case_dir) → RegionPropertiesSnapshot | None`, a stdlib-only,
structurally-parsed reader of `<case_dir>/constant/regionProperties` producing

    RegionPropertiesSnapshot(
        fluid_regions: tuple[str, ...] | None,   # None iff group key absent
        solid_regions: tuple[str, ...] | None,   # None iff group key absent
    )

following DEC-V61-211 **local-mirror dataclass** (stdlib-only, no `trimesh`
contagion) + DEC-V61-213 **key-presence-vs-payload-completeness separation**
(each field independently optional). Re-exported from the package `__init__.py`
as `extract_region_properties_snapshot`.

### Scope (v0.1 · this DEC)

- **In**: parse the `regions ( ... )` entry; surface `fluid` and `solid` group
  region-name tuples. Accept both the canonical single-paren OpenFOAM form
  `regions (fluid (a b) solid (c))` and the double-paren charter form
  `regions ((fluid (a b)) (solid (c)))`. Key-presence semantics: group absent →
  `None`; group present but empty → `()`; group present populated → `tuple`.
- **Honest-refusal (return `None`) on**: missing/unreadable file; no parseable
  `regions` entry; duplicate `regions` key; duplicate `fluid`/`solid` group;
  a name-list containing a nested group; any out-of-grammar token (digit-led
  name, stray paren, `$macro`).
- **Out (deferred / scope-locked, documented in module docstring)**: `#include`
  resolution; macro substitution; string-literal-aware comment stripping;
  three-level nesting; group keys other than `fluid`/`solid` (e.g. `porous`) are
  parsed but ignored (surfaced on neither field).

### Scope-locking rationale

A general OpenFOAM-dict parser is multi-hour infrastructure. v0.1 is a
top-level structural parser (`_parse_top_level_items` → words + balanced-paren
groups) over a comment-stripped buffer — bounded, correct for the in-repo case
shapes, and **honest** (refuses rather than guesses on anything outside the
two-level `(groupWord (name ...))` schema).

## Why region_properties first (and the PIVOT framing)

Per charter §"P2 extractor multi-region disposition": `solver_block`
cleanly-extends, `shm_dict`/`thermo_dict` need region-aware variants — and ALL
of them need the region list `regionProperties` declares. The CHT topology fans
out from this one dict. Building it first unblocks W3.0.1/W3.0.2/W3.0.6 and lets
each be tested independently of `trimesh`/`geometry_ingest`.

## Architectural placement

Mirrors DEC-V61-211 exactly: stdlib-only (`pathlib` + `re` + `dataclasses`),
pure function, read-only (one `Path.read_text`), no route, no mutation, no
import from `geometry_ingest`. `RegionPropertiesSnapshot` is a NEW dataclass
(no upstream equivalent → no mirror-parity canary needed today). Tests live in
top-level `tests/p3/` (NOT `ui/backend/tests/`) so they run without the
`trimesh`-importing `conftest.py` — same trimesh-free placement as the P2
sibling tests in `tests/`.

## Passes-criteria (charter W3.0 row)

1. `pytest -q tests/p3/test_region_properties_reader.py` → **30 passed**.
2. case_002b-shaped fixture (7 regions: 1 fluid + 6 Ti solids) yields correct
   `fluid_regions` / `solid_regions` tuples (`region_bay_air` + 6 Ti names).
3. case_011-shaped fixture (3 regions: 2 fluid air streams + 1 Al-6061 solid)
   yields `("region_hot_fluid","region_cold_fluid")` + `("region_solid",)`.
4. missing-key (group absent → `None`) AND present-but-empty (`fluid ()` → `()`)
   regression cases both green (DEC-V61-213 separation).
5. `test_extractor_module_loads_without_trimesh` subprocess pin passes.
6. Sibling tests (solver_block / thermo_dict / shm_dict): **141 passed,
   12 skipped** — no regression.
7. Codex APPROVE (86gs xhigh primary, CRS fallback) — **gate pending R0**.

## Build trail (workflow + adversarial pre-review)

Implementation was produced by a deterministic 3-phase workflow
(`wf_848ed684-5c3`): understand (3 parallel readers nailing sibling pattern /
OpenFOAM `regionProperties` grammar / fixtures+test convention) → implement
(`backend-engineer` wrote the extractor + 24 tests, pytest green) → adversarial
review (2 `test-red-team` lenses). The main session then verified diffs and
**fixed the red-team findings before this DEC** (governance kept in main session;
Codex run by main session, not delegated):

- **P1 (parser-correctness · must-fix)**: the implementer's `_extract_group`
  used a global `\bfluid\s*\(` regex over the whole `regions` body with **no
  depth anchoring** — a `fluid`/`solid` token nested inside another group's
  name-list false-matched and fabricated tuples (e.g.
  `regions ( solid ( metal fluid (deep) ) )` → `fluid_regions=('deep',)`).
  **Fixed**: rewrote as a top-level structural parser
  (`_parse_top_level_items` + `_parse_names` + `_extract_group_pairs`); group
  detection is now top-level-anchored, nested shapes trigger honest refusal.
  3 regression tests added (`test_nested_fluid_inside_solid_does_not_fabricate`,
  `test_region_name_with_paren_suffix_does_not_conjure_group`,
  `test_three_level_nested_name_list_refuses`) — each FAILS on the old code.
- **P2 (silent name corruption)**: `re.findall(r"[A-Za-z_]\w*", sub_body)`
  truncated `123air` → `air`, fabricating a name. **Fixed**: strict whole-token
  tokenizer refuses out-of-grammar tokens; `test_digit_prefixed_name_is_not_
  silently_corrupted` now asserts honest refusal (was xfail).
- **P2 (dishonest docstring)**: the scope-out described the failure as a
  quoted-string edge case while the real wrong-output was in-block depth
  confusion. **Fixed**: rewrote the `## Scope-locked NON-features` section to
  honestly describe top-level anchoring + refusal semantics.
- **P3 (dead code)**: removed unused `_GROUP_TOKEN_RE` / `_ABSENT` sentinel.

## Governance (DEC-level meta)

- `autonomous_governance: true` (counter +1 on Accept per RETRO-V61-001).
- Kogami opt-in: **false** (per user 直接开干; reversible). Not a charter /
  governance-rule-change / ≥3-shared-path change — sub-DEC class.
- Codex round cap = 3 per v2.3; this is the W3.0 implementation DEC, Codex
  pre-merge mandatory per charter passes-criterion #7 (new OpenFOAM dict parser).
- Four-question gate (V130): LLM offline ✓ (pure parser, zero LLM) · artifacts
  canonical ✓ (reads on-disk `regionProperties`) · TrustGate-explainable ✓
  (honest None on every ambiguity, never fabricates) · AI advisory-only ✓
  (read-only extractor, no writes).
- Surface-scan (V61-088): clean — zero pre-existing `regionProperties`
  production reference; new-extractor disposition.

## Ratification

**Codex chain R0→R1→R2 = APPROVE** (86gs gpt-5.4 xhigh; chain report
`reports/codex_tool_reports/v61_218_chain_report.md`):

- **R0** CHANGES_REQUIRED · 2× P2: (1) trailing tokens after `regions (...)`
  list silently truncated → partial snapshot; (2) `regions (` inside a quoted
  metadata string false-counted as a duplicate key. **Fixed**: `_TRAILING_OK_RE`
  trailing-content check + `_index_in_string` string-aware token scan; +2 tests.
- **R1** CHANGES_REQUIRED · 1× P2: stray `;` INSIDE the `regions` body skipped
  as whitespace → malformed source accepted. **Fixed**: removed `;` from the
  tokenizer skip set so an in-body `;` refuses; +3 parametrized tests.
- **R2** APPROVE clean — "did not identify a discrete bug; refusal behavior
  consistent with documented scope; no regression."

All three findings were **P2 honest-refusal edge cases** (no P1, no logic bug).
Tests: **35 passed** (W3.0 suite) · **141 passed, 12 skipped** (sibling
extractors — no regression). Status flipped Proposed → **Accepted**; counter
+1 (`autonomous_governance: true`); session-end Notion sync (Accepted-only).

**Calibration note (RETRO-V61-001 intake)**: predicted `confidence: high`;
chain ran the full cap=3 — but every round was a malformed-input honest-refusal
edge case, not a logic defect. New calibration anchor: **structured-parser
honest-refusal work has a ~3-round floor** unless ALL malformed-input classes
(trailing tokens · in-string tokens · embedded statement terminators · nested
name-lists) are enumerated BEFORE first review (echoes P2-close lesson
"enumerate-ALL-forms-before-writing"). The 2-lens `test-red-team` workflow pass
caught the depth-confusion P1 *before* Codex; the residual P2 honest-refusal
gaps are what Codex's blind-spot review adds on top.
