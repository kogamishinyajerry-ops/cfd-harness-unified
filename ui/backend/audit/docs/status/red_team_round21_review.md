# Red Team Round-21 Review — M6 Meta Scan (Real BC Contract)

**Scope:** M6 milestone replaced the Phase-0 MOCKED `bc_contract` gate with a real
evidence-driven gate. Backend (`backends/openfoam.py`) now parses every
`0/<field>` file (U, p, and each `bc_contract.turbulence_fields` entry)
and persists `artifacts/bc_quality.json`. Audit
(`audit/boundary_conditions.py`) reads BOTH `bc_quality.json` AND
`geometry_quality.json` (the first cross-artifact audit in the harness)
and evaluates three dimensions: file presence, patch coverage, and
BC type match (with manifest-key resolution to literal-patch OR type-class).

**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round20_review.md` (M5: 0 fixes in batch, 3 LOW info documented; second consecutive zero-fix milestone).
**Verdict:** **PASS — 0/0/0/4 at probe time, 0 in-batch fixes, 4 LOW DOCUMENTED-NOT-FIXED**. M6 introduced a new contract surface (cross-artifact dependency on geometry_quality.json) — per R-20's prediction, this could have produced 1 MED. It did not, because the new dependency was treated exactly like a missing artifact (BLOCKED with explicit reason) rather than as a novel failure mode requiring novel honesty rules.

---

## Method

16 probes against the new BC-gate surface. The cross-artifact dependency (BC audit needs polyMesh patches from geometry_quality.json) was the predicted MED ceiling-raiser; probes 5, 6, 11, 16 specifically target that surface.

| #  | Probe                                                                                | Outcome    |
|----|--------------------------------------------------------------------------------------|------------|
| 1  | `bc_quality.json` missing + openfoam backend → silent PASS?                          | clean (BLOCKED with `bc_quality.json_missing`) |
| 2  | `bc_quality.bc_parsing_status: "blocked"` (zero dir OSError) → propagates             | clean (test_bc_gate_blocked_when_bc_quality_marked_blocked) |
| 3  | Missing `turbulence_fields` entry on disk (manifest says nut, no 0/nut) → FAIL       | clean (test_bc_gate_file_presence_fail_on_missing_turbulence_field) |
| 4  | Unparseable 0/<file> (no `boundaryField` block) → FAIL                                | clean (test_bc_gate_file_presence_fail_on_unparseable_file) |
| 5  | **Cross-artifact**: `geometry_quality.json` missing → BC silent PASS?                | clean (BLOCKED with `geometry_evidence_missing`) — explicitly designed |
| 6  | **Cross-artifact**: `geometry_quality.status: "blocked"` (boundary missing) → BC?    | clean (same BLOCKED path; test_bc_gate_blocked_when_geometry_quality_missing) |
| 7  | Realized polyMesh patch missing from one 0/<file> → FAIL with per-field gap          | clean (test_bc_gate_patch_coverage_fail_on_missing_patch_entry) |
| 8  | Manifest `wall` key on BFS expands to topWall + bottomWall + stepFace               | clean (test_bc_gate_type_match_resolves_wall_to_multiple_patches) |
| 9  | Manifest `wall` on flat_plate where `wall` IS a literal patch → literal wins         | clean (test_bc_gate_resolves_literal_patch_before_type_class) |
| 10 | BC type mismatch (topWall realized=slip but manifest declares noSlip) → FAIL          | clean (test_bc_gate_type_match_fail_on_mismatch) |
| 11 | Manifest declares BC for nonexistent patch `ghost` → FAIL with unresolvable_keys      | clean (test_bc_gate_type_match_fail_on_unresolvable_key) |
| 12 | Manifest declares no per-patch BC sections → type_match PASS (nothing to check)       | clean (covered by note field; PASS path) |
| 13 | `turbulence_fields` lists U by accident → dedup, not double-process                   | clean (test_collect_and_persist_bc_deduplicates_canonical_fields) |
| 14 | Comments hide `type fake;` lines → parser ignores                                     | clean (test_parse_field_boundary_field_strips_comments) |
| 15 | Nested `{}` block inside a BC entry (e.g. `transform { type none; }`) confuses parser? | clean (test_parse_field_boundary_field_handles_nested_braces_in_block) |
| 16 | Truncated 0/<file> (unbalanced braces) → no partial claim                             | clean (test_parse_field_boundary_field_returns_empty_on_truncated) |
| 17 | `bc_quality.json` tamper surface (user edits realized type to match manifest)        | R21-F-01 (LOW info, deferred — same family R-32, R-38, R-41) |
| 18 | Manifest BC `field_class` field-class-to-file mapping is private (`_FIELD_CLASS_TO_FILE`) — typo (`pressuer`) silently treated as `pressuer` → file missing → FAIL | R21-F-02 (LOW info, deferred — message is clear enough) |
| 19 | Empty key block in bc_contract (e.g. `inlet: {}`) → resolve and check zero pairs       | R21-F-03 (LOW info, deferred — current behavior: skip silently; manifest typo) |
| 20 | Field-class block has `type: null` → skip (intended) vs FAIL (debatable)              | R21-F-04 (LOW info, deferred — current: skip; matches "no type declared" semantics) |

---

## Findings

### R21-F-01 — LOW (info, deferred) — `bc_quality.json` is a tamper surface

**Same class as R-32 (solver_gate.json), R-38 (mesh_quality.json), R-41 (geometry_quality.json).** A user could edit the realized type to match the manifest's declared type, fooling the audit. Internal case-dir artifacts are trusted-by-convention; defense-in-depth via per-artifact signing would address all four together in one sweep.

**Decision:** DEFER. Document in RISK_REGISTER as R-44.

### R21-F-02 — LOW (info, deferred) — `field_class` typo silently mapped to a missing file

**File:** `src/cfdtrust/audit/boundary_conditions.py:_field_class_to_file`.

The mapping `{velocity: U, pressure: p}` plus identity-fallback means a manifest typo like `pressuer` becomes a lookup for file `0/pressuer` which is missing → FAIL via the file_presence dim. The user sees "missing field file" rather than "you typo'd a recognized field class."

**Why not fix:** the FAIL message is unambiguous (`expected file: 0/pressuer`) and the user can correct it. A schema-level enum on field-class adds maintenance overhead each time a new turbulence model adds a field (e.g. `vSmagorinsky`, `epsilon`).

**Decision:** DEFER. Document in RISK_REGISTER as R-45.

### R21-F-03 — LOW (info, deferred) — empty key block `inlet: {}` skipped silently

**File:** `src/cfdtrust/audit/boundary_conditions.py:_eval_type_match`.

A manifest with `bc_contract.inlet: {}` (empty dict for a declared patch) resolves the key but checks zero field-classes. The type_match dim reports `checked_count` unchanged from the absent state, and the gate may PASS the type_match dim with the user thinking they declared something. Patch coverage still catches it if the patch is in polyMesh.

**Why not fix:** the patch_coverage dim catches the actual structural problem (every realized polyMesh patch must have BCs in every field file). An empty manifest declaration is informational/atypical; the harness's existing dimensions already cover the failure modes that matter.

**Decision:** DEFER. Document in RISK_REGISTER as R-46.

### R21-F-04 — LOW (info, deferred) — field-class block with `type: null` skipped silently

**File:** `src/cfdtrust/audit/boundary_conditions.py:_eval_type_match`.

A manifest like `inlet: { velocity: { type: null } }` skips the type check for that pair (treated as "no type declared, nothing to check"). Defensible as "absent intent" but a YAML user may write null thinking it means "any type acceptable" — that's not what the harness implements.

**Decision:** DEFER. Document in RISK_REGISTER as R-47. Document the convention in CASE_NOTES.md if a real user hits it.

---

## Pattern confirmation — three in a row

R-19 prediction: "pattern reuse → MED ceiling 0."
R-20 confirmation: "two in a row with zero fixes."
R-21 confirmation: **third consecutive zero-fix milestone**, AND the first one to introduce a NEW contract surface (cross-artifact dependency on geometry_quality.json). The pattern still holds because:

- The new failure mode (geometry evidence missing) was treated as a familiar one (BLOCKED with explicit reason), not as a novel honesty puzzle.
- The dimension framework (file_presence + patch_coverage + type_match) extended naturally from M5's 2-dim pattern to M6's 3-dim.
- INCOMPLETE-rolls-up-to-FAIL extended from M4/M5 to M6 without modification.

**Refined rule of thumb:** a new contract surface adds MED risk ONLY when it introduces a new honesty rule (not just a new check). M6 added a new CHECK (cross-artifact) but reused the existing BLOCKED-on-missing-evidence honesty rule, so no new MED ceiling.

---

## Live verification (mandatory per M2.3a doctrine)

Fresh flat_plate end-to-end run:

```
/tmp/m6_flat/case          — flat plate Re_L=4e6, 6000 cells
  blockMesh OK → geometry_quality.json (5 patches: inlet/outlet/wall/top/frontAndBack)
              → bc_quality.json       (5 fields parsed: U/p/k/omega/nut, all patches present)
              → checkMesh OK          → simpleFoam 159 iter converged
  geometry_contract: PASS — presence 5/5; dimensionality 2.5D + frontAndBack empty matches
  mesh_contract:     FAIL — quality PASS; y+ FAIL (wall avg=51.48 outside [0.5, 5.0])
  bc_contract:       PASS — file_presence 5; patch_coverage 5/5; type_match 9 pairs
  overall_status:    FAIL — driven by mesh_contract FAIL (y+ overshoot)
