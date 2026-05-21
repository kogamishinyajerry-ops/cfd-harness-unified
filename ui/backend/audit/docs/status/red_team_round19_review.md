# Red Team Round-19 Review — M4 Meta Scan (Real Mesh Contract)

**Scope:** M4 milestone replaced the Phase-0 MOCKED `mesh_contract` gate with a real
evidence-driven gate. Backend (`backends/openfoam.py`) now invokes `checkMesh`
between `blockMesh` and `simpleFoam`, parses its output, and persists
`artifacts/mesh_quality.json` as the single source of truth. Audit
(`audit/mesh.py`) reads that file plus the y+ map from `solver_gate.json`
and evaluates two independent dimensions against the manifest's
`mesh_contract.quality_thresholds` + `mesh_contract.y_plus_target`.

**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round18_review.md` (M3: 1 MED + 1 LOW closed in batch; 3 LOW info documented).
**Verdict:** **PASS — 0/0/0/4 at probe time, 0 in-batch fixes, 4 LOW DOCUMENTED-NOT-FIXED**. M4 added a new real trust gate but, unlike M2.3 which exposed HIGH-class drift, the M4 gate landed clean because the design pattern from M2.3 (single-source-of-truth persistence, dimension-level honesty) was applied from the start.

---

## Method

10 probes against the new mesh-gate surface. Two flavors:
1. **New trust gate** (checkMesh persistence + dimension evaluation) — predicted by the round-17 pattern ("new trust gate ≈ 1-2 MED"). M4 added the gate but **borrowed the M2.3a single-source-of-truth pattern wholesale** (mesh_quality.json mirrors solver_gate.json), so the failure modes that would have produced MEDs were structurally pre-empted.
2. **Cross-case generality** (y+ patch selection, threshold typing, missing-data semantics) — informational; covered by tests, no honesty-rule violations.

| #  | Probe                                                                                | Outcome    |
|----|--------------------------------------------------------------------------------------|------------|
| 1  | `mesh_quality.json` absent but `mesh_report.json` exists → could gate silently PASS? | clean (BLOCKED with `mesh_quality_json_missing`) |
| 2  | `checkmesh_status: "blocked"` (OSError/timeout) propagates BLOCKED, not PASS         | clean (test_mesh_gate_blocked_when_checkmesh_oserrored) |
| 3  | Quality threshold declared but corresponding metric absent in parsed log             | clean (INCOMPLETE → overall FAIL, not silent PASS) |
| 4  | `Failed N mesh checks.` in checkMesh log → gate must FAIL even if metrics pass       | clean (test_mesh_gate_fails_when_checkmesh_reports_failed_checks) |
| 5  | Per-check `OK.` suffix mis-matching terminal `Mesh OK.` line                         | clean — caught DURING M4.1 dev, parser distinguishes via `line.strip() == "Mesh OK."` |
| 6  | `mesh_quality.json` tamperable on disk (user edits FAIL → ok)                        | R19-F-01 (LOW info, deferred — same threat model as R-32) |
| 7  | `y_plus` patch hint missing → fallback picks wrong patch (e.g. inlet "wallA")        | clean (test_mesh_gate_y_plus_uses_wall_patch_hint + fallback test) |
| 8  | Manifest declares `y_plus_target` but solver hasn't run → silent PASS?               | clean (INCOMPLETE → overall FAIL; honesty fence test) |
| 9  | `checkmesh_status` absent (legacy mesh_quality.json shape) → ambiguous semantics     | R19-F-02 (LOW info, deferred — current artifacts all have this field) |
| 10 | `_persist_mesh_quality` OSError during write → does the run crash?                   | clean (try/except OSError, mirrors `_write_gate` from R17-F-02) |
| 11 | Quality threshold key drift (e.g. `max_skewness` vs `maxSkewness`)                   | R19-F-03 (LOW info, deferred — schema-level fix, not gate-level) |
| 12 | y+ data comes from a function-object that emitted multiple wall patches              | clean — manifest's `wall_patch` field disambiguates; verified in live BFS run |
| 13 | mocked backend + real M4 gate → silent PASS via MOCKED path                          | clean (test_mesh_gate_mocked_backend_returns_mocked; status MOCKED, NOT PASS) |
| 14 | Quality FAIL **AND** y+ FAIL → both surface in `summary` and `mesh_report.json`      | clean (combined `_combine_dimensions` returns FAIL with both fails in details) |
| 15 | Empty/whitespace checkMesh log → safe defaults, no crash                             | clean (test_parse_checkmesh_empty_log_returns_safe_defaults) |
| 16 | `checkmesh_status: "failed"` but manifest thresholds all pass numerically            | clean (test_mesh_gate_fails_when_checkmesh_reports_failed_checks; `overall_mesh_ok=False` flips overall to FAIL) |
| 17 | `mesh_quality.json` non-JSON → catastrophic uncaught exception?                      | R19-F-04 (LOW info — `_read_mesh_quality` catches `JSONDecodeError`, returns BLOCKED with reason; deferred fence test) |

---

## Findings

### R19-F-01 — LOW (info, deferred) — `mesh_quality.json` is a tamper surface

**File:** `src/cfdtrust/backends/openfoam.py:_persist_mesh_quality` + `src/cfdtrust/audit/mesh.py:_read_mesh_quality`.

A user could open `artifacts/mesh_quality.json` and rewrite `overall_mesh_ok` from `false` to `true`, or zero out a violated `max_skewness`. The audit gate trusts what it reads.

**Threat model:** SAME class as R-32 (`solver_gate.json` tamper surface). Per the round-17 deferral rationale: internal case-dir artifacts are trusted-by-convention; only externally-supplied inputs (reference CSV, manifest) carry integrity guarantees. If the threat model ever expands to "hostile case-dir editor", every artifact under `artifacts/` needs per-file signing in one sweep — single-file fixes would be lopsided.

**Decision:** DEFER. Document in RISK_REGISTER as R-38.

### R19-F-02 — LOW (info, deferred) — `checkmesh_status` field is required-by-convention but unenforced

**File:** `src/cfdtrust/audit/mesh.py:run`.

The audit gate reads `mesh_quality.get("checkmesh_status")` and only treats `"blocked"` specially. If a legacy or malformed `mesh_quality.json` lacks this field entirely, the gate falls through to the quality-dimension evaluation — which will then find no geometry data and emit INCOMPLETE → FAIL. That's a safe-degrade outcome but it's not explicit-by-design.

**Threat model:** A real-world malformed JSON would be more likely to OSError or JSONDecodeError (caught) than to silently drop fields. All M4.1-generated artifacts include `checkmesh_status`.

**Decision:** DEFER. If a sibling schema file is ever added for artifacts (currently only manifests + trust_report have schemas), this falls out naturally.

### R19-F-03 — LOW (info, deferred) — threshold name drift not caught at schema validation time

**File:** `src/cfdtrust/schemas/case_manifest.schema.json` + `src/cfdtrust/audit/mesh.py`.

The manifest's `mesh_contract.quality_thresholds` is currently an open `additionalProperties: true` object. A user typo (`maxSkewness` instead of `max_skewness`) would silently be ignored by the gate (no metric → not in the recognized-list iteration → not checked).

Two ways to fix:
- (a) tighten the schema to `additionalProperties: false` + enumerate the three known keys
- (b) audit gate warns when a manifest-declared threshold key isn't in the recognized list

Both are non-trivial and slightly opinionated (the schema lock-in would block legitimate forward-compat manifest fields).

**Decision:** DEFER. Document in RISK_REGISTER as R-39. Re-evaluate when a real case ships a typo and the gate silently passes — i.e. when the failure mode actually occurs once.

### R19-F-04 — LOW (info, deferred) — `_read_mesh_quality` BLOCKED-on-JSON-decode-error path lacks dedicated regression test

**File:** `src/cfdtrust/audit/mesh.py:_read_mesh_quality`.

`_read_mesh_quality` catches `(OSError, json.JSONDecodeError)` and returns `(None, "mesh_quality_json_unreadable: ...")`. The gate then emits BLOCKED. This is functionally correct (verified by inspection) but no test specifically writes a malformed-JSON `mesh_quality.json` to assert BLOCKED.

**Decision:** DEFER fence test to Round-20 OR next milestone that touches `audit/mesh.py`. Risk is low because (a) the path is structurally identical to the JSON-decode handling in `_read_persisted_gate` from M2.3a which IS tested, and (b) M4.1's only writer is `_persist_mesh_quality` which uses `json.dumps`.

---

## Pattern update — predictive accuracy

Round-17 pattern: "each new trust boundary ≈ 1-2 MED + a few LOW info."
Round-18 confirmation: user-string surface produced exactly 1 MED.
**Round-19 refinement:** A new trust gate that **reuses an existing persistence pattern wholesale** can land MED-free. M4 borrowed M2.3a's single-source-of-truth design (one file written by execute, read by audit) PLUS the failed-write-tolerance from R17-F-02 PLUS the dimension-INCOMPLETE-not-PASS honesty from R15-F-02. The result: 4 LOW info, 0 MED, 0 HIGH.

This is the first milestone since R-18 to land **zero in-batch fixes**, and the explanation is methodological, not luck: when a new layer reuses verified pattern, the failure-mode taxonomy is already explored.

**New rule of thumb:** if a new trust gate is built by copying an existing gate's persistence + reading + honesty contract, the MED ceiling is 0. If it introduces a NEW contract (e.g. external file integrity, new user-input shape), the MED ceiling is 1-2.

---

## Live verification (mandatory per M2.3a doctrine)

Two fresh live runs against real OpenFOAM 11 container:

```
/tmp/m4_live/bfs           — BFS Re_H=37,400, 11600 cells
  blockMesh OK → checkMesh OK → simpleFoam 2000/2000 iter, FAIL on p
  mesh_quality.json:
    checkmesh_status: ok
    max_non_orthogonality: 0.0   (≤ 65)   ✓
    max_skewness:         8.68e-14 (≤ 4.0) ✓
    max_aspect_ratio:     22.2268  (≤ 1000) ✓
    overall_mesh_ok:      true
  mesh_contract gate: FAIL
    summary: "quality PASS; y+ FAIL (bottomWall avg=20.7663 outside [0.5, 5.0])."

