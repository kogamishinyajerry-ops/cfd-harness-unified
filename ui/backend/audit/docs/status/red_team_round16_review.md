# Red Team Round-16 Review — Phase 1 Step 2d Meta Scan

**Scope:** adversarial probe of the sub-commit 2d additions: NASA TMR reference data ingestion (`reference/cf_reference.csv` + `provenance.md`), the new `src/cfdtrust/qoi/` package (`flat_plate_cf.py` + `wall_shear.py`), rewired `audit/qoi.py`, updated `audit/report.py` validation_status mapping, schema deltas, and the live wallShearStress + polyMesh fixtures. ~600 LOC across 4 new modules + 1 new external data source (first time the harness ingests data it didn't generate).
**Author:** test-red-team agent.
**Date:** 2026-05-21.
**Previous round:** `red_team_round15_review.md` (PASS, 0/0/2/2 — 2 MEDs closed on 2c).
**Verdict:** **FAIL — 0/0/2/5** at probe time, **all closed in this same batch**. Pattern prediction held precisely: "200-400 LOC + new external data ingestion → 1 HIGH or 2 MED expected." Two MEDs surfaced; both data-integrity / honesty-rule issues, same family as R15-F-01 / R15-F-02.

---

## Method

18 probes over 4 surfaces (ingestion, parser, comparator, audit orchestration). All findings reproducible offline via the in-repo fixtures + new schema tests. No live docker re-run was needed beyond the one already performed for 2d.

| # | Probe                                                                          | Outcome   |
|---|--------------------------------------------------------------------------------|-----------|
| 1 | Reference CSV tamper detection at load time                                     | **R16-F-01** (MED) |
| 2 | polyMesh parser behavior on `format binary` files                               | **R16-F-02** (LOW) |
| 3 | Symlink walk applied to audit-layer file reads                                  | **R16-F-03** (LOW) |
| 4 | Boundary parser regex `(\w+)\s*\{([^{}]*)\}` — nested-brace handling             | clean (no nested braces in OF boundary files) |
| 5 | `_parse_count_paren_block` regex matches face-record count instead of file count | clean (re.search left-to-right, file count is leftmost) |
| 6 | `boundary` patch missing `nFaces` or `startFace`                                | clean (ValueError with diagnostic) |
| 7 | `nFaces` negative? `startFace + nFaces` overruns `len(faces)`?                  | clean (`\d+` excludes negatives; face_centers bound-checks) |
| 8 | Re_L mismatch (4e6 vs NASA 5e6) — is 10% tolerance enough?                      | clean (turbulent-region Cf delta ~5%; documented in provenance) |
| 9 | `_find_latest_time` directory walk — symlink, traversal, weird names            | partial — see R16-F-03 |
| 10 | `extract_wall_cf` cross-file consistency (boundary vs WSS face count)          | clean (ValueError on mismatch) |
| 11 | `extract_wall_cf` performance on 1M-cell cases                                | informational only — not a 2d concern |
| 12 | `_attempt_real_comparison` silent fallback paths — diagnostic granularity      | informational only — accepted |
| 13 | `linear_interpolate` floating-point edge cases at curve endpoints               | clean (live data has 2/100 dropped, expected) |
| 14 | **`reference_csv` path absolute / `..`-traversal**                              | **R16-F-05** (MED) |
| 15 | manifest `tolerance` / `x_min_compare_m` type and range validation             | **R16-F-06** (LOW) — schema gap |
| 16 | Schema enforcement: `validation_status=validated` requires `ref_gate=PASS`     | **R16-F-07** (LOW) — schema gap |
| 17 | Kinematic vs dynamic wallShearStress / Cf normalization                         | clean (incompressible, ρ cancels — matches NASA TMR convention) |
| 18 | `qoi.csv` column layout consistency across mocked vs real modes                 | **R16-F-08** (LOW) |

Probes 1 + 14 are the two MEDs. Probe 1 is the "data we trust isn't checked"
class; probe 14 is the classic "path-from-config not constrained" class. Both
are first-class trust-harness concerns: the project's principles 2, 5, 6, 11,
12 all turn on "evidence is what it claims to be."

---

## Findings

### R16-F-01 — MEDIUM — Reference CSV has no runtime tamper-detection; only the upstream NASA file is hash-checked (closed in this batch)

**File:** `cases/flat_plate_rans_sst/reference/cf_reference.csv` (the derived data the gate actually reads) vs `cases/flat_plate_rans_sst/case_manifest.yaml > reference_comparison.source_sha256` (which hashes the *upstream* NASA tecplot file).

The 2d landing carried two distinct files into provenance:

| File                                       | Hash recorded? | Audited at load? |
|--------------------------------------------|----------------|-------------------|
| Upstream NASA `cf_plate_sstv.dat` (32 KB)  | yes (`source_sha256`) | no — the harness never opens this file |
| Derived `reference/cf_reference.csv` (14 KB, what gate reads) | **no**           | **no** |

Result: anyone with write access to `cases/flat_plate_rans_sst/reference/cf_reference.csv` (an attacker, an over-eager refactor, a clumsy "I'll just regenerate this") could swap in a curve. A curve designed to make our run silently PASS (e.g. flat Cf ≈ 2.8e-3 across the whole plate) would not be detected.

This is structurally the same failure mode as R15-F-02 ("PASS without checking anything"), one level up the call chain — instead of fabricating the *measurement*, fabricate the *reference*.

**Fix (applied in this batch):**

1. Added `reference_csv_sha256: 48eb163b4d56a390c87e4085d763a612697c65c7504e6470348e628bb9d21f2c` to the manifest's `reference_comparison` block (covers the actual in-repo CSV).
2. `audit/qoi.py._attempt_real_comparison` reads the manifest's expected hash, computes the actual hash of the on-disk CSV via `_file_sha256()`, and BLOCKs with reason `reference_csv_sha_mismatch` (surfacing both hashes) if they differ.
3. If the manifest omits `reference_csv_sha256`, the check is skipped (back-compat for pre-2d manifests; documented in code).
4. Schema constrains the format: `"pattern": "^[a-fA-F0-9]{64}$"`.
5. Two regression tests: `test_r16_f01_sha_mismatch_blocks_reference_load` (tamper detected) and `test_r16_f01_correct_sha_lets_real_comparison_run` (positive path).

### R16-F-02 — LOW — polyMesh parsers don't detect `format binary`; failure mode is confusing rather than honest (closed in this batch)

**File:** `src/cfdtrust/qoi/wall_shear.py` (all four parsers).

OpenFOAM emits binary mesh files when `writeFormat binary;` is set in `system/controlDict`. The current `flat_plate_rans_sst` controlDict sets ASCII, but any future case (or a manifest copy-paste from elsewhere) could be binary.

Pre-fix: the binary payload would pass the FoamFile-block strip cleanly, then the count-paren regex would search through unprintable bytes, and the user would see something like `ValueError: expected '<int> ( block; first 200 chars: '\x00\x00...'`. Confusing.

**Fix (applied in this batch):** new `_assert_ascii_foamfile()` helper, called by all four parsers (`parse_polymesh_{boundary,points,faces}` + `parse_boundary_field_vectors`). Detects `\bformat\s+binary\s*;` in the FoamFile header and raises a structured ValueError naming the file + a clear remediation (`Set writeFormat ascii;`). Regression test: `test_r16_f02_binary_format_polymesh_blocks_explicitly`.

### R16-F-03 — LOW — `audit/qoi.py` reads case-dir files without going through the R-17 symlink walk (closed in this batch)

**File:** `src/cfdtrust/audit/qoi.py` `_attempt_real_comparison`.

The OpenFOAM adapter's `_find_symlink_at_any_depth` (R-17 closure, sub-commit 2a) is invoked only when `backends/openfoam.run()` runs. The audit-layer `audit/qoi.run()` opens case-dir files (polyMesh + `<time>/wallShearStress`) independently. A malicious case_dir could symlink `159/` to `/etc/` or symlink `constant/polyMesh/boundary` to `/etc/passwd` — these wouldn't trigger R-17 because that walk fires elsewhere.

**Fix (applied in this batch):** the audit-layer real-comparison path checks `is_symlink()` on:
- the latest time-step directory (`case_dir / latest`)
- the wallShearStress file (`case_dir / latest / "wallShearStress"`)
- the three polyMesh files (`constant/polyMesh/{boundary,faces,points}`)

Any symlink → BLOCKED with a structured `reason: *_is_symlink` and the resolved target in `detail`. Cheaper than running a full recursive walk twice per `cmd_run`. Regression test: `test_r16_f03_blocks_symlinked_time_dir`.

### R16-F-05 — MEDIUM — `reference_csv` path not constrained to live under `case_dir` (closed in this batch)

**File:** `src/cfdtrust/audit/qoi.py` `_attempt_real_comparison`.

Pre-fix code: `ref_csv_path = case_dir / ref_csv_rel`. In Python's pathlib semantics, an absolute right-hand-side replaces the left: `Path("/foo") / "/bar" == PosixPath("/bar")`. So a manifest with `reference_csv: /etc/passwd` (or `reference_csv: ../../etc/hosts`) would resolve outside the case dir.

This isn't a code-execution exploit (we'd just try to parse the file as a CSV and ValueError out), but it violates the trust model: the case_dir should be self-contained, and any file the harness reads in service of a gate should be auditable as part of the case. An out-of-tree reference is unauditable.