```

Plus dry-run verification against the live BFS:

```
/tmp/m4_live/bfs          — BFS Re_H=37,400, 11600 cells
  bc_contract: PASS — file_presence 5; patch_coverage 5/5; type_match 15 pairs
    (wall key correctly resolves to 3 wall-typed patches: topWall + bottomWall + stepFace
     × 3 field classes (velocity/k/omega) = 9 wall pairs + 4 inlet + 2 outlet = 15)
```

**The harness is now 3-of-3 audit gates real.** Pre-M6, every case reported `bc_contract: MOCKED`. Post-M6, the harness catches BC/manifest drift at audit time — before the operator wastes a solver run debugging a mismatch.

---

## Test coverage

29 new M6 tests:

- parser (8): BFS U canonical, scalar K, no boundaryField, truncated, untyped-block skip, comment stripping, nested-braces tolerance
- persistence (3): ok / missing-file / blocked paths
- backend collect (2): manifest field walking, dedup of canonical fields
- audit gate (16): mocked → MOCKED, missing bc_quality → BLOCKED, missing geometry_quality → BLOCKED, blocked bc_quality → BLOCKED, file_presence FAIL on missing/unparseable, patch_coverage FAIL on missing patch, type_match PASS on canonical, wall key → multi-patch expansion, type mismatch → FAIL, unresolvable key → FAIL, literal-wins-over-type-class, end-to-end PASS evidence chain, honesty fences (empty contract, no artifacts), field-class missing recorded in both file_presence and type_match dims

Suite: **281/281 pass + 1 opt-in network skip** (was 252 before M6 = +29 new BC tests).

---

## Round-21 verdict

| Severity      | Count | Disposition |
|---------------|-------|-------------|
| HIGH          | 0     | —           |
| MEDIUM        | 0     | —           |
| LOW (closed)  | 0     | —           |
| LOW (info)    | 4     | All DOCUMENTED-NOT-FIXED, rationale per finding |

**Status:** PASS. M6 ships. **Three consecutive zero-fix milestones (M4 + M5 + M6).** The harness is now 3-of-3 audit gates real; only `solver_execution`, `qoi`, and `reference_comparison` remain — and solver_execution is already real since M2 (gates as real evidence; previous trust loop). qoi + reference_comparison are M2-real too.

**Milestone arc:** the v0 wedge promise — "a CFD case is correct ONLY if it passes its explicit case contract" — is now enforced at every audit layer (geometry, mesh, BC), every evidence layer (solver, qoi, reference). The remaining gaps are not honesty gaps; they're domain expansion (more turbulence models, more case archetypes, AI advisor on top).

**Predicted next milestone friction:** the obvious next milestone is M7 (BC value-checking — does `0/U.inlet.value` equal the manifest's declared `magnitude_m_s`?). That's purely additive within the existing BC gate framework — predicted 0-1 MED. Beyond M7, the failure-mode taxonomy is essentially saturated for Phase-1 single-case verification; future milestones extend BREADTH (more cases, more models) rather than DEPTH (more honesty rules).
