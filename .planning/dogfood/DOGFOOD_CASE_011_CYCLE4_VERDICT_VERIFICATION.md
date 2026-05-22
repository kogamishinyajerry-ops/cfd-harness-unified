# Dogfood: case_011 · cycle-4 verdict-layer wiring verification · 2026-05-22

## What ran

- Command: `cfdtrust ingest <case>` then `cfdtrust report <case>` (via venv shim)
- HEAD: `f6e9a45` (Codex R0→R1 closed on cycle-4 spike B multi-region verdict)
- Wall clock: 2026-05-22T10:43:30Z → 10:47:40Z (~250s; checkMesh in Docker dominates)
- Exit codes: ingest=0, report=1 (overall_status=FAIL → CLI returns non-zero, expected)
- Case dir: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case`

## What changed vs cycle-2 baseline

| Aspect | Cycle-2 baseline | Cycle-4 actual |
|---|---|---|
| bc_contract gate status | BLOCKED | **BLOCKED** (still) |
| reason | `multi_region_bc_validation_not_yet_wired` | `multi_region_empty_region_detected` |
| `fluid_region_count` | (absent) | 0 |
| `solid_region_count` | (absent) | 0 |
| `empty_region_count` | (absent) | 3 |
| `expected_fluid_fields` | (absent) | `["U", "p"]` |
| `missing_in_all_fluid_regions` | (absent) | `["U", "p"]` |
| `fluid_regions` / `solid_regions` | (absent) | both `[]` |
| `per_region_field_summary` | present (cycle-1 layer) | present, but each region `fields_present: []` |
| trust_report `overall_status` | unchanged from cycle-2 (FAIL via solver gate) | FAIL (residual_targets_not_met, same chain) |
| `solver_execution` | `ingested` | `ingested` |
| `validation_status` | `not_validated` | `not_validated` |
| `bc_parsing_status` (bc_quality.json) | `ok` | `ok` |
| `layout` | `multi_region` | `multi_region` |

Verdict-layer schema **did** wire (all 7 new detail fields emitted exactly as designed in spike B). What didn't land cleanly is the verdict **value** for this case.

## Verdict explanation

Expected verdict (per case_011 manifest + on-disk evidence):

- Manifest declares `turbulence_fields: [__none_laminar__]` (sentinel) → `expected_fluid_fields` rightfully derives to `["U", "p"]` only. ✓ matches bc_quality.json.
- On-disk: `0/region_hot_fluid/` and `0/region_cold_fluid/` each contain `U`, `p`, `p_rgh`, `T`; `0/region_solid/` contains `T`, `p` (no U, correct for solid). All 3 regions are populated.
- Expected outcome: **WARN with `multi_region_per_class_pending`** — every fluid region carries U+p, both manifest-declared fluid fields present in ≥1 fluid region, ceiling-WARN until Gap #28 per-class schema lands.

Actual outcome: **BLOCKED with `multi_region_empty_region_detected`**. Root cause is upstream — `_parse_field_boundary_field` in `backends/openfoam.py` walks the boundaryField block but returns 0 patches, so `bc_quality.regions[*].fields_present` is empty for every region. The verdict layer faithfully concludes "all 3 regions empty → BLOCKED". The verdict layer behaves as designed; the BC-file parser behind it does not.

## Honesty fence status

- `solver_execution`: `ingested` (✓ same as cycle-2, no claim of real run)
- `overall_status`: `FAIL` (driven by solver gate `residual_targets_not_met`, **not** by BC verdict — BC BLOCKED would propagate too, but solver_execution FAIL is the dominant signal)
- `validation_status`: `not_validated` (✓ honesty cap held)
- `bc_parsing_status`: `ok` (parser claims success despite every region returning empty patches — this is a separate honesty concern, see Gap #44 below)
- `layout`: `multi_region` (✓ preserved)

No honesty-fence regression. The trust_report does NOT falsely claim BC validation success; it BLOCKS the BC gate, just on a wrong reason.

## Net-new findings

### Gap #44 (NEW · regression of an old shape) — Multi-region BC parser silently drops regex-named patches

**Symptom**: Every per-region `fields_present` is `[]` even though `0/region_*/U` and `0/region_*/p` exist on disk with well-formed `boundaryField { ... }` blocks. Confirmed by running `_parse_field_boundary_field` directly on `0/region_hot_fluid/U` → regex `_BOUNDARY_FIELD_OPEN_RE` matches the block opener, but the per-patch walker returns 0 entries.

**Root cause**: The first patch line in case_011 fluid-region U/p files is `"region_<name>_to_.*"  { type fixedValue; ... }` — a **quoted-regex single-patch name** (one block, one patch, regex-quoted), NOT the canonical OpenFOAM grouped form `"(name1|name2|...)"`. Parser line 1421 (`if inner[j] in ('"', '('):`) routes to `_GROUPED_PATCH_HEADER_RE = r'"?\(\s*([^)]+?)\s*\)"?'` which **requires literal `(...)` parens inside the quotes**. The quoted-regex single-name form has no parens, regex fails, fallback path is "silent break on unparseable" (line 1426 comment), so the walker exits at the very first patch and all subsequent patches in the same file are dropped.

**Why cycle-2 didn't surface this**: cycle-2's BC verdict was the unconditional pessimistic `multi_region_bc_validation_not_yet_wired` BLOCKED — verdict didn't depend on `fields_present`, so the empty arrays were not load-bearing. Spike B's verdict layer **does** depend on `fields_present`, exposing the upstream parser gap that was previously masked.

**Suggested fix scope** (out of scope for this dogfood):

1. Extend `_GROUPED_PATCH_HEADER_RE` (or add a sibling regex) to also accept `"<single-name-or-regex>"` — quoted-string single-patch form. Map to a single synthetic patch entry with the literal regex string as the name.
2. Per-region multi-region cases are particularly prone to this — `region_<name>_to_<other>` mappedWall patches are typically grouped via quoted regex, not plain identifiers. Adding a fixture under `tests/data/multi_region/case_with_quoted_regex_patch/` would catch any future regressions.
3. Optional: when the walker silently breaks, emit `parse_error: "patch_walker_silent_break_at_byte_<N>"` instead of falling back to the file-level `no_boundary_field_block_found`. Right now bc_quality.json says `parse_error: "no_boundary_field_block_found"` which is misleading — the block WAS found, the walker just couldn't iterate it.

**Honesty observation**: `bc_quality.bc_parsing_status: "ok"` is itself misleading when every region has 0 patches parsed but the parser thinks the regions exist. A future polish would gate `bc_parsing_status` to require ≥1 parsed patch in ≥1 fluid region before declaring `ok` for multi-region layouts.

## Artifacts pointer

- Captures: `/Users/Zhuanz/Desktop/cfd-audit-merge/.demo/captures/2026-05-22T1900Z/stage_cycle4_case_011_redogfood.txt`
- `bc_audit.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/bc_audit.json`
- `bc_quality.json` (upstream — where the rot starts): `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/bc_quality.json`
- `trust_report.json`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/trust_report.json`
- `residuals.csv`: `/Users/Zhuanz/Desktop/cfd-harness-unified/_sandboxes/case_011_plate_fin_compact_hx/case/artifacts/residuals.csv` (201 rows; solver evidence intact)

