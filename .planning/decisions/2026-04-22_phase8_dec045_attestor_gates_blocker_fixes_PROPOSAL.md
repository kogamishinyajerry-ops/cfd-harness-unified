---
decision_id: DEC-V61-045
status: IN_PROGRESS (Waves 1+2 landed 2026-04-22 per Kogami A2+b approval; Waves 3+4 deferred to Sprint 2)
waves_landed:
  - wave_1_A: 61c7cd1 (convergence_attestor loader + A1 exit + CA-005/006/007)
  - wave_1_B: 9e6f30f (comparator_gates VTK reader fix)
  - wave_1_C: 49ba6e5 (21 new tests for Wave 1)
  - wave_2_D: 396cefe (HAZARD tier in _derive_contract_status + U_ref plumb)
  - wave_2_E: ad0bad2 (12 new tests for Wave 2)
  - codex_verify: CV-S003q-01 VERIFIED @ ad0bad2 (233 passed + 1 skipped)
waves_deferred:
  - wave_3: TaskRunner reorder (attestor pre-comparator); deferred to Sprint 2
  - wave_4: A6 outer-iter semantics + per-case promote_to_fail; deferred to Sprint 2
timestamp: 2026-04-22T19:20 local
scope: |
  Phase 8 Sprint 1 follow-up — fix 8 Codex blockers across DEC-036b
  (CHANGES_REQUIRED, 3 blockers + 2 nits) and DEC-038 (BLOCK, 5 blockers
  + 3 nits). v6.2 independent-verification protocol surfaced substantial
  gaps between DEC-stated contracts and landed implementation. Combined
  fix DEC because both sides share orchestration touchpoints
  (_audit_fixture_doc + _derive_contract_status + TaskRunner flow).

  This DEC is a PROPOSAL — awaiting Kogami approval of scope + approach
  before any code change. Once approved, this becomes DEC-V61-045 with
  autonomous_governance path and pre-merge Codex review (self-pass well
  below 0.70 given complexity).

autonomous_governance: pending_kogami_approval
claude_signoff: proposal_only
codex_tool_invoked: false (no diff yet; pre-merge required before landing)
codex_rounds: 0
codex_verdict: not_yet_requested
external_gate_self_estimated_pass_rate: 0.50
  (Complex multi-module change touching orchestration + verdict engine +
  new YAML schema + attestor-pre-extraction reordering + 4-5 physics
  semantics fixes. self-pass notably low because the blast radius
  includes: (a) task_runner execution order change risks comparison_result
  not being populated for in-tolerance healthy runs, (b) HAZARD tier
  propagating to UI/API snapshot tests that may require fixture rebase,
  (c) A6 outer-iteration semantics redesign is genuinely non-trivial
  physics reasoning.)
reversibility: |
  Partially reversible. New YAML file is additive; tier wiring in
  _derive_contract_status is additive HAZARD set; attestor-pre-extraction
  move is a reordering (reversible by swap-back). A6 semantics rewrite is
  a behavior change that breaks impinging_jet expectations — irreversible
  without spec decision on correct A6 model.
---

# DEC-V61-045 (PROPOSAL): Attestor + Gates Blocker Fix Bundle

## Upstream findings

Both source DECs have codex_verdict on main but landed code contradicts DEC spec:

### DEC-V61-036b (CHANGES_REQUIRED)
Codex report: `reports/codex_tool_reports/20260422_dec036b_codex_review.md`
Codex independent pass-rate: 0.42 (claude-estimated 0.60)

- **B1** `expected_verdict` decided before attestor/gates run, never recomputed → stale PASS in fixture metadata + CLI summary
- **B2** G3 `U_ref` never resolved from `task_spec.boundary_conditions`; all cases audited at default 1.0
- **B3** `read_final_velocity_max()` scans every VTK incl. allPatches + earlier timesteps → false-positives
- S1 WARN paths print to stdout but don't stamp WARN concern
- S2 test coverage weaker than DEC claims

### DEC-V61-038 (BLOCK)
Codex report: `reports/codex_tool_reports/20260422_dec038_codex_review.md`
Codex independent pass-rate: 0.33 (claude-estimated 0.65)