**Fix (applied in this batch):**

1. Schema regex `"pattern": "^[^/].*"` on `reference_csv` — rejects absolute paths at validation time.
2. Runtime double-check: `Path(ref_csv_rel).is_absolute()` AND `_resolved_under(ref_csv_path, case_dir)`. Both `.resolve()`'d, so a relative `..`-traversal that escapes case_dir is also caught.
3. Three regression tests: `test_r16_f05_absolute_reference_csv_path_blocks`, `test_r16_f05_traversal_reference_csv_path_blocks`, `test_r16_f06_schema_rejects_absolute_reference_csv` (schema layer).

### R16-F-06 — LOW — manifest schema didn't constrain new 2d fields (closed in this batch)

**File:** `src/cfdtrust/schemas/case_manifest.schema.json` `reference_comparison`.

Pre-fix the schema's `reference_comparison` block only typed `status`, `source`, `tolerance`, `notes`. The 2d landing added six new fields (`source_url`, `source_sha256`, `reference_csv`, `reference_csv_sha256`, `qoi`, `x_min_compare_m`) but only via `additionalProperties: true`, so the schema neither documented nor validated them.

**Fix (applied in this batch):** all six fields are now in the schema with appropriate type and range constraints:
- `source_url`: string + `format: uri`
- `source_sha256` and `reference_csv_sha256`: `pattern: "^[a-fA-F0-9]{64}$"`
- `reference_csv`: relative-path pattern (see R16-F-05)
- `qoi`: non-empty string
- `tolerance`: `exclusiveMinimum: 0`
- `x_min_compare_m`: `minimum: 0`

