---
decision_id: DEC-V61-201-SUB-INGEST-BC-REGEX-GROUPED-PATCHES
title: bc_audit parser handles regex-grouped patch blocks (canonical OpenFOAM "(patch1|patch2)" syntax)
status: Accepted
accepted_date: 2026-05-22
parent_dec: DEC-V61-201-SUB-INGEST
phase: post-merge follow-up (M2.6)
notion_sync_status: synced 2026-05-22 (https://www.notion.so/367c68942bed81499746d241512268b8)
---

## Why

case_006 (ONERA M6 transonic) dogfood surfaced this as a **production
blocker for compressible aero**: the M2.6-cycle-1 bc_audit parser
(`_parse_field_boundary_field` in `cfdtrust/backends/openfoam.py`)
silently drops every `0/<field>` patch declared with the canonical
OpenFOAM regex-grouped syntax:

```
boundaryField
{
    "(wing|farfield|symmetry)"
    {
        type            fixedValue;
        value           uniform 0;
    }
}
```

The grouped syntax is a one-block-declares-many-patches shortcut, very
common in compressible-aero benchmark cases (ONERA M6, RAE 2822, NACA
0012 transonic, ...). case_006's `0/p`, `0/k`, `0/omega` are all
authored this way; the result is `bc_quality.json` reports zero parsed
patches for those fields → audit gate produces a false-negative
"missing BC declarations" signal even though the case is fully BC-
specified.

Witness count: **1 of N**. Every V-series compressible-aero case in the
corpus (V20-V51+ transonic-aero subset) uses this pattern. case_006
just happens to be the first that ran through the new M2.6 ingest
path; the others would all degrade identically the moment they're
ingested. Closing the blocker for case_006 closes the systemic regression.

## What

Extend `_parse_field_boundary_field` to recognize a second patch-entry
syntax inside the `boundaryField { ... }` walker:

```
"(name1|name2|...)" { ...BC block... }
```

When the walker encounters this syntax, expand it into N synthetic
per-patch entries — each named `name1`, `name2`, ... — all carrying
**the same parsed BC block** (type, value_scalar/vector, params).
Downstream consumers (`_persist_bc_quality`, `_collect_and_persist_bc`,
the audit gate) see exactly what they would have seen had the case
author written N separate single-patch blocks.

Backwards-compatibility: the existing single-name path
(`patch_name { ... }`) is unchanged. The new branch only fires when
the parser sees `"` or `(` at the patch-name position.

## How

Two minimal additions to `_parse_field_boundary_field`:

1. **Module-level regex** — match the grouped patch header line:
   `^\s*"?\(\s*([^)]+?)\s*\)"?\s*$` with capture group = the inner
   pipe-separated name list (e.g. `wing|farfield|symmetry`).
2. **Walker branch** — at the patch-name position, peek for `"` or `(`;
   if seen, consume the grouped header (up through the matching `)`,
   skipping any trailing optional `"`), split the capture on `|`,
   strip whitespace, drop empty fragments (graceful handling for
   `"(wing|)"`); then proceed into the standard `{ ... }` block read.
   For each split name, write the SAME parsed `patch_entry` dict into
   `patches[name]`.

LOC: ~30-50 net added (one regex + one walker branch + a short
post-block fan-out loop). Single file edit (`backends/openfoam.py`).
No schema change — synthetic per-patch entries match the existing
`bc_quality.json` shape exactly.

## Scope class

Sub-DEC (parent: DEC-V61-201-SUB-INGEST). Single subsystem
(cfdtrust audit ingest); single file edit + test additions;
~30-50 LOC. NOT charter — does not cross ≥3 shared code paths and
does not touch a governance rule. Per v2.3 sub-DEC scope, no Codex
relay round required (parser-additive change, falls back to existing
regex on non-match, no security or signing surface touched). Honesty
fences and `bc_quality.json` schema unchanged.

## Acceptance criteria

1. `_parse_field_boundary_field` returns N entries (one per name in the
   alternation list) when fed a `"(name1|name2|...)" { type X; }`
   block. Each entry carries the same parsed `type` / `value_*` /
   `params` shape as the single-patch path.
2. Mixed files containing both single-patch and grouped declarations
   parse both kinds correctly; ordering is irrelevant.
3. Malformed alternation (empty fragment, e.g. `"(wing|)"`) parses the
   valid names and silently drops the empties — no exception raised,
   no entry produced for the empty fragment.
4. `pytest -q ui/backend/audit/cfdtrust_tests/` all green (no
   regressions in the existing 200+ tests).

## Risks

LOW. The change is **additive** at the parser walker:

- If the new branch's peek fails (no `"` and no `(` at name pos),
  the walker falls through to the existing alphanumeric name read —
  exact pre-V201-SUB-GROUPED behavior preserved.
- If the new branch matches but the alternation list is empty post-
  strip, no patches are written from that block, but the walker
  continues forward (matching the existing posture for malformed
  blocks: silent skip, no exception).
- No persistence path changes; `bc_quality.json` shape is identical.
- No effect on the polyMesh/boundary parser (different code path).

Blast radius: bc_audit gate behavior for cases using grouped syntax
(today: parses 0 patches; after: parses all N). For cases using only
single-patch syntax (today: works; after: still works identically).

## Implementation note

Commit SHA: `<filled-on-commit>`