- **CA-001** `_derive_contract_status()` hard-fails ONLY on A1/A4; A2/A3/A5/A6 ignored → in-band scalar w/ CONTINUITY_NOT_CONVERGED still returns PASS (defeats two-tier model)
- **CA-002** `TaskRunner.run_task()` executes comparator BEFORE attestor → non-converged runs flow through extraction+correction (violates "attestor first" contract)
- **CA-003** A1 log-only; never consumes `ExecutionResult.success` exit code; only matches `^Floating point exception`
- **CA-004** `knowledge/attestor_thresholds.yaml` DOES NOT EXIST despite being referenced → per-case override + HAZARD→FAIL promotion non-functional
- **CA-005** A3/A6 field-agnostic; produces incorrect A6 HAZARD on impinging_jet p_rgh (DEC expects A4-only)
- CA-006 "stuck" uses `< 1.0` decade, DEC says `<= 1.0`
- CA-007 A4 gap-block consecutiveness stricter than DEC
- CA-008 missing 10-case real-log integration matrix (only LDC+BFS)

## Proposed fix bundle (7 tracks, ordered by dependency)

### Track 1: Land `knowledge/attestor_thresholds.yaml` [DEC-038 CA-004]
- New file per DEC-038 spec section 4
- Schema validation (strict YAML → dataclass)
- Loader in `convergence_attestor.py` with per-case key lookup + default fallback
- Tests: unknown case → defaults; known case → override; malformed YAML → raise

### Track 2: Wire HAZARD tier in `_derive_contract_status` [DEC-038 CA-001]
- Add HAZARD concern set: `{A2: CONTINUITY_NOT_CONVERGED, A3: RESIDUALS_ABOVE_TARGET, A5: BOUNDING_RECURRENT, A6: NO_RESIDUAL_PROGRESS}`
- Promotion rule: per-case override can promote HAZARD→FAIL (from Track 1 YAML)
- Preserve A1/A4 hard-FAIL behavior (unchanged)
- Contract: in-band scalar + any HAZARD concern → `contract_status=HAZARD`
- Tests: 4 new test cases per concern code; 1 promotion override test

### Track 3: Move attestor pre-extraction in TaskRunner [DEC-038 CA-002]
- `TaskRunner.run_task()` reorder: solver → **attestor check** → (if FAIL/HAZARD with promotion) short-circuit correction generation, populate attestor-only ComparisonResult → UI still renders
- If PASS or unpromoted HAZARD → continue with comparator → correction
- Blast radius: `comparison_result` may be None for ATTEST_FAIL; UI/API must handle
- Tests: full E2E per path (PASS / HAZARD / ATTEST_FAIL)

### Track 4: Fix A1 to consume exit_code [DEC-038 CA-003]
- `attest()` takes `execution_result: ExecutionResult | None = None` param
- If `execution_result.success is False` → A1 FAIL regardless of log content
- Regex widen: `(Floating point exception|Floating exception|FOAM FATAL)` with consistent anchoring

### Track 5: Recompute `expected_verdict` post-gates [DEC-036b B1]
- `_audit_fixture_doc()` assembles concerns list → call `_derive_contract_status` helper → write back final verdict to fixture metadata
- Preserve "expected_verdict" as goldens-derived baseline; add "actual_verdict" for post-gate result
- CLI summary prints actual_verdict not expected_verdict

### Track 6: Plumb U_ref from task_spec [DEC-036b B2]
- `_audit_fixture_doc(task_spec, ...)` extract `u_ref = task_spec.boundary_conditions.get_ref_velocity()` helper
- Per flow_type: internal→inlet U, LDC→lid U, external→free-stream, buoyancy→reference
- Unresolved → `WARN` concern stamped in fixture (not just stdout)
- Pass through to `check_all_gates(U_ref=u_ref)`; `None` behaves per Track 4 semantics

### Track 7: Fix `read_final_velocity_max()` [DEC-036b B3]
- Identify latest-time VTK directory by numeric time suffix (not alphabetic sort)
- Exclude `allPatches/*.vtk` and boundary-patch VTK files; internal-field only
- Tests: multi-timestep tree with earlier spike + clean final → no false-fire

