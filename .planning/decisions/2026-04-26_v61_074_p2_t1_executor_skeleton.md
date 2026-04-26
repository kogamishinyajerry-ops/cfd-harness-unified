---
decision_id: DEC-V61-074
title: P2-T1 · ExecutorMode ABC + 4-mode skeleton + manifest tagging + dispatch + routing (full P2-T1 scope · T1.a skeleton + T1.b integration)
status: Accepted (2026-04-26 · full P2-T1 scope landed · T1.a skeleton at 16000ab Codex APPROVE round 3 · T1.b.1 pre-merge at f599129 Codex APPROVE round 2 + LOW verbatim · T1.b.2+T1.b.3 post-commit at 69c0ed6+c7ede01 Codex APPROVE round 2 after 8d7f990 fix closing 2 MED + 1 LOW · 49/49 executor tests · 119/119 audit_package tests · 966/968 full-suite pass / 0 fail / 2 skipped)
authored_by: Claude Code Opus 4.7 (1M context)
authored_at: 2026-04-26
authored_under: 治理收口 anchor session · P2-T1 kickoff
parent_dec: DEC-V61-073 (4-PC closure 2026-04-26 · status=Accepted as of 06e5f29)
parent_specs:
  - docs/specs/EXECUTOR_ABSTRACTION.md (v0.2 · canonical ExecutorMode + ExecutorAbc contract)
  - .planning/specs/EXECUTOR_ABSTRACTION_compatibility_spike.md (P2-T0 · COMPATIBLE_WITH_MANIFEST_TAG_EXTENSION)