## Verdict

⚠ **Deviation found.** Spike B verdict-layer **schema** verified clean — all 7 new detail fields (`fluid_region_count`, `solid_region_count`, `empty_region_count`, `fluid_regions`, `solid_regions`, `expected_fluid_fields`, `missing_in_all_fluid_regions`) emit exactly as designed, and the verdict computation correctly maps "all regions empty" → BLOCKED `multi_region_empty_region_detected`.

But the **expected verdict path was `WARN multi_region_per_class_pending`**, not BLOCKED, because case_011's regions are NOT empty on disk. The deviation is upstream: BC-file parser (`backends/openfoam.py:_parse_field_boundary_field`) silently drops every patch in fluid-region U/p files when the first patch carries a quoted-regex single name (e.g. `"region_hot_fluid_to_.*"`). Spike B's verdict layer is doing exactly what it should given empty `fields_present`; the parser gap that feeds it is Gap #44.

Net-new findings: 1 (Gap #44 · multi-region BC parser quoted-regex-single-name silent drop).

---

## Cycle-4b: post-Gap #44 fix · 2026-05-22

**HEAD**: `915410f` (Gap #44 quoted-regex single-name patch parser fix)

The cycle-4 deviation surfaced above (every region's `fields_present` empty → BLOCKED `multi_region_empty_region_detected`) was traced to `_parse_field_boundary_field` silently dropping every patch when the first patch line carries the quoted-regex single-name form (`"region_hot_fluid_to_.*"`). Gap #44 fix extended the walker to accept this form alongside the Gap #23 grouped form. Three regression tests landed; full audit suite 454 → 457 passed.

### Cycle-4 → cycle-4b verdict transition

| Field | Cycle-4 deviation | Cycle-4b post-fix |
|---|---|---|
| `bc_audit.gate_status` | **BLOCKED** | **WARN** ✓ |
| `bc_audit.reason` | `multi_region_empty_region_detected` | `multi_region_per_class_pending` ✓ |
| `bc_audit.fluid_region_count` | 0 | **2** (region_cold_fluid, region_hot_fluid) ✓ |
| `bc_audit.solid_region_count` | 0 | **1** (region_solid) ✓ |
| `bc_audit.empty_region_count` | 3 | **0** ✓ |
| `bc_audit.expected_fluid_fields` | `[U, p]` | `[U, p]` (same; sentinel correctly stripped) |
| `bc_audit.missing_in_all_fluid_regions` | `[U, p]` | `[]` ✓ |
| `bc_quality.regions[cold_fluid].fields_present` | `[]` | `[U, p]` ✓ |
| `bc_quality.regions[hot_fluid].fields_present` | `[]` | `[U, p]` ✓ |
| `bc_quality.regions[solid].fields_present` | `[]` | `[p]` (solid honestly has only p, no U — per-class verdict still deferred to Gap #28 so this is "advisory missing", not failure) |

### Honesty fence status (post-fix)

- `bc_parsing_status`: `ok` (now correctly reflecting parsed evidence, not the pre-fix lie)
- `bc_contract.status`: `WARN` (the cycle-4 ceiling — PASS unreachable until Gap #28 per-class schema lands)
- `solver_execution`: `ingested` (unchanged)
- `validation_status`: `not_validated` (honesty cap held)
- `layout`: `multi_region` (unchanged)
- `overall_status`: still driven by solver gate FAIL (residual_targets_not_met), but the BC chain no longer contributes a spurious BLOCKED

### Verdict

✓ **Cycle-4 deviation closed.** Gap #44 fix landed and case_011's bc_contract gate now produces the verdict the cycle-4 spike B was designed to emit: `WARN multi_region_per_class_pending` with full 7-field verdict-layer detail (fluid_region_count=2, solid_region_count=1, empty_region_count=0, both fluid regions enumerated, expected_fluid_fields=[U, p], missing_in_all_fluid_regions=[]).

### The load-bearing trust beat

Spike B (multi-region verdict-layer wiring) shipped → its dependence on `fields_present` exposed a latent BC parser bug (quoted-regex single-name silently dropping all patches) → same arc → Gap #44 fix → re-dogfood verifies clean transition `BLOCKED empty → WARN per_class_pending`. **This is the cycle-4 equivalent of cycle-2's Gap #32 sentinel-leak self-discovery and cycle-1's TBD-17 honesty-fence self-snitch. The engine refused to lie: cycle-2's pessimistic BLOCKED masked the parser bug, cycle-4's wiring exposed it, cycle-4b's same-arc fix closes it.**

Captures: `.demo/captures/2026-05-22T1930Z/stage_cycle4b_case_011_post_gap44_redogfood.txt`