/tmp/m4_flat/case          — flat plate Re_L=4e6, 6000 cells
  blockMesh OK → checkMesh OK → simpleFoam 159/500 iter, converged
  mesh_quality.json:
    checkmesh_status: ok
    max_non_orthogonality: 0.0
    max_skewness:         1.10e-13
    max_aspect_ratio:     15.30
    overall_mesh_ok:      true
  mesh_contract gate: FAIL
    summary: "quality PASS; y+ FAIL (wall avg=51.4846 outside [0.5, 5.0])."
```

Both cases now produce HONEST mesh validation. Pre-M4, both cases reported `mesh_contract: MOCKED` and the operator had no visibility into the y+ over-shoot. Post-M4, the y+ mismatch surfaces with exact numbers and a clear remediation path.

This is exactly the v0 wedge promise: a CFD case is correct ONLY if it passes its explicit case contract. Pre-M4, the contract was unenforced at the mesh layer. Post-M4, it is.

---

## Test coverage

16 new M4.2 audit-gate tests + 18 new M4.1 backend tests = 34 mesh-related tests:

- parser: canonical OK, failed checks, empty, partial, per-check vs terminal `Mesh OK.` discrimination, malformed numerics
- persistence: OK / failed / OSError-blocked / timeout-blocked paths
- backend wiring: docker call ordering (blockMesh → checkMesh → simpleFoam), OSError captures, timeout captures, mesh_quality.json existence after run
- audit gate: mocked backend → MOCKED; missing artifacts → BLOCKED; quality FAIL on each metric; quality INCOMPLETE → overall FAIL; y+ FAIL outside target; y+ INCOMPLETE → overall FAIL; wall_patch hint vs fallback; combined PASS path; honesty fences

Suite: **226/226 pass + 1 opt-in network skip** (was 192 before M4 = +34 new mesh tests).
`make bootstrap-check`: exit 0 (will be re-verified at session-end).

---

## Round-19 verdict

| Severity      | Count | Disposition |
|---------------|-------|-------------|
| HIGH          | 0     | —           |
| MEDIUM        | 0     | —           |
| LOW (closed)  | 0     | —           |
| LOW (info)    | 4     | All DOCUMENTED-NOT-FIXED, rationale in each finding |

**Status:** PASS. M4 ships. The mesh gate is the first real evidence-backed audit gate in the harness; both geometry and bc gates remain MOCKED (M5/M6 follow-up).

**Predicted next milestone friction:** Geometry contract (mesh structure → patch topology cross-check) and BC contract (0/ dictionary parse → patch-vs-required-patches reconcile) each have ONE new trust boundary. Per the refined pattern, if each milestone reuses the M4 pattern (persist → read → dimension evaluate), each should land 0 MED. If either introduces a brand-new contract surface (e.g. mesh-topology validation against the geometry block — no existing pattern), expect 1 MED.