autonomous_governance: true
external_gate_self_estimated_pass_rate: 0.80 (T1.a) / 0.65 (T1.b)
external_gate_actual_outcome: APPROVE_AFTER_2_REVISIONS_T1A (R1: 3 findings — StrEnum vs (str, Enum), RunReport contract weakness, fallback test假覆盖; R2 closed all 3 + introduced 1 MED — bare-string notes char-explosion; R3 closed; final APPROVE @ 16000ab) · APPROVE_AFTER_1_REVISION_T1B1 (R1: 1 HIGH — class-identity contract_hash vs spec-derived; R2: APPROVE_WITH_COMMENTS, 1 LOW — stale inline comment closed verbatim within RETRO-V61-001 5-condition exception) · APPROVE_AFTER_1_REVISION_T1B2_T1B3 (post-commit R1: 2 MED + 1 LOW — short-circuit Notion write-back missing, WARN ceiling histogram incoherence, _extract_mode non-mapping crash; R2 at 8d7f990 closed all 3 + 10 regression tests, APPROVE_WITH_COMMENTS 0 blocking)
pc_closure_commits:
  P2-T1.a-R1: 479597f (initial skeleton · 15 files · 1301 LOC · 39 tests)
  P2-T1.a-R2: 20afaaf (StrEnum + RunReport hardening + fallback test fix · folded into parallel session's gov commit by accident — see SUMMARY for attribution note · 45 tests)
  P2-T1.a-R3: 16000ab (bare-string notes char-explosion fix · 46 tests)
  P2-T1.b.1: f599129 (manifest tagging + spec-derived contract_hash · folded into parallel claude-opus47-app session's notion-sync commit by accident — see P2-T1.b closure addendum attribution note · +5 manifest tests + +3 contract_hash_pinning tests)
  P2-T1.b.2: 69c0ed6 (TaskRunner ExecutorMode dispatch + short-circuit · clean self-attribution · +7 dispatch tests)
  P2-T1.b.3: c7ede01 (TrustGate per-ExecutorMode routing §6.1 + §6.3 · clean self-attribution · +10 routing tests)
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
notion_sync_status: synced 2026-04-26 (https://www.notion.so/DEC-V61-074-P2-T1-ExecutorMode-ABC-manifest-tagging-dispatch-routing-full-P2-T1-scope-T-34ec68942bed8124a43ad6f75af3dfe8)
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

---

## P2-T1.b closure addendum (2026-04-26 · post-Codex APPROVE)

P2-T1.b (manifest tagging + TaskRunner dispatch + TrustGate
per-mode routing) GREEN. Status flips from `Accepted` (skeleton-only
sub-scope) to `Accepted (full scope)`. The DEC now covers the full
P2-T1 surface; no DEC-V61-074a was opened — T1.b's blast radius
matched the addendum extension threshold (single trust-core write +
two non-trust-core wires + co-located tests).

### Codex review history (T1.b · pre-merge required for trust-core write)

| Round | Diff target | Verdict | Findings closed | New findings |
| --- | --- | --- | --- | --- |
| R1 | T1.b.1 unstaged (manifest.py + tests) | CHANGES_REQUIRED | — | 1 HIGH (`contract_hash` class-identity hash, not spec-derived per §3/F-3 + §6.3) |
| R2 | T1.b.1 unstaged (R2 patch on src/executor/base.py + 3 pinning tests) | APPROVE_WITH_COMMENTS | 1 HIGH (R1 closed) | 1 LOW (stale inline comment at manifest.py:467 still cited class-qualname derivation) |
| R2-verbatim | inline comment fix (5 LOC, 1 file, manifest.py only) | APPROVE-equivalent | 1 LOW (R2 closed verbatim) | 0 |

R2-verbatim qualifies for the §10.5.4 / RETRO-V61-001 5-condition
verbatim exception (≤20 LOC, ≤2 files, no public API surface change,
diff-level match to Codex `Suggested fix`, references R2 finding ID).
No additional Codex round triggered for the comment swap.

T1.b.2 (`src/task_runner.py` dispatch) and T1.b.3
(`src/metrics/trust_gate.py` per-mode routing) post-commit Codex
review per RETRO-V61-001 baseline (`src.metrics` spec implementation
+ adapter-boundary modification ≥5 LOC). Both batched as a single
review request; they live outside trust-core 5 so pre-merge was not
mandatory.

| Round | Diff target | Verdict | Findings |
| --- | --- | --- | --- |
| Post-commit R1 | 69c0ed6 + c7ede01 (batched) | CHANGES_REQUIRED on both | T1.b.2 1 MED (short-circuit bypassed Notion write-back, breaking `notion_client` `success=False → Status=Review` contract) · T1.b.3 1 MED (WARN ceiling left `count_by_status` unchanged → `overall=WARN AND has_warnings=False` public-API correctness bug) · T1.b.3 1 LOW (`_extract_mode` AttributeError on non-mapping `executor` payload) |
| Post-commit R2 | 8d7f990 (single fix commit closing all 3 R1 findings + 10 regression tests) | **APPROVE_WITH_COMMENTS** | 0 blocking · 2 advisory: (a) histogram-bump approach acceptable in current API shape — caveat: `sum(count_by_status.values()) > len(reports)` after ceiling, no in-tree consumer assumes that invariant; future refactor option = dedicated `routing_ceiling_applied` field if `TrustGateReport` becomes broader external contract (deferred · non-blocking) · (b) confirms test verification posture under repo `.venv` (27 + 70 tests green) |

**Post-commit Codex APPROVE achieved. T1.b.2 + T1.b.3 fully closed.**

Self-pass-rate calibration update: T1.b post-commit estimated 0.80,
actual = APPROVE_AFTER_1_REVISION (3 substantive findings on
otherwise-mechanical wiring/routing — Codex catches integration gaps
that local test scope misses, specifically: adjacent-system contracts
like Notion write-back, public-API histogram coherence, and schema-
robustness on non-mapping payloads). 0.80 was over-confident for
T1.b's recurring "Codex catches what local tests don't" pattern.

### Self-pass-rate calibration data (RETRO candidate)

- T1.b.1 estimated 0.65; actual outcome `APPROVE_AFTER_1_REVISION`
  (R2 closed R1's HIGH; LOW handled verbatim). 0.65 honest within
  tolerance — Codex caught a substantive contract drift (skeleton
  class-identity hash slipped into T1.b without being upgraded to
  spec-derived per the `base.py` docstring's own forecast). Higher-
  impact than T1.a's mechanical-class-of-bug findings (Codex's
  consistent failure-detection mode for spec-driven Python work
  remains: spec-vs-code mechanical drift, type-system rigor gaps).
- The R1 finding was foreshadowed by `src/executor/base.py:172-178`
  T1.a docstring text: *"For P2-T1 skeleton this is *not* the SHA-256
  of a frozen spec file (per §3 ideal); that integration lands in
  P2-T1.b."* T1.b.1 missed honoring that promise on first attempt;
  Codex caught the gap in R1.

### P2-T1.b commits

- **T1.b.1 (manifest tagging + R2 contract_hash fix)**: `f599129`
  *(see attribution note below — this commit's authorship is
  misaligned)*
- **T1.b.2 (TaskRunner ExecutorMode dispatch)**: `69c0ed6` (clean
  self-attribution)
- **T1.b.3 (TrustGate per-mode routing)**: `c7ede01` (clean
  self-attribution)
- **T1.b.4 (this closure addendum + STATE.md sync)**: `2a5e9c4`
- **T1.b post-commit fix (Codex R1 → R2 closure)**: `8d7f990`
  (closes 2 MED + 1 LOW · +10 regression tests · 966/968 full-suite)

#### Attribution note for T1.b.1 (`f599129`)

The T1.b.1 source edits (`src/audit_package/manifest.py` +
`src/executor/base.py` + tests/test_audit_package/test_manifest.py +
`tests/test_executor_modes/test_executor_abc.py`) were swept into a
parallel `claude-opus47-app` session's commit `f599129` (titled
"gov(notion-sync): DEC-V61-085 PROPOSED synced") by their `git add -A`
running between this session's specific-file `git add` and intended
`git commit`. The 5-file diff in `f599129` (384 insertions / 14
deletions) is dominated by T1.b.1 content; only the V61-085 doc
frontmatter touchup is theirs.

Same root cause as P2-T1.a R2 (commit `20afaaf` attribution
misalignment) — concurrent-session interleaving. The brief's
explicit ban on `git add -A` is the right rule but it doesn't bind
the parallel session, only this one. Functional state is correct;
attribution is misaligned. T1.b.2 + T1.b.3 commits got in cleanly
because they were staged + committed within a single tool call each,
beating the parallel session's window.

### Test posture at closure (HEAD `c7ede01`)

| Suite | Count | Status |
| --- | --- | --- |
| `tests/test_executor_modes/*` | 49 | ✅ all pass (was 46 at T1.a; +3 contract_hash_pinning) |
| `tests/test_audit_package/*` | 119 | ✅ all pass (was 114; +5 TestExecutorManifestField) |
| `tests/test_metrics/*` | 87 | ✅ all pass (added +10 trust_gate_executor_mode_routing) |
| `tests/test_task_runner_executor_mode.py` | 7 | ✅ all pass (new file) |
| `tests/test_task_runner.py` | 25 | ✅ all pass (no regression on legacy CFDExecutor path) |
| Full repo suite | 956 passed / 2 skipped / 0 failed (at c7ede01 closure) → **966 passed / 2 skipped / 0 failed** (after 8d7f990 post-commit fix · +10 regression tests) | ✅ |

Net change vs. T1.a closure baseline (~930 passed / 1 pre-existing
flake / 2 skipped): **+25 tests** (5 manifest + 7 dispatch + 10
routing + 3 pinning), **+1 flake closed** (parallel session's
`d349e4d` fixed `test_build_trust_gate_report_resolves_display_title_to_slug`
during this session via sys.modules+parent-attr restore in
`tests/test_plane_guard_edge.py`'s polluter — independent fix, not
part of T1.b scope but contributing to the GREEN posture).

### EXECUTOR_ABSTRACTION.md §3/§6.1/§6.3 contract surface delivered

| Spec clause | Implementation surface | T1.b commit |
| --- | --- | --- |
| §3 additive `executor` manifest field | `src/audit_package/manifest.py:_build_executor_section` + `build_manifest(executor=...)` kwarg | `f599129` (attribution-misaligned, see note) |
| §3 / F-3 spec-derived `contract_hash` | `src/executor/base.py:_executor_spec_sha256` + rewritten `ExecutorAbc.contract_hash` property | `f599129` |
| §6.1 `mock` ceiling = WARN | `apply_executor_mode_routing` + `_NOTE_MOCK_NO_TRUTH_SOURCE` | `c7ede01` |
| §6.1 `future_remote` refusal → `ModeNotYetImplementedError` | `apply_executor_mode_routing` + `ModeNotYetImplementedError` exception | `c7ede01` |
| §6.3 `hybrid_init` reference-run gate | `apply_executor_mode_routing` `hybrid_init_reference_run_present` flag + `_NOTE_HYBRID_INIT_INVARIANT_UNVERIFIED` | `c7ede01` |
| §6.4 trust-core boundary preservation | `src.metrics.trust_gate` reads manifest's `executor.mode` as opaque string (no `src.executor` import); plane Contract 2 honored | `c7ede01` |
| TaskRunner dispatch on ExecutorMode | `src/task_runner.py` `executor_mode` / `executor_abc` kwargs + `_resolve_executor_abc` registry + short-circuit helper | `69c0ed6` |

### Risk-flag intake adoption (per spec §7)

T1.b lands the following risk flags inline:

- ✅ `manifest_tag_round_trip_test`: covered by
  `test_executor_field_round_trips_through_zip_serialization`.
- ✅ `legacy_signed_zip_compatibility_test`: covered by
  `test_legacy_signed_zip_compatibility_no_executor_field` +
  `test_legacy_manifest_treated_as_docker_openfoam` (trust_gate
  routing fallback).
- ✅ `executor_contract_hash_pinning`: covered by
  `TestExecutorContractHashPinning` (3 tests; pinned per Codex R1
  fix as the verbatim mitigation for the HIGH finding).
- ⏸ `executable_smoke_test` (V61-053): deferred to P2-T2
  (FoamAgentExecutor → docker-openfoam wrapping) — there's no
  end-to-end Docker smoke run in T1.b scope; skeleton substitution
  via MagicMock is the appropriate scope for dispatch-contract tests.
- ⏸ `solver_stability_on_novel_geometry` (V61-053): deferred to
  P2-T4 (HybridInitExecutor real-surrogate landing); the skeleton
  uniformly returns MODE_NOT_APPLICABLE which is the §5.2 escape, not
  a solver-stability outcome.

### What's queued for next session (P2-T2)

DEC-V61-075 (P2-T2): `FoamAgentExecutor → docker-openfoam wrapping`
is **unblocked** by this closure. T2's scope substantializes the
`DockerOpenFOAMExecutor` from skeleton (passes-through to wrapped
`FoamAgentExecutor.execute`) to a fully-formed adapter that:

1. Constructs the manifest via `build_manifest(executor=DockerOpenFOAMExecutor())`
   automatically (the §3 contract identity now flows through).
2. Lands the §6.3 reference-run resolution path (the
   `hybrid_init_reference_run_present` flag's actual data source) —
   probably `src.audit_package` decision-trail introspection.
3. Wires the `executable_smoke_test` for whitelist cases (V61-053
   risk flag #4).

Per the brief's explicit ban on opening P2-T2 in this session, T2
remains pending until CFDJerry kicks off the next session.

### Counter v6.1

`autonomous_governance_counter_v61` advances **49 → 50** (this
addendum's `autonomous_governance: true`). Per RETRO-V61-001 risk-
tier-driven cadence, no STOP threshold; counter remains pure
telemetry. RETRO trigger conditions checked:

- Phase close: P2-T1 not yet closed (T2..T5 still queued); no
  phase-close retro yet.
- Counter ≥20: counter at 50 — clearly ≥20, but RETRO-V61-001 was
  the most recent arc-size retro (counter at ~46 at that retro's
  filing); next arc-size retro is candidate when counter reaches
  ~60-70 or after P2 closeout (whichever comes first).
- PR `CHANGES_REQUIRED`: T1.b.1 R1 was CHANGES_REQUIRED — qualifies
  as an incident retro candidate but the resolution scope (single
  HIGH finding closed in 1 round) is well-trodden ground (same class
  of "spec-vs-code mechanical drift" as T1.a R2). No new retro
  needed; logged in this addendum's calibration data.
- Post-R3 live-run defect: N/A (no executable smoke test in T1.b
  scope).

### Notion sync pending

Frontmatter `notion_sync_status: pending` — sync entire DEC (T1.a +
T1.b coverage) to Notion Decisions DB after closure. Co-sync the
P2-T1.b commits map + `external_gate_actual_outcome` field
(`APPROVE_AFTER_1_REVISION_T1B1` or similar) for audit-portal
completeness.