Regression tests: `test_r16_f06_schema_rejects_negative_x_min_compare`, `test_r16_f06_schema_rejects_zero_tolerance`, `test_r16_f06_schema_rejects_absolute_reference_csv`.

### R16-F-07 — LOW — trust_report.json schema didn't enforce `validation_status=validated` → `reference_comparison.status=PASS` (closed in this batch)

**File:** `src/cfdtrust/schemas/trust_report.schema.json`.

Pre-fix the schema had one allOf rule: `validation_status=validated` requires `solver_execution=real`. The 2d audit-layer code (`audit/report.py`) now ALSO requires `reference_comparison.status=PASS` for `validated`, but the schema didn't echo that constraint. A future aggregator regression could mint `validation_status=validated` with a FAILed reference comparison.

**Fix (applied in this batch):** added an allOf rule requiring `gates.reference_comparison.status == "PASS"` whenever `validation_status == "validated"`. Regression test: `test_r16_f07_trust_report_schema_rejects_validated_with_failed_reference` (asserts both the rejection AND the positive case).

### R16-F-08 — LOW — qoi.csv column layout differs between real and mocked modes (closed in this batch)

**File:** `src/cfdtrust/audit/qoi.py` `_write_qoi_csv`.

Pre-fix: when `measured_cf` was present the CSV had 5 columns (`name,x_m,value,units,source`); when not, 4 columns (`name,value,units,source`). Any downstream consumer that depended on a fixed schema (Excel, pandas, the cockpit Trust Loop Status table) would silently break when the case flipped between mocked and real.

**Fix (applied in this batch):** both modes now emit the same 5-column header. Mocked rows carry an empty `x_m` field. Regression test: `test_r16_f08_qoi_csv_header_is_consistent_across_modes` asserts identical headers in both modes.

---

## What was probed and worked

- **Subprocess discipline** stayed clean — 2d added no new subprocess invocations; the polyMesh parsers are pure Python.
- **Regex DoS resistance**: all five regexes use bounded char classes; the `_parse_count_paren_block` paren-walk is O(n) not backtracking.
- **Cross-file consistency** in `extract_wall_cf`: boundary's `nFaces` vs `wallShearStress` vector count vs `faces[startFace:startFace+nFaces]` are all checked; mismatch → ValueError with diagnostic.
- **Honesty rule** preserved across new gate states: `validation_status=validated` requires both real solver AND PASS reference (now enforced by schema + aggregator + tests, three independent layers).
- **Re_L mismatch documented and tested**: the 14% over-prediction at x=1.9m AND the 68% under-prediction at x=0.03m are explained quantitatively in `provenance.md` AND fenced by the live-fixture test `test_real_openfoam_cf_compared_against_nasa_reference_lands_on_fail`.
- **Kinematic-vs-dynamic Cf convention**: the inline comment in `wall_shear.extract_wall_cf` documents the ρ-cancellation reasoning; matches NASA TMR's CFL3D convention.

