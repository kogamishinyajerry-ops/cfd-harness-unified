---
decision_id: DEC-V61-074
title: P2-T1.a · ExecutorMode ABC + 4-mode skeleton (skeleton-only · trust-core untouched)
status: Accepted (2026-04-26 · skeleton-only sub-scope landed at 16000ab · Codex APPROVE round 3 · 46/46 executor tests green · ~930 full-suite pass / 1 pre-existing flake / 2 skipped)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: 治理收口 anchor session · P2-T1 kickoff
parent_dec: DEC-V61-073 (4-PC closure 2026-04-26 · status=Accepted as of 06e5f29)
parent_specs:
  - docs/specs/EXECUTOR_ABSTRACTION.md (v0.2 · canonical ExecutorMode + ExecutorAbc contract)
  - .planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md (P2-T0 · COMPATIBLE_WITH_MANIFEST_TAG_EXTENSION)
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.80
external_gate_actual_outcome: APPROVE_AFTER_2_REVISIONS (R1: 3 findings — StrEnum vs (str, Enum), RunReport contract weakness, fallback test假覆盖; R2 closed all 3 + introduced 1 MED — bare-string notes char-explosion; R3 closed; final APPROVE @ 16000ab)
pc_closure_commits:
  P2-T1.a-R1: 479597f (initial skeleton · 15 files · 1301 LOC · 39 tests)
  P2-T1.a-R2: 20afaaf (StrEnum + RunReport hardening + fallback test fix · folded into parallel session's gov commit by accident — see SUMMARY for attribution note · 45 tests)
  P2-T1.a-R3: 16000ab (bare-string notes char-explosion fix · 46 tests)
sub_scope_rationale: |
  P2-T1's full implementation per the spike F-3 migration plan touches
  src/audit_package/manifest.py (trust-core 5 modules) to add the
  additive `executor` field. Per RETRO-V61-001 baseline + §10.5.4a
  surface 1 (FoamAgentExecutor call sites), trust-core writes require
  Codex pre-merge review. To keep this commit's blast radius small and
  avoid mixing the kickoff-skeleton with a trust-core-touching change,
  P2-T1 is split:
    - **T1.a (this DEC)**: skeleton-only — new src/executor/ package
      under Plane.EXECUTION, ExecutorMode StrEnum + ExecutorAbc ABC +
      4 mode-stub classes, plane assignment update, tests. NO writes
      under trust-core 5 modules.
    - **T1.b (next session)**: manifest.py additive `executor` field +
      TaskRunner dispatch + TrustGate routing per §6.1 + legacy
      compatibility tests. Trust-core write — Codex pre-merge review
      mandatory.
notion_sync_status: pending
---

# DEC-V61-074 · P2-T1 ExecutorMode ABC + 4-mode skeleton

## Why

DEC-V61-073's 4-PC arc closed Accepted at 06e5f29:
- PC-2 EXECUTOR_ABSTRACTION.md v0.2 with §5 hybrid-init invariant + §6
  TrustGate routing → Codex APPROVE
- PC-3 sampling_audit.py budget gate + 24 tests → Codex APPROVE
- PC-4 §10.5.4a 7-surface canonical + chronology bridges → Codex APPROVE

P2-T1 is the first concrete implementation of the EXECUTOR_ABSTRACTION
spec. It introduces the `ExecutorMode` enum + `ExecutorAbc` ABC + 4
concrete mode-stub classes that subsequent P2-T2..T5 tasks fill in
with real behavior:

- DEC-V61-075 (P2-T2): `FoamAgentExecutor` → docker-openfoam wrapping
- DEC-V61-076 (P2-T3): `MockExecutor` re-tag as `ExecutorMode.MOCK`
- DEC-V61-077 (P2-T4): hybrid-init mode (requires SBPS §1 ratify)
- DEC-V61-078 (P2-T5): future-remote stub doc-only
- DEC-V61-079 (P2 closeout retro)

## Decision

### T1.a sub-scope (this commit)

Land skeleton structures with **no** changes to trust-core 5 modules:

1. **New package `src/executor/`** (Plane.EXECUTION):
   - `__init__.py` — public surface: `ExecutorMode`, `ExecutorAbc`,
     `ExecutorStatus`, `RunReport`, the 4 mode classes.
   - `base.py` — `ExecutorMode(StrEnum)` with values `mock`,
     `docker_openfoam`, `hybrid_init`, `future_remote`;
     `ExecutorStatus(StrEnum)` with values `OK`, `MODE_NOT_APPLICABLE`,
     `MODE_NOT_YET_IMPLEMENTED`; `RunReport` frozen dataclass;
     `ExecutorAbc` ABC with `MODE` classvar + `VERSION` classvar +
     `contract_hash` property + abstract `execute(task_spec)`.
   - `docker_openfoam.py` — `DockerOpenFOAMExecutor(ExecutorAbc)`:
     wraps `src.foam_agent_adapter.FoamAgentExecutor` (read-only).
     `execute()` delegates to wrapped instance, packages the
     `ExecutionResult` into a `RunReport` with `status=OK`.
   - `mock.py` — `MockExecutor(ExecutorAbc)`: returns synthetic
     `ExecutionResult` (no Docker, no OpenFOAM). Skeleton-only;
     P2-T3 will re-tag the existing `src.foam_agent_adapter.MockExecutor`
     to use this abstraction.
   - `hybrid_init.py` — `HybridInitExecutor(ExecutorAbc)`: skeleton
     returns `RunReport(status=MODE_NOT_APPLICABLE, ...)` per §5.2 of
     the spec (the surrogate isn't built yet; no case is applicable).
     P2-T4 will land the real surrogate-warm-start behavior.
   - `future_remote.py` — `FutureRemoteExecutor(ExecutorAbc)`: skeleton
     returns `RunReport(status=MODE_NOT_YET_IMPLEMENTED, ...)`. P2-T5
     will document the HPC contract; no implementation this milestone.

2. **`src/_plane_assignment.py`**: add
   `"src.executor": Plane.EXECUTION` to the assignment table. Run
   plane-guard tests to verify no four-plane contract violations.

3. **`tests/test_executor_modes/`**:
   - `test_executor_abc.py` — enum membership (4 values, exact spelling),
     ExecutorAbc subclass enforcement (`MODE` ClassVar + abstract
     `execute`), RunReport invariants (frozen, mode/status/notes),
     contract_hash determinism (same class → same hash; different
     class → different hash).
   - `test_docker_openfoam_wrapper.py` — `DockerOpenFOAMExecutor`
     delegates to a wrapped CFDExecutor instance (mocked); the
     wrapped instance's `ExecutionResult` is packaged into a
     `RunReport(status=OK, mode=DOCKER_OPENFOAM, ...)`.
     Acknowledges P2-T2 will provide the real Docker integration.
   - `test_mock_executor_skeleton.py` — `MockExecutor` returns
     `RunReport(status=OK, mode=MOCK, ...)` with synthetic
     `ExecutionResult.is_mock=True`. Forward-compat with P2-T3.
   - `test_hybrid_init_skeleton.py` — `HybridInitExecutor` returns
     `RunReport(status=MODE_NOT_APPLICABLE, mode=HYBRID_INIT,
     execution_result=None, notes=("hybrid_init_skeleton_no_surrogate",))`.
     §5.2 contract held.
   - `test_future_remote_skeleton.py` — `FutureRemoteExecutor` returns
     `RunReport(status=MODE_NOT_YET_IMPLEMENTED, mode=FUTURE_REMOTE,
     execution_result=None, notes=("future_remote_stub_only",))`.

4. **`tests/methodology/test_sampling_audit.py`** (regression):
   confirm a fake commit diff modifying `src/executor/` does NOT
   trigger any §10.5.4a surface flag (new package is in
   Plane.EXECUTION but not on the audit-required list).

### T1.b out-of-scope (deferred to next session)

The following land in DEC-V61-074 R2 (or a new DEC-V61-074a if scope
warrants splitting):

- `src/audit_package/manifest.py` additive `executor` top-level field
  per spike F-3 migration plan. Trust-core write — pre-merge Codex
  review mandatory per RETRO-V61-001.
- `src/task_runner.py` dispatch via `ExecutorMode` (read manifest's
  `executor.mode`, route to the right `ExecutorAbc` subclass).
- `src/metrics/trust_gate.py` per-mode verdict ceilings per §6.1 (mock
  ceiling = WARN with note `mock_executor_no_truth_source`;
  hybrid_init defers to OpenFOAM `canonical_artifacts`; future_remote
  refuses to score).
- Round-trip + legacy-compat tests:
  `test_manifest_tag_round_trip` and
  `test_legacy_signed_zip_compatibility`.

### Acceptance criteria for T1.a

1. `pytest tests/test_executor_modes/ -q` → all pass.
2. `pytest -q` (full suite) — net-positive vs baseline 884 passed (PC
   closure baseline). No new failures.
3. Plane-guard tests still pass after `_plane_assignment.py` update.
4. `python -m scripts.methodology.sampling_audit --range HEAD~1..HEAD`
   on the T1.a commit emits **zero** §10.5.4a flags
   (i.e. the new `src/executor/` package does not touch any
   audit-required surface).
5. Codex review of the `src/executor/` package + tests +
   plane-assignment update returns APPROVE (post-commit; no
   pre-merge required because no trust-core write).

## Impact

| Item | Value |
| --- | --- |
| New files | 5 src/executor/* + 5 tests/test_executor_modes/* |
| Lines of code | ~300 src + ~250 tests (estimate) |
| Trust-core writes | **0** |
| §10.5.4a surfaces touched | **0** (verified by sampling_audit run) |
| Plane assignments | +1 (`src.executor` → Plane.EXECUTION) |
| Codex review mode | post-commit (no trust-core touch) |
| Predicted pass-rate | 0.80 — clear contract spec; mechanical drift between spec text and Python expressions is the main risk vector |

## Counter v6.1

`autonomous_governance_counter_v61` advances **48 → 49** (this DEC's
`autonomous_governance: true`).

## Cross-references

- **Parent DEC**: DEC-V61-073 (4-PC closure)
- **Parent spec**: `docs/specs/EXECUTOR_ABSTRACTION.md` v0.2
- **Compatibility spike**: `.planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md`
- **ADR-001 plane contract**: `docs/adr/ADR-001-four-plane-import-enforcement.md`
- **Existing executors**: `src/foam_agent_adapter.py:22` (MockExecutor)
  + `src/foam_agent_adapter.py:520` (FoamAgentExecutor) — both
  implement `src.models.CFDExecutor` Protocol (line 190); P2-T1 wraps
  them at a higher abstraction without modifying either.

## Branch + commits

Direct-to-main per §10 治理降级 (no trust-core write; skeleton +
plane-assignment + tests only).

---

## P2-T1.a closure addendum (2026-04-26 · post-Codex APPROVE)

Status flips from `PROPOSED` to `Accepted`. P2-T1.a (skeleton-only
sub-scope) is GREEN.

### Codex review history

| Round | Commit | Verdict | Findings closed | New findings |
| --- | --- | --- | --- | --- |
| R1 | `479597f` | CHANGES_REQUIRED | — | 3 (StrEnum, RunReport contract, fallback test) |
| R2 | `20afaaf` * | CHANGES_REQUIRED | 3 (R1 closed) | 1 MED (bare-string notes char-explosion) |
| R3 | `16000ab` | **APPROVE** | 1 (R2 closed) | 0 |

\* **Attribution note**: R2 source edits (StrEnum switch + RunReport
type-checks + fallback test rewrite) were swept into a parallel
Claude session's commit `20afaaf` (titled "land Opus Gate authority
verdict") by their `git add -A` running between my edit and my
intended `git commit`. The R2 source content matches what I authored;
attribution is misaligned but functional state is correct. R3 is a
clean self-attributed commit.

### Self-pass-rate calibration data (RETRO candidate)

- Estimated 0.80; actual outcome `APPROVE_AFTER_2_REVISIONS`.
- Codex caught **only mechanical class-of-bug** issues:
  - Type-system footguns: `(str, Enum)` not equivalent to `StrEnum`
    in Python's `__str__` semantics; bare-string `notes` triggers
    `tuple("alpha")` char-explosion.
  - Test-coverage假象: a fallback-path test that never actually
    exercises the fallback.
- Zero findings on the higher-level contract (ExecutorAbc enforcement,
  MODE_NOT_APPLICABLE escape semantics, trust-core boundary
  preservation, plane assignment).
- 0.80 estimate was honest within tolerance; type-system rigor is the
  consistent failure mode for spec-driven Python skeleton work.

### Test posture at closure (HEAD `16000ab`)

| Suite | Count | Status |
| --- | --- | --- |
| `tests/test_executor_modes/*` | 46 | ✅ all pass |
| `tests/test_plane_*` + `test_gen_importlinter` | 50 | ✅ all pass |
| Full repo suite | ~930 | ✅ pass / 1 pre-existing `test_build_trust_gate_report_resolves_display_title_to_slug` flake / 2 skipped |

Net change vs DEC-V61-073 PC closure baseline (884 passed): **+46
tests** added by this DEC, **0 regressions**.

### §10.5.4a sampling-audit smoke run

```
sampling-audit budget gate · range=479597f^..16000ab
  estimated_tokens=14k cap=100000
  surfaces_flagged: (none)
  verdict=OK
```

Zero §10.5.4a surfaces flagged for the entire P2-T1.a arc — confirms
trust-core boundary held throughout (no FoamAgentExecutor call sites
added, no Docker/subprocess reachability changes, no /api routes,
no reports/ persistence, no user_drafts→TaskSpec plumbing, no
correction_spec/ writes, no .planning/case_profiles/ writes).

### What's queued for next session (P2-T1.b)

Per the sub-scope rationale in this DEC's frontmatter:

1. **`src/audit_package/manifest.py`** additive `executor` top-level
   field per spike F-3. **Trust-core write** — Codex pre-merge review
   mandatory (RETRO-V61-001 baseline + §10.5.4a surface 1).
2. **`src/task_runner.py`** dispatch via `ExecutorMode` (read
   manifest's `executor.mode`, route to right `ExecutorAbc` subclass).
3. **`src/metrics/trust_gate.py`** per-mode verdict ceilings per §6.1
   (mock = WARN with note; hybrid_init defers to OpenFOAM artifact;
   future_remote refuses to score).
4. **Round-trip + legacy-compat tests**:
   - `test_manifest_tag_round_trip` — `read(write(manifest))` survives
     the new `executor` field.
   - `test_legacy_signed_zip_compatibility` — pre-P2 zips verify with
     absent `executor` field treated as `DOCKER_OPENFOAM`.
5. Possible new DEC `DEC-V61-074a` if T1.b warrants its own kickoff;
   otherwise extends this DEC with a "P2-T1.b closure" addendum.

### Counter v6.1

`autonomous_governance_counter_v61` advances **48 → 49** (this DEC's
`autonomous_governance: true`). Per RETRO-V61-001 risk-tier-driven
cadence, no STOP threshold; counter remains pure telemetry.

### Notion sync pending

Frontmatter `notion_sync_status: pending` — sync to Notion Decisions
DB after closure. Co-sync `pc_closure_commits` map +
`external_gate_actual_outcome` field for audit-portal completeness.