### Track 8 (A6 redesign) [DEC-038 CA-005]
- **Non-trivial physics call** — needs Kogami/Codex consultation:
  - Current A6 scans per-field Initial residual lines across every inner PBiCGStab/GAMG solve
  - Multi-solve outer iterations (buoyantFoam, pimpleFoam) have many inner solves per Time= block
  - Correct A6 should compare outer-step residuals (first solve of each Time=) rather than every inner solve
  - impinging_jet regression: A6 must NOT fire (A4 carries it); DHC A6 should still fire if stuck
- Risk: this behavioral change may flip other cases' attestor output

### Track 9 (Test matrix expansion) [DEC-036b S2, DEC-038 CA-008]
- Threshold-boundary tests for G3 (99·U_ref pass / 101·U_ref fail / U_ref=None WARN)
- 10-case real-log integration matrix for attestor (currently only LDC+BFS)
- VTK-branch test with crafted real-timestep-layout fixture
- WARN concern assertions (not just stdout)

## Execution plan

Sequential waves (due to dependency ordering):

**Wave 1**: Track 1 (YAML) + Track 4 (A1 exit-code) + Track 7 (VTK reader) + Track 9a (nit-level tests)
  — Independent, can parallelize via subagents

**Wave 2**: Track 2 (HAZARD tier) + Track 6 (U_ref plumb)
  — Depends on Wave 1 Track 1 (YAML loader for promotion)

**Wave 3**: Track 3 (TaskRunner reorder) + Track 5 (verdict recompute)
  — Depends on Wave 2 (HAZARD tier must be wired before reorder can short-circuit)

**Wave 4**: Track 8 (A6 redesign) + Track 9b (full integration matrix)
  — Highest risk; isolate to final wave for easier rollback

**Codex rounds**: ≥2 required per wave (pre-merge given self-pass 0.50). Total 8 rounds minimum.

## Risks

1. **Fixture rebase cascade**: Wave 2+3 flip many test fixtures from PASS to HAZARD (correct behavior) — this is UI/API snapshot churn.
2. **impinging_jet behavior change**: Wave 4 A6 redesign flips impinging_jet from A4+A6 to A4-only; any downstream consumer expecting A6 concern breaks.
3. **TaskRunner reorder blast radius**: Wave 3 changes task_runner execution order; any caller expecting comparison_result always populated breaks.
4. **YAML schema drift**: Wave 1 introduces YAML schema that must stay forward-compatible.
5. **Self-pass 0.50 realistic**: with 8 tracks and 4 waves, expect ≥1 Codex CHANGES_REQUIRED round before final APPROVE.

## Scope decision points for Kogami

Kogami should explicitly approve/reject:

(a) **Execute all 9 tracks autonomously** (Claude drives, Codex audits per wave) — est. 3-5 sessions
(b) **Execute Waves 1-2 only** (low-risk additive fixes); defer Waves 3-4 to Phase 8 Sprint 2
(c) **Pivot** — accept DEC-036b/038 current state as "known gap" and plan v2 in Sprint 2 rather than patch
(d) **Delete + rewrite** — landed code has substantial contract gap; full rewrite may be cleaner than patch
(e) **Other** — Kogami-defined

Recommendation: **(b) Waves 1-2**. Rationale:
- Wave 1 is low-risk additive (YAML + A1 exit-code + VTK reader + unit tests)
- Wave 2 wires the HAZARD tier which is the single most important gap (CA-001)
- Wave 3 (TaskRunner reorder) has high blast radius; deferring allows Sprint 2 dedicated session
- Wave 4 (A6 redesign) needs physics discussion, not just code change
- Delivering Waves 1-2 captures ~60% of blocker remediation with ~30% of total risk

---

**Status**: PROPOSAL ONLY. No code changed. Awaiting Kogami scope decision.
**Author**: Claude Code Opus 4.7 (v6.2 Main Driver)
**Related**: DEC-V61-036b (CHANGES_REQUIRED), DEC-V61-038 (BLOCK)
