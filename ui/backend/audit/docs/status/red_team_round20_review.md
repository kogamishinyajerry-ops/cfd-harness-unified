# Red Team Round-20 Review — M5 Meta Scan (Real Geometry Contract)

**Scope:** M5 milestone replaced the Phase-0 MOCKED `geometry_contract` gate with a real
evidence-driven gate. Backend (`backends/openfoam.py`) now parses
`constant/polyMesh/boundary` after blockMesh succeeds and persists
`artifacts/geometry_quality.json` as the single source of truth. Audit
(`audit/geometry.py`) reads that file and evaluates two dimensions:
patch presence (manifest's `required_patches` vs realized polyMesh) and
dimensionality (manifest's `2.5D`/`2D`/`3D` vs presence of `empty` patches).

**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round19_review.md` (M4: 0 fixes in batch, 4 LOW info documented; first zero-MED milestone since M2.3).
**Verdict:** **PASS — 0/0/0/3 at probe time, 0 in-batch fixes, 3 LOW DOCUMENTED-NOT-FIXED**. M5 added a new real trust gate but followed the M4 pattern wholesale (persist → read → dimension-evaluate → INCOMPLETE-not-PASS); R-19's prediction (pattern reuse → MED ceiling 0) held.

---

## Method

12 probes against the new geometry-gate surface.

| #  | Probe                                                                              | Outcome    |
|----|------------------------------------------------------------------------------------|------------|
| 1  | `geometry_quality.json` absent + openfoam backend → silent PASS?                   | clean (BLOCKED with `geometry_quality_json_missing`) |
| 2  | persistence `status: blocked` (boundary file missing/unreadable) → propagates       | clean (test_geometry_gate_blocked_when_persistence_was_blocked) |
| 3  | Required patch missing in realized polyMesh → FAIL                                  | clean (test_geometry_gate_presence_fail_when_required_patch_missing) |
| 4  | Realized patch NOT in manifest (extras) → FAIL?                                     | clean — extras are informational only (manifest contract is one-way minimum) |
| 5  | `dimensionality: 2.5D` but no `empty` patch in polyMesh → FAIL                      | clean (test_geometry_gate_dimensionality_25d_fail_without_empty_patch) |
| 6  | `dimensionality: 3D` but realized has `empty` patches → FAIL                        | clean (test_geometry_gate_dimensionality_3d_fail_with_empty_patch) |
| 7  | Unknown dimensionality string (typo, e.g. `2D5`) → INCOMPLETE → FAIL                | clean (test_geometry_gate_dimensionality_incomplete_on_unknown_string) |
| 8  | polyMesh patch block without `type` field — parser must skip, not crash             | clean (test_parse_polymesh_boundary_skips_untyped_block) |
| 9  | polyMesh with truncated/unbalanced braces — parser must not loop / claim partial    | clean (test_parse_polymesh_boundary_unbalanced_braces_safe) |
| 10 | `// type fake;` hidden inside a comment fools parser?                               | clean — `_strip_foam_comments` removes // and /* */ before parsing |
| 11 | `inGroups List<word> 1(wall);` line confuses type/nFaces extraction?                | clean (test_parse_polymesh_boundary_handles_inGroups) |
| 12 | mocked backend + real M5 gate → silent PASS via MOCKED path?                        | clean (test_geometry_gate_mocked_backend_returns_mocked) |
| 13 | manifest `required_patches: []` (empty list) → FAIL?                                | clean (test_geometry_gate_fails_on_empty_required_patches) |
| 14 | `geometry_quality.json` is tamperable on disk (user edits FAIL → ok)                | R20-F-01 (LOW info, deferred — same family as R-38, R-32) |
| 15 | `dimensionality` field is `additionalProperties: true` in schema; only 3 keys gated | R20-F-02 (LOW info, deferred — same family as R-39) |
| 16 | Parser strips `/* */` greedy across patch blocks if a `*/` accidentally appears mid-block | R20-F-03 (LOW info, deferred — extremely unlikely in OpenFOAM output; pattern is `.*?` non-greedy with DOTALL) |

---

## Findings

### R20-F-01 — LOW (info, deferred) — `geometry_quality.json` is a tamper surface

**File:** `src/cfdtrust/backends/openfoam.py:_persist_geometry_quality` + `src/cfdtrust/audit/geometry.py:_read_geometry_quality`.

A user could open `artifacts/geometry_quality.json` and add fake patch entries (e.g. inject a `stepFace` to satisfy a manifest that lists it). The audit trusts what it reads.

**Threat model:** SAME class as R-38 (mesh_quality.json) and R-32 (solver_gate.json). Internal case-dir artifacts are trusted-by-convention. The audit gate could re-parse polyMesh/boundary directly as a cheap defense, but that breaks the M4 single-source-of-truth pattern (and the polyMesh file is itself a tamper surface — defense-in-depth at this layer is not the right place).

**Decision:** DEFER. Document in RISK_REGISTER as R-41.

### R20-F-02 — LOW (info, deferred) — `geometry_contract.dimensionality` enum not constrained by schema

**File:** `src/cfdtrust/schemas/case_manifest.schema.json` + `src/cfdtrust/audit/geometry.py:_eval_dimensionality`.

The gate recognizes three values (`2D`, `2.5D`, `3D`) and surfaces INCOMPLETE for anything else. The schema currently allows any string in `geometry_contract.dimensionality`. A typo (`2.5d` lowercase, `2-5D`) would silently INCOMPLETE → FAIL rather than schema-reject at manifest load.

**Why not fix:** the audit gate's FAIL message clearly states "unrecognized dimensionality; recognized values are '2D', '2.5D', '3D'" — the user has enough information to correct the typo. A schema-level enum would catch this 1 step earlier but adds maintenance overhead (we'd need to update the schema every time we recognize a new dimensionality keyword like `axisymmetric`).

**Decision:** DEFER. Document in RISK_REGISTER as R-42. Re-evaluate if a user reports confusion.

### R20-F-03 — LOW (info, deferred) — comment stripper could over-strip if `/* */` appears inside a string literal in polyMesh

**File:** `src/cfdtrust/backends/openfoam.py:_strip_foam_comments`.

The block-comment regex `r"/\*.*?\*/"` with `re.DOTALL` is non-greedy and would stop at the first `*/`. If OpenFOAM ever wrote a string field containing `/* ... */` literally (e.g. a future custom dictionary value), the stripper would corrupt it. polyMesh/boundary's grammar (type/nFaces/startFace + optional inGroups) does NOT include free-form strings, so this is hypothetical.

**Decision:** DEFER. Document in RISK_REGISTER as R-43. Only revisit if a parser regression is reported.

---

## Pattern confirmation

R-19's refinement: "a new trust gate that reuses verified persistence + reading + honesty contract has MED ceiling of 0."

R-20 confirms: M5 followed the M4 pattern exactly (backend persistence → audit read → dimension evaluate → INCOMPLETE-not-PASS). Result: 0 in-batch fixes, second consecutive zero-MED milestone. The methodology is now reproducible — when the next gate (e.g. M6 bc_contract) is built, the same playbook applies.

**Falsification test for future:** if a future milestone introduces a NEW contract surface (not just "persist + read"), the prediction is 1-2 MED. If M6 stays within the same pattern (parse `0/` directory → persist `bc_quality.json` → audit reads and matches against manifest) then MED ceiling stays at 0. If M6 introduces a new contract type (e.g. "is the BC dimensionally consistent with the geometry?"), expect 1 MED.

---

## Live verification (mandatory per M2.3a doctrine)

Fresh flat_plate live run (single canonical run, since the gate logic is symmetric across cases):

```
/tmp/m5_flat/case          — flat plate Re_L=4e6, 6000 cells
  blockMesh OK → geometry_quality.json persisted (5 patches: inlet/outlet/wall/top/frontAndBack)
                → checkMesh OK → simpleFoam 159 iter converged
  geometry_contract gate: PASS
    summary: "presence PASS (5/5); dimensionality PASS."
    Realized: inlet(patch), outlet(patch), wall(wall), top(symmetryPlane), frontAndBack(empty)
    Manifest 2.5D + frontAndBack empty → dimensionality matches
```

Plus dry-run verification against the live BFS (`/tmp/m4_live/bfs`) without re-executing simpleFoam:

```
/tmp/m4_live/bfs           — BFS Re_H=37,400, 11600 cells
  geometry_contract gate: PASS
    summary: "presence PASS (6/6); dimensionality PASS."
    Realized: inlet, outlet, topWall, bottomWall, stepFace, frontAndBack
    Manifest 2.5D + frontAndBack empty → matches
```

Both cases now produce a real geometry validation result. Pre-M5, both reported MOCKED with no actual patch inspection. The harness is now 2-of-3 audit gates real (geometry + mesh); only `bc_contract` remains Phase-0 MOCKED (M6 target).

---

## Test coverage

26 new M5 tests:

- parser: BFS canonical (6 patches), flat-plate canonical (5 patches with symmetryPlane), empty input, no-opener, untyped-block-skip, comment stripping, inGroups tolerance, unbalanced braces, partial fields
- persistence: ok / blocked / empty-patches paths
- audit gate: mocked → MOCKED, missing JSON → BLOCKED, persistence-blocked → BLOCKED, all required present → PASS, missing required → FAIL, extras don't fail, 2.5D + empty → PASS, 2.5D no empty → FAIL, 3D + empty → FAIL, unknown dim → FAIL via INCOMPLETE, no dim → PASS, end-to-end PASS evidence chain, honesty fences

Suite: **252/252 pass + 1 opt-in network skip** (was 226 before M5 = +26 new geometry tests). `make bootstrap-check` exit 0 (will be re-verified at session-end).

---

## Round-20 verdict

| Severity      | Count | Disposition |
|---------------|-------|-------------|
| HIGH          | 0     | —           |
| MEDIUM        | 0     | —           |
| LOW (closed)  | 0     | —           |
| LOW (info)    | 3     | All DOCUMENTED-NOT-FIXED, rationale in each finding |

**Status:** PASS. M5 ships. Two consecutive milestones (M4 + M5) with zero in-batch fixes — the pattern reuse methodology is confirmed reproducible.

**Predicted M6 (bc_contract) friction:** if M6 follows the same pattern (parse `0/` dictionaries → persist `bc_quality.json` → audit reads and compares to manifest), expect 0 MED. The main new contract surface is "is `0/U`'s patch list a superset of polyMesh patches?" which is a cross-artifact check — borderline novel but symmetric with M5's `manifest required_patches ⊆ realized polyMesh patches` check.