---

## Cumulative severity trend

| Round                       | CRIT | HIGH | MED | LOW | Total |
|-----------------------------|------|------|-----|-----|-------|
| 13 (2a meta)                | 0    | 0    | 0   | 0   | 0     |
| 14 (2b meta + fix)          | 0    | 0    | 1   | 2   | 3     |
| 15 (2c meta + fix)          | 0    | 0    | 2   | 2   | 4     |
| **16 (2d meta + fix)**      | **0**| **0**| **2**| **5**| **7** |

All MEDs since round 13 have been honesty-rule failures, not security failures. The "what could produce a false PASS?" frame continues to outperform the "what could the harness do to the host?" frame for finding net-new bugs.

The "1 HIGH or 2 MED" pattern prediction has held for three consecutive sub-commits (14, 15, 16), all with new-external-dep / new-data-ingestion / new-format-parsing surface. The pattern is now load-bearing for planning future rounds.

---

## Pattern update — orthogonal axes are predictive, "total LOC" is not

Re-examining rounds 13-16:

| Round | LOC delta | Surface novelty                          | Findings   |
|-------|-----------|-------------------------------------------|------------|
| 13    | ~40       | tightened existing function              | 0          |
| 14    | ~200      | NEW: case-dir scaffold (OF dictionaries) | 1 MED+ 2 LOW |
| 15    | ~200      | NEW: docker subprocess + log parser      | 2 MED + 2 LOW |
| 16    | ~600      | NEW: external data + custom OF parsers   | 2 MED + 5 LOW |

The two **MED** counts didn't scale with LOC (round 16 is 3× round 15 by LOC but same MED count). The **LOW** count tracks total surface area. **Hypothesis**: MEDs are "honesty class" issues that scale with the *number of distinct trust-boundary crossings*, not with raw LOC. Each new external-data ingestion (round 14: case_dir dictionary trust; round 15: docker subprocess trust; round 16: NASA reference trust) is approximately one trust boundary and yields approximately 1-2 MEDs.

This refines the planning rule: next sub-commit that adds a NEW trust boundary (e.g. a real mesh_contract gate that reads `checkMesh` log, or a real qoi_stability gate that processes a time-series) should pre-budget for 1-2 MED fixes during meta-scan.

---

## Verdict

**PASS (mechanically closed)** on the round-16 batch.

All seven findings (2 MED + 5 LOW) have code fixes + regression tests; 160/160 pytest + 1 opt-in network skip. `make bootstrap-check` exit 0. The live trust loop (real Docker, real NASA reference, real comparison) still produces the same correct FAIL outcome that 2d landed.

Phase 1 step 2d is now structurally honest AND defended against the most plausible "make the gate lie" attacks: reference tampering (F-01), absolute-path manifest injection (F-05), and validation_status downgrade bypass (F-07). The trust harness's product hazard surface has shrunk one more notch.

---

## Recommended next options for the owner

1. **(α)** **Phase 1 close-out + Phase 2 planning**. Phase 1 milestone delivered: trust loop end-to-end against real CFD + real reference data, honesty rules preserved across 16 red-team rounds. Natural inflection point — write the Phase 1 retrospective and plan Phase 2 (real mesh_contract / qoi_stability gates) deliberately rather than autonomously.
2. **(β)** Continue pushing — start Phase 2 step 1 (mesh_contract gate de-mocking: parse `checkMesh` log, enforce manifest y+ target, drop the case's MOCKED gates one by one). The Phase 2 pattern prediction: per the orthogonal-axes hypothesis, expect 1-2 MED on the first checkMesh-parsing landing.
3. **(γ)** Tighten what's already there — add a `cfdtrust verify-reference` CLI subcommand that re-computes `reference_csv_sha256` and emits a fresh manifest stanza, to make legitimate reference updates a single command. ~30 min.
4. **(δ)** Natural session boundary.

Recommendation: **(α)**. Sixteen consecutive red-team rounds with all findings closed in-batch (or documented with concrete deferral rationale) is unusual project hygiene. The right move is to *publish* that state — write the Phase 1 retro, declare the milestone — before pushing into Phase 2. The autonomous push has earned its punctuation mark.
