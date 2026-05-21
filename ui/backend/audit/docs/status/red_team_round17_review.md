# Red Team Round-17 Review — M2 Meta Scan (backward_facing_step)

**Scope:** the M2 milestone landed as the project's first multi-case milestone — `cases/backward_facing_step/` scaffold, NASA TMR Driver-Seegmiller reference data, and the live wallShearStress + comparison flow against the new case. ~500 LOC across new case dictionaries + manifest + reference data + provenance.
**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round16_review.md` (PASS, 2 MED + 5 LOW on 2d, all closed).
**Verdict:** **EARLY-DETECTION HIT — 1 HIGH-class + 1 MED surfaced LIVE during M2.3 execution (not in retrospective meta-scan), both closed in same milestone**. Round-17 retrospective scan adds 2 LOWs (one DOCUMENTED, one CLOSING this batch).

The pattern from round 16 ("LOC doesn't scale findings; new trust boundaries do") was validated emphatically: the new case_dir + new patch-naming axis surfaced TWO bugs that flat_plate had hidden by coincidence (clean convergence + literal "wall" patch name).

---

## What M2 surfaced

M2's milestone goal was *"prove harness generality, not flat-plate specificity."* It delivered exactly that, by revealing two harness assumptions invisible until a second case forced them into view:

### M2.3a — HIGH-class — `solver.execute()` FAIL silently became PASS in `read_artifacts()` (closed in M2.3)

**File:** `src/cfdtrust/audit/solver.py`.

Pre-M2.3 architecture:

| Function           | Called by         | Logic                            |
|--------------------|-------------------|----------------------------------|
| `solver.execute()` | `cmd_run`         | Runs backend, returns gate dict  |
| `solver.read_artifacts()` | `cmd_report` | Checks `solver.log` exists → PASS, else BLOCKED |

The two functions disagreed when execute returned anything other than PASS/MOCKED. flat_plate hid this because it converged at iter 159 with all 5 residual targets met (execute=PASS, read_artifacts=PASS happened to agree). BFS exposed it: simpleFoam ran 2000/2000 iters with the `p` residual stuck at 3.16e-5 vs target 1e-5 — backend returned FAIL — but `read_artifacts()` saw `solver.log` exists and returned PASS. `trust_report.json` propagated the false PASS as the gate's status.

This is THE failure mode the project's core principles 11-12 forbid (`Do not hide mocked execution / missing evidence`). HIGH-class severity classification because a FAILed run was being persisted as healthy gate state — silently — across two of the three CLI subcommands.

**Fix (closed in M2.3):** `execute()` persists the result to `artifacts/solver_gate.json`; `read_artifacts()` loads that file as the single source of truth. Legacy file-existence fallback retained (with a `warning` field) for case dirs that ran pre-fix.

3 regression tests fence the contract:
- `test_m23a_failed_execute_propagates_through_to_trust_report` — FAIL survives the round-trip
- `test_m23a_execute_writes_solver_gate_json` — gate is written on every execute call
- `test_m23a_legacy_case_dir_without_persisted_gate_still_works` — back-compat for pre-fix case dirs

### M2.3b — MEDIUM — `wall_shear.extract_wall_cf` hardcoded patch name (closed in M2.3)

**File:** `src/cfdtrust/audit/qoi.py` + `src/cfdtrust/qoi/wall_shear.py`.

Pre-M2.3, the audit-layer call to `wall_shear.extract_wall_cf(...)` hardcoded `patch="wall"` — flat_plate's literal patch name. BFS uses `bottomWall`, `stepFace`, `topWall`, so the extractor blocked with `patch 'wall' not in polyMesh/boundary; available: ['bottomWall', 'frontAndBack', ...]`. The harness wasn't a harness; it was a flat_plate-specific pipeline that happened to look generic.

**Fix (closed in M2.3):** new manifest field `reference_comparison.wall_patch` (string, default "wall" for back-compat) drives which patch the extractor reads from. BFS declares `wall_patch: bottomWall`. Schema constrains the field to a valid OpenFOAM patch-name pattern (`^[A-Za-z][A-Za-z0-9_]*$`).

2 regression tests fence the field:
- `test_m23b_wall_patch_field_is_honored` — BFS-class case with non-wall patch extracts correctly
- `test_m23b_default_wall_patch_is_wall_for_back_compat` — flat_plate's old manifests still work

---

## Round-17 retrospective probes

After the in-flight fixes, scanned the new code surface for residual issues:

| # | Probe                                                                  | Outcome      |
|---|------------------------------------------------------------------------|--------------|
| 1 | `solver_gate.json` tamper surface (can a user flip FAIL→PASS by hand?) | R17-F-01 (LOW info — DOCUMENTED) |
| 2 | `wall_patch` default fallback — silent regression if a case forgets it? | clean (default "wall" + extractor errors with clear list of available patches) |
| 3 | BFS scaffold dictionaries pass schema validation                        | clean (5 new fence tests added) |
| 4 | Reference CSV / manifest SHA cycle works for the new case               | clean (`test_backward_facing_step_reference_csv_matches_manifest_sha`) |
| 5 | `validation_status` mapping handles BFS's FAIL outcome correctly        | clean (`solver=real + ref=FAIL → not_validated`, R16-F-07 already fences this) |
| 6 | `execute()` propagates disk-write OSError uncaught                      | R17-F-02 (LOW — CLOSING this batch) |
| 7 | `_find_latest_time` symlink walk applied to BFS time dirs (1000, 1500, 2000) | clean (R16-F-03 already covers this — multi-time-dir doesn't change the surface) |
| 8 | Relative-error metric at near-zero reference (BFS reattachment)         | not a finding — metric is honest; 4250% at recirculation-zero is communicating a real CFD model deficiency |
| 9 | yPlus FO regex against 3 wall patches (bottomWall/stepFace/topWall)     | clean (regex `patch (\w+) y+ :` matches per-patch lines) |
| 10 | controlDict wallShearStress FO emits per-face data for both bottomWall AND stepFace | clean (BFS live run produced 160-vector bottomWall block) |
| 11 | qoi.csv 5-column shape (R16-F-08) holds across BFS's larger row count   | clean (160 wall faces > flat_plate's 100; CSV grows linearly) |
| 12 | BFS's max_iterations=2000 vs flat_plate's 500 — any hidden bounds?       | clean |

### R17-F-01 — LOW (informational) — `solver_gate.json` tamper surface; DOCUMENTED-NOT-FIXED

**File:** `src/cfdtrust/audit/solver.py` — the M2.3a persistence file.

A user (or a buggy refactor) could edit `artifacts/solver_gate.json` post-write, e.g. flipping `"status": "FAIL"` to `"status": "PASS"`. `read_artifacts()` would then return the tampered value.

**Why DOCUMENTED-not-fixed:** the project's threat model (per `docs/project-memory/PRODUCT_PRINCIPLES.md` and the trust-boundary analysis in round 16) treats *user-owned files inside the case dir* as part of the trust input, not as adversarial. The same surface exists for `solver.log`, `residuals.csv`, `qoi.csv` — none are hash-checked. The two artifacts that ARE integrity-checked (manifest reference CSV via R16-F-01, manifest itself via schema validation) are the externally-supplied inputs; internal artifacts are trusted-by-convention.

If the threat model ever expands to "harness must resist a hostile case-dir editor", this becomes a real fix (sign each artifact with the run's entropy + verify on read). For Phase 1's "trusted local user" scope, the cost outweighs the benefit. Recording the decision here so a future maintainer doesn't re-discover it as a "new" finding.

### R17-F-02 — LOW — `execute()` propagated disk-write OSError uncaught (closed in this batch)

**File:** `src/cfdtrust/audit/solver.py` `_write_gate()`.

Pre-fix: if `_write_gate` raised `OSError` (disk full, permissions, R/O filesystem mid-run), the exception propagated up through `execute()` and the caller lost the just-computed gate result entirely.

**Fix (applied in this batch):** wrap the write in `try/except OSError`. On failure, augment the returned gate with `details.gate_persistence_failed = str(e)` and a `next_step` hint, then return the gate object. The original execute-result truth survives in memory even when persistence is broken.

1 regression test (`test_r17_f02_gate_persistence_failure_does_not_obliterate_gate`) fences: monkeypatches `Path.write_text` to raise OSError on `solver_gate.json`, asserts the returned gate still carries the original `status: MOCKED` AND the `gate_persistence_failed` augmentation.

---

## What was probed and worked

- **Round-trip honesty**: `execute() → solver_gate.json → read_artifacts() → trust_report.json` now carries FAIL truthfully across all three CLI subcommands. Three independent test paths fence this (M2.3a tests).
- **Cross-case generality**: BFS uses 6 patches (vs flat_plate's 5), 3 distinct wall patches (vs flat_plate's 1), 2.5D layout in different orientation. All scaffold fences from flat_plate carried over cleanly with case-specific patch-name declaration.
- **Reference data integrity**: BFS reference CSV hash check (R16-F-01 pattern) works identically to flat_plate's. Schema-layer enforcement of all 2d fields (R16-F-06) catches typos at validation time.
- **Multi-case cockpit**: cockpit now lists both cases in Trust Loop Status — flat_plate (MOCKED in source) + BFS (MOCKED in source); both produce structurally valid trust_report.json files in the mocked path; both fail-state-correctly in the live path.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH-class | MED | LOW | Total |
|-----------------------------|------|------------|-----|-----|-------|
| 13 (2a meta)                | 0    | 0          | 0   | 0   | 0     |
| 14 (2b meta + fix)          | 0    | 0          | 1   | 2   | 3     |
| 15 (2c meta + fix)          | 0    | 0          | 2   | 2   | 4     |
| 16 (2d meta + fix)          | 0    | 0          | 2   | 5   | 7     |
| **17 (M2 meta + in-flight fix)** | **0** | **1** | **1** | **2** | **4** |

First HIGH-class since round 10. Notable because:
1. **It was caught during execution, not by retrospective scan.** The pattern of "run the second case live, watch the trust report, notice the disagreement" is more effective than reading the diff. M2's milestone goal directly produced the finding.
2. **The fix was small (3 functions, 1 new file persistence path)** — but the absence of any other case beyond flat_plate had hidden the bug for 16 rounds. Confirms that "1-case projects are 0-case projects in terms of harness validation."

---

## Pattern update — runtime-surfaced bugs vs static-scan bugs

| Detection moment | Round 14 | Round 15 | Round 16 | Round 17 |
|------------------|----------|----------|----------|----------|
| Static scan      | 1 MED + 2 LOW | 2 MED + 2 LOW | 2 MED + 5 LOW | 0 + 2 LOW |
| Live execution   | 0        | 1 LOW (R16-F-01: Time regex unit suffix) | 0 | **1 HIGH + 1 MED** |

Rounds 14-16 found everything by static code review; round 17 found the most important issues by *running the system in a configuration it had never run in before*. This validates the "real-usage eval > static review" pillar from the Anthropic Agent Canon adoption (memory file `reference_anthropic_agent_canon.md` §VI).

Forward implication: future milestones should ALWAYS include a live-run step against a configuration the system hasn't seen. The marginal cost of one extra docker invocation per milestone is the cheapest "catch the bug a static scanner missed" insurance available.

---

## Verdict

**PASS** on M2.

The M2 milestone delivered EXACTLY what its charter promised: a second case end-to-end through the harness AND surfaced two harness-generality bugs that a single-case project would have shipped indefinitely. 171/171 pytest + 1 opt-in network skip. `make bootstrap-check` exit 0.

Both findings (M2.3a HIGH-class, M2.3b MEDIUM) closed in the same milestone — the in-flight close pattern from rounds 14-16 held. Cockpit shows both cases with truthful gate states. Phase 1's "OpenFOAM-based CFD Trust Workbench" v0 wedge thesis now has TWO independent case validations supporting it.

---

## Recommended next milestones

| # | Title | Brief                                                                                  | Predicted budget |
|---|-------|----------------------------------------------------------------------------------------|------------------|
| **M3** | Newbie-Ready CLI | `cfdtrust init <name>` scaffolds from template; `verify-reference` bumps hashes; better diagnostics | 4-6 crew-hour |
| **M4** | Real Mesh Contract | Parse checkMesh log, enforce manifest y+ target, drop mesh_contract from MOCKED        | 6-8 crew-hour |
| **M5** | AI Advisor MVP | `cfdtrust advise <case>` reads trust_report, gives natural-language explanation        | 4-6 crew-hour |
| **M1** | First Validated PASS (deferred from initial pick) | Refine flat_plate to y+<5 + low-Re wall functions; first `validation_status: validated` in project history | 4-6 crew-hour |

Recommendation: **M3 next**. M2 just exposed harness-generality holes; M3 is "make those holes findable in advance via better CLI scaffolding" — the natural follow-up. M4 has higher V&V value but bigger surface; M1 has the most prestige (first validated PASS) but doesn't expand harness capability.

Owner decision required at next session boundary.
